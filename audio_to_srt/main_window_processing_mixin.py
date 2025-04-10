import os
from PySide6.QtWidgets import (
    QMessageBox, QTableWidgetItem
)
from PySide6.QtCore import Qt

from config_manager import (
    save_last_used_key, get_proxy_settings, get_conversion_settings
)
from worker_threads import ProcessWorker
from ui_components import SUPPORTED_AUDIO_EXTENSIONS


class ProcessingMixin:
    """处理相关功能混入类"""

    def start_processing(self):
        """开始处理"""
        # 获取选中的文件
        selected_files = self.file_list.get_selected_file_paths()

        if not selected_files:
            QMessageBox.warning(self, "错误", "请选择要处理的音频文件")
            return

        # 获取当前服务
        service = "groq" if self.groq_radio.isChecked() else "deepgram"

        # 获取API密钥
        api_key = self.api_key_combo.currentData()
        if not api_key:
            QMessageBox.warning(self, "错误", "请先添加API密钥")
            # 打开API密钥管理对话框
            self.open_api_key_manager()
            return

        # 获取输出格式
        output_format = "srt" if self.srt_radio.isChecked() else "text"

        # 获取语言设置
        language = self.lang_combo.currentData()

        # 获取高级转换设置
        conversion_settings = get_conversion_settings()
        service_settings = conversion_settings.get(service, {})

        # 保存最后使用的API密钥
        save_last_used_key(api_key, service)

        # 禁用UI
        self.set_ui_enabled(False)

        # 清空进度状态
        self.file_progress = {}
        self.progress_bar.setValue(0)

        # 获取代理设置
        proxy = get_proxy_settings(service)

        # 创建和启动工作线程
        self.process_worker = ProcessWorker(
            selected_files,
            api_key,
            service,
            output_format,
            language,
            service_settings
        )

        # 连接信号
        self.process_worker.started_file.connect(self.on_file_started)
        self.process_worker.finished_file.connect(self.on_file_finished)
        self.process_worker.error_file.connect(self.on_file_error)
        self.process_worker.progress.connect(self.on_file_progress)
        self.process_worker.all_completed.connect(self.on_all_completed)

        # 启动线程
        self.process_worker.start()

        # 记录日志
        self.log(f"开始处理 {len(selected_files)} 个文件...")
        self.log(f"使用服务: {service.capitalize()}")
        self.log(f"输出格式: {output_format.upper()}")

        # 记录更多设置信息
        if service == "groq":
            self.log(f"使用模型: {service_settings.get('model', 'whisper-large-v3')}")
            if service_settings.get('translate', False):
                self.log("启用翻译: 是")
        elif service == "deepgram":
            self.log(f"使用模型: {service_settings.get('model', 'nova-2')}")
            if service_settings.get('diarize', False):
                self.log("启用说话人分离: 是")

        if language:
            self.log(f"指定语言: {language}")
        if proxy:
            self.log(f"使用代理: {proxy}")

        self.status_bar.showMessage("处理中...")

    def set_ui_enabled(self, enabled):
        """设置UI元素启用状态"""
        # 服务选择
        self.groq_radio.setEnabled(enabled)
        self.deepgram_radio.setEnabled(enabled)
        self.api_key_combo.setEnabled(enabled)
        self.api_key_manage_btn.setEnabled(enabled)

        # 格式选择
        self.srt_radio.setEnabled(enabled)
        self.text_radio.setEnabled(enabled)

        # 语言
        self.lang_combo.setEnabled(enabled)

        # 高级设置
        self.conversion_settings_btn.setEnabled(enabled)

        # 文件操作
        self.add_file_btn.setEnabled(enabled)
        self.remove_file_btn.setEnabled(enabled and self.file_list.selectedItems())
        self.clear_files_btn.setEnabled(enabled and self.file_list.rowCount() > 0)
        self.select_all_checkbox.setEnabled(enabled and self.file_list.rowCount() > 0)

        # 开始按钮
        self.start_btn.setEnabled(enabled and self.file_list.selectedItems())

        # 代理按钮
        self.proxy_btn.setEnabled(enabled)

    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_file_started(self, file_path):
        """文件开始处理"""
        # 使用Windows路径格式
        file_path_formatted = file_path.replace("/", "\\")
        self.log(f"开始处理: {file_path_formatted}")

        # 查找并更新表格项
        self._update_file_status(file_path, "处理中...")

    def on_file_finished(self, file_path, output_path):
        """文件处理完成"""
        # 使用Windows路径格式
        file_path_formatted = file_path.replace("/", "\\")
        output_path_formatted = output_path.replace("/", "\\")

        self.log(f"处理完成: {file_path_formatted} -> {output_path_formatted}")

        # 查找并更新表格项
        self._update_file_status(file_path, "已完成")

        # 更新进度条
        self.update_overall_progress()

    def on_file_error(self, file_path, error_message):
        """文件处理错误"""
        # 使用Windows路径格式
        file_path_formatted = file_path.replace("/", "\\")

        self.log(f"处理失败: {file_path_formatted} - {error_message}")

        # 查找并更新表格项
        self._update_file_status(file_path, "失败")

        # 更新进度条
        self.update_overall_progress()

    def on_file_progress(self, file_path, stage, percentage):
        """文件处理进度更新"""
        # 更新文件进度
        self.file_progress[file_path] = percentage

        # 查找并更新表格项
        self._update_file_status(file_path, f"{stage} {percentage}%")

        # 更新总进度条
        self.update_overall_progress()

        # 更新进度条状态文本
        self.progress_bar.setStatus(stage)

    def _update_file_status(self, file_path, status):
        """更新表格中文件的状态

        这是一个新增的辅助方法，用于在表格中查找并更新文件状态
        """
        # 查找文件所在的行
        for row in range(self.file_list.rowCount()):
            item = self.file_list.item(row, 0)  # 第一列存储文件名
            if item and item.data(Qt.UserRole) == file_path:
                # 文件名加上状态信息
                file_name = os.path.basename(file_path)
                status_label = f"{file_name} ({status})"

                # 更新表格项的显示文本
                item.setText(status_label)
                break

    def update_overall_progress(self):
        """更新总体进度条"""
        if not self.file_progress:
            self.progress_bar.setValue(0)
            return

        # 获取正在处理的文件数量
        processing_files = len(self.file_progress)
        if processing_files == 0:
            self.progress_bar.setValue(0)
            return

        # 计算总进度
        total_progress = sum(self.file_progress.values())
        avg_progress = total_progress / processing_files

        # 更新进度条
        self.progress_bar.setValue(int(avg_progress))

    def on_all_completed(self):
        """所有文件处理完成"""
        self.log("所有文件处理完成!")
        self.status_bar.showMessage("处理完成")

        # 启用UI
        self.set_ui_enabled(True)

        # 清理
        self.process_worker = None