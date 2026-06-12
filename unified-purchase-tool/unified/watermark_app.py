#!/usr/bin/env python3
"""水单自动识别与记账工具 — PySide6 版本。

支持文本型/扫描件 PDF，多笔汇款记录批量提取，结果追加写入 已付款.xlsx。
"""

from __future__ import annotations

import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pdfplumber
from openpyxl import Workbook, load_workbook
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from unified import style as _style

try:
    import pypdfium2 as pdfium
    import pytesseract
    from PIL import Image, ImageEnhance
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

_EXCEL_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, 'frozen', False) else __file__))
DEFAULT_EXCEL_PATH = os.path.join(_EXCEL_DIR, "已付款.xlsx")


# ═══════════════════════════════════════════════════════════════════════════
# Business logic (unchanged)
# ═══════════════════════════════════════════════════════════════════════════

def _ocr_page(page, scale=5):
    bitmap = page.render(scale=scale)
    img = bitmap.to_pil().convert("L")
    enhancer = ImageEnhance.Contrast(img)
    return enhancer.enhance(2.0)


def _ocr_text_from_pdf(pdf_path):
    if not OCR_AVAILABLE:
        raise RuntimeError("OCR 依赖未安装（pypdfium2, pytesseract, Pillow）")
    pdf = pdfium.PdfDocument(pdf_path)
    parts = [_ocr_page(pdf[i]) for i in range(len(pdf))]
    return "\n".join(pytesseract.image_to_string(p, lang="chi_sim+eng", config="--psm 4")
                     for p in parts)


def _extract_supplier_from_segment(segment, payer_accounts):
    supplier = None
    payee_account = None
    acct_matches = list(re.finditer(r'(?<!\d)(\d{8,25})(?!\d)', segment))
    candidates = []
    for m in acct_matches:
        a = m.group(1)
        if a in payer_accounts or len(a) == 8:
            continue
        if len(a) >= 16 and re.match(r'20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d+', a):
            continue
        candidates.append((m.start(), a))
    if not candidates:
        return None, None
    acct_pos, payee_account = candidates[-1]
    tail = segment[acct_pos + len(payee_account):]
    cleaned = re.sub(r'^[\sA-Za-z\[\]:：,.·\-_]{1,20}(?=[一-鿿]|[A-Z][a-z]{2,})', '', tail)
    cn_text = re.findall(r'[一-鿿A-Za-z0-9]{2,}', cleaned[:80])
    if cn_text:
        raw = cn_text[0][:30].strip()
        raw = re.sub(r'[a-zA-Z\[\]]+$', '', raw).strip()
        if len(raw) >= 2:
            supplier = raw
    return supplier, payee_account


def _clean_amount(raw, fix_map=None):
    s = re.sub(r"\s+", "", raw).replace(",", "")
    try:
        return float(s)
    except ValueError:
        pass
    default_fixes = {"O": "0", "S": "5", "Z": "2", "l": "1", "B": "8"}
    for i_val in ["9", "1"]:
        m = dict(default_fixes, I=i_val, i=i_val)
        fixed = s
        for k, v in m.items():
            fixed = fixed.replace(k, v)
        try:
            return float(fixed)
        except ValueError:
            continue
    raise ValueError(f"无法解析金额: {raw}")


