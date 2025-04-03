import sys
import os
import json
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QSplitter,
                               QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                               QCheckBox, QGroupBox, QPushButton, QScrollArea)
from PySide6.QtCore import Qt, QTimer, QSettings, QRect
from PySide6.QtGui import QClipboard, QTextDocument


class ClipboardHtmlViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        # 设置窗口标题和初始大小
        self.setWindowTitle("剪切板HTML查看器")
        self.setMinimumSize(900, 700)

        # 从设置中加载窗口位置和大小
        self.settings = QSettings("ClipboardHtmlViewer", "App")
        self.loadSettings()

        # 设置窗口置顶
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建水平分割器
        hsplitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(hsplitter)

        # 创建左侧文本框 - 用于显示剪切板内容
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_label = QLabel("剪切板内容预览:")
        left_layout.addWidget(left_label)

        self.clipboard_view = QTextEdit()
        self.clipboard_view.setReadOnly(True)
        self.clipboard_view.setAcceptRichText(True)
        left_layout.addWidget(self.clipboard_view)

        # 创建右侧的垂直分割器
        vsplitter = QSplitter(Qt.Vertical)

        # 创建右上侧文本框 - 用于显示原始HTML代码
        original_html_container = QWidget()
        original_html_layout = QVBoxLayout(original_html_container)
        original_html_layout.setContentsMargins(0, 0, 0, 0)

        original_html_label = QLabel("原始HTML代码:")
        original_html_layout.addWidget(original_html_label)

        self.html_view = QTextEdit()
        self.html_view.setReadOnly(True)
        self.html_view.setLineWrapMode(QTextEdit.NoWrap)
        original_html_layout.addWidget(self.html_view)

        # 创建右中间的优化选项区域
        options_container = QWidget()
        options_layout = QVBoxLayout(options_container)
        options_layout.setContentsMargins(0, 0, 0, 0)

        options_label = QLabel("HTML优化选项:")
        options_layout.addWidget(options_label)

        # 创建一个滚动区域来容纳所有选项
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 结构优化选项
        structure_group = QGroupBox("结构优化")
        structure_layout = QVBoxLayout()

        self.remove_html_head = QCheckBox("移除<html>, <head>, <meta>等标签")
        self.remove_html_head.setChecked(True)
        structure_layout.addWidget(self.remove_html_head)

        self.remove_comments = QCheckBox("移除HTML注释")
        self.remove_comments.setChecked(True)
        structure_layout.addWidget(self.remove_comments)

        self.remove_empty_tags = QCheckBox("移除空标签 (空的span, div等)")
        self.remove_empty_tags.setChecked(True)
        structure_layout.addWidget(self.remove_empty_tags)

        self.format_html = QCheckBox("格式化HTML (添加缩进和换行)")
        self.format_html.setChecked(True)
        structure_layout.addWidget(self.format_html)

        structure_group.setLayout(structure_layout)
        scroll_layout.addWidget(structure_group)

        # 属性优化选项
        attr_group = QGroupBox("属性优化")
        attr_layout = QVBoxLayout()

        self.remove_class = QCheckBox("移除class属性")
        self.remove_class.setChecked(False)
        attr_layout.addWidget(self.remove_class)

        self.remove_id = QCheckBox("移除id属性")
        self.remove_id.setChecked(False)
        attr_layout.addWidget(self.remove_id)

        self.remove_style = QCheckBox("移除style属性")
        self.remove_style.setChecked(False)
        attr_layout.addWidget(self.remove_style)

        self.remove_data_attrs = QCheckBox("移除data-*属性")
        self.remove_data_attrs.setChecked(True)
        attr_layout.addWidget(self.remove_data_attrs)

        attr_group.setLayout(attr_layout)
        scroll_layout.addWidget(attr_group)

        # 其他优化选项
        other_group = QGroupBox("其他优化")
        other_layout = QVBoxLayout()

        self.remove_whitespace = QCheckBox("精简空白字符")
        self.remove_whitespace.setChecked(True)
        other_layout.addWidget(self.remove_whitespace)

        self.minimize_tags = QCheckBox("最小化标签 (简化冗余标签)")
        self.minimize_tags.setChecked(False)
        other_layout.addWidget(self.minimize_tags)

        other_group.setLayout(other_layout)
        scroll_layout.addWidget(other_group)

        scroll_area.setWidget(scroll_widget)
        options_layout.addWidget(scroll_area)

        # 添加优化按钮
        optimize_button = QPushButton("应用优化选项")
        optimize_button.clicked.connect(self.updateOptimizedView)
        options_layout.addWidget(optimize_button)

        # 创建右下侧文本框 - 用于显示优化后的HTML代码
        optimized_html_container = QWidget()
        optimized_html_layout = QVBoxLayout(optimized_html_container)
        optimized_html_layout.setContentsMargins(0, 0, 0, 0)

        optimized_html_label = QLabel("优化后的HTML代码:")
        optimized_html_layout.addWidget(optimized_html_label)

        self.optimized_html_view = QTextEdit()
        self.optimized_html_view.setReadOnly(True)
        self.optimized_html_view.setLineWrapMode(QTextEdit.NoWrap)
        optimized_html_layout.addWidget(self.optimized_html_view)

        # 将左侧容器和右侧垂直分割器添加到水平分割器
        hsplitter.addWidget(left_container)
        hsplitter.addWidget(vsplitter)

        # 将容器添加到垂直分割器
        vsplitter.addWidget(original_html_container)
        vsplitter.addWidget(options_container)
        vsplitter.addWidget(optimized_html_container)

        # 设置分割器初始大小
        hsplitter.setSizes([int(self.width() * 0.4), int(self.width() * 0.6)])
        self.hsplitter = hsplitter

        vsplitter.setSizes([int(self.height() * 0.3), int(self.height() * 0.3), int(self.height() * 0.4)])
        self.vsplitter = vsplitter

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
            self.setGeometry(QRect(int(x), int(y), 900, 700))

    def saveSettings(self):
        """保存窗口位置和大小到设置"""
        self.settings.setValue("geometry", self.geometry())
        self.settings.setValue("hsplitter_sizes", self.hsplitter.sizes())
        self.settings.setValue("vsplitter_sizes", self.vsplitter.sizes())

        # 保存优化选项
        self.settings.setValue("remove_html_head", self.remove_html_head.isChecked())
        self.settings.setValue("remove_comments", self.remove_comments.isChecked())
        self.settings.setValue("remove_empty_tags", self.remove_empty_tags.isChecked())
        self.settings.setValue("format_html", self.format_html.isChecked())
        self.settings.setValue("remove_class", self.remove_class.isChecked())
        self.settings.setValue("remove_id", self.remove_id.isChecked())
        self.settings.setValue("remove_style", self.remove_style.isChecked())
        self.settings.setValue("remove_data_attrs", self.remove_data_attrs.isChecked())
        self.settings.setValue("remove_whitespace", self.remove_whitespace.isChecked())
        self.settings.setValue("minimize_tags", self.minimize_tags.isChecked())

    def loadOptimizationSettings(self):
        """从设置中加载优化选项"""
        self.remove_html_head.setChecked(self.settings.value("remove_html_head", True, type=bool))
        self.remove_comments.setChecked(self.settings.value("remove_comments", True, type=bool))
        self.remove_empty_tags.setChecked(self.settings.value("remove_empty_tags", True, type=bool))
        self.format_html.setChecked(self.settings.value("format_html", True, type=bool))
        self.remove_class.setChecked(self.settings.value("remove_class", False, type=bool))
        self.remove_id.setChecked(self.settings.value("remove_id", False, type=bool))
        self.remove_style.setChecked(self.settings.value("remove_style", False, type=bool))
        self.remove_data_attrs.setChecked(self.settings.value("remove_data_attrs", True, type=bool))
        self.remove_whitespace.setChecked(self.settings.value("remove_whitespace", True, type=bool))
        self.minimize_tags.setChecked(self.settings.value("minimize_tags", False, type=bool))

    def closeEvent(self, event):
        """窗口关闭事件，保存设置"""
        self.saveSettings()
        super().closeEvent(event)

    def onClipboardChange(self):
        """剪切板内容变化时的处理函数"""
        self.updateViews()

    def checkClipboard(self):
        """定时检查剪切板内容"""
        clipboard_text = self.clipboard.text()
        clipboard_html = self.clipboard.mimeData().html()

        # 如果内容有变化，则更新视图
        if clipboard_text != self.last_clipboard_text or clipboard_html != self.last_clipboard_html:
            self.updateViews()

    def optimize_html(self, html_content):
        """根据用户选择优化HTML代码"""
        if not html_content:
            return ""

        optimized_html = html_content

        # 移除HTML、HEAD、META等标签及其内容
        if self.remove_html_head.isChecked():
            optimized_html = re.sub(r'<html[^>]*>.*?<body[^>]*>', '', optimized_html, flags=re.DOTALL | re.IGNORECASE)
            optimized_html = re.sub(r'</body>.*?</html>', '', optimized_html, flags=re.DOTALL | re.IGNORECASE)

        # 移除注释
        if self.remove_comments.isChecked():
            optimized_html = re.sub(r'<!--.*?-->', '', optimized_html, flags=re.DOTALL)

        # 移除空的标签
        if self.remove_empty_tags.isChecked():
            optimized_html = re.sub(r'<span[^>]*>\s*</span>', '', optimized_html)
            optimized_html = re.sub(r'<div[^>]*>\s*</div>', '', optimized_html)
            optimized_html = re.sub(r'<p[^>]*>\s*</p>', '', optimized_html)

        # 移除class属性
        if self.remove_class.isChecked():
            optimized_html = re.sub(r' class="[^"]*"', '', optimized_html)

        # 移除id属性
        if self.remove_id.isChecked():
            optimized_html = re.sub(r' id="[^"]*"', '', optimized_html)

        # 移除style属性
        if self.remove_style.isChecked():
            optimized_html = re.sub(r' style="[^"]*"', '', optimized_html)

        # 移除data-*属性
        if self.remove_data_attrs.isChecked():
            optimized_html = re.sub(r' data-[^=]*="[^"]*"', '', optimized_html)

        # 移除不必要的空格和换行
        if self.remove_whitespace.isChecked():
            optimized_html = re.sub(r'\s+', ' ', optimized_html)
            optimized_html = re.sub(r'>\s+<', '><', optimized_html)

        # 最小化标签 (简化冗余标签)
        if self.minimize_tags.isChecked():
            # 移除多余的嵌套span
            optimized_html = re.sub(r'<span[^>]*><span([^>]*)>(.*?)</span></span>', r'<span\1>\2</span>', optimized_html)
            # 移除单个换行符周围的额外p标签
            optimized_html = re.sub(r'<p[^>]*>(\s*)<br[^>]*>(\s*)</p>', r'<br>', optimized_html)

        # 格式化HTML
        if self.format_html.isChecked():
            formatted_html = ""
            indent = 0
            lines = []

            i = 0
            while i < len(optimized_html):
                if optimized_html[i:i + 2] == '</':
                    # 闭合标签减少缩进
                    indent = max(0, indent - 2)
                    j = optimized_html.find('>', i)
                    if j == -1:
                        break
                    lines.append(' ' * indent + optimized_html[i:j + 1])
                    i = j + 1
                elif optimized_html[i] == '<' and optimized_html[i:i + 4] != '<!--' and optimized_html[i:i + 2] != '</':
                    # 开始标签
                    j = optimized_html.find('>', i)
                    if j == -1:
                        break

                    # 检查是否为自闭合标签
                    is_self_closing = optimized_html[j - 1] == '/' or optimized_html[i:j].lower() in ['<br', '<hr', '<img', '<input', '<link', '<meta']

                    lines.append(' ' * indent + optimized_html[i:j + 1])
                    if not is_self_closing:
                        indent += 2
                    i = j + 1
                else:
                    # 文本内容
                    j = optimized_html.find('<', i)
                    if j == -1:
                        lines.append(' ' * indent + optimized_html[i:])
                        break

                    if j > i:
                        text_content = optimized_html[i:j].strip()
                        if text_content:
                            lines.append(' ' * indent + text_content)
                    i = j

            optimized_html = '\n'.join(lines)

        return optimized_html

    def updateOptimizedView(self):
        """更新优化后的HTML视图"""
        if self.html_view.toPlainText():
            optimized_html = self.optimize_html(self.html_view.toPlainText())
            self.optimized_html_view.setPlainText(optimized_html)

    def updateViews(self):
        """更新视图"""
        mime_data = self.clipboard.mimeData()

        # 保存当前剪切板内容
        self.last_clipboard_text = self.clipboard.text()
        self.last_clipboard_html = mime_data.html()

        # 更新左侧富文本视图
        if mime_data.hasHtml():
            self.clipboard_view.setHtml(mime_data.html())
        elif mime_data.hasText():
            self.clipboard_view.setPlainText(mime_data.text())
        else:
            self.clipboard_view.setPlainText("剪切板中没有文本内容")

        # 更新右上侧原始HTML代码视图
        if mime_data.hasHtml():
            html_content = mime_data.html()
            self.html_view.setPlainText(html_content)

            # 更新右下侧优化后的HTML代码视图
            self.updateOptimizedView()
        else:
            self.html_view.setPlainText("剪切板中没有HTML内容")
            self.optimized_html_view.setPlainText("无HTML内容可优化")


def main():
    app = QApplication(sys.argv)

    # 创建并显示主窗口
    window = ClipboardHtmlViewer()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()