"""打包脚本：用 PyInstaller 把程序打包成单文件 exe，并内置 ffmpeg。

运行（需在项目虚拟环境内）：
    .venv\\Scripts\\python.exe build_exe.py

产物：dist\\视频转MP3.exe （免安装、随处可运行；ffmpeg 已内置）
"""
from __future__ import annotations

import os
import subprocess
import sys

# ffmpeg 的 shared 构建目录（含 ffmpeg.exe 与依赖 DLL）
FFMPEG_BIN = r"C:\app\ffmpeg\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\bin"

# 只需要 ffmpeg.exe + 这些运行 DLL（ffplay/ffprobe 用不到，跳过以减小体积）
KEEP = {
    "ffmpeg.exe",
    "avcodec-61.dll", "avdevice-61.dll", "avfilter-10.dll",
    "avformat-61.dll", "avutil-59.dll", "postproc-58.dll",
    "swresample-5.dll", "swscale-8.dll",
}

EXE_NAME = "视频转MP3"


def main() -> int:
    if not os.path.isdir(FFMPEG_BIN):
        print(f"[错误] 找不到 ffmpeg 目录：{FFMPEG_BIN}")
        return 1

    add_bins: list[str] = []
    for name in os.listdir(FFMPEG_BIN):
        if name.lower() in {k.lower() for k in KEEP}:
            src = os.path.join(FFMPEG_BIN, name)
            add_bins += ["--add-binary", f"{src};."]

    if not add_bins:
        print("[错误] 未在 ffmpeg 目录中找到需要打包的文件。")
        return 1

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--windowed", "--onefile",
        "--name", EXE_NAME,
        "--hidden-import", "core",
        "--hidden-import", "ui_mainwindow",
        *add_bins,
        "main.py",
    ]
    print(">>> " + " ".join(cmd))
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
