import os
import sys
import json
import traceback
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog,
                               QMessageBox, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QComboBox, QLineEdit,
                               QTextEdit, QProgressBar, QCheckBox, QGroupBox,
                               QRadioButton, QSpinBox, QDialog, QFormLayout,
                               QButtonGroup)
from PySide6.QtCore import Qt, QThread, Signal, QCoreApplication, QFile, QResource
from PySide6.QtGui import QIcon, QFont

# 导入核心模块中的变量和函数
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from audio_to_srt_core import (transcribe_audio, transcribe_audio_to_srt,
                               supported_models, supported_languages, supported_formats,
                               GROQ_API_URL, get_api_keys, add_api_key, remove_api_key,
                               get_proxy_settings, save_proxy_settings,
                               get_output_format, save_output_format,
                               get_last_used_key, save_last_used_key)


class ProxySettingsDialog(QDialog):
    """代理设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理设置")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # 代理设置表单
        form_layout = QFormLayout()
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("例如: socks5://127.0.0.1:7890")
        self.proxy_input.setText(get_proxy_settings())
        form_layout.addRow("代理地址:", self.proxy_input)

        # 说明文本
        help_text = QLabel("设置代理格式示例:\n - HTTP代理: http://127.0.0.1:7890\n - SOCKS5代理: socks5://127.0.0.1:7890\n\n留空表示不使用代理")
        help_text.setWordWrap(True)

        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(form_layout)
        layout.addWidget(help_text)
        layout.addLayout(button_layout)

    def save_settings(self):
        """保存设置并关闭对话框"""
        proxy = self.proxy_input.text().strip()
        save_proxy_settings(proxy)
        self.accept()


class APIKeyDialog(QDialog):
    """API密钥管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API密钥管理")
        self.setMinimumSize(500, 300)
        self.parent_window = parent

        layout = QVBoxLayout(self)

        # 顶部说明
        info_label = QLabel("管理Groq API密钥")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        # 密钥列表
        self.key_list = QComboBox()
        layout.addWidget(self.key_list)

        # 新建密钥表单
        new_key_group = QGroupBox("添加新密钥")
        new_key_layout = QFormLayout()

        self.key_name_input = QLineEdit()
        self.key_name_input.setPlaceholderText("为密钥指定一个名称 (可选)")

        self.key_value_input = QLineEdit()
        self.key_value_input.setPlaceholderText("输入Groq API密钥，以gsk_开头")

        new_key_layout.addRow("名称:", self.key_name_input)
        new_key_layout.addRow("密钥:", self.key_value_input)

        new_key_group.setLayout(new_key_layout)
        layout.addWidget(new_key_group)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_key)

        self.remove_btn = QPushButton("删除所选")
        self.remove_btn.clicked.connect(self.remove_key)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # 初始化完所有控件后再刷新密钥列表
        self.refresh_keys()

    def refresh_keys(self):
        """刷新密钥列表"""
        self.key_list.clear()
        keys = get_api_keys()
        for name, key in keys.items():
            display_text = f"{name}: {key[:5]}...{key[-4:]}" if name != key else f"{key[:5]}...{key[-4:]}"
            self.key_list.addItem(display_text, (name, key))

        # 更新删除按钮状态
        self.remove_btn.setEnabled(self.key_list.count() > 0)

    def add_key(self):
        """添加新密钥"""
        name = self.key_name_input.text().strip()
        key = self.key_value_input.text().strip()

        if not key:
            QMessageBox.warning(self, "错误", "请输入API密钥")
            return

        if not key.startswith("gsk_"):
            QMessageBox.warning(self, "错误", "Groq API密钥通常以gsk_开头")
            return

        # 如果未提供名称，使用密钥值作为名称
        if not name:
            name = key

        # 添加密钥
        add_api_key(name, key)

        # 清空输入框
        self.key_name_input.clear()
        self.key_value_input.clear()

        # 刷新列表
        self.refresh_keys()

        # 同时刷新主窗口的密钥列表
        if self.parent_window:
            self.parent_window.load_api_keys()

    def remove_key(self):
        """删除所选密钥"""
        if self.key_list.currentIndex() < 0:
            return

        name, _ = self.key_list.currentData()

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除这个API密钥吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            remove_api_key(name)
            self.refresh_keys()

            # 同时刷新主窗口的密钥列表
            if self.parent_window:
                self.parent_window.load_api_keys()

    def refresh_keys(self):
        """刷新密钥列表"""
        self.key_list.clear()
        keys = get_api_keys()
        for name, key in keys.items():
            display_text = f"{name}: {key[:5]}...{key[-4:]}" if name != key else f"{key[:5]}...{key[-4:]}"
            self.key_list.addItem(display_text, (name, key))

        # 更新删除按钮状态
        self.remove_btn.setEnabled(self.key_list.count() > 0)

    def add_key(self):
        """添加新密钥"""
        name = self.key_name_input.text().strip()
        key = self.key_value_input.text().strip()

        if not key:
            QMessageBox.warning(self, "错误", "请输入API密钥")
            return

        if not key.startswith("gsk_"):
            QMessageBox.warning(self, "错误", "Groq API密钥通常以gsk_开头")
            return

        # 如果未提供名称，使用密钥值作为名称
        if not name:
            name = key

        # 添加密钥
        add_api_key(name, key)

        # 清空输入框
        self.key_name_input.clear()
        self.key_value_input.clear()

        # 刷新列表
        self.refresh_keys()

    def remove_key(self):
        """删除所选密钥"""
        if self.key_list.currentIndex() < 0:
            return

        name, _ = self.key_list.currentData()

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除这个API密钥吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            remove_api_key(name)
            self.refresh_keys()


