"""Shared PaddleOCR engine — PP-OCRv5 mobile models, single singleton.

Usage:
    from unified.ocr import get_engine, ocr_text_from_image, ocr_text_from_pdf

    engine = get_engine()              # PaddleOCR instance (lazy, call once)
    text = ocr_text_from_image(arr)    # numpy (H,W,3) RGB → text
    text = ocr_text_from_pdf(path)     # PDF path → text
"""

from __future__ import annotations

import os

# ── Must be set before paddle import ──
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

import json
from typing import Any

_PADDLE_OCR: Any = None


def get_engine() -> Any:
    """Return the singleton PaddleOCR instance (mobile models, tuned for CPU)."""
    global _PADDLE_OCR
    if _PADDLE_OCR is None:
        from paddleocr import PaddleOCR
        _PADDLE_OCR = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,

            text_detection_model_name="PP-OCRv5_mobile_det",
            text_det_limit_side_len=960,
            text_det_limit_type="min",
            text_det_thresh=0.3,

            text_recognition_model_name="PP-OCRv5_mobile_rec",

            text_rec_score_thresh=0.3,
        )
    return _PADDLE_OCR


def _extract_text_from_result(result: Any) -> str:
    """Pull rec_texts out of a PaddleOCR predict() result."""
    texts: list[str] = []
    for page in result:
        d = page.json
        if isinstance(d, str):
            d = json.loads(d)
        res = d.get("res", d)
        for t, s in zip(res.get("rec_texts", []), res.get("rec_scores", [])):
            t2 = str(t).strip()
            if t2 and (s is None or s > 0.1):
                texts.append(t2)
        if not texts and res.get("rec_text", ""):
            texts.append(str(res["rec_text"]).strip())
    return "\n".join(texts)


def ocr_text_from_image(image: "np.ndarray") -> str:  # type: ignore[name-defined]
    """OCR a numpy image (H, W, 3) RGB. Returns concatenated text."""
    engine = get_engine()
    result = engine.predict(image)
    if result is None:
        raise RuntimeError("PaddleOCR predict returned None")
    text = _extract_text_from_result(result)
    if not text.strip():
        raise RuntimeError("OCR did not find any text in image")
    return text


def ocr_text_from_pdf(pdf_path: str) -> str:
    """OCR all pages of a PDF via PaddleOCR's built-in PDF reader. Returns text."""
    engine = get_engine()
    result = engine.predict(str(pdf_path))
    if result is None:
        raise RuntimeError("PaddleOCR predict returned None")
    text = _extract_text_from_result(result)
    if not text.strip():
        raise RuntimeError("OCR did not find any text in PDF")
    return text
