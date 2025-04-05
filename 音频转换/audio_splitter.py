import os
import subprocess
import tempfile
import math
from pathlib import Path
from typing import List, Union, Callable, Dict, Optional, Tuple


class AudioSplitter:
    """
    音频分割器类 - 用于将长音频文件分割成多个较短的片段
    支持按时长均匀分割
    """

    def __init__(self, converter):
        """
        初始化音频分割器

        参数:
            converter: VideoToAudioConverter实例，用于音频处理
        """
        self.converter = converter

    def split_audio(self, input_path: str, output_format: str = None,
                    segment_duration: int = 1800, sample_rate: int = 16000,
                    channels: int = 1, bitrate: str = None,
                    progress_callback: Callable[[int], None] = None) -> Union[List[str], Exception]:
        """
        将音频文件按指定时长分割

        参数:
            input_path (str): 输入音频或视频文件路径
            output_format (str): 输出音频格式，如为None则保持原格式
            segment_duration (int): 每段的时长(秒)，默认30分钟
            progress_callback (callable): 进度回调函数，参数为进度百分比(0-100)

        返回:
            List[str] 或 Exception: 成功时返回分段文件路径列表，失败时返回异常
        """
        try:
            # 确保文件存在
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"找不到文件: {input_path}")

            # 获取输入文件的音频信息
            audio_info = self.converter.get_audio_info(input_path)
            total_duration = audio_info.get('duration', 0)

            if total_duration <= 0:
                raise ValueError(f"无法获取音频时长或音频时长为0: {input_path}")

            # 如果时长不超过单段时长，无需分割
            if total_duration <= segment_duration:
                # 直接转换并返回
                if output_format == "auto":
                    output_path = self.converter.extract_audio(input_path)
                else:
                    output_path = self.converter.convert(input_path, output_format=output_format)

                if progress_callback:
                    progress_callback(100)

                return [output_path]

            # 计算所需的段数
            num_segments = math.ceil(total_duration / segment_duration)

            # 防止段数过多
            if num_segments > 9:
                num_segments = 9
                segment_duration = math.ceil(total_duration / num_segments)

            # 准备输出路径
            input_path_obj = Path(input_path)
            output_dir = input_path_obj.parent
            base_name = input_path_obj.stem

            # 确定输出格式
            if output_format == "auto":
                # 获取原始音频格式
                codec = audio_info.get('codec', 'opus')
                # 映射到适当的文件扩展名
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
            else:
                ext = output_format

            # 确定ffmpeg命令
            ffmpeg_cmd = "ffmpeg"
            if self.converter.ffmpeg_path:
                ffmpeg_cmd = self.converter.ffmpeg_path

            # 存储输出文件路径
            output_files = []

            # 对每个段进行处理
            for i in range(num_segments):
                # 计算当前段的起始时间和持续时间
                start_time = i * segment_duration
                current_segment_duration = min(segment_duration, total_duration - start_time)

                # 构建输出文件名
                output_filename = f"{base_name}_part{i + 1}.{ext}"
                output_path = os.path.join(output_dir, output_filename)

                # 添加到输出文件列表
                output_files.append(output_path)

                # 使用ffmpeg进行分段提取
                cmd = [
                    ffmpeg_cmd,
                    "-i", input_path,
                    "-ss", str(start_time),  # 起始时间
                    "-t", str(current_segment_duration),  # 持续时间
                    "-vn",  # 不要视频
                    "-y"  # 覆盖现有文件
                ]

                # 添加输出格式参数
                if output_format == "auto":
                    # 直接提取
                    cmd.extend(["-acodec", "copy"])
                else:
                    # 指定格式转换
                    if ext == "opus":
                        cmd.extend(["-c:a", "libopus"])
                    elif ext == "mp3":
                        cmd.extend(["-c:a", "libmp3lame"])
                    elif ext == "aac":
                        cmd.extend(["-c:a", "aac"])
                    elif ext == "flac":
                        cmd.extend(["-c:a", "flac"])
                    elif ext == "wav":
                        cmd.extend(["-c:a", "pcm_s16le"])

                    # 添加采样率和声道
                    cmd.extend(["-ar", str(sample_rate)])
                    cmd.extend(["-ac", str(channels)])

                    # 添加比特率（如果有）
                    if bitrate and output_format != "auto" and ext != "wav" and ext != "flac":
                        cmd.extend(["-b:a", bitrate])

                # 添加输出路径
                cmd.append(output_path)

                # 执行命令
                print(f"执行分段命令: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=False)

                # 检查命令是否成功
                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    raise RuntimeError(f"分段失败: {error_msg}")

                # 更新进度
                if progress_callback:
                    progress = int((i + 1) * 100 / num_segments)
                    progress_callback(progress)

            return output_files

        except Exception as e:
            print(f"分段失败: {str(e)}")
            return e

    def split_audio_at_silence(self, input_path: str, output_format: str = None,
                               segment_duration: int = 1800, max_offset: int = 60,
                               silence_threshold: float = -50, silence_duration: float = 0.5,
                               sample_rate: int = 16000, channels: int = 1, bitrate: str = None,
                               progress_callback: Callable[[int], None] = None) -> Union[List[str], Exception]:
        """
        将音频文件在静音处分割

        参数:
            input_path (str): 输入音频或视频文件路径
            output_format (str): 输出音频格式，如为None则保持原格式
            segment_duration (int): 理想的每段时长(秒)
            max_offset (int): 允许的最大偏移量(秒)
            silence_threshold (float): 静音阈值(dB)，默认-50dB
            silence_duration (float): 静音持续时间(秒)，默认0.5秒
            progress_callback (callable): 进度回调函数，参数为进度百分比(0-100)

        返回:
            List[str] 或 Exception: 成功时返回分段文件路径列表，失败时返回异常
        """
        try:
            # 确保文件存在
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"找不到文件: {input_path}")

            # 获取输入文件的音频信息
            audio_info = self.converter.get_audio_info(input_path)
            total_duration = audio_info.get('duration', 0)

            if total_duration <= 0:
                raise ValueError(f"无法获取音频时长或音频时长为0: {input_path}")

            # 如果时长不超过单段时长，无需分割
            if total_duration <= segment_duration:
                # 直接转换并返回
                if output_format == "auto":
                    output_path = self.converter.extract_audio(input_path)
                else:
                    output_path = self.converter.convert(input_path, output_format=output_format)

                if progress_callback:
                    progress_callback(100)

                return [output_path]

            # 检测静音点
            silence_points = self._detect_silence_points(
                input_path,
                segment_duration,
                max_offset,
                silence_threshold,
                silence_duration
            )

            if not silence_points:
                raise ValueError("找不到合适的静音点进行分割")

            # 准备输出路径
            input_path_obj = Path(input_path)
            output_dir = input_path_obj.parent
            base_name = input_path_obj.stem

            # 确定输出格式
            if output_format == "auto":
                # 获取原始音频格式
                codec = audio_info.get('codec', 'opus')
                # 映射到适当的文件扩展名
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
            else:
                ext = output_format

            # 确定ffmpeg命令
            ffmpeg_cmd = "ffmpeg"
            if self.converter.ffmpeg_path:
                ffmpeg_cmd = self.converter.ffmpeg_path

            # 存储输出文件路径
            output_files = []

            # 将静音点转换为分段起始时间列表
            start_times = [0] + [point for point in silence_points]

            # 对每个段进行处理
            for i in range(len(start_times)):
                # 计算当前段的起始时间和持续时间
                start_time = start_times[i]

                # 如果是最后一段，使用总时长作为结束时间
                if i == len(start_times) - 1:
                    end_time = total_duration
                else:
                    end_time = start_times[i + 1]

                current_segment_duration = end_time - start_time

                # 构建输出文件名
                output_filename = f"{base_name}_part{i + 1}.{ext}"
                output_path = os.path.join(output_dir, output_filename)

                # 添加到输出文件列表
                output_files.append(output_path)

                # 使用ffmpeg进行分段提取
                cmd = [
                    ffmpeg_cmd,
                    "-i", input_path,
                    "-ss", str(start_time),  # 起始时间
                    "-t", str(current_segment_duration),  # 持续时间
                    "-vn",  # 不要视频
                    "-y"  # 覆盖现有文件
                ]

                # 添加输出格式参数
                if output_format == "auto":
                    # 直接提取
                    cmd.extend(["-acodec", "copy"])
                else:
                    # 指定格式转换
                    if ext == "opus":
                        cmd.extend(["-c:a", "libopus"])
                    elif ext == "mp3":
                        cmd.extend(["-c:a", "libmp3lame"])
                    elif ext == "aac":
                        cmd.extend(["-c:a", "aac"])
                    elif ext == "flac":
                        cmd.extend(["-c:a", "flac"])
                    elif ext == "wav":
                        cmd.extend(["-c:a", "pcm_s16le"])

                    # 添加采样率和声道
                    cmd.extend(["-ar", str(sample_rate)])
                    cmd.extend(["-ac", str(channels)])

                    # 添加比特率（如果有）
                    if bitrate and output_format != "auto" and ext != "wav" and ext != "flac":
                        cmd.extend(["-b:a", bitrate])

                # 添加输出路径
                cmd.append(output_path)

                # 执行命令
                print(f"执行分段命令: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=False)

                # 检查命令是否成功
                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    raise RuntimeError(f"分段失败: {error_msg}")

                # 更新进度
                if progress_callback:
                    progress = int((i + 1) * 100 / len(start_times))
                    progress_callback(progress)

            return output_files

        except Exception as e:
            print(f"分段失败: {str(e)}")
            return e

    def _detect_silence_points(self, input_path: str, segment_duration: int, max_offset: int,
                               silence_threshold: float, silence_duration: float) -> List[float]:
        """
        使用ffmpeg的silencedetect滤镜检测静音点

        参数:
            input_path (str): 输入音频或视频文件路径
            segment_duration (int): 理想的每段时长(秒)
            max_offset (int): 允许的最大偏移量(秒)
            silence_threshold (float): 静音阈值(dB)
            silence_duration (float): 静音持续时间(秒)

        返回:
            List[float]: 静音点列表(秒)
        """
        # 获取音频信息
        audio_info = self.converter.get_audio_info(input_path)
        total_duration = audio_info.get('duration', 0)

        # 计算段数
        num_segments = math.ceil(total_duration / segment_duration)

        if num_segments <= 1:
            return []

        # 限制段数
        if num_segments > 9:
            num_segments = 9
            segment_duration = math.ceil(total_duration / num_segments)

        # 确定ffmpeg命令
        ffmpeg_cmd = "ffmpeg"
        if self.converter.ffmpeg_path:
            ffmpeg_cmd = self.converter.ffmpeg_path

        # 构建命令 - 使用silencedetect滤镜检测静音
        cmd = [
            ffmpeg_cmd,
            "-i", input_path,
            "-af", f"silencedetect=noise={silence_threshold}dB:d={silence_duration}",
            "-f", "null",
            "-"
        ]

        # 执行命令
        print(f"执行静音检测命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=False)

        # 检查命令是否成功
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            raise RuntimeError(f"静音检测失败: {error_msg}")

        # 解析输出，获取静音区间
        stderr_output = result.stderr
        silence_intervals = []

        for line in stderr_output.split('\n'):
            if "silence_start" in line:
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        start_time = float(parts[-1].strip())
                        silence_intervals.append((start_time, None))
                    except ValueError:
                        pass
            elif "silence_end" in line and silence_intervals and silence_intervals[-1][1] is None:
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        end_time = float(parts[-1].strip().split('|')[0])
                        silence_intervals[-1] = (silence_intervals[-1][0], end_time)
                    except ValueError:
                        pass

        # 去除不完整的区间
        silence_intervals = [interval for interval in silence_intervals if interval[1] is not None]

        # 计算理想的切割点
        ideal_cut_points = []
        for i in range(1, num_segments):
            ideal_cut_points.append(i * segment_duration)

        # 为每个理想切割点找到最近的静音中点
        actual_cut_points = []

        for ideal_point in ideal_cut_points:
            best_point = None
            min_distance = float('inf')

            for start, end in silence_intervals:
                # 使用静音区间的中点
                silence_midpoint = (start + end) / 2

                # 只考虑在允许偏移范围内的静音点
                if abs(silence_midpoint - ideal_point) <= max_offset:
                    distance = abs(silence_midpoint - ideal_point)
                    if distance < min_distance:
                        min_distance = distance
                        best_point = silence_midpoint

            if best_point is not None:
                # 尝试使用整数秒
                best_point = round(best_point)
                actual_cut_points.append(best_point)
            else:
                # 如果找不到合适的静音点，使用理想切割点
                print(f"警告: 在{ideal_point}秒附近找不到合适的静音点")
                actual_cut_points.append(ideal_point)

        return actual_cut_points