import os
import json
import time
import requests
import sys
from datetime import timedelta
import configparser

# Groq API URL
GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# 支持的输出格式
supported_formats = {
    "srt": "SRT字幕格式",
    "text": "纯文本格式"
}

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

# 默认配置
DEFAULT_CONFIG = {
    "Settings": {
        "proxy": "",
        "last_used_key": "",
        "output_format": "srt"
    },
    "APIKeys": {}
}


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()

    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(CONFIG_FILE):
        for section, items in DEFAULT_CONFIG.items():
            config[section] = items

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE, encoding='utf-8')

        # 确保所有必要的部分都存在
        for section, items in DEFAULT_CONFIG.items():
            if section not in config:
                config[section] = {}

            # 确保每个部分都有必要的键
            for key, value in items.items():
                if key not in config[section]:
                    config[section][key] = value

    return config


def save_config(config):
    """保存配置到文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)


def get_proxy_settings():
    """获取代理设置"""
    config = load_config()
    return config['Settings']['proxy']


def get_last_used_key():
    """获取上次使用的API密钥"""
    config = load_config()
    return config['Settings']['last_used_key']


def get_output_format():
    """获取输出格式设置"""
    config = load_config()
    return config['Settings']['output_format']


def save_proxy_settings(proxy):
    """保存代理设置"""
    config = load_config()
    config['Settings']['proxy'] = proxy
    save_config(config)


def save_last_used_key(key):
    """保存上次使用的API密钥"""
    config = load_config()
    config['Settings']['last_used_key'] = key
    save_config(config)


def save_output_format(format):
    """保存输出格式设置"""
    config = load_config()
    config['Settings']['output_format'] = format
    save_config(config)


def get_api_keys():
    """获取所有API密钥"""
    config = load_config()
    return dict(config['APIKeys'])


def add_api_key(name, key):
    """添加API密钥"""
    config = load_config()
    config['APIKeys'][name] = key
    save_config(config)


def remove_api_key(name):
    """删除API密钥"""
    config = load_config()
    if name in config['APIKeys']:
        del config['APIKeys'][name]
        save_config(config)


# 支持的模型
supported_models = {
    "whisper-large-v3": {
        "name": "Whisper Large V3",
        "description": "高精度多语言转写",
    },
    "whisper-large-v3-turbo": {
        "name": "Whisper Large V3 Turbo",
        "description": "更快速度的多语言转写",
    },
    "distil-whisper-large-v3-en": {
        "name": "Distil Whisper Large V3 (英语)",
        "description": "优化的英语转写",
    }
}

# 支持的语言（常用语言列表）
supported_languages = {
    "zh": "中文",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "pt": "葡萄牙语",
    "it": "意大利语"
}


def format_timestamp(seconds, always_include_hours=True):
    """
    将秒数转换为SRT格式的时间戳 (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)

    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"


def create_srt_from_segments(segments):
    """
    从时间戳段生成SRT格式字幕
    """
    srt_content = ""

    for i, segment in enumerate(segments, start=1):
        # 支持两种可能的数据结构
        if isinstance(segment, dict):
            start_time = segment.get("start", 0)
            end_time = segment.get("end", 0)
            text = segment.get("text", "").strip()
        else:
            # 如果是对象而不是字典
            start_time = getattr(segment, "start", 0)
            end_time = getattr(segment, "end", 0)
            text = getattr(segment, "text", "").strip()

        # 确保字幕文本不为空
        if not text:
            continue

        # 格式化为SRT格式的条目
        srt_entry = f"{i}\n{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n{text}\n\n"
        srt_content += srt_entry

    return srt_content


def transcribe_audio(audio_file_path, output_path=None, model="whisper-large-v3", language=None,
                     output_format="srt", progress_callback=None, max_segment_size=None):
    """
    使用Groq API的Whisper模型将音频文件转写为指定格式

    参数:
    - audio_file_path: 音频文件路径
    - output_path: 输出文件路径（如果不提供，将使用与音频文件相同的名称但扩展名根据格式变化）
    - model: 使用的Whisper模型名称，默认为"whisper-large-v3"
    - language: 音频语言代码（可选）
    - output_format: 输出格式，"srt"或"text"
    - progress_callback: 进度回调函数(stage, percentage)
    - max_segment_size: 最大段落大小（字节），用于大文件拆分

    返回:
    - 生成的文件路径列表
    """
    # 检查文件是否存在
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_file_path}")

    # 如果未提供输出路径，则使用默认路径
    if output_path is None:
        base_name = os.path.splitext(audio_file_path)[0]
        extension = ".srt" if output_format == "srt" else ".txt"
        output_path = f"{base_name}{extension}"

    # 获取API密钥
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("未设置GROQ_API_KEY环境变量")

    # 获取代理设置
    proxy = get_proxy_settings()
    proxies = {}

    if proxy:
        try:
            # 如果是SOCKS代理，检查是否安装了PySocks
            if proxy.startswith('socks'):
                try:
                    import socks
                except ImportError:
                    if progress_callback:
                        progress_callback("warning", 0)
                    raise Exception("使用SOCKS代理需要安装PySocks库。请使用pip install PySocks命令安装后再尝试。")

            # 对于SOCKS代理，使用socks5h://前缀以便在代理服务器上进行DNS解析
            if proxy.startswith('socks5://'):
                proxy = proxy.replace('socks5://', 'socks5h://')

            # 设置代理字典
            proxies = {
                'http': proxy,
                'https': proxy
            }
        except Exception as e:
            if progress_callback:
                progress_callback("error", 0)
            raise Exception(f"代理设置错误: {str(e)}")

    # 设置API请求参数
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    # 如果提供了进度回调函数，通知上传开始
    if progress_callback:
        progress_callback("uploading", 0)

    try:
        # 打开音频文件并准备上传
        with open(audio_file_path, "rb") as audio_file:
            if progress_callback:
                progress_callback("uploading", 30)

            # 准备请求数据
            files = {
                "file": (os.path.basename(audio_file_path), audio_file, "audio/mpeg")
            }

            # 设置响应格式
            response_format = "verbose_json" if output_format == "srt" else "text"

            data = {
                "model": model,
                "response_format": response_format,
                "temperature": 0.0
            }

            # 如果提供了语言参数，则添加
            if language:
                data["language"] = language

            if progress_callback:
                progress_callback("uploading", 60)

            # 发送请求
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                files=files,
                data=data,
                proxies=proxies
            )

            if progress_callback:
                progress_callback("processing", 0)

            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败 (状态码: {response.status_code}): {response.text}"
                raise Exception(error_msg)

            if progress_callback:
                progress_callback("processing", 50)

            # 处理不同格式的响应
            if output_format == "srt":
                # 解析JSON响应
                transcription = response.json()

                # 提取分段信息
                if "segments" in transcription:
                    segments = transcription["segments"]
                else:
                    # 如果没有分段信息，创建一个简单的分段
                    segments = [{"start": 0, "end": 0, "text": transcription.get("text", "")}]

                if progress_callback:
                    progress_callback("processing", 70)

                # 创建SRT内容
                content = create_srt_from_segments(segments)
            else:
                # 纯文本格式，直接使用响应文本
                content = response.text

            if progress_callback:
                progress_callback("downloading", 0)

            # 写入文件
            with open(output_path, "w", encoding="utf-8") as output_file:
                output_file.write(content)

            if progress_callback:
                progress_callback("downloading", 100)

            return [output_path]

    except Exception as e:
        raise Exception(f"转写过程中出错: {str(e)}")


