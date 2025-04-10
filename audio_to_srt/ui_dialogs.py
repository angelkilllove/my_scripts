from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QGroupBox, QRadioButton,
    QListWidget, QListWidgetItem, QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt

from config_manager import (
    get_proxy_details, save_proxy_settings,
    get_api_keys, add_api_key, remove_api_key
)


class ProxySettingsDialog(QDialog):
    """代理设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)

        # 创建布局
        layout = QVBoxLayout(self)

        # 使用选项卡分别设置不同服务的代理
        self.tab_widget = QTabWidget()
        self.groq_tab = self.create_proxy_tab("groq")
        self.deepgram_tab = self.create_proxy_tab("deepgram")

        self.tab_widget.addTab(self.groq_tab, "Groq代理")
        self.tab_widget.addTab(self.deepgram_tab, "Deepgram代理")

        layout.addWidget(self.tab_widget)

        # 按钮
        button_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_proxy_tab(self, service_name):
        """创建代理设置选项卡

        参数:
        - service_name: 服务名称("groq"或"deepgram")
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 加载当前设置
        settings = get_proxy_details(service_name)
        enabled = settings.get("enabled", "False").lower() == "true"
        proxy_type = settings.get("type", "http")
        host = settings.get("host", "")
        port = settings.get("port", "")
        username = settings.get("username", "")
        password = settings.get("password", "")

        # 代理设置表单
        form_layout = QVBoxLayout()

        # 代理类型选择
        proxy_type_group = QGroupBox("代理类型")
        proxy_type_layout = QHBoxLayout()

        no_proxy_radio = QRadioButton("不使用代理")
        http_proxy_radio = QRadioButton("HTTP代理")
        socks5_proxy_radio = QRadioButton("SOCKS5代理")

        if not enabled:
            no_proxy_radio.setChecked(True)
        elif proxy_type == "socks5":
            socks5_proxy_radio.setChecked(True)
        else:
            http_proxy_radio.setChecked(True)

        proxy_type_layout.addWidget(no_proxy_radio)
        proxy_type_layout.addWidget(http_proxy_radio)
        proxy_type_layout.addWidget(socks5_proxy_radio)

        proxy_type_group.setLayout(proxy_type_layout)
        form_layout.addWidget(proxy_type_group)

        # 代理设置
        proxy_settings_group = QGroupBox("代理服务器")
        proxy_settings_layout = QVBoxLayout()

        # 主机和端口
        host_port_layout = QHBoxLayout()

        host_label = QLabel("主机:")
        host_input = QLineEdit(host)
        host_input.setPlaceholderText("例如: 127.0.0.1")

        port_label = QLabel("端口:")
        port_input = QLineEdit(port)
        port_input.setPlaceholderText("例如: 7890")

        host_port_layout.addWidget(host_label)
        host_port_layout.addWidget(host_input, 3)
        host_port_layout.addWidget(port_label)
        host_port_layout.addWidget(port_input, 1)

        proxy_settings_layout.addLayout(host_port_layout)

        # 用户名密码（可选）
        auth_layout = QHBoxLayout()

        username_label = QLabel("用户名:")
        username_input = QLineEdit(username)
        username_input.setPlaceholderText("可选")

        password_label = QLabel("密码:")
        password_input = QLineEdit(password)
        password_input.setPlaceholderText("可选")
        password_input.setEchoMode(QLineEdit.Password)

        auth_layout.addWidget(username_label)
        auth_layout.addWidget(username_input)
        auth_layout.addWidget(password_label)
        auth_layout.addWidget(password_input)

        proxy_settings_layout.addLayout(auth_layout)

        proxy_settings_group.setLayout(proxy_settings_layout)
        form_layout.addWidget(proxy_settings_group)

        # 说明文本
        help_text = QLabel("代理设置将用于所有API请求。如果不确定，请保持默认设置。")
        help_text.setWordWrap(True)
        form_layout.addWidget(help_text)

        layout.addLayout(form_layout)

        # 保存按钮
        save_btn = QPushButton("保存设置")
        layout.addWidget(save_btn)

        # 更新UI启用状态
        def update_ui_state():
            enabled = not no_proxy_radio.isChecked()
            proxy_settings_group.setEnabled(enabled)

        # 连接信号
        no_proxy_radio.toggled.connect(update_ui_state)
        http_proxy_radio.toggled.connect(update_ui_state)
        socks5_proxy_radio.toggled.connect(update_ui_state)

        # 保存设置
        def save_settings():
            settings = {
                "enabled": str(not no_proxy_radio.isChecked()),
                "type": "socks5" if socks5_proxy_radio.isChecked() else "http",
                "host": host_input.text().strip(),
                "port": port_input.text().strip(),
                "username": username_input.text().strip(),
                "password": password_input.text()
            }

            # 验证设置
            if settings["enabled"].lower() == "true":
                if not settings["host"]:
                    QMessageBox.warning(self, "错误", "请输入代理主机地址")
                    return

                if not settings["port"]:
                    QMessageBox.warning(self, "错误", "请输入代理端口")
                    return

            # 保存设置
            save_proxy_settings(settings, service_name)
            QMessageBox.information(self, "成功", f"{service_name.capitalize()}代理设置已保存")

        save_btn.clicked.connect(save_settings)

        # 初始化UI状态
        update_ui_state()

        return tab


