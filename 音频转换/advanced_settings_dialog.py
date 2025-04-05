from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QDoubleSpinBox, QSpinBox, QPushButton, QGroupBox,
                               QCheckBox, QSlider, QTabWidget, QWidget)
from PySide6.QtCore import Qt


class AdvancedSettingsDialog(QDialog):
    """音频分割高级设置对话框"""

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("音频分割高级设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)
        
        # 默认设置
        self.default_settings = {
            'use_silence_detection': True,
            'silence_threshold': -40,  # dB
            'silence_duration': 0.5,   # 秒
            'max_offset': 60,          # 秒
            'min_segment_length': 30   # 秒
        }
        
        # 使用提供的设置或默认设置
        self.settings = settings or self.default_settings.copy()
        
        # 创建界面
        self.setup_ui()
    
    def setup_ui(self):
        """设置对话框界面"""
        main_layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # ===== 基本选项卡 =====
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # 智能分割开关
        self.use_silence_check = QCheckBox("启用智能分割（在静音点切分）")
        self.use_silence_check.setChecked(self.settings['use_silence_detection'])
        self.use_silence_check.toggled.connect(self.update_ui_state)
        basic_layout.addWidget(self.use_silence_check)
        
        # 分割设置组
        split_group = QGroupBox("分割设置")
        split_layout = QVBoxLayout()
        
        # 最大偏移量
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("最大偏移时长(秒):"))
        self.max_offset_spin = QSpinBox()
        self.max_offset_spin.setRange(1, 300)
        self.max_offset_spin.setValue(self.settings['max_offset'])
        self.max_offset_spin.setToolTip("在理想分割点附近搜索静音的最大范围（秒）")
        offset_layout.addWidget(self.max_offset_spin)
        split_layout.addLayout(offset_layout)
        
        # 最小段长度
        min_length_layout = QHBoxLayout()
        min_length_layout.addWidget(QLabel("最小段长度(秒):"))
        self.min_segment_spin = QSpinBox()
        self.min_segment_spin.setRange(1, 300)
        self.min_segment_spin.setValue(self.settings['min_segment_length'])
        self.min_segment_spin.setToolTip("每段的最小长度，防止过短片段")
        min_length_layout.addWidget(self.min_segment_spin)
        split_layout.addLayout(min_length_layout)
        
        split_group.setLayout(split_layout)
        basic_layout.addWidget(split_group)
        
        # ===== 高级选项卡 =====
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        
        # 静音检测组
        silence_group = QGroupBox("静音检测参数")
        silence_layout = QVBoxLayout()
        
        # 静音阈值
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("静音阈值(dB):"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(-70, -10)
        self.threshold_slider.setValue(self.settings['silence_threshold'])
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(5)
        
        self.threshold_label = QLabel(f"{self.settings['silence_threshold']}dB")
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_label.setText(f"{v}dB"))
        
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_label)
        silence_layout.addLayout(threshold_layout)
        
        threshold_help = QLabel("较高的值(-20dB)会检测较大的声音，较低的值(-60dB)只会检测非常安静的部分")
        threshold_help.setWordWrap(True)
        silence_layout.addWidget(threshold_help)
        
        # 静音持续时间
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("静音持续时间(秒):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 5.0)
        self.duration_spin.setSingleStep(0.1)
        self.duration_spin.setValue(self.settings['silence_duration'])
        self.duration_spin.setToolTip("静音需要持续多长时间才会被识别为一个有效的静音点")
        duration_layout.addWidget(self.duration_spin)
        silence_layout.addLayout(duration_layout)
        
        silence_group.setLayout(silence_layout)
        advanced_layout.addWidget(silence_group)
        
        # 添加选项卡
        tab_widget.addTab(basic_tab, "基本设置")
        tab_widget.addTab(advanced_tab, "高级设置")
        main_layout.addWidget(tab_widget)
        
        # 重置按钮
        reset_button = QPushButton("重置为默认值")
        reset_button.clicked.connect(self.reset_to_defaults)
        main_layout.addWidget(reset_button)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)
        
        # 更新UI状态
        self.update_ui_state()
    
    def update_ui_state(self):
        """根据是否启用智能分割更新UI状态"""
        enabled = self.use_silence_check.isChecked()
        self.max_offset_spin.setEnabled(enabled)
        self.threshold_slider.setEnabled(enabled)
        self.duration_spin.setEnabled(enabled)
    
    def reset_to_defaults(self):
        """重置所有设置为默认值"""
        self.use_silence_check.setChecked(self.default_settings['use_silence_detection'])
        self.max_offset_spin.setValue(self.default_settings['max_offset'])
        self.min_segment_spin.setValue(self.default_settings['min_segment_length'])
        self.threshold_slider.setValue(self.default_settings['silence_threshold'])
        self.duration_spin.setValue(self.default_settings['silence_duration'])
    
    def get_settings(self):
        """获取当前设置"""
        return {
            'use_silence_detection': self.use_silence_check.isChecked(),
            'silence_threshold': self.threshold_slider.value(),
            'silence_duration': self.duration_spin.value(),
            'max_offset': self.max_offset_spin.value(),
            'min_segment_length': self.min_segment_spin.value()
        }
