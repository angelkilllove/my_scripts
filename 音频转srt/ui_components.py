import os
import av
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QProgressBar, QAbstractItemView,
    QHeaderView, QStyledItemDelegate, QStyleOptionViewItem, QStyle
)
from PySide6.QtCore import Qt, Signal, QMimeData, QUrl, QEvent, QSize, QSettings, QPoint
from PySide6.QtGui import QResizeEvent

# 支持的音频文件扩展名
SUPPORTED_AUDIO_EXTENSIONS = [
    ".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".opus",
    ".mpeg", ".mpga", ".webm", ".flac"
]


class AudioTableWidget(QTableWidget):
    """音频文件表格控件，支持拖放和显示音频文件信息，可调整大小和记住位置"""

    files_dropped = Signal(list)  # 文件拖放信号
    size_changed = Signal(QSize)  # 大小改变信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)  # 文件路径、时长、采样率、通道数、文件格式、比特率、大小
        self.setHorizontalHeaderLabels(["文件路径", "时长", "采样率", "通道", "格式", "比特率", "文件大小"])

        # 配置表格外观和行为
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)  # 整行选择
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 允许多选
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 不可编辑
        self.verticalHeader().setVisible(False)  # 隐藏垂直表头
        self.setShowGrid(False)  # 不显示网格线

        # 允许拖动调整列宽
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # 设置列宽默认值
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # 文件路径列自适应宽度
        for col in range(1, 7):
            self.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # 加载保存的大小设置
        self.loadSettings()

        # 启用拖放功能
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        # 接收调整大小事件
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """事件过滤器，用于捕获大小改变"""
        if obj == self and event.type() == QEvent.Resize:
            resize_event = QResizeEvent(event.size(), event.oldSize())
            self.size_changed.emit(resize_event.size())
            # 保存当前大小
            self.saveSettings()
        return super().eventFilter(obj, event)

    def saveSettings(self):
        """保存表格设置"""
        settings = QSettings("AudioTranscriber", "TableSettings")
        settings.setValue("tableSize", self.size())
        settings.setValue("columnWidths", [self.columnWidth(i) for i in range(self.columnCount())])

    def loadSettings(self):
        """加载表格设置"""
        settings = QSettings("AudioTranscriber", "TableSettings")
        size = settings.value("tableSize")
        if size:
            self.resize(size)

        column_widths = settings.value("columnWidths")
        if column_widths and len(column_widths) == self.columnCount():
            for i, width in enumerate(column_widths):
                if width > 0:  # 确保宽度有效
                    self.setColumnWidth(i, width)

    def add_audio_file(self, file_path):
        """添加音频文件到表格，并提取其元数据"""
        row = self.rowCount()
        self.insertRow(row)

        # 文件路径（显示完整路径，使用Windows风格）
        file_path_formatted = file_path.replace("/", "\\")
        path_item = QTableWidgetItem(file_path_formatted)
        path_item.setData(Qt.UserRole, file_path)  # 存储原始路径
        self.setItem(row, 0, path_item)

        try:
            # 使用PyAV提取音频元数据
            container = av.open(file_path)
            audio_stream = next((s for s in container.streams if s.type == 'audio'), None)

            if audio_stream:
                # 计算时长
                duration = container.duration / 1000000.0 if container.duration else 0  # 转换为秒
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                time_str = f"{minutes:02d}:{seconds:02d}"
                self.setItem(row, 1, QTableWidgetItem(time_str))

                # 采样率
                sample_rate = f"{audio_stream.sample_rate // 1000}kHz" if audio_stream.sample_rate else "未知"
                self.setItem(row, 2, QTableWidgetItem(sample_rate))

                # 通道数
                channels = str(audio_stream.channels) if audio_stream.channels else "未知"
                self.setItem(row, 3, QTableWidgetItem(channels))

                # 文件格式
                format_name = container.format.name if hasattr(container, 'format') and hasattr(container.format, 'name') else "未知"
                self.setItem(row, 4, QTableWidgetItem(format_name))

                # 比特率
                bit_rate = f"{audio_stream.bit_rate // 1000}kbps" if hasattr(audio_stream, 'bit_rate') and audio_stream.bit_rate else "未知"
                self.setItem(row, 5, QTableWidgetItem(bit_rate))
            else:
                # 如果没有音频流
                self.setItem(row, 1, QTableWidgetItem("未知"))
                self.setItem(row, 2, QTableWidgetItem("未知"))
                self.setItem(row, 3, QTableWidgetItem("未知"))
                self.setItem(row, 4, QTableWidgetItem("未知"))
                self.setItem(row, 5, QTableWidgetItem("未知"))

            # 关闭容器
            container.close()
        except Exception as e:
            # 处理错误情况
            print(f"提取音频信息出错: {e}")
            self.setItem(row, 1, QTableWidgetItem("错误"))
            self.setItem(row, 2, QTableWidgetItem("错误"))
            self.setItem(row, 3, QTableWidgetItem("错误"))
            self.setItem(row, 4, QTableWidgetItem("错误"))
            self.setItem(row, 5, QTableWidgetItem("错误"))

        # 文件大小
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            self.setItem(row, 6, QTableWidgetItem(size_str))
        except:
            self.setItem(row, 6, QTableWidgetItem("未知"))

        # 居中显示除文件路径外的所有列
        for col in range(1, 7):
            if self.item(row, col):
                self.item(row, col).setTextAlignment(Qt.AlignCenter)

        return row

    def get_selected_file_paths(self):
        """获取所有选中的文件路径"""
        file_paths = []
        for item in self.selectedItems():
            if item.column() == 0:  # 只处理第一列的项目
                file_path = item.data(Qt.UserRole)
                file_paths.append(file_path)
        return file_paths

    def get_all_file_paths(self):
        """获取所有文件路径"""
        file_paths = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item:
                file_path = item.data(Qt.UserRole)
                file_paths.append(file_path)
        return file_paths

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
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

    def dragMoveEvent(self, event):
        """拖拽移动事件 - 必须重写以允许放置"""
        if event.mimeData().hasUrls():
            event.accept()  # 显式接受事件
        else:
            event.ignore()  # 显式拒绝事件

    def dropEvent(self, event):
        """拖拽释放事件"""
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
                self.files_dropped.emit(files)
                event.accept()  # 显式接受事件
                return

        event.ignore()  # 显式拒绝事件


class ProgressBarWithLabel(QProgressBar):
    """带有标签的进度条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(True)
        self.setFormat("%p% - %v/%m")
        self.status_text = ""

    def setStatus(self, text):
        """设置状态文本"""
        self.status_text = text
        self.updateText()

    def updateText(self):
        """更新显示文本"""
        if self.status_text:
            self.setFormat(f"{self.status_text} - %p%")
        else:
            self.setFormat("%p% - %v/%m")