import os
import json
import traceback
from typing import Optional, Callable, Dict, Any

from api_clients import APIClientBase, print_debug
from utils.subtitle_formatter import format_subtitle_text
from utils.timestamp_formatter import format_timestamp


class GroqClient(APIClientBase):
    """Groq API客户端"""

    def __init__(self, api_key: str, proxy: Optional[str] = None):
        super().__init__(api_key, proxy)
        self._async_client = None

    def _create_async_client(self):
        """创建异步客户端"""
        try:
            # 首先检查是否安装了 groq
            try:
                import groq
            except ImportError as e:
                error_msg = f"未安装groq库: {e}。请使用pip install groq安装。"
                print_debug(error_msg)
                raise ImportError(error_msg)

            # 导入必要的模块
            import groq
            import httpx
            from groq import AsyncGroq

            print_debug("开始创建AsyncGroq客户端")

            # 按照官方示例设置代理
            if self.proxy:
                print_debug(f"配置代理: {self.proxy}")

                # 创建带代理的httpx异步客户端 - 与测试代码保持一致
                httpx_client = httpx.AsyncClient(
                    proxy=self.proxy,
                    transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0")
                )

                # 使用httpx客户端创建groq客户端
                self._async_client = AsyncGroq(
                    api_key=self.api_key,
                    http_client=httpx_client
                )
                print_debug("成功创建带代理的AsyncGroq客户端")
            else:
                # 不使用代理
                self._async_client = AsyncGroq(api_key=self.api_key)
                print_debug("成功创建无代理的AsyncGroq客户端")

            return self._async_client

        except Exception as e:
            error_msg = f"创建Groq客户端失败: {e}"
            print_debug(error_msg)
            traceback.print_exc()
            raise Exception(error_msg)

    def get_async_client(self):
        """获取异步客户端"""
        if not self._async_client:
            self._create_async_client()
        return self._async_client

    async def transcribe(self,
                         file_path: str,
                         output_format: str = "srt",
                         language: Optional[str] = None,
                         progress_callback: Optional[Callable] = None,
                         **kwargs) -> str:
        """
        使用Groq API转写音频文件

        参数:
        - file_path: 音频文件路径
        - output_format: 输出格式
        - language: 语言代码（可选）
        - progress_callback: 进度回调函数
        - **kwargs: 高级选项

        返回:
        - 输出文件路径
        """
        print_debug(f"开始转写: {file_path}")
        print_debug(f"转写选项: {kwargs}")

        # 检查文件是否存在
        if not os.path.exists(file_path):
            error_msg = f"音频文件不存在: {file_path}"
            print_debug(error_msg)
            raise FileNotFoundError(error_msg)

        # 计算输出路径
        base_name = os.path.splitext(file_path)[0]
        extension = ".srt" if output_format == "srt" else ".txt"
        output_path = f"{base_name}{extension}"

        # 检查文件是否已存在，如果存在则重命名
        counter = 1
        while os.path.exists(output_path):
            output_path = f"{base_name}_{counter}{extension}"
            counter += 1

        if progress_callback:
            progress_callback("准备中", 10)

        try:
            # 获取异步客户端
            client = self.get_async_client()

            if progress_callback:
                progress_callback("上传中", 30)

            # 提取选项
            model = kwargs.get("model", "whisper-large-v3")
            timestamps = kwargs.get("timestamps", "granular")
            temperature = kwargs.get("temperature", 0.0)
            translate = kwargs.get("translate", False)
            max_line_count = kwargs.get("max_line_count", 2)
            max_line_width = kwargs.get("max_line_width", 42)

            # 使用文件对象 - 与测试代码保持一致
            with open(file_path, "rb") as audio_file:
                # 设置请求参数
                if progress_callback:
                    progress_callback("处理中", 50)

                # 准备API调用参数 - 与测试代码保持一致
                request_params = {
                    "model": model,
                    "file": audio_file,
                    "response_format": "verbose_json" if output_format == "srt" else "text"
                }

                # 添加条件参数
                if language and not translate:
                    request_params["language"] = language

                if translate:
                    request_params["translate"] = True
                    if language:
                        request_params["task"] = f"translate:{language}"

                if timestamps != "granular":
                    request_params["timestamps"] = timestamps

                if temperature != 0.0:
                    request_params["temperature"] = temperature

                print_debug(f"API请求参数: {str(request_params)[:200]}...")

                # 执行异步转写
                try:
                    # 与测试代码保持完全一致的调用方式
                    transcription = await client.audio.transcriptions.create(**request_params)
                except Exception as e:
                    error_msg = f"API调用错误: {e}"
                    print_debug(error_msg)
                    traceback.print_exc()
                    raise Exception(error_msg)

                if progress_callback:
                    progress_callback("格式化", 80)

                # 处理响应结果
                print_debug(f"获取到转写结果，类型: {type(transcription)}")

                # 将响应对象转换为字典以便于调试
                if hasattr(transcription, 'model_dump'):
                    # 如果是Pydantic模型对象
                    response_dict = transcription.model_dump()
                elif hasattr(transcription, '__dict__'):
                    # 如果是普通对象
                    response_dict = transcription.__dict__
                else:
                    # 如果是字典或其他类型
                    response_dict = transcription if isinstance(transcription, dict) else {"text": str(transcription)}

                print_debug(f"转写响应内容片段: {str(response_dict)[:200]}...")

                if output_format == "srt":
                    # 转换为SRT格式
                    segments = []

                    # 支持多种可能的数据结构
                    if isinstance(response_dict, dict):
                        # 检查不同可能的键名
                        if "segments" in response_dict:
                            segments = response_dict["segments"]
                        elif "results" in response_dict and "segments" in response_dict["results"]:
                            segments = response_dict["results"]["segments"]

                    print_debug(f"找到 {len(segments)} 个分段")
                    content = self._create_srt_from_segments(segments, max_line_count, max_line_width)

                    # 如果没有分段但有完整文本，创建一个简单的SRT
                    if not segments and "text" in response_dict:
                        print_debug("没有找到分段信息，创建简单SRT")
                        content = "1\n00:00:00,000 --> 00:05:00,000\n" + response_dict["text"] + "\n\n"
                else:
                    # 直接使用文本
                    if isinstance(response_dict, dict) and "text" in response_dict:
                        content = response_dict["text"]
                    elif hasattr(transcription, "text"):
                        content = transcription.text
                    else:
                        content = str(transcription)

                print_debug(f"准备写入输出文件: {output_path}")
                print_debug(f"输出内容长度: {len(content)} 字符")

                # 写入输出文件
                with open(output_path, "w", encoding="utf-8") as output_file:
                    output_file.write(content)

                if progress_callback:
                    progress_callback("完成", 100)

                return output_path

        except Exception as e:
            error_msg = f"转写过程中出错: {str(e)}"
            print_debug(error_msg)
            traceback.print_exc()
            raise Exception(error_msg)

    def _create_srt_from_segments(self, segments, max_line_count=2, max_line_width=42):
        """从时间戳段生成SRT格式字幕"""
        srt_content = ""
        print_debug(f"开始处理分段，共 {len(segments)} 个")
        print_debug(f"字幕设置: 最大行数={max_line_count}, 每行最大字符数={max_line_width}")

        try:
            for i, segment in enumerate(segments, start=1):
                # 支持字典或对象格式的分段
                if isinstance(segment, dict):
                    start_time = segment.get("start", 0)
                    end_time = segment.get("end", 0)
                    text = segment.get("text", "").strip()
                else:
                    # 如果是对象
                    start_time = getattr(segment, "start", 0)
                    end_time = getattr(segment, "end", 0)
                    text = getattr(segment, "text", "").strip()

                # 确保字幕文本不为空
                if not text:
                    continue

                # 格式化文本 - 应用最大行数和每行最大字符数
                formatted_text = format_subtitle_text(text, max_line_count, max_line_width)

                # 格式化为SRT格式的条目
                srt_entry = f"{i}\n{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n{formatted_text}\n\n"
                srt_content += srt_entry

        except Exception as e:
            print_debug(f"创建SRT内容时出错: {e}")
            traceback.print_exc()

        print_debug(f"SRT生成完成，总长度: {len(srt_content)} 字符")
        # 如果没有内容，添加一个简单条目避免空文件
        if not srt_content:
            print_debug("生成的SRT为空，添加默认条目")
            srt_content = "1\n00:00:00,000 --> 00:01:00,000\n[无法识别内容]\n\n"

        return srt_content

    def close(self):
        """关闭客户端连接"""
        if self._async_client:
            print_debug("关闭异步客户端")
            # 不使用异步关闭方式，避免事件循环问题
            self._async_client = None