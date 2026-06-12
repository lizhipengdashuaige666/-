from __future__ import annotations

from pathlib import Path
import traceback

from app.config import load_config
from app.extractor import ContractExtractor
from app.logger_service import RenameLogger
from app.models import LogEntry, OCRResult, OCRTextLine
from app.ocr_cache import OCRTextCache
from app.ocr_service import PaddleOCRService
from app.pdf_service import PDFService
from app.renamer import FileRenamer
from app.vendor_cache import VendorCache


REPORT_PATH = Path("repair_shenzhen_names_report.txt")
BAD_PREFIXES = ("深圳", "苏州", "广东", "合同")


def flush(lines: list[str]) -> None:
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def build_cached_name_map(
    ocr_cache: OCRTextCache,
    extractor: ContractExtractor,
    renamer: FileRenamer,
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for record in ocr_cache._data.values():
        if not isinstance(record, dict):
            continue
        lines = [
            OCRTextLine(text=str(item.get("text", "")), score=item.get("score"))
            for item in record.get("lines", [])
            if isinstance(item, dict)
        ]
        result = OCRResult(lines=lines, full_text=str(record.get("full_text", "")), raw=None)
        extraction = extractor.extract(result)
        if extraction.is_valid:
            mapping[extraction.contract_no or ""] = renamer.build_filename(
                extraction.vendor_short_name or "",
                extraction.contract_no or "",
            )
    return mapping


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    config = load_config(base_dir)
    extractor = ContractExtractor()
    renamer = FileRenamer()
    pdf_service = PDFService(dpi=config.render_dpi)
    ocr_cache = OCRTextCache(config.ocr_text_cache_path)
    vendor_cache = VendorCache(config.vendor_cache_path)
    logger = RenameLogger(config.log_dir / "rename_log.csv")
    ocr_service: PaddleOCRService | None = None

    cached_names = build_cached_name_map(ocr_cache, extractor, renamer)
    targets: list[Path] = []
    for prefix in BAD_PREFIXES:
        targets.extend(config.pdf_dir.glob(f"{prefix}双章合同*.pdf"))
    targets = sorted(set(targets))

    lines = [f"TOTAL={len(targets)}", f"PDF_DIR={config.pdf_dir}"]
    flush(lines)

    for pdf_path in targets:
        try:
            parsed = renamer.parse_named_filename(pdf_path.name)
            contract_no = parsed[1] if parsed else ""
            desired_name = cached_names.get(contract_no)

            if not desired_name:
                ocr_result = ocr_cache.get(pdf_path)
                if ocr_result is None:
                    if ocr_service is None:
                        ocr_service = PaddleOCRService(lang=config.ocr_lang)
                    image = pdf_service.render_first_page(pdf_path)
                    ocr_result = ocr_service.recognize(image)
                    ocr_cache.remember(pdf_path, ocr_result)

                extraction = extractor.extract(ocr_result)
                if not extraction.is_valid:
                    reason = extraction.reason or "OCR 结果无法提取关键字段"
                    lines.append(f"SKIP|{pdf_path.name}|{reason}")
                    flush(lines)
                    continue
                desired_name = renamer.build_filename(
                    extraction.vendor_short_name or "",
                    extraction.contract_no or "",
                    suffix=pdf_path.suffix,
                )
                vendor_cache.remember(extraction.vendor_name, extraction.vendor_short_name)

            if desired_name == pdf_path.name:
                lines.append(f"OK|{pdf_path.name}|无需修复")
                flush(lines)
                continue

            final_path = renamer.rename_file(pdf_path, desired_name)
            logger.write(
                LogEntry(
                    original_name=pdf_path.name,
                    new_name=final_path.name,
                    status="成功",
                    error_reason="修复错误简称：城市词/合同词",
                )
            )
            lines.append(f"FIXED|{pdf_path.name}|{final_path.name}")
            flush(lines)
        except Exception as exc:
            lines.append(f"FAIL|{pdf_path.name}|{exc}")
            lines.append(traceback.format_exc())
            flush(lines)


if __name__ == "__main__":
    main()
