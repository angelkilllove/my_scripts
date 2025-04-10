import os
from PySide6.QtWidgets import (
    QMessageBox, QFileDialog, QTableWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette

from config_manager import (
    get_api_keys, get_last_used_key, get_last_used_key_name, get_output_format, get_api_service,
    get_last_directory, save_last_directory, save_last_used_key, save_output_format, save_api_service,
    get_conversion_settings
)
from ui_dialogs import ProxySettingsDialog, APIKeyDialog, DependencyCheckerDialog, AboutDialog
from ui_settings_dialog import ConversionSettingsDialog
from ui_components import SUPPORTED_AUDIO_EXTENSIONS


class MethodsMixin:
    """窗口方法混入类"""

    def load_settings(self):
        """加载设置"""
        # 加载API服务
        service = get_api_service()
        if service == "groq":
            self.groq_radio.setChecked(True)
        elif service == "deepgram":
            self.deepgram_radio.setChecked(True)
        else:
            self.groq_radio.setChecked(True)

        # 加载输出格式
        output_format = get_output_format()
        if output_format == "srt":
            self.srt_radio.setChecked(True)
        elif output_format == "text":
            self.text_radio.setChecked(True)
        else:
            self.srt_radio.setChecked(True)

        # 更新按钮状态
        self.update_file_buttons()

        # 加载API密钥
        self.load_api_keys()

    def load_api_keys(self):
        """加载API密钥"""
        # 清空当前列表
        self.api_key_combo.clear()

        # 获取当前服务
        current_service = "groq" if self.groq_radio.isChecked() else "deepgram"

        # 获取密钥
        keys = get_api_keys(current_service)

        if not keys:
            self.api_key_combo.addItem("未配置API密钥", None)
            self.api_key_combo.setEnabled(False)
            return

        self.api_key_combo.setEnabled(True)

        # 获取上次使用的密钥名称
        last_key_name = get_last_used_key_name(current_service)
        last_key_index = 0

        # 添加密钥到下拉列表
        for i, (name, key) in enumerate(keys.items()):
            # 格式化显示
            masked_key = f"{key[:5]}...{key[-4:]}" if len(key) > 10 else key
            display_text = f"{name}: {masked_key}" if name != key else masked_key
            self.api_key_combo.addItem(display_text, key)

            # 如果是上次使用的密钥，记录索引
            if name == last_key_name:
                last_key_index = i

        # 选择上次使用的密钥
        if last_key_name and last_key_index < self.api_key_combo.count():
            self.api_key_combo.setCurrentIndex(last_key_index)

        # 更新开始按钮状态
        self.update_start_button()

    def open_proxy_settings(self):
        """打开代理设置对话框"""
        dialog = ProxySettingsDialog(self)
        # 确保对话框显示在前面并设置模态
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec()

    def open_api_key_manager(self):
        """打开API密钥管理对话框"""
        current_service = "groq" if self.groq_radio.isChecked() else "deepgram"
        dialog = APIKeyDialog(self, current_service)
        # 确保对话框大小足够避免重叠，并设置模态
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setMinimumSize(550, 350)
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec()

        # 对话框关闭后刷新API密钥
        self.load_api_keys()

    def open_conversion_settings(self):
        """打开转换设置对话框"""
        dialog = ConversionSettingsDialog(self)
        # 设置当前服务
        current_service = "groq" if self.groq_radio.isChecked() else "deepgram"
        dialog.set_service(current_service)

        # 连接设置变更信号
        dialog.settings_changed.connect(self.on_conversion_settings_changed)

        # 显示对话框
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec()

    def on_conversion_settings_changed(self):
        """转换设置变更处理"""
        # 如果需要在设置变更后更新UI，可以在这里实现
        self.log("转换设置已更新")

    def check_dependencies(self):
        """检查依赖"""
        dialog = DependencyCheckerDialog(self)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.exec()

    def show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.exec()

    def on_service_changed(self, id):
        """服务类型改变时的处理"""
        service = "groq" if id == 0 else "deepgram"
        save_api_service(service)

        # 重新加载API密钥
        self.load_api_keys()

        # 更新UI状态
        if service == "deepgram":
            self.log("Deepgram API支持正在开发中，可能无法正常工作。")

    def on_format_changed(self, id):
        """输出格式改变时的处理"""
        output_format = "srt" if id == 0 else "text"
        save_output_format(output_format)

    def add_files(self):
        """添加文件"""
        # 获取上次打开的目录
        last_dir = get_last_directory()
        start_dir = last_dir if last_dir and os.path.exists(last_dir) else ""

        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter(f"音频文件 ({' '.join(['*' + ext for ext in SUPPORTED_AUDIO_EXTENSIONS])})")

        # 设置起始目录
        if start_dir:
            file_dialog.setDirectory(start_dir)

        if file_dialog.exec():
            files = file_dialog.selectedFiles()

            # 保存最后使用的目录
            if files:
                last_dir = os.path.dirname(files[0])
                save_last_directory(last_dir)

            self.add_dropped_files(files)

    def add_dropped_files(self, files):
        """添加拖放的文件"""
        for file_path in files:
            # 检查文件是否已在列表中
            found = False
            for path in self.file_list.get_all_file_paths():
                if path == file_path:
                    found = True
                    break

            if not found:
                # 添加文件到表格
                row = self.file_list.add_audio_file(file_path)

                # 选中新添加的行
                self.file_list.selectRow(row)

        # 更新UI状态
        self.update_file_buttons()

    def remove_files(self):
        """删除所选文件"""
        # 获取选中的行索引
        selected_rows = set()
        for item in self.file_list.selectedItems():
            selected_rows.add(item.row())

        # 按照索引从大到小的顺序删除行（避免索引变化）
        for row in sorted(selected_rows, reverse=True):
            self.file_list.removeRow(row)

        # 更新UI状态
        self.update_file_buttons()

    def clear_files(self):
        """清空文件列表"""
        # 删除所有行
        self.file_list.setRowCount(0)

        # 更新UI状态
        self.update_file_buttons()

    def update_file_buttons(self):
        """更新文件操作按钮状态"""
        has_files = self.file_list.rowCount() > 0
        has_selection = len(self.file_list.selectedItems()) > 0

        self.remove_file_btn.setEnabled(has_selection)
        self.clear_files_btn.setEnabled(has_files)
        self.select_all_checkbox.setEnabled(has_files)

        # 检查是否全选 - 计算方式是通过选中项数量和表格的总单元格数量比较
        if has_files and has_selection:
            # 计算选中项的行数
            selected_rows = set()
            for item in self.file_list.selectedItems():
                selected_rows.add(item.row())
            all_selected = len(selected_rows) == self.file_list.rowCount()
        else:
            all_selected = False

        # 更新复选框状态，但避免触发信号
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(all_selected)
        self.select_all_checkbox.blockSignals(False)

        self.update_start_button()

    def toggle_select_all(self, checked):
        """切换全选/取消全选"""
        self.file_list.blockSignals(True)  # 阻止信号以避免触发多次update_file_buttons

        if checked:
            self.file_list.selectAll()
        else:
            self.file_list.clearSelection()

        self.file_list.blockSignals(False)

        # 手动更新按钮状态
        self.update_file_buttons()

    def update_start_button(self):
        """更新开始按钮状态"""
        has_selection = len(self.file_list.selectedItems()) > 0 and len(self.file_list.get_selected_file_paths()) > 0
        has_api_key = self.api_key_combo.isEnabled() and self.api_key_combo.currentData() is not None

        # 如果有选中文件且有API密钥，则启用开始按钮
        self.start_btn.setEnabled(has_selection and has_api_key)

        # 根据文件列表状态更新按钮文本
        if has_selection:
            file_count = len(set(item.row() for item in self.file_list.selectedItems()))
            self.start_btn.setText(f"开始转换 ({file_count}个文件)")
        else:
            self.start_btn.setText("开始转换")

    def _update_file_status(self, file_path, status):
        """更新表格中文件的状态

        这是一个辅助方法，用于在表格中查找并更新文件状态
        """
        # 查找文件所在的行
        for row in range(self.file_list.rowCount()):
            item = self.file_list.item(row, 0)  # 第一列存储文件路径
            if item and item.data(Qt.UserRole) == file_path:
                # 获取文件路径并添加状态信息
                file_path_formatted = file_path.replace("/", "\\")
                status_label = f"{file_path_formatted} ({status})"

                # 更新表格项的显示文本
                item.setText(status_label)
                break