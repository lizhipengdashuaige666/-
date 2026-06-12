from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import OCRResult, OCRTextLine


class OCRTextCache:
    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def get(self, pdf_path: Path) -> OCRResult | None:
        record = self._data.get(self._key(pdf_path))
        if not isinstance(record, dict):
            return None
        if record.get("fingerprint") != self._fingerprint(pdf_path):
            return None

        line_records = record.get("lines", [])
        lines = [
            OCRTextLine(text=str(item.get("text", "")).strip(), score=item.get("score"))
            for item in line_records
            if isinstance(item, dict) and str(item.get("text", "")).strip()
        ]
        full_text = str(record.get("full_text", "")).strip() or "\n".join(line.text for line in lines)
        if not full_text:
            return None
        return OCRResult(lines=lines, full_text=full_text, raw={"source": "ocr_text_cache"})

    def remember(self, pdf_path: Path, result: OCRResult) -> None:
        if not result.full_text.strip():
            return
        self._data[self._key(pdf_path)] = {
            "fingerprint": self._fingerprint(pdf_path),
            "full_text": result.full_text,
            "lines": [
                {"text": line.text, "score": line.score}
                for line in result.lines
                if line.text.strip()
            ],
        }
        self._save()

    def _load(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {}
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        self.cache_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _key(self, pdf_path: Path) -> str:
        return str(pdf_path.resolve()).casefold()

    def _fingerprint(self, pdf_path: Path) -> dict[str, int]:
        stat = pdf_path.stat()
        return {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
