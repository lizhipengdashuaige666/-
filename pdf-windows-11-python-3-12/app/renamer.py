from __future__ import annotations

import shutil
import re
from pathlib import Path


class FileRenamer:
    ILLEGAL_CHAR_PATTERN = re.compile(r'[\\/:*?"<>|]+')

    # Mode A: 双章合同 —— {vendor_short}双章合同{contract_no}.pdf
    CURRENT_NAMED_PATTERN = re.compile(
        r'^([^\\/:*?"<>|]+?)双章合同([A-Za-z]{1,8}\d[\w.\-]*)(?:\(\d+\))?\.pdf$',
        re.IGNORECASE,
    )

    # Mode B: PO 订单 —— {vendor_short}{contract_no}.pdf
    PO_NAMED_PATTERN = re.compile(
        r'^([^\\/:*?"<>|]+?)([A-Za-z]{1,8}\d[\w.\-]*)(?:\(\d+\))?\.pdf$',
        re.IGNORECASE,
    )

    LEGACY_NAMED_PATTERNS = [
        re.compile(
            r'^(.+?)_?([A-Za-z]{1,8}\d[\w.\-]*)_双章合同(?:\(\d+\))?\.pdf$',
            re.IGNORECASE,
        ),
        re.compile(
            r'^(.+?)_?([A-Za-z]{1,8}\d[\w.\-]*)(?:\(\d+\))?\.pdf$',
            re.IGNORECASE,
        ),
    ]

    def scan_pdfs(self, directory: Path, recursive: bool = False) -> list[Path]:
        pattern = "**/*.pdf" if recursive else "*.pdf"
        return sorted(path for path in directory.glob(pattern) if path.is_file())

    def parse_named_filename(self, file_name: str) -> tuple[str, str] | None:
        for pattern in [self.CURRENT_NAMED_PATTERN, self.PO_NAMED_PATTERN, *self.LEGACY_NAMED_PATTERNS]:
            match = pattern.match(file_name)
            if match:
                return match.group(1), match.group(2).upper()
        return None

    def is_already_named(self, file_name: str) -> bool:
        return bool(self.CURRENT_NAMED_PATTERN.match(file_name))

    def is_po_named(self, file_name: str) -> bool:
        return bool(self.PO_NAMED_PATTERN.match(file_name))

    def is_legacy_named(self, file_name: str) -> bool:
        return any(pattern.match(file_name) for pattern in self.LEGACY_NAMED_PATTERNS)

    def is_any_named(self, file_name: str) -> bool:
        return self.parse_named_filename(file_name) is not None

    # ------------------------------------------------------------------
    # 命名模板
    # ------------------------------------------------------------------
    def build_filename(
        self,
        vendor_short_name: str,
        contract_no: str,
        naming_mode: str = "dual_chop",
        suffix: str = ".pdf",
    ) -> str:
        """
        naming_mode:
          "dual_chop" → 里博双章合同PO20260527007.pdf
          "po_order"  → 里博PO20260527007.pdf
        """
        vendor = self.sanitize_part(vendor_short_name)
        contract = self.sanitize_part(contract_no)
        final_suffix = suffix if suffix.lower().startswith(".") else ".pdf"

        if naming_mode == "po_order":
            return f"{vendor}{contract}{final_suffix.lower()}"
        # 默认 dual_chop
        return f"{vendor}双章合同{contract}{final_suffix.lower()}"

    def sanitize_part(self, value: str) -> str:
        sanitized = self.ILLEGAL_CHAR_PATTERN.sub("_", value.strip())
        sanitized = re.sub(r"\s+", "", sanitized)
        sanitized = re.sub(r"_+", "_", sanitized)
        sanitized = sanitized.strip("._-")
        return sanitized

    def sanitize_filename(self, value: str) -> str:
        if not value.lower().endswith(".pdf"):
            value = f"{value}.pdf"

        stem = Path(value).stem
        suffix = Path(value).suffix.lower() or ".pdf"
        sanitized_stem = self.sanitize_part(stem)
        sanitized_stem = sanitized_stem or "未命名合同"
        return f"{sanitized_stem}{suffix}"

    def ensure_unique_path(self, source_path: Path, desired_name: str) -> Path:
        sanitized_name = self.sanitize_filename(desired_name)
        candidate = source_path.with_name(sanitized_name)
        if candidate == source_path or not candidate.exists():
            return candidate

        stem = candidate.stem
        suffix = candidate.suffix
        index = 1
        while True:
            next_candidate = source_path.with_name(f"{stem}({index}){suffix}")
            if next_candidate == source_path or not next_candidate.exists():
                return next_candidate
            index += 1

    def rename_file(self, source_path: Path, desired_name: str) -> Path:
        target_path = self.ensure_unique_path(source_path, desired_name)
        if target_path == source_path:
            return source_path
        return source_path.rename(target_path)

    def move_to_output(self, source_path: Path, output_dir: Path) -> Path:
        """将已命名的文件移动到输出目录，重名时自动添加序号后缀。"""
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / source_path.name
        if not target.exists():
            return Path(shutil.move(str(source_path), str(target)))

        stem = target.stem
        suffix = target.suffix
        index = 1
        while True:
            candidate = output_dir / f"{stem}({index}){suffix}"
            if not candidate.exists():
                return Path(shutil.move(str(source_path), str(candidate)))
            index += 1
