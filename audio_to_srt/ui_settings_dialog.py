from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QGroupBox, QRadioButton, QLineEdit, QFormLayout,
    QSlider
)
from PySide6.QtCore import Qt, Signal
import json

from config_manager import (
    save_conversion_settings, get_conversion_settings
)


class ConversionSettingsDialog(QDialog):
    """转换设置对话框"""
    settings_changed = Signal()  # 设置变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("转换设置")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self.current_service = "groq"  # 默认服务
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.groq_tab = self.create_groq_tab()
        self.deepgram_tab = self.create_deepgram_tab()

        self.tab_widget.addTab(self.groq_tab, "Groq设置")
        self.tab_widget.addTab(self.deepgram_tab, "Deepgram设置")

        layout.addWidget(self.tab_widget)

        # 底部按钮区域
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存设置")
        self.save_btn.clicked.connect(self.save_settings)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def create_groq_tab(self):
        """创建Groq设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ===== 模型选择区域 =====
        model_group = QGroupBox("模型选择")
        model_layout = QVBoxLayout()

        model_form = QFormLayout()
        self.groq_model_combo = QComboBox()
        self.groq_model_combo.addItem("whisper-large-v3", "whisper-large-v3")
        self.groq_model_combo.addItem("whisper-medium", "whisper-medium")

        model_form.addRow("转写模型:", self.groq_model_combo)
        model_layout.addLayout(model_form)

        # 添加模型说明
        model_description = QLabel(
            "whisper-large-v3: 更高准确度，支持多种语言\n"
            "whisper-medium: 速度更快，准确度适中"
        )
        model_description.setStyleSheet("color: gray;")
        model_layout.addWidget(model_description)

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # ===== 高级选项区域 =====
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QFormLayout()

        # 时间戳精度
        self.groq_timestamps_combo = QComboBox()
        self.groq_timestamps_combo.addItem("标准精度", "granular")
        self.groq_timestamps_combo.addItem("高精度", "word")
        advanced_layout.addRow("时间戳精度:", self.groq_timestamps_combo)

        # 检测语言
        self.groq_detect_lang_check = QCheckBox("自动检测语言")
        advanced_layout.addRow("语言检测:", self.groq_detect_lang_check)

        # 翻译选项
        self.groq_translate_check = QCheckBox("将音频翻译为所选语言")
        self.groq_translate_check.setChecked(False)
        advanced_layout.addRow("翻译:", self.groq_translate_check)

        # 温度设置
        self.groq_temperature_spin = QDoubleSpinBox()
        self.groq_temperature_spin.setRange(0.0, 1.0)
        self.groq_temperature_spin.setSingleStep(0.1)
        self.groq_temperature_spin.setValue(0.0)
        advanced_layout.addRow("温度:", self.groq_temperature_spin)

        # 分段选项
        self.groq_max_line_count = QSpinBox()
        self.groq_max_line_count.setRange(1, 5)
        self.groq_max_line_count.setValue(2)
        advanced_layout.addRow("字幕最大行数:", self.groq_max_line_count)

        # 每行最大字符数
        self.groq_max_line_width = QSpinBox()
        self.groq_max_line_width.setRange(30, 100)
        self.groq_max_line_width.setValue(42)
        advanced_layout.addRow("每行最大字符数:", self.groq_max_line_width)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()
        return tab

    def create_deepgram_tab(self):
        """创建Deepgram设置选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ===== 模型选择区域 =====
        model_group = QGroupBox("模型选择")
        model_layout = QFormLayout()

        self.dg_model_combo = QComboBox()
        self.dg_model_combo.addItem("nova-2", "nova-2")
        self.dg_model_combo.addItem("nova", "nova")
        self.dg_model_combo.addItem("enhanced", "enhanced")
        model_layout.addRow("转写模型:", self.dg_model_combo)

        # 模型版本
        self.dg_version_combo = QComboBox()
        self.dg_version_combo.addItem("最新版本", "latest")
        self.dg_version_combo.addItem("特定版本", "")
        model_layout.addRow("模型版本:", self.dg_version_combo)

        # 版本输入框
        self.dg_version_input = QLineEdit()
        self.dg_version_input.setPlaceholderText("留空使用最新版本")
        self.dg_version_input.setEnabled(False)
        model_layout.addRow("指定版本:", self.dg_version_input)

        # 连接版本选择和输入框
        self.dg_version_combo.currentIndexChanged.connect(
            lambda idx: self.dg_version_input.setEnabled(idx == 1)
        )

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # ===== 高级设置区域 =====
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QVBoxLayout()

        # === 功能设置 ===
        features_form = QFormLayout()

        # 智能格式化
        self.dg_smart_format_check = QCheckBox("启用")
        self.dg_smart_format_check.setChecked(True)
        features_form.addRow("智能格式化:", self.dg_smart_format_check)

        # 标点符号
        self.dg_punctuate_check = QCheckBox("启用")
        self.dg_punctuate_check.setChecked(True)
        features_form.addRow("自动标点:", self.dg_punctuate_check)

        # 说话人分离
        self.dg_diarize_check = QCheckBox("启用")
        features_form.addRow("说话人分离:", self.dg_diarize_check)

        # 语言检测
        self.dg_detect_language_check = QCheckBox("启用")
        self.dg_detect_language_check.setChecked(True)
        features_form.addRow("语言检测:", self.dg_detect_language_check)

        # 多通道
        self.dg_multichannel_check = QCheckBox("处理多声道")
        features_form.addRow("多声道:", self.dg_multichannel_check)

        # 关键词增强
        self.dg_keywords_input = QLineEdit()
        self.dg_keywords_input.setPlaceholderText("逗号分隔的关键词列表")
        features_form.addRow("关键词增强:", self.dg_keywords_input)

        advanced_layout.addLayout(features_form)

        # === 性能设置 ===
        performance_group = QGroupBox("性能设置")
        performance_layout = QFormLayout()

        # 处理精度
        self.dg_tier_combo = QComboBox()
        self.dg_tier_combo.addItem("标准", "base")
        self.dg_tier_combo.addItem("增强", "enhanced")
        performance_layout.addRow("处理精度:", self.dg_tier_combo)

        # 音频采样率
        self.dg_sample_rate_combo = QComboBox()
        self.dg_sample_rate_combo.addItem("自动", "")
        self.dg_sample_rate_combo.addItem("8 kHz", "8000")
        self.dg_sample_rate_combo.addItem("16 kHz", "16000")
        self.dg_sample_rate_combo.addItem("44.1 kHz", "44100")
        self.dg_sample_rate_combo.addItem("48 kHz", "48000")
        performance_layout.addRow("音频采样率:", self.dg_sample_rate_combo)

        performance_group.setLayout(performance_layout)
        advanced_layout.addWidget(performance_group)

        # === 输出格式设置 ===
        output_group = QGroupBox("输出设置")
        output_layout = QFormLayout()

        # 时间戳精度
        self.dg_timestamps_combo = QComboBox()
        self.dg_timestamps_combo.addItem("单词级", "word")
        self.dg_timestamps_combo.addItem("句子级", "sentence")
        output_layout.addRow("时间戳精度:", self.dg_timestamps_combo)

        # 置信度阈值
        self.dg_confidence_slider = QSlider(Qt.Horizontal)
        self.dg_confidence_slider.setRange(0, 100)
        self.dg_confidence_slider.setValue(70)
        self.dg_confidence_label = QLabel("0.7")
        self.dg_confidence_slider.valueChanged.connect(
            lambda v: self.dg_confidence_label.setText(f"{v / 100:.1f}")
        )
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(self.dg_confidence_slider)
        confidence_layout.addWidget(self.dg_confidence_label)
        output_layout.addRow("置信度阈值:", confidence_layout)

        output_group.setLayout(output_layout)
        advanced_layout.addWidget(output_group)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()
        return tab

    def set_service(self, service):
        """设置当前服务"""
        self.current_service = service
        if service == "groq":
            self.tab_widget.setCurrentIndex(0)
        else:
            self.tab_widget.setCurrentIndex(1)

    def load_settings(self):
        """加载设置"""
        settings = get_conversion_settings()

        # Groq设置
        groq_settings = settings.get("groq", {})

        # 模型
        model = groq_settings.get("model", "whisper-large-v3")
        index = self.groq_model_combo.findData(model)
        if index >= 0:
            self.groq_model_combo.setCurrentIndex(index)

        # 时间戳
        timestamps = groq_settings.get("timestamps", "granular")
        index = self.groq_timestamps_combo.findData(timestamps)
        if index >= 0:
            self.groq_timestamps_combo.setCurrentIndex(index)

        # 检测语言
        self.groq_detect_lang_check.setChecked(groq_settings.get("detect_language", True))

        # 翻译
        self.groq_translate_check.setChecked(groq_settings.get("translate", False))

        # 温度
        self.groq_temperature_spin.setValue(groq_settings.get("temperature", 0.0))

        # 字幕行数
        self.groq_max_line_count.setValue(groq_settings.get("max_line_count", 2))

        # 字符数
        self.groq_max_line_width.setValue(groq_settings.get("max_line_width", 42))

        # Deepgram设置
        dg_settings = settings.get("deepgram", {})

        # 模型
        model = dg_settings.get("model", "nova-2")
        index = self.dg_model_combo.findData(model)
        if index >= 0:
            self.dg_model_combo.setCurrentIndex(index)

        # 版本
        version = dg_settings.get("version", "")
        if version and version != "latest":
            self.dg_version_combo.setCurrentIndex(1)
            self.dg_version_input.setText(version)
            self.dg_version_input.setEnabled(True)
        else:
            self.dg_version_combo.setCurrentIndex(0)
            self.dg_version_input.setEnabled(False)

        # 智能格式化
        self.dg_smart_format_check.setChecked(dg_settings.get("smart_format", True))

        # 标点符号
        self.dg_punctuate_check.setChecked(dg_settings.get("punctuate", True))

        # 说话人分离
        self.dg_diarize_check.setChecked(dg_settings.get("diarize", False))

        # 语言检测
        self.dg_detect_language_check.setChecked(dg_settings.get("detect_language", True))

        # 多通道
        self.dg_multichannel_check.setChecked(dg_settings.get("multichannel", False))

        # 关键词
        self.dg_keywords_input.setText(dg_settings.get("keywords", ""))

        # 处理精度
        tier = dg_settings.get("tier", "base")
        index = self.dg_tier_combo.findData(tier)
        if index >= 0:
            self.dg_tier_combo.setCurrentIndex(index)

        # 采样率
        sample_rate = dg_settings.get("sample_rate", "")
        index = self.dg_sample_rate_combo.findData(str(sample_rate))
        if index >= 0:
            self.dg_sample_rate_combo.setCurrentIndex(index)

        # 时间戳
        timestamps = dg_settings.get("timestamps", "word")
        index = self.dg_timestamps_combo.findData(timestamps)
        if index >= 0:
            self.dg_timestamps_combo.setCurrentIndex(index)

        # 置信度
        confidence = dg_settings.get("confidence", 0.7)
        self.dg_confidence_slider.setValue(int(confidence * 100))
        self.dg_confidence_label.setText(f"{confidence:.1f}")

    def save_settings(self):
        """保存设置"""
        settings = get_conversion_settings()  # 获取当前设置

        # 更新Groq设置
        groq_settings = {}
        groq_settings["model"] = self.groq_model_combo.currentData()
        groq_settings["timestamps"] = self.groq_timestamps_combo.currentData()
        groq_settings["detect_language"] = self.groq_detect_lang_check.isChecked()
        groq_settings["translate"] = self.groq_translate_check.isChecked()
        groq_settings["temperature"] = self.groq_temperature_spin.value()
        groq_settings["max_line_count"] = self.groq_max_line_count.value()
        groq_settings["max_line_width"] = self.groq_max_line_width.value()

        settings["groq"] = groq_settings

        # 更新Deepgram设置
        dg_settings = {}
        dg_settings["model"] = self.dg_model_combo.currentData()

        # 版本
        if self.dg_version_combo.currentIndex() == 1 and self.dg_version_input.text():
            dg_settings["version"] = self.dg_version_input.text().strip()
        else:
            dg_settings["version"] = "latest"

        dg_settings["smart_format"] = self.dg_smart_format_check.isChecked()
        dg_settings["punctuate"] = self.dg_punctuate_check.isChecked()
        dg_settings["diarize"] = self.dg_diarize_check.isChecked()
        dg_settings["detect_language"] = self.dg_detect_language_check.isChecked()
        dg_settings["multichannel"] = self.dg_multichannel_check.isChecked()
        dg_settings["keywords"] = self.dg_keywords_input.text().strip()
        dg_settings["tier"] = self.dg_tier_combo.currentData()
        dg_settings["sample_rate"] = self.dg_sample_rate_combo.currentData()
        dg_settings["timestamps"] = self.dg_timestamps_combo.currentData()
        dg_settings["confidence"] = self.dg_confidence_slider.value() / 100.0

        settings["deepgram"] = dg_settings

        # 保存所有设置
        save_conversion_settings(settings)

        # 发出设置变更信号
        self.settings_changed.emit()

        self.accept()