from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.config import load_suppliers
from core.logger import logger

BUSINESS_TYPES = ("供应商往来对账单", "双章合同", "采购订单", "对账单", "订单", "合同", "发票", "PO")

_escaped_types = []
for _bt in BUSINESS_TYPES:
    if _bt == "PO":
        _escaped_types.append(r"(?<![a-zA-Z])PO(?![a-zA-Z])")
    else:
        _escaped_types.append(re.escape(_bt))
FILENAME_PATTERN = re.compile(rf"^(.+?)({'|'.join(_escaped_types)})(.+)$", re.IGNORECASE)
NUMBER_PATTERNS = (
    re.compile(r"(PO[\w-]{4,})", re.IGNORECASE),
    re.compile(r"(HT[\w-]{3,})", re.IGNORECASE),
    re.compile(r"(?:订单号|采购单号|合同编号|合同号|发票号码)[：:\s]*([\w-]{4,})", re.IGNORECASE),
    re.compile(r"(\d{8,})"),
)
PDF_MAX_PAGES = 5


@dataclass(frozen=True)
class ParsedDocument:
    supplier: str | None
    business_type: str | None
    number: str | None
    source: str

    @property
    def ok(self) -> bool:
        return bool(self.supplier)


def parse_document(file_path: str | Path) -> ParsedDocument:
    path = Path(file_path)
    by_name = _parse_from_name(path)
    if by_name.ok:
        return by_name

    by_pdf = _parse_from_pdf(path)
    if by_pdf.ok:
        return by_pdf

    logger.error(f"文件识别失败: {file_path}")
    return ParsedDocument(None, None, None, "未识别")


def parse_filename(file_path: str | Path) -> tuple[str | None, str | None, str | None]:
    parsed = parse_document(file_path)
    return parsed.supplier, parsed.business_type, parsed.number


def _parse_from_name(path: Path) -> ParsedDocument:
    stem = path.stem.strip()
    suppliers = load_suppliers()
    for supplier in sorted(suppliers, key=len, reverse=True):
        if stem.startswith(supplier):
            rest = stem[len(supplier):].strip(" _-")
            business_match = _find_business_match(rest)
            if business_match:
                business_type, raw_business_type = business_match
                number = _number_from_rest(rest, raw_business_type) or _find_number(rest) or rest or stem
                return ParsedDocument(supplier, business_type, number, "文件名")

    match = FILENAME_PATTERN.match(stem)
    if match:
        supplier, business_type, number = (part.strip(" _-") for part in match.groups())
        if supplier and number:
            return ParsedDocument(supplier, _normalize_business_type(business_type), number, "文件名")

    for supplier in sorted(suppliers, key=len, reverse=True):
        if supplier in stem:
            business_type = _find_business_type(stem) or "文件"
            number = _find_number(stem) or stem
            return ParsedDocument(supplier, business_type, number, "文件名")

    return ParsedDocument(None, None, None, "文件名")


def _parse_from_pdf(path: Path) -> ParsedDocument:
    if path.suffix.lower() != ".pdf" or not path.is_file():
        return ParsedDocument(None, None, None, "PDF内容")

    text = _extract_pdf_text(path)
    if not text:
        return ParsedDocument(None, None, None, "PDF内容")

    suppliers = load_suppliers()
    for supplier in sorted(suppliers, key=len, reverse=True):
        if supplier in text:
            business_type = _find_business_type(text) or "文件"
            number = _find_number(text) or path.stem
            return ParsedDocument(supplier, business_type, number, "PDF内容")

    return ParsedDocument(None, None, None, "PDF内容")


def _extract_pdf_text(path: Path, max_pages: int = PDF_MAX_PAGES) -> str:
    try:
        import fitz
    except ModuleNotFoundError:
        logger.error("缺少 PyMuPDF，无法从 PDF 内容识别供应商")
        return ""

    try:
        with fitz.open(str(path)) as doc:
            pages = min(max_pages, len(doc))
            return "\n".join(doc[index].get_text() for index in range(pages))
    except Exception as exc:
        logger.error(f"读取 PDF 内容失败: {exc}")
        return ""


def _find_business_type(text: str) -> str | None:
    match = _find_business_match(text)
    return match[0] if match else None


_PO_PATTERN = re.compile(r"(?<![a-zA-Z])po(?![a-zA-Z])")


def _find_business_match(text: str) -> tuple[str, str] | None:
    lower = text.lower()
    for business_type in BUSINESS_TYPES:
        if business_type == "PO":
            if _PO_PATTERN.search(lower):
                return "PO", "PO"
        elif business_type.lower() in lower:
            return _normalize_business_type(business_type), business_type
    return None


def _normalize_business_type(business_type: str) -> str:
    lower = business_type.lower()
    if lower == "po" or "订单" in business_type:
        return "PO"
    if "对账单" in business_type:
        return "对账单"
    return business_type


def _number_from_rest(rest: str, raw_business_type: str) -> str:
    return rest.replace(raw_business_type, "", 1).strip(" _-")


def _find_number(text: str) -> str | None:
    for pattern in NUMBER_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None
