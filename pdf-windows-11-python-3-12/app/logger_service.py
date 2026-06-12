from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from app.models import LogEntry


class RenameLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def _ensure_header(self) -> None:
        if self.log_path.exists():
            return

        with self.log_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["timestamp", "original_name", "new_name", "status", "error_reason"],
            )
            writer.writeheader()

    def write(self, entry: LogEntry) -> None:
        with self.log_path.open("a", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["timestamp", "original_name", "new_name", "status", "error_reason"],
            )
            writer.writerow(
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "original_name": entry.original_name,
                    "new_name": entry.new_name,
                    "status": entry.status,
                    "error_reason": entry.error_reason,
                }
            )