class APIKeyDialog(QDialog):
    """API密钥管理对话框"""

    def __init__(self, parent=None, service="groq"):
        super().__init__(parent)
        self.parent_window = parent
        self.service = service

        title_text = "Groq API密钥管理" if service == "groq" else "Deepgram API密钥管理"
        self.setWindowTitle(title_text)
        self.setMinimumSize(550, 350)

        layout = QVBoxLayout(self)

        # 顶部说明
        info_label = QLabel(title_text)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        # 密钥列表
        self.key_list = QListWidget()
        layout.addWidget(self.key_list)

        # 新建密钥表单
        new_key_group = QGroupBox("添加新密钥")
        new_key_layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_label = QLabel("名称:")
        self.key_name_input = QLineEdit()
        self.key_name_input.setPlaceholderText("为密钥指定一个名称 (可选)")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.key_name_input)

        key_layout = QHBoxLayout()
        key_label = QLabel("密钥:")
        self.key_value_input = QLineEdit()

        key_prefix = "gsk_" if service == "groq" else ""
        self.key_value_input.setPlaceholderText(f"输入{title_text}，{key_prefix}开头")

        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_value_input)

        new_key_layout.addLayout(name_layout)
        new_key_layout.addLayout(key_layout)

        new_key_group.setLayout(new_key_layout)
        layout.addWidget(new_key_group)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_key)

        self.remove_btn = QPushButton("删除所选")
        self.remove_btn.clicked.connect(self.remove_key)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # 初始化完所有控件后再刷新密钥列表
        self.refresh_keys()

    def refresh_keys(self):
        """刷新密钥列表"""
        self.key_list.clear()
        keys = get_api_keys(self.service)

        for name, key in keys.items():
            masked_key = f"{key[:5]}...{key[-4:]}" if len(key) > 10 else key
            item_text = f"{name}: {masked_key}" if name != key else masked_key
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, (name, key))
            self.key_list.addItem(item)

        # 更新删除按钮状态
        self.remove_btn.setEnabled(self.key_list.count() > 0)

    def add_key(self):
        """添加新密钥"""
        name = self.key_name_input.text().strip()
        key = self.key_value_input.text().strip()

        if not key:
            QMessageBox.warning(self, "错误", "请输入API密钥")
            return

        key_prefix = "gsk_" if self.service == "groq" else ""
        if key_prefix and not key.startswith(key_prefix):
            QMessageBox.warning(self, "错误", f"{self.service.capitalize()} API密钥通常以{key_prefix}开头")
            return

        # 如果未提供名称，使用密钥值作为名称
        if not name:
            name = key

        # 添加密钥
        add_api_key(name, key, self.service)

        # 清空输入框
        self.key_name_input.clear()
        self.key_value_input.clear()

        # 刷新列表
        self.refresh_keys()

        # 同时刷新主窗口的密钥列表
        if self.parent_window and hasattr(self.parent_window, 'load_api_keys'):
            self.parent_window.load_api_keys()

    def remove_key(self):
        """删除所选密钥"""
        selected_items = self.key_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        name, _ = item.data(Qt.UserRole)

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除这个API密钥吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            remove_api_key(name, self.service)
            self.refresh_keys()

            # 同时刷新主窗口的密钥列表
            if self.parent_window and hasattr(self.parent_window, 'load_api_keys'):
                self.parent_window.load_api_keys()


