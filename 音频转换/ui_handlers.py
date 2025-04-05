import os
from PySide6.QtWidgets import QMessageBox, QFileDialog, QDialog
from PySide6.QtCore import Qt

from file_operations import process_file_for_conversion, FileOverwriteDialog
from settings_manager import save_main_window_settings, load_main_window_settings


def browse_output_dir(main_window):
    """打开文件夹对话框选择输出目录"""
    dir_path = QFileDialog.getExistingDirectory(
        main_window, "选择输出目录", main_window.output_dir_edit.text() or os.path.expanduser("~")
    )
    if dir_path:
        main_window.output_dir_edit.setText(dir_path)
        return True
    return False


def save_settings(main_window):
    """保存当前设置到配置文件"""
    success, message = save_main_window_settings(main_window)
    if success:
        main_window.statusBar().showMessage("设置已保存", 3000)
    else:
        QMessageBox.warning(main_window, "保存设置失败", message)


def load_settings(main_window):
    """从配置文件加载设置"""
    success, message = load_main_window_settings(main_window)
    if not success:
        print(f"加载设置失败: {message}")


def on_conversion_started(main_window, idx):
    """转换开始的回调"""
    if idx < len(main_window.file_list):
        file_info = main_window.file_list[idx]
        file_info['status'] = '处理中...'

        # 更新表格
        if main_window.file_table.item(idx, 1):
            main_window.file_table.item(idx, 1).setText('处理中...')

        # 更新状态栏
        main_window.update_status_bar()


def on_conversion_progress(main_window, idx, progress):
    """转换进度的回调"""
    if idx < len(main_window.file_list):
        file_info = main_window.file_list[idx]
        file_info['status'] = f'处理中... {progress}%'

        # 更新表格
        if main_window.file_table.item(idx, 1):
            main_window.file_table.item(idx, 1).setText(f'处理中... {progress}%')


def on_conversion_finished(main_window, idx, success, result):
    """转换完成的回调"""
    if idx < len(main_window.file_list):
        file_info = main_window.file_list[idx]
        file_info['processing'] = False
        file_info['completed'] = True

        if success:
            file_info['status'] = f'成功: {result}'
        else:
            file_info['status'] = f'失败: {result}'

        # 刷新表格
        main_window.refresh_file_table()


def start_conversion(main_window):
    """开始转换选中的文件"""
    # 获取选中的行
    selected_rows = sorted(set(index.row() for index in main_window.file_table.selectedIndexes()))

    if not selected_rows:
        QMessageBox.information(main_window, "提示", "请先选择要转换的文件")
        return

    # 检查是否有文件正在处理
    if any(main_window.file_list[row]['processing'] for row in selected_rows if row < len(main_window.file_list)):
        QMessageBox.warning(main_window, "处理中", "有文件正在处理，请等待完成后再开始新的转换。")
        return

    # 检查选中的文件
    valid_files = []
    for row in selected_rows:
        if row < len(main_window.file_list):
            file_info = main_window.file_list[row]
            # 所有文件都可以处理，除非正在处理中
            if not file_info['processing']:
                valid_files.append((row, file_info))

    if not valid_files:
        QMessageBox.information(main_window, "提示", "没有可处理的文件")
        return

    # 获取转换选项
    output_format = main_window.format_combo.currentData()

    # 显示智能分割提示
    if main_window.segment_duration_spin.value() > 0 and main_window.split_settings.get('use_silence_detection', False):
        main_window.statusBar().showMessage("使用智能分割 - 将在静音处分割音频", 3000)

    # 文件覆盖选项
    overwrite_all = False
    skip_all = False

    # 开始转换
    for idx, file_info in valid_files:
        # 处理文件转换
        result = process_file_for_conversion(main_window, idx, file_info, output_format, overwrite_all, skip_all)

        # 检查处理结果
        if result.get("action") == FileOverwriteDialog.OVERWRITE_ALL:
            overwrite_all = True
        elif result.get("action") == FileOverwriteDialog.SKIP_ALL:
            skip_all = True
        elif result.get("action") == FileOverwriteDialog.CANCEL:
            # 用户选择取消所有转换
            break


