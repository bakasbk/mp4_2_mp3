"""PySide6 主界面：拖放区、来源列表、已识别视频面板、导出目录选择、进度与日志。"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSplitter, QVBoxLayout,
    QWidget,
)

from core import convert_one, discover_videos, find_ffmpeg, unique_mp3_name

STYLE = """
QWidget {
    background-color: #f5f7fa;
    color: #1f2933;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}
QFrame#dropArea {
    background-color: #ffffff;
    border: 2px dashed #c3ccd9;
    border-radius: 12px;
}
QFrame#dropArea QLabel { color: #6b7785; }
QLabel#title { font-size: 19px; font-weight: 600; color: #14233a; }
QLabel#subtitle { color: #6b7785; }
QLabel#section { font-weight: 600; color: #33415c; margin-top: 4px; }
QPushButton {
    background-color: #2f6fed; color: white; border: none;
    border-radius: 8px; padding: 8px 14px; font-weight: 500;
}
QPushButton:hover { background-color: #1f5bdb; }
QPushButton:disabled { background-color: #b8c2d0; }
QPushButton#secondary { background-color: #eef2f7; color: #1f2933; }
QPushButton#secondary:hover { background-color: #e0e7f0; }
QPushButton#start { background-color: #1aa179; font-size: 15px; padding: 10px; }
QPushButton#start:hover { background-color: #158c69; }
QListWidget, QPlainTextEdit, QLineEdit, QComboBox {
    background-color: #ffffff; border: 1px solid #d6dde6; border-radius: 8px;
}
QListWidget::item:selected { background-color: #d6e4ff; color: #1f2933; }
QProgressBar {
    border: 1px solid #d6dde6; border-radius: 6px;
    background-color: #ffffff; text-align: center; height: 20px;
}
QProgressBar::chunk { background-color: #2f6fed; border-radius: 5px; }
"""


class DropArea(QFrame):
    """可接受文件/文件夹拖放的虚线框区域。"""

    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(96)
        lay = QVBoxLayout(self)
        lbl = QLabel("拖拽 文件 / 文件夹 到此处")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 15px; font-weight: 600; color:#33415c;")
        sub = QLabel("支持批量：多个视频文件，或含视频的文件夹（递归处理所有层级内的视频）")
        sub.setAlignment(Qt.AlignCenter)
        lay.addStretch()
        lay.addWidget(lbl)
        lay.addWidget(sub)
        lay.addStretch()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()


class ScannerWorker(QThread):
    """后台线程：扫描来源，递归展开为视频文件列表，避免大目录卡界面。"""

    done = Signal(list)

    def __init__(self, inputs: list[str]) -> None:
        super().__init__()
        self.inputs = inputs

    def run(self) -> None:
        self.done.emit(discover_videos(self.inputs))


class ConversionWorker(QThread):
    """后台线程：顺序转换，逐个发送进度与日志。"""

    progress = Signal(int, int)        # done, total
    log = Signal(str)                  # 单行日志
    finished = Signal(int, int, list)  # ok, fail, failed_list

    def __init__(self, inputs: list[str], out_dir: str, ffmpeg: str, bitrate: str) -> None:
        super().__init__()
        self.inputs = inputs
        self.out_dir = out_dir
        self.ffmpeg = ffmpeg
        self.bitrate = bitrate

    def run(self) -> None:
        videos = discover_videos(self.inputs)
        total = len(videos)
        if total == 0:
            self.log.emit("未找到任何视频文件。")
            self.finished.emit(0, 0, [])
            return

        used: set[str] = set()
        ok = 0
        fail = 0
        failed: list[str] = []
        for i, src in enumerate(videos, 1):
            name = Path(src).name
            self.log.emit(f"[{i}/{total}] 处理: {name}")
            dst = unique_mp3_name(Path(src).stem, used, self.out_dir)
            success, msg = convert_one(src, str(dst), self.ffmpeg, self.bitrate)
            if success:
                ok += 1
                self.log.emit(f"  ✓ {msg}")
            else:
                fail += 1
                failed.append(src)
                self.log.emit(f"  ✗ {msg}")
            self.progress.emit(i, total)
        self.finished.emit(ok, fail, failed)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("视频转 MP3 批量工具")
        self.resize(1120, 700)
        self.setMinimumSize(880, 560)

        self.out_dir: str | None = None
        self.ffmpeg = find_ffmpeg()
        self.worker: ConversionWorker | None = None
        self.scanner: ScannerWorker | None = None
        self._scan_token = 0

        self._build_ui()
        self._refresh_ffmpeg_state()

    # ---------- UI 构建 ----------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # 顶部标题（跨整行）
        title = QLabel("视频转 MP3 批量工具")
        title.setObjectName("title")
        subtitle = QLabel("批量选择或拖入视频文件/文件夹，递归提取音频并扁平导出为 mp3")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        # 左右分栏：左=原交互结构，右=已识别视频(整列)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setContentsMargins(0, 0, 0, 0)

        # ===== 左列：原结构 =====
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(12)

        # 拖放区
        self.drop = DropArea()
        self.drop.files_dropped.connect(self.add_items)
        lv.addWidget(self.drop)

        # 按钮行
        btn_row = QHBoxLayout()
        self.btn_files = QPushButton("添加文件")
        self.btn_dir = QPushButton("添加文件夹")
        self.btn_remove = QPushButton("移除选中")
        self.btn_remove.setObjectName("secondary")
        self.btn_clear = QPushButton("清空")
        self.btn_clear.setObjectName("secondary")
        self.btn_files.clicked.connect(self.on_add_files)
        self.btn_dir.clicked.connect(self.on_add_dir)
        self.btn_remove.clicked.connect(self.on_remove_selected)
        self.btn_clear.clicked.connect(self.on_clear)
        for b in (self.btn_files, self.btn_dir, self.btn_remove, self.btn_clear):
            btn_row.addWidget(b)
        btn_row.addStretch()
        lv.addLayout(btn_row)

        # 待处理来源列表
        src_label = QLabel("待处理来源（拖入的文件/文件夹）：")
        src_label.setObjectName("section")
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        lv.addWidget(src_label)
        lv.addWidget(self.list, 1)

        # 导出目录
        out_row = QHBoxLayout()
        out_label = QLabel("导出到：")
        out_label.setObjectName("section")
        self.out_edit = QLabel("（未选择）")
        self.out_edit.setStyleSheet("color:#6b7785; padding:4px 8px; background:#fff; border:1px solid #d6dde6; border-radius:8px;")
        self.btn_out = QPushButton("选择导出文件夹")
        self.btn_open = QPushButton("打开导出文件夹")
        self.btn_open.setObjectName("secondary")
        self.btn_out.clicked.connect(self.on_choose_out)
        self.btn_open.clicked.connect(self.on_open_out)
        out_row.addWidget(out_label)
        out_row.addWidget(self.out_edit, 1)
        out_row.addWidget(self.btn_out)
        out_row.addWidget(self.btn_open)
        lv.addLayout(out_row)

        # 选项行
        opt_row = QHBoxLayout()
        bitrate_label = QLabel("音频码率：")
        bitrate_label.setObjectName("section")
        self.bitrate = QComboBox()
        self.bitrate.addItems(["128k", "192k", "256k", "320k"])
        self.bitrate.setCurrentText("192k")
        self.bitrate.setFixedWidth(90)
        opt_row.addWidget(bitrate_label)
        opt_row.addWidget(self.bitrate)
        opt_row.addStretch()
        lv.addLayout(opt_row)

        # 开始按钮
        self.btn_start = QPushButton("开始转换")
        self.btn_start.setObjectName("start")
        self.btn_start.clicked.connect(self.on_start)
        lv.addWidget(self.btn_start)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setValue(0)
        lv.addWidget(self.progress)

        # 日志
        log_label = QLabel("运行日志：")
        log_label.setObjectName("section")
        lv.addWidget(log_label)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(150)
        lv.addWidget(self.log)

        # ===== 右列：已识别视频（占整列）=====
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(8)
        self.video_count = QLabel("已识别视频：0 个")
        self.video_count.setObjectName("section")
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        rv.addWidget(self.video_count)
        rv.addWidget(self.video_list, 1)

        # 放入分栏
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)   # 左列稍宽
        splitter.setStretchFactor(1, 2)   # 右列整列显示视频
        root.addWidget(splitter, 1)

    # ---------- 来源列表管理 ----------
    def add_items(self, paths: list[str]) -> None:
        existing = {self.list.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self.list.count())}
        added = 0
        for p in paths:
            if p in existing:
                continue
            item = QListWidgetItem(p)
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.list.addItem(item)
            existing.add(p)
            added += 1
        # 若尚未选择导出目录，默认用第一个来源的父目录
        if added and not self.out_dir and self.list.count():
            first = Path(self.list.item(0).data(Qt.ItemDataRole.UserRole))
            default = first.parent if first.is_file() else first
            self._set_out_dir(str(default))
        # 来源变了，重新扫描右侧视频列表
        self.refresh_scan()

    def on_add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.m4v *.webm *.mpg *.mpeg *.ts *.vob *.ogv *.3gp);;所有文件 (*.*)",
        )
        if files:
            self.add_items(files)

    def on_add_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.add_items([folder])

    def on_remove_selected(self) -> None:
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        self.refresh_scan()

    def on_clear(self) -> None:
        self.list.clear()
        self.refresh_scan()

    # ---------- 递归扫描（右侧面板）----------
    def refresh_scan(self) -> None:
        """依据左侧来源，后台递归扫描出所有视频，刷新右侧列表与计数。"""
        inputs = [self.list.item(i).data(Qt.ItemDataRole.UserRole)
                  for i in range(self.list.count())]
        if not inputs:
            self.video_list.clear()
            self.video_count.setText("已识别视频：0 个")
            return
        self.video_count.setText("已识别视频：扫描中…")
        self._scan_token += 1
        token = self._scan_token
        self.scanner = ScannerWorker(inputs)
        self.scanner.done.connect(lambda vids: self._on_scan_done(vids, token))
        self.scanner.start()

    def _on_scan_done(self, vids: list[str], token: int) -> None:
        if token != self._scan_token:
            return  # 已有更新的扫描，丢弃过时结果
        self.video_list.clear()
        for v in vids:
            item = QListWidgetItem(v)
            item.setToolTip(v)
            self.video_list.addItem(item)
        self.video_count.setText(f"已识别视频：{len(vids)} 个")

    # ---------- 导出目录 ----------
    def on_choose_out(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹", self.out_dir or "")
        if folder:
            self._set_out_dir(folder)

    def _set_out_dir(self, path: str) -> None:
        self.out_dir = path
        self.out_edit.setText(path)
        self.out_edit.setStyleSheet("color:#1f2933; padding:4px 8px; background:#fff; border:1px solid #d6dde6; border-radius:8px;")

    def on_open_out(self) -> None:
        if self.out_dir and Path(self.out_dir).is_dir():
            try:
                os.startfile(self.out_dir)  # type: ignore[attr-defined]
            except Exception as e:  # noqa: BLE001
                self.append_log(f"无法打开文件夹: {e}")

    # ---------- ffmpeg 状态 ----------
    def _refresh_ffmpeg_state(self) -> None:
        if not self.ffmpeg:
            self.btn_start.setEnabled(False)
            self.append_log("⚠ 未检测到 ffmpeg，请安装后重试（开始按钮已禁用）。")

    # ---------- 转换流程 ----------
    def on_start(self) -> None:
        inputs = [self.list.item(i).data(Qt.ItemDataRole.UserRole)
                  for i in range(self.list.count())]
        if not inputs:
            QMessageBox.information(self, "提示", "请先添加视频文件或文件夹。")
            return
        if not self.out_dir or not Path(self.out_dir).is_dir():
            QMessageBox.information(self, "提示", "请先选择导出文件夹。")
            return
        if not self.ffmpeg:
            QMessageBox.critical(self, "缺少 ffmpeg", "未找到 ffmpeg，无法转换。")
            return

        self._set_controls_enabled(False)
        self.log.clear()
        self.progress.setValue(0)
        self.append_log(f"开始转换，共 {len(discover_videos(inputs))} 个视频文件 → {self.out_dir}")

        self.worker = ConversionWorker(
            inputs, self.out_dir, self.ffmpeg, self.bitrate.currentText()
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, done: int, total: int) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def on_finished(self, ok: int, fail: int, failed: list[str]) -> None:
        self._set_controls_enabled(True)
        summary = f"转换完成：成功 {ok} 个，失败 {fail} 个。"
        self.append_log(summary)
        if failed:
            self.append_log("失败文件：")
            for f in failed[:30]:
                self.append_log("  - " + f)
        QMessageBox.information(self, "完成", summary)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.btn_start.setEnabled(enabled and bool(self.ffmpeg))
        self.btn_files.setEnabled(enabled)
        self.btn_dir.setEnabled(enabled)
        self.btn_remove.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        self.btn_out.setEnabled(enabled)
        self.bitrate.setEnabled(enabled)

    def append_log(self, text: str) -> None:
        self.log.appendPlainText(text)


def main() -> None:
    app = QApplication([])
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
