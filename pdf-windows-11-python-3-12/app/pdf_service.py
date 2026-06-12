from __future__ import annotations

from pathlib import Path

import fitz
import numpy as np


class PDFRenderError(RuntimeError):
    """PDF 渲染失败。"""


class PDFService:
    def __init__(self, dpi: int = 200) -> None:
        self.dpi = dpi

    def render_first_page(self, pdf_path: Path) -> np.ndarray:
        """渲染 PDF 首页为 numpy 数组 (H, W, 3) RGB 格式，直接供 OCR 使用。"""
        try:
            with fitz.open(pdf_path) as document:
                if document.page_count == 0:
                    raise PDFRenderError("PDF 没有可读取的页面。")

                page = document.load_page(0)
                pixmap = page.get_pixmap(dpi=self.dpi, alpha=False)
                # 直接从 fitz Pixmap 构造 numpy 数组，避免 PIL 中间层
                arr = np.frombuffer(pixmap.samples, dtype=np.uint8)
                arr = arr.reshape(pixmap.height, pixmap.width, pixmap.n)
                return np.ascontiguousarray(arr)
        except PDFRenderError:
            raise
        except Exception as exc:
            raise PDFRenderError(f"首页渲染失败: {exc}") from exc
