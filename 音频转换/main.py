import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog,
                               QMessageBox, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QComboBox, QSpinBox, QCheckBox, QPushButton,
                               QGroupBox, QRadioButton, QDialog, QLineEdit, QGridLayout)
from PySide6.QtCore import Qt, QMimeData, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QClipboard, QIcon

# 导入自定义模块
from audio_converter import VideoToAudioConverter
from audio_processor import AudioProcessor

# 常量定义
FORMATS = ["opus", "mp3", "wav", "aac", "flac", "ogg"]
SAMPLE_RATES = [8000, 16000, 22050, 24000, 44100, 48000]
DEFAULT_SAMPLE_RATE = 16000  # 适合语音识别
BITRATES = {
    "opus": ["16k", "24k", "32k", "48k", "64k", "96k", "128k"],
    "mp3": ["64k", "96k", "128k", "160k", "192k", "256k", "320k"],
    "wav": [],  # WAV不需要比特率
    "aac": ["32k", "64k", "96k", "128k", "160k", "192k", "256k"],
    "flac": [],  # FLAC是无损的，不需要比特率
    "ogg": ["32k", "64k", "96k", "128k", "160k", "192k", "256k"]
}


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

    def get_ffmpeg_path(self):
        """获取设置的FFmpeg路径"""
        path = self.path_edit.text().strip()
        return path if path else None


