import os
import tempfile
import subprocess
import shutil
from pathlib import Path
from pydub import AudioSegment


class VideoToAudioConverter:
    """
    使用PyDub提供的功能从视频文件中提取音频
    """

    def __init__(self, ffmpeg_path=None):
        self.ffmpeg_path = ffmpeg_path
        self._check_dependencies()

    def _check_dependencies(self):
        """
        检查是否安装了必要的依赖项
        """
        try:
            # 如果指定了ffmpeg路径，则设置环境变量
            if self.ffmpeg_path:
                os.environ["FFMPEG_BINARY"] = self.ffmpeg_path
                os.environ["FFPROBE_BINARY"] = self.ffmpeg_path.replace("ffmpeg", "ffprobe")

            # 使用subprocess直接测试ffmpeg而不创建临时文件
            ffmpeg_cmd = "ffmpeg" if not self.ffmpeg_path else self.ffmpeg_path
            try:
                subprocess.run([ffmpeg_cmd, "-version"], check=True, encoding='utf-8', capture_output=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                raise Exception("FFmpeg未安装或无法运行。请安装FFmpeg或指定正确的路径。")

        except Exception as e:
            if "ffmpeg" in str(e).lower() or "avconv" in str(e).lower():
                raise Exception("缺少必要的依赖项: FFmpeg未安装或无法找到。"
                                "请访问 https://ffmpeg.org/download.html 下载并安装，"
                                "或在设置中指定FFmpeg可执行文件路径。") from e
            raise

    def get_audio_info(self, video_path):
        """
        获取视频中音频轨道的信息

        参数:
            video_path (str): 输入视频文件的路径

        返回:
            dict: 包含音频信息的字典
        """
        try:
            # 确保视频文件存在
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")

            # 确定ffprobe命令
            ffprobe_cmd = "ffprobe"
            if self.ffmpeg_path:
                ffprobe_path = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
                if os.path.exists(ffprobe_path):
                    ffprobe_cmd = ffprobe_path

            # 先获取格式信息（包含整体信息）
            format_cmd = [
                ffprobe_cmd,
                "-v", "error",
                "-show_entries", "format=duration,bit_rate,size",
                "-of", "json",
                video_path
            ]

            print(f"执行格式信息命令: {' '.join(format_cmd)}")
            format_result = subprocess.run(format_cmd, capture_output=True, text=True, encoding='utf-8', check=False)

            format_info = {}
            if format_result.returncode == 0:
                import json
                format_data = json.loads(format_result.stdout)
                format_info = format_data.get("format", {})

            # 获取视频文件大小
            video_file_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
            if format_info.get("size"):
                try:
                    video_file_size = int(format_info["size"])
                except (ValueError, TypeError):
                    pass

            # 构建命令来获取音频流信息
            stream_cmd = [
                ffprobe_cmd,
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,channels,sample_rate,bit_rate,duration",
                "-of", "json",
                video_path
            ]

            print(f"执行音频流信息命令: {' '.join(stream_cmd)}")
            stream_result = subprocess.run(stream_cmd, capture_output=True, text=True, encoding='utf-8', check=False)

            # 默认值
            codec_name = "未知"
            channels = 2
            sample_rate = 44100
            audio_bit_rate = 0
            duration = 0

            if stream_result.returncode == 0:
                stream_data = json.loads(stream_result.stdout)

                # 如果有有效的音频流
                if stream_data.get("streams"):
                    stream_info = stream_data.get("streams", [{}])[0]
                    codec_name = stream_info.get("codec_name", codec_name)
                    channels = int(stream_info.get("channels", channels)) if stream_info.get("channels") else channels
                    sample_rate = int(stream_info.get("sample_rate", sample_rate)) if stream_info.get("sample_rate") else sample_rate

                    # 获取音频流持续时间
                    if stream_info.get("duration"):
                        duration = float(stream_info.get("duration"))

                    # 获取音频流比特率
                    if stream_info.get("bit_rate"):
                        try:
                            audio_bit_rate = int(stream_info.get("bit_rate"))
                        except (ValueError, TypeError):
                            audio_bit_rate = 0

            # 如果音频流中没有持续时间，使用格式信息中的持续时间
            if duration == 0 and format_info.get("duration"):
                try:
                    duration = float(format_info.get("duration"))
                except (ValueError, TypeError):
                    duration = 0

            # 如果音频流没有比特率，尝试使用其他方法估算
            if audio_bit_rate == 0:
                # 1. 从格式信息中获取总比特率，然后估算音频比特率
                if format_info.get("bit_rate"):
                    try:
                        total_bit_rate = int(format_info.get("bit_rate"))
                        # 不同类型视频中音频占比不同，这里假设音频占10-20%
                        audio_bit_rate = int(total_bit_rate * 0.15)
                    except (ValueError, TypeError):
                        pass

                # 2. 如果仍然没有比特率，根据编解码器和声道数设置一个标准值
                if audio_bit_rate == 0:
                    # 特别注意立体声会翻倍比特率
                    base_rates = {
                        "aac": 96000,  # 每声道约96kbps
                        "mp3": 128000,  # 每声道约128kbps
                        "opus": 48000,  # 每声道约48kbps
                        "vorbis": 96000,  # 每声道约96kbps
                        "flac": 320000,  # 每声道约320kbps
                        "pcm_s16le": 705600,  # 16位每声道约705.6kbps (44.1kHz)
                        "pcm_s24le": 1058400  # 24位每声道约1058.4kbps (44.1kHz)
                    }

                    # 获取基础比特率，如果没有匹配的编解码器则使用默认值
                    base_rate = base_rates.get(codec_name, 128000)

                    # 根据声道数调整比特率
                    audio_bit_rate = base_rate * channels

            # 计算音频大小（字节）
            estimated_size = (audio_bit_rate / 8) * duration

            # 构建返回值
            result = {
                "codec": codec_name,
                "channels": channels,
                "sample_rate": sample_rate,
                "bit_rate": audio_bit_rate,
                "duration": duration,
                "estimated_size": estimated_size,
                "estimated_size_mb": estimated_size / (1024 * 1024),  # 转换为MB
                "video_file_size_mb": video_file_size / (1024 * 1024),  # 转换为MB
                "channels_description": "单声道" if channels == 1 else f"{channels}声道"
            }

            print(f"音频信息: {result}")
            return result

        except Exception as e:
            print(f"获取音频信息失败: {str(e)}")
            # 返回基本信息而不是失败
            return {
                "codec": "未知",
                "channels": 2,
                "sample_rate": 44100,
                "bit_rate": 256000,  # 默认立体声128kbps
                "duration": 0,
                "estimated_size": 0,
                "estimated_size_mb": 0,
                "video_file_size_mb": os.path.getsize(video_path) / (1024 * 1024) if os.path.exists(video_path) else 0,
                "channels_description": "立体声"
            }

    def extract_audio(self, video_path, output_format=None):
        """
        直接提取视频中的音频轨道而不进行转码

        参数:
            video_path (str): 输入视频文件的路径
            output_format (str, optional): 如果指定，则使用该扩展名保存

        返回:
            str: 输出音频文件的路径
        """
        try:
            # 确保视频文件存在
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")

            video_path = Path(video_path)

            # 获取音频信息
            audio_info = self.get_audio_info(str(video_path))
            codec = audio_info["codec"]

            # 确定输出格式和扩展名
            if output_format:
                ext = output_format
            else:
                # 根据编解码器确定文件扩展名
                codec_to_ext = {
                    "aac": "aac",
                    "mp3": "mp3",
                    "opus": "opus",
                    "vorbis": "ogg",
                    "flac": "flac",
                    "pcm_s16le": "wav",
                    "pcm_s24le": "wav",
                    "pcm_f32le": "wav"
                }
                ext = codec_to_ext.get(codec, "m4a")

            output_path = video_path.with_suffix(f".{ext}")

            # 确保输出目录存在
            output_dir = os.path.dirname(str(output_path))
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 使用ffmpeg直接提取
            ffmpeg_cmd = "ffmpeg"
            if self.ffmpeg_path:
                ffmpeg_cmd = self.ffmpeg_path

            cmd = [
                ffmpeg_cmd,
                "-i", str(video_path),
                "-vn",  # 不要视频
                "-acodec", "copy",  # 复制音频流
                "-y",  # 覆盖现有文件
                str(output_path)
            ]

            # 打印诊断信息
            print(f"执行命令: {' '.join(cmd)}")

            # 执行命令
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=False)

                # 检查命令是否成功
                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    print(f"ffmpeg提取失败: {error_msg}")
                    # 尝试回退到转换方式
                    print("尝试使用转码方式提取音频...")
                    return self.convert(
                        str(video_path),
                        output_format=ext,
                        sample_rate=audio_info["sample_rate"],
                        channels=audio_info["channels"]
                    )

                # 检查文件是否存在
                if not os.path.exists(str(output_path)) or os.path.getsize(str(output_path)) == 0:
                    print("输出文件不存在或大小为0，尝试使用转码方式...")
                    return self.convert(
                        str(video_path),
                        output_format=ext,
                        sample_rate=audio_info["sample_rate"],
                        channels=audio_info["channels"]
                    )

                return str(output_path)

            except subprocess.SubprocessError as e:
                print(f"执行ffmpeg命令失败: {str(e)}")
                # 尝试回退到转换方式
                return self.convert(
                    str(video_path),
                    output_format=ext,
                    sample_rate=audio_info["sample_rate"],
                    channels=audio_info["channels"]
                )

        except Exception as e:
            print(f"音频提取失败: {str(e)}")
            raise Exception(f"音频提取失败: {str(e)}") from e

    def convert(self, video_path, output_format="opus", sample_rate=16000, channels=1, bitrate=None):
        """
        将视频文件转换为音频文件

        参数:
            video_path (str): 输入视频文件的路径
            output_format (str): 输出音频格式，默认为opus
            sample_rate (int): 输出音频采样率，默认为16000Hz
            channels (int): 输出音频声道数，默认为1（单声道）
            bitrate (str): 输出音频比特率，如果为None则使用默认推荐值

        返回:
            str: 输出音频文件的路径
        """
        try:
            # 确保视频文件存在
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")

            # 计算输出路径
            video_path = Path(video_path)
            output_path = video_path.with_suffix(f".{output_format}")

            # 确保输出目录存在
            output_dir = os.path.dirname(str(output_path))
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 确定比特率
            if bitrate is None:
                # 根据格式和采样率推荐比特率
                bitrate = self._get_recommended_bitrate(output_format, sample_rate)

            # 对于opus格式，使用FFmpeg直接转换以确保使用libopus编解码器
            if output_format == "opus":
                ffmpeg_cmd = "ffmpeg"
                if self.ffmpeg_path:
                    ffmpeg_cmd = self.ffmpeg_path

                cmd = [
                    ffmpeg_cmd,
                    "-i", str(video_path),
                    "-vn",  # 不要视频
                    "-c:a", "libopus",  # 使用libopus编解码器
                    "-b:a", bitrate,  # 比特率
                    "-ar", str(sample_rate),  # 采样率
                    "-ac", str(channels),  # 声道数
                    "-y",  # 覆盖现有文件
                    str(output_path)
                ]

                # 打印诊断信息
                print(f"执行命令: {' '.join(cmd)}")

                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=False)

                    # 检查命令是否成功
                    if result.returncode != 0:
                        error_msg = result.stderr.strip()
                        print(f"ffmpeg转换失败: {error_msg}")

                        # 尝试使用不同的编解码器
                        if "libopus" in error_msg:
                            print("尝试使用备用编解码器...")
                            cmd[6] = "opus"  # 尝试使用opus而不是libopus
                            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=False)

                            if result.returncode != 0:
                                # 尝试使用pydub
                                print("转换到wav然后使用pydub...")
                                return self._convert_with_pydub(video_path, output_format, sample_rate, channels, bitrate)
                        else:
                            # 尝试使用pydub
                            print("尝试使用pydub...")
                            return self._convert_with_pydub(video_path, output_format, sample_rate, channels, bitrate)

                    # 检查文件是否存在
                    if not os.path.exists(str(output_path)) or os.path.getsize(str(output_path)) == 0:
                        print("输出文件不存在或大小为0，尝试使用pydub...")
                        return self._convert_with_pydub(video_path, output_format, sample_rate, channels, bitrate)

                    return str(output_path)

                except subprocess.SubprocessError as e:
                    print(f"执行ffmpeg命令失败: {str(e)}")
                    # 尝试使用pydub
                    return self._convert_with_pydub(video_path, output_format, sample_rate, channels, bitrate)
            else:
                # 对于其他格式，使用pydub
                return self._convert_with_pydub(video_path, output_format, sample_rate, channels, bitrate)

        except Exception as e:
            print(f"音频转换失败: {str(e)}")
            raise Exception(f"音频转换失败: {str(e)}") from e

    def _convert_with_pydub(self, video_path, output_format, sample_rate, channels, bitrate):
        """使用pydub进行转换的辅助方法"""
        try:
            print(f"使用pydub转换音频: {video_path}")

            # 计算输出路径
            if isinstance(video_path, Path):
                output_path = video_path.with_suffix(f".{output_format}")
            else:
                output_path = Path(video_path).with_suffix(f".{output_format}")

            # 加载视频中的音频
            try:
                audio = AudioSegment.from_file(str(video_path))
            except Exception as e:
                print(f"pydub加载文件失败: {str(e)}")
                # 尝试先用ffmpeg转成wav
                temp_wav = str(Path(video_path).with_suffix(".temp.wav"))
                ffmpeg_cmd = "ffmpeg" if not self.ffmpeg_path else self.ffmpeg_path

                wav_cmd = [
                    ffmpeg_cmd,
                    "-i", str(video_path),
                    "-vn",  # 不要视频
                    "-acodec", "pcm_s16le",  # 转换为PCM
                    "-ar", str(sample_rate),  # 采样率
                    "-ac", str(channels),  # 声道数
                    "-y",  # 覆盖现有文件
                    temp_wav
                ]

                print(f"尝试先转成wav: {' '.join(wav_cmd)}")
                subprocess.run(wav_cmd, check=True, encoding='utf-8', capture_output=True)

                # 再用pydub加载
                audio = AudioSegment.from_file(temp_wav)

                # 处理完删除临时文件
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)

            # 设置采样率和声道数
            if audio.frame_rate != sample_rate or audio.channels != channels:
                audio = audio.set_frame_rate(sample_rate).set_channels(channels)

            # 确定编解码器参数
            codec_args = {}
            if output_format == "mp3":
                codec_args = {'codec': 'libmp3lame'}
            elif output_format == "aac":
                codec_args = {'codec': 'aac'}
            elif output_format == "flac":
                codec_args = {'codec': 'flac'}
            elif output_format == "opus":
                codec_args = {'codec': 'libopus'}

            # 导出为指定格式
            export_args = {
                'format': output_format,
                **codec_args
            }

            # 添加比特率（如果需要）
            if bitrate:
                export_args['bitrate'] = bitrate

            # 导出
            audio.export(str(output_path), **export_args)

            return str(output_path)

        except Exception as e:
            print(f"pydub转换失败: {str(e)}")
            raise Exception(f"无法使用pydub转换: {str(e)}") from e

    def _get_recommended_bitrate(self, format_name, sample_rate):
        """
        根据格式和采样率获取推荐比特率

        参数:
            format_name (str): 音频格式
            sample_rate (int): 采样率

        返回:
            str: 推荐比特率
        """
        # 基于格式和采样率的推荐比特率（kbps）
        recommendations = {
            "opus": {
                8000: "16k",  # 低品质电话语音
                16000: "24k",  # 良好语音质量，适合语音识别
                24000: "32k",  # 较高语音质量
                48000: "64k"  # 高质量音频
            },
            "mp3": {
                8000: "64k",  # 低品质
                16000: "96k",  # 中等品质
                24000: "128k",  # 良好品质
                44100: "192k",  # 高品质
                48000: "192k"  # 高品质
            },
            "aac": {
                8000: "32k",
                16000: "64k",
                24000: "96k",
                44100: "128k",
                48000: "160k"
            },
            "flac": {
                # FLAC是无损的，不需要指定比特率
                8000: None,
                16000: None,
                24000: None,
                44100: None,
                48000: None
            },
            "ogg": {
                8000: "32k",
                16000: "64k",
                24000: "96k",
                44100: "128k",
                48000: "160k"
            }
        }

        # 获取最接近的采样率
        available_rates = list(recommendations.get(format_name, {}).keys())
        if not available_rates:
            return "128k"  # 默认值

        # 找到最接近的采样率
        closest_rate = min(available_rates, key=lambda x: abs(x - sample_rate))
        rate = recommendations.get(format_name, {}).get(closest_rate)

        # 如果没有推荐值，使用默认值
        if not rate:
            if format_name == "flac":
                return None  # FLAC不需要比特率
            return "128k"

        return rate

    @staticmethod
    def find_ffmpeg():
        """
        尝试在系统中查找ffmpeg可执行文件的路径

        返回:
            str or None: ffmpeg路径或None（如果找不到）
        """
        # Windows上通常的安装位置
        windows_paths = [
            os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'ffmpeg', 'bin', 'ffmpeg.exe')
        ]

        # 首先尝试从PATH中查找
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path

        # 在Windows上尝试常见安装位置
        if os.name == 'nt':
            for path in windows_paths:
                if os.path.isfile(path):
                    return path

        return None