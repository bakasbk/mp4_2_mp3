"""核心逻辑：查找 ffmpeg、递归扫描视频、命名冲突处理、单文件转换。

本模块不依赖任何 GUI 库，可单独测试。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# 支持的视频扩展名（小写、不含点）
VIDEO_EXTS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "m4v", "webm",
    "mpg", "mpeg", "ts", "vob", "ogv", "3gp", "m2ts", "mts", "mp4v",
}

# PATH 找不到 ffmpeg 时的常见兜底路径（含本机已发现的路径）
_FFMPEG_CANDIDATES = [
    r"C:\app\ffmpeg\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
]


def find_ffmpeg() -> str | None:
    """返回可用的 ffmpeg 可执行路径；找不到返回 None。

    查找顺序：
    1) PyInstaller 打包后的内置副本（_MEIPASS 或 exe 同目录）
    2) PATH
    3) 常见兜底路径
    """
    # 1) 打包后内置的 ffmpeg（与 DLL 一起被解压到同一目录）
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        bundled = os.path.join(base, "ffmpeg.exe")
        if os.path.isfile(bundled):
            return bundled
    # 2) PATH
    found = shutil.which("ffmpeg")
    if found:
        return found
    # 3) 常见兜底路径
    for cand in _FFMPEG_CANDIDATES:
        if Path(cand).is_file():
            return cand
    return None


def _is_video(path: Path) -> bool:
    return path.suffix.lower().lstrip(".") in VIDEO_EXTS


def discover_videos(paths: list[str]) -> list[str]:
    """将输入的 文件/文件夹 列表展开为视频文件绝对路径列表（去重、排序）。

    - 输入为文件：扩展名匹配则保留
    - 输入为目录：rglob 递归，按扩展名过滤
    - 不存在的路径会被忽略
    """
    result: list[Path] = []
    seen: set[Path] = set()
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for f in pp.rglob("*"):
                if f.is_file() and _is_video(f):
                    key = f.resolve()
                    if key not in seen:
                        seen.add(key)
                        result.append(f)
        elif pp.is_file():
            if _is_video(pp):
                key = pp.resolve()
                if key not in seen:
                    seen.add(key)
                    result.append(pp)
    result.sort(key=lambda x: x.as_posix().lower())
    return [str(p) for p in result]


def unique_mp3_name(stem: str, used: set[str], dst_dir: str) -> Path:
    """在 dst_dir 下生成不重复的 mp3 文件名。

    冲突时追加 _1/_2... 并登记到 used 集合，保证整批扁平导出不互相覆盖。
    """
    base = Path(dst_dir)
    name = f"{stem}.mp3"
    if name not in used and not (base / name).exists():
        used.add(name)
        return base / name
    i = 1
    while True:
        cand = f"{stem}_{i}.mp3"
        if cand not in used and not (base / cand).exists():
            used.add(cand)
            return base / cand
        i += 1


def convert_one(src: str, dst_path: str, ffmpeg: str, bitrate: str = "192k") -> tuple[bool, str]:
    """用 ffmpeg 将单个视频转成 mp3。返回 (是否成功, 信息)。"""
    cmd = [
        ffmpeg, "-y", "-i", src,
        "-vn", "-acodec", "libmp3lame", "-b:a", bitrate,
        dst_path,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except Exception as e:  # 含 FileNotFoundError
        return False, f"启动 ffmpeg 失败: {e}"
    if proc.returncode != 0:
        err_lines = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        return False, "ffmpeg 错误: " + " | ".join(err_lines)[-300:]
    return True, f"已生成 {Path(dst_path).name}"


if __name__ == "__main__":
    print("ffmpeg:", find_ffmpeg())
    print("sample scan:", discover_videos(["."])[:5])
