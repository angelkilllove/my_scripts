# 使clients文件夹成为可导入的包
from .groq_client import GroqClient
from .deepgram_client import DeepgramClient

__all__ = ['GroqClient', 'DeepgramClient']
