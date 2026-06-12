from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    source_path: Path
    target_path: Path
    moved: bool


class SendPlatformBridge:
    def __init__(self, enabled: bool, inbox_dir: Path) -> None:
        self.enabled = enabled
        self.inbox_dir = inbox_dir

    def deliver(self, pdf_path: Path) -> DeliveryResult:
        if not self.enabled:
            return DeliveryResult(source_path=pdf_path, target_path=pdf_path, moved=False)

        if not pdf_path.exists():
            raise FileNotFoundError(f"文件不存在，无法移动到发送平台: {pdf_path}")

        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._unique_target(pdf_path.name)

        if pdf_path.resolve() == target_path.resolve():
            return DeliveryResult(source_path=pdf_path, target_path=pdf_path, moved=False)

        moved_path = Path(shutil.move(str(pdf_path), str(target_path)))
        return DeliveryResult(source_path=pdf_path, target_path=moved_path, moved=True)

    def describe(self, result: DeliveryResult) -> str:
        if not self.enabled:
            return ""
        if result.moved:
            return f"已移动到发送平台: {result.target_path}"
        return f"已在发送平台目录: {result.target_path}"

    def _unique_target(self, file_name: str) -> Path:
        candidate = self.inbox_dir / file_name
        if not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        index = 1
        while True:
            next_candidate = self.inbox_dir / f"{stem}({index}){suffix}"
            if not next_candidate.exists():
                return next_candidate
            index += 1
