import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QClipboard

class TextMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文本合并工具")
        self.resize(800, 600)
        
        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        
        # 默认标签文本
        self.default_labels = [
            "===确定为AI开始===", 
            "===确定为AI结束===", 
            "===疑似AI开始===", 
            "===疑似AI结束===", 
            "===确定为人工开始===", 
            "===确定为人工结束==="
        ]
        
        # 从配置文件加载或使用默认值
        self.labels = self.load_config()
        
        # 设置中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建三组文本编辑区
        self.text_areas = []
        self.label_inputs = []
        
        for i in range(3):
            group_layout = QVBoxLayout()
            
            # 创建两个标签输入框
            label_layout = QHBoxLayout()
            
            start_label = QLabel("开始标签:")
            self.label_inputs.append(QLineEdit(self.labels[i*2]))
            self.label_inputs[-1].textChanged.connect(lambda text, idx=i*2: self.update_label(idx, text))
            
            end_label = QLabel("结束标签:")
            self.label_inputs.append(QLineEdit(self.labels[i*2+1]))
            self.label_inputs[-1].textChanged.connect(lambda text, idx=i*2+1: self.update_label(idx, text))
            
            label_layout.addWidget(start_label)
            label_layout.addWidget(self.label_inputs[-2])
            label_layout.addWidget(end_label)
            label_layout.addWidget(self.label_inputs[-1])
            
            group_layout.addLayout(label_layout)
            
            # 创建大文本框
            text_edit = QTextEdit()
            text_edit.setPlaceholderText(f"在此处粘贴文本 {i+1}")
            self.text_areas.append(text_edit)
            group_layout.addWidget(text_edit)
            
            main_layout.addLayout(group_layout)
        
        # 创建输出按钮
        output_button = QPushButton("合并并复制到剪贴板")
        output_button.clicked.connect(self.merge_and_copy)
        main_layout.addWidget(output_button)
    
    def load_config(self):
        """从配置文件加载标签，如果不存在则使用默认值"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self.default_labels
        except Exception as e:
            print(f"加载配置文件出错: {e}")
            return self.default_labels
    
    def save_config(self):
        """保存当前标签到配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.labels, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存配置文件出错: {e}")
    
    @Slot(int, str)
    def update_label(self, index, text):
        """更新标签并保存配置"""
        self.labels[index] = text
        self.save_config()
    
    @Slot()
    def merge_and_copy(self):
        """合并文本并复制到剪贴板"""
        result = ""
        
        for i in range(3):
            start_label = self.labels[i*2]
            end_label = self.labels[i*2+1]
            content = self.text_areas[i].toPlainText()
            
            result += f"{start_label}{content}{end_label}"
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(result)
        
        # 显示成功提示（可以改为状态栏或对话框）
        self.statusBar().showMessage("已成功复制到剪贴板", 3000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextMergerApp()
    window.show()
    sys.exit(app.exec())
