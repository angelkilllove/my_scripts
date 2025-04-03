import json
import logging
import os
import platform
import sqlite3
import subprocess
import time
import re
import sys
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast

import psutil
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 类型提示
FuncT = TypeVar('FuncT', bound=Callable[..., Any])


# 常量配置
class Config:
    """配置常量类"""
    # API配置
    API_URL = "https://pool.ccursor.org/api/get_next_token.php"
    ACCESS_CODE = ""
    SCRIPT_VERSION = "2025031402"  # 脚本版本号

    APP_NAME = "Cursor"
    # APP_NAME = "Cursor Nightly"

    # 进程配置
    PROCESS_TIMEOUT = 30
    # 需要关闭的Cursor进程
    CURSOR_PROCESS_NAMES = [APP_NAME + '.exe', APP_NAME]

    # 数据库键
    DB_KEYS = {
        'email': 'cursorAuth/cachedEmail',
        'access_token': 'cursorAuth/accessToken',
        'refresh_token': 'cursorAuth/refreshToken'
    }

    # 版本配置
    MIN_PATCH_VERSION = "0.45"  # 需要 patch 的版本
    VERSION_PATTERN = r"^\d+\.\d+"  # 版本号格式

    WINDOWS_APP_NAME_MAP = {
        "Cursor": "cursor",
        "Cursor Nightly": "cursor-nightly"
    }

    CURRENT_WINDOWS_APP_NAME_KEY = WINDOWS_APP_NAME_MAP[APP_NAME]


