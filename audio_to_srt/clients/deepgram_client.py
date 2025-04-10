import os
import traceback
from typing import Optional, Callable, Dict, Any, List

from api_clients import APIClientBase, print_debug
from utils.subtitle_formatter import format_subtitle_text
from utils.timestamp_formatter import format_timestamp


class DeepgramClient(APIClientBase):
    """Deepgram API客户端"""

    def __init__(self, api_key: str, proxy: Optional[str] = None):
        super().__init__(api_key, proxy)
        self._client = None

    def _create_client(self):
        """创建Deepgram客户端"""
        # 首先检查是否安装了Deepgram库
        try:
            import deepgram
        except ImportError as e:
            error_msg = f"未安装deepgram库: {e}。请使用pip install deepgram-sdk安装。"
            print_debug(error_msg)
            raise ImportError(error_msg)

        try:
            # 导入必要的模块
            from deepgram import Deepgram, DeepgramClientOptions

            print_debug("开始创建Deepgram客户端")

            # 创建客户端选项
            options = DeepgramClientOptions()
            
            # 如果有代理配置，设置代理
            if self.proxy:
                print_debug(f"配置代理: {self.proxy}")
                # 注意：Deepgram SDK可能不直接支持代理，可能需要配置环境变量
                # 这里是示例代码，需要根据实际SDK调整
                options.proxy = self.proxy

            # 创建客户端
            self._client = Deepgram(self.api_key, options)
            print_debug("成功创建Deepgram客户端")

            return self._client

        except Exception as e:
            error_msg = f"创建Deepgram客户端失败: {e}"
            print_debug(error_msg)
            traceback.print_exc()
            raise Exception(error_msg)

    def get_client(self):
        """获取客户端"""
        if not self._client:
            self._create_client()
        return self._client

    async def transcribe(self,
                         file_path: str,
                         output_format: str = "srt",
                         language: Optional[str] = None,
                         progress_callback: Optional[Callable] = None,
                         **kwargs) -> str:
        """
        使用Deepgram API转写音频文件

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
            # 获取客户端
            client = self.get_client()

            if progress_callback:
                progress_callback("上传中", 30)

            # 提取选项
            model = kwargs.get("model", "nova-2")
            version = kwargs.get("version", "latest")
            smart_format = kwargs.get("smart_format", True)
            punctuate = kwargs.get("punctuate", True)
            diarize = kwargs.get("diarize", False)
            detect_language = kwargs.get("detect_language", True)
            multichannel = kwargs.get("multichannel", False)
            keywords = kwargs.get("keywords", [])
            tier = kwargs.get("tier", "base")
            sample_rate = kwargs.get("sample_rate", None)
            timestamps = kwargs.get("timestamps", "word")
            confidence = kwargs.get("confidence", 0.7)

            # 读取文件内容
            with open(file_path, "rb") as audio_file:
                audio_data = audio_file.read()

            if progress_callback:
                progress_callback("处理中", 50)

            # 准备请求选项
            options = {
                "model": model,
                "smart_format": smart_format,
                "punctuate": punctuate,
                "diarize": diarize,
                "multichannel": multichannel,
                "tier": tier,
                "utterances": True,
            }
            
            # 添加条件选项
            if version != "latest":
                options["version"] = version
                
            if language and not detect_language:
                options["language"] = language
            elif detect_language:
                options["detect_language"] = True
                
            if sample_rate:
                options["sample_rate"] = sample_rate
                
            if keywords:
                options["keywords"] = keywords if isinstance(keywords, list) else keywords.split(",")
                
            if timestamps:
                options["timestamps"] = timestamps

            print_debug(f"Deepgram请求选项: {options}")

            # 执行异步转写
            try:
                # 注意：此处API调用需要根据实际的Deepgram Python SDK调整
                # 这是一个示例实现，需要修改以适应实际SDK
                from deepgram import PrerecordedOptions
                dg_options = PrerecordedOptions(**options)
                response = await client.transcription.prerecorded.v("1").transcribe(audio_data, dg_options)
                print_debug(f"Deepgram响应: {str(response)[:200]}...")
                
            except Exception as e:
                error_msg = f"Deepgram API调用错误: {e}"
                print_debug(error_msg)
                traceback.print_exc()
                raise Exception(error_msg)

            if progress_callback:
                progress_callback("格式化", 80)

            # 处理响应结果
            if output_format == "srt":
                # 将结果转换为SRT格式
                # 这里需要根据Deepgram的实际响应结构调整
                content = self._create_srt(response, confidence)
            else:
                # 提取完整文本
                content = self._extract_text(response)

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

    def _create_srt(self, response, confidence_threshold=0.7):
        """从Deepgram响应创建SRT格式字幕"""
        try:
            # 示例实现，需要根据实际Deepgram SDK响应调整
            srt_content = ""
            index = 1
            
            # 尝试获取段落或句子
            if hasattr(response, "results") and hasattr(response.results, "utterances"):
                utterances = response.results.utterances
                for utterance in utterances:
                    start = float(utterance.start)
                    end = float(utterance.end)
                    text = utterance.transcript
                    confidence = float(utterance.confidence)
                    
                    # 只包含高于阈值的内容
                    if confidence >= confidence_threshold:
                        srt_entry = f"{index}\n{format_timestamp(start)} --> {format_timestamp(end)}\n{text}\n\n"
                        srt_content += srt_entry
                        index += 1
            
            # 如果没有找到分段，尝试使用整个转写文本
            if not srt_content and hasattr(response, "results") and hasattr(response.results, "channels"):
                channels = response.results.channels
                if len(channels) > 0 and hasattr(channels[0], "alternatives"):
                    alternatives = channels[0].alternatives
                    if len(alternatives) > 0 and hasattr(alternatives[0], "transcript"):
                        transcript = alternatives[0].transcript
                        if transcript:
                            srt_content = f"1\n00:00:00,000 --> 00:05:00,000\n{transcript}\n\n"
            
            # 如果还是没有内容，添加默认条目
            if not srt_content:
                srt_content = "1\n00:00:00,000 --> 00:01:00,000\n[无法识别内容]\n\n"
                
            return srt_content
            
        except Exception as e:
            print_debug(f"创建SRT内容时出错: {e}")
            traceback.print_exc()
            return "1\n00:00:00,000 --> 00:01:00,000\n[处理错误]\n\n"

    def _extract_text(self, response):
        """从Deepgram响应中提取文本"""
        try:
            # 示例实现，需要根据实际Deepgram SDK响应调整
            if hasattr(response, "results") and hasattr(response.results, "channels"):
                channels = response.results.channels
                if len(channels) > 0 and hasattr(channels[0], "alternatives"):
                    alternatives = channels[0].alternatives
                    if len(alternatives) > 0 and hasattr(alternatives[0], "transcript"):
                        return alternatives[0].transcript
            
            # 如果找不到文本，返回空字符串
            print_debug("无法从Deepgram响应中提取文本")
            return "[无法提取文本]"
            
        except Exception as e:
            print_debug(f"提取文本时出错: {e}")
            traceback.print_exc()
            return "[提取错误]"

    def close(self):
        """关闭客户端连接"""
        if self._client:
            print_debug("关闭Deepgram客户端")
            # 释放资源
            self._client = None