# Anaconda环境选择器

这是一个使用PySide6开发的GUI应用程序，用于管理Anaconda虚拟环境和Python脚本。

## 功能

- 自动检测并列出系统中所有的Anaconda虚拟环境
- 显示每个环境的详细信息（环境名称、Python版本、解释器路径）
- 选择Python脚本文件
- 生成VBS文件，用于在指定的Anaconda环境中运行Python脚本
- 可选择是否隐藏运行窗口

## 使用要求

- Windows操作系统
- 已安装Anaconda或Miniconda
- PySide6库

## 安装依赖

```bash
pip install PySide6
```

## 使用方法

1. 运行应用程序：
   ```bash
   python anaconda_env_selector.py
   ```

2. 设置Anaconda安装路径：
   - 默认路径为`H:\anaconda3`
   - 如果您的Anaconda安装在其他位置，请点击"浏览..."按钮选择正确的路径
   - 选择正确的路径后，应用程序将自动加载环境列表

3. 在下拉框中选择一个Anaconda环境
4. 点击"选择Python文件"按钮，选择要运行的Python脚本
5. 选择是否隐藏运行窗口（默认隐藏）
6. 点击"生成VBS文件"按钮，生成VBS脚本
7. 生成的VBS文件将保存在Python脚本的同一目录下，文件名与Python脚本相同（扩展名为.vbs）

## VBS文件说明

生成的VBS文件将：
1. 激活选定的Anaconda环境
2. 在该环境中运行选定的Python脚本
3. 根据设置决定是否隐藏命令行窗口

## 注意事项

- 确保Anaconda已正确安装，且可以通过命令行访问
- 如果环境列表为空，请点击"刷新环境列表"按钮重新加载
- 生成的VBS文件可以直接双击运行，无需打开命令行 