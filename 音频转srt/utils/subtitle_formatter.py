# utils/subtitle_formatter.py
import re

def format_subtitle_text(text, max_line_count=2, max_line_width=42):
    """格式化字幕文本
    
    参数:
    - text: 原始文本
    - max_line_count: 最大行数
    - max_line_width: 每行最大字符数
    
    返回:
    - 格式化后的文本
    """
    # 如果文本很短，直接返回
    if len(text) <= max_line_width:
        return text
        
    # 将文本按自然分隔符分割
    # 保留分隔符在分割结果中
    parts = re.split(r'([,.!?;，。！？；])', text)
    
    # 重新组合分隔符和文本
    chunks = []
    current = ""
    for i in range(0, len(parts), 2):
        if i < len(parts):
            part = parts[i]
            # 如果后面有分隔符，加上它
            if i + 1 < len(parts):
                part += parts[i + 1]
            
            # 如果当前行加上新部分不超过限制，添加到当前行
            if len(current) + len(part) <= max_line_width:
                current += part
            else:
                # 否则开始新行
                if current:
                    chunks.append(current)
                current = part
    
    # 添加最后一行
    if current:
        chunks.append(current)
        
    # 限制行数
    if len(chunks) > max_line_count:
        # 如果超过最大行数，合并多余的行
        remaining_text = " ".join(chunks[max_line_count-1:])
        chunks = chunks[:max_line_count-1]
        
        # 将剩余文本截断到适合最后一行的长度
        if len(remaining_text) > max_line_width:
            remaining_text = remaining_text[:max_line_width-3] + "..."
            
        chunks.append(remaining_text)
        
    # 拼接结果
    return "\n".join(chunks)


