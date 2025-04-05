import os
import json


class SettingsManager:
    """设置管理类，负责保存和加载程序设置"""

    def __init__(self):
        """初始化设置管理器"""
        self.settings_dir = os.path.join(os.path.expanduser("~"), ".audio_converter")
        self.settings_file = os.path.join(self.settings_dir, "settings.json")
        
        # 确保设置目录存在
        os.makedirs(self.settings_dir, exist_ok=True)

    def save_settings(self, main_window):
        """保存设置到文件"""
        try:
            settings = {
                'output_format': main_window.format_combo.currentData(),
                'output_path': main_window.output_dir_edit.text(),
                'segment_duration': main_window.segment_duration_spin.value(),
                'ffmpeg_path': main_window.ffmpeg_path,
                'sample_rate': main_window.sample_rate_combo.currentText(),
                'channels': main_window.channels_combo.currentIndex(),
                'bitrate': main_window.bitrate_combo.currentText() if main_window.bitrate_combo.isEnabled() else '',
                'split_settings': main_window.split_settings
            }
            
            # 保存设置到文件
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            return True, "设置已保存"
        except Exception as e:
            return False, f"保存设置失败: {str(e)}"

    def load_settings(self, main_window):
        """从文件加载设置"""
        if not os.path.exists(self.settings_file):
            return False, "设置文件不存在"
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # 应用设置到主窗口
            if 'output_format' in settings:
                index = main_window.format_combo.findData(settings['output_format'])
                if index >= 0:
                    main_window.format_combo.setCurrentIndex(index)
            
            if 'output_path' in settings:
                main_window.output_dir_edit.setText(settings['output_path'])
            
            if 'segment_duration' in settings:
                main_window.segment_duration_spin.setValue(float(settings['segment_duration']))
            
            if 'ffmpeg_path' in settings:
                main_window.ffmpeg_path = settings['ffmpeg_path']
            
            if 'sample_rate' in settings:
                index = main_window.sample_rate_combo.findText(settings['sample_rate'])
                if index >= 0:
                    main_window.sample_rate_combo.setCurrentIndex(index)
            
            if 'channels' in settings and 0 <= int(settings['channels']) < main_window.channels_combo.count():
                main_window.channels_combo.setCurrentIndex(int(settings['channels']))
            
            if 'bitrate' in settings and main_window.bitrate_combo.isEnabled():
                index = main_window.bitrate_combo.findText(settings['bitrate'])
                if index >= 0:
                    main_window.bitrate_combo.setCurrentIndex(index)
            
            if 'split_settings' in settings:
                main_window.split_settings = settings['split_settings']
            
            return True, "设置已加载"
        except Exception as e:
            return False, f"加载设置失败: {str(e)}"


def save_main_window_settings(main_window):
    """保存主窗口设置的便捷方法"""
    settings_manager = SettingsManager()
    success, message = settings_manager.save_settings(main_window)
    return success, message


def load_main_window_settings(main_window):
    """加载主窗口设置的便捷方法"""
    settings_manager = SettingsManager()
    success, message = settings_manager.load_settings(main_window)
    return success, message


def show_ffmpeg_settings_dialog(main_window):
    """显示FFmpeg设置对话框"""
    try:
        from ffmpeg_settings_dialog import FFmpegSettingsDialog

        dialog = FFmpegSettingsDialog(main_window, main_window.ffmpeg_path)
        if dialog.exec() == QDialog.Accepted:
            new_path = dialog.get_ffmpeg_path()
            if new_path != main_window.ffmpeg_path:
                main_window.ffmpeg_path = new_path

                # 清除缓存的音频信息
                for file_info in main_window.file_list:
                    if not file_info['processing'] and not file_info['completed']:
                        file_info['audio_info'] = None

                # 重新获取音频信息
                main_window.refresh_file_table()
                main_window.update_audio_info()
                
                # 保存设置
                save_main_window_settings(main_window)
                
                return True, "FFmpeg路径已更新"
        
        return False, "FFmpeg设置未更改"
    except ImportError:
        return False, "无法导入FFmpeg设置对话框"
