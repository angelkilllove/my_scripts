import os
import configparser
import json
from typing import Dict, Any, Optional

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

# 默认配置
DEFAULT_CONFIG = {
    "Settings": {
        "output_format": "srt",
        "api_service": "groq",  # 默认使用Groq，预留deepgram支持
        "last_used_key_name": "",
        "last_used_deepgram_key_name": "",
        "last_directory": ""  # 新增：上次打开的目录
    },
    "APIKeys": {},
    "DeepgramKeys": {},  # 预留给Deepgram API密钥
    "GroqProxy": {
        "enabled": "False",
        "type": "http",
        "host": "",
        "port": "",
        "username": "",
        "password": ""
    },
    "DeepgramProxy": {
        "enabled": "False",
        "type": "http",
        "host": "",
        "port": "",
        "username": "",
        "password": ""
    },
    "ConversionSettings": {
        # 默认转换设置，JSON格式保存
        "settings": "{}"
    }
}


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()

    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(CONFIG_FILE):
        for section, items in DEFAULT_CONFIG.items():
            config[section] = items

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE, encoding='utf-8')

        # 确保所有必要的部分都存在
        for section, items in DEFAULT_CONFIG.items():
            if section not in config:
                config[section] = {}

            # 确保每个部分都有必要的键
            for key, value in items.items():
                if key not in config[section]:
                    config[section][key] = value

    return config


def save_config(config):
    """保存配置到文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)


def get_proxy_settings(service="groq"):
    """获取代理设置"""
    config = load_config()
    section = f"{service.capitalize()}Proxy"

    if section not in config:
        return ""

    if config[section].getboolean("enabled", fallback=False):
        proxy_type = config[section].get("type", "http")
        host = config[section].get("host", "")
        port = config[section].get("port", "")
        username = config[section].get("username", "")
        password = config[section].get("password", "")

        if not host or not port:
            return ""

        # 构建代理字符串
        prefix = "socks5://" if proxy_type == "socks5" else "http://"

        if username and password:
            return f"{prefix}{username}:{password}@{host}:{port}"
        else:
            return f"{prefix}{host}:{port}"
    else:
        return ""


def get_proxy_details(service="groq"):
    """获取代理详细设置"""
    config = load_config()
    section = f"{service.capitalize()}Proxy"

    if section not in config:
        return DEFAULT_CONFIG[section]

    return dict(config[section])


def save_proxy_settings(settings, service="groq"):
    """保存代理设置

    参数:
    - settings: 代理设置字典
      {
        "enabled": True/False,
        "type": "http"/"socks5",
        "host": 主机地址,
        "port": 端口,
        "username": 用户名(可选),
        "password": 密码(可选)
      }
    - service: 服务名称("groq"或"deepgram")
    """
    config = load_config()
    section = f"{service.capitalize()}Proxy"

    if section not in config:
        config[section] = {}

    for key, value in settings.items():
        if key in ["enabled", "type", "host", "port", "username", "password"]:
            config[section][key] = str(value)

    save_config(config)


def get_last_directory():
    """获取上次打开的目录"""
    config = load_config()
    return config['Settings'].get('last_directory', '')


def save_last_directory(directory):
    """保存上次打开的目录"""
    config = load_config()
    config['Settings']['last_directory'] = directory
    save_config(config)


def get_last_used_key_name(service="groq"):
    """获取上次使用的API密钥名称"""
    config = load_config()
    if service == "deepgram":
        return config['Settings'].get('last_used_deepgram_key_name', '')
    return config['Settings'].get('last_used_key_name', '')


def get_last_used_key(service="groq"):
    """获取上次使用的API密钥值"""
    config = load_config()
    key_name = ""
    if service == "deepgram":
        key_name = config['Settings'].get('last_used_deepgram_key_name', '')
        if key_name and key_name in config['DeepgramKeys']:
            return config['DeepgramKeys'][key_name]
    else:
        key_name = config['Settings'].get('last_used_key_name', '')
        if key_name and key_name in config['APIKeys']:
            return config['APIKeys'][key_name]
    return ""


def get_output_format():
    """获取输出格式设置"""
    config = load_config()
    return config['Settings']['output_format']


def get_api_service():
    """获取当前使用的API服务"""
    config = load_config()
    return config['Settings']['api_service']


def save_last_used_key(key, service="groq"):
    """保存上次使用的API密钥

    参数:
    - key: API密钥值
    - service: 服务名称
    """
    config = load_config()
    key_name = ""

    # 查找密钥对应的名称
    if service == "deepgram":
        for name, value in config['DeepgramKeys'].items():
            if value == key:
                key_name = name
                break
        config['Settings']['last_used_deepgram_key_name'] = key_name
    else:
        for name, value in config['APIKeys'].items():
            if value == key:
                key_name = name
                break
        config['Settings']['last_used_key_name'] = key_name

    save_config(config)


def save_output_format(format_type):
    """保存输出格式设置"""
    config = load_config()
    config['Settings']['output_format'] = format_type
    save_config(config)


def save_api_service(service):
    """保存当前使用的API服务"""
    config = load_config()
    config['Settings']['api_service'] = service
    save_config(config)


def get_api_keys(service="groq"):
    """获取所有API密钥"""
    config = load_config()
    if service == "deepgram":
        return dict(config['DeepgramKeys'])
    return dict(config['APIKeys'])


def add_api_key(name, key, service="groq"):
    """添加API密钥"""
    config = load_config()
    if service == "deepgram":
        config['DeepgramKeys'][name] = key
    else:
        config['APIKeys'][name] = key
    save_config(config)


def remove_api_key(name, service="groq"):
    """删除API密钥"""
    config = load_config()
    section = 'DeepgramKeys' if service == "deepgram" else 'APIKeys'

    if name in config[section]:
        del config[section][name]
        save_config(config)


def get_conversion_settings():
    """获取转换设置"""
    config = load_config()
    # 修复：使用字符串访问ConversionSettings节
    if 'ConversionSettings' in config:
        settings_json = config['ConversionSettings'].get('settings', '{}')
    else:
        settings_json = '{}'

    try:
        return json.loads(settings_json)
    except json.JSONDecodeError:
        return {}


def save_conversion_settings(settings):
    """保存转换设置

    参数:
    - settings: 设置字典
    """
    config = load_config()
    if 'ConversionSettings' not in config:
        config['ConversionSettings'] = {}

    config['ConversionSettings']['settings'] = json.dumps(settings)
    save_config(config)