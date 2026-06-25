from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QTextCursor, QShortcut, QKeySequence, QPixmap, QImage, QAction
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup,
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QHeaderView,
    QRadioButton, QScrollArea, QSplitter, QMenu,
    QStackedWidget, QStatusBar, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QProgressBar, QSizePolicy, QColorDialog,
)

from app.config import AppConfig
from app.email_service import EmailConfig, EmailFetchError, EmailService
from app.extractor import ContractExtractor
from app.logger_service import RenameLogger
from app.models import BatchSummary, LogEntry, PendingRename
from app.ocr_cache import OCRTextCache
from app.ocr_service import OCRServiceError, PaddleOCRService
from app.pdf_service import PDFRenderError, PDFService
from app.renamer import FileRenamer
from app.send_platform import SendPlatformBridge
from app.vendor_cache import VendorCache
from unified import style as _style

# Theme is managed by the unified shell via unified/style.py.
# Use _token() to resolve any color dynamically from the current theme.
def _token(shell: object | None, key: str, fallback: str) -> str:
    """Return the current theme value for *key*, or *fallback* if unavailable."""
    if shell is not None and hasattr(shell, '_theme_overrides'):
        return (shell._theme_overrides or {}).get(key) or _style.TOKENS.get(key, fallback)
    return _style.TOKENS.get(key, fallback)


