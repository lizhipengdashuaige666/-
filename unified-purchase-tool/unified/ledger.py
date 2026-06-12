"""Shared Excel ledger writer — single source of truth for 已发台账.xlsx."""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import openpyxl

LEDGER_PATH = Path(r"D:\采购工作\采购订单\已发\已发台账.xlsx")
HEADERS = ["供应商", "订单号", "文件名称", "类型", "单章合同", "双章合同", "发送日期"]


def _ensure_workbook(excel_path: Path):
    """Return (workbook, worksheet) with headers guaranteed."""
    if excel_path.exists() and excel_path.stat().st_size > 1000:
        wb = openpyxl.load_workbook(str(excel_path))
        ws = wb.active
        if ws is None:
            ws = wb.create_sheet("台账")
        for i, h in enumerate(HEADERS, 1):
            existing = ws.cell(row=1, column=i).value
            if existing != h:
                ws.cell(row=1, column=i, value=h)
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "台账"
        for i, h in enumerate(HEADERS, 1):
            ws.cell(row=1, column=i, value=h)
    return wb, ws


def append_row(supplier: str, number: str, filename: str,
               business_type: str, date_str: str | None = None,
               excel_path: Path | None = None) -> bool:
    """Append one row to the ledger. Returns True on success."""
    if excel_path is None:
        excel_path = LEDGER_PATH
    try:
        wb, ws = _ensure_workbook(excel_path)
        row_num = ws.max_row + 1
        today = date_str or datetime.now().strftime("%Y-%m-%d")
        ws.cell(row=row_num, column=1, value=supplier)
        ws.cell(row=row_num, column=2, value=number)
        ws.cell(row=row_num, column=3, value=filename)
        ws.cell(row=row_num, column=4, value=business_type)
        ws.cell(row=row_num, column=5, value="是")
        ws.cell(row=row_num, column=6, value="是")
        ws.cell(row=row_num, column=7, value=today)

        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        tmp.close()
        wb.save(tmp.name)
        shutil.copy2(tmp.name, str(excel_path))
        os.unlink(tmp.name)
        return True
    except PermissionError:
        return False
    except Exception:
        return False
