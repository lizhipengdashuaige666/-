"""Payment detail dialog — info card, status timeline, action buttons, attachments."""

from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from unified.payment_models import (
    STATUS_DISPLAY,
    TRANSITIONS,
    PaymentLog,
    PaymentRecord,
    PaymentStatus,
)
from unified.payment_service import PaymentService
from unified.style import FontSize, FontWeight, apply_shadow


class PaymentDetailDialog(QDialog):
    def __init__(
        self, payment_id: int, service: PaymentService,
        parent: QWidget | None = None, shell: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._payment_id = payment_id
        self._service = service
        self._shell = shell
        self._record: PaymentRecord | None = None
        self._is_light = self._detect_light()

        self.setWindowTitle("付款详情")
        self.setMinimumSize(580, 520)
        self.resize(620, 600)
        self.setModal(True)
        self._build_ui()
        self._load_data()

    def _detect_light(self) -> bool:
        if self._shell and hasattr(self._shell, '_theme_overrides'):
            return self._shell._theme_overrides.get("_mode") == "light"
        return True

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ── Info card ──
        info_card = QFrame()
        info_card.setObjectName("card")
        info_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_shadow(info_card, elevation=1, is_light=self._is_light)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(18, 16, 18, 16)
        info_layout.setSpacing(8)

        self._title_label = QLabel()
        self._title_label.setObjectName("cardTitle")
        info_layout.addWidget(self._title_label)

        self._info_grid = QVBoxLayout()
        self._info_grid.setSpacing(4)
        info_layout.addLayout(self._info_grid)

        self._notes_label = QLabel()
        self._notes_label.setObjectName("sideSubtitle")
        self._notes_label.setWordWrap(True)
        info_layout.addWidget(self._notes_label)

        root.addWidget(info_card)

        # ── Action buttons ──
        self._actions_row = QHBoxLayout()
        self._actions_row.setSpacing(10)
        root.addLayout(self._actions_row)

        # ── Status timeline ──
        timeline_label = QLabel("状态记录")
        timeline_label.setObjectName("sectionLabel")
        root.addWidget(timeline_label)

        timeline_frame = QFrame()
        timeline_frame.setObjectName("card")
        timeline_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_shadow(timeline_frame, elevation=1, is_light=self._is_light)
        tl_outer = QVBoxLayout(timeline_frame)
        tl_outer.setContentsMargins(14, 12, 14, 12)

        self._timeline_scroll = QScrollArea()
        self._timeline_scroll.setWidgetResizable(True)
        self._timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._timeline_scroll.setMaximumHeight(180)
        self._timeline_content = QWidget()
        self._timeline_layout = QVBoxLayout(self._timeline_content)
        self._timeline_layout.setContentsMargins(0, 0, 0, 0)
        self._timeline_layout.setSpacing(0)
        self._timeline_layout.addStretch()
        self._timeline_scroll.setWidget(self._timeline_content)
        tl_outer.addWidget(self._timeline_scroll)
        root.addWidget(timeline_frame)

        # ── Attachments ──
        attach_label = QLabel("附件")
        attach_label.setObjectName("sectionLabel")
        root.addWidget(attach_label)

        attach_frame = QFrame()
        attach_frame.setObjectName("card")
        attach_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        apply_shadow(attach_frame, elevation=1, is_light=self._is_light)
        af_layout = QVBoxLayout(attach_frame)
        af_layout.setContentsMargins(14, 12, 14, 12)
        af_layout.setSpacing(6)
        self._attach_list = QVBoxLayout()
        self._attach_list.setSpacing(4)
        af_layout.addLayout(self._attach_list)
        root.addWidget(attach_frame)

        # ── Close ──
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.accept)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

    def _load_data(self) -> None:
        self._record = self._service.get_by_id(self._payment_id)
        if self._record is None:
            return

        r = self._record
        status_info = STATUS_DISPLAY.get(r.status_enum, ("未知", "tagGray", "#999"))
        self.setWindowTitle(f"付款详情 — {r.payment_no}")
        self._title_label.setText(f"{r.supplier_name}  ·  ¥{r.amount:,.2f}")

        # Info rows
        info_rows = [
            ("付款单号", r.payment_no),
            ("供应商", r.supplier_name),
            ("金额", f"¥{r.amount:,.2f}"),
            ("申请日期", r.apply_date),
            ("PO号", r.po_number or "—"),
            ("创建时间", r.created_time),
            ("更新时间", r.updated_time),
        ]
        while self._info_grid.count():
            item = self._info_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for label_text, value_text in info_rows:
            row_w = QWidget()
            row_layout = QHBoxLayout(row_w)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            lbl = QLabel(label_text)
            lbl.setObjectName("sideSubtitle")
            lbl.setFixedWidth(70)
            val = QLabel(value_text)
            val.setObjectName("ocrValue")
            val.setWordWrap(True)
            row_layout.addWidget(lbl)
            row_layout.addWidget(val, 1)
            self._info_grid.addWidget(row_w)

        if r.notes:
            self._notes_label.setText(f"备注: {r.notes}")
        else:
            self._notes_label.hide()

        # Status badge in title
        self._title_label.setText(
            f"{r.supplier_name}  ·  ¥{r.amount:,.2f}  [{status_info[0]}]"
        )

        # Action buttons
        self._build_action_buttons()

        # Timeline
        logs = self._service.get_logs_for_payment(self._payment_id)
        self._build_timeline(logs)

        # Attachments
        attachments = self._service.get_attachments(self._payment_id)
        self._build_attachments(attachments)

    def _build_action_buttons(self) -> None:
        while self._actions_row.count():
            item = self._actions_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._record is None:
            return

        current = self._record.status_enum
        allowed = TRANSITIONS.get(current, [])

        if not allowed:
            label = QLabel("已是终态，无需操作")
            label.setObjectName("sideSubtitle")
            self._actions_row.addWidget(label)
        else:
            label = QLabel("推进状态:")
            label.setObjectName("ocrValue")
            self._actions_row.addWidget(label)
            for target in allowed:
                disp = STATUS_DISPLAY.get(target, (target.value, "tagGray", "#999"))
                btn = QPushButton(f"标记为「{disp[0]}」")
                btn.setObjectName("primaryBtn")
                btn.clicked.connect(lambda checked, t=target: self._do_transition(t))
                self._actions_row.addWidget(btn)

        self._actions_row.addStretch()

    def _do_transition(self, target: PaymentStatus) -> None:
        try:
            self._service.transition_status(
                self._payment_id, target.value,
                operator="当前用户",
            )
            self._load_data()
        except ValueError as e:
            QMessageBox.warning(self, "操作失败", str(e))

    def _build_timeline(self, logs: list[PaymentLog]) -> None:
        # Remove old entries (keep the stretch at the end)
        while self._timeline_layout.count() > 1:
            item = self._timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not logs:
            empty = QLabel("暂无状态变更记录")
            empty.setObjectName("sideSubtitle")
            self._timeline_layout.insertWidget(0, empty)
            return

        for log_entry in logs:
            entry = self._make_timeline_entry(log_entry)
            self._timeline_layout.insertWidget(self._timeline_layout.count() - 1, entry)

    def _make_timeline_entry(self, log_entry: PaymentLog) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(10)

        # Dot
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot_color = "#007AFF"
        if "导入" in log_entry.action:
            dot_color = "#2B8A3E"
        elif "已付款" in log_entry.new_status:
            dot_color = "#2B8A3E"
        dot.setStyleSheet(
            f"background: {dot_color}; border-radius: 5px; border: none;"
        )
        row.addWidget(dot)

        # Content
        content = QVBoxLayout()
        content.setSpacing(2)
        action_lbl = QLabel(log_entry.action)
        action_lbl.setObjectName("ocrValue")
        meta_text = f"{log_entry.timestamp}  ·  {log_entry.operator}"
        meta_lbl = QLabel(meta_text)
        meta_lbl.setObjectName("sideSubtitle")
        if log_entry.notes:
            notes_lbl = QLabel(log_entry.notes)
            notes_lbl.setObjectName("sideSubtitle")
            content.addWidget(notes_lbl)
        content.addWidget(action_lbl)
        content.addWidget(meta_lbl)
        row.addLayout(content, 1)

        return w

    def _build_attachments(self, attachments) -> None:
        while self._attach_list.count():
            item = self._attach_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        add_btn = QPushButton("+ 添加附件")
        add_btn.setObjectName("smallBtn")
        add_btn.clicked.connect(self._add_attachment)
        self._attach_list.addWidget(add_btn)

        if not attachments:
            empty = QLabel("暂无附件")
            empty.setObjectName("sideSubtitle")
            self._attach_list.addWidget(empty)
            return

        for att in attachments:
            row_w = QWidget()
            row = QHBoxLayout(row_w)
            row.setContentsMargins(0, 2, 0, 2)
            row.setSpacing(8)
            name_lbl = QLabel(att.filename)
            name_lbl.setObjectName("ocrValue")
            row.addWidget(name_lbl, 1)
            open_btn = QPushButton("打开")
            open_btn.setObjectName("smallBtn")
            open_btn.clicked.connect(lambda checked, p=att.filepath: os.startfile(p))
            del_btn = QPushButton("删除")
            del_btn.setObjectName("dangerButton")
            del_btn.clicked.connect(lambda checked, aid=att.id: self._remove_attachment(aid))
            row.addWidget(open_btn)
            row.addWidget(del_btn)
            self._attach_list.addWidget(row_w)

    def _add_attachment(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择附件", "",
            "所有文件 (*.*);;图片 (*.png *.jpg *.jpeg *.bmp);;PDF (*.pdf)",
        )
        if path:
            self._service.add_attachment(self._payment_id, path)
            self._load_data()

    def _remove_attachment(self, attachment_id: int) -> None:
        r = QMessageBox.question(
            self, "确认删除", "确定要删除此附件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r == QMessageBox.StandardButton.Yes:
            self._service.remove_attachment(attachment_id)
            self._load_data()