def _extract_records_from_text(text, pdf_path):
    records = []
    text = re.sub(r"\s+", " ", text)
    amount_pattern = re.compile(r"[+＋]?\s*CNY\s*([\d,\sIOloSZBi]+\.\s?\d{2})", re.IGNORECASE)
    amounts = list(amount_pattern.finditer(text))
    if not amounts:
        return records

    payer_accounts = set()
    for m in re.finditer(r"(?:ATR?U?[KkB]S?\s*[:-]?\s*)(\d{8,})", text):
        payer_accounts.add(m.group(1))
    m_fn = re.search(r"(\d{10,})", os.path.basename(pdf_path))
    if m_fn:
        payer_accounts.add(m_fn.group(1))

    global_date = datetime.today().strftime("%Y-%m-%d")
    for dm in re.finditer(r"(\d{4}[/-]\d{2}[/-]\d{2})", text):
        try:
            global_date = dm.group(1).replace("/", "-")
            break
        except Exception:
            pass

    amount_positions = [0] + [am.end() for am in amounts]
    for i, am in enumerate(amounts):
        try:
            amount = _clean_amount(am.group(1))
        except ValueError:
            continue
        seg_start = amount_positions[i]
        seg_end = am.start()
        segment = text[seg_start:seg_end]
        supplier, payee_account = _extract_supplier_from_segment(segment, payer_accounts)
        if not supplier:
            before = text[max(0, am.start() - 600):am.start()]
            supplier, payee_account = _extract_supplier_from_segment(before, payer_accounts)
        rec_date = None
        for dm in re.finditer(r"(\d{4}[/-]\d{2}[/-]\d{2})", segment):
            try:
                rec_date = dm.group(1).replace("/", "-")
                break
            except Exception:
                pass
        if not rec_date:
            rec_date = global_date
        after_start = am.end()
        after_end = amounts[i + 1].start() if i + 1 < len(amounts) else len(text)
        after_segment = text[after_start:after_end]
        txn_id = None
        m_txn = re.search(r"(\d{8}\d{10,})", after_segment)
        if m_txn:
            raw_txn = m_txn.group(1)
            try:
                y, mth, d = int(raw_txn[:4]), int(raw_txn[4:6]), int(raw_txn[6:8])
                if 2020 <= y <= 2030 and 1 <= mth <= 12 and 1 <= d <= 31:
                    txn_id = raw_txn
            except Exception:
                txn_id = raw_txn
        if not supplier and payee_account:
            supplier = f"(收款账号 {payee_account[-6:]})"
        records.append({
            "amount": amount, "supplier": supplier,
            "payee_account": payee_account, "date": rec_date,
            "txn_id": txn_id,
        })
    return records


def extract_info_from_pdf(pdf_path):
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
    except Exception:
        text_parts = []
    if text_parts:
        full_text = "\n".join(text_parts)
    elif OCR_AVAILABLE:
        try:
            full_text = _ocr_text_from_pdf(pdf_path)
        except Exception as e:
            raise RuntimeError(f"OCR识别失败: {e}")
    else:
        raise RuntimeError("该PDF为扫描件且OCR依赖未安装，无法识别。")
    if not full_text.strip():
        raise RuntimeError("PDF内容为空，无法提取信息。")
    return _extract_records_from_text(full_text, pdf_path)


def append_to_excel(records, excel_path=None):
    if excel_path is None:
        excel_path = DEFAULT_EXCEL_PATH
    headers = ["识别日期", "付款日期", "供应商", "收款账号", "付款金额", "源文件名", "交易流水号"]
    today = datetime.today().strftime("%Y-%m-%d")
    if not os.path.exists(excel_path):
        wb = Workbook()
        ws = wb.active
        ws.title = "已付款"
        ws.append(headers)
    else:
        wb = load_workbook(excel_path)
        if "已付款" in wb.sheetnames:
            ws = wb["已付款"]
            existing = [cell.value for cell in ws[1]]
            if existing != headers:
                for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
                    missing = len(headers) - len(row)
                    for _ in range(missing):
                        row[-1].offset(column=1).value = None
                for i, h in enumerate(headers, 1):
                    ws.cell(row=1, column=i, value=h)
        else:
            ws = wb.create_sheet("已付款")
            ws.append(headers)
    for rec in records:
        ws.append([
            today, rec.get("date") or "未识别",
            rec.get("supplier") or "未识别", rec.get("payee_account") or "",
            f"{rec['amount']:.2f}" if rec.get("amount") is not None else "未识别",
            rec.get("filename", ""), rec.get("txn_id") or "",
        ])
    for col_cells in ws.columns:
        max_len = 0
        col_letter = col_cells[0].column_letter
        for cell in col_cells:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 4, 50)
    wb.save(excel_path)


# ═══════════════════════════════════════════════════════════════════════════
# PySide6 GUI
# ═══════════════════════════════════════════════════════════════════════════

