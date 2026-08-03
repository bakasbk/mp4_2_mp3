# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\avcodec-61.dll', '.'), ('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\avdevice-61.dll', '.'), ('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\avfilter-10.dll', '.'), ('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\avformat-61.dll', '.'), ('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\avutil-59.dll', '.'), ('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\ffmpeg.exe', '.'), ('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\postproc-58.dll', '.'), ('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\swresample-5.dll', '.'), ('C:\\app\\ffmpeg\\ffmpeg-n7.1-latest-win64-gpl-shared-7.1\\bin\\swscale-8.dll', '.')],
    datas=[],
    hiddenimports=['core', 'ui_mainwindow'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='视频转MP3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
