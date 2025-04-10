import sys
import importlib.util
from PySide6.QtWidgets import QApplication, QMessageBox

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 检查关键依赖
    missing_modules = []
    for module_name in ["PySide6", "httpx"]:
        if importlib.util.find_spec(module_name) is None:
            missing_modules.append(module_name)
    
    if missing_modules:
        error_msg = "缺少必要的依赖项: " + ", ".join(missing_modules) + "\n\n"
        error_msg += "请使用以下命令安装依赖:\n"
        error_msg += "pip install " + " ".join(missing_modules)
        
        QMessageBox.critical(None, "依赖错误", error_msg)
        sys.exit(1)
    
    # 导入主窗口类
    try:
        from main_window import MainWindow
        
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec())
    except ImportError as e:
        QMessageBox.critical(None, "导入错误", f"无法导入主窗口类: {str(e)}")
        sys.exit(1)
