from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from unified import style
from unified.watermark_app import WatermarkApp

_HERE = Path(__file__).resolve().parent.parent
_PROJECTS = _HERE.parent
_NAMING_PROJECT = _PROJECTS / "pdf-windows-11-python-3-12"
_WORKBENCH_PROJECT = _PROJECTS / "wechat-wxwork-text-purchase-workbench-main"

_NAV_ITEMS = [
    ("合同命名", "PDF 合同自动识别与重命名"),
    ("合同发送台", "合同与对账单发送到供应商群聊"),
    ("水单识别", "银行付款水单自动识别与记账"),
    ("付款跟踪", "付款申请单跟踪、状态管理与导出"),
]


def _nav_display_name(full: str) -> str:
    """Return the readable module label shown in the topbar."""
    return full.split("  ", 1)[-1] if "  " in full else full


class UnifiedApp(QMainWindow):
    """统一采购工具壳 — 侧栏导航 + 业务页面

    水单识别直接加载，合同命名/发送台延迟加载以降低启动开销。
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("采购工作台")
        self.resize(1360, 780)
        self.setMinimumSize(1240, 700)
        self.setAcceptDrops(True)

        self._theme_overrides = style.load_theme()
        # index 0 = 合同命名 (lazy), 1 = 合同发送台 (lazy), 2 = 水单识别 (direct), 3 = 付款跟踪 (lazy)
        self._lazy_loaded: dict[int, bool] = {0: False, 1: False, 2: True, 3: False}
        self._page_transition_anim: QPropertyAnimation | None = None

        # ── 页面 ──
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(
            f"background: {self.theme_tokens().get('bg', style.BG)};"
        )

        # index 2 — 水单识别（直接加载）
        self.watermark_page = WatermarkApp(parent=self, shell=self)

        # index 0, 1, 3 — 占位（延迟加载）
        self.rename_page = None
        self.workbench_page = None
        self.payment_page = None
        self._placeholder0 = QWidget()
        self._placeholder1 = QWidget()
        self._placeholder3 = QWidget()
        self.stack.addWidget(self._placeholder0)    # index 0: 合同命名
        self.stack.addWidget(self._placeholder1)    # index 1: 合同发送台
        self.stack.addWidget(self.watermark_page)   # index 2: 水单识别
        self.stack.addWidget(self._placeholder3)    # index 3: 付款跟踪

        # ── 侧栏 ──
        self._nav_buttons: list[QPushButton] = []
        sidebar = self._build_sidebar()
        topbar = self._build_topbar()

        # ── 布局 ──
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(topbar)
        content_layout.addWidget(self.stack, 1)

        body = QWidget()
        hbox = QHBoxLayout(body)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addWidget(sidebar)
        hbox.addWidget(content, 1)
        self.setCentralWidget(body)

        self._apply_theme()
        self._switch_page(0)

    # ── 侧栏 ──────────────────────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        w = QFrame()
        w.setObjectName("sharedSidebar")
        w.setFixedWidth(188)
        w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(8)

        title = QLabel("采购工作台")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        section = QLabel("快速入口")
        section.setObjectName("navSection")
        layout.addWidget(section)

        for i, (name, desc) in enumerate(_NAV_ITEMS):
            btn = QPushButton(name)
            btn.setObjectName("navItem")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(desc)
            btn.setProperty("pageIndex", i)
            btn.clicked.connect(lambda checked, idx=i: self._switch_page(idx))
            self._nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        version = QLabel("v2.4 — 统一版")
        version.setObjectName("versionLabel")
        layout.addWidget(version)

        return w

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(76)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 13, 24, 13)
        layout.setSpacing(18)

        title_col = QVBoxLayout()
        title_col.setSpacing(5)
        self._module_title = QLabel(_nav_display_name(_NAV_ITEMS[0][0]))
        self._module_title.setObjectName("topbarTitle")
        self._module_title.setMinimumHeight(34)
        self._module_subtitle = QLabel(_NAV_ITEMS[0][1])
        self._module_subtitle.setObjectName("topbarSubtitle")
        self._module_subtitle.setMinimumHeight(18)
        title_col.addWidget(self._module_title)
        title_col.addWidget(self._module_subtitle)
        layout.addLayout(title_col)

        layout.addStretch(1)

        search = QLineEdit()
        search.setObjectName("globalSearch")
        search.setPlaceholderText("搜索供应商、合同、PO")
        search.setReadOnly(True)
        search.setFixedWidth(220)
        layout.addWidget(search)

        return bar

    def _switch_page(self, index: int) -> None:
        if index == 2:
            self._fade_to(index)
            return

        if not self._lazy_loaded.get(index):
            try:
                self._lazy_load_page(index)
            except Exception:
                QMessageBox.critical(
                    self, "加载失败",
                    f"模块加载失败，请检查依赖是否安装。\n"
                    f"详情: {sys.exc_info()[1]}",
                )
                return
            self._lazy_loaded[index] = True

        self._fade_to(index)

    def _fade_to(self, index: int) -> None:
        """Crossfade transition between pages."""
        old = self.stack.currentWidget()
        self.stack.setCurrentIndex(index)
        self._sync_navigation(index)
        new_page = self.stack.currentWidget()
        if old is None or old is new_page:
            return
        # Fade in the new page
        if new_page:
            effect = QGraphicsOpacityEffect(new_page)
            new_page.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(180)
            anim.setStartValue(0.4)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(lambda page=new_page: page.setGraphicsEffect(None))
            self._page_transition_anim = anim
            anim.start()

    def _lazy_load_page(self, index: int) -> None:
        if index == 0:
            # 合同命名
            sys.path.insert(0, str(_NAMING_PROJECT))
            from app.config import load_config
            from app.gui import ContractRenameApp
            self.naming_config = load_config(_NAMING_PROJECT)
            self.rename_page = ContractRenameApp(
                self.naming_config, parent=self, shell=self,
            )
            self.stack.removeWidget(self._placeholder0)
            self._placeholder0.deleteLater()
            self._placeholder0 = None
            self.stack.insertWidget(0, self.rename_page)

        elif index == 1:
            # 合同发送台
            sys.path.insert(0, str(_WORKBENCH_PROJECT))
            from gui.app import PurchaseWorkbench
            self.workbench_page = PurchaseWorkbench(parent=self, shell=self)
            self.stack.removeWidget(self._placeholder1)
            self._placeholder1.deleteLater()
            self._placeholder1 = None
            self.stack.insertWidget(1, self.workbench_page)

        elif index == 3:
            # 付款跟踪
            from unified.payment_view import PaymentTrackingView
            self.payment_page = PaymentTrackingView(parent=self, shell=self)
            self.stack.removeWidget(self._placeholder3)
            self._placeholder3.deleteLater()
            self._placeholder3 = None
            self.stack.insertWidget(3, self.payment_page)

    def _sync_navigation(self, index: int) -> None:
        for btn in self._nav_buttons:
            page_index = int(btn.property("pageIndex"))
            active = page_index == index
            btn.setChecked(active)
            label = _NAV_ITEMS[page_index][0]
            btn.setText(f"|  {label}" if active else f"   {label}")
        if hasattr(self, "_module_title"):
            self._module_title.setText(_nav_display_name(_NAV_ITEMS[index][0]))
            self._module_subtitle.setText(_NAV_ITEMS[index][1])

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
        p = self.rename_page
        if (p is not None
                and hasattr(p, 'worker_thread')
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

        wb = self.workbench_page
        if (wb is not None
                and hasattr(wb, 'tasks')):
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

        # 付款跟踪数据库清理
        if self.payment_page is not None:
            try:
                from unified.payment_db import close_db
                close_db()
            except Exception:
                pass

        event.accept()

    # ── 主题 API ──────────────────────────────────────────────────────
    def theme_tokens(self) -> dict:
        mode = self._theme_overrides.get("_mode", "dark")
        return style.resolved_tokens(mode, self._theme_overrides)

    def _apply_theme(self) -> None:
        tokens = self.theme_tokens()
        self.setStyleSheet(style.build(tokens))
        self.stack.setStyleSheet(f"background: {tokens.get('bg', style.BG)};")

    def reload_theme(self, theme_overrides: dict | None = None) -> None:
        if theme_overrides is not None:
            self._theme_overrides = theme_overrides
        self._apply_theme()

    def toggle_theme(self) -> str:
        """Switch between dark and light mode. Returns new mode name."""
        mode = self._theme_overrides.get("_mode", "dark")
        new_mode = "light" if mode == "dark" else "dark"
        self._theme_overrides["_mode"] = new_mode
        style.save_theme(self._theme_overrides)
        self._apply_theme()
        return new_mode