def split_output_file(content, output_path, output_format, max_segment_size):
    """
    拆分过大的输出文件为多个小文件

    参数:
    - content: 要拆分的内容
    - output_path: 原始输出路径
    - output_format: 输出格式
    - max_segment_size: 最大段落大小（字节）

    返回:
    - 生成的文件路径列表
    """
    # 获取基本路径信息
    base_path, extension = os.path.splitext(output_path)
    file_paths = []

    if output_format == "srt":
        # 拆分SRT文件
        srt_entries = content.split("\n\n")
        current_part = 1
        current_content = ""
        current_index = 1

        for entry in srt_entries:
            if not entry.strip():
                continue

            # 替换索引号为当前索引
            entry_lines = entry.splitlines()
            if len(entry_lines) >= 1 and entry_lines[0].isdigit():
                entry_lines[0] = str(current_index)
            entry = "\n".join(entry_lines)

            # 测试添加这个条目后的大小
            test_content = current_content
            if current_content:
                test_content += "\n\n"
            test_content += entry

            # 如果超过大小限制，保存当前内容并开始新文件
            if len(test_content.encode('utf-8')) > max_segment_size and current_content:
                part_path = f"{base_path}_part{current_part}{extension}"
                with open(part_path, "w", encoding="utf-8") as f:
                    f.write(current_content)
                file_paths.append(part_path)

                # 重置变量
                current_part += 1
                current_content = entry
                current_index = 1
            else:
                # 添加到当前内容
                current_content = test_content
                current_index += 1

        # 保存最后一部分
        if current_content:
            part_path = f"{base_path}_part{current_part}{extension}"
            with open(part_path, "w", encoding="utf-8") as f:
                f.write(current_content)
            file_paths.append(part_path)
    else:
        # 拆分纯文本文件
        # 尝试按段落拆分
        paragraphs = content.split("\n\n")
        current_part = 1
        current_content = ""

        for paragraph in paragraphs:
            # 测试添加这个段落后的大小
            test_content = current_content
            if current_content and not current_content.endswith("\n\n"):
                test_content += "\n\n"
            test_content += paragraph

            # 如果超过大小限制，保存当前内容并开始新文件
            if len(test_content.encode('utf-8')) > max_segment_size and current_content:
                part_path = f"{base_path}_part{current_part}{extension}"
                with open(part_path, "w", encoding="utf-8") as f:
                    f.write(current_content)
                file_paths.append(part_path)

                # 重置变量
                current_part += 1
                current_content = paragraph
            else:
                # 添加到当前内容
                current_content = test_content

        # 保存最后一部分
        if current_content:
            part_path = f"{base_path}_part{current_part}{extension}"
            with open(part_path, "w", encoding="utf-8") as f:
                f.write(current_content)
            file_paths.append(part_path)

    return file_paths


# 保留原函数名以保持向后兼容
def transcribe_audio_to_srt(audio_file_path, output_srt_path=None, model="whisper-large-v3", language=None, progress_callback=None):
    """
    使用Groq API的Whisper模型将音频文件转写为SRT格式 (向后兼容函数)
    """
    return transcribe_audio(
        audio_file_path=audio_file_path,
        output_path=output_srt_path,
        model=model,
        language=language,
        output_format="srt",
        progress_callback=progress_callback
    )[0]  # 返回第一个文件路径


# 用于测试
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python audio_to_srt_core.py <音频文件路径> [输出文件路径] [模型名称] [语言代码]")
        sys.exit(1)

    audio_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    model = sys.argv[3] if len(sys.argv) > 3 else "whisper-large-v3"
    lang = sys.argv[4] if len(sys.argv) > 4 else None


    def print_progress(stage, percentage):
        print(f"{stage}: {percentage}%")


    try:
        srt_path = transcribe_audio_to_srt(audio_file, output_file, model, lang, print_progress)
        print(f"转写完成! SRT文件已保存到: {srt_path}")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)