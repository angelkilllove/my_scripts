from PySide6 import QtCore
import sys
import os
import json
import re
import html
from html.parser import HTMLParser
from collections import defaultdict
import copy
from PySide6.QtWidgets import (QApplication, QMainWindow, QSplitter,
                               QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                               QCheckBox, QGroupBox, QPushButton, QScrollArea, QListWidget,
                               QListWidgetItem, QFileDialog, QLineEdit, QRadioButton,
                               QMessageBox, QInputDialog, QDialog, QFormLayout, QGridLayout)
from PySide6.QtCore import Qt, QTimer, QSettings, QRect, QSize, QPoint
from PySide6.QtGui import QClipboard, QFont, QColor, QTextDocument, QTextCursor


class StyleParser(HTMLParser):
    """解析HTML并提取样式信息的解析器"""

    def __init__(self, style_props):
        super().__init__()
        self.style_props = style_props  # 要关注的样式属性列表
        self.reset()
        self.result = []  # 存储所有文本片段及其样式
        self.current_style = {}  # 当前元素的样式
        self.style_stack = []  # 样式栈，用于处理嵌套元素

    def handle_starttag(self, tag, attrs):
        # 保存当前样式
        self.style_stack.append(copy.deepcopy(self.current_style))

        # 处理style属性
        for attr in attrs:
            if attr[0] == 'style':
                style_text = attr[1]
                style_parts = [p.strip() for p in style_text.split(';') if p.strip()]

                for part in style_parts:
                    if ':' in part:
                        prop, value = part.split(':', 1)
                        prop = prop.strip().lower()
                        value = value.strip()

                        # 检查是否是我们关注的属性
                        for style_prop in self.style_props:
                            if prop.startswith(style_prop):
                                self.current_style[prop] = value
                                break

    def handle_endtag(self, tag):
        # 恢复父元素的样式
        if self.style_stack:
            self.current_style = self.style_stack.pop()

    def handle_data(self, data):
        if data.strip():  # 忽略空白文本
            # 创建当前文本片段的样式副本
            style_snapshot = {}
            for prop in self.style_props:
                for key, value in self.current_style.items():
                    if key.startswith(prop):
                        style_snapshot[key] = value

            # 将文本和样式存储起来
            self.result.append({
                'text': data,
                'style': style_snapshot
            })


class StyleComboDialog(QDialog):
    """设置style组合开始和结束标志的对话框"""

    def __init__(self, style_combo, parent=None):
        super().__init__(parent)
        self.style_combo = style_combo
        self.setWindowTitle("设置标志")

        layout = QFormLayout(self)

        # 显示当前样式组合
        style_text = ", ".join([f"{k}={v}" for k, v in style_combo.items()])
        style_label = QLabel(f"样式组合: {style_text}")
        layout.addRow(style_label)

        # 开始标志输入
        self.start_marker = QLineEdit()
        self.start_marker.setPlaceholderText(r"例如: \n<b>")
        layout.addRow("开始标志:", self.start_marker)

        # 结束标志输入
        self.end_marker = QLineEdit()
        self.end_marker.setPlaceholderText(r"例如: </b>\n")
        layout.addRow("结束标志:", self.end_marker)

        # 确定和取消按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)

    def get_markers(self):
        """获取用户输入的标志"""
        return self.start_marker.text(), self.end_marker.text()