class ContractRenameApp(QWidget):
    def __init__(self, config: AppConfig, parent: QWidget | None = None,
                 shell: object | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._shell = shell
        self.pdf_service = PDFService(dpi=self.config.render_dpi)
        self.extractor = ContractExtractor()
        self.renamer = FileRenamer()
        self.logger = RenameLogger(self.config.log_dir / "rename_log.csv")
        self.vendor_cache = VendorCache(self.config.vendor_cache_path)
        self.ocr_cache = OCRTextCache(self.config.ocr_text_cache_path)
        self.send_bridge = SendPlatformBridge(enabled=self.config.send_platform_enabled, inbox_dir=self.config.send_platform_inbox_dir)
        self.ocr_service: PaddleOCRService | None = None
        self.email_service = EmailService()
        self.worker_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.pending_review: PendingRename | None = None
        self.pending_decision: tuple[str, str | None] | None = None
        self.pending_event: threading.Event | None = None
        self.summary = BatchSummary()
        self._mode = self.config.naming_mode
        self._ocr_visible = False
        self._pending_ocr_text = ""
        self._pending_cache_info: str | None = None
        self._total_files = 0
        self._current_filter = "all"
        self._file_statuses: dict[str, str] = {}
        self._file_sizes: dict[str, str] = {}
        self._file_times: dict[str, str] = {}
        self._file_paths: dict[str, Path] = {}
        self._current_pdf_path: Path | None = None
        self._preview_page = 0
        self._preview_total = 0
        self._stat_value_labels: dict[str, QLabel] = {}
        self._processing_times: deque[float] = deque(maxlen=50)
        self._resize_timer: QTimer | None = None

        self.setWindowTitle("采购工作台")
        self.setObjectName("appRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            self.resize(min(1200, available.width() - 40),
                        min(800, available.height() - 40))
        else:
            self.resize(1200, 800)
        self.setMinimumSize(850, 520)
        # Theme and stylesheet are managed by the unified shell
        self._build_ui()
        QShortcut(QKeySequence(Qt.Key.Key_Return), self).activated.connect(self._on_return_confirm)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self._on_escape_skip)
        QTimer.singleShot(200, self._poll_ui_queue)

    # ═══════════════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════════════
    def run(self) -> None:
        self.show()

    def add_paths(self, paths: list[Path]) -> None:
        pdf_paths = []
        for p in paths:
            if p.is_dir():
                pdf_paths.extend(sorted(f for f in p.iterdir() if f.suffix.lower() == ".pdf"))
            elif p.suffix.lower() == ".pdf":
                pdf_paths.append(p)
        if pdf_paths:
            self._add_files([str(p) for p in pdf_paths])

    def _add_files(self, paths):
        for p in paths:
            p = os.path.normpath(p)
            fn = os.path.basename(p)
            if fn not in self._file_statuses:
                size_bytes = os.path.getsize(p)
                if size_bytes >= 1024 * 1024:
                    size_str = f"{size_bytes / (1024 * 1024):.1f}MB"
                else:
                    size_str = f"{size_bytes / 1024:.0f}KB"
                self._file_sizes[fn] = size_str
                self._file_times[fn] = datetime.now().strftime("%H:%M")
                self._file_paths[fn] = Path(p)
                item = QListWidgetItem(f"{fn}\n{size_str} · {self._file_times.get(fn, '')}")
                item.setData(Qt.ItemDataRole.UserRole, "waiting")
                item.setForeground(QColor(_token(self._shell, "text2", "#98989E")))
                self.file_list.addItem(item)
                self._file_statuses[fn] = "waiting"
        self._refresh_summary()

    # ═══════════════════════════════════════════════════════════════════════
    # Layout: three-column with shadows
    # ═══════════════════════════════════════════════════════════════════════
    def _card(self, name: str) -> QFrame:
        card = QFrame()
        card.setObjectName(name)
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        _style.apply_shadow(card)
        return card

    def _build_ui(self) -> None:
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setHandleWidth(6)
        border_color = _token(self._shell, "border", "#3A3A3E")
        h_splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {border_color}; }}")

        left_panel = self._build_left_panel()
        center_panel = self._build_center_panel()
        right_panel = self._build_right_panel()

        h_splitter.addWidget(left_panel)
        h_splitter.addWidget(center_panel)
        h_splitter.addWidget(right_panel)

        h_splitter.setSizes([320, 600, 320])

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.addWidget(h_splitter)


    # ═══════════════════════════════════════════════════════════════════════
    # LEFT — File queue
    # ═══════════════════════════════════════════════════════════════════════
    def _build_left_panel(self) -> QWidget:
        panel = self._card("sideCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # ── Title ──
        title = QLabel("文件队列")
        title.setObjectName("sideTitle")
        layout.addWidget(title)

        # ── Search ──
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("搜索文件名...")
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        # ── Status filter ──
        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["全部", "待处理", "OCR中", "待确认", "已完成", "失败"])
        self._filter_combo.setCurrentIndex(0)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_combo)
        layout.addWidget(self._filter_combo)

        # ── File list ──
        self.file_list = QListWidget()
        self.file_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.file_list.setMinimumHeight(120)
        self.file_list.itemClicked.connect(self._on_file_selected)
        layout.addWidget(self.file_list, stretch=1)

        # ── Drag zone ──
        drop_zone = QFrame()
        drop_zone.setObjectName("previewCard")
        drop_zone.setMinimumHeight(48)
        drop_zone.setMaximumHeight(56)
        drop_zone.setCursor(Qt.CursorShape.PointingHandCursor)
        dz_layout = QVBoxLayout(drop_zone)
        dz_layout.setContentsMargins(8, 6, 8, 6)
        dz_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_text = QLabel("拖拽 PDF 文件或文件夹到此处")
        dz_text.setObjectName("sideSubtitle")
        dz_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dz_layout.addWidget(dz_text)
        layout.addWidget(drop_zone)

        return panel

    # ═══════════════════════════════════════════════════════════════════════
    # CENTER — Toolbar + Stats + PDF preview + Rename card
    # ═══════════════════════════════════════════════════════════════════════
    def _build_center_panel(self) -> QWidget:
        area = QWidget()
        area.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_toolbar())
        layout.addWidget(self._build_stat_row())

        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setHandleWidth(6)
        border_color = _token(self._shell, "border", "#3A3A3E")
        v_splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {border_color}; }}")
        v_splitter.addWidget(self._build_preview_card())
        v_splitter.addWidget(self._build_rename_card())
        v_splitter.setSizes([400, 180])

        layout.addWidget(v_splitter, 1)
        layout.setSpacing(6)
        return area

    # ── Toolbar ───────────────────────────────────────────────────────────
    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("toolbar")
        bar.setFixedHeight(50)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(2, 0, 2, 0)
        bar_layout.setSpacing(6)

        # Title
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("采购工作台")
        title.setObjectName("toolbarTitle")
        title_box.addWidget(title, stretch=1)
        bar_layout.addLayout(title_box, stretch=1)

        # Mode: radio group
        self.dual_radio = QRadioButton("双章合同")
        self.dual_radio.setChecked(self._mode == "dual_chop")
        self.dual_radio.toggled.connect(self._on_mode_changed)
        self.po_radio = QRadioButton("采购订单")
        self.po_radio.setChecked(self._mode == "po_order")
        self.po_radio.toggled.connect(self._on_mode_changed)
        mode_group = QHBoxLayout()
        mode_group.setSpacing(0)
        mode_group.addWidget(self.dual_radio)
        mode_group.addWidget(self.po_radio)
        bar_layout.addLayout(mode_group)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {_token(self._shell, 'border', '#D9D9DF')};")
        sep.setFixedWidth(1)
        bar_layout.addWidget(sep)

        # Actions
        self.fetch_button = QPushButton("拉取邮件")
        self.fetch_button.setObjectName("secondaryBtn")
        self.fetch_button.setFixedHeight(32)
        self.fetch_button.clicked.connect(self._fetch_emails)
        self.start_button = QPushButton("开始扫描")
        self.start_button.setObjectName("primaryBtn")
        self.start_button.setFixedHeight(32)
        self.start_button.clicked.connect(self._start_processing)
        bar_layout.addWidget(self.fetch_button)
        bar_layout.addWidget(self.start_button)

        # Stop — hidden until processing
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("stopBtn")
        self.stop_button.setFixedHeight(32)
        self.stop_button.setEnabled(False)
        self.stop_button.setVisible(False)
        self.stop_button.clicked.connect(self._stop_with_confirm)
        bar_layout.addWidget(self.stop_button)

        self.theme_btn = QPushButton("主题")
        self.theme_btn.setObjectName("secondaryBtn")
        self.theme_btn.setFixedHeight(32)
        self.theme_btn.clicked.connect(self._toggle_theme)
        bar_layout.addWidget(self.theme_btn)

        return bar

    # ── Stats row ─────────────────────────────────────────────────────────
    def _build_stat_row(self) -> QWidget:
        row = QWidget()
        row.setFixedHeight(80)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        stats = [
            ("pending", "待处理",  "0", _token(self._shell, "text", "#F5F5F7")),
            ("done",    "已完成",  "0", _token(self._shell, "success", "#30D158")),
            ("failed",  "失败",    "0", _token(self._shell, "danger", "#FF453A")),
            ("review",  "待确认",  "0", _token(self._shell, "primary", "#0A84FF")),
        ]
        self._stat_value_labels = {}

        for key, label_text, val, color in stats:
            card = self._card("statCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(2)

            vl = QLabel(val)
            vl.setObjectName("statValue")
            vl.setProperty("statColor", color)
            ll = QLabel(label_text)
            ll.setObjectName("statLabel")

            cl.addWidget(vl)
            cl.addWidget(ll)
            self._stat_value_labels[key] = vl
            row_layout.addWidget(card, 1)

        return row

    # ── PDF preview ───────────────────────────────────────────────────────
    def _build_preview_card(self) -> QWidget:
        card = self._card("centerCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        preview_title = QLabel("PDF 预览")
        preview_title.setObjectName("cardTitle")
        hdr.addWidget(preview_title)
        hdr.addStretch()
        self.page_label = QLabel("")
        self.page_label.setObjectName("sideSubtitle")
        self.page_label.setFixedWidth(40)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.addWidget(self.page_label)
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.setObjectName("secondaryBtn")
        self.prev_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_page_btn.clicked.connect(self._prev_page)
        self.prev_page_btn.setVisible(False)
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.setObjectName("secondaryBtn")
        self.next_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_page_btn.clicked.connect(self._next_page)
        self.next_page_btn.setVisible(False)
        hdr.addWidget(self.prev_page_btn)
        hdr.addWidget(self.next_page_btn)
        layout.addLayout(hdr)

        # Preview area
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setObjectName("previewScroll")
        self.preview_scroll.setMinimumHeight(160)
        self.preview_scroll.setWidgetResizable(True)
        self.preview_label = QLabel("选择文件以预览")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_color = _token(self._shell, "text3", "#6C6C72")
        self.preview_label.setStyleSheet(
            f"font-size: 13px; color: {placeholder_color}; background: transparent; padding: 20px;"
        )
        self.preview_label.setMinimumHeight(200)
        self.preview_scroll.setWidget(self.preview_label)
        layout.addWidget(self.preview_scroll, 1)

        return card

    # ── Rename card ───────────────────────────────────────────────────────
    def _build_rename_card(self) -> QWidget:
        card = self._card("renameCard")
        self.rename_card = card
        card.setMinimumHeight(0)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        title = QLabel("建议文件名")
        title.setObjectName("cardTitle")
        hdr.addWidget(title)
        hdr.addStretch()
        self.progress_label = QLabel("就绪")
        self.progress_label.setObjectName("sideSubtitle")
        hdr.addWidget(self.progress_label)
        layout.addLayout(hdr)

        self.suggested_entry = QLineEdit()
        self.suggested_entry.setObjectName("suggestName")
        self.suggested_entry.setPlaceholderText("选择左侧文件后将自动生成建议文件名")
        self.suggested_entry.setMinimumHeight(52)
        layout.addWidget(self.suggested_entry)

        layout.addSpacing(8)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addStretch()
        self.copy_button = QPushButton("复制")
        self.copy_button.setObjectName("secondaryBtn")
        self.copy_button.clicked.connect(self._copy_suggested_name)
        self.skip_button = QPushButton("跳过")
        self.skip_button.setObjectName("secondaryBtn")
        self.skip_button.clicked.connect(self._skip_current)
        self.confirm_button = QPushButton("确认")
        self.confirm_button.setObjectName("primaryBtn")
        self.confirm_button.clicked.connect(self._confirm_current)
        self.skip_button.setEnabled(False)
        self.confirm_button.setEnabled(False)
        action_row.addWidget(self.copy_button)
        action_row.addWidget(self.skip_button)
        action_row.addWidget(self.confirm_button)
        layout.addLayout(action_row)

        # Footer
        layout.addSpacing(6)
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(6)
        self.summary_label = QLabel("等待开始")
        self.summary_label.setObjectName("sideSubtitle")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        footer_layout.addWidget(self.summary_label)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(100)
        self.open_folder_btn = QPushButton("输出目录")
        self.open_folder_btn.setObjectName("secondaryBtn")
        self.open_folder_btn.setFixedHeight(24)
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        bottom_row.addStretch()
        bottom_row.addWidget(self.progress_bar)
        bottom_row.addWidget(self.open_folder_btn)
        footer_layout.addLayout(bottom_row)
        layout.addLayout(footer_layout)

        return card

    # ═══════════════════════════════════════════════════════════════════════
    # RIGHT — Review center
    # ═══════════════════════════════════════════════════════════════════════
    def _build_right_panel(self) -> QWidget:
        panel = self._card("reviewCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Title + status
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title2 = QLabel("审核中心")
        title2.setObjectName("sideTitle")
        title_row.addWidget(title2)
        title_row.addStretch()
        self._review_status_pill = QLabel("待扫描")
        self._review_status_pill.setObjectName("tagGray")
        title_row.addWidget(self._review_status_pill)
        # Edit cache button
        cache_btn = QPushButton("编辑缓存")
        cache_btn.setObjectName("smallBtn")
        cache_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cache_btn.clicked.connect(self._open_cache_editor)
        title_row.addWidget(cache_btn)
        layout.addLayout(title_row)

        # OCR info cards
        self._ocr_vendor_value = QLabel("等待识别")
        self._ocr_contract_value = QLabel("等待识别")
        self._ocr_date_value = QLabel("等待识别")
        self._ocr_cache_value = QLabel("等待识别")
        self._ocr_cache_value.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ocr_cache_value.mousePressEvent = lambda e: self._edit_cache_entry()

        layout.addWidget(self._ocr_info_card("供应商", self._ocr_vendor_value))
        layout.addWidget(self._ocr_info_card("合同号", self._ocr_contract_value))
        layout.addWidget(self._ocr_info_card("日期",   self._ocr_date_value))
        layout.addWidget(self._ocr_info_card("缓存命中", self._ocr_cache_value))

        # Confidence
        conf_row = QHBoxLayout()
        conf_row.setSpacing(6)
        conf_row.addWidget(QLabel("识别状态"))
        conf_row.addStretch()
        self._ocr_conf_pill = QLabel("-")
        self._ocr_conf_pill.setObjectName("tagGray")
        conf_row.addWidget(self._ocr_conf_pill)
        layout.addLayout(conf_row)

        # OCR text preview
        self.ocr_toggle = QPushButton("识别文字")
        self.ocr_toggle.setObjectName("collapseBtn")
        self.ocr_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ocr_toggle.clicked.connect(self._toggle_ocr)
        layout.addWidget(self.ocr_toggle)

        self.ocr_text = QPlainTextEdit()
        self.ocr_text.setObjectName("ocrBox")
        self.ocr_text.setReadOnly(True)
        self.ocr_text.setMinimumHeight(50)
        self.ocr_text.setMaximumHeight(100)
        self.ocr_text.setVisible(False)
        layout.addWidget(self.ocr_text)

        # Log
        log_hdr = QHBoxLayout()
        log_hdr.setSpacing(6)
        log_label = QLabel("处理日志")
        log_label.setObjectName("sectionLabel")
        log_hdr.addWidget(log_label)
        log_hdr.addStretch()
        layout.addLayout(log_hdr)

        self.log_text = QPlainTextEdit()
        self.log_text.setObjectName("logBox")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(500)
        self.log_text.setMinimumHeight(40)
        self.log_text.setMaximumHeight(160)
        layout.addWidget(self.log_text)

        return panel

    def _ocr_info_card(self, title: str, value_label: QLabel) -> QFrame:
        card = QFrame()
        card.setObjectName("ocrInfoCard")
        card.setFixedHeight(46)
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lyt = QHBoxLayout(card)
        lyt.setContentsMargins(12, 6, 12, 6)
        lyt.setSpacing(8)

        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        lab = QLabel(title)
        lab.setObjectName("sectionLabel")
        value_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {_token(self._shell, 'text', '#F5F5F7')}; background: transparent;")
        value_label.setWordWrap(True)
        vbox.addWidget(lab)
        vbox.addWidget(value_label)
        lyt.addLayout(vbox, stretch=1)
        return card

    # ═══════════════════════════════════════════════════════════════════════
    # Filter / Search helpers
    # ═══════════════════════════════════════════════════════════════════════
    def _on_search(self, text: str) -> None:
        text = text.strip().lower()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item:
                # Search and filter work together: item is visible only if BOTH match
                matches_search = (not text) or (text in item.text().lower())
                matches_filter = self._filter_matches(item)
                item.setHidden(not (matches_search and matches_filter))

    def _on_filter_combo(self, idx: int) -> None:
        mapping = {0: "all", 1: "pending_waiting", 2: "ocr_active", 3: "pending", 4: "done", 5: "failed"}
        self._current_filter = mapping.get(idx, "all")
        search_text = self.search_box.text().strip().lower() if hasattr(self, "search_box") else ""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item:
                matches_search = (not search_text) or (search_text in item.text().lower())
                matches_filter = self._filter_matches(item)
                item.setHidden(not (matches_search and matches_filter))

    def _filter_matches(self, item: QListWidgetItem) -> bool:
        st = item.data(Qt.ItemDataRole.UserRole) or ""
        key = self._current_filter
        if key == "all":
            return True
        elif key == "pending_waiting":
            return st in {"waiting"}
        elif key == "ocr_active":
            return st in {"scanning", "ocr", "extracting"}
        elif key == "pending":
            return st == "pending"
        elif key == "done":
            return st in {"done", "moving", "queued"}
        elif key == "failed":
            return st == "failed"
        return True

    def _on_mode_changed(self) -> None:
        self._mode = "dual_chop" if self.dual_radio.isChecked() else "po_order"

    def _prev_page(self) -> None:
        if self._preview_total <= 1:
            return
        self._preview_page = max(0, self._preview_page - 1)
        self._render_preview_page()

    def _next_page(self) -> None:
        if self._preview_total <= 1:
            return
        self._preview_page = min(self._preview_total - 1, self._preview_page + 1)
        self._render_preview_page()

    def _on_file_selected(self, item: QListWidgetItem) -> None:
        """Click a file in the left queue -> show its PDF preview."""
        text = item.text()
        fn = text.split("\n")[0].strip()
        # Strip emoji icon prefix if present (e.g. "✅  迈瑞PO20250529001.pdf")
        import re
        fn = re.sub(r'^[^\w]*\s+', '', fn)
        if not fn:
            return
        found = None
        # 1) currently pending file
        if self.pending_review and self.pending_review.original_name == fn:
            found = self.pending_review.original_path
        # 2) path cache (from _add_files or _reset_file_list)
        if not found and fn in self._file_paths:
            found = self._file_paths[fn]
        # 3) fallback: pdf_dir / fn
        if not found:
            candidate = self.config.pdf_dir / fn
            if candidate.exists():
                found = candidate
        if found:
            self._current_pdf_path = found
            self._load_preview(found)

    def _load_preview(self, pdf_path: Path) -> None:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            self._preview_total = doc.page_count
            self._preview_page = 0
            self._render_preview_page()
            doc.close()
            self.prev_page_btn.setVisible(self._preview_total > 1)
            self.next_page_btn.setVisible(self._preview_total > 1)
        except Exception:
            self.preview_label.setText("无法加载 PDF 预览")
            placeholder_color = _token(self._shell, "text3", "#6C6C72")
            self.preview_label.setStyleSheet(
                f"font-size: 13px; color: {placeholder_color}; background: transparent; padding: 40px;"
            )
            self.page_label.setText("")
            self._preview_total = 0
            self.prev_page_btn.setVisible(False)
            self.next_page_btn.setVisible(False)

    def _render_preview_page(self) -> None:
        if not self._current_pdf_path or not self._current_pdf_path.exists():
            return
        try:
            import fitz
            doc = fitz.open(self._current_pdf_path)
            self._preview_total = doc.page_count
            page = doc.load_page(self._preview_page)
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            if self.preview_scroll.width() > 20 and pixmap.width() > self.preview_scroll.width() - 20:
                pixmap = pixmap.scaledToWidth(self.preview_scroll.width() - 20, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(pixmap)
            self.preview_label.setStyleSheet("background: transparent; padding: 0;")
            self.preview_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            self.page_label.setText(f"{self._preview_page + 1} / {self._preview_total}")
            doc.close()
        except Exception:
            self.preview_label.setText("渲染失败")
            placeholder_color = _token(self._shell, "text3", "#6C6C72")
            self.preview_label.setStyleSheet(
                f"font-size: 13px; color: {placeholder_color}; background: transparent; padding: 40px;"
            )

    # ═══════════════════════════════════════════════════════════════════════
    # OCR / Confidence / Timing
    # ═══════════════════════════════════════════════════════════════════════
    def _update_ocr_confidence(self, avg_confidence: float) -> None:
        pct = min(99, int(avg_confidence * 100))
        if pct >= 80:
            self._ocr_conf_pill.setObjectName("tagGreen")
            self._review_status_pill.setObjectName("tagGreen")
            status_text = "识别完成"
        elif pct >= 50:
            self._ocr_conf_pill.setObjectName("tagOrange")
            self._review_status_pill.setObjectName("tagOrange")
            status_text = "低置信度"
        else:
            self._ocr_conf_pill.setObjectName("tagRed")
            self._review_status_pill.setObjectName("tagRed")
            status_text = "需确认"
        self._ocr_conf_pill.setStyleSheet("")
        self._review_status_pill.setStyleSheet("")
        self._ocr_conf_pill.setText(f"{pct}%")
        self._review_status_pill.setText(status_text)
        self._append_log(f"OCR完成 → 置信度 {pct}%")

    def _update_list_colors(self) -> None:
        """Refresh list item colors after OCR confidence changes."""
        pass

    def _record_timing(self, elapsed: float) -> None:
        self._processing_times.append(elapsed)

    # ═══════════════════════════════════════════════════════════════════════
    # Processing (UNCHANGED business logic)
    # ═══════════════════════════════════════════════════════════════════════
    def _start_processing(self) -> None:
        pdf_dir = self.config.pdf_dir
        if not pdf_dir.exists():
            QMessageBox.critical(self, "目录不存在", f"未找到 PDF 目录:\n{pdf_dir}")
            return
        if self.worker_thread and self.worker_thread.is_alive():
            QMessageBox.information(self, "处理中", "当前已有任务在运行。")
            return
        self.summary = BatchSummary()
        self._refresh_summary()
        self._clear_review_panel()
        mode_label = "双章合同" if self._mode == "dual_chop" else "PO 订单"
        self._append_log(f"开始批量扫描 (模板: {mode_label})。")
        self.stop_event.clear()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.stop_button.setVisible(True)
        self.fetch_button.setEnabled(False)
        self.dual_radio.setEnabled(False)
        self.po_radio.setEnabled(False)
        self._set_progress("正在扫描 PDF 文件...")
        self._append_log("扫描开始")
        self._review_status_pill.setObjectName("tagBlue")
        self._review_status_pill.setStyleSheet("")
        self._review_status_pill.setText("扫描中")
        self.worker_thread = threading.Thread(target=self._worker_run, daemon=True)
        self.worker_thread.start()

    def _fetch_emails(self) -> None:
        if not self.config.email_enabled:
            QMessageBox.information(self, "未启用", "邮件拉取功能尚未启用。")
            return
        if not self.config.email_username or not self.config.email_password:
            QMessageBox.critical(self, "配置不完整", "请填写 EMAIL_USERNAME 和 EMAIL_PASSWORD。")
            return
        self.fetch_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self._set_progress("正在连接邮箱拉取 PDF 附件...")
        self._append_log("开始从邮箱拉取采购合同 PDF 附件...")
        email_config = EmailConfig(
            imap_server=self.config.email_imap_server, imap_port=self.config.email_imap_port,
            username=self.config.email_username, password=self.config.email_password,
            sender_keywords=self.config.email_sender_keywords, subject_keywords=self.config.email_subject_keywords,
            download_dir=self.config.pdf_dir, mark_read=self.config.email_mark_read, unread_only=True,
        )
        def _run():
            try:
                result = self.email_service.fetch_pdf_attachments(email_config)
                self.ui_queue.put(("email_done", result))
            except EmailFetchError as exc:
                self.ui_queue.put(("email_error", str(exc)))
            except Exception as exc:
                self.ui_queue.put(("email_error", f"未知错误: {exc}"))
                self.ui_queue.put(("debug_error", traceback.format_exc()))
        self.worker_thread = threading.Thread(target=_run, daemon=True)
        self.worker_thread.start()

    def _on_fetch_finished(self, result) -> None:
        self.worker_thread = None
        self.fetch_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self._set_progress("邮件拉取完成")
        self._append_log(f"邮件拉取完成: 下载 {result.downloaded} 个 PDF，跳过 {result.skipped} 封邮件")
        # Auto-refresh file list with newly downloaded PDFs
        if result.downloaded > 0:
            pdf_files = self.renamer.scan_pdfs(self.config.pdf_dir, recursive=self.config.recursive_scan)
            self._reset_file_list([(p.name, str(p)) for p in pdf_files])
            self._total_files = len(pdf_files)
            self.progress_bar.setRange(0, max(self._total_files, 1))
            self._refresh_summary()

    def _on_fetch_error(self, error_msg: str) -> None:
        self.worker_thread = None
        self.fetch_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self._set_progress("邮件拉取失败")
        self._append_log(f"邮件拉取失败: {error_msg}")
        QMessageBox.critical(self, "邮件拉取失败", error_msg)

    def _stop_with_confirm(self) -> None:
        reply = QMessageBox.question(
            self, "确认停止",
            "将停止正在处理的任务，已完成的文件不受影响。\n确定停止？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._stop_processing()

    def _stop_processing(self) -> None:
        self.stop_event.set()
        self._set_progress("已收到终止请求...")
        if self.pending_event and not self.pending_event.is_set():
            self.pending_decision = ("stop", None)
            self.pending_event.set()

    def _worker_run(self) -> None:
        naming_mode = self._mode
        def _qt(mt, payload=None):
            self.ui_queue.put((mt, payload))
        try:
            pdf_files = self.renamer.scan_pdfs(self.config.pdf_dir, recursive=self.config.recursive_scan)
            _qt("reset_total", len(pdf_files))
            _qt("reset_file_list", [(p.name, str(p)) for p in pdf_files])
            if not pdf_files:
                _qt("status", "未找到任何 PDF 文件。")
                return
            for index, pdf_path in enumerate(pdf_files, start=1):
                if self.stop_event.is_set():
                    break
                file_start = time.monotonic()
                _qt("status", f"正在处理第 {index}/{len(pdf_files)} 个文件: {pdf_path.name}")
                _qt("update_file_status", (pdf_path.name, "scanning"))
                if self.renamer.is_already_named(pdf_path.name):
                    if self.send_bridge.enabled:
                        _qt("update_file_status", (pdf_path.name, "queued"))
                        self._deliver_and_record(pdf_path, original_name=pdf_path.name, failure_prefix="文件已命名，但移动到发送平台失败")
                    else:
                        _qt("update_file_status", (pdf_path.name, "moving"))
                        final_path = self.renamer.move_to_output(pdf_path, self.config.output_dir)
                        self._record_result(LogEntry(original_name=pdf_path.name, new_name=final_path.name, status="成功", error_reason="已移动到输出目录"))
                        _qt("add_to_workbench", str(final_path))
                    _qt("update_file_status", (pdf_path.name, "done"))
                    _qt("timing", time.monotonic() - file_start)
                    continue
                try:
                    _qt("update_file_status", (pdf_path.name, "ocr"))
                    ocr_result = self.ocr_cache.get(pdf_path)
                    if ocr_result is None:
                        if self.ocr_service is None:
                            _qt("status", "正在初始化 OCR 模型...")
                            _qt("review_pill", ("tagOrange", "模型加载中…"))
                            self.ocr_service = PaddleOCRService(lang=self.config.ocr_lang)
                        _qt("status", f"OCR识别中 ({index}/{len(pdf_files)})")
                        _qt("review_pill", ("tagBlue", f"OCR {index}/{len(pdf_files)}"))
                        image = self.pdf_service.render_first_page(pdf_path)
                        ocr_result = self.ocr_service.recognize(image)
                        self.ocr_cache.remember(pdf_path, ocr_result)
                    _qt("update_file_status", (pdf_path.name, "extracting"))
                    extraction = self.extractor.extract(ocr_result)
                    scores = [line.score for line in ocr_result.lines if line.score is not None]
                    avg_conf = sum(scores) / len(scores) if scores else 0
                    _qt("ocr_confidence", avg_conf)
                    cache_match = self.vendor_cache.match_text(ocr_result.full_text)
                    fuzzy_info: str | None = None
                    if cache_match:
                        self._pending_cache_info = f"精确命中: {cache_match.vendor_short_name} (全称: {cache_match.vendor_name})"
                        extraction.vendor_name = cache_match.vendor_name
                        extraction.vendor_short_name = cache_match.vendor_short_name
                    elif extraction.vendor_name:
                        fuzzy_match = self.vendor_cache.fuzzy_match(ocr_result.full_text)
                        if fuzzy_match:
                            self._pending_cache_info = f"模糊匹配: {fuzzy_match.vendor_short_name} (全称: {fuzzy_match.vendor_name})"
                            extraction.vendor_name = fuzzy_match.vendor_name
                            extraction.vendor_short_name = fuzzy_match.vendor_short_name
                            fuzzy_info = f"模糊记忆匹配: {fuzzy_match.vendor_name}"
                        else:
                            self._pending_cache_info = None
                    else:
                        self._pending_cache_info = None

                    if not extraction.is_valid:
                        partial_name = self.renamer.build_filename(
                            extraction.vendor_short_name or "", extraction.contract_no or "",
                            naming_mode=naming_mode, suffix=pdf_path.suffix)
                        _qt("update_file_status", (pdf_path.name, "pending"))
                        suggested_path = self.renamer.ensure_unique_path(pdf_path, partial_name)
                        pending = PendingRename(
                            original_path=pdf_path, original_name=pdf_path.name,
                            ocr_text=ocr_result.full_text, extraction=extraction,
                            suggested_name=suggested_path.name)
                        decision, manual_name = self._wait_for_review(pending)
                        if decision == "stop": self.stop_event.set(); break
                        if decision == "skip":
                            self._record_result(LogEntry(original_name=pdf_path.name, new_name="", status="跳过", error_reason="用户手动跳过"))
                            _qt("update_file_status", (pdf_path.name, "failed"))
                            _qt("timing", time.monotonic() - file_start)
                            continue
                        final_name = manual_name or pending.suggested_name
                        _qt("update_file_status", (pdf_path.name, "renaming"))
                        final_path = self.renamer.rename_file(pdf_path, final_name)
                        final_path = self.renamer.move_to_output(final_path, self.config.output_dir)
                        if extraction.vendor_name:
                            self.vendor_cache.remember(extraction.vendor_name, extraction.vendor_short_name)
                        _qt("update_file_status", (pdf_path.name, "queued" if self.send_bridge.enabled else "moving"))
                        _qt("update_file_paths", (pdf_path.name, str(final_path)))
                        self._deliver_and_record(final_path, original_name=pdf_path.name, failure_prefix="已手动命名，但移动到发送平台失败")
                        _qt("add_to_workbench", str(final_path))
                        _qt("update_file_status", (pdf_path.name, "done"))
                        _qt("timing", time.monotonic() - file_start)
                        continue

                    suggested_name = self.renamer.build_filename(
                        extraction.vendor_short_name or "", extraction.contract_no or "",
                        naming_mode=naming_mode, suffix=pdf_path.suffix)
                    if cache_match or fuzzy_info:
                        _qt("update_file_status", (pdf_path.name, "renaming"))
                        final_path = self.renamer.rename_file(pdf_path, suggested_name)
                        final_path = self.renamer.move_to_output(final_path, self.config.output_dir)
                        self.vendor_cache.remember(extraction.vendor_name, extraction.vendor_short_name)
                        prefix = "缓存命中" if cache_match else f"模糊记忆 ({fuzzy_info})"
                        _qt("update_file_status", (pdf_path.name, "queued" if self.send_bridge.enabled else "moving"))
                        _qt("update_file_paths", (pdf_path.name, str(final_path)))
                        self._deliver_and_record(final_path, original_name=pdf_path.name, success_prefix=f"{prefix}，自动重命名")
                        _qt("add_to_workbench", str(final_path))
                        _qt("update_file_status", (pdf_path.name, "done"))
                        _qt("timing", time.monotonic() - file_start)
                        continue

                    _qt("update_file_status", (pdf_path.name, "pending"))
                    suggested_path = self.renamer.ensure_unique_path(pdf_path, suggested_name)
                    pending = PendingRename(
                        original_path=pdf_path, original_name=pdf_path.name,
                        ocr_text=ocr_result.full_text, extraction=extraction,
                        suggested_name=suggested_path.name)
                    decision, manual_name = self._wait_for_review(pending)
                    if decision == "stop": self.stop_event.set(); break
                    if decision == "skip":
                        self._record_result(LogEntry(original_name=pdf_path.name, new_name="", status="跳过", error_reason="用户手动跳过"))
                        _qt("update_file_status", (pdf_path.name, "failed"))
                        _qt("timing", time.monotonic() - file_start)
                        continue
                    final_name = manual_name or pending.suggested_name
                    _qt("update_file_status", (pdf_path.name, "renaming"))
                    final_path = self.renamer.rename_file(pdf_path, final_name)
                    final_path = self.renamer.move_to_output(final_path, self.config.output_dir)
                    self.vendor_cache.remember(extraction.vendor_name, extraction.vendor_short_name)
                    _qt("update_file_status", (pdf_path.name, "queued" if self.send_bridge.enabled else "moving"))
                    _qt("update_file_paths", (pdf_path.name, str(final_path)))
                    self._deliver_and_record(final_path, original_name=pdf_path.name, failure_prefix="已重命名，但移动到发送平台失败")
                    _qt("add_to_workbench", str(final_path))
                    _qt("update_file_status", (pdf_path.name, "done"))
                    _qt("timing", time.monotonic() - file_start)
                except (PDFRenderError, OCRServiceError) as exc:
                    self._record_result(LogEntry(original_name=pdf_path.name, new_name="", status="失败", error_reason=str(exc)))
                    _qt("update_file_status", (pdf_path.name, "failed"))
                    _qt("timing", time.monotonic() - file_start)
                except Exception as exc:
                    self._record_result(LogEntry(original_name=pdf_path.name, new_name="", status="失败", error_reason=str(exc)))
                    _qt("debug_error", traceback.format_exc())
                    _qt("update_file_status", (pdf_path.name, "failed"))
                    _qt("timing", time.monotonic() - file_start)
        except Exception as exc:
            _qt("fatal_error", str(exc))
            _qt("debug_error", traceback.format_exc())
        finally:
            _qt("finished", None)

    # ═══════════════════════════════════════════════════════════════════════
    # UI Review (pending confirmation flow)
    # ═══════════════════════════════════════════════════════════════════════
    def _wait_for_review(self, pending: PendingRename) -> tuple[str, str | None]:
        decision_event = threading.Event()
        self.pending_decision = None
        self.pending_event = decision_event
        self.ui_queue.put(("pending", pending))
        decision_event.wait()
        decision = self.pending_decision or ("skip", None)
        self.pending_event = None
        self.pending_decision = None
        return decision

    def _record_result(self, entry: LogEntry) -> None:
        self.logger.write(entry)
        self.ui_queue.put(("record", entry))

    def _deliver_and_record(self, pdf_path: Path, original_name: str,
                            success_prefix: str = "", failure_prefix: str = "移动到发送平台失败") -> None:
        try:
            delivery = self.send_bridge.deliver(pdf_path)
        except Exception as exc:
            self._record_result(LogEntry(original_name=original_name, new_name=pdf_path.name,
                                         status="失败", error_reason=f"{failure_prefix}: {exc}"))
            return
        delivery_note = self.send_bridge.describe(delivery)
        reason = "；".join(part for part in [success_prefix, delivery_note] if part)
        self._record_result(LogEntry(original_name=original_name, new_name=delivery.target_path.name,
                                     status="成功", error_reason=reason))

    # ═══════════════════════════════════════════════════════════════════════
    # Auto-load renamed files into the workbench (right panel)
    # ═══════════════════════════════════════════════════════════════════════
    def _add_to_workbench(self, pdf_path: Path) -> None:
        """将已命名的 PDF 自动加载到右侧"合同、对账发送台"。"""
        parent = self.parent()
        # Walk up to find the UnifiedApp shell
        while parent is not None:
            if hasattr(parent, 'workbench_page'):
                try:
                    parent.workbench_page.add_paths([pdf_path])
                except Exception:
                    pass
                return
            parent = parent.parent()

    # ═══════════════════════════════════════════════════════════════════════
    # UI queue poller
    # ═══════════════════════════════════════════════════════════════════════
    def _poll_ui_queue(self) -> None:
        while True:
            try:
                mt, payload = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                if mt == "status":
                    self._set_progress(str(payload))
                elif mt == "reset_total":
                    self.summary = BatchSummary(total=int(payload))
                    self._total_files = int(payload)
                    self.progress_bar.setRange(0, self._total_files)
                    self.progress_bar.setValue(0)
                    self._refresh_summary()
                elif mt == "reset_file_list":
                    self._reset_file_list(payload)
                elif mt == "update_file_status":
                    name, status = payload
                    self._update_file_list_item(name, status)
                    done_count = sum(1 for i in range(self.file_list.count())
                                     if self.file_list.item(i)
                                     and self.file_list.item(i).data(Qt.ItemDataRole.UserRole) in ("done", "failed"))
                    self.progress_bar.setValue(min(done_count, self._total_files))
                    self._refresh_summary()
                elif mt == "pending":
                    self._show_pending(payload)
                elif mt == "record":
                    self._handle_record(payload)
                elif mt == "finished":
                    self._finish_processing()
                elif mt == "fatal_error":
                    self._set_progress("任务异常终止")
                    QMessageBox.critical(self, "运行失败", str(payload))
                elif mt == "email_done":
                    self._on_fetch_finished(payload)
                elif mt == "email_error":
                    self._on_fetch_error(str(payload))
                elif mt == "debug_error":
                    self._append_log(str(payload))
                elif mt == "ocr_confidence":
                    self._update_ocr_confidence(float(payload))
                elif mt == "timing":
                    self._record_timing(float(payload))
                elif mt == "review_pill":
                    obj_name, text = payload
                    self._review_status_pill.setObjectName(obj_name)
                    self._review_status_pill.setStyleSheet("")
                    self._review_status_pill.setText(text)
                elif mt == "add_to_workbench":
                    try:
                        self._add_to_workbench(Path(payload))
                    except Exception:
                        pass
                elif mt == "update_file_paths":
                    old_name, new_path = payload
                    new_path = Path(new_path)
                    self._file_paths[old_name] = new_path
                    # Update file list display with new filename
                    new_name = new_path.name
                    self._update_file_list_item_with_new_name(old_name, new_name)
            except Exception:
                import traceback
                self._append_log(f"[内部错误] {traceback.format_exc()}")
        QTimer.singleShot(200, self._poll_ui_queue)

    # ═══════════════════════════════════════════════════════════════════════
    # File list UI
    # ═══════════════════════════════════════════════════════════════════════
    def _reset_file_list(self, items: list[tuple[str, str]]) -> None:
        self.file_list.clear()
        self._file_statuses.clear()
        self._file_sizes.clear()
        self._file_times.clear()
        self._file_paths.clear()
        for name, full_path in items:
            try:
                size_bytes = os.path.getsize(full_path)
                size_str = f"{size_bytes / (1024*1024):.1f}MB" if size_bytes >= 1024*1024 else f"{size_bytes/1024:.0f}KB"
            except Exception:
                size_str = "?"
            self._file_sizes[name] = size_str
            self._file_times[name] = datetime.now().strftime("%H:%M")
            self._file_paths[name] = Path(full_path)
            item = QListWidgetItem(f"{name}\n{size_str} · {self._file_times.get(name, '')}")
            item.setData(Qt.ItemDataRole.UserRole, "waiting")
            item.setForeground(QColor(_token(self._shell, "text2", "#98989E")))
            self.file_list.addItem(item)
            self._file_statuses[name] = "waiting"
        self._append_log(f"扫描开始 → 找到 {len(items)} 个 PDF 文件")

    def _update_file_list_item(self, filename: str, status: str) -> None:
        icons = {
            "waiting": "⏳", "scanning": "🔍", "ocr": "🔍", "extracting": "🔍",
            "pending": "✋", "renaming": "✎", "moving": "→", "queued": "→",
            "done": "✅", "failed": "❌",
        }
        primary  = _token(self._shell, "primary", "#0A84FF")
        success  = _token(self._shell, "success", "#30D158")
        warning  = _token(self._shell, "warning", "#FF9F0A")
        danger   = _token(self._shell, "danger", "#FF453A")
        text2    = _token(self._shell, "text2", "#98989E")
        colors = {
            "waiting": text2, "scanning": primary, "ocr": primary,
            "extracting": primary, "pending": warning, "renaming": primary,
            "moving": primary, "queued": primary, "done": success, "failed": danger,
        }
        icon = icons.get(status, "⏳")
        color = colors.get(status, text2)
        self._set_file_list_item(filename, icon, color, status)

    def _update_file_list_item_with_new_name(self, old_name: str, new_name: str) -> None:
        """After renaming, update list item to show the new filename."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item and old_name in item.text():
                st = item.data(Qt.ItemDataRole.UserRole) or "done"
                icon = "✅"
                color_ = _token(self._shell, "success", "#30D158")
                size = self._file_sizes.get(old_name, "?")
                item.setText(f"{icon}  {new_name}\n     {size} · {self._file_times.get(old_name, '')}")
                item.setForeground(QColor(color_))
                item.setData(Qt.ItemDataRole.UserRole, "done")
                # Update all tracking dicts
                self._file_statuses[new_name] = st
                if old_name in self._file_statuses:
                    del self._file_statuses[old_name]
                if old_name in self._file_sizes:
                    self._file_sizes[new_name] = self._file_sizes.pop(old_name)
                if old_name in self._file_times:
                    self._file_times[new_name] = self._file_times.pop(old_name)
                if old_name in self._file_paths:
                    pass  # already updated by update_file_paths handler
                # Re-apply filter
                filter_text = self.search_box.text().strip().lower() if hasattr(self, "search_box") else ""
                matches_search = (not filter_text) or (filter_text in item.text().lower())
                matches_filter = self._filter_matches(item)
                item.setHidden(not (matches_search and matches_filter))
                break

    def _set_file_list_item(self, filename: str, icon: str, color: str, status: str) -> None:
        size = self._file_sizes.get(filename, "?")

        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item and filename in item.text():
                item.setData(Qt.ItemDataRole.UserRole, status)
                item.setText(f"{icon}  {filename}\n     {size} · {self._file_times.get(filename, '')}")
                item.setForeground(QColor(color))
                self._file_statuses[filename] = status
                if status == "pending":
                    self.file_list.setCurrentItem(item)
                    self.file_list.scrollToItem(item)
                # Re-apply current filter so visibility updates after status change
                filter_text = self.search_box.text().strip().lower() if hasattr(self, "search_box") else ""
                matches_search = (not filter_text) or (filter_text in item.text().lower())
                matches_filter = self._filter_matches(item)
                item.setHidden(not (matches_search and matches_filter))
                break

    # ═══════════════════════════════════════════════════════════════════════
    # Pending review
    # ═══════════════════════════════════════════════════════════════════════
    def _show_pending(self, pending: object) -> None:
        if not isinstance(pending, PendingRename):
            return
        self.pending_review = pending
        self.summary.reviewed += 1
        self._refresh_summary()
        e = pending.extraction

        self._ocr_vendor_value.setText(e.vendor_name or "未识别")
        self._ocr_contract_value.setText(e.contract_no or "未识别")
        # Show cache hit info
        self._ocr_cache_value.setText(self._pending_cache_info or "无匹配")
        self._update_cache_value_style()
        # Extract date from OCR text (extractor doesn't have date field)
        self._ocr_date_value.setText(self._extract_date_from_text(pending.ocr_text))

        self.suggested_entry.setText(pending.suggested_name)
        self.suggested_entry.setFocus()
        self.suggested_entry.selectAll()

        self._pending_ocr_text = pending.ocr_text
        if self._ocr_visible:
            self.ocr_text.setPlainText(pending.ocr_text)

        self.confirm_button.setEnabled(True)
        self.skip_button.setEnabled(True)
        self._set_progress(f"等待确认: {pending.original_name}")

        self._review_status_pill.setObjectName("tagBlue")
        self._review_status_pill.setStyleSheet("")
        self._review_status_pill.setText("待确认")

        # Load PDF preview for this file
        self._current_pdf_path = pending.original_path
        self._load_preview(pending.original_path)

        self._append_log(f"生成文件名 → {pending.suggested_name}")
        self._append_log("等待确认")

        # Highlight rename card when pending review
        self._set_rename_card_active(True)

    def _confirm_current(self) -> None:
        if not self.pending_review or not self.pending_event:
            return
        name = self.suggested_entry.text().strip()
        if not name:
            QMessageBox.warning(self, "文件名为空", "请输入建议文件名后再确认。")
            return
        self.pending_decision = ("confirm", name)
        self.pending_event.set()
        self.summary.reviewed = max(0, self.summary.reviewed - 1)
        self._append_log(f"重命名完成 → {name}")
        self._refresh_summary()
        self._clear_review_panel()

    def _skip_current(self) -> None:
        if not self.pending_review or not self.pending_event:
            return
        self.pending_decision = ("skip", None)
        self.pending_event.set()
        self.summary.reviewed = max(0, self.summary.reviewed - 1)
        self._refresh_summary()
        self._clear_review_panel()

    def _handle_record(self, payload: object) -> None:
        if not isinstance(payload, LogEntry):
            return
        if payload.status == "成功":
            self.summary.success += 1
        elif payload.status == "跳过":
            self.summary.skipped += 1
        else:
            self.summary.failed += 1
        self._refresh_summary()
        suffix = f" | {payload.error_reason}" if payload.error_reason else ""
        is_err = payload.status == "失败"
        self._append_log(f"[{payload.status}] {payload.original_name} → {payload.new_name or '-'}{suffix}", is_error=is_err)

    def _refresh_summary(self) -> None:
        total = max(self._total_files, len(self._file_statuses), 0)
        remaining = max(total - self.summary.success - self.summary.failed - self.summary.skipped - self.summary.reviewed, 0)
        self.summary_label.setText(
            f"已完成 {self.summary.success} · 失败 {self.summary.failed} · "
            f"跳过 {self.summary.skipped} · 待确认 {self.summary.reviewed}")
        if self._stat_value_labels:
            self._stat_value_labels.get("pending", QLabel()).setText(str(remaining))
            self._stat_value_labels.get("done",    QLabel()).setText(str(self.summary.success))
            self._stat_value_labels.get("failed",  QLabel()).setText(str(self.summary.failed))
            self._stat_value_labels.get("review",  QLabel()).setText(str(self.summary.reviewed))

    def _append_log(self, msg: str, is_error: bool = False) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        primary = _token(self._shell, "primary", "#0A84FF")
        danger  = _token(self._shell, "danger", "#FF453A")
        err_bg  = _token(self._shell, "err_bg", "#3D1C1A")
        text_c  = _token(self._shell, "text", "#F5F5F7")
        if is_error:
            html = (f'<div style="background:{err_bg}; color:{danger}; padding:3px 6px; '
                    f'border-left:3px solid {danger}; margin:1px 0; border-radius:4px;">'
                    f'{ts}  {msg}</div>')
        else:
            html = (f'<div style="color:{text_c}; padding:2px 0; '
                    f'border-left:3px solid {primary}; padding-left:6px; margin:1px 0;">'
                    f'{ts}  {msg}</div>')
        self.log_text.appendHtml(html)
        c = self.log_text.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(c)

    def _clear_review_panel(self) -> None:
        self.pending_review = None
        self._pending_cache_info = None
        self.suggested_entry.setText("")
        self._ocr_vendor_value.setText("等待识别")
        self._ocr_contract_value.setText("等待识别")
        self._ocr_date_value.setText("等待识别")
        self._ocr_cache_value.setText("等待识别")
        self._ocr_cache_value.setStyleSheet("")
        self._pending_ocr_text = ""
        self.ocr_text.clear()
        self.confirm_button.setEnabled(False)
        self.skip_button.setEnabled(False)
        self._review_status_pill.setObjectName("tagGray")
        self._review_status_pill.setStyleSheet("")
        self._review_status_pill.setText("待扫描")
        self._ocr_conf_pill.setObjectName("tagGray")
        self._ocr_conf_pill.setStyleSheet("")
        self._ocr_conf_pill.setText("-")
        self._current_pdf_path = None
        self.preview_label.setText("从左侧文件队列选择文件后显示预览")
        placeholder_color = _token(self._shell, "text3", "#6C6C72")
        self.preview_label.setStyleSheet(
            f"font-size: 12px; color: {placeholder_color}; background: transparent; padding: 30px;"
        )
        self.preview_label.setPixmap(QPixmap())
        self.page_label.setText("")
        self._preview_total = 0
        self.prev_page_btn.setVisible(False)
        self.next_page_btn.setVisible(False)
        self._set_rename_card_active(False)

    def _set_rename_card_active(self, active: bool) -> None:
        """Highlight border on the rename review card to draw attention."""
        card = self.findChild(QFrame, "renameCard")
        if card is not None:
            if active:
                card.setProperty("active", True)
            else:
                card.setProperty("active", False)
            card.style().unpolish(card)
            card.style().polish(card)

    def _finish_processing(self) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_button.setVisible(False)
        self.fetch_button.setEnabled(True)
        self.dual_radio.setEnabled(True)
        self.po_radio.setEnabled(True)
        if self.stop_event.is_set():
            self._set_progress("任务已终止")
        else:
            self._set_progress("批量任务已完成")
        self._review_status_pill.setObjectName("tagGray")
        self._review_status_pill.setStyleSheet("")
        self._review_status_pill.setText("完成")
        self._append_log("批量任务已结束。")

    # ═══════════════════════════════════════════════════════════════════════
    # Misc actions
    # ═══════════════════════════════════════════════════════════════════════
    _DATE_PATTERNS = [
        # Label-prefixed: 日期: 2024-12-01 / 日期 2024年12月1日
        re.compile(r"(?:日期|交易日期|付款日期|签订日期|签约日期)\s*[:：]?\s*(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})"),
        re.compile(r"(?:日期|交易日期|付款日期|签订日期|签约日期)\s*[:：]?\s*(\d{1,2})[-/月](\d{1,2})[-/日](\d{4})"),
        # Standalone: 2024-11-20 / 2024/11/20
        re.compile(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"),
        # Standalone Chinese: 2024年11月20日
        re.compile(r"\b(\d{4})年(\d{1,2})月(\d{1,2})日\b"),
    ]

    def _extract_date_from_text(self, ocr_text: str) -> str:
        for pat in self._DATE_PATTERNS:
            m = pat.search(ocr_text)
            if m:
                groups = m.groups()
                if len(groups) == 3:
                    a, b, c = groups
                    if len(a) == 4:
                        return f"{a}-{b.zfill(2)}-{c.zfill(2)}"
                    else:
                        return f"{c}-{a.zfill(2)}-{b.zfill(2)}"
                return groups[0]
        return "未识别日期"

    def _toggle_ocr(self) -> None:
        self._ocr_visible = not self._ocr_visible
        self.ocr_text.setVisible(self._ocr_visible)
        arrow = "识别文字 ▾" if self._ocr_visible else "识别文字 ▸"
        self.ocr_toggle.setText(f"{arrow}  识别文字")
        if self._ocr_visible and self._pending_ocr_text:
            self.ocr_text.setPlainText(self._pending_ocr_text)

    def _on_return_confirm(self) -> None:
        if hasattr(self, "confirm_button") and self.confirm_button.isEnabled():
            self._confirm_current()

    def _on_escape_skip(self) -> None:
        if hasattr(self, "skip_button") and self.skip_button.isEnabled():
            self._skip_current()

    def _copy_suggested_name(self) -> None:
        if hasattr(self, "suggested_entry"):
            QApplication.clipboard().setText(self.suggested_entry.text())
            self.progress_label.setText("已复制")
            QTimer.singleShot(1500, lambda: self.progress_label.setText("就绪"))

    def _open_output_folder(self) -> None:
        os.startfile(str(self.config.output_dir))

    def _set_progress(self, text: str) -> None:
        if hasattr(self, "progress_label"):
            self.progress_label.setText(text)

    # ═══════════════════════════════════════════════════════════════════════
    # Cache editor
    # ═══════════════════════════════════════════════════════════════════════
    def _edit_cache_entry(self) -> None:
        """点击缓存命中标签时，快速编辑当前匹配的供应商简称。"""
        if not self._pending_cache_info:
            return
        current = self._ocr_cache_value.text()
        dlg = CacheEditDialog(self, current)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_text = dlg.result_name.strip()
            if new_text and new_text != current:
                self._apply_cache_correction(new_text)

    def _apply_cache_correction(self, corrected_name: str) -> None:
        """将修正后的名称写回 vendor_cache。"""
        if not self.pending_review:
            return
        e = self.pending_review.extraction
        old_name = e.vendor_short_name
        e.vendor_short_name = corrected_name
        self.vendor_cache.remember(e.vendor_name, corrected_name)
        self._ocr_cache_value.setText(f"精确命中: {corrected_name} (全称: {e.vendor_name or '未知'}) [已修正]")
        self._update_cache_value_style()
        self._append_log(f"缓存已修正: {old_name} → {corrected_name}")
        # Update suggested name
        if old_name and corrected_name:
            self.suggested_entry.setText(
                self.suggested_entry.text().replace(old_name, corrected_name))

    def _update_cache_value_style(self) -> None:
        info = self._ocr_cache_value.text()
        if "模糊" in info:
            self._ocr_cache_value.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: #F0A030; background: transparent;")
        elif "精确" in info or "命中" in info:
            self._ocr_cache_value.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: #30C860; background: transparent;")
        elif "已修正" in info:
            self._ocr_cache_value.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: #5090F0; background: transparent;")
        else:
            self._ocr_cache_value.setStyleSheet(
                f"font-size: 13px; font-weight: 600; color: {_token(self._shell, 'text3', '#6C6C72')}; background: transparent;")
        self._ocr_cache_value.setCursor(Qt.CursorShape.PointingHandCursor if ("命中" in info or "匹配" in info) else Qt.CursorShape.ArrowCursor)

    def _open_cache_editor(self) -> None:
        """打开完整的缓存编辑器，列出所有供应商条目。"""
        dlg = VendorCacheManagerDialog(self, self.vendor_cache)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._append_log("供应商缓存已更新")

    # ═══════════════════════════════════════════════════════════════════════
    # Theme toggle
    # ═══════════════════════════════════════════════════════════════════════
    def _toggle_theme(self) -> None:
        """Toggle between dark and light mode."""
        new_mode = self._shell.toggle_theme()
        mode_text = "亮色模式" if new_mode == "light" else "暗黑模式"
        self._append_log(f"界面已切换为{mode_text}")
        self._refresh_summary()

    def _open_theme_dialog(self) -> None:
        dlg = ThemeSettingsDialog(self, self._shell._theme_overrides)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._shell.reload_theme(dlg.current_theme)
            self._refresh_summary()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._current_pdf_path:
            return
        # Debounce: re-render only after resize stops for 150ms
        if self._resize_timer is None:
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.setInterval(150)
            self._resize_timer.timeout.connect(self._render_preview_page)
        self._resize_timer.start()


# ═══════════════════════════════════════════════════════════════════════════
# Theme settings dialog
# ═══════════════════════════════════════════════════════════════════════════
class ThemeSettingsDialog(QDialog):
    COLOR_KEYS = [
        ("主背景色", "bg"),
        ("卡片背景色", "card"),
        ("主文字色", "text"),
        ("辅助文字色", "text2"),
        ("边框色", "border"),
        ("主色调(蓝)", "primary"),
        ("成功(绿)", "success"),
        ("警告(橙)", "warning"),
        ("错误(红)", "danger"),
        ("标签-绿色", "tag_green"),
        ("标签-橙色", "tag_orange"),
        ("标签-蓝色", "tag_blue"),
        ("标签-红色", "tag_red"),
        ("标签-灰色", "tag_gray"),
        ("日志区域背景", "log_bg"),
        ("错误日志背景", "err_bg"),
        ("错误日志文字", "err_text"),
        ("输入框背景", "input_bg"),
        ("输入框聚焦背景", "input_bg_focus"),
        ("卡片次要背景", "card_alt"),
        ("选中背景", "selection_bg"),
        ("悬停背景", "hover_bg"),
        ("边框-中", "border_m"),
        ("文字-第三级", "text3"),
    ]

    def __init__(self, parent: QWidget, current_theme: dict) -> None:
        super().__init__(parent)
        self.current_theme = dict(current_theme)
        self.setWindowTitle("界面颜色设置")
        self.setModal(True)
        self.resize(420, 520)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        inner = QWidget()
        form = QVBoxLayout(inner)
        form.setSpacing(4)

        self._btns: dict[str, QPushButton] = {}
        for display_name, key in self.COLOR_KEYS:
            row = QHBoxLayout()
            row.setContentsMargins(0, 2, 0, 2)
            label = QLabel(display_name)
            label.setFixedWidth(100)
            btn = QPushButton()
            btn.setFixedSize(60, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._update_btn_color(btn, self.current_theme[key])
            btn.clicked.connect(lambda _=False, k=key: self._pick_color(k))
            self._btns[key] = btn
            reset_btn = QPushButton("↺")
            reset_btn.setFixedSize(24, 24)
            reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reset_btn.clicked.connect(lambda _=False, k=key, d=display_name: self._reset_color(k))
            row.addWidget(label)
            row.addWidget(btn)
            row.addWidget(reset_btn)
            row.addStretch()
            form.addLayout(row)

        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        preview_btn = QPushButton("预览")
        preview_btn.setObjectName("primaryBtn")
        preview_btn.clicked.connect(self._preview)
        save_btn = QPushButton("保存并应用")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(preview_btn)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        # Inherit parent stylesheet so buttons match
        import unified.style as _s
        self._theme = dict(_s.TOKENS)
        self._theme.update(self.current_theme)
        self.setStyleSheet(parent.styleSheet())

    def _update_btn_color(self, btn: QPushButton, color: str) -> None:
        border_m = self._theme.get("border_m", "#D1D1D6")
        btn.setStyleSheet(
            f"background-color: {color}; border: 1px solid {border_m}; border-radius: 6px;"
        )

    def _pick_color(self, key: str) -> None:
        initial = QColor(self.current_theme.get(key, "#FFFFFF"))
        color = QColorDialog.getColor(initial, self, f"选择颜色 - {key}")
        if color.isValid():
            self.current_theme[key] = color.name()
            self._update_btn_color(self._btns[key], color.name())

    def _reset_color(self, key: str) -> None:
        default = _style.TOKENS.get(key, "#FFFFFF")
        self.current_theme[key] = default
        self._update_btn_color(self._btns[key], default)

    def _preview(self) -> None:
        self.parent()._shell.reload_theme(self.current_theme)


# ═══════════════════════════════════════════════════════════════════════════
# Cache edit dialog — 点击缓存命中标签时弹出，快速修正简称
# ═══════════════════════════════════════════════════════════════════════════
class CacheEditDialog(QDialog):
    def __init__(self, parent: QWidget, current_text: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("修正缓存供应商简称")
        self.setMinimumWidth(420)
        self.result_name = ""
        self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 18, 20, 18)

        info = QLabel(f"当前缓存匹配:\n{current_text}")
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 13px; color: #98989E;")
        layout.addWidget(info)

        layout.addWidget(QLabel("修正为简称（如: 林吉源）:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入正确的供应商简称")
        layout.addWidget(self.name_edit)

        hint = QLabel("此操作会更新 vendor_cache.json 中对应条目的简称和别名。")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; color: #6C6C72;")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存修正")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _accept(self) -> None:
        self.result_name = self.name_edit.text().strip()
        self.accept()


# ═══════════════════════════════════════════════════════════════════════════
# Vendor cache manager dialog — 完整的缓存编辑器
# ═══════════════════════════════════════════════════════════════════════════
class VendorCacheManagerDialog(QDialog):
    def __init__(self, parent: QWidget, vendor_cache: VendorCache) -> None:
        super().__init__(parent)
        self.setWindowTitle("供应商缓存管理")
        self.setMinimumSize(600, 420)
        self.vendor_cache = vendor_cache
        self._modified = False
        self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QLabel("双击单元格编辑简称和全称，右键删除条目。修改后点保存。")
        header.setStyleSheet("font-size: 12px; color: #98989E;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["供应商简称", "供应商全称", "命中次数"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self._load_data()
        layout.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _load_data(self) -> None:
        vendors = self.vendor_cache._data.get("vendors", [])
        self.table.setRowCount(len(vendors))
        for i, v in enumerate(vendors):
            sn = str(v.get("vendor_short_name", ""))
            fn = str(v.get("vendor_name", ""))
            cnt = str(v.get("count", ""))
            self.table.setItem(i, 0, QTableWidgetItem(sn))
            self.table.setItem(i, 1, QTableWidgetItem(fn))
            cnt_item = QTableWidgetItem(cnt)
            cnt_item.setFlags(cnt_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 2, cnt_item)

    def _on_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        menu = QMenu(self.table)
        delete_action = menu.addAction("删除此条目")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == delete_action:
            self.table.removeRow(row)
            self._modified = True

    def _save(self) -> None:
        vendors = []
        for i in range(self.table.rowCount()):
            sn_item = self.table.item(i, 0)
            fn_item = self.table.item(i, 1)
            cnt_item = self.table.item(i, 2)
            sn = sn_item.text().strip() if sn_item else ""
            fn = fn_item.text().strip() if fn_item else ""
            cnt = int(cnt_item.text()) if cnt_item and cnt_item.text().isdigit() else 1
            if not sn and not fn:
                continue
            vendors.append({
                "vendor_name": fn,
                "vendor_short_name": sn,
                "aliases": sorted({fn, sn}),
                "count": cnt,
                "first_seen": "",
                "last_seen": "",
            })
        self.vendor_cache._data["vendors"] = vendors
        self.vendor_cache.save()
        self._modified = True
        self.accept()
