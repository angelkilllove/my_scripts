# utils/timestamp_formatter.py

def format_timestamp(seconds, always_include_hours=True):
    """将秒数转换为SRT格式的时间戳 (HH:MM:SS,mmm)

    参数:
    - seconds: 秒数
    - always_include_hours: 是否总是包含小时部分

    返回:
    - 格式化的时间戳字符串
    """
    # 确保seconds是数值类型
    try:
        seconds = float(seconds)
    except (ValueError, TypeError):
        seconds = 0.0

    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)

    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
