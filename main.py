"""VoiceMeeter MP3-to-Mic 一键切换工具 — 入口。

启动 tkinter GUI, 提供一键切换音频路由的功能。
需要以管理员权限运行 (切换默认音频设备需要)。

用法:
    python main.py
    或双击 launcher.bat (自动请求管理员权限)
"""

import sys
import os


def check_admin() -> bool:
    """检测是否以管理员权限运行。"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def main():
    # 延迟导入 GUI, 以便在导入失败时给出友好错误
    try:
        from toggle_app import ToggleApp
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请先安装依赖: pip install -r requirements.txt")
        sys.exit(1)

    if not check_admin():
        print("⚠ 警告: 未以管理员权限运行")
        print("  切换 Windows 默认音频设备需要管理员权限")
        print("  请使用 launcher.bat 启动, 或右键以管理员运行")
        # 不阻止运行, VoiceMeeter 层面的路由切换不需要管理员

    app = ToggleApp()
    app.run()


if __name__ == "__main__":
    main()
