from pydub import AudioSegment
from pydub.effects import normalize
import os


class AudioProcessor:
    """
    提供简单的音频处理功能，主要用于优化语音识别
    """
    
    def __init__(self):
        pass
    
    def process_audio(self, input_path, output_path, 
                      apply_high_pass=False, 
                      apply_speech_enhance=False, 
                      apply_normalize=False):
        """
        应用处理到音频文件
        
        参数:
            input_path (str): 输入音频文件路径
            output_path (str): 输出音频文件路径
            apply_high_pass (bool): 是否应用高通滤波器
            apply_speech_enhance (bool): 是否应用语音增强
            apply_normalize (bool): 是否应用音量归一化
            
        返回:
            str: 处理后音频文件的路径
        """
        # 如果不需要任何处理，直接返回原文件路径
        if not (apply_high_pass or apply_speech_enhance or apply_normalize):
            # 如果输入和输出路径相同，直接返回
            if input_path == output_path:
                return input_path
            # 否则复制文件
            else:
                audio = AudioSegment.from_file(input_path)
                audio.export(output_path, format=os.path.splitext(output_path)[1][1:])
                return output_path
        
        # 加载音频
        audio = AudioSegment.from_file(input_path)
        
        # 应用高通滤波器
        if apply_high_pass:
            audio = self._apply_high_pass_filter(audio)
        
        # 应用语音增强
        if apply_speech_enhance:
            audio = self._enhance_speech(audio)
        
        # 应用归一化
        if apply_normalize:
            audio = self._normalize_audio(audio)
        
        # 确定输出格式
        output_format = os.path.splitext(output_path)[1][1:]
        
        # 导出处理后的音频
        audio.export(output_path, format=output_format)
        
        return output_path
    
    def _apply_high_pass_filter(self, audio, cutoff_freq=300):
        """
        应用高通滤波器去除低频噪音
        """
        return audio.high_pass_filter(cutoff_freq)
    
    def _enhance_speech(self, audio):
        """
        增强300Hz-3kHz范围的频率，这是人声的主要频率范围
        """
        # 通过组合高通和低通滤波器来创建带通滤波器效果
        return audio.high_pass_filter(300).low_pass_filter(3000)
    
    def _normalize_audio(self, audio, target_dBFS=-20):
        """
        归一化音频的音量
        """
        # 使用pydub自带的normalize效果
        return normalize(audio, target_dBFS)
