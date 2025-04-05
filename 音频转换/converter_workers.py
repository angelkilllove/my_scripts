import os
from pathlib import Path
import shutil
from PySide6.QtCore import QObject, Signal, QRunnable


class WorkerSignals(QObject):
    """
    定义工作线程的信号
    """
    started = Signal(int)  # 参数: file_index
    progress = Signal(int, int)  # 参数: file_index, progress_percent
    finished = Signal(int, bool, str)  # 参数: file_index, success, output_path/error_message
    batch_completed = Signal()  # 所有任务完成


class AudioInfoWorker(QRunnable):
    """获取音频信息的工作线程"""

    class Signals(QObject):
        finished = Signal(int, bool, object)  # idx, success, result/error

    def __init__(self, idx, file_path, ffmpeg_path):
        super().__init__()
        self.idx = idx
        self.file_path = file_path
        self.ffmpeg_path = ffmpeg_path
        self.signals = self.Signals()

    def run(self):
        try:
            from audio_converter import VideoToAudioConverter
            converter = VideoToAudioConverter(self.ffmpeg_path)
            audio_info = converter.get_audio_info(self.file_path)
            self.signals.finished.emit(self.idx, True, audio_info)
        except Exception as e:
            print(f"获取音频信息失败: {str(e)}")
            self.signals.finished.emit(self.idx, False, str(e))


class ConversionWorker(QRunnable):
    """
    处理转换操作的工作线程
    """

    def __init__(self, file_index: int, input_path: str, output_format: str,
                 segment_duration: float, sample_rate: int = None, channels: int = None,
                 bitrate: str = None, ffmpeg_path: str = None, split_settings: dict = None,
                 output_path: str = None):
        super().__init__()
        self.file_index = file_index
        self.input_path = input_path
        self.output_format = output_format
        self.segment_duration = segment_duration  # 分钟
        self.sample_rate = sample_rate
        self.channels = channels
        self.bitrate = bitrate
        self.ffmpeg_path = ffmpeg_path
        self.split_settings = split_settings or {}
        self.output_path = output_path  # 指定输出文件路径
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.started.emit(self.file_index)

            # 导入音频转换器
            from audio_converter import VideoToAudioConverter
            
            # 创建转换器实例
            converter = VideoToAudioConverter(self.ffmpeg_path)

            # 如果不需要分段
            if self.segment_duration <= 0:
                # 根据模式处理
                if self.output_format == "auto":
                    # 自动检测模式 - 直接提取而不修改参数
                    if self.output_path:
                        # 使用指定的输出路径
                        output_ext = os.path.splitext(self.output_path)[1][1:]
                        output_path = converter.extract_audio(self.input_path, output_format=output_ext)
                        
                        # 如果输出路径不是期望的路径，移动文件
                        if output_path != self.output_path and os.path.exists(output_path):
                            # 确保目标目录存在
                            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
                            
                            # 移动文件
                            shutil.copy2(output_path, self.output_path)
                            os.remove(output_path)
                            output_path = self.output_path
                    else:
                        output_path = converter.extract_audio(self.input_path)
                else:
                    # 转换模式 - 使用设置的参数
                    if self.output_path:
                        # 先转换到临时文件，然后移动到指定位置
                        output_path = converter.convert(
                            self.input_path,
                            output_format=self.output_format,
                            sample_rate=self.sample_rate,
                            channels=self.channels,
                            bitrate=self.bitrate
                        )
                        
                        # 如果输出路径不是期望的路径，移动文件
                        if output_path != self.output_path and os.path.exists(output_path):
                            # 确保目标目录存在
                            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
                            
                            # 移动文件
                            shutil.copy2(output_path, self.output_path)
                            os.remove(output_path)
                            output_path = self.output_path
                    else:
                        output_path = converter.convert(
                            self.input_path,
                            output_format=self.output_format,
                            sample_rate=self.sample_rate,
                            channels=self.channels,
                            bitrate=self.bitrate
                        )

                self.signals.progress.emit(self.file_index, 100)
                self.signals.finished.emit(self.file_index, True, output_path)
            else:
                # 需要分段转换
                try:
                    from audio_splitter import AudioSplitter
                    splitter = AudioSplitter(converter)
                except ImportError:
                    # 如果没有audio_splitter模块，使用简单的分段
                    self.signals.finished.emit(self.file_index, False, "未找到音频分段模块，请确保audio_splitter.py存在")
                    return

                # 设置分段时长 (从分钟转为秒)
                segment_duration_sec = int(self.segment_duration * 60)
                
                # 处理输出路径
                # 如果指定了输出路径，确保目录存在
                if self.output_path:
                    os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
                
                # 根据模式处理
                if self.output_format == "auto":
                    # 自动检测模式 - 分段但不转换格式
                    if self.split_settings.get('use_silence_detection', False):
                        result = splitter.split_audio_at_silence(
                            self.input_path,
                            "auto",  # 使用原始格式
                            segment_duration_sec,
                            max_offset=self.split_settings.get('max_offset', 60),
                            silence_threshold=self.split_settings.get('silence_threshold', -40),
                            silence_duration=self.split_settings.get('silence_duration', 0.5),
                            progress_callback=lambda p: self.signals.progress.emit(self.file_index, p)
                        )
                    else:
                        result = splitter.split_audio(
                            self.input_path,
                            "auto",  # 使用原始格式
                            segment_duration_sec,
                            progress_callback=lambda p: self.signals.progress.emit(self.file_index, p)
                        )
                else:
                    # 正常转换模式
                    if self.split_settings.get('use_silence_detection', False):
                        result = splitter.split_audio_at_silence(
                            self.input_path,
                            self.output_format,
                            segment_duration_sec,
                            max_offset=self.split_settings.get('max_offset', 60),
                            silence_threshold=self.split_settings.get('silence_threshold', -40),
                            silence_duration=self.split_settings.get('silence_duration', 0.5),
                            sample_rate=self.sample_rate,
                            channels=self.channels,
                            bitrate=self.bitrate,
                            progress_callback=lambda p: self.signals.progress.emit(self.file_index, p)
                        )
                    else:
                        result = splitter.split_audio(
                            self.input_path,
                            self.output_format,
                            segment_duration_sec,
                            sample_rate=self.sample_rate,
                            channels=self.channels,
                            bitrate=self.bitrate,
                            progress_callback=lambda p: self.signals.progress.emit(self.file_index, p)
                        )

                if isinstance(result, list):
                    # 分段成功，返回信息
                    self.signals.finished.emit(self.file_index, True, f"成功创建{len(result)}个分段文件")
                else:
                    # 分段失败
                    self.signals.finished.emit(self.file_index, False, str(result))

        except Exception as e:
            self.signals.finished.emit(self.file_index, False, str(e))
