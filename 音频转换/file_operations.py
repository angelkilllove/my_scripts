import os
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QCheckBox, QPushButton, QStyle)
from PySide6.QtCore import Qt


def generate_unique_filename(filepath):
    """生成一个不存在的文件名，通过添加序号(n)"""
    if not os.path.exists(filepath):
        return filepath

    path_obj = Path(filepath)
    base_dir = path_obj.parent
    filename = path_obj.stem
    extension = path_obj.suffix

    index = 1
    while True:
        new_filename = os.path.join(base_dir, f"{filename}({index}){extension}")
        if not os.path.exists(new_filename):
            return new_filename
        index += 1


def get_default_extension(codec):
    """根据编解码器获取默认扩展名"""
    # 映射到适当的文件扩展名
    codec_to_ext = {
        "aac": "aac",
        "mp3": "mp3",
        "opus": "opus",
        "vorbis": "ogg",
        "flac": "flac",
        "pcm_s16le": "wav",
        "pcm_s24le": "wav",
        "pcm_f32le": "wav"
    }
    return codec_to_ext.get(codec, "m4a")


class FileOverwriteDialog(QDialog):
    """文件覆盖确认对话框"""

    OVERWRITE = 0
    SKIP = 1
    RENAME = 2
    CANCEL = 3
    OVERWRITE_ALL = 4
    SKIP_ALL = 5

    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件已存在")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # 提示信息
        icon_label = QLabel()
        try:
            icon_label.setPixmap(self.style().standardIcon(QStyle.SP_MessageBoxWarning).pixmap(32, 32))
        except:
            pass  # 忽略图标设置错误

        message_layout = QHBoxLayout()
        message_layout.addWidget(icon_label)
        message_label = QLabel(f"文件 '{os.path.basename(filename)}' 已经存在，您要如何处理？")
        message_label.setWordWrap(True)
        message_layout.addWidget(message_label, 1)  # 拉伸因子为1

        layout.addLayout(message_layout)

        # 计算替代文件名
        self.renamed_path = generate_unique_filename(filename)
        renamed_basename = os.path.basename(self.renamed_path)

        rename_info = QLabel(f"重命名选项将自动将文件另存为：{renamed_basename}")
        rename_info.setStyleSheet("color: blue;")
        layout.addWidget(rename_info)

        # 水平按钮布局
        button_layout = QHBoxLayout()

        self.overwrite_btn = QPushButton("覆盖(&O)")
        self.overwrite_btn.clicked.connect(self.overwrite_clicked)

        self.skip_btn = QPushButton("跳过(&S)")
        self.skip_btn.clicked.connect(self.skip_clicked)

        self.rename_btn = QPushButton("重命名(&R)")
        self.rename_btn.clicked.connect(self.rename_clicked)

        self.cancel_btn = QPushButton("取消(&C)")
        self.cancel_btn.clicked.connect(self.cancel_clicked)

        button_layout.addWidget(self.overwrite_btn)
        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.rename_btn)
        button_layout.addWidget(self.cancel_btn)

        # 添加"应用到所有文件"选项
        apply_layout = QHBoxLayout()

        self.apply_all_check = QCheckBox("对所有冲突文件执行相同操作")
        apply_layout.addWidget(self.apply_all_check)

        layout.addSpacing(10)
        layout.addLayout(button_layout)
        layout.addLayout(apply_layout)

        self.result = None

    def overwrite_clicked(self):
        self.result = self.OVERWRITE_ALL if self.apply_all_check.isChecked() else self.OVERWRITE
        self.accept()

    def skip_clicked(self):
        self.result = self.SKIP_ALL if self.apply_all_check.isChecked() else self.SKIP
        self.accept()

    def rename_clicked(self):
        self.result = self.RENAME
        self.accept()

    def cancel_clicked(self):
        self.result = self.CANCEL
        self.accept()

    def get_action(self):
        return self.result

    def get_renamed_path(self):
        return self.renamed_path


def process_file_for_conversion(main_window, idx, file_info, output_format, overwrite_all=False, skip_all=False):
    """处理单个文件转换，包括处理冲突"""
    input_path = Path(file_info['path'])
    
    # 确定输出扩展名
    if output_format == "auto":
        # 自动检测模式，尝试获取原始编解码器
        if file_info.get('audio_info') and file_info['audio_info'].get('codec'):
            output_ext = get_default_extension(file_info['audio_info']['codec'])
        else:
            # 如果未知，默认为opus
            output_ext = "opus"
    else:
        output_ext = output_format
    
    # 构建输出路径
    output_dir = main_window.output_dir_edit.text()
    if output_dir and os.path.isdir(output_dir):
        # 使用指定的输出目录
        output_filename = f"{input_path.stem}.{output_ext}"
        output_path = os.path.join(output_dir, output_filename)
    else:
        # 使用原始文件所在目录
        output_path = str(input_path.with_suffix(f".{output_ext}"))
    
    # 检查文件是否存在并处理覆盖选项
    if os.path.exists(output_path) and not overwrite_all and not skip_all:
        dialog = FileOverwriteDialog(output_path, main_window)
        if dialog.exec() == QDialog.Accepted:
            action = dialog.get_action()
            
            if action == FileOverwriteDialog.SKIP or action == FileOverwriteDialog.SKIP_ALL:
                # 跳过当前文件
                return {"action": action}
            elif action == FileOverwriteDialog.RENAME:
                # 自动重命名（确保生成的文件名不会覆盖现有文件）
                output_path = dialog.get_renamed_path()
            elif action == FileOverwriteDialog.CANCEL:
                # 取消所有转换
                return {"action": action}
            elif action == FileOverwriteDialog.OVERWRITE or action == FileOverwriteDialog.OVERWRITE_ALL:
                # 覆盖文件 - 使用原路径
                pass
        else:
            # 对话框取消
            return {"action": FileOverwriteDialog.SKIP}
    elif os.path.exists(output_path) and skip_all:
        # 如果设置了skip_all，跳过该文件
        return {"action": FileOverwriteDialog.SKIP}
    
    # 开始处理文件
    # 标记为处理中
    file_info['processing'] = True
    file_info['status'] = '处理中...'
    
    # 获取转换参数
    segment_duration = main_window.segment_duration_spin.value()
    sample_rate = int(main_window.sample_rate_combo.currentText()) if output_format != "auto" else None
    channels = 1 if main_window.channels_combo.currentIndex() == 0 else 2 if output_format != "auto" else None
    bitrate = main_window.bitrate_combo.currentText() if main_window.bitrate_combo.isEnabled() and output_format != "auto" else None

    # 创建处理线程
    from converter_workers import ConversionWorker
    
    worker = ConversionWorker(
        idx, 
        file_info['path'], 
        output_format, 
        segment_duration, 
        sample_rate,
        channels,
        bitrate,
        main_window.ffmpeg_path,
        main_window.split_settings,
        output_path           # 具体输出文件路径
    )
    
    # 连接信号
    worker.signals.started.connect(main_window.on_conversion_started)
    worker.signals.progress.connect(main_window.on_conversion_progress)
    worker.signals.finished.connect(main_window.on_conversion_finished)
    
    # 启动线程
    main_window.thread_pool.start(worker)
    
    # 刷新表格（立即更新UI）
    main_window.refresh_file_table()
    
    return {"action": FileOverwriteDialog.OVERWRITE_ALL if overwrite_all else None}
