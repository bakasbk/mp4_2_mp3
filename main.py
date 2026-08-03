r"""入口：启动视频转 MP3 批量工具（PySide6）。

运行方式（必须使用本项目虚拟环境的 Python）：
    .venv\Scripts\python.exe main.py
或先激活环境：
    .venv\Scripts\Activate.ps1      # PowerShell
    .venv\Scripts\activate.bat       # CMD
    python main.py
"""
from __future__ import annotations


def main() -> None:
    try:
        from ui_mainwindow import main as _run
    except ModuleNotFoundError as e:
        if "PySide6" in str(e):
            print("错误：未找到 PySide6。请使用本项目虚拟环境的 Python 运行：")
            print('  .\\.venv\\Scripts\\python.exe main.py')
            print("或先激活环境：")
            print("  PowerShell : .\\.venv\\Scripts\\Activate.ps1")
            print("  CMD        : .\\.venv\\Scripts\\activate.bat")
            raise SystemExit(1)
        raise
    _run()


if __name__ == "__main__":
    main()
