from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class OCRTextLine:
    text: str
    score: float | None = None


@dataclass(slots=True)
class OCRResult:
    lines: list[OCRTextLine]
    full_text: str
    raw: Any = None


@dataclass(slots=True)
class ExtractionResult:
    vendor_name: str | None = None
    vendor_short_name: str | None = None
    contract_no: str | None = None
    reason: str | None = None

    @property
    def is_valid(self) -> bool:
        return bool(self.vendor_short_name and self.contract_no)


@dataclass(slots=True)
class PendingRename:
    original_path: Path
    original_name: str
    ocr_text: str
    extraction: ExtractionResult
    suggested_name: str


@dataclass(slots=True)
class LogEntry:
    original_name: str
    new_name: str
    status: str
    error_reason: str = ""


@dataclass(slots=True)
class BatchSummary:
    total: int = 0
    success: int = 0
    skipped: int = 0
    failed: int = 0
    reviewed: int = 0
    recent_messages: list[str] = field(default_factory=list)

    def add_message(self, message: str) -> None:
        self.recent_messages.append(message)
        if len(self.recent_messages) > 20:
            self.recent_messages = self.recent_messages[-20:]
