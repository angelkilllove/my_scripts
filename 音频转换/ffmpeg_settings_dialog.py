import sys
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QFileDialog)


class FFmpegSettingsDialog(QDialog):
    """FFmpeg设置对话框，用于设置FFmpeg可执行文件路径"""

    def __init__(self, parent=None, current_path=None):
        super().__init__(parent)
        self.setWindowTitle("FFmpeg设置")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # 创建路径输入区域
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("FFmpeg路径:"))
        self.path_edit = QLineEdit()
        if current_path:
            self.path_edit.setText(current_path)
        path_layout.addWidget(self.path_edit)

        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_ffmpeg)
        path_layout.addWidget(browse_button)

        layout.addLayout(path_layout)

        # 创建提示标签
        info_label = QLabel("请指定FFmpeg可执行文件的路径。如果已在系统PATH中，可以留空。")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 自动检测按钮
        detect_button = QPushButton("自动检测")
        detect_button.clicked.connect(self.auto_detect_ffmpeg)
        layout.addWidget(detect_button)

        # 创建按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def browse_ffmpeg(self):
        """打开文件对话框浏览FFmpeg可执行文件"""
        file_filter = "可执行文件 (*.exe);;所有文件 (*)" if sys.platform == "win32" else "所有文件 (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择FFmpeg可执行文件", "", file_filter)

        if file_path:
            self.path_edit.setText(file_path)
    
    def auto_detect_ffmpeg(self):
        """尝试自动检测FFmpeg路径"""
        # 导入视频转换器类中的查找函数
        try:
            from audio_converter import VideoToAudioConverter
            ffmpeg_path = VideoToAudioConverter.find_ffmpeg()
            
            if ffmpeg_path:
                self.path_edit.setText(ffmpeg_path)
                self.statusBar().showMessage("已成功检测到FFmpeg") if hasattr(self, 'statusBar') else None
            else:
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage("无法自动检测到FFmpeg")
        except Exception as e:
            print(f"自动检测FFmpeg失败: {str(e)}")

    def get_ffmpeg_path(self):
        """获取设置的FFmpeg路径"""
        path = self.path_edit.text().strip()
        return path if path else None