class WatermarkApp(QWidget):
    def __init__(self, parent: QWidget | None = None,
                 shell: object | None = None) -> None:
        super().__init__(parent)
        self._shell = shell
        self.setObjectName("watermarkRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAcceptDrops(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QLabel("水单自动识别")
        header.setObjectName("toolbarTitle")
        subtitle = QLabel("将银行付款水单 PDF 拖入窗口自动识别汇款记录\n"
                          "支持文本型 PDF 及扫描件 OCR | 每份 PDF 提取全部汇款记录")
        subtitle.setObjectName("toolbarSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # File list
        list_card = QFrame()
        list_card.setObjectName("card")
        lc = QVBoxLayout(list_card)
        lc.setContentsMargins(14, 14, 14, 14)
        lc.setSpacing(8)

        list_header = QHBoxLayout()
        label = QLabel("待处理 PDF 列表")
        label.setObjectName("cardTitle")
        count_label = QLabel("")
        count_label.setObjectName("sideSubtitle")
        self._count_label = count_label
        list_header.addWidget(label)
        list_header.addStretch()
        list_header.addWidget(count_label)
        lc.addLayout(list_header)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        remove_action = QAction("移除选中项", self.file_list)
        remove_action.triggered.connect(self._remove_selected)
        self.file_list.addAction(remove_action)
        lc.addWidget(self.file_list, 1)

        layout.addWidget(list_card, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        select_btn = QPushButton("选择文件")
        select_btn.setObjectName("secondaryBtn")
        select_btn.clicked.connect(self._select_files)

        start_btn = QPushButton("开始识别")
        start_btn.setObjectName("primaryBtn")
        start_btn.clicked.connect(self._process_files)

        clear_btn = QPushButton("清空列表")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self.clear_list)

        btn_row.addWidget(select_btn)
        btn_row.addWidget(start_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Status
        self._status = QLabel("就绪")
        self._status.setObjectName("sideSubtitle")
        layout.addWidget(self._status)

    def _select_files(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择水单PDF", "",
            "PDF文件 (*.pdf);;所有文件 (*.*)")
        self._add_files(paths)

    def add_paths(self, paths: list[Path]) -> None:
        self._add_files([str(p) for p in paths])

    def _add_files(self, paths: list[str]) -> None:
        new = 0
        for p in paths:
            p = os.path.normpath(p)
            if p and p not in {self.file_list.item(i).data(Qt.ItemDataRole.UserRole)
                               for i in range(self.file_list.count())}:
                item = QListWidgetItem(os.path.basename(p))
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.file_list.addItem(item)
                new += 1
        self._refresh_count()

    def clear_list(self) -> None:
        self.file_list.clear()
        self._refresh_count()

    def _remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self._refresh_count()

    def _refresh_count(self) -> None:
        c = self.file_list.count()
        self._count_label.setText(f"共 {c} 个文件" if c else "")

    def _process_files(self) -> None:
        if self.file_list.count() == 0:
            QMessageBox.information(self, "提示", "请先添加 PDF 文件。")
            return

        self._status.setText("正在识别...")
        self.setCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()

        files = [(self.file_list.item(i).data(Qt.ItemDataRole.UserRole), i)
                 for i in range(self.file_list.count())]
        all_records = []
        errors = []

        for path, _ in files:
            fname = os.path.basename(path)
            try:
                records = extract_info_from_pdf(path)
                for rec in records:
                    rec["filename"] = fname
                all_records.extend(records)
                if not records:
                    errors.append(f"{fname} — 未提取到任何记录")
            except Exception:
                errors.append(f"{fname} — "
                              f"{traceback.format_exc().strip().split(chr(10))[-1]}")

        if all_records:
            try:
                append_to_excel(all_records)
            except Exception:
                errors.append(f"Excel写入失败: "
                              f"{traceback.format_exc().strip().split(chr(10))[-1]}")

        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.clear_list()

        summary = f"成功写入 {len(all_records)} 条记录到 已付款.xlsx"
        if errors:
            detail = "\n".join(errors[-8:])
            summary += f"\n\n{len(errors)} 个问题:\n{detail}"
        self._status.setText(summary.split("\n")[0])
        QMessageBox.information(self, "完成", summary)

    # Drag & drop
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()]
        pdfs = [str(p) for p in paths if p.suffix.lower() == ".pdf"]
        if pdfs:
            self._add_files(pdfs)