class SyncedTextEdit(QTextEdit):
    """
    同步显示选择的文本编辑框
    当在富文本预览中选择文本时，自动在HTML代码中选中对应部分
    """

    def __init__(self, parent=None, html_view=None):
        super().__init__(parent)
        self.html_view = html_view
        self._html_content = ""

    def setHtmlView(self, html_view):
        """设置HTML视图"""
        self.html_view = html_view

    def setHtmlContent(self, content):
        """设置HTML内容"""
        self._html_content = content

    def mousePressEvent(self, event):
        """鼠标按下事件，记录起始位置"""
        super().mousePressEvent(event)
        self.syncSelectionToHtml()

    def mouseMoveEvent(self, event):
        """鼠标移动事件，更新选择"""
        super().mouseMoveEvent(event)
        self.syncSelectionToHtml()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件，完成选择"""
        super().mouseReleaseEvent(event)
        self.syncSelectionToHtml()

    def syncSelectionToHtml(self):
        """同步选择到HTML视图"""
        if not self.html_view or not self._html_content:
            return

        # 获取当前选择的文本
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return

        selected_text = cursor.selectedText()
        if not selected_text:
            return

        # 在HTML内容中查找匹配的文本
        # 注意：这是一个简化的实现，可能无法处理所有情况
        html_content = self._html_content

        # 在HTML中查找选中的纯文本
        # 先使用正则表达式移除HTML标签，只保留文本内容
        html_without_tags = re.sub(r'<[^>]*>', '', html_content)

        # 在未标记的文本中查找选中的文本的位置
        try:
            start_pos_in_plain = html_without_tags.index(selected_text)
            end_pos_in_plain = start_pos_in_plain + len(selected_text)
        except ValueError:
            # 如果找不到完全匹配的文本，则放弃同步
            return

        # 将纯文本位置转换为HTML中的位置
        # 这需要一个更复杂的算法，这里只是一个简化的实现
        # 实际应用中可能需要更精确的映射
        tag_count = 0
        start_pos_in_html = 0
        end_pos_in_html = 0
        char_count = 0

        i = 0
        while i < len(html_content):
            if html_content[i] == '<':
                # 如果是标签开始，找到标签结束
                tag_end = html_content.find('>', i)
                if tag_end != -1:
                    tag_count += 1
                    i = tag_end + 1
                    continue

            # 非标签字符
            if char_count == start_pos_in_plain:
                start_pos_in_html = i

            if char_count == end_pos_in_plain:
                end_pos_in_html = i
                break

            char_count += 1
            i += 1

        # 如果未找到结束位置，则使用HTML内容长度
        if end_pos_in_html == 0:
            end_pos_in_html = len(html_content)

        # 在HTML视图中选择对应的部分
        html_cursor = self.html_view.textCursor()
        html_cursor.setPosition(start_pos_in_html)
        html_cursor.setPosition(end_pos_in_html, QTextCursor.KeepAnchor)
        self.html_view.setTextCursor(html_cursor)
        self.html_view.ensureCursorVisible()


class HTMLStyleExtractor(QMainWindow):
    def __init__(self):
        super().__init__()

        # 设置窗口标题和初始大小
        self.setWindowTitle("HTML样式提取器")
        self.setMinimumSize(1200, 800)

        # 从设置中加载窗口位置和大小
        self.settings = QSettings("HTMLStyleExtractor", "App")
        self.loadSettings()

        # 设置窗口置顶
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建主水平分割器
        main_hsplitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_hsplitter)

        # 创建左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 创建左侧垂直分割器（剪切板预览和HTML代码）
        left_vsplitter = QSplitter(Qt.Vertical)
        left_layout.addWidget(left_vsplitter)

        # 剪切板预览
        clipboard_container = QWidget()
        clipboard_layout = QVBoxLayout(clipboard_container)
        clipboard_layout.setContentsMargins(2, 2, 2, 2)

        clipboard_label = QLabel("剪切板预览:")
        clipboard_layout.addWidget(clipboard_label)

        self.clipboard_view = SyncedTextEdit()
        self.clipboard_view.setReadOnly(True)
        self.clipboard_view.setAcceptRichText(True)
        clipboard_layout.addWidget(self.clipboard_view)

        # HTML代码
        html_container = QWidget()
        html_layout = QVBoxLayout(html_container)
        html_layout.setContentsMargins(2, 2, 2, 2)

        html_label = QLabel("HTML代码:")
        html_layout.addWidget(html_label)

        self.html_view = QTextEdit()
        self.html_view.setReadOnly(True)
        self.html_view.setLineWrapMode(QTextEdit.NoWrap)
        html_layout.addWidget(self.html_view)

        # 设置同步关系
        self.clipboard_view.setHtmlView(self.html_view)

        # 添加到左侧垂直分割器
        left_vsplitter.addWidget(clipboard_container)
        left_vsplitter.addWidget(html_container)

        # CSS属性选择
        css_group = QGroupBox("要关注的CSS属性")
        css_layout = QVBoxLayout()

        self.css_props = {
            "color": "颜色",
            "background": "背景",
            "font-family": "字体",
            "font-size": "字体大小",
            "font-weight": "字体粗细",
            "text-align": "文本对齐",
            "margin": "外边距",
            "padding": "内边距",
            "border": "边框",
            "display": "显示方式",
            "position": "定位",
            "width": "宽度",
            "height": "高度"
        }

        self.css_checkboxes = {}
        for prop, label in self.css_props.items():
            checkbox = QCheckBox(f"{label} ({prop})")
            self.css_checkboxes[prop] = checkbox
            css_layout.addWidget(checkbox)

        css_group.setLayout(css_layout)

        # 创建滚动区域包含CSS属性
        css_scroll = QScrollArea()
        css_scroll.setWidgetResizable(True)
        css_scroll.setWidget(css_group)
        left_layout.addWidget(css_scroll)

        # 添加分析按钮
        analyze_button = QPushButton("分析HTML样式")
        analyze_button.clicked.connect(self.analyzeHTML)
        left_layout.addWidget(analyze_button)

        # 创建右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 右侧垂直分割器
        right_vsplitter = QSplitter(Qt.Vertical)
        right_layout.addWidget(right_vsplitter)

        # 上部分：样式组合列表
        combo_container = QWidget()
        combo_layout = QVBoxLayout(combo_container)
        combo_layout.setContentsMargins(2, 2, 2, 2)

        combo_layout.addWidget(QLabel("样式组合列表:"))

        self.combo_list = QListWidget()
        # 设置列表为扩展选择模式，支持Ctrl和Shift多选
        self.combo_list.setSelectionMode(QListWidget.ExtendedSelection)
        combo_layout.addWidget(self.combo_list)

        # 样式组合操作按钮
        combo_buttons = QHBoxLayout()

        self.move_up_button = QPushButton("上移")
        self.move_up_button.clicked.connect(self.moveStyleUp)
        combo_buttons.addWidget(self.move_up_button)

        self.move_down_button = QPushButton("下移")
        self.move_down_button.clicked.connect(self.moveStyleDown)
        combo_buttons.addWidget(self.move_down_button)

        self.set_markers_button = QPushButton("设置标志")
        self.set_markers_button.clicked.connect(self.setStyleMarkers)
        combo_buttons.addWidget(self.set_markers_button)

        combo_layout.addLayout(combo_buttons)

        # 中部分：全局设置 - 改为使用网格布局减少空间
        global_container = QWidget()
        global_layout = QGridLayout(global_container)
        global_layout.setContentsMargins(2, 2, 2, 2)

        global_layout.addWidget(QLabel("全局设置:"), 0, 0, 1, 4)

        # 文本开始和结束标志
        global_layout.addWidget(QLabel("文本开始标志:"), 1, 0)
        self.global_start_marker = QLineEdit()
        global_layout.addWidget(self.global_start_marker, 1, 1)

        global_layout.addWidget(QLabel("文本结束标志:"), 1, 2)
        self.global_end_marker = QLineEdit()
        global_layout.addWidget(self.global_end_marker, 1, 3)

        # 保存路径
        global_layout.addWidget(QLabel("保存路径:"), 2, 0)
        self.save_path = QLineEdit()
        global_layout.addWidget(self.save_path, 2, 1, 1, 2)

        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browseSavePath)
        global_layout.addWidget(browse_button, 2, 3)

        # 是否覆盖已有文件
        overwrite_widget = QWidget()
        overwrite_layout = QHBoxLayout(overwrite_widget)
        overwrite_layout.setContentsMargins(0, 0, 0, 0)

        self.overwrite_yes = QRadioButton("覆盖已有文件")
        self.overwrite_no = QRadioButton("自动重命名")
        self.overwrite_no.setChecked(True)

        overwrite_layout.addWidget(self.overwrite_yes)
        overwrite_layout.addWidget(self.overwrite_no)
        global_layout.addWidget(overwrite_widget, 3, 0, 1, 4)

        # 运行和保存按钮
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)

        process_button = QPushButton("生成结果")
        process_button.clicked.connect(self.processText)
        action_layout.addWidget(process_button)

        save_button = QPushButton("保存结果")
        save_button.clicked.connect(self.saveResult)
        action_layout.addWidget(save_button)

        save_settings_button = QPushButton("保存设置")
        save_settings_button.clicked.connect(self.saveSettings)
        action_layout.addWidget(save_settings_button)

        global_layout.addWidget(action_widget, 4, 0, 1, 4)

        # 下部分：结果显示
        result_container = QWidget()
        result_layout = QVBoxLayout(result_container)
        result_layout.setContentsMargins(2, 2, 2, 2)

        result_layout.addWidget(QLabel("处理结果:"))

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)

        # 添加面板到分割器
        main_hsplitter.addWidget(left_panel)
        main_hsplitter.addWidget(right_panel)

        right_vsplitter.addWidget(combo_container)
        right_vsplitter.addWidget(global_container)
        right_vsplitter.addWidget(result_container)

        # 设置分割器初始大小
        main_hsplitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])
        left_vsplitter.setSizes([int(self.height() * 0.5), int(self.height() * 0.5)])
        right_vsplitter.setSizes([int(self.height() * 0.3), int(self.height() * 0.1), int(self.height() * 0.6)])

        # 保存分割器的引用
        self.main_hsplitter = main_hsplitter
        self.left_vsplitter = left_vsplitter
        self.right_vsplitter = right_vsplitter

        # 获取剪切板实例
        self.clipboard = QApplication.clipboard()

        # 监听剪切板变化
        self.clipboard.dataChanged.connect(self.onClipboardChange)

        # 初始化时立即获取剪切板内容
        self.onClipboardChange()

        # 设置定时器，定期检查剪切板内容（防止某些应用不触发dataChanged信号）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.checkClipboard)
        self.timer.start(1000)  # 每秒检查一次

        # 保存上一次的剪切板文本，用于检测变化
        self.last_clipboard_text = ""
        self.last_clipboard_html = ""

        # 存储解析结果
        self.parsed_segments = []
        self.style_combos = []
        self.style_markers = {}  # 存储每个样式组合的标记
        # 添加活跃状态追踪
        self.is_active = True
        # 监听窗口状态变化
        self.is_minimized = False

        # 加载设置
        self.loadAppSettings()

    def changeEvent(self, event):
        """处理窗口状态变化事件"""
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                # 窗口最小化，停止定时器
                self.is_minimized = True
                self.timer.stop()
            elif self.is_minimized:
                # 窗口从最小化恢复，重启定时器
                self.is_minimized = False
                self.timer.start(1000)
                # 恢复时立即更新一次
                self.onClipboardChange()
        super().changeEvent(event)

    def loadSettings(self):
        """从设置中加载窗口位置和大小"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.setGeometry(geometry)
        else:
            # 如果没有保存的设置，居中显示窗口
            screen_geometry = QApplication.primaryScreen().availableGeometry()
            x = (screen_geometry.width() - self.width()) / 2
            y = (screen_geometry.height() - self.height()) / 2
            self.setGeometry(QRect(int(x), int(y), 1200, 800))

    def loadAppSettings(self):
        """加载应用设置"""
        # 加载CSS属性选择
        for prop, checkbox in self.css_checkboxes.items():
            checkbox.setChecked(self.settings.value(f"css_prop_{prop}", False, type=bool))

        # 加载全局标记
        self.global_start_marker.setText(self.settings.value("global_start_marker", ""))
        self.global_end_marker.setText(self.settings.value("global_end_marker", ""))

        # 加载保存路径
        self.save_path.setText(self.settings.value("save_path", ""))

        # 加载覆盖设置
        overwrite = self.settings.value("overwrite_file", False, type=bool)
        self.overwrite_yes.setChecked(overwrite)
        self.overwrite_no.setChecked(not overwrite)

        # 加载样式标记
        markers_count = self.settings.beginReadArray("style_markers")
        for i in range(markers_count):
            self.settings.setArrayIndex(i)
            style_str = self.settings.value("style", "")
            start_marker = self.settings.value("start_marker", "")
            end_marker = self.settings.value("end_marker", "")

            if style_str:
                style_dict = json.loads(style_str)
                self.style_markers[self.style_dict_to_tuple(style_dict)] = (start_marker, end_marker)

        self.settings.endArray()

    def saveAppSettings(self):
        """保存应用设置"""
        # 保存CSS属性选择
        for prop, checkbox in self.css_checkboxes.items():
            self.settings.setValue(f"css_prop_{prop}", checkbox.isChecked())

        # 保存全局标记
        self.settings.setValue("global_start_marker", self.global_start_marker.text())
        self.settings.setValue("global_end_marker", self.global_end_marker.text())

        # 保存保存路径
        self.settings.setValue("save_path", self.save_path.text())

        # 保存覆盖设置
        self.settings.setValue("overwrite_file", self.overwrite_yes.isChecked())

        # 保存样式标记
        self.settings.beginWriteArray("style_markers", len(self.style_markers))

        idx = 0
        for style_tuple, markers in self.style_markers.items():
            self.settings.setArrayIndex(idx)

            style_dict = dict(style_tuple)
            self.settings.setValue("style", json.dumps(style_dict))
            self.settings.setValue("start_marker", markers[0])
            self.settings.setValue("end_marker", markers[1])

            idx += 1

        self.settings.endArray()

        QMessageBox.information(self, "保存设置", "设置已保存！")

    def closeEvent(self, event):
        """窗口关闭事件，保存设置"""
        self.settings.setValue("geometry", self.geometry())
        super().closeEvent(event)

    def changeEvent(self, event):
        """处理窗口状态变化事件"""
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                # 窗口最小化，停止定时器和监听
                self.is_active = False
                self.timer.stop()
            else:
                # 窗口从最小化恢复，重启定时器
                self.is_active = True
                self.timer.start(1000)
                # 注意：恢复时不自动更新，只开始监测变化
        super().changeEvent(event)

    def style_dict_to_tuple(self, style_dict):
        """将样式字典转换为可哈希的元组"""
        return tuple(sorted(style_dict.items()))

    def activateWindow(self):
        """重写激活窗口方法"""
        super().activateWindow()
        self.is_active = True
        # 窗口激活时启动定时器
        if not self.timer.isActive():
            self.timer.start(1000)

    def onClipboardChange(self):
        """剪切板内容变化时的处理函数"""
        self.updateClipboardView()

    def checkClipboard(self):
        """定时检查剪切板内容"""
        if not self.is_active:
            return  # 如果窗口不活跃，不检查变化

        clipboard_text = self.clipboard.text()
        clipboard_html = self.clipboard.mimeData().html()

        # 如果内容有变化，则更新视图
        if clipboard_text != self.last_clipboard_text or clipboard_html != self.last_clipboard_html:
            self.updateClipboardView()

    def updateClipboardView(self):
        """更新剪切板视图"""
        mime_data = self.clipboard.mimeData()

        # 保存当前剪切板内容
        self.last_clipboard_text = self.clipboard.text()
        self.last_clipboard_html = mime_data.html()

        # 更新富文本预览
        if mime_data.hasHtml():
            html_content = mime_data.html()
            self.clipboard_view.setHtml(html_content)
            self.clipboard_view.setHtmlContent(html_content)

            # 更新HTML代码视图
            self.html_view.setPlainText(html_content)
        elif mime_data.hasText():
            self.clipboard_view.setPlainText(mime_data.text())
            self.html_view.setPlainText("剪切板中没有HTML内容")
        else:
            self.clipboard_view.setPlainText("剪切板中没有文本内容")
            self.html_view.setPlainText("剪切板中没有HTML内容")

    def analyzeHTML(self):
        """分析HTML中的样式"""
        html_text = self.html_view.toPlainText()
        if not html_text or html_text == "剪切板中没有HTML内容":
            QMessageBox.warning(self, "错误", "剪切板中没有有效的HTML内容")
            return

        # 获取选中的CSS属性
        selected_props = [prop for prop, checkbox in self.css_checkboxes.items() if checkbox.isChecked()]
        if not selected_props:
            QMessageBox.warning(self, "错误", "请至少选择一个CSS属性")
            return

        # 解析HTML
        parser = StyleParser(selected_props)
        parser.feed(html_text)

        # 保存解析结果
        self.parsed_segments = parser.result

        # 提取不同的样式组合
        seen_styles = set()
        self.style_combos = []

        for segment in self.parsed_segments:
            # 过滤掉非选中的CSS属性
            filtered_style = {k: v for k, v in segment['style'].items()
                              if any(k.startswith(prop) for prop in selected_props)}

            style_tuple = self.style_dict_to_tuple(filtered_style)
            if style_tuple not in seen_styles:
                seen_styles.add(style_tuple)
                self.style_combos.append(dict(style_tuple))

        # 清空并更新列表
        self.combo_list.clear()

        # 先检查加载的样式标记是否与当前选择的属性匹配
        valid_markers = {}
        for style_tuple, markers in self.style_markers.items():
            style_dict = dict(style_tuple)
            if all(any(k.startswith(prop) for prop in selected_props) for k in style_dict.keys()):
                valid_markers[style_tuple] = markers

        self.style_markers = valid_markers

        # 添加样式组合到列表
        for style in self.style_combos:
            style_tuple = self.style_dict_to_tuple(style)

            # 创建显示文本
            if style_tuple in self.style_markers:
                start, end = self.style_markers[style_tuple]
                display_text = self.create_style_display_text(style, start, end)
            else:
                display_text = self.create_style_display_text(style)

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, style)

            # 设置工具提示
            if style_tuple in self.style_markers:
                start, end = self.style_markers[style_tuple]
                tooltip = f"开始标志: {start}, 结束标志: {end}"
                item.setToolTip(tooltip)

            self.combo_list.addItem(item)

    def create_style_display_text(self, style, start_marker=None, end_marker=None):
        """创建样式显示文本"""
        base_text = ", ".join([f"{k}={v}" for k, v in style.items()])

        if start_marker is not None and end_marker is not None:
            return f"{base_text} [已设置标志]"
        else:
            return base_text

    def moveStyleUp(self):
        """将选中的样式向上移动"""
        current_row = self.combo_list.currentRow()
        if current_row > 0:
            item = self.combo_list.takeItem(current_row)
            self.combo_list.insertItem(current_row - 1, item)
            self.combo_list.setCurrentRow(current_row - 1)

            # 同时调整样式组合列表
            self.style_combos.insert(current_row - 1, self.style_combos.pop(current_row))

    def moveStyleDown(self):
        """将选中的样式向下移动"""
        current_row = self.combo_list.currentRow()
        if current_row < self.combo_list.count() - 1 and current_row >= 0:
            item = self.combo_list.takeItem(current_row)
            self.combo_list.insertItem(current_row + 1, item)
            self.combo_list.setCurrentRow(current_row + 1)

            # 同时调整样式组合列表
            self.style_combos.insert(current_row + 1, self.style_combos.pop(current_row))

    def setStyleMarkers(self):
        """为选中的样式设置标志"""
        current_item = self.combo_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "错误", "请先选择一个样式组合")
            return

        style = current_item.data(Qt.UserRole)

        # 显示设置对话框
        dialog = StyleComboDialog(style, self)

        # 如果已有设置，则填充到对话框
        style_tuple = self.style_dict_to_tuple(style)
        if style_tuple in self.style_markers:
            start, end = self.style_markers[style_tuple]
            dialog.start_marker.setText(start)
            dialog.end_marker.setText(end)

        # 如果用户确认，则保存设置
        if dialog.exec():
            start_marker, end_marker = dialog.get_markers()
            self.style_markers[style_tuple] = (start_marker, end_marker)

            # 更新列表项显示
            current_row = self.combo_list.currentRow()
            current_item.setText(self.create_style_display_text(style, start_marker, end_marker))
            current_item.setToolTip(f"开始标志: {start_marker}, 结束标志: {end_marker}")

    def browseSavePath(self):
        """浏览保存路径"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "选择保存路径", "", "文本文件 (*.txt);;所有文件 (*.*)")

        if filename:
            self.save_path.setText(filename)

    def processText(self):
        """处理文本，生成结果"""
        if not self.parsed_segments:
            QMessageBox.warning(self, "错误", "请先分析HTML")
            return

        # 获取选中的样式组合
        selected_items = self.combo_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "错误", "请至少选择一个样式组合")
            return

        selected_styles = [item.data(Qt.UserRole) for item in selected_items]
        selected_style_tuples = [self.style_dict_to_tuple(style) for style in selected_styles]

        # 按组合顺序处理文本
        result = []

        # 添加全局开始标志
        global_start = self.global_start_marker.text()
        if global_start:
            result.append(self.process_escapes(global_start))

        # 遍历所有文本片段
        for segment in self.parsed_segments:
            # 过滤样式
            style = {k: v for k, v in segment['style'].items()
                     if any(k.startswith(prop) for prop, checkbox in self.css_checkboxes.items()
                            if checkbox.isChecked())}

            style_tuple = self.style_dict_to_tuple(style)

            # 检查是否是选中的样式
            if style_tuple in selected_style_tuples:
                # 获取样式索引
                style_index = selected_style_tuples.index(style_tuple)

                # 添加开始标志
                if style_tuple in self.style_markers:
                    start_marker, _ = self.style_markers[style_tuple]
                    if start_marker:
                        result.append(self.process_escapes(start_marker))

                # 添加文本
                result.append(segment['text'])

                # 添加结束标志
                if style_tuple in self.style_markers:
                    _, end_marker = self.style_markers[style_tuple]
                    if end_marker:
                        result.append(self.process_escapes(end_marker))

        # 添加全局结束标志
        global_end = self.global_end_marker.text()
        if global_end:
            result.append(self.process_escapes(global_end))

        # 显示结果
        self.result_text.setPlainText(''.join(result))

    def process_escapes(self, text):
        """处理转义字符"""
        return text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')

    def saveResult(self):
        """保存结果到文件"""
        result_text = self.result_text.toPlainText()
        if not result_text:
            QMessageBox.warning(self, "错误", "没有结果可保存")
            return

        # 获取保存路径
        file_path = self.save_path.text()
        if not file_path:
            QMessageBox.warning(self, "错误", "请设置保存路径")
            return

        # 检查是否需要重命名
        if not self.overwrite_yes.isChecked() and os.path.exists(file_path):
            base_name, ext = os.path.splitext(file_path)
            counter = 1
            while os.path.exists(f"{base_name}_{counter}{ext}"):
                counter += 1
            file_path = f"{base_name}_{counter}{ext}"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(result_text)
            QMessageBox.information(self, "保存成功", f"结果已保存到: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存文件时出错: {str(e)}")

    def saveSettings(self):
        """保存所有设置"""
        self.saveAppSettings()

def main():
    app = QApplication(sys.argv)

    # 创建并显示主窗口
    window = HTMLStyleExtractor()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()