def start_conversion_all(main_window):
    """开始转换所有非成功文件"""
    # 检查是否有文件正在处理
    if any(f['processing'] for f in main_window.file_list):
        QMessageBox.warning(main_window, "处理中", "有文件正在处理，请等待完成后再开始新的转换。")
        return

    # 检查是否有文件
    valid_files = []
    for idx, file_info in enumerate(main_window.file_list):
        # 所有非成功的文件（未处理和失败的）
        if not file_info['processing'] and not ('成功' in file_info.get('status', '')):
            valid_files.append((idx, file_info))

    if not valid_files:
        QMessageBox.information(main_window, "提示", "没有需要处理的文件")
        return

    # 获取转换选项
    output_format = main_window.format_combo.currentData()

    # 显示智能分割提示
    if main_window.segment_duration_spin.value() > 0 and main_window.split_settings.get('use_silence_detection', False):
        main_window.statusBar().showMessage("使用智能分割 - 将在静音处分割音频", 3000)

    # 文件覆盖选项
    overwrite_all = False
    skip_all = False

    # 开始转换
    for idx, file_info in valid_files:
        # 处理文件转换
        result = process_file_for_conversion(main_window, idx, file_info, output_format, overwrite_all, skip_all)

        # 检查处理结果
        if result.get("action") == FileOverwriteDialog.OVERWRITE_ALL:
            overwrite_all = True
        elif result.get("action") == FileOverwriteDialog.SKIP_ALL:
            skip_all = True
        elif result.get("action") == FileOverwriteDialog.CANCEL:
            # 用户选择取消所有转换
            break


def show_advanced_settings(main_window):
    """显示高级分段设置对话框"""
    # 导入高级设置对话框
    from advanced_settings_dialog import AdvancedSettingsDialog

    dialog = AdvancedSettingsDialog(main_window, main_window.split_settings)
    if dialog.exec() == QDialog.Accepted:
        main_window.split_settings = dialog.get_settings()

        # 如果启用了智能分割，更新状态栏提示
        if main_window.split_settings['use_silence_detection']:
            main_window.statusBar().showMessage("已启用智能分割 - 将在静音处分割音频", 5000)
        else:
            main_window.statusBar().showMessage("智能分割已禁用 - 将按时长均匀分割", 5000)


def refresh_selected_files(main_window):
    """刷新选中的文件状态"""
    selected_rows = sorted(set(index.row() for index in main_window.file_table.selectedIndexes()))

    if not selected_rows:
        QMessageBox.information(main_window, "提示", "请先选择要刷新的文件")
        return

    refreshed_count = 0
    for row in selected_rows:
        if row < len(main_window.file_list):
            file_info = main_window.file_list[row]

            # 如果正在处理中，不能刷新
            if file_info['processing']:
                continue

            # 重置状态
            file_info['status'] = '等待中'
            file_info['audio_info'] = None
            file_info['completed'] = False
            refreshed_count += 1

    if refreshed_count > 0:
        # 刷新表格
        main_window.refresh_file_table()

        # 重新获取音频信息
        main_window.update_audio_info()

        QMessageBox.information(main_window, "刷新完成", f"已刷新 {refreshed_count} 个文件状态")

        # 启用转换按钮
        main_window.convert_button.setEnabled(True)
        main_window.convert_all_button.setEnabled(True)


def refresh_all_files(main_window):
    """刷新所有文件状态"""
    # 检查是否有正在处理中的文件
    if any(f['processing'] for f in main_window.file_list):
        QMessageBox.warning(main_window, "无法刷新", "有文件正在处理中，无法刷新所有文件")
        return

    refreshed_count = 0
    for file_info in main_window.file_list:
        # 重置状态
        file_info['status'] = '等待中'
        file_info['audio_info'] = None
        file_info['completed'] = False
        refreshed_count += 1

    if refreshed_count > 0:
        # 刷新表格
        main_window.refresh_file_table()

        # 重新获取音频信息
        main_window.update_audio_info()

        QMessageBox.information(main_window, "刷新完成", f"已刷新所有 {refreshed_count} 个文件状态")

        # 启用转换按钮
        main_window.convert_button.setEnabled(True)
        main_window.convert_all_button.setEnabled(True)
