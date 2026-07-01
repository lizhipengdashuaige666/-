"""Payment tracking main page — dashboard, filters, card list, import/export."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from unified import style as _style
from unified.payment_detail import PaymentDetailDialog
from unified.payment_import import PaymentImportDialog
from unified.payment_models import (
    STATUS_DISPLAY,
    TRANSITIONS,
    PaymentRecord,
    PaymentStatus,
)
from unified.payment_service import PaymentService
from unified.style import FontSize, FontWeight, apply_shadow


class PaymentTrackingView(QWidget):
    def __init__(
        self, parent: QWidget | None = None, shell: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._shell = shell
        self.setObjectName("paymentRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAcceptDrops(True)

        self._service = PaymentService()
        self._filters: dict = {}
        self._current_query = ""
        self._all_records: list[PaymentRecord] = []
        self._sort_by = "updated_time"
        self._sort_desc = True

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._apply_filters)

        self._build_ui()
        self._refresh_all()

    @property
    def _is_light(self) -> bool:
        if self._shell and hasattr(self._shell, '_theme_overrides'):
            return self._shell._theme_overrides.get("_mode") == "light"
        return True

    # ── Build UI ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        # Header row
        header_row = QHBoxLayout()
        title = QLabel("付款跟踪中心")
        title.setObjectName("toolbarTitle")
        subtitle = QLabel("跟踪付款申请审批与到账状态，自动检测逾期")
        subtitle.setObjectName("toolbarSubtitle")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header_row.addLayout(title_col)
        header_row.addStretch()

        import_btn = QPushButton("导入 Excel")
        import_btn.setObjectName("primaryBtn")
        import_btn.clicked.connect(self._on_import)
        export_btn = QPushButton("导出")
        export_btn.setObjectName("secondaryBtn")
        export_btn.clicked.connect(self._on_export)
        header_row.addWidget(export_btn)
        header_row.addWidget(import_btn)
        root.addLayout(header_row)

        # Dashboard cards
        root.addWidget(self._build_dashboard())

        # Filter bar
        root.addWidget(self._build_filter_bar())

        # Card list area
        self._list_area = QScrollArea()
        self._list_area.setWidgetResizable(True)
        self._list_area.setFrameShape(QFrame.Shape.NoFrame)
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        self._list_area.setWidget(self._list_widget)
        root.addWidget(self._list_area, 1)

        # Status bar
        self._status_label = QLabel()
        self._status_label.setObjectName("sideSubtitle")
        root.addWidget(self._status_label)

    def _build_dashboard(self) -> QWidget:
        card = QFrame()
        card.setObjectName("statCard")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_shadow(card, elevation=1, is_light=self._is_light)
        self._dash_layout = QHBoxLayout(card)
        self._dash_layout.setContentsMargins(16, 14, 16, 14)
        self._dash_layout.setSpacing(12)

        stat_specs = [
            ("待审批", "pending", "待审批"),
            ("待财务", "review", "待财务"),
            ("已付款", "done", "已付款"),
            ("逾期提醒", "failed", "逾期"),
        ]
        self._stat_labels: dict[str, tuple[QLabel, QLabel]] = {}
        for label_text, role, key in stat_specs:
            val_label, desc_label = self._make_stat_card(label_text, role)
            self._dash_layout.addWidget(val_label.parent())
            self._stat_labels[key] = (val_label, desc_label)

        return card

    def _make_stat_card(self, label_text: str, role: str) -> tuple[QLabel, QLabel]:
        frame = QFrame()
        frame.setObjectName("card")
        frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        val = QLabel("—")
        val.setObjectName("statValue")
        val.setProperty("statRole", role)
        lbl = QLabel(label_text)
        lbl.setObjectName("statLabel")
        layout.addWidget(val)
        layout.addWidget(lbl)
        return val, lbl

    def _build_filter_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("card")
        bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_shadow(bar, elevation=1, is_light=self._is_light)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self._search_box = QLineEdit()
        self._search_box.setObjectName("searchBox")
        self._search_box.setPlaceholderText("搜索供应商、付款单号、PO号...")
        self._search_box.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_box, 1)

        self._status_combo = QComboBox()
        self._status_combo.addItem("全部状态", None)
        self._status_combo.addItem("待审批", "待审批")
        self._status_combo.addItem("待财务", "待财务")
        self._status_combo.addItem("已付款", "已付款")
        self._status_combo.addItem("逾期(待财务>7天)", "__overdue__")
        self._status_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self._status_combo)

        self._sort_combo = QComboBox()
        self._sort_combo.addItem("最近更新", "updated_time_desc")
        self._sort_combo.addItem("金额降序", "amount_desc")
        self._sort_combo.addItem("金额升序", "amount_asc")
        self._sort_combo.addItem("申请日期降序", "apply_date_desc")
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        layout.addWidget(self._sort_combo)

        clear_btn = QPushButton("清除")
        clear_btn.setObjectName("smallBtn")
        clear_btn.clicked.connect(self._clear_filters)
        layout.addWidget(clear_btn)

        return bar

    # ── Data loading ──────────────────────────────────────────────────

    def _refresh_all(self) -> None:
        self._all_records = self._service.search(
            query=self._current_query, filters=self._filters,
            sort_by=self._sort_by, sort_desc=self._sort_desc, limit=500,
        )
        self._refresh_dashboard()
        self._rebuild_card_list()
        self._status_label.setText(f"共 {len(self._all_records)} 条记录")

    def _refresh_dashboard(self) -> None:
        stats = self._service.get_dashboard_stats()
        by_status = stats["by_status"]
        overdue = stats["overdue_count"]

        updates = {
            "待审批": str(by_status.get("待审批", 0)),
            "待财务": str(by_status.get("待财务", 0)),
            "已付款": str(by_status.get("已付款", 0)),
            "逾期": str(overdue),
        }
        for key, (val_label, _) in self._stat_labels.items():
            val_label.setText(updates.get(key, "0"))

    def _rebuild_card_list(self) -> None:
        # Remove old cards (keep stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._all_records:
            empty = QLabel("暂无付款记录\n点击「导入 Excel」或拖放 Excel 文件开始")
            empty.setObjectName("hint")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(120)
            self._list_layout.insertWidget(0, empty)
            return

        overdue_ids = {r.id for r in self._service.scan_overdue()}

        for record in self._all_records:
            card = self._make_payment_card(record, record.id in overdue_ids)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

    def _make_payment_card(self, record: PaymentRecord, is_overdue: bool) -> QFrame:
        status_enum = record.status_enum
        disp = STATUS_DISPLAY.get(status_enum, ("未知", "tagGray", "#999"))
        status_color = disp[2]

        card = QFrame()
        card.setObjectName("card")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card.setStyleSheet(
            f"QFrame#card {{ border-left: 4px solid {status_color}; }}"
        )
        apply_shadow(card, elevation=1, is_light=self._is_light)

        row = QHBoxLayout(card)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        # Status badge
        badge = QLabel(disp[0])
        badge.setObjectName(disp[1])
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedWidth(56)
        row.addWidget(badge)

        # Center info
        info = QVBoxLayout()
        info.setSpacing(3)

        supplier_lbl = QLabel(record.supplier_name)
        supplier_lbl.setObjectName("cardTitle")

        detail_text = record.payment_no
        if record.po_number:
            detail_text = f"{record.po_number}  /  {record.payment_no}"
        detail_lbl = QLabel(detail_text)
        detail_lbl.setObjectName("sideSubtitle")

        info.addWidget(supplier_lbl)
        info.addWidget(detail_lbl)

        if is_overdue:
            overdue_lbl = QLabel("逾期")
            overdue_lbl.setObjectName("tagRed")
            overdue_lbl.setFixedWidth(40)
            info.addWidget(overdue_lbl)

        row.addLayout(info, 1)

        # Amount + date
        amount_col = QVBoxLayout()
        amount_col.setSpacing(2)
        amount_lbl = QLabel(f"¥{record.amount:,.2f}")
        amount_lbl.setObjectName("infoValue")
        amount_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        date_lbl = QLabel(record.apply_date)
        date_lbl.setObjectName("sideSubtitle")
        date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        amount_col.addWidget(amount_lbl)
        amount_col.addWidget(date_lbl)
        row.addLayout(amount_col)

        # Action buttons
        action_col = QVBoxLayout()
        action_col.setSpacing(4)

        view_btn = QPushButton("查看")
        view_btn.setObjectName("smallBtn")
        view_btn.clicked.connect(lambda checked, rid=record.id: self._on_view(rid))
        action_col.addWidget(view_btn)

        allowed = TRANSITIONS.get(status_enum, [])
        if allowed:
            next_status = allowed[0]
            next_disp = STATUS_DISPLAY.get(next_status, ("推进", "tagGray", "#999"))
            advance_btn = QPushButton(next_disp[0])
            advance_btn.setObjectName("smallBtn")
            advance_btn.clicked.connect(
                lambda checked, rid=record.id, ns=next_status: self._on_advance(rid, ns)
            )
            action_col.addWidget(advance_btn)

        row.addLayout(action_col)

        return card

    # ── Event handlers ────────────────────────────────────────────────

    def _on_search_changed(self, _text: str) -> None:
        self._search_timer.start()

    def _apply_filters(self) -> None:
        self._current_query = self._search_box.text().strip()

        status_val = self._status_combo.currentData()
        self._filters = {}
        if status_val == "__overdue__":
            self._filters["status"] = ["待财务"]
        elif status_val:
            self._filters["status"] = [status_val]

        self._refresh_all()

    def _on_sort_changed(self) -> None:
        sort_data = self._sort_combo.currentData()
        mapping = {
            "updated_time_desc": ("updated_time", True),
            "amount_desc": ("amount", True),
            "amount_asc": ("amount", False),
            "apply_date_desc": ("apply_date", True),
        }
        self._sort_by, self._sort_desc = mapping.get(sort_data, ("updated_time", True))
        self._refresh_all()

    def _clear_filters(self) -> None:
        self._search_box.clear()
        self._status_combo.setCurrentIndex(0)
        self._sort_combo.setCurrentIndex(0)
        self._filters = {}
        self._current_query = ""
        self._sort_by = "updated_time"
        self._sort_desc = True
        self._refresh_all()

    def _on_view(self, payment_id: int) -> None:
        dlg = PaymentDetailDialog(payment_id, self._service, parent=self, shell=self._shell)
        dlg.exec()
        self._refresh_all()

    def _on_advance(self, payment_id: int, target: PaymentStatus) -> None:
        try:
            self._service.transition_status(payment_id, target.value, operator="当前用户")
            self._refresh_all()
        except ValueError as e:
            QMessageBox.warning(self, "操作失败", str(e))

    def _on_import(self) -> None:
        dlg = PaymentImportDialog(self._service, parent=self, shell=self._shell)
        if dlg.exec():
            self._refresh_all()

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "导出付款记录", "付款记录_导出.xlsx",
            "Excel 文件 (*.xlsx)",
        )
        if path:
            count = self._service.export_to_excel(path, filters=self._filters)
            QMessageBox.information(
                self, "导出完成", f"成功导出 {count} 条付款记录",
            )

    # ── Drag-drop ─────────────────────────────────────────────────────

    def add_paths(self, paths: list[Path]) -> None:
        for p in paths:
            if p.suffix.lower() in (".xlsx", ".xls"):
                dlg = PaymentImportDialog(self._service, parent=self, shell=self._shell)
                dlg._filepath = str(p)
                dlg._parse_preview()
                dlg._show_step2()
                if dlg.exec():
                    self._refresh_all()
                return

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()]
        self.add_paths(paths)