class TranscriptionWorker(QThread):
    """后台转写工作线程"""
    finished = Signal(list)  # 成功信号，返回生成的文件路径列表
    error = Signal(str)  # 错误信号，返回错误信息
    progress = Signal(int)  # 进度信号，0-100
    warning = Signal(str)  # 警告信号，返回警告信息

    def __init__(self, audio_file, api_key, model, language, auto_detect, output_format, max_size):
        super().__init__()
        self.audio_file = audio_file
        self.api_key = api_key
        self.model = model
        self.language = None if auto_detect else language
        self.auto_detect = auto_detect
        self.output_format = output_format
        self.max_size = max_size

    def run(self):
        try:
            # 检查是否安装了requests库
            try:
                import requests
            except ImportError:
                try:
                    import pip
                    self.progress.emit(5)
                    pip.main(['install', 'requests'])
                    self.progress.emit(10)
                    import requests
                except Exception as e:
                    error_msg = "错误: 无法安装必要的依赖包 'requests'。请手动安装: pip install requests"
                    self.error.emit(error_msg)
                    return

            # 进度更新
            self.progress.emit(15)

            # 设置环境变量
            os.environ["GROQ_API_KEY"] = self.api_key

            # 生成输出文件路径
            base_name = os.path.splitext(self.audio_file)[0]
            extension = ".srt" if self.output_format == "srt" else ".txt"
            output_path = f"{base_name}{extension}"

            # 检查文件是否已存在，如果存在则重命名
            counter = 1
            while os.path.exists(output_path):
                output_path = f"{base_name}_{counter}{extension}"
                counter += 1

            self.progress.emit(20)

            # 保存最后使用的API密钥
            save_last_used_key(self.api_key)

            # 保存输出格式设置
            save_output_format(self.output_format)

            # 调用转写函数
            output_paths = transcribe_audio(
                audio_file_path=self.audio_file,
                output_path=output_path,
                model=self.model,
                language=self.language,
                output_format=self.output_format,
                progress_callback=self.update_progress,
                max_segment_size=self.max_size
            )

            self.progress.emit(100)
            self.finished.emit(output_paths)

        except Exception as e:
            error_msg = f"错误: {str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(error_msg)

    def update_progress(self, stage, percentage):
        """更新进度条，根据不同阶段调整进度"""
        if stage == "uploading":
            # 上传阶段占20%到40%
            progress = 20 + int(percentage * 0.2)
            self.progress.emit(progress)
        elif stage == "processing":
            # 处理阶段占40%到90%
            progress = 40 + int(percentage * 0.5)
            self.progress.emit(progress)
        elif stage == "downloading":
            # 下载和保存阶段占90%到100%
            progress = 90 + int(percentage * 0.1)
            self.progress.emit(progress)
        elif stage == "warning":
            # 发出警告信号
            self.warning.emit("使用SOCKS代理需要安装PySocks库。请使用pip install PySocks命令安装后再尝试。")
        elif stage == "error":
            # 发出错误信号
            self.error.emit("代理设置错误，请检查代理配置。")
        else:
            return


