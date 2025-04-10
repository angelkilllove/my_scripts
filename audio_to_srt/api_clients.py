# 兼容性修复
try:
    # 检查typing_extensions是否有TypeIs
    import typing_extensions

    if 'TypeIs' not in dir(typing_extensions):
        import sys
        import types

        # 简单添加缺失的TypeIs
        typing_extensions.TypeIs = types.SimpleNamespace
        sys.modules['typing_extensions'].TypeIs = typing_extensions.TypeIs
        print("[DEBUG] 已添加TypeIs到typing_extensions模块")
except Exception as e:
    print(f"[DEBUG] typing_extensions兼容性修复失败: {e}")

import asyncio
from typing import Optional, Dict, Any, Callable, List
import os
import sys
import traceback
import json
from abc import ABC, abstractmethod
import importlib.util

# 从工具包导入格式化工具
from utils.subtitle_formatter import format_subtitle_text
from utils.timestamp_formatter import format_timestamp

# 增加详细调试输出
debug_info = []


def print_debug(msg):
    """输出调试信息到控制台并保存"""
    print(f"[DEBUG] {msg}")
    debug_info.append(msg)
    sys.stdout.flush()  # 确保立即输出


# 检查Python版本
print_debug(f"Python版本: {sys.version}")
print_debug(f"Python路径: {sys.executable}")

# 检查必要的依赖
def check_module(module_name):
    """详细检查模块是否可用"""
    print_debug(f"检查模块 {module_name}...")
    try:
        module = __import__(module_name)
        print_debug(f"成功导入模块 {module_name}")
        return True, module
    except ImportError as e:
        print_debug(f"无法导入模块 {module_name}: {e}")
    except Exception as e:
        print_debug(f"导入模块 {module_name} 时发生错误: {e}")
    return False, None


# 检查必要的依赖
httpx_available, _ = check_module("httpx")
HTTPX_AVAILABLE = httpx_available

socks_available, _ = check_module("httpx_socks")
SOCKS_AVAILABLE = socks_available

groq_available, _ = check_module("groq")
GROQ_AVAILABLE = groq_available

deepgram_available, _ = check_module("deepgram")
DEEPGRAM_AVAILABLE = deepgram_available

# 显示环境概述
print_debug(f"环境概述: HTTPX={HTTPX_AVAILABLE}, SOCKS={SOCKS_AVAILABLE}, GROQ={GROQ_AVAILABLE}, DEEPGRAM={DEEPGRAM_AVAILABLE}")


class APIClientBase(ABC):
    """API客户端基类"""

    def __init__(self, api_key: str, proxy: Optional[str] = None):
        self.api_key = api_key
        self.proxy = proxy

    @abstractmethod
    async def transcribe(self,
                         file_path: str,
                         output_format: str = "srt",
                         language: Optional[str] = None,
                         progress_callback: Optional[Callable] = None,
                         **kwargs) -> str:
        """
        转写音频文件

        参数:
        - file_path: 音频文件路径
        - output_format: 输出格式
        - language: 语言代码（可选）
        - progress_callback: 进度回调函数
        - **kwargs: 附加选项

        返回:
        - 输出文件路径
        """
        pass

    @abstractmethod
    def close(self):
        """关闭连接"""
        pass


# 导入具体实现客户端
from clients.groq_client import GroqClient
from clients.deepgram_client import DeepgramClient


def create_client(service: str, api_key: str, proxy: Optional[str] = None) -> APIClientBase:
    """
    创建API客户端

    参数:
    - service: 服务类型 ("groq" 或 "deepgram")
    - api_key: API密钥
    - proxy: 代理设置 (可选)

    返回:
    - API客户端实例
    """
    print_debug(f"创建API客户端: service={service}")

    if service == "groq":
        return GroqClient(api_key, proxy)
    elif service == "deepgram":
        return DeepgramClient(api_key, proxy)
    else:
        error_msg = f"不支持的服务类型: {service}"
        print_debug(error_msg)
        raise ValueError(error_msg)


# 初始模块加载是否成功的诊断信息
def get_diagnostics():
    """获取诊断信息"""
    return {
        "debug_info": debug_info,
        "httpx_available": HTTPX_AVAILABLE,
        "socks_available": SOCKS_AVAILABLE,
        "groq_available": GROQ_AVAILABLE,
        "deepgram_available": DEEPGRAM_AVAILABLE
    }