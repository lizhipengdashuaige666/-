"""Excel import wizard — file selection → preview → results."""

from __future__ import annotations

from pathlib import Path

import openpyxl
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QProgressBar, QPushButton, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from unified.payment_models import ImportResult
from unified.payment_service import PaymentService
from unified.style import FontSize, FontWeight, apply_shadow


class PaymentImportDialog(QDialog):
    def __init__(
        self, service: PaymentService,
        parent: QWidget | None = None, shell: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._shell = shell
        self._filepath: str = ""
        self._preview_data: list[dict] = []
        self._is_light = self._detect_light()

        self.setWindowTitle("导入付款申请")
        self.setMinimumSize(640, 520)
        self.resize(680, 560)
        self.setModal(True)
        self._build_ui()

    def _detect_light(self) -> bool:
        if self._shell and hasattr(self._shell, '_theme_overrides'):
            return self._shell._theme_overrides.get("_mode") == "light"
        return True

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        self._stack.addWidget(self._build_step3())
        root.addWidget(self._stack, 1)

    # ── Step 1: File selection ────────────────────────────────────────

    def _build_step1(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = QLabel("导入付款申请 Excel")
        title.setObjectName("toolbarTitle")
        subtitle = QLabel("支持从 ERP 导出的付款申请单 Excel 文件\n自动识别表头，跳过重复单号")
        subtitle.setObjectName("toolbarSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        drop = QFrame()
        drop.setObjectName("dropPanel")
        drop.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        drop.setAcceptDrops(True)
        drop.setMinimumHeight(200)
        drop.dragEnterEvent = self._step1_drag_enter
        drop.dragMoveEvent = self._step1_drag_enter
        drop.dropEvent = self._step1_drop
        dl = QVBoxLayout(drop)
        dl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_title = QLabel("拖放 Excel 文件到此处")
        drop_title.setObjectName("dropTitle")
        drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_hint = QLabel("或点击下方按钮选择文件")
        drop_hint.setObjectName("hint")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.addWidget(drop_title)
        dl.addWidget(drop_hint)
        layout.addWidget(drop, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        select_btn = QPushButton("选择 Excel 文件")
        select_btn.setObjectName("primaryBtn")
        select_btn.clicked.connect(self._select_file)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(select_btn)
        layout.addLayout(btn_row)

        return page

    def _step1_drag_enter(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _step1_drop(self, event) -> None:
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()]
        for p in paths:
            if p.suffix.lower() in (".xlsx", ".xls"):
                self._filepath = str(p)
                self._parse_preview()
                self._show_step2()
                return
        QMessageBox.warning(self, "格式错误", "请拖放 Excel 文件（.xlsx / .xls）")

    def _select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择付款申请 Excel", "",
            "Excel 文件 (*.xlsx *.xls);;所有文件 (*.*)",
        )
        if path:
            self._filepath = path
            self._parse_preview()
            self._show_step2()

    # ── Step 2: Preview ───────────────────────────────────────────────

    def _build_step2(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("预览数据")
        title.setObjectName("toolbarTitle")
        self._step2_summary = QLabel()
        self._step2_summary.setObjectName("toolbarSubtitle")
        layout.addWidget(title)
        layout.addWidget(self._step2_summary)

        self._preview_table = QTableWidget()
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._preview_table.horizontalHeader().setStretchLastSection(True)
        self._preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._preview_table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        back_btn = QPushButton("返回")
        back_btn.setObjectName("secondaryBtn")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        import_btn = QPushButton("确认导入")
        import_btn.setObjectName("primaryBtn")
        import_btn.clicked.connect(self._do_import)
        btn_row.addStretch()
        btn_row.addWidget(back_btn)
        btn_row.addWidget(import_btn)
        layout.addLayout(btn_row)

        return page

    def _parse_preview(self) -> None:
        self._preview_data = []
        try:
            wb = openpyxl.load_workbook(self._filepath, data_only=True)
            ws = wb.active
            if ws is None:
                return
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            if not rows:
                return

            _, col_map = PaymentService._detect_columns(rows)
            if col_map.get("payment_no") is None:
                return

            header_row = 0
            for i in range(min(10, len(rows))):
                cells = [str(c).strip() if c else "" for c in rows[i]]
                if any("付款申请单号" in c or "申请单号" in c for c in cells):
                    header_row = i
                    break

            data_rows = rows[header_row + 1:]
            for row in data_rows:
                payment_no = PaymentService._cell_str(row, col_map.get("payment_no"))
                supplier = PaymentService._cell_str(row, col_map.get("supplier"))
                amount_raw = PaymentService._cell_str(row, col_map.get("amount"))
                apply_date = PaymentService._cell_str(row, col_map.get("apply_date"))
                po_number = PaymentService._cell_str(row, col_map.get("po_number"))
                notes = PaymentService._cell_str(row, col_map.get("notes"))

                if not payment_no:
                    continue

                is_dup = self._service.get_by_payment_no(payment_no) is not None
                self._preview_data.append({
                    "payment_no": payment_no,
                    "supplier": supplier,
                    "amount": amount_raw,
                    "apply_date": apply_date,
                    "po_number": po_number,
                    "notes": notes,
                    "is_duplicate": is_dup,
                })
        except Exception as e:
            QMessageBox.warning(self, "解析失败", f"无法读取 Excel 文件:\n{e}")

    def _show_step2(self) -> None:
        new = sum(1 for d in self._preview_data if not d["is_duplicate"])
        dup = sum(1 for d in self._preview_data if d["is_duplicate"])
        self._step2_summary.setText(
            f"共解析 {len(self._preview_data)} 条记录，其中 {new} 条新记录，{dup} 条已存在（将跳过）"
        )

        headers = ["付款申请单号", "供应商", "金额", "申请日期", "PO号", "备注", "状态"]
        preview = self._preview_data[:20]
        self._preview_table.setColumnCount(len(headers))
        self._preview_table.setHorizontalHeaderLabels(headers)
        self._preview_table.setRowCount(len(preview))

        for i, d in enumerate(preview):
            items = [
                d["payment_no"], d["supplier"], d["amount"],
                d["apply_date"], d["po_number"], d["notes"],
                "已存在(跳过)" if d["is_duplicate"] else "新记录",
            ]
            for j, val in enumerate(items):
                item = QTableWidgetItem(val)
                if d["is_duplicate"]:
                    item.setForeground(Qt.GlobalColor.gray)
                self._preview_table.setItem(i, j, item)

        self._stack.setCurrentIndex(1)

    # ── Step 3: Results ───────────────────────────────────────────────

    def _build_step3(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("导入完成")
        title.setObjectName("toolbarTitle")
        layout.addWidget(title)

        self._result_label = QLabel()
        self._result_label.setObjectName("ocrValue")
        self._result_label.setWordWrap(True)
        layout.addWidget(self._result_label)

        self._error_list = QLabel()
        self._error_list.setObjectName("sideSubtitle")
        self._error_list.setWordWrap(True)
        layout.addWidget(self._error_list)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        close_btn = QPushButton("完成")
        close_btn.setObjectName("primaryBtn")
        close_btn.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        return page

    def _do_import(self) -> None:
        result = self._service.import_from_excel(self._filepath)
        self._show_step3(result)

    def _show_step3(self, result: ImportResult) -> None:
        parts = []
        parts.append(f"成功导入: {result.imported} 条")
        if result.skipped:
            parts.append(f"跳过重复: {result.skipped} 条")
        if result.errors:
            parts.append(f"错误: {len(result.errors)} 条")
        self._result_label.setText("  |  ".join(parts))

        if result.errors:
            self._error_list.setText("错误详情:\n" + "\n".join(result.errors[-10:]))
            self._error_list.show()
        else:
            self._error_list.hide()

        self._stack.setCurrentIndex(2)
