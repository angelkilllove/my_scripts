import sys
import os
from pathlib import Path
from datetime import timedelta
from typing import List, Dict, Tuple, Optional

from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox,
                               QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                               QSpinBox, QPushButton, QTableWidget, QTableWidgetItem,
                               QHeaderView, QAbstractItemView, QDoubleSpinBox, QProgressBar,
                               QProgressDialog, QDialog, QRadioButton, QGroupBox, QButtonGroup,
                               QLineEdit, QGridLayout, QCheckBox, QStyle)
from PySide6.QtCore import Qt, QMimeData, QThreadPool
from PySide6.QtGui import QDragEnterEvent, QDropEvent

# 导入自定义模块
from audio_converter import VideoToAudioConverter
from converter_workers import AudioInfoWorker
from ui_handlers import (browse_output_dir, save_settings, load_settings,
                         on_conversion_started, on_conversion_progress,
                         on_conversion_finished, start_conversion,
                         start_conversion_all, show_advanced_settings,
                         refresh_selected_files, refresh_all_files)
from settings_manager import show_ffmpeg_settings_dialog

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
    "ogg": ["32k", "64k", "96k", "128k", "160k", "192k", "256k"],
    "auto": []  # 自动模式不需要比特率
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量音视频转换工具")
        self.setMinimumSize(900, 600)

        # 初始化数据
        self.file_list = []  # 存储文件路径和相关信息
        self.ffmpeg_path = VideoToAudioConverter.find_ffmpeg()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # 限制最大同时处理数量

        # 高级分段设置
        self.split_settings = {
            'use_silence_detection': False,
            'silence_threshold': -40,  # dB
            'silence_duration': 0.5,  # 秒
            'max_offset': 60,  # 秒
            'min_segment_length': 30  # 秒
        }

        # 设置中央部件
        self.setup_ui()

        # 检查 FFmpeg
        if not self.ffmpeg_path:
            QMessageBox.warning(self, "FFmpeg未找到",
                                "未在系统中找到FFmpeg。某些功能可能无法使用。\n"
                                "请在设置中手动指定FFmpeg路径。")

    def setup_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # ------- 文件列表区域 -------
        file_list_layout = QVBoxLayout()
        file_list_label = QLabel("文件列表:")
        file_list_layout.addWidget(file_list_label)

        # 创建表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(8)
        self.file_table.setHorizontalHeaderLabels([
            "文件名", "状态", "时长", "格式", "声道", "采样率", "比特率", "分段数"
        ])

        # 设置表格属性
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table.setAlternatingRowColors(True)

        # 修改表格属性，允许调整列宽
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        for i in range(1, 8):
            self.file_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Interactive)

        file_list_layout.addWidget(self.file_table)

        # 添加文件按钮区域
        file_buttons_layout = QHBoxLayout()
        self.add_files_btn = QPushButton("添加文件")
        self.add_files_btn.clicked.connect(self.add_files)
        self.remove_files_btn = QPushButton("移除选中文件")
        self.remove_files_btn.clicked.connect(self.remove_selected_files)
        self.clear_files_btn = QPushButton("清空列表")
        self.clear_files_btn.clicked.connect(self.clear_files)
        self.refresh_selected_btn = QPushButton("刷新选中文件")
        self.refresh_selected_btn.clicked.connect(lambda: refresh_selected_files(self))
        self.refresh_all_btn = QPushButton("刷新所有文件")
        self.refresh_all_btn.clicked.connect(lambda: refresh_all_files(self))

        file_buttons_layout.addWidget(self.add_files_btn)
        file_buttons_layout.addWidget(self.remove_files_btn)
        file_buttons_layout.addWidget(self.clear_files_btn)
        file_buttons_layout.addWidget(self.refresh_selected_btn)
        file_buttons_layout.addWidget(self.refresh_all_btn)

        file_list_layout.addLayout(file_buttons_layout)
        main_layout.addLayout(file_list_layout)

        # ------- 转换选项区域 -------
        options_group = QGroupBox("转换选项")
        options_layout = QVBoxLayout()

        # 输出格式设置组
        format_group = QGroupBox("输出格式设置")
        format_group_layout = QVBoxLayout()

        # 输出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("输出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("自动检测", "auto")
        for fmt in FORMATS:
            self.format_combo.addItem(fmt, fmt)
        self.format_combo.setCurrentText("opus")  # 默认opus
        format_layout.addWidget(self.format_combo)
        format_group_layout.addLayout(format_layout)

        # 采样率
        sample_rate_layout = QHBoxLayout()
        sample_rate_layout.addWidget(QLabel("采样率(Hz):"))
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems([str(sr) for sr in SAMPLE_RATES])
        self.sample_rate_combo.setCurrentText(str(DEFAULT_SAMPLE_RATE))  # 默认16kHz，适合语音识别
        sample_rate_layout.addWidget(self.sample_rate_combo)
        format_group_layout.addLayout(sample_rate_layout)

        # 声道数
        channels_layout = QHBoxLayout()
        channels_layout.addWidget(QLabel("声道数:"))
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["1 (单声道)", "2 (立体声)"])
        self.channels_combo.setCurrentIndex(0)  # 默认单声道，适合语音识别
        channels_layout.addWidget(self.channels_combo)
        format_group_layout.addLayout(channels_layout)

        # 比特率
        bitrate_layout = QHBoxLayout()
        bitrate_layout.addWidget(QLabel("比特率:"))
        self.bitrate_combo = QComboBox()
        # 初始化为opus的比特率选项
        self.bitrate_combo.addItems(BITRATES["opus"])
        self.bitrate_combo.setCurrentText("24k")  # 默认24k，适合语音识别
        bitrate_layout.addWidget(self.bitrate_combo)
        format_group_layout.addLayout(bitrate_layout)

        format_group.setLayout(format_group_layout)
        options_layout.addWidget(format_group)

        # 在格式选项后添加输出路径设置
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(QLabel("输出路径:"))
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("留空将输出到源文件所在目录")
        self.output_dir_edit.setToolTip("设置统一的输出路径，留空则输出到每个文件的原始目录")
        output_dir_layout.addWidget(self.output_dir_edit)

        browse_dir_btn = QPushButton("浏览...")
        browse_dir_btn.clicked.connect(lambda: browse_output_dir(self))
        output_dir_layout.addWidget(browse_dir_btn)

        options_layout.addLayout(output_dir_layout)

        # 分段设置
        segment_layout = QHBoxLayout()
        segment_layout.addWidget(QLabel("分段时长(分钟):"))
        self.segment_duration_spin = QDoubleSpinBox()
        self.segment_duration_spin.setRange(0, 180)  # 0表示不分段，最大180分钟
        self.segment_duration_spin.setValue(0)  # 默认不分段
        self.segment_duration_spin.setDecimals(1)  # 精确到小数点后1位
        self.segment_duration_spin.setSingleStep(1)
        self.segment_duration_spin.valueChanged.connect(self.update_segment_counts)
        segment_layout.addWidget(self.segment_duration_spin)

        segment_layout.addWidget(QLabel("分段时长为0表示不分段"))

        # 高级分段设置按钮
        self.advanced_settings_btn = QPushButton("高级分段设置...")
        self.advanced_settings_btn.clicked.connect(lambda: show_advanced_settings(self))
        self.advanced_settings_btn.setEnabled(False)  # 默认禁用
        self.segment_duration_spin.valueChanged.connect(self.update_advanced_button_state)
        segment_layout.addWidget(self.advanced_settings_btn)

        options_layout.addLayout(segment_layout)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # ------- 底部按钮区域 -------
        bottom_layout = QHBoxLayout()

        # FFmpeg设置按钮
        ffmpeg_button = QPushButton("FFmpeg设置")
        ffmpeg_button.clicked.connect(lambda: show_ffmpeg_settings_dialog(self))
        bottom_layout.addWidget(ffmpeg_button)

        # 保存设置按钮
        save_settings_btn = QPushButton("保存设置")
        save_settings_btn.clicked.connect(lambda: save_settings(self))
        bottom_layout.addWidget(save_settings_btn)

        # 转换按钮
        self.convert_button = QPushButton("转换选中文件")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(lambda: start_conversion(self))
        bottom_layout.addWidget(self.convert_button)

        # 转换所有文件
        self.convert_all_button = QPushButton("转换所有文件")
        self.convert_all_button.setEnabled(False)
        self.convert_all_button.clicked.connect(lambda: start_conversion_all(self))
        bottom_layout.addWidget(self.convert_all_button)

        main_layout.addLayout(bottom_layout)

        # ------- 状态栏 -------
        self.status_label = QLabel("拖放文件到此窗口或点击\"添加文件\"按钮选择文件")
        self.status_label.setMinimumWidth(self.width() * 0.8)  # 确保状态栏宽度不会随文字变化
        self.statusBar().addWidget(self.status_label)

        # 设置窗口接受拖放
        self.setAcceptDrops(True)

        # 在设置完所有UI后，连接信号
        self.format_combo.currentTextChanged.connect(self.update_format_options)
        # 初始化格式选项
        self.update_format_options(self.format_combo.currentText())

        # 加载设置
        load_settings(self)

    def dragEnterEvent(self, event: QDragEnterEvent):
        # 接受文件拖放
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        # 处理拖放的文件
        urls = event.mimeData().urls()
        files = [url.toLocalFile() for url in urls]
        self.add_files_from_paths(files)

    def add_files(self):
        """打开文件对话框添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音视频文件", "",
            "音视频文件 (*.mp4 *.avi *.mov *.mkv *.webm *.mp3 *.wav *.ogg *.flac *.aac *.m4a *.opus);;所有文件 (*)"
        )

        if files:
            self.add_files_from_paths(files)

    def add_files_from_paths(self, file_paths):
        """从路径列表添加文件"""
        added_count = 0

        for path in file_paths:
            # 检查文件是否已在列表中
            if any(f['path'] == path for f in self.file_list):
                continue

            # 添加到文件列表
            self.file_list.append({
                'path': path,
                'filename': os.path.basename(path),
                'status': '等待中',
                'audio_info': None,  # 稍后获取
                'processing': False,
                'completed': False,
                'segments': 0
            })
            added_count += 1

        if added_count > 0:
            # 刷新表格
            self.refresh_file_table()

            # 异步获取音频信息
            self.update_audio_info()

            # 启用转换按钮
            self.convert_button.setEnabled(True)
            self.convert_all_button.setEnabled(True)

    def remove_selected_files(self):
        """移除选中的文件"""
        selected_rows = sorted(set(index.row() for index in self.file_table.selectedIndexes()), reverse=True)

        for row in selected_rows:
            if row < len(self.file_list):
                # 检查是否正在处理
                if self.file_list[row]['processing']:
                    QMessageBox.warning(self, "无法移除", f"文件 '{self.file_list[row]['filename']}' 正在处理中，无法移除。")
                    continue

                # 移除文件
                del self.file_list[row]

        # 刷新表格
        self.refresh_file_table()

        # 如果列表为空，禁用转换按钮
        if not self.file_list:
            self.convert_button.setEnabled(False)
            self.convert_all_button.setEnabled(False)

    def clear_files(self):
        """清空文件列表"""
        # 检查是否有正在处理的文件
        if any(f['processing'] for f in self.file_list):
            QMessageBox.warning(self, "无法清空", "有文件正在处理中，无法清空列表。")
            return

        self.file_list = []
        self.refresh_file_table()
        self.convert_button.setEnabled(False)
        self.convert_all_button.setEnabled(False)

    def refresh_file_table(self):
        """刷新文件表格"""
        self.file_table.setRowCount(len(self.file_list))

        for row, file_info in enumerate(self.file_list):
            # 文件名
            filename_item = QTableWidgetItem(file_info['filename'])
            filename_item.setToolTip(file_info['path'])  # 添加完整路径提示
            self.file_table.setItem(row, 0, filename_item)

            # 状态
            status_item = QTableWidgetItem(file_info['status'])
            status_item.setToolTip(file_info['status'])  # 添加完整状态提示
            if file_info['completed']:
                if '成功' in file_info['status']:
                    status_item.setForeground(Qt.green)
                else:
                    status_item.setForeground(Qt.red)
            elif file_info['processing']:
                status_item.setForeground(Qt.blue)
            self.file_table.setItem(row, 1, status_item)

            # 音频信息
            audio_info = file_info.get('audio_info')

            if audio_info:
                # 时长
                duration_sec = audio_info.get('duration', 0)
                duration_str = str(timedelta(seconds=int(duration_sec)))
                self.file_table.setItem(row, 2, QTableWidgetItem(duration_str))

                # 格式
                self.file_table.setItem(row, 3, QTableWidgetItem(audio_info.get('codec', '未知')))

                # 声道
                self.file_table.setItem(row, 4, QTableWidgetItem(audio_info.get('channels_description', '未知')))

                # 采样率
                self.file_table.setItem(row, 5, QTableWidgetItem(f"{audio_info.get('sample_rate', 0)} Hz"))

                # 比特率
                bit_rate = audio_info.get('bit_rate', 0)
                bit_rate_str = f"{bit_rate / 1000:.0f} kbps"
                if audio_info.get('is_bit_rate_estimated', False):
                    bit_rate_str += " (估算)"
                self.file_table.setItem(row, 6, QTableWidgetItem(bit_rate_str))

                # 分段数
                if self.segment_duration_spin.value() > 0 and duration_sec > 0:
                    segment_duration_sec = self.segment_duration_spin.value() * 60
                    segments = min(9, max(1, int((duration_sec + segment_duration_sec - 1) // segment_duration_sec)))
                    file_info['segments'] = segments
                    self.file_table.setItem(row, 7, QTableWidgetItem(str(segments)))
                else:
                    file_info['segments'] = 0
                    self.file_table.setItem(row, 7, QTableWidgetItem('不分段'))
            else:
                for col in range(2, 8):
                    self.file_table.setItem(row, col, QTableWidgetItem('加载中...'))

        # 更新状态栏
        self.update_status_bar()

    def update_status_bar(self):
        """更新状态栏信息"""
        total_files = len(self.file_list)
        completed_files = sum(1 for f in self.file_list if f['completed'])
        processing_files = sum(1 for f in self.file_list if f['processing'] and not f['completed'])

        if total_files == 0:
            status_text = "拖放文件到此窗口或点击\"添加文件\"按钮选择文件"
        else:
            status_text = f"总计: {total_files} 文件"

            if processing_files > 0:
                status_text += f" | 处理中: {processing_files}"

            if completed_files > 0:
                status_text += f" | 完成: {completed_files}"

        # 设置固定宽度的状态栏标签
        self.status_label.setText(status_text)
        self.status_label.setMinimumWidth(self.width() * 0.8)  # 确保状态栏宽度不会随文字变化

    def update_audio_info(self):
        """异步获取所有文件的音频信息"""
        for idx, file_info in enumerate(self.file_list):
            if file_info['audio_info'] is None and not file_info['processing']:
                # 标记为正在处理
                file_info['processing'] = True
                file_info['status'] = '获取信息中...'

                # 更新表格中的状态
                if self.file_table.item(idx, 1):
                    self.file_table.item(idx, 1).setText('获取信息中...')

                # 创建处理线程
                worker = AudioInfoWorker(idx, file_info['path'], self.ffmpeg_path)
                worker.signals.finished.connect(self.on_audio_info_ready)

                # 启动线程
                self.thread_pool.start(worker)

                # 刷新表格
                self.refresh_file_table()

    def on_audio_info_ready(self, idx, success, result):
        """音频信息获取完成的回调"""
        if idx < len(self.file_list):
            file_info = self.file_list[idx]
            file_info['processing'] = False

            if success:
                file_info['audio_info'] = result
                file_info['status'] = '准备就绪'
            else:
                file_info['status'] = f'获取信息失败: {result}'

            # 刷新表格
            self.refresh_file_table()

    def update_format_options(self, format_name):
        """根据选择的格式更新所有相关选项"""
        # 如果是自动检测模式，禁用所有参数设置
        if format_name == "auto":
            self.bitrate_combo.setEnabled(False)
            self.bitrate_combo.clear()
            self.bitrate_combo.addItem("不适用")

            self.sample_rate_combo.setEnabled(False)
            self.channels_combo.setEnabled(False)
            self.statusBar().showMessage("自动检测模式将保持原始音频格式不变", 3000)
            return

        # 对于其他格式，启用所有参数设置
        self.sample_rate_combo.setEnabled(True)
        self.channels_combo.setEnabled(True)

        # 更新比特率选项
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

        # 根据格式设置推荐采样率和声道数
        if format_name == "opus":
            # Opus适合语音识别
            self.sample_rate_combo.setCurrentText("16000")
            self.channels_combo.setCurrentIndex(0)  # 单声道
        elif format_name == "mp3" or format_name == "aac":
            # MP3/AAC适合音乐
            self.sample_rate_combo.setCurrentText("44100")
            self.channels_combo.setCurrentIndex(1)  # 立体声
        elif format_name == "wav" or format_name == "flac":
            # WAV/FLAC保持高质量
            self.sample_rate_combo.setCurrentText("48000")
            self.channels_combo.setCurrentIndex(1)  # 立体声

    def update_segment_counts(self):
        """更新所有文件的分段数显示"""
        segment_duration = self.segment_duration_spin.value()

        for idx, file_info in enumerate(self.file_list):
            audio_info = file_info.get('audio_info')

            if audio_info:
                duration_sec = audio_info.get('duration', 0)

                if segment_duration > 0 and duration_sec > 0:
                    segment_duration_sec = segment_duration * 60
                    segments = min(9, max(1, int((duration_sec + segment_duration_sec - 1) // segment_duration_sec)))
                    file_info['segments'] = segments

                    # 更新表格
                    if self.file_table.item(idx, 7):
                        self.file_table.item(idx, 7).setText(str(segments))
                else:
                    file_info['segments'] = 0

                    # 更新表格
                    if self.file_table.item(idx, 7):
                        self.file_table.item(idx, 7).setText('不分段')

    def update_advanced_button_state(self):
        """更新高级设置按钮状态"""
        # 只有当分段时长大于0时才启用高级设置按钮
        self.advanced_settings_btn.setEnabled(self.segment_duration_spin.value() > 0)

    def on_conversion_started(self, idx):
        """转换开始的回调"""
        on_conversion_started(self, idx)

    def on_conversion_progress(self, idx, progress):
        """转换进度的回调"""
        on_conversion_progress(self, idx, progress)

    def on_conversion_finished(self, idx, success, result):
        """转换完成的回调"""
        on_conversion_finished(self, idx, success, result)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()