class AudioToSrtGUI(QMainWindow):
    """音频转SRT字幕GUI主窗口"""

    def __init__(self):
        super().__init__()

        # 设置窗口属性
        self.setWindowTitle("音频转SRT/文本工具")
        self.setMinimumSize(650, 550)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 标题
        title_label = QLabel("音频转SRT/文本工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # ----------------- API密钥设置 -----------------
        api_group = QGroupBox("API设置")
        api_layout = QVBoxLayout()

        api_key_layout = QHBoxLayout()
        api_label = QLabel("Groq API密钥:")

        # 改为下拉列表选择API密钥
        self.api_key_combo = QComboBox()
        self.api_key_combo.setEditable(True)
        self.api_key_combo.setMinimumWidth(300)

        # 管理密钥按钮
        api_manage_btn = QPushButton("管理密钥")
        api_manage_btn.clicked.connect(self.open_api_key_manager)

        api_key_layout.addWidget(api_label)
        api_key_layout.addWidget(self.api_key_combo, 1)
        api_key_layout.addWidget(api_manage_btn)

        # 代理设置
        proxy_layout = QHBoxLayout()
        proxy_label = QLabel("代理设置:")
        self.proxy_status = QLabel("未设置")
        proxy_btn = QPushButton("设置代理")
        proxy_btn.clicked.connect(self.open_proxy_settings)

        proxy_layout.addWidget(proxy_label)
        proxy_layout.addWidget(self.proxy_status, 1)
        proxy_layout.addWidget(proxy_btn)

        api_layout.addLayout(api_key_layout)
        api_layout.addLayout(proxy_layout)
        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)

        # ----------------- 模型设置 -----------------
        model_group = QGroupBox("转写设置")
        model_layout = QVBoxLayout()

        # 模型选择
        model_select_layout = QHBoxLayout()
        model_label = QLabel("选择模型:")
        self.model_combo = QComboBox()
        for model_id, model_info in supported_models.items():
            self.model_combo.addItem(f"{model_info['name']} - {model_info['description']}", model_id)
        model_select_layout.addWidget(model_label)
        model_select_layout.addWidget(self.model_combo)

        # 语言选择
        lang_layout = QHBoxLayout()
        lang_label = QLabel("选择语言:")
        self.lang_combo = QComboBox()
        for lang_code, lang_name in supported_languages.items():
            self.lang_combo.addItem(lang_name, lang_code)
        self.auto_detect_lang = QCheckBox("自动检测语言")
        self.auto_detect_lang.setChecked(True)
        self.auto_detect_lang.stateChanged.connect(self.toggle_language_combo)
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addWidget(self.auto_detect_lang)

        # 输出格式
        format_layout = QHBoxLayout()
        format_label = QLabel("输出格式:")
        self.format_group = QButtonGroup(self)

        for format_id, format_desc in supported_formats.items():
            radio_btn = QRadioButton(format_desc)
            if format_id == get_output_format():
                radio_btn.setChecked(True)
            self.format_group.addButton(radio_btn, id=list(supported_formats.keys()).index(format_id))
            format_layout.addWidget(radio_btn)

        model_layout.addLayout(model_select_layout)
        model_layout.addLayout(lang_layout)
        model_layout.addLayout(format_layout)
        model_group.setLayout(model_layout)
        main_layout.addWidget(model_group)

        # 文件选择
        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout()
        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setWordWrap(True)
        self.select_file_btn = QPushButton("选择音频文件")
        self.select_file_btn.clicked.connect(self.select_audio_file)
        file_layout.addWidget(self.file_path_label)
        file_layout.addWidget(self.select_file_btn)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # 转换按钮
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setEnabled(False)
        main_layout.addWidget(self.convert_btn)

        # 日志区域
        log_label = QLabel("日志输出:")
        main_layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)

        # 初始化变量
        self.audio_file_path = None
        self.worker = None

        # 加载设置
        self.load_api_keys()
        self.load_proxy_settings()

    def load_api_keys(self):
        """从配置文件加载API密钥"""
        # 清空当前密钥列表
        self.api_key_combo.clear()

        # 获取所有API密钥
        keys = get_api_keys()

        for name, key in keys.items():
            display_text = f"{name}: {key[:5]}...{key[-4:]}" if name != key else f"{key[:5]}...{key[-4:]}"
            self.api_key_combo.addItem(display_text, key)

        # 设置上次使用的密钥
        last_key = get_last_used_key()
        if last_key:
            for i in range(self.api_key_combo.count()):
                if self.api_key_combo.itemData(i) == last_key:
                    self.api_key_combo.setCurrentIndex(i)
                    break

        if self.api_key_combo.count() > 0:
            self.log(f"已加载 {self.api_key_combo.count()} 个API密钥")
        else:
            self.log("未找到API密钥，请点击'管理密钥'添加")

    def load_proxy_settings(self):
        """加载代理设置"""
        proxy = get_proxy_settings()
        if proxy:
            self.proxy_status.setText(proxy)
            self.log(f"已加载代理设置: {proxy}")
        else:
            self.proxy_status.setText("未设置")

    def open_api_key_manager(self):
        """打开API密钥管理器"""
        dialog = APIKeyDialog(self)
        # 不论对话框如何关闭，都重新加载密钥列表
        dialog.exec()
        # 强制刷新密钥列表
        self.load_api_keys()

    def open_proxy_settings(self):
        """打开代理设置对话框"""
        dialog = ProxySettingsDialog(self)
        if dialog.exec():
            self.load_proxy_settings()

    def toggle_language_combo(self, state):
        """切换语言选择下拉框的启用状态"""
        self.lang_combo.setEnabled(not state)

    def select_audio_file(self):
        """选择音频文件"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("音频文件 (*.mp3 *.mp4 *.wav *.m4a *.ogg *.opus *.webm *.mpeg *.mpga)")

        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            self.audio_file_path = file_paths[0]
            self.file_path_label.setText(self.audio_file_path)
            self.convert_btn.setEnabled(True)
            self.log("已选择文件: " + self.audio_file_path)

    def log(self, message):
        """添加日志消息"""
        self.log_text.append(message)
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start_conversion(self):
        """开始转换过程"""
        # 检查API密钥
        api_key = self.api_key_combo.currentData()
        if not api_key:
            api_key = self.api_key_combo.currentText().strip()

        if not api_key:
            QMessageBox.warning(self, "错误", "请选择或输入有效的Groq API密钥")
            return

        # 检查是否有选择文件
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            QMessageBox.warning(self, "错误", "请选择有效的音频文件")
            return

        # 获取其他设置
        model = self.model_combo.currentData()
        language = self.lang_combo.currentData()
        auto_detect = self.auto_detect_lang.isChecked()

        # 获取输出格式
        output_format = list(supported_formats.keys())[self.format_group.checkedId()]

        # 禁用界面元素
        self.convert_btn.setEnabled(False)
        self.select_file_btn.setEnabled(False)

        # 重置进度条
        self.progress_bar.setValue(0)

        # 日志
        self.log(f"开始转换: {os.path.basename(self.audio_file_path)}")
        self.log(f"使用模型: {model}")
        self.log(f"语言设置: {'自动检测' if auto_detect else language}")
        self.log(f"输出格式: {supported_formats[output_format]}")

        # 创建并启动工作线程
        self.worker = TranscriptionWorker(
            self.audio_file_path,
            api_key,
            model,
            language,
            auto_detect,
            output_format,
            None  # 移除了大文件拆分功能
        )

        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.error.connect(self.on_conversion_error)
        self.worker.warning.connect(self.on_conversion_warning)

        self.worker.start()

    def on_conversion_warning(self, warning_message):
        """处理转换过程中的警告"""
        self.log(f"警告: {warning_message}")

        # 显示警告消息
        QMessageBox.warning(self, "代理设置警告", warning_message)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def on_conversion_finished(self, file_paths):
        """转换完成处理"""
        # 输出结果
        if len(file_paths) == 1:
            self.log(f"转换完成! 文件已保存至: {file_paths[0]}")
        else:
            self.log(f"转换完成! 生成了{len(file_paths)}个文件:")
            for path in file_paths:
                self.log(f"  - {path}")

        # 重新启用界面元素
        self.convert_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)

        # 提示用户
        if len(file_paths) == 1:
            QMessageBox.information(
                self,
                "转换成功",
                f"音频转换完成!\n\n文件已保存至:\n{file_paths[0]}"
            )
        else:
            message = f"音频转换完成!\n\n共生成{len(file_paths)}个文件:\n"
            for path in file_paths[:3]:  # 只显示前3个，避免消息框太大
                message += f"- {path}\n"

            if len(file_paths) > 3:
                message += f"...(共{len(file_paths)}个文件)"

            QMessageBox.information(self, "转换成功", message)

    def on_conversion_error(self, error_message):
        """转换错误处理"""
        self.log(f"转换失败: {error_message}")

        # 重新启用界面元素
        self.convert_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)

        # 进度条重置
        self.progress_bar.setValue(0)

        # 显示错误消息
        error_dialog = QMessageBox(self)
        error_dialog.setWindowTitle("转换错误")
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText("转换过程中发生错误")
        error_dialog.setDetailedText(error_message)
        error_dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle("Fusion")

    window = AudioToSrtGUI()
    window.show()

    sys.exit(app.exec())