class DependencyCheckerDialog(QDialog):
    """依赖检查对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("依赖检查")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # 依赖状态显示
        status_group = QGroupBox("依赖状态")
        status_layout = QVBoxLayout()

        self.groq_status = QLabel("Groq SDK: 正在检查...")
        self.deepgram_status = QLabel("Deepgram SDK: 正在检查...")
        self.httpx_status = QLabel("HTTPX: 正在检查...")
        self.httpx_socks_status = QLabel("HTTPX-SOCKS: 正在检查...")

        status_layout.addWidget(self.groq_status)
        status_layout.addWidget(self.deepgram_status)
        status_layout.addWidget(self.httpx_status)
        status_layout.addWidget(self.httpx_socks_status)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # 详细信息区域
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("检查依赖中...")
        layout.addWidget(self.details_text)

        # 安装提示
        help_text = QLabel(
            "请使用以下命令安装缺失的依赖:\n\n"
            "pip install groq  # Groq API客户端\n"
            "pip install deepgram-sdk  # Deepgram API客户端\n"
            "pip install httpx  # HTTP客户端\n"
            "pip install httpx-socks  # SOCKS代理支持\n"
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # 按钮
        button_layout = QHBoxLayout()
        self.check_btn = QPushButton("重新检查")
        self.check_btn.clicked.connect(self.check_dependencies)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)

        button_layout.addWidget(self.check_btn)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # 检查依赖
        self.check_dependencies()

    def check_dependencies(self):
        """检查依赖"""
        self.details_text.clear()

        try:
            # 尝试获取诊断信息
            from api_clients import get_diagnostics
            diagnostics = get_diagnostics()

            # 添加诊断信息到详细区域
            if 'debug_info' in diagnostics:
                self.details_text.append("=== 详细诊断信息 ===\n")
                for line in diagnostics['debug_info']:
                    self.details_text.append(line)

            # 更新状态标签
            groq_available = diagnostics.get('groq_available', False)
            self.groq_status.setText(f"Groq SDK: {'已安装' if groq_available else '未安装'}")
            self.groq_status.setStyleSheet("color: green" if groq_available else "color: red")

            deepgram_available = diagnostics.get('deepgram_available', False)
            self.deepgram_status.setText(f"Deepgram SDK: {'已安装' if deepgram_available else '未安装'}")
            self.deepgram_status.setStyleSheet("color: green" if deepgram_available else "color: red")

            httpx_available = diagnostics.get('httpx_available', False)
            self.httpx_status.setText(f"HTTPX: {'已安装' if httpx_available else '未安装'}")
            self.httpx_status.setStyleSheet("color: green" if httpx_available else "color: red")

            socks_available = diagnostics.get('socks_available', False)
            self.httpx_socks_status.setText(f"HTTPX-SOCKS: {'已安装' if socks_available else '未安装'}")
            self.httpx_socks_status.setStyleSheet("color: green" if socks_available else "color: red")

        except ImportError:
            # 如果没有get_diagnostics函数，使用传统方法检查
            try:
                import groq
                self.groq_status.setText("Groq SDK: 已安装")
                self.groq_status.setStyleSheet("color: green")
                self.details_text.append(f"Groq SDK版本: {getattr(groq, '__version__', '未知')}")
                self.details_text.append(f"Groq SDK位置: {getattr(groq, '__file__', '未知')}")
            except ImportError:
                self.groq_status.setText("Groq SDK: 未安装")
                self.groq_status.setStyleSheet("color: red")
                self.details_text.append("Groq SDK未安装")

            try:
                import deepgram
                self.deepgram_status.setText("Deepgram SDK: 已安装")
                self.deepgram_status.setStyleSheet("color: green")
            except ImportError:
                self.deepgram_status.setText("Deepgram SDK: 未安装")
                self.deepgram_status.setStyleSheet("color: red")

            try:
                import httpx
                self.httpx_status.setText("HTTPX: 已安装")
                self.httpx_status.setStyleSheet("color: green")
            except ImportError:
                self.httpx_status.setText("HTTPX: 未安装")
                self.httpx_status.setStyleSheet("color: red")

            try:
                import httpx_socks
                self.httpx_socks_status.setText("HTTPX-SOCKS: 已安装")
                self.httpx_socks_status.setStyleSheet("color: green")
            except ImportError:
                self.httpx_socks_status.setText("HTTPX-SOCKS: 未安装")
                self.httpx_socks_status.setStyleSheet("color: red")

        except Exception as e:
            self.details_text.append(f"检查依赖时出错: {str(e)}")


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)

        # 应用名称
        app_name = QLabel("音频转文本/SRT工具")
        app_name.setAlignment(Qt.AlignCenter)
        font = app_name.font()
        font.setPointSize(16)
        font.setBold(True)
        app_name.setFont(font)
        layout.addWidget(app_name)

        # 版本信息
        version = QLabel("版本: 1.0.0")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        # 说明
        description = QLabel(
            "这是一个基于AI的音频转文本/SRT工具，支持多种API服务和代理设置。\n\n"
            "支持的服务:\n"
            "- Groq Whisper API\n"
            "- Deepgram API (开发中)\n\n"
            "支持的功能:\n"
            "- 多文件批处理\n"
            "- SRT字幕和纯文本输出\n"
            "- HTTP和SOCKS5代理支持\n"
            "- 多语言支持"
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)

        # 作者信息
        author = QLabel("作者: AI音频处理工具开发团队")
        author.setAlignment(Qt.AlignCenter)
        layout.addWidget(author)

        # 关闭按钮
        button_layout = QHBoxLayout()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)