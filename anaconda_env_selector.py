import sys
import os
import subprocess
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QComboBox, QPushButton, QLabel, 
                              QFileDialog, QCheckBox, QMessageBox, QGroupBox,
                              QLineEdit)
from PySide6.QtCore import Qt

class AnacondaEnvSelector(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Anaconda环境选择器")
        self.setMinimumSize(600, 350)
        
        # 存储环境信息
        self.environments = []
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建Anaconda路径设置组
        anaconda_group = QGroupBox("Anaconda安装路径")
        anaconda_layout = QHBoxLayout(anaconda_group)
        
        # Anaconda路径输入框
        self.anaconda_path = QLineEdit("H:\\anaconda3")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_anaconda_path)
        
        anaconda_layout.addWidget(self.anaconda_path)
        anaconda_layout.addWidget(browse_btn)
        
        # 创建环境选择组
        env_group = QGroupBox("Anaconda环境")
        env_layout = QVBoxLayout(env_group)
        
        # 环境选择下拉框
        env_label = QLabel("选择Python环境:")
        self.env_combo = QComboBox()
        self.env_combo.setMinimumWidth(400)
        
        # 环境详情标签
        self.env_details = QLabel("环境详情: ")
        
        env_layout.addWidget(env_label)
        env_layout.addWidget(self.env_combo)
        env_layout.addWidget(self.env_details)
        
        # 创建文件选择组
        file_group = QGroupBox("Python文件")
        file_layout = QVBoxLayout(file_group)
        
        # 文件选择部分
        file_select_layout = QHBoxLayout()
        self.file_path = QLabel("未选择文件")
        select_file_btn = QPushButton("选择Python文件")
        select_file_btn.clicked.connect(self.select_python_file)
        
        file_select_layout.addWidget(self.file_path)
        file_select_layout.addWidget(select_file_btn)
        
        # 隐藏窗口选项
        self.hide_window_checkbox = QCheckBox("隐藏运行窗口")
        self.hide_window_checkbox.setChecked(True)
        
        file_layout.addLayout(file_select_layout)
        file_layout.addWidget(self.hide_window_checkbox)
        
        # 创建操作按钮
        action_layout = QHBoxLayout()
        generate_btn = QPushButton("生成VBS文件")
        generate_btn.clicked.connect(self.generate_vbs)
        refresh_btn = QPushButton("刷新环境列表")
        refresh_btn.clicked.connect(self.load_environments)
        
        action_layout.addWidget(refresh_btn)
        action_layout.addWidget(generate_btn)
        
        # 添加所有组件到主布局
        main_layout.addWidget(anaconda_group)
        main_layout.addWidget(env_group)
        main_layout.addWidget(file_group)
        main_layout.addLayout(action_layout)
        
        # 加载环境列表
        self.load_environments()
        
        # 连接环境选择变化信号
        self.env_combo.currentIndexChanged.connect(self.update_env_details)
    
    def browse_anaconda_path(self):
        """浏览选择Anaconda安装路径"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择Anaconda安装目录", self.anaconda_path.text()
        )
        if dir_path:
            self.anaconda_path.setText(dir_path)
            # 重新加载环境列表
            self.load_environments()
    
    def load_environments(self):
        """加载所有Anaconda环境"""
        try:
            self.environments = []
            self.env_combo.clear()
            
            # 获取用户指定的Anaconda路径
            anaconda_dir = self.anaconda_path.text()
            
            if not os.path.exists(anaconda_dir):
                QMessageBox.warning(self, "警告", f"指定的Anaconda路径不存在: {anaconda_dir}")
                return
            
            # 添加base环境
            if os.path.exists(os.path.join(anaconda_dir, "python.exe")):
                self._add_environment("base", anaconda_dir)
            
            # 查找envs目录下的环境
            envs_dir = os.path.join(anaconda_dir, "envs")
            if os.path.exists(envs_dir):
                for env_name in os.listdir(envs_dir):
                    env_path = os.path.join(envs_dir, env_name)
                    if os.path.isdir(env_path) and os.path.exists(os.path.join(env_path, "python.exe")):
                        self._add_environment(env_name, env_path)
            
            # 如果有环境，选择第一个
            if self.environments:
                self.update_env_details(0)
            else:
                QMessageBox.warning(
                    self, 
                    "警告", 
                    f"在指定的Anaconda路径下未找到环境: {anaconda_dir}\n请确认路径是否正确。"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载环境列表失败: {str(e)}")
    
    def _add_environment(self, env_name, env_path):
        """添加环境到列表"""
        try:
            python_path = os.path.join(env_path, "python.exe")
            pythonw_path = os.path.join(env_path, "pythonw.exe")
            
            # 优先使用pythonw.exe
            python_exe = pythonw_path if os.path.exists(pythonw_path) else python_path
            
            # 获取Python版本
            try:
                version_result = subprocess.run(
                    [python_path, "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                python_version = version_result.stdout.strip()
            except Exception:
                python_version = "未知版本"
            
            # 存储环境信息
            env_info = {
                "name": env_name,
                "path": env_path,
                "python_path": python_exe,
                "version": python_version
            }
            
            self.environments.append(env_info)
            self.env_combo.addItem(f"{env_name} ({python_version})")
            return True
        except Exception as e:
            print(f"添加环境 {env_name} 失败: {str(e)}")
            return False
    
    def update_env_details(self, index):
        """更新环境详情显示"""
        if index >= 0 and index < len(self.environments):
            env = self.environments[index]
            details = f"环境名称: {env['name']}\n"
            details += f"Python版本: {env['version']}\n"
            details += f"解释器路径: {env['python_path']}"
            self.env_details.setText(details)
    
    def select_python_file(self):
        """选择Python文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Python文件", "", "Python文件 (*.py)"
        )
        if file_path:
            self.file_path.setText(file_path)
    
    def generate_vbs(self):
        """生成VBS文件"""
        # 检查是否选择了环境
        if not self.environments or self.env_combo.currentIndex() < 0:
            QMessageBox.warning(self, "警告", "请先选择一个Anaconda环境")
            return
        
        # 检查是否选择了Python文件
        python_file = self.file_path.text()
        if python_file == "未选择文件" or not os.path.exists(python_file):
            QMessageBox.warning(self, "警告", "请选择有效的Python文件")
            return
        
        # 获取选中的环境
        env = self.environments[self.env_combo.currentIndex()]
        
        # 确定VBS文件路径
        vbs_file = os.path.splitext(python_file)[0] + ".vbs"
        
        # 确定是否隐藏窗口
        hide_window = self.hide_window_checkbox.isChecked()
        
        # 生成VBS脚本内容
        vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\n'
        vbs_content += 'Set fso = CreateObject("Scripting.FileSystemObject")\n\n'
        vbs_content += "' 获取脚本所在目录\n"
        vbs_content += 'strPath = fso.GetParentFolderName(WScript.ScriptFullName)\n\n'
        
        # 构建命令行 - 使用activate.bat激活环境
        anaconda_dir = self.anaconda_path.text()
        activate_path = os.path.join(anaconda_dir, "Scripts", "activate.bat")
        
        # 确保使用正确的Python解释器
        python_exe = env['python_path']
        # 获取python.exe路径（无论原始路径是python.exe还是pythonw.exe）
        if python_exe.lower().endswith('pythonw.exe'):
            python_exe = python_exe.replace('pythonw.exe', 'python.exe')
        
        # 获取pythonw.exe路径（用于隐藏窗口模式）
        pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
        
        py_filename = os.path.basename(python_file)
        
        if hide_window:
            # 隐藏窗口模式 - 使用pythonw.exe
            vbs_content += "' 使用完整的激活命令并运行程序（隐藏窗口）\n"
            vbs_content += 'cmd = "cmd /c call ""' + activate_path.replace('\\', '\\\\') + '"" ' + env['name'] + ' && " & _\n'
            vbs_content += '      """' + pythonw_exe.replace('\\', '\\\\') + '"" """ & strPath & "\\' + py_filename + '"""\n\n'
            vbs_content += "WshShell.Run cmd, 0, True\n"
        else:
            # 显示窗口和输出模式 - 创建一个批处理文件来运行Python脚本
            bat_file = os.path.splitext(python_file)[0] + "_runner.bat"
            bat_content = '@echo off\n'
            bat_content += 'call "' + activate_path + '" ' + env['name'] + '\n'
            bat_content += 'echo 正在使用环境: ' + env['name'] + '\n'
            bat_content += 'echo 运行Python脚本: ' + py_filename + '\n'
            bat_content += 'echo.\n'
            bat_content += '"' + python_exe + '" "' + python_file + '"\n'
            bat_content += 'echo.\n'
            bat_content += 'echo 脚本执行完毕，按任意键退出...\n'
            bat_content += 'pause > nul\n'
            
            # 写入批处理文件
            try:
                with open(bat_file, "w", encoding="gbk") as f:
                    f.write(bat_content)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"生成批处理文件失败: {str(e)}")
                return
            
            # VBS调用批处理文件
            vbs_content += "' 使用批处理文件运行Python脚本（显示窗口和输出）\n"
            vbs_content += 'batFile = strPath & "\\' + os.path.basename(bat_file) + '"\n'
            vbs_content += 'WshShell.Run "cmd /c """ & batFile & """", 1, False\n'
        
        try:
            # 写入VBS文件
            with open(vbs_file, "w") as f:
                f.write(vbs_content)
            
            QMessageBox.information(
                self, 
                "成功", 
                f"VBS文件已生成: {vbs_file}" + 
                ("" if hide_window else f"\n批处理文件已生成: {bat_file}")
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                "错误", 
                f"生成VBS文件失败: {str(e)}"
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnacondaEnvSelector()
    window.show()
    sys.exit(app.exec()) 