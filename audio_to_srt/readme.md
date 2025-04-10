# 音频转文本/SRT工具

这是一个基于AI的音频转文本工具，支持将音频文件转换为SRT字幕或纯文本格式。该工具设计为模块化架构，支持多种API服务和代理设置，特别适合需要高质量文字转写的场景。

## 功能特点

- **多API服务支持**：
  - Groq Whisper API
  - Deepgram API (预留接口)

- **多格式输出**：
  - SRT字幕格式（带时间戳）
  - 纯文本格式

- **多文件批处理**：
  - 支持拖放多个文件
  - 支持多种音频格式（mp3、mp4、wav等）
  - 批量处理多个文件

- **网络代理支持**：
  - HTTP/HTTPS代理
  - SOCKS5代理
  - 支持带认证的代理

- **用户友好界面**：
  - 拖放文件操作
  - 实时进度显示
  - 详细的日志输出

## 系统要求

- Python 3.8+
- PySide6
- 以下依赖项（见requirements.txt）:
  - groq
  - deepgram-sdk (可选)
  - httpx
  - httpx-socks (SOCKS5代理支持)

## 安装方法

1. 确保已安装Python 3.8或以上版本
2. 安装依赖:

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

1. 运行主程序:

```bash
python main_app.py
```

2. 添加Groq API密钥：点击"管理密钥"按钮
3. 拖放音频文件到应用程序窗口，或点击"添加文件"按钮
4. 选择输出格式（SRT或纯文本）
5. 点击"开始转换"按钮

### 代理设置

如果需要通过代理访问API：

1. 点击"代理设置"按钮
2. 选择代理类型（HTTP或SOCKS5）
3. 输入代理地址和端口
4. 如果需要，输入代理认证信息（用户名/密码）
5. 点击"保存"按钮

## 项目结构

- **main_app.py**：程序入口点
- **main_window.py**：主窗口类实现（由多个模块组成）
- **config_manager.py**：配置管理模块
- **api_clients.py**：API客户端模块
- **worker_threads.py**：工作线程模块
- **ui_components.py**：UI组件模块
- **ui_dialogs.py**：UI对话框模块

## 开发扩展

- **添加新API服务**：扩展`api_clients.py`模块，实现`APIClientBase`接口

```python
class NewApiClient(APIClientBase):
    async def transcribe(self, file_path, output_format, language, progress_callback):
        # 实现转写功能
        pass
```

- **添加新输出格式**：扩展格式处理部分

## 常见问题

- **API密钥无效**：确保输入了正确的API密钥，并且账户有足够的额度
- **网络连接问题**：如果在需要代理的网络环境中，请正确配置代理设置
- **文件格式不支持**：确保使用支持的音频格式

## 许可证

本项目采用MIT许可证
