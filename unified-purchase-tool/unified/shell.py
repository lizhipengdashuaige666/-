from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

# 添加两个子项目的路径
_NAMING_PROJECT = Path(r"C:\Users\19811\.claude\projects\pdf-windows-11-python-3-12")
_WORKBENCH_PROJECT = Path(r"C:\Users\19811\.claude\projects\wechat-wxwork-text-purchase-workbench-main")
sys.path.insert(0, str(_NAMING_PROJECT))
sys.path.insert(0, str(_WORKBENCH_PROJECT))

from app.config import load_config
from app.gui import ContractRenameApp
from gui.app import PurchaseWorkbench

from unified import style


class UnifiedApp(QMainWindow):
    """统一采购工具壳 — 侧栏导航 + 业务页面"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("采购工作台")
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)

        # ── 加载主题 ──
        self._theme_overrides = style.load_theme()

        # ── 加载配置 ──
        self.naming_config = load_config(_NAMING_PROJECT)

        # ── 创建页面 ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {style.BG};")
        self.rename_page = ContractRenameApp(self.naming_config, parent=self, shell=self)
        self.workbench_page = PurchaseWorkbench(parent=self, shell=self)
        self.stack.addWidget(self.rename_page)     # index 0
        self.stack.addWidget(self.workbench_page)  # index 1

        # ── 侧栏 ──
        self._nav_buttons: list[QPushButton] = []
        sidebar = self._build_sidebar()

        # ── 布局 ──
        body = QWidget()
        hbox = QHBoxLayout(body)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addWidget(sidebar)
        hbox.addWidget(self.stack, 1)
        self.setCentralWidget(body)

        self.setStyleSheet(style.build(self._theme_overrides))
        self.stack.setCurrentIndex(0)
        if self._nav_buttons:
            self._nav_buttons[0].setChecked(True)

    # ── 侧栏 ──────────────────────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        w = QFrame()
        w.setObjectName("sharedSidebar")
        w.setFixedWidth(220)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("📂 采购工作台")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        section = QLabel("业务板块")
        section.setObjectName("navSection")
        layout.addWidget(section)

        nav_items = [
            ("📄 合同命名", "PDF 合同自动识别与重命名"),
            ("📤 合同、对账发送台", "合同与对账单发送到供应商群聊"),
        ]
        for i, (name, desc) in enumerate(nav_items):
            btn = QPushButton(name)
            btn.setObjectName("navItem")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(desc)
            btn.clicked.connect(lambda checked, idx=i: self._switch_page(idx))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        version = QLabel("v2.1 — 统一版")
        version.setObjectName("versionLabel")
        layout.addWidget(version)

        return w

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

    # ── 拖放支持 ──────────────────────────────────────────────────────
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        current = self.stack.currentWidget()
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()]
        if hasattr(current, 'add_paths'):
            current.add_paths(paths)

    # ── 关闭确认 ──────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:
        # Check if naming tool is busy
        p = self.rename_page
        if (hasattr(p, 'worker_thread')
                and p.worker_thread
                and p.worker_thread.is_alive()):
            r = QMessageBox.question(
                self, "确认退出",
                "合同命名工具仍在处理文件，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r == QMessageBox.StandardButton.No:
                event.ignore()
                return
            if hasattr(p, '_stop_processing'):
                p._stop_processing()

        # Check if workbench has tasks marked "发送中" (in-flight sends)
        wb = self.workbench_page
        if hasattr(wb, 'tasks'):
            sending = [t for t in wb.tasks if getattr(t, 'status', '') == '发送中']
            if sending:
                r = QMessageBox.question(
                    self, "确认退出",
                    f"发送台仍有 {len(sending)} 个文件正在发送中，确定要退出吗？\n退出可能导致文件未完整发送。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if r == QMessageBox.StandardButton.No:
                    event.ignore()
                    return

        event.accept()

    # ── 主题 API ──────────────────────────────────────────────────────
    def reload_theme(self, theme_overrides: dict | None = None) -> None:
        if theme_overrides is not None:
            self._theme_overrides = theme_overrides
        self.setStyleSheet(style.build(self._theme_overrides))
