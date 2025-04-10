from PySide6.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QFileDialog, QTextEdit, QSplitter, QCheckBox, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont

from ui_components import AudioTableWidget, ProgressBarWithLabel, SUPPORTED_AUDIO_EXTENSIONS


class UIInitMixin:
    """UI初始化混入类"""

    def init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("音频转文本/SRT工具")
        self.setMinimumSize(900, 700)  # 增加窗口大小

        # 创建中心部件
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 标题
        title_label = QLabel("音频转文本/SRT工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = title_label.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # 各个区域初始化
        self.init_service_selection(main_layout)
        self.init_conversion_settings(main_layout)
        self.init_file_list(main_layout)
        self.init_progress_and_log(main_layout)
        self.init_action_buttons(main_layout)

        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")

        # 菜单栏
        self.create_menu()

        # 设置拖放
        self.setAcceptDrops(True)

    def init_service_selection(self, main_layout):
        """初始化服务选择区域"""
        service_group = QGroupBox("API服务设置")
        service_layout = QVBoxLayout()

        # 服务选择行
        service_row = QHBoxLayout()
        service_label = QLabel("选择服务:")

        self.service_group = QButtonGroup(self)
        self.groq_radio = QRadioButton("Groq Whisper")
        self.deepgram_radio = QRadioButton("Deepgram (开发中)")

        self.service_group.addButton(self.groq_radio, 0)
        self.service_group.addButton(self.deepgram_radio, 1)

        service_row.addWidget(service_label)
        service_row.addWidget(self.groq_radio)
        service_row.addWidget(self.deepgram_radio)
        service_row.addStretch()

        service_layout.addLayout(service_row)

        # API密钥选择行
        key_row = QHBoxLayout()
        key_label = QLabel("API密钥:")
        self.api_key_combo = QComboBox()
        self.api_key_combo.setMinimumWidth(300)

        self.api_key_manage_btn = QPushButton("管理密钥")
        self.api_key_manage_btn.clicked.connect(self.open_api_key_manager)

        key_row.addWidget(key_label)
        key_row.addWidget(self.api_key_combo)
        key_row.addWidget(self.api_key_manage_btn)
        key_row.addStretch()

        service_layout.addLayout(key_row)

        service_group.setLayout(service_layout)
        main_layout.addWidget(service_group)

        # 连接信号
        self.service_group.idClicked.connect(self.on_service_changed)

    def init_conversion_settings(self, main_layout):
        """初始化转换设置区域"""
        settings_group = QGroupBox("转换设置")
        settings_layout = QHBoxLayout()

        # 输出格式
        format_layout = QVBoxLayout()
        format_label = QLabel("输出格式:")
        self.format_group = QButtonGroup(self)

        format_buttons_layout = QHBoxLayout()
        self.srt_radio = QRadioButton("SRT字幕格式")
        self.text_radio = QRadioButton("纯文本格式")

        self.format_group.addButton(self.srt_radio, 0)
        self.format_group.addButton(self.text_radio, 1)

        format_buttons_layout.addWidget(self.srt_radio)
        format_buttons_layout.addWidget(self.text_radio)

        format_layout.addWidget(format_label)
        format_layout.addLayout(format_buttons_layout)

        # 语言选择（可选）
        lang_layout = QVBoxLayout()
        lang_label = QLabel("语言(可选):")
        self.lang_combo = QComboBox()

        # 添加常用语言
        self.lang_combo.addItem("自动检测", "")
        self.lang_combo.addItem("中文", "zh")
        self.lang_combo.addItem("英语", "en")
        self.lang_combo.addItem("日语", "ja")
        self.lang_combo.addItem("韩语", "ko")
        self.lang_combo.addItem("法语", "fr")
        self.lang_combo.addItem("德语", "de")
        self.lang_combo.addItem("西班牙语", "es")
        self.lang_combo.addItem("俄语", "ru")

        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)

        # 高级设置按钮
        settings_btn_layout = QVBoxLayout()
        settings_btn_layout.addStretch()
        self.conversion_settings_btn = QPushButton("高级设置")
        self.conversion_settings_btn.clicked.connect(self.open_conversion_settings)
        settings_btn_layout.addWidget(self.conversion_settings_btn)

        settings_layout.addLayout(format_layout)
        settings_layout.addLayout(lang_layout)
        settings_layout.addLayout(settings_btn_layout)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # 连接信号
        self.format_group.idClicked.connect(self.on_format_changed)

    def init_file_list(self, main_layout):
        """初始化文件列表区域"""
        files_group = QGroupBox("音频文件")
        files_layout = QVBoxLayout()

        # 拖放说明
        drag_label = QLabel("拖放音频文件到此处，或点击添加按钮选择文件")
        drag_label.setAlignment(Qt.AlignCenter)
        files_layout.addWidget(drag_label)

        # 创建按钮区域，放在文件列表上方
        button_layout = QHBoxLayout()

        # 全选复选框
        self.select_all_checkbox = QCheckBox("全选")
        self.select_all_checkbox.setEnabled(False)
        self.select_all_checkbox.toggled.connect(self.toggle_select_all)
        button_layout.addWidget(self.select_all_checkbox)

        button_layout.addStretch()

        # 操作按钮
        self.add_file_btn = QPushButton("添加文件")
        self.add_file_btn.clicked.connect(self.add_files)
        button_layout.addWidget(self.add_file_btn)

        self.remove_file_btn = QPushButton("删除所选")
        self.remove_file_btn.clicked.connect(self.remove_files)
        button_layout.addWidget(self.remove_file_btn)

        self.clear_files_btn = QPushButton("清空列表")
        self.clear_files_btn.clicked.connect(self.clear_files)
        button_layout.addWidget(self.clear_files_btn)

        # 先添加按钮区域
        files_layout.addLayout(button_layout)

        # 使用增强版的音频表格
        self.file_list = AudioTableWidget()
        self.file_list.setMinimumHeight(250)
        self.file_list.files_dropped.connect(self.add_dropped_files)

        # 连接大小变化信号
        self.file_list.size_changed.connect(self.on_table_size_changed)

        # 添加表格到布局
        files_layout.addWidget(self.file_list, 1)  # 使用拉伸因子，允许表格伸展

        # 设置布局
        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)

        # 连接信号
        self.file_list.itemSelectionChanged.connect(self.update_file_buttons)

    def init_progress_and_log(self, main_layout):
        """初始化进度和日志区域"""
        # 创建分割器，允许调整大小
        splitter = QSplitter(Qt.Vertical)

        # 进度区域
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_group = QGroupBox("进度")
        progress_inner_layout = QVBoxLayout()

        # 使用自定义进度条组件
        self.progress_bar = ProgressBarWithLabel()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        progress_inner_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_inner_layout)
        progress_layout.addWidget(progress_group)

        # 日志区域
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_group = QGroupBox("日志")
        log_inner_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_inner_layout.addWidget(self.log_text)

        log_group.setLayout(log_inner_layout)
        log_layout.addWidget(log_group)

        # 添加到分割器
        splitter.addWidget(progress_widget)
        splitter.addWidget(log_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def init_action_buttons(self, main_layout):
        """初始化操作按钮"""
        btn_layout = QHBoxLayout()

        self.proxy_btn = QPushButton("代理设置")
        self.proxy_btn.clicked.connect(self.open_proxy_settings)

        self.start_btn = QPushButton("开始转换")
        self.start_btn.setMinimumWidth(120)  # 增加按钮宽度
        self.start_btn.setMinimumHeight(40)  # 增加按钮高度
        font = self.start_btn.font()
        font.setBold(True)
        self.start_btn.setFont(font)
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)

        btn_layout.addWidget(self.proxy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)

        main_layout.addLayout(btn_layout)

    def create_menu(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件")

        add_action = QAction("添加文件", self)
        add_action.triggered.connect(self.add_files)
        file_menu.addAction(add_action)

        clear_action = QAction("清空列表", self)
        clear_action.triggered.connect(self.clear_files)
        file_menu.addAction(clear_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 设置菜单
        settings_menu = menu_bar.addMenu("设置")

        proxy_action = QAction("代理设置", self)
        proxy_action.triggered.connect(self.open_proxy_settings)
        settings_menu.addAction(proxy_action)

        api_key_action = QAction("API密钥管理", self)
        api_key_action.triggered.connect(self.open_api_key_manager)
        settings_menu.addAction(api_key_action)

        conversion_settings_action = QAction("转换高级设置", self)
        conversion_settings_action.triggered.connect(self.open_conversion_settings)
        settings_menu.addAction(conversion_settings_action)

        # 工具菜单
        tools_menu = menu_bar.addMenu("工具")

        check_deps_action = QAction("检查依赖", self)
        check_deps_action.triggered.connect(self.check_dependencies)
        tools_menu.addAction(check_deps_action)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)