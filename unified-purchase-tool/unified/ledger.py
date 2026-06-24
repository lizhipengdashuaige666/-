"""Shared Excel ledger writer — single source of truth for 已发台账.xlsx.

通过 Excel COM 接口读写，避开加密软件的文件锁。
"""

import time
import ctypes
from datetime import datetime
from pathlib import Path

LEDGER_PATH = Path(r"D:\采购工作\采购订单\已发\已发台账.xlsx")
HEADERS = ["供应商", "订单号", "文件名称", "类型", "单章合同", "双章合同", "发送日期"]


def _get_excel():
    """Return a running or new Excel Application object."""
    import win32com.client
    try:
        return win32com.client.GetActiveObject("Excel.Application")
    except Exception:
        return win32com.client.Dispatch("Excel.Application")


def _find_or_open_workbook(xl, excel_path: Path):
    """Find workbook if already open in Excel, otherwise open it."""
    target = excel_path.name
    try:
        for wb in xl.Workbooks:
            if wb.Name == target:
                return wb
    except Exception:
        pass
    return xl.Workbooks.Open(str(excel_path))


def append_row(supplier: str, number: str, filename: str,
               business_type: str, date_str: str | None = None,
               excel_path: Path | None = None) -> bool:
    """Append one row via COM — works through encryption. 文件被占用时弹窗等用户。"""
    if excel_path is None:
        excel_path = LEDGER_PATH

    today = date_str or datetime.now().strftime("%Y-%m-%d")

    while True:
        xl = None
        wb = None
        try:
            xl = _get_excel()
            wb = _find_or_open_workbook(xl, excel_path)
            ws = wb.Worksheets(1)

            # Ensure headers
            for i, h in enumerate(HEADERS, 1):
                existing = ws.Cells(1, i).Value
                if existing != h:
                    ws.Cells(1, i).Value = h

            # Find first empty row
            row = 2
            while ws.Cells(row, 1).Value is not None:
                row += 1

            ws.Cells(row, 1).Value = supplier
            ws.Cells(row, 2).Value = number
            ws.Cells(row, 3).Value = filename
            ws.Cells(row, 4).Value = business_type
            ws.Cells(row, 5).Value = "是"
            ws.Cells(row, 6).Value = "是"
            ws.Cells(row, 7).Value = today

            wb.Save()
            return True
        except Exception:
            # 文件被占用或打开失败 → 弹窗等用户关闭 Excel
            if wb:
                try:
                    wb.Close(False)
                except Exception:
                    pass
            if xl:
                try:
                    xl.Quit()
                except Exception:
                    pass
            result = ctypes.windll.user32.MessageBoxW(
                0,
                "台账需要记录，请保存并关闭 Excel 中的台账文件，\n然后点「确定」继续。\n点「取消」则跳过本次记录。",
                "台账写入",
                0x00040001 | 0x00000030 | 0x00000100,  # MB_OKCANCEL | MB_ICONWARNING | MB_TOPMOST
            )
            if result != 1:
                return False
            time.sleep(0.3)
