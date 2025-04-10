import os
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStatusBar, QTextEdit, QGroupBox, QRadioButton,
    QComboBox, QButtonGroup, QPushButton, QListWidgetItem,
    QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QAction

from ui_components import ProgressBarWithLabel, SUPPORTED_AUDIO_EXTENSIONS
from config_manager import (
    get_api_keys, get_last_used_key, get_output_format, get_proxy_settings,
    get_api_service, save_last_used_key, save_output_format, save_api_service
)
from ui_dialogs import ProxySettingsDialog, APIKeyDialog, DependencyCheckerDialog, AboutDialog
from worker_threads import ProcessWorker

# 导入新的Mixin类
from main_window_init_mixin import UIInitMixin
from main_window_methods_mixin import MethodsMixin
from main_window_processing_mixin import ProcessingMixin
from main_window_events_mixin import EventsMixin

# 支持的格式
SUPPORTED_FORMATS = {
    "srt": "SRT字幕格式",
    "text": "纯文本格式"
}


class MainWindow(QMainWindow, UIInitMixin, MethodsMixin, ProcessingMixin, EventsMixin):
    """主窗口类，使用多重继承组合各个功能Mixin"""

    def __init__(self):
        super().__init__()

        # 初始化变量
        self.process_worker = None
        self.file_progress = {}  # 文件进度跟踪

        # 初始化UI
        self.init_ui()

        # 加载设置
        self.load_settings()