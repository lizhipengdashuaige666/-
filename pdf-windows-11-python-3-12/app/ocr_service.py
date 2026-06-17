from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from unified.ocr import get_engine

from app.models import OCRResult, OCRTextLine


class OCRServiceError(RuntimeError):
    """OCR 执行失败。"""


class PaddleOCRService:
    def __init__(self, lang: str = "ch") -> None:
        self.lang = lang
        self._engine: Any = None

    @property
    def engine(self) -> Any:
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    def _build_engine(self) -> Any:
        """获取共享的 PaddleOCR 引擎（移动端模型）。"""
        try:
            return get_engine()
        except ImportError as exc:
            raise OCRServiceError(
                "未安装 PaddleOCR。请先根据 README 安装 requirements.txt 中的依赖。"
            ) from exc

    def recognize(self, image: np.ndarray) -> OCRResult:
        """直接接收 numpy 数组 (H, W, 3) RGB。"""
        raw_result = None
        last_error: Exception | None = None

        try:
            raw_result = self.engine.predict(image)
        except Exception as exc:
            last_error = exc

        if raw_result is None:
            raise OCRServiceError(f"OCR 识别失败: {last_error}")

        lines = self._parse_result(raw_result)
        if not lines:
            raise OCRServiceError("OCR 未识别出可用文本。")

        full_text = "\n".join(line.text for line in lines if line.text.strip())
        return OCRResult(lines=lines, full_text=full_text, raw=raw_result)

    def _parse_result(self, raw_result: Any) -> list[OCRTextLine]:
        lines: list[OCRTextLine] = []
        items = raw_result if isinstance(raw_result, Iterable) and not isinstance(raw_result, (str, bytes, dict)) else [raw_result]

        for item in items:
            lines.extend(self._extract_lines_from_item(item))

        return [line for line in lines if line.text.strip()]

    def _extract_lines_from_item(self, item: Any) -> list[OCRTextLine]:
        data = self._unwrap_item(item)

        if isinstance(data, dict):
            texts = data.get("rec_texts")
            scores = data.get("rec_scores")
            if texts:
                return [
                    OCRTextLine(text=str(text).strip(), score=self._score_at(scores, index))
                    for index, text in enumerate(texts)
                    if str(text).strip()
                ]

            rec_text = data.get("rec_text")
            if rec_text:
                return [OCRTextLine(text=str(rec_text).strip(), score=self._safe_float(data.get("rec_score")))]

        if isinstance(data, list):
            return self._extract_from_legacy_list(data)

        return []

    def _unwrap_item(self, item: Any) -> Any:
        if hasattr(item, "res"):
            return getattr(item, "res")
        if isinstance(item, dict) and "res" in item:
            return item["res"]
        return item

    def _extract_from_legacy_list(self, data: list[Any]) -> list[OCRTextLine]:
        lines: list[OCRTextLine] = []

        for entry in data:
            if isinstance(entry, list) and entry and isinstance(entry[0], list):
                lines.extend(self._extract_from_legacy_list(entry))
                continue

            if (
                isinstance(entry, (list, tuple))
                and len(entry) >= 2
                and isinstance(entry[1], (list, tuple))
                and entry[1]
            ):
                text = str(entry[1][0]).strip()
                score = self._safe_float(entry[1][1] if len(entry[1]) > 1 else None)
                if text:
                    lines.append(OCRTextLine(text=text, score=score))

        return lines

    def _score_at(self, scores: Any, index: int) -> float | None:
        if scores is None:
            return None
        try:
            return self._safe_float(scores[index])
        except Exception:
            return None

    def _safe_float(self, value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None
