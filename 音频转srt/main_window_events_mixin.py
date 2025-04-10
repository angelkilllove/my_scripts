import os
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from ui_components import SUPPORTED_AUDIO_EXTENSIONS


class EventsMixin:
    """窗口事件处理混入类"""

    def closeEvent(self, event):
        """关闭窗口事件处理"""
        # 检查是否有正在进行的任务
        if self.process_worker and self.process_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "确认退出",
                "当前有任务正在处理中，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 终止工作线程
                self.process_worker.terminate()
                self.process_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def dragEnterEvent(self, event):
        """拖拽进入事件处理"""
        # 改进拖放处理逻辑
        if event.mimeData().hasUrls():
            # 检查是否有支持的音频文件
            has_valid_file = False
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):  # 首先确保是文件
                    file_ext = os.path.splitext(file_path)[1].lower()
                    if file_ext in SUPPORTED_AUDIO_EXTENSIONS:
                        has_valid_file = True
                        break

            if has_valid_file:
                event.accept()  # 显式接受事件
                return

        event.ignore()  # 显式拒绝事件

    def dropEvent(self, event):
        """拖拽释放事件处理"""
        # 改进拖放处理逻辑
        if event.mimeData().hasUrls():
            # 获取拖放的文件
            urls = event.mimeData().urls()
            files = []

            for url in urls:
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):  # 首先确保是文件
                    file_ext = os.path.splitext(file_path)[1].lower()
                    # 只处理支持的音频文件
                    if file_ext in SUPPORTED_AUDIO_EXTENSIONS:
                        files.append(file_path)

            if files:
                self.add_dropped_files(files)
                event.accept()  # 显式接受事件
                return

        event.ignore()  # 显式拒绝事件

    def keyPressEvent(self, event):
        """键盘事件处理"""
        # 删除键删除所选文件
        if event.key() == Qt.Key_Delete and self.file_list.hasFocus():
            self.remove_files()
        # Ctrl+A全选
        elif event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier and self.file_list.hasFocus():
            self.file_list.selectAll()
            self.select_all_checkbox.setChecked(True)
        else:
            super().keyPressEvent(event)