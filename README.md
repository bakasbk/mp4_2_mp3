# 视频转 MP3 批量工具

批量把视频文件（含嵌套文件夹）转成 mp3 的桌面小工具。支持拖入 / 选择多个**文件或文件夹**，自动递归提取视频，调用 ffmpeg 转码，并扁平化导出到指定目录。

基于 **Python 3.13 + PySide6 (Qt)** 实现，界面现代、支持拖放、后台线程转换不卡界面。

---

## 功能特性

- **批量拖入 / 选择**：可一次性拖入或添加多个视频文件、或多个文件夹（混合也行）
- **递归扫描**：文件夹无论嵌套多少层，里面的视频都会被递归取出处理
- **常见视频格式**：`mp4 / mkv / avi / mov / wmv / flv / m4v / webm / mpg / mpeg / ts / vob / ogv / 3gp / m2ts / mts` 等
- **实时核对**：右侧「已识别视频」面板逐条列出递归展开后的视频，并显示**总数**，来源一变动即自动重新扫描
- **码率可选**：128k / 192k / 256k / 320k（默认 192k）
- **扁平化导出**：所有 mp3 不保留层级，统一放到你选择的导出目录
- **同名不丢**：导出时遇到同名自动加序号后缀（`lecture.mp3` → `lecture_1.mp3` → `lecture_2.mp3`），不覆盖
- **进度与日志**：进度条 + 实时日志，完成后弹窗汇总成功 / 失败数量

## 界面结构

```
┌─────────────────────────── 视频转 MP3 批量工具 ───────────────────────────┐
│  标题 + 副标题                                                            │
├───────────────────────────────┬──────────────────────────────────────────┤
│  左列（交互区）                │  右列（已识别视频 · 整列）                │
│   ├ 拖放区                     │   ├ 已识别视频：N 个                      │
│   ├ 添加文件/文件夹/移除/清空  │   └ 视频列表（完整路径，可核对）          │
│   ├ 待处理来源列表             │                                            │
│   ├ 导出到（选择/打开目录）    │                                            │
│   ├ 音频码率                   │                                            │
│   ├ 开始转换                   │                                            │
│   ├ 进度条                     │                                            │
│   └ 运行日志                   │                                            │
└───────────────────────────────┴──────────────────────────────────────────┘
```
中间分隔条可拖拽调整左右宽度。

---

## 方式一：直接用打包好的 exe（最简单，无需环境）

`dist/视频转MP3.exe` 是**单文件、免安装**的可执行程序，**已内置 ffmpeg**，即使电脑没装 ffmpeg 也能直接转码。

> 双击即可运行，无需 Python、无需 ffmpeg。

---

## 方式二：从源码运行

### 1. 准备环境

```powershell
# 创建并激活虚拟环境（用受管 Python）
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # PowerShell；CMD 用 .venv\Scripts\activate.bat

# 安装依赖
pip install -r requirements.txt     # 主要是 PySide6
```

### 2. 确保有 ffmpeg

从源码运行需要系统已安装 ffmpeg 且能被找到：

- 推荐：`ffmpeg` 在 `PATH` 中；或
- 放在常见路径（脚本会自动兜底查找）：`C:\app\ffmpeg\...\bin\`、`C:\ffmpeg\bin\`、`C:\ProgramData\chocolatey\bin\` 等

> 找不到 ffmpeg 时，「开始转换」按钮会被禁用并提示。

### 3. 启动

```powershell
.\.venv\Scripts\python.exe main.py
# 或激活环境后： python main.py
```

---

## 方式三：自己重新打包 exe

```powershell
# 1. 安装打包工具（在虚拟环境内）
.\.venv\Scripts\python.exe -m pip install pyinstaller

# 2. 执行打包脚本（自动把 ffmpeg 打进单文件）
.\.venv\Scripts\python.exe build_exe.py
```

产物：`dist/视频转MP3.exe`（单文件，ffmpeg 已内置）。

> 等价手动命令见 `build_exe.py` 内的 `cmd` 构造（含 `--onefile --windowed` 及各 `--add-binary ffmpeg.dll;.`）。

若要**减小体积**、让 exe 依赖系统 PATH 上的 ffmpeg，可去掉 `build_exe.py` 里的 `--add-binary` 并还原 `core.find_ffmpeg` 的内置查找逻辑。

---

## 目录结构

```
mp423/
├── main.py            # 入口：启动 QApplication
├── ui_mainwindow.py   # PySide6 界面（拖放/列表/分栏/进度/日志/转换线程）
├── core.py            # 核心逻辑（find_ffmpeg / discover_videos / unique_mp3_name / convert_one）
├── build_exe.py       # 打包脚本（PyInstaller）
├── requirements.txt   # 依赖
├── 视频转MP3.spec     # PyInstaller 生成的 spec
├── dist/
│   └── 视频转MP3.exe  # 打包产物（单文件、内置 ffmpeg）
└── build/             # PyInstaller 中间产物
```

## 转换原理

每个视频执行（码率可配）：

```bash
ffmpeg -y -i <输入视频> -vn -acodec libmp3lame -b:a <码率> <输出.mp3>
```

`-vn` 去掉视频流，仅保留音频并编码为 mp3。

---

## 常见问题

- **运行时报 `No module named 'PySide6'`**：你用了系统 Python。务必用本项目的 `.venv` 解释器（`.\.venv\Scripts\python.exe main.py`）或先激活虚拟环境。
- **exe 首次启动稍慢**：单文件 exe 每次启动会自解压到临时目录，属正常。
- **某个视频转换失败**：日志会列出失败文件路径，常见原因：文件损坏、编码不支持、或 ffmpeg 缺失（仅源码运行模式）。
