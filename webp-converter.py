import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
                             QListWidget, QProgressBar, QMessageBox)
from PySide6.QtCore import Qt, QMimeData, Signal, QThread, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
from PIL import Image

class ConvertThread(QThread):
    progress_updated = Signal(int)
    conversion_complete = Signal()
    conversion_error = Signal(str)
    
    def __init__(self, file_list):
        super().__init__()
        self.file_list = file_list
        
    def run(self):
        total_files = len(self.file_list)
        converted = 0
        
        for file_path in self.file_list:
            try:
                if file_path.lower().endswith('.webp'):
                    # 获取输出路径 (与原文件相同目录，但扩展名改为.png)
                    output_path = os.path.splitext(file_path)[0] + '.png'
                    
                    # 转换图片
                    img = Image.open(file_path)
                    img.save(output_path, 'PNG')
                    
                    converted += 1
                    self.progress_updated.emit(int(converted / total_files * 100))
            except Exception as e:
                self.conversion_error.emit(f"转换文件 {os.path.basename(file_path)} 时出错: {str(e)}")
                
        self.conversion_complete.emit()


class DropArea(QLabel):
    files_dropped = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText("将WebP文件拖放到这里")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 30px;
                background-color: #f8f8f8;
                font-size: 16px;
            }
        """)
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #3498db;
                    border-radius: 5px;
                    padding: 30px;
                    background-color: #e8f4fc;
                    font-size: 16px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 30px;
                background-color: #f8f8f8;
                font-size: 16px;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        file_paths = []
        
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.webp'):
                    file_paths.append(file_path)
        
        if file_paths:
            self.files_dropped.emit(file_paths)
            
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 30px;
                background-color: #f8f8f8;
                font-size: 16px;
            }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("WebP转PNG转换器")
        self.setMinimumSize(500, 400)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 添加拖放区域
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.add_files)
        main_layout.addWidget(self.drop_area)
        
        # 文件列表
        self.file_list_widget = QListWidget()
        main_layout.addWidget(self.file_list_widget)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 添加文件按钮
        self.add_button = QPushButton("添加文件")
        self.add_button.clicked.connect(self.browse_files)
        button_layout.addWidget(self.add_button)
        
        # 清除列表按钮
        self.clear_button = QPushButton("清除列表")
        self.clear_button.clicked.connect(self.clear_files)
        button_layout.addWidget(self.clear_button)
        
        # 转换按钮
        self.convert_button = QPushButton("转换为PNG")
        self.convert_button.clicked.connect(self.start_conversion)
        self.convert_button.setEnabled(False)
        button_layout.addWidget(self.convert_button)
        
        main_layout.addLayout(button_layout)
        
        # 创建中心部件并设置布局
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # 存储文件路径
        self.file_paths = []
        
        # 转换线程
        self.convert_thread = None
    
    def add_files(self, file_paths):
        for file_path in file_paths:
            if file_path not in self.file_paths:
                self.file_paths.append(file_path)
                self.file_list_widget.addItem(os.path.basename(file_path))
        
        self.convert_button.setEnabled(len(self.file_paths) > 0)
    
    def browse_files(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("WebP Files (*.webp)")
        
        if file_dialog.exec():
            self.add_files(file_dialog.selectedFiles())
    
    def clear_files(self):
        self.file_paths = []
        self.file_list_widget.clear()
        self.convert_button.setEnabled(False)
    
    def start_conversion(self):
        if not self.file_paths:
            return
        
        # 禁用按钮
        self.convert_button.setEnabled(False)
        self.add_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        
        # 显示进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 创建并启动转换线程
        self.convert_thread = ConvertThread(self.file_paths)
        self.convert_thread.progress_updated.connect(self.update_progress)
        self.convert_thread.conversion_complete.connect(self.conversion_finished)
        self.convert_thread.conversion_error.connect(self.show_error)
        self.convert_thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def conversion_finished(self):
        self.progress_bar.setValue(100)
        
        # 重新启用按钮
        self.convert_button.setEnabled(True)
        self.add_button.setEnabled(True)
        self.clear_button.setEnabled(True)
        
        # 显示完成消息
        QMessageBox.information(self, "转换完成", f"成功将 {len(self.file_paths)} 个WebP文件转换为PNG格式!")
    
    def show_error(self, error_message):
        QMessageBox.warning(self, "转换错误", error_message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
