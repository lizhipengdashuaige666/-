from __future__ import annotations

import csv
from pathlib import Path
import traceback

from app.config import load_config
from app.extractor import ContractExtractor
from app.logger_service import RenameLogger
from app.models import LogEntry
from app.ocr_cache import OCRTextCache
from app.ocr_service import PaddleOCRService
from app.pdf_service import PDFRenderError, PDFService
from app.renamer import FileRenamer
from app.send_platform import SendPlatformBridge
from app.vendor_cache import VendorCache


REPORT_PATH = Path("batch_run_report.txt")


def flush_report(report_lines: list[str]) -> None:
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")


def normalize_named_files(
    extractor: ContractExtractor,
    renamer: FileRenamer,
    vendor_cache: VendorCache,
    pdf_dir: Path,
    naming_mode: str,
    report_lines: list[str],
) -> int:
    changed = 0
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        parsed = renamer.parse_named_filename(pdf_path.name)
        if not parsed:
            continue

        vendor_name, contract_no = parsed
        vendor_short = extractor.abbreviate_company_name(vendor_name)
        if not vendor_short:
            report_lines.append(f"SKIP_NORMALIZE|{pdf_path.name}|供应商简称为空或疑似需方公司")
            continue

        vendor_cache.remember(vendor_name, vendor_short)
        desired_name = renamer.build_filename(vendor_short, contract_no, naming_mode=naming_mode, suffix=pdf_path.suffix)
        target_path = renamer.ensure_unique_path(pdf_path, desired_name)
        if target_path.name == pdf_path.name:
            continue

        try:
            final_path = pdf_path.rename(target_path)
        except PermissionError as exc:
            report_lines.append(f"SKIP_NORMALIZE|{pdf_path.name}|文件可能正在被打开或预览: {exc}")
            continue

        changed += 1
        report_lines.append(f"NORMALIZED|{pdf_path.name}|{final_path.name}")

    return changed


def seed_cache_from_log(
    extractor: ContractExtractor,
    renamer: FileRenamer,
    vendor_cache: VendorCache,
    log_path: Path,
    report_lines: list[str],
) -> int:
    if not log_path.exists():
        return 0

    added = 0
    with log_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            new_name = row.get("new_name", "")
            parsed = renamer.parse_named_filename(new_name)
            if not parsed:
                continue

            vendor_name, _contract_no = parsed
            vendor_short = extractor.abbreviate_company_name(vendor_name)
            if not vendor_short:
                continue

            vendor_cache.remember(vendor_name, vendor_short)
            added += 1

    if added:
        report_lines.append(f"CACHE_FROM_LOG={added}")
    return added


