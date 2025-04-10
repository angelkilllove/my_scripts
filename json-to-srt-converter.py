import sys
import os
import json
import re
from datetime import datetime
import configparser
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QTextEdit, QPushButton,
                               QFileDialog, QCheckBox, QListWidget, QGroupBox,
                               QLineEdit, QMessageBox, QGridLayout, QToolButton,
                               QInputDialog, QListWidgetItem)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class JsonToSrtConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON字幕转SRT转换器")
        self.setMinimumSize(800, 600)

        # 加载语言配置
        self.lang_config = self.load_language_config()

        # 初始化配置
        self.config = configparser.ConfigParser()
        self.config_file = "converter_settings.ini"
        self.load_settings()

        # 主部件和布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # 输入区域
        input_group = QGroupBox("输入JSON字幕")
        input_layout = QVBoxLayout()

        # 文件加载区域
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("拖拽JSON文件到此处或点击浏览按钮选择文件")
        self.file_path_edit.setReadOnly(True)

        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_button)

        # 文本输入区域
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("或在此处直接粘贴JSON文本")
        self.text_edit.setAcceptDrops(True)

        input_layout.addLayout(file_layout)
        input_layout.addWidget(self.text_edit)

        input_group.setLayout(input_layout)

        # 语言选择区域
        lang_group = QGroupBox("语言选择")
        lang_layout = QVBoxLayout()

        self.lang_list = QListWidget()
        # 从配置文件加载语言列表
        for lang in self.lang_config.get("languages", []):
            item_text = f"{lang['chinese_name']} ({lang['english_name']}/{lang['code']})"
            self.lang_list.addItem(item_text)

        self.lang_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

        # 默认选中第一项
        if self.lang_list.count() > 0:
            self.lang_list.item(0).setSelected(True)

        # 上移下移按钮
        button_layout = QHBoxLayout()
        up_button = QPushButton("上移")
        down_button = QPushButton("下移")
        up_button.clicked.connect(self.move_item_up)
        down_button.clicked.connect(self.move_item_down)

        button_layout.addWidget(up_button)
        button_layout.addWidget(down_button)

        lang_layout.addWidget(QLabel("选择要包含的语言并排序 (可多选):"))
        lang_layout.addWidget(self.lang_list)
        lang_layout.addLayout(button_layout)

        lang_group.setLayout(lang_layout)

        # 输出设置区域
        output_group = QGroupBox("输出设置")
        output_layout = QGridLayout()

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("输出文件夹路径")

        if self.last_output_path:
            self.output_path_edit.setText(self.last_output_path)

        output_browse = QToolButton()
        output_browse.setText("...")
        output_browse.clicked.connect(self.browse_output_path)

        self.save_settings_checkbox = QCheckBox("保存设置")
        self.save_settings_checkbox.setChecked(True)

        output_layout.addWidget(QLabel("输出路径:"), 0, 0)
        output_layout.addWidget(self.output_path_edit, 0, 1)
        output_layout.addWidget(output_browse, 0, 2)
        output_layout.addWidget(self.save_settings_checkbox, 1, 0, 1, 3)

        output_group.setLayout(output_layout)

        # 转换按钮
        convert_button = QPushButton("开始转换")
        convert_button.clicked.connect(self.convert)
        convert_button.setMinimumHeight(40)

        # 添加到主布局
        main_layout.addWidget(input_group)
        main_layout.addWidget(lang_group)
        main_layout.addWidget(output_group)
        main_layout.addWidget(convert_button)

        self.setCentralWidget(main_widget)

        # 设置拖放支持
        self.setAcceptDrops(True)

    def load_language_config(self):
        """加载语言配置文件"""
        config_path = "language_config.json"
        default_config = {
            "languages": [
                {
                    "code": "en",
                    "english_name": "English",
                    "chinese_name": "英文",
                    "alternatives": ["english", "eng"]
                },
                {
                    "code": "zh",
                    "english_name": "Chinese",
                    "chinese_name": "中文",
                    "alternatives": ["chinese", "zh-cn", "zh_cn", "cn"]
                }
            ]
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果文件不存在，创建默认配置文件
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                return default_config
        except Exception as e:
            print(f"加载语言配置出错: {str(e)}")
            return default_config

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                # 自动设置输出路径为文件所在文件夹
                self.output_path_edit.setText(os.path.dirname(file_path))

                # 尝试读取文件内容
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.text_edit.setText(content)
                        self.file_path_edit.setText(file_path)
                except Exception as e:
                    QMessageBox.warning(self, "读取错误", f"无法读取文件: {str(e)}")
        elif event.mimeData().hasText():
            # 如果拖拽的是文本内容
            self.text_edit.setText(event.mimeData().text())

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择JSON文件", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            self.file_path_edit.setText(file_path)
            # 自动设置输出路径为文件所在文件夹
            self.output_path_edit.setText(os.path.dirname(file_path))

            # 尝试读取文件内容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.text_edit.setText(f.read())
            except Exception as e:
                QMessageBox.warning(self, "读取错误", f"无法读取文件: {str(e)}")

    def browse_output_path(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹", self.output_path_edit.text())
        if folder_path:
            self.output_path_edit.setText(folder_path)

    def move_item_up(self):
        current_row = self.lang_list.currentRow()
        if current_row > 0:
            item = self.lang_list.takeItem(current_row)
            self.lang_list.insertItem(current_row - 1, item)
            self.lang_list.setCurrentRow(current_row - 1)

    def move_item_down(self):
        current_row = self.lang_list.currentRow()
        if current_row < self.lang_list.count() - 1:
            item = self.lang_list.takeItem(current_row)
            self.lang_list.insertItem(current_row + 1, item)
            self.lang_list.setCurrentRow(current_row + 1)

    def load_settings(self):
        self.last_output_path = ""
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file)
                if 'Settings' in self.config:
                    self.last_output_path = self.config.get('Settings', 'OutputPath', fallback="")
            except Exception as e:
                print(f"读取配置文件出错: {str(e)}")

    def save_settings(self):
        if not 'Settings' in self.config:
            self.config.add_section('Settings')

        self.config.set('Settings', 'OutputPath', self.output_path_edit.text())

        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
        except Exception as e:
            QMessageBox.warning(self, "保存设置出错", f"无法保存设置: {str(e)}")

    def get_language_code(self, text):
        """从列表项文本中提取语言代码"""
        # 从格式 "中文 (Chinese/zh)" 中提取 "zh"
        pattern = r"\(.*?/(\w+(-\w+)?)\)"
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return None

    def get_language_from_json(self, json_key):
        """识别JSON中的语言字段，返回标准代码"""
        # 检查是否直接匹配标准代码
        json_key = json_key.lower()

        for lang in self.lang_config.get("languages", []):
            if json_key == lang["code"]:
                return lang["code"]
            if json_key in lang.get("alternatives", []):
                return lang["code"]

        # 找不到匹配项，返回原始键值
        return json_key

    def format_time(self, time_str):
        # 处理数字类型时间（浮点数或整数）
        if isinstance(time_str, (int, float)):
            total_seconds = float(time_str)
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = total_seconds % 60
            milliseconds = int((seconds - int(seconds)) * 1000)
            seconds = int(seconds)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

        # 处理字符串类型的时间
        if isinstance(time_str, str):
            # 检查是否包含冒号（时:分:秒格式）
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:  # 分:秒
                    minutes, seconds = parts
                    hours = 0
                elif len(parts) == 3:  # 时:分:秒
                    hours, minutes, seconds = parts
                else:
                    return "00:00:00,000"  # 默认时间

                try:
                    hours = int(hours)
                    minutes = int(minutes)
                    seconds = float(seconds)

                    milliseconds = int((seconds - int(seconds)) * 1000)
                    seconds = int(seconds)

                    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
                except:
                    return "00:00:00,000"  # 失败时返回默认时间
            else:
                # 尝试解析简单的秒数
                try:
                    seconds = float(time_str)
                    hours = 0
                    minutes = int(seconds / 60)
                    seconds = seconds % 60
                    milliseconds = int((seconds - int(seconds)) * 1000)
                    seconds = int(seconds)

                    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
                except:
                    return "00:00:00,000"  # 默认时间

        # 如果所有解析尝试都失败，返回默认时间
        return "00:00:00,000"

    def convert(self):
        # 检查是否有输入
        json_text = self.text_edit.toPlainText().strip()
        if not json_text:
            QMessageBox.warning(self, "输入错误", "请输入或加载JSON字幕文件")
            return

        # 检查输出路径
        output_path = self.output_path_edit.text()
        if not output_path:
            QMessageBox.warning(self, "输出错误", "请选择输出文件夹")
            return

        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path)
            except Exception as e:
                QMessageBox.warning(self, "输出错误", f"无法创建输出文件夹: {str(e)}")
                return

        # 检查语言选择
        selected_items = self.lang_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "语言选择错误", "请至少选择一种语言")
            return

        # 获取选中的语言代码
        selected_lang_codes = []
        for item in selected_items:
            lang_code = self.get_language_code(item.text())
            if lang_code:
                selected_lang_codes.append(lang_code)

        # 尝试解析JSON
        try:
            subtitles = json.loads(json_text)
        except Exception as e:
            QMessageBox.critical(self, "JSON解析错误", f"无法解析JSON: {str(e)}")
            return

        # 创建视频文件过滤器
        video_filter = "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.mpg *.mpeg *.3gp);;所有文件 (*.*)"

        # 弹出文件选择对话框（选择视频文件）
        video_file, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件（将在相同位置创建同名SRT文件）",
            output_path,
            video_filter
        )

        if not video_file:
            return  # 用户取消了操作

        # 提取视频文件的路径和名称（不含扩展名）
        video_dir = os.path.dirname(video_file)
        video_name = os.path.splitext(os.path.basename(video_file))[0]

        # 生成SRT文件路径
        output_file = os.path.join(video_dir, f"{video_name}.srt")

        # 检查SRT文件是否已存在
        if os.path.exists(output_file):
            reply = QMessageBox.question(
                self,
                "文件已存在",
                f"SRT文件 {video_name}.srt 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # 生成一个包含所有选定语言的SRT文件
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, sub in enumerate(subtitles, 1):
                    start_time = self.format_time(sub.get("start", "0"))
                    end_time = self.format_time(sub.get("end", "0"))

                    # 收集所有选定语言的文本
                    texts = []
                    for lang_code in selected_lang_codes:
                        # 遍历字幕项中的所有键
                        for key in sub.keys():
                            # 检查键是否是语言代码或其变体
                            normalized_key = self.get_language_from_json(key)
                            if normalized_key == lang_code:
                                texts.append(sub[key])
                                break

                    if texts:  # 如果至少有一种语言有文本
                        # 写入SRT格式
                        f.write(f"{i}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write("\n".join(texts) + "\n\n")

            success_count = 1
        except Exception as e:
            QMessageBox.warning(self, "转换错误", f"转换字幕时出错: {str(e)}")
            return

        # 更新输出路径为视频文件的目录
        self.output_path_edit.setText(video_dir)

        # 保存设置（如果选中了保存设置复选框）
        if self.save_settings_checkbox.isChecked():
            self.save_settings()

        # 显示成功信息
        if success_count > 0:
            QMessageBox.information(self, "转换成功", f"成功生成SRT文件\n保存在: {output_file}")
        else:
            QMessageBox.warning(self, "转换失败", "没有生成SRT文件")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JsonToSrtConverter()
    window.show()
    sys.exit(app.exec())