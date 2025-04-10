import os
import asyncio
import traceback
from PySide6.QtCore import QThread, Signal


class ProcessWorker(QThread):
    """处理工作线程"""
    started_file = Signal(str)  # 开始处理某个文件的信号
    finished_file = Signal(str, str)  # 完成处理某个文件的信号，返回输入文件路径和输出文件路径
    error_file = Signal(str, str)  # 某个文件处理错误的信号，返回文件路径和错误信息
    progress = Signal(str, str, int)  # 进度信号，文件名、状态和百分比
    all_completed = Signal()  # 所有文件处理完成的信号

    def __init__(self, audio_files, api_key, service, output_format, language=None, service_settings=None):
        super().__init__()
        self.audio_files = audio_files
        self.api_key = api_key
        self.service = service
        self.output_format = output_format
        self.language = language
        self.service_settings = service_settings or {}
        self.client = None

    def run(self):
        """运行处理任务"""
        # 导入必要的模块 (在线程中导入以避免阻塞主线程)
        try:
            from api_clients import create_client, print_debug
            from config_manager import get_proxy_settings
        except ImportError as e:
            for file in self.audio_files:
                self.error_file.emit(file, f"模块导入错误: {str(e)}")
            return

        try:
            # 获取代理设置
            proxy = get_proxy_settings(self.service)
            print_debug(f"获取代理设置: {proxy}")

            # 创建API客户端
            self.client = create_client(self.service, self.api_key, proxy)
            print_debug(f"已创建客户端: {self.client.__class__.__name__}")

            # 使用异步循环处理所有文件
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 创建任务列表
            tasks = []
            for file_path in self.audio_files:
                tasks.append(self.process_file(self.client, file_path))

            # 执行任务
            print_debug(f"开始执行 {len(tasks)} 个任务")
            loop.run_until_complete(asyncio.gather(*tasks))

            # 完成后安全地关闭事件循环
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

            # 执行清理
            print_debug("任务执行完毕")

            # 发出完成信号
            self.all_completed.emit()

        except Exception as e:
            # 全局错误处理
            print_debug(f"执行过程中发生错误: {e}")
            traceback.print_exc()
            for file_path in self.audio_files:
                self.error_file.emit(file_path, f"初始化错误: {str(e)}")
        finally:
            # 在线程结束时关闭客户端
            if self.client:
                print_debug("线程结束，关闭客户端")
                self.client.close()

    async def process_file(self, client, file_path):
        """处理单个文件"""
        try:
            # 发出开始信号
            self.started_file.emit(file_path)

            # 定义进度回调
            file_name = os.path.basename(file_path)

            def progress_callback(stage, percentage):
                self.progress.emit(file_path, stage, percentage)

            # 准备转写选项
            transcribe_options = {
                "file_path": file_path,
                "output_format": self.output_format,
                "language": self.language,
                "progress_callback": progress_callback
            }

            # 添加服务特定选项
            if self.service == "groq":
                # 为Groq服务添加选项
                for key in ['model', 'timestamps', 'temperature', 'translate', 'max_line_count', 'max_line_width']:
                    if key in self.service_settings:
                        transcribe_options[key] = self.service_settings[key]

            elif self.service == "deepgram":
                # 为Deepgram服务添加选项
                for key, value in self.service_settings.items():
                    if key in ['model', 'version', 'smart_format', 'punctuate', 'diarize',
                               'detect_language', 'multichannel', 'keywords', 'tier',
                               'sample_rate', 'timestamps', 'confidence']:
                        transcribe_options[key] = value

            # 执行转写
            output_path = await client.transcribe(**transcribe_options)

            # 发出完成信号
            self.finished_file.emit(file_path, output_path)

        except Exception as e:
            # 发出错误信号
            error_msg = str(e)
            traceback.print_exc()
            self.error_file.emit(file_path, error_msg)