def deliver_to_send_platform(
    bridge: SendPlatformBridge,
    pdf_path: Path,
) -> tuple[Path, str]:
    delivery = bridge.deliver(pdf_path)
    return delivery.target_path, bridge.describe(delivery)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    config = load_config(base_dir)
    naming_mode = config.naming_mode

    renamer = FileRenamer()
    logger = RenameLogger(config.log_dir / "rename_log.csv")
    pdf_service = PDFService(dpi=config.render_dpi)
    ocr_service: PaddleOCRService | None = None
    extractor = ContractExtractor()
    vendor_cache = VendorCache(config.vendor_cache_path)
    ocr_cache = OCRTextCache(config.ocr_text_cache_path)
    send_bridge = SendPlatformBridge(
        enabled=config.send_platform_enabled,
        inbox_dir=config.send_platform_inbox_dir,
    )

    report_lines: list[str] = [
        f"PDF_DIR={config.pdf_dir}",
        f"RENDER_DPI={config.render_dpi}",
        f"NAMING_MODE={naming_mode}",
        f"OCR_TEXT_CACHE={config.ocr_text_cache_path}",
        f"SEND_PLATFORM_ENABLED={config.send_platform_enabled}",
        f"SEND_PLATFORM_INBOX={config.send_platform_inbox_dir}",
    ]
    seed_cache_from_log(extractor, renamer, vendor_cache, config.log_dir / "rename_log.csv", report_lines)
    normalized = normalize_named_files(extractor, renamer, vendor_cache, config.pdf_dir, naming_mode, report_lines)
    pdf_files = renamer.scan_pdfs(config.pdf_dir, recursive=config.recursive_scan)

    success = 0
    skipped = 0
    failed = 0

    report_lines.append(f"NORMALIZED={normalized}")
    report_lines.append(f"TOTAL={len(pdf_files)}")
    flush_report(report_lines)

    for pdf_path in pdf_files:
        try:
            if renamer.is_already_named(pdf_path.name):
                parsed = renamer.parse_named_filename(pdf_path.name)
                if parsed:
                    vendor_cache.remember(parsed[0], extractor.abbreviate_company_name(parsed[0]))

                try:
                    delivered_path, delivery_note = deliver_to_send_platform(send_bridge, pdf_path)
                except Exception as exc:
                    failed += 1
                    logger.write(LogEntry(
                        original_name=pdf_path.name, new_name=pdf_path.name,
                        status="失败", error_reason=f"文件已命名，但移动到发送平台失败: {exc}",
                    ))
                    report_lines.append(f"FAIL_DELIVER|{pdf_path.name}|{exc}")
                    flush_report(report_lines)
                    continue

                if send_bridge.enabled:
                    success += 1
                    status = "成功"
                    error_reason = delivery_note
                    report_lines.append(f"DELIVERED|{pdf_path.name}|{delivered_path}")
                else:
                    try:
                        moved_path = renamer.move_to_output(pdf_path, config.output_dir)
                        success += 1
                        status = "成功"
                        error_reason = f"已移动到输出目录: {moved_path}"
                        report_lines.append(f"MOVED|{pdf_path.name}|{moved_path.name}")
                    except Exception as exc:
                        failed += 1
                        logger.write(LogEntry(
                            original_name=pdf_path.name, new_name=pdf_path.name,
                            status="失败", error_reason=f"移动到输出目录失败: {exc}",
                        ))
                        report_lines.append(f"FAIL_MOVE|{pdf_path.name}|{exc}")
                        flush_report(report_lines)
                        continue

                logger.write(LogEntry(
                    original_name=pdf_path.name, new_name=delivered_path.name,
                    status=status, error_reason=error_reason,
                ))
                flush_report(report_lines)
                continue

            ocr_result = ocr_cache.get(pdf_path)
            if ocr_result:
                report_lines.append(f"OCR_CACHE_HIT|{pdf_path.name}")
            else:
                if ocr_service is None:
                    ocr_service = PaddleOCRService(lang=config.ocr_lang)
                image = pdf_service.render_first_page(pdf_path)
                ocr_result = ocr_service.recognize(image)
                ocr_cache.remember(pdf_path, ocr_result)
            extraction = extractor.extract(ocr_result)

            # 精确匹配
            cache_match = vendor_cache.match_text(ocr_result.full_text)
            fuzzy_used = False
            if cache_match:
                extraction.vendor_name = cache_match.vendor_name
                extraction.vendor_short_name = cache_match.vendor_short_name
            elif extraction.vendor_name:
                # 模糊匹配
                fuzzy_match = vendor_cache.fuzzy_match(ocr_result.full_text)
                if fuzzy_match:
                    extraction.vendor_name = fuzzy_match.vendor_name
                    extraction.vendor_short_name = fuzzy_match.vendor_short_name
                    fuzzy_used = True

            if not extraction.is_valid:
                skipped += 1
                reason = extraction.reason or "OCR 结果无法提取关键字段"
                logger.write(LogEntry(
                    original_name=pdf_path.name, new_name="", status="跳过", error_reason=reason,
                ))
                report_lines.append(f"SKIP|{pdf_path.name}|{reason}")
                flush_report(report_lines)
                continue

            desired_name = renamer.build_filename(
                extraction.vendor_short_name or "",
                extraction.contract_no or "",
                naming_mode=naming_mode,
                suffix=pdf_path.suffix,
            )
            final_path = renamer.rename_file(pdf_path, desired_name)
            final_path = renamer.move_to_output(final_path, config.output_dir)
            vendor_cache.remember(extraction.vendor_name, extraction.vendor_short_name)

            try:
                delivered_path, delivery_note = deliver_to_send_platform(send_bridge, final_path)
            except Exception as exc:
                failed += 1
                logger.write(LogEntry(
                    original_name=pdf_path.name, new_name=final_path.name,
                    status="失败", error_reason=f"已重命名，但移动到发送平台失败: {exc}",
                ))
                report_lines.append(f"FAIL_DELIVER|{pdf_path.name}|{final_path.name}|{exc}")
                flush_report(report_lines)
                continue

            success += 1
            tag = "FUZZY" if fuzzy_used else ("CACHE" if cache_match else "OCR")
            logger.write(LogEntry(
                original_name=pdf_path.name, new_name=delivered_path.name,
                status="成功", error_reason=delivery_note,
            ))
            report_lines.append(
                f"SUCCESS|{pdf_path.name}|{delivered_path.name}|"
                f"{extraction.vendor_short_name}|{extraction.contract_no}|{tag}"
            )
            flush_report(report_lines)
        except PDFRenderError as exc:
            failed += 1
            logger.write(LogEntry(
                original_name=pdf_path.name, new_name="", status="失败", error_reason=str(exc),
            ))
            report_lines.append(f"FAIL|{pdf_path.name}|{exc}")
            flush_report(report_lines)
        except Exception as exc:
            failed += 1
            logger.write(LogEntry(
                original_name=pdf_path.name, new_name="", status="失败", error_reason=str(exc),
            ))
            report_lines.append(f"FAIL|{pdf_path.name}|{exc}")
            report_lines.append(traceback.format_exc())
            flush_report(report_lines)

    report_lines.append(f"SUMMARY|success={success}|skipped={skipped}|failed={failed}")
    flush_report(report_lines)


if __name__ == "__main__":
    main()