# 装饰器
def error_handler(func: FuncT) -> FuncT:
    """处理函数执行过程中可能出现的异常"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} 执行时出错: {e}")
            return None if not isinstance(None, type(func.__annotations__.get('return'))) else False

    return cast(FuncT, wrapper)


@dataclass
class TokenData:
    """Token数据类"""
    mac_machine_id: str
    machine_id: str
    dev_device_id: str
    email: str
    token: str

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'TokenData':
        """从字典创建TokenData实例"""
        return cls(
            mac_machine_id=data['mac_machine_id'],
            machine_id=data['machine_id'],
            dev_device_id=data['dev_device_id'],
            email=data['email'],
            token=data['token']
        )


class FilePathManager:
    """文件路径管理器"""
    _OS_PATHS = {
        "Windows": {
            "storage": lambda: Path(os.getenv('APPDATA', '')) / Config.APP_NAME / 'User' / 'globalStorage' / 'storage.json',
            "db": lambda: Path(os.getenv('APPDATA', '')) / Config.APP_NAME / 'User' / 'globalStorage' / 'state.vscdb',
            "app": lambda: Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / Config.CURRENT_WINDOWS_APP_NAME_KEY / "resources",
        },
        "Darwin": {
            "storage": lambda: Path.home() / 'Library' / 'Application Support' / Config.APP_NAME / 'User' / 'globalStorage' / 'storage.json',
            "db": lambda: Path.home() / 'Library' / 'Application Support' / Config.APP_NAME / 'User' / 'globalStorage' / 'state.vscdb',
            "app": lambda: Path(f"/Applications/{Config.APP_NAME}.app/Contents/Resources"),
        },
        "Linux": {
            "storage": lambda: Path.home() / '.config' / Config.APP_NAME / 'User' / 'globalStorage' / 'storage.json',
            "db": lambda: Path.home() / '.config' / Config.APP_NAME / 'User' / 'globalStorage' / 'state.vscdb',
            "app": lambda: None,  # Linux暂不支持获取应用路径, 需要手动解包并修改此处
        }
    }

    @staticmethod
    def _get_path_by_key(key: str) -> Optional[Path]:
        """根据键获取对应的路径"""
        system = platform.system()
        if system not in FilePathManager._OS_PATHS:
            raise OSError(f"不支持的操作系统: {system}，需要手动解包并修改路径")

        path_func = FilePathManager._OS_PATHS[system].get(key)
        return path_func() if path_func else None

    @staticmethod
    def get_storage_path() -> Path:
        """获取storage.json文件路径"""
        path = FilePathManager._get_path_by_key("storage")
        if not path:
            raise OSError(f"无法获取storage路径，不支持的操作系统: {platform.system()}")
        return path

    @staticmethod
    def get_db_path() -> Path:
        """获取数据库文件路径"""
        path = FilePathManager._get_path_by_key("db")
        if not path:
            raise OSError(f"无法获取数据库路径，不支持的操作系统: {platform.system()}")
        return path

    @staticmethod
    def get_cursor_app_paths() -> Tuple[Path, Path]:
        """获取Cursor应用相关路径"""
        base_path = FilePathManager._get_path_by_key("app")
        if not base_path:
            raise OSError(f"无法获取应用路径，不支持的操作系统: {platform.system()}")
        return base_path / "app" / "package.json", base_path / "app" / "out" / "main.js"

    @staticmethod
    def get_update_config_path() -> Optional[Path]:
        """获取更新配置文件路径"""
        base_path = FilePathManager._get_path_by_key("app")
        if not base_path:
            raise OSError(f"无法获取应用路径，不支持的操作系统: {platform.system()}")
        return base_path / "app-update.yml"


class FilePermissionManager:
    """文件权限管理器"""

    @staticmethod
    @error_handler
    def make_file_writable(file_path: Union[str, Path]) -> bool:
        """修改文件权限为可写"""
        file_path = Path(file_path)
        if platform.system() == "Windows":
            subprocess.run(['attrib', '-R', str(file_path)], check=True)
        else:
            os.chmod(file_path, 0o666)
        return True

    @staticmethod
    @error_handler
    def make_file_readonly(file_path: Union[str, Path]) -> bool:
        """修改文件权限为只读"""
        file_path = Path(file_path)
        if platform.system() == "Windows":
            subprocess.run(['attrib', '+R', str(file_path)], check=True)
        else:
            os.chmod(file_path, 0o444)
        return True

    @staticmethod
    @error_handler
    def modify_file(file_path: Path, modifier_func: Callable[[str], str]) -> bool:
        """修改文件内容并创建备份"""
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return False

        # 读取并修改内容
        content = file_path.read_text(encoding="utf-8")
        updated_content = modifier_func(content)

        # 检查内容是否有变化
        if content == updated_content:
            logger.warning(f"文件内容未发生变化，可能已修改或不支持当前版本")
            return False

        # 写入修改后的内容
        FilePermissionManager.make_file_writable(file_path)
        file_path.write_text(updated_content, encoding="utf-8")
        FilePermissionManager.make_file_readonly(file_path)
        return True


class CursorAuthManager:
    """Cursor认证信息管理器"""

    def __init__(self):
        self.db_path = FilePathManager.get_db_path()

    @error_handler
    def update_auth(self, email: Optional[str] = None,
                    access_token: Optional[str] = None,
                    refresh_token: Optional[str] = None) -> bool:
        """更新或插入Cursor的认证信息"""
        updates: List[Tuple[str, str]] = []
        if email is not None:
            updates.append((Config.DB_KEYS['email'], email))
        if access_token is not None:
            updates.append((Config.DB_KEYS['access_token'], access_token))
        if refresh_token is not None:
            updates.append((Config.DB_KEYS['refresh_token'], refresh_token))

        if not updates:
            logger.info("没有提供任何要更新的值")
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for key, value in updates:
                cursor.execute("SELECT 1 FROM itemTable WHERE key = ?", (key,))
                exists = cursor.fetchone() is not None

                if exists:
                    cursor.execute("UPDATE itemTable SET value = ? WHERE key = ?", (value, key))
                else:
                    cursor.execute("INSERT INTO itemTable (key, value) VALUES (?, ?)", (key, value))
                logger.info(f"成功{'更新' if exists else '插入'} {key.split('/')[-1]}")
            return True


class CursorManager:
    """Cursor管理器"""

    @staticmethod
    @error_handler
    def reset_cursor_id(token_data: TokenData) -> bool:
        """重置Cursor ID"""
        storage_path = FilePathManager.get_storage_path()
        if not storage_path.exists():
            logger.warning(f"未找到文件: {storage_path}")
            return False

        def update_storage(content: str) -> str:
            data = json.loads(content)
            data.update({
                "telemetry.macMachineId": token_data.mac_machine_id,
                "telemetry.machineId": token_data.machine_id,
                "telemetry.devDeviceId": token_data.dev_device_id
            })
            return json.dumps(data, indent=4)

        result = FilePermissionManager.modify_file(storage_path, update_storage)
        if result:
            logger.info("Cursor 机器码已成功修改")
        return result

    @staticmethod
    @error_handler
    def exit_cursor() -> bool:
        """安全退出Cursor进程"""
        logger.info("开始退出 " + Config.APP_NAME + "...")

        # 获取所有匹配cursor名称的进程
        cursor_processes = [
            proc for proc in psutil.process_iter(['pid', 'name'])
            if any(name.lower() == proc.info['name'].lower() for name in Config.CURSOR_PROCESS_NAMES)
        ]

        if not cursor_processes:
            logger.info("未发现需要关闭的 " + Config.APP_NAME + " 主进程")
            return True

        # 温和地请求进程终止
        for proc in cursor_processes:
            try:
                if proc.is_running():
                    logger.info(f"正在关闭进程: {proc.info['name']} (PID: {proc.pid})")
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 等待进程终止
        start_time = time.time()
        while time.time() - start_time < Config.PROCESS_TIMEOUT:
            still_running = [p for p in cursor_processes if p.is_running()]
            if not still_running:
                logger.info("所有 " + Config.APP_NAME + " 主进程已正常关闭")
                return True
            time.sleep(0.5)

        still_running = [p for p in cursor_processes if p.is_running()]
        if still_running:
            process_list = ", ".join(f"{p.info['name']} (PID: {p.pid})" for p in still_running)
            logger.warning(f"以下进程未能在规定时间内关闭: {process_list}")
            return False

        return True


class TokenManager:
    """Token管理器"""

    @staticmethod
    @error_handler
    def fetch_token_data(access_code: str, cursor_version: str) -> Optional[TokenData]:
        """获取Token数据"""
        logger.info("正在获取 Token 数据...")

        params = {
            "accessCode": access_code,
            "cursorVersion": cursor_version,
            "scriptVersion": Config.SCRIPT_VERSION
        }
        response = requests.get(Config.API_URL, params=params, timeout=10)

        if response.status_code != 200:
            logger.warning(f"API请求失败: 状态码 {response.status_code}")
            return None

        data = response.json()

        if data.get("code") == 0:
            token_data = data.get("data")
            if token_data:
                logger.info("成功获取 Token 数据")
                return TokenData.from_dict(token_data)

        error_msg = data.get('message', '未知错误')
        logger.warning(f"获取 Token 失败: {error_msg}")
        return None

    @staticmethod
    @error_handler
    def update_token(token_data: TokenData) -> bool:
        """更新Cursor的token信息"""
        # 更新机器ID
        if not CursorManager.reset_cursor_id(token_data):
            return False

        # 更新认证信息
        auth_manager = CursorAuthManager()
        if not auth_manager.update_auth(email=token_data.email, access_token=token_data.token, refresh_token=token_data.token):
            return False

        logger.info(f"成功更新 {Config.APP_NAME} 认证信息! 邮箱: {token_data.email}")
        return True


class Utils:
    """工具类"""

    @staticmethod
    def get_user_confirmation(message: str, default: bool = False) -> bool:
        """获取用户确认"""
        logger.info(f"{message} (y/n)")
        response = input().strip().lower()
        if not response:
            return default
        return response == 'y'

    @staticmethod
    @error_handler
    def version_check(version: str, min_version: str = "", max_version: str = "") -> bool:
        """
        版本号检查

        Args:
            version: 当前版本号
            min_version: 最小版本号要求
            max_version: 最大版本号要求

        Returns:
            bool: 版本号是否符合要求
        """
        if not version or not re.match(Config.VERSION_PATTERN, version):
            logger.error(f"无效的版本号格式: {version}")
            return False

        # 提取版本号
        version = version.split(".")[0:2]
        version = ".".join(version)

        def parse_version(ver: str) -> Tuple[int, ...]:
            return tuple(map(int, ver.split(".")))

        current = parse_version(version)

        if min_version and current < parse_version(min_version):
            return False

        if max_version and current > parse_version(max_version):
            return False

        return True

    @staticmethod
    @error_handler
    def check_files_exist(pkg_path: Path, main_path: Path) -> bool:
        """
        检查文件是否存在

        Args:
            pkg_path: package.json 文件路径
            main_path: main.js 文件路径

        Returns:
            bool: 检查是否通过
        """
        missing_files = []
        for file_path in [pkg_path, main_path]:
            if not file_path.exists():
                missing_files.append(str(file_path))

        if missing_files:
            logger.error(f"以下文件不存在: {', '.join(missing_files)}")
            return False
        return True


class CursorPatcher:
    """Cursor补丁管理器"""

    @staticmethod
    def check_version(version: str) -> bool:
        """检查版本是否需要打补丁"""
        return Utils.version_check(version, min_version=Config.MIN_PATCH_VERSION)

    @staticmethod
    @error_handler
    def patch_main_js(main_path: Path) -> bool:
        """
        修改main.js文件以移除机器码检查

        Args:
            main_path: main.js文件路径

        Returns:
            bool: 修改是否成功
        """

        def apply_patch(content: str) -> str:
            """应用补丁的函数"""
            patterns = {
                r"async getMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMachineId(){return \1}",
                r"async getMacMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMacMachineId(){return \1}"
            }

            # 检查是否存在需要修复的代码
            found_patterns = False
            for pattern in patterns.keys():
                if re.search(pattern, content):
                    found_patterns = True
                    break

            if not found_patterns:
                logger.info("未发现需要修复的代码，可能已经修复或不支持当前版本")
                return content

            # 执行替换
            for pattern, replacement in patterns.items():
                content = re.sub(pattern, replacement, content)

            return content

        result = FilePermissionManager.modify_file(main_path, apply_patch)
        if result:
            logger.info("成功 Patch " + Config.APP_NAME + " 机器码")
        return True


class UpdateManager:
    """更新管理器"""

    @staticmethod
    def disable_auto_update_main() -> None:
        """禁用自动更新主函数"""
        # 检查是否已禁用自动更新
        old_auto_update_disabled = UpdateManager.check_old_auto_update_disabled()
        new_auto_update_disabled = UpdateManager.check_new_auto_update_disabled()

        if old_auto_update_disabled and new_auto_update_disabled:
            logger.info(Config.APP_NAME + " 自动更新已被禁用")
            return

        if Utils.get_user_confirmation("是否要禁用 " + Config.APP_NAME + " 自动更新？", default=False):
            if not old_auto_update_disabled:
                if UpdateManager.disable_old_auto_update():
                    logger.info(Config.APP_NAME + " 旧版自动更新已成功禁用")
                else:
                    logger.warning("禁用旧版自动更新失败，可能不支持当前版本或已禁用")
            if not new_auto_update_disabled:
                if UpdateManager.disable_new_auto_update():
                    logger.info(Config.APP_NAME + " 新版自动更新已成功禁用")
                else:
                    logger.warning("禁用新版自动更新失败，可能不支持当前版本或已禁用")

    @staticmethod
    def check_new_auto_update_disabled() -> bool:
        """检查自动更新是否已被禁用"""
        # 获取main.js文件路径
        _, main_path = FilePathManager.get_cursor_app_paths()

        if not main_path.exists():
            logger.error("无法找到main.js文件，无法检查自动更新状态")
            return False

        try:
            # 读取文件内容
            content = main_path.read_text(encoding="utf-8")
            # 检查是否包含已禁用更新的标记
            return '!!this.args["disable-updates"]' not in content
        except Exception as e:
            logger.error(f"检查自动更新状态时出错: {e}")
            return False

    @staticmethod
    @error_handler
    def disable_new_auto_update() -> bool:
        """禁用自动更新"""
        # 获取main.js文件路径
        _, main_path = FilePathManager.get_cursor_app_paths()

        if not main_path.exists():
            logger.error("无法找到main.js文件，禁用自动更新失败")
            return False

        def update_content(content: str) -> str:
            """更新内容，禁用自动更新"""
            return content.replace('!!this.args["disable-updates"]', 'true')

        result = FilePermissionManager.modify_file(main_path, update_content)
        return result

    @staticmethod
    def check_old_auto_update_disabled() -> bool:
        """检查旧版自动更新是否已被禁用"""
        update_path = FilePathManager.get_update_config_path()
        if not update_path or not update_path.exists():
            logger.info("未找到旧版自动更新配置文件，可能已升级")
            return True
        if update_path.stat().st_size == 0:
            return True
        return False

    @staticmethod
    def disable_old_auto_update() -> bool:
        """禁用旧版自动更新"""
        update_path = FilePathManager.get_update_config_path()
        try:
            # 清空文件内容
            FilePermissionManager.modify_file(update_path, lambda x: "")
            logger.info("已成功禁用旧版自动更新")
            return True

        except Exception as e:
            logger.error(f"禁用旧版自动更新时发生错误: {e}")
            return False


class UserInterface:
    """用户界面类，处理用户交互"""

    @staticmethod
    def display_welcome() -> None:
        """显示欢迎信息"""
        print("\n" + "=" * 60)
        print(f"  {Config.APP_NAME} Token 管理工具 v{Config.SCRIPT_VERSION}")
        print("  支持自动获取 Token 和修补 " + Config.APP_NAME)
        print("=" * 60 + "\n")

    @staticmethod
    def request_access_code() -> str:
        """请求用户输入授权码"""
        print("\n" + "-" * 40)
        print("请输入授权码")
        print("获取地址：https://pool.ccursor.org")
        print("-" * 40)
        return input("授权码: ").strip() or Config.ACCESS_CODE

    @staticmethod
    def wait_for_continue() -> None:
        """等待用户按键继续"""
        time.sleep(0.05)
        input("按回车键继续...")


def main() -> None:
    """主函数"""
    try:
        # 显示欢迎信息
        UserInterface.display_welcome()
        time.sleep(0.05)

        logger.info("提示：本脚本请不要在 " + Config.APP_NAME + " 中执行")

        # 获取Cursor路径
        pkg_path, main_path = FilePathManager.get_cursor_app_paths()

        if not Utils.check_files_exist(pkg_path, main_path):
            logger.warning("请检查是否正确安装 " + Config.APP_NAME)
            return

        # 检查版本
        try:
            cursor_version = json.loads(pkg_path.read_text(encoding="utf-8"))["version"]
            logger.info(f"当前 {Config.APP_NAME} 版本: {cursor_version}")
            need_patch = CursorPatcher.check_version(cursor_version)
            if not need_patch:
                logger.info("当前版本无需 Patch，继续执行 Token 更新...")
        except Exception as e:
            logger.error(f"读取版本信息失败: {e}")
            return

        # 首先退出Cursor
        logger.info("即将退出 " + Config.APP_NAME + "，请确保所有工作已保存。")
        UserInterface.wait_for_continue()

        # 退出Cursor
        if not CursorManager.exit_cursor():
            logger.error("无法关闭 " + Config.APP_NAME + " 进程，请手动关闭后重试")
            return
        logger.info("\n")

        # 执行Patch操作
        if need_patch:
            if not CursorPatcher.patch_main_js(main_path):
                logger.warning("Patch 失败，但程序将继续执行")
            else:
                logger.info("Patch 成功完成")
        logger.info("\n")

        logger.info("从 0.45.xx 开始每次更新都需要重新执行此脚本")
        logger.info("提示：建议禁用 " + Config.APP_NAME + " 自动更新！")
        # 禁用自动更新
        UpdateManager.disable_auto_update_main()
        logger.info("\n")

        # 获取授权码并更新token
        if not Utils.get_user_confirmation("是否获取并替换Token？", default=False):
            logger.info("已取消更新Token")
            return

        # 获取授权码
        access_code = "ac_a22355cf6e71488fade6511438e1a9fd"

        # 获取token数据
        token_data = TokenManager.fetch_token_data(access_code, cursor_version)
        if token_data and TokenManager.update_token(token_data):
            logger.info("Token 更新成功")
        else:
            logger.warning("Token 更新失败")

        logger.info("所有操作已完成，现在可以重新打开 " + Config.APP_NAME + " 体验了")

    except Exception as e:
        logger.error(f"程序执行过程中发生错误: {e}")
        # logger.exception("详细错误信息:")
        sys.exit(1)


if __name__ == "__main__":
    main()