class AudioInfoDialog(QDialog):
    """显示音频信息的对话框"""

    def __init__(self, parent=None, audio_info=None):
        super().__init__(parent)
        self.setWindowTitle("音频信息")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # 添加音频信息网格
        grid_layout = QGridLayout()

        if audio_info:
            # 格式化比特率显示
            bit_rate_str = f"{int(audio_info.get('bit_rate', 0) / 1000)} kbps"
            if audio_info.get('channels', 0) > 1:
                bit_rate_str += f" ({int(audio_info.get('bit_rate', 0) / audio_info.get('channels', 1) / 1000)} kbps/声道)"

            # 格式化声道信息
            channels_str = audio_info.get("channels_description",
                                          "单声道" if audio_info.get('channels', 0) == 1 else
                                          f"{audio_info.get('channels', 0)}声道")

            labels = [
                ("音频编解码器:", audio_info.get("codec", "未知")),
                ("声道:", channels_str),
                ("采样率:", f"{audio_info.get('sample_rate', 0)} Hz"),
                ("音频比特率:", bit_rate_str),
                ("时长:", f"{audio_info.get('duration', 0):.2f} 秒"),
                ("视频文件大小:", f"{audio_info.get('video_file_size_mb', 0):.2f} MB"),
                ("估计音频大小:", f"{audio_info.get('estimated_size_mb', 0):.2f} MB"),
                ("音频占比:",
                 f"{(audio_info.get('estimated_size_mb', 0) / audio_info.get('video_file_size_mb', 1) * 100) if audio_info.get('video_file_size_mb', 0) > 0 else 0:.1f}%"),
            ]

            for row, (label, value) in enumerate(labels):
                grid_layout.addWidget(QLabel(label), row, 0)
                grid_layout.addWidget(QLabel(value), row, 1)
        else:
            grid_layout.addWidget(QLabel("无法获取音频信息"), 0, 0, 1, 2)

        layout.addLayout(grid_layout)

        # 添加音频提取建议
        if audio_info and audio_info.get("estimated_size_mb", 0) > 0:
            suggestion_label = QLabel()
            audio_size_ratio = audio_info.get("estimated_size_mb", 0) / audio_info.get("video_file_size_mb", 1) if audio_info.get("video_file_size_mb", 0) > 0 else 0

            if audio_size_ratio < 0.1:
                suggestion_label.setText("建议: 音频占视频比例较小，提取后可大幅节省空间。")
            elif audio_size_ratio < 0.3:
                suggestion_label.setText("建议: 音频占视频比例适中，提取后有一定空间节省。")
            else:
                suggestion_label.setText("建议: 音频占视频比例较大，视频可能主要是音频内容。")

            suggestion_label.setStyleSheet("color: blue;")
            layout.addWidget(suggestion_label)

        # 添加按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频转音频工具")
        self.setMinimumSize(600, 500)

        # 检查FFmpeg
        self.ffmpeg_path = VideoToAudioConverter.find_ffmpeg()

        self.setup_ui()

    def setup_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建拖放区域
        self.drop_area = DropArea(self)
        main_layout.addWidget(self.drop_area)

        # 创建转换选项组
        conversion_group = QGroupBox("转换选项")
        conversion_layout = QVBoxLayout()

        # 转换模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("转换模式:"))
        self.extract_radio = QRadioButton("直接提取音频")
        self.extract_radio.setChecked(True)
        self.extract_radio.toggled.connect(self.update_ui_state)
        self.convert_radio = QRadioButton("转换为新格式")
        mode_layout.addWidget(self.extract_radio)
        mode_layout.addWidget(self.convert_radio)
        conversion_layout.addLayout(mode_layout)

        # 创建格式选择区域
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(FORMATS)
        self.format_combo.setCurrentText("opus")  # 默认opus，最适合语音识别
        self.format_combo.currentTextChanged.connect(self.update_bitrate_options)
        format_layout.addWidget(self.format_combo)
        conversion_layout.addLayout(format_layout)

        # 创建比特率选择区域
        bitrate_layout = QHBoxLayout()
        bitrate_layout.addWidget(QLabel("比特率:"))
        self.bitrate_combo = QComboBox()
        # 初始化比特率选项
        self.update_bitrate_options("opus")
        bitrate_layout.addWidget(self.bitrate_combo)
        conversion_layout.addLayout(bitrate_layout)

        # 创建采样率选择区域
        sample_rate_layout = QHBoxLayout()
        sample_rate_layout.addWidget(QLabel("采样率(Hz):"))
        self.sample_rate_combo = QComboBox()
        for rate in SAMPLE_RATES:
            self.sample_rate_combo.addItem(str(rate))
        self.sample_rate_combo.setCurrentText(str(DEFAULT_SAMPLE_RATE))  # 默认16kHz，适合语音识别
        sample_rate_layout.addWidget(self.sample_rate_combo)
        conversion_layout.addLayout(sample_rate_layout)

        # 创建声道选择区域
        channels_layout = QHBoxLayout()
        channels_layout.addWidget(QLabel("声道数:"))
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["1 (单声道)", "2 (立体声)"])
        self.channels_combo.setCurrentIndex(0)  # 默认单声道，适合语音识别
        channels_layout.addWidget(self.channels_combo)
        conversion_layout.addLayout(channels_layout)

        conversion_group.setLayout(conversion_layout)
        main_layout.addWidget(conversion_group)

        # 创建音频处理选项区域
        processing_group = QGroupBox("音频预处理选项")
        processing_layout = QVBoxLayout()

        # 高通滤波选项
        self.high_pass_check = QCheckBox("应用高通滤波器 (去除低频噪音)")
        self.high_pass_check.setChecked(False)
        processing_layout.addWidget(self.high_pass_check)

        # 语音增强选项
        self.speech_enhance_check = QCheckBox("应用语音增强 (提升人声频率范围)")
        self.speech_enhance_check.setChecked(False)
        processing_layout.addWidget(self.speech_enhance_check)

        # 归一化音量选项
        self.normalize_check = QCheckBox("归一化音量 (平衡音量大小)")
        self.normalize_check.setChecked(False)
        processing_layout.addWidget(self.normalize_check)

        processing_group.setLayout(processing_layout)
        main_layout.addWidget(processing_group)

        # 创建额外选项区域
        extra_group = QGroupBox("附加选项")
        extra_layout = QVBoxLayout()

        # 定位到转换好的文件选项
        self.locate_file_check = QCheckBox("转换完成后定位到文件")
        self.locate_file_check.setChecked(True)
        extra_layout.addWidget(self.locate_file_check)

        # 复制到剪贴板选项
        self.copy_to_clipboard_check = QCheckBox("转换完成后复制文件路径到剪贴板")
        self.copy_to_clipboard_check.setChecked(True)
        extra_layout.addWidget(self.copy_to_clipboard_check)

        extra_group.setLayout(extra_layout)
        main_layout.addWidget(extra_group)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        # 音频信息按钮
        self.info_button = QPushButton("查看音频信息")
        self.info_button.setEnabled(False)
        self.info_button.clicked.connect(self.show_audio_info)
        button_layout.addWidget(self.info_button)

        # FFmpeg设置按钮
        ffmpeg_button = QPushButton("FFmpeg设置")
        ffmpeg_button.clicked.connect(self.show_ffmpeg_settings)
        button_layout.addWidget(ffmpeg_button)

        # 创建转换按钮
        self.convert_button = QPushButton("开始转换")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self.convert_video)
        button_layout.addWidget(self.convert_button)

        main_layout.addLayout(button_layout)

        # 状态区域
        self.status_label = QLabel("拖入视频文件或点击上方区域选择文件")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        # 文件路径存储
        self.video_path = None
        self.audio_info = None

        # 更新UI状态
        self.update_ui_state()

    def update_ui_state(self):
        """根据选择的模式更新UI状态"""
        is_extract_mode = self.extract_radio.isChecked()

        # 禁用/启用相关控件
        self.format_combo.setEnabled(not is_extract_mode)
        self.bitrate_combo.setEnabled(not is_extract_mode)
        self.sample_rate_combo.setEnabled(not is_extract_mode)
        self.channels_combo.setEnabled(not is_extract_mode)

        # 处理选项只在转换模式下可用
        self.high_pass_check.setEnabled(not is_extract_mode)
        self.speech_enhance_check.setEnabled(not is_extract_mode)
        self.normalize_check.setEnabled(not is_extract_mode)

    def update_bitrate_options(self, format_name):
        """根据选择的格式更新比特率选项"""
        self.bitrate_combo.clear()

        # 获取当前格式的比特率选项
        bitrates = BITRATES.get(format_name, [])

        if not bitrates:
            self.bitrate_combo.setEnabled(False)
            self.bitrate_combo.addItem("不适用")
        else:
            self.bitrate_combo.setEnabled(True)
            self.bitrate_combo.addItems(bitrates)

            # 设置默认值
            default_index = 0
            if format_name == "opus":
                # 24k是opus的推荐值
                default_index = bitrates.index("24k") if "24k" in bitrates else 0
            elif format_name == "mp3":
                # 128k是mp3的推荐值
                default_index = bitrates.index("128k") if "128k" in bitrates else 0

            self.bitrate_combo.setCurrentIndex(default_index)

    def set_video_path(self, path):
        """设置视频文件路径并获取音频信息"""
        self.video_path = path
        filename = os.path.basename(path)
        self.status_label.setText(f"已选择: {filename}")
        self.convert_button.setEnabled(True)
        self.info_button.setEnabled(True)

        # 尝试获取音频信息
        try:
            converter = VideoToAudioConverter(self.ffmpeg_path)
            self.audio_info = converter.get_audio_info(path)
        except Exception as e:
            self.audio_info = None
            self.status_label.setText(f"已选择: {filename} (无法获取音频信息: {str(e)})")

    def show_audio_info(self):
        """显示音频信息对话框"""
        if not self.video_path:
            return

        # 如果还没有获取音频信息，尝试获取
        if not self.audio_info:
            try:
                converter = VideoToAudioConverter(self.ffmpeg_path)
                self.audio_info = converter.get_audio_info(self.video_path)
            except Exception as e:
                QMessageBox.warning(self, "无法获取音频信息", f"获取音频信息失败: {str(e)}")
                return

        # 显示音频信息对话框
        dialog = AudioInfoDialog(self, self.audio_info)
        dialog.exec()

    def show_ffmpeg_settings(self):
        """显示FFmpeg设置对话框"""
        dialog = FFmpegSettingsDialog(self, self.ffmpeg_path)
        if dialog.exec() == QDialog.Accepted:
            new_path = dialog.get_ffmpeg_path()
            # 只有当路径变化时才更新
            if new_path != self.ffmpeg_path:
                self.ffmpeg_path = new_path
                # 清除缓存的音频信息
                self.audio_info = None
                if self.video_path:
                    self.set_video_path(self.video_path)

                # 尝试测试新路径
                try:
                    converter = VideoToAudioConverter(self.ffmpeg_path)
                    QMessageBox.information(self, "FFmpeg设置", "FFmpeg路径设置成功!")
                except Exception as e:
                    QMessageBox.warning(self, "FFmpeg设置", f"FFmpeg路径设置失败: {str(e)}")

    def convert_video(self):
        if not self.video_path:
            return

        try:
            # 创建转换器
            converter = VideoToAudioConverter(self.ffmpeg_path)

            # 检查是提取模式还是转换模式
            is_extract_mode = self.extract_radio.isChecked()

            if is_extract_mode:
                # 直接提取模式
                output_path = converter.extract_audio(self.video_path)
                success_message = "音频提取成功"
            else:
                # 转换模式 - 获取设置
                output_format = self.format_combo.currentText()
                sample_rate = int(self.sample_rate_combo.currentText())
                channels = 1 if self.channels_combo.currentIndex() == 0 else 2

                # 获取比特率（如果适用）
                bitrate = None
                if self.bitrate_combo.isEnabled():
                    bitrate = self.bitrate_combo.currentText()

                # 获取处理选项
                apply_high_pass = self.high_pass_check.isChecked()
                apply_speech_enhance = self.speech_enhance_check.isChecked()
                apply_normalize = self.normalize_check.isChecked()

                # 进行转换
                temp_audio_path = converter.convert(
                    self.video_path,
                    output_format=output_format,
                    sample_rate=sample_rate,
                    channels=channels,
                    bitrate=bitrate
                )

                # 如果需要应用处理
                if apply_high_pass or apply_speech_enhance or apply_normalize:
                    processor = AudioProcessor()
                    output_path = processor.process_audio(
                        temp_audio_path,
                        Path(self.video_path).with_suffix(f".{output_format}"),
                        apply_high_pass=apply_high_pass,
                        apply_speech_enhance=apply_speech_enhance,
                        apply_normalize=apply_normalize
                    )
                    # 如果创建了临时文件，删除它
                    if temp_audio_path != output_path:
                        os.remove(temp_audio_path)
                else:
                    output_path = temp_audio_path

                success_message = "音频转换成功"

            # 如果需要定位到文件
            if self.locate_file_check.isChecked():
                self.show_in_folder(output_path)

            # 如果需要复制到剪贴板
            if self.copy_to_clipboard_check.isChecked():
                self.copy_to_clipboard(output_path)

            QMessageBox.information(self, success_message, f"输出文件: {output_path}")

        except Exception as e:
            QMessageBox.critical(self, "操作失败", f"处理过程中出错: {str(e)}")

    def show_in_folder(self, path):
        # 根据不同平台打开文件夹并选中文件
        if sys.platform == 'win32':
            import subprocess
            subprocess.run(['explorer', '/select,', os.path.normpath(path)])
        elif sys.platform == 'darwin':  # macOS
            import subprocess
            subprocess.run(['open', '-R', path])
        else:  # Linux
            # 打开文件所在文件夹
            import subprocess
            subprocess.run(['xdg-open', os.path.dirname(path)])

    def copy_to_clipboard(self, path):
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()

        # 设置文本路径
        mime_data.setText(path)

        # 设置文件URL（用于某些支持拖放文件的应用）
        url = f"file:///{os.path.abspath(path)}"
        mime_data.setUrls([url])

        clipboard.setMimeData(mime_data)

        self.status_label.setText(f"文件路径已复制到剪贴板: {path}")


class DropArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)

        # 样式设置
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border: 2px dashed #aaaaaa;
                border-radius: 5px;
            }
        """)

        # 创建布局和标签
        layout = QVBoxLayout(self)
        self.label = QLabel("拖放视频文件到这里或点击选择文件")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        # 点击打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm);;所有文件 (*)"
        )

        if file_path:
            self.parent.set_video_path(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        # 仅接受文件
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        # 获取第一个拖入的文件
        file_url = event.mimeData().urls()[0]
        file_path = file_url.toLocalFile()

        # 检查是否为视频文件
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
        if any(file_path.lower().endswith(ext) for ext in valid_extensions):
            self.parent.set_video_path(file_path)
        else:
            QMessageBox.warning(self, "不支持的文件", "请拖入支持的视频文件格式")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()