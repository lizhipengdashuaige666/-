from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    base_dir: Path
    pdf_dir: Path
    output_dir: Path
    naming_mode: str
    recursive_scan: bool
    render_dpi: int
    log_dir: Path
    temp_dir: Path
    cache_dir: Path
    vendor_cache_path: Path
    ocr_text_cache_path: Path
    ocr_lang: str
    window_title: str
    send_platform_enabled: bool
    send_platform_dir: Path
    send_platform_inbox_dir: Path
    email_enabled: bool
    email_imap_server: str
    email_imap_port: int
    email_username: str
    email_password: str
    email_sender_keywords: list[str]
    email_subject_keywords: list[str]
    email_mark_read: bool

    def ensure_runtime_dirs(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.send_platform_enabled:
            self.send_platform_inbox_dir.mkdir(parents=True, exist_ok=True)


def _as_bool(value: str, default: bool = False) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "y", "on"}


def _resolve_path(base_dir: Path, raw_value: str, fallback: str) -> Path:
    value = (raw_value or fallback).strip()
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def load_config(base_dir: Path) -> AppConfig:
    env_path = base_dir / ".env"
    load_dotenv(env_path)

    pdf_dir = _resolve_path(
        base_dir,
        os.getenv("PDF_DIR", r"D:\采购工作\采购订单电子档"),
        r"D:\采购工作\采购订单电子档",
    )
    log_dir = _resolve_path(base_dir, os.getenv("LOG_DIR", "logs"), "logs")
    temp_dir = _resolve_path(base_dir, os.getenv("TEMP_DIR", "temp"), "temp")
    cache_dir = _resolve_path(base_dir, os.getenv("CACHE_DIR", "cache"), "cache")
    default_send_platform_dir = (
        r"C:\Users\19811\.claude\projects\wechat-wxwork-text-purchase-workbench-main"
    )
    send_platform_dir = _resolve_path(
        base_dir,
        os.getenv("SEND_PLATFORM_DIR", default_send_platform_dir),
        default_send_platform_dir,
    )
    send_platform_inbox_dir = _resolve_path(
        base_dir,
        os.getenv("SEND_PLATFORM_INBOX_DIR", str(send_platform_dir / "inbox")),
        str(send_platform_dir / "inbox"),
    )
    output_dir = _resolve_path(
        base_dir,
        os.getenv("OUTPUT_DIR", r"D:\采购工作\采购订单"),
        r"D:\采购工作\采购订单",
    )

    config = AppConfig(
        base_dir=base_dir,
        pdf_dir=pdf_dir,
        output_dir=output_dir,
        naming_mode=os.getenv("NAMING_MODE", "dual_chop").strip() or "dual_chop",
        recursive_scan=_as_bool(os.getenv("RECURSIVE_SCAN", "false")),
        render_dpi=int(os.getenv("RENDER_DPI", "200")),
        log_dir=log_dir,
        temp_dir=temp_dir,
        cache_dir=cache_dir,
        vendor_cache_path=cache_dir / "vendor_cache.json",
        ocr_text_cache_path=cache_dir / "ocr_text_cache.json",
        ocr_lang=os.getenv("OCR_LANG", "ch").strip() or "ch",
        window_title=os.getenv("WINDOW_TITLE", "采购合同 PDF 自动命名工具").strip()
        or "采购合同 PDF 自动命名工具",
        send_platform_enabled=_as_bool(os.getenv("SEND_PLATFORM_ENABLED", "false"), default=False),
        send_platform_dir=send_platform_dir,
        send_platform_inbox_dir=send_platform_inbox_dir,
        email_enabled=_as_bool(os.getenv("EMAIL_ENABLED", "false"), default=False),
        email_imap_server=os.getenv("EMAIL_IMAP_SERVER", "imap.exmail.qq.com").strip() or "imap.exmail.qq.com",
        email_imap_port=int(os.getenv("EMAIL_IMAP_PORT", "993")),
        email_username=os.getenv("EMAIL_USERNAME", "").strip(),
        email_password=os.getenv("EMAIL_PASSWORD", "").strip(),
        email_sender_keywords=[kw.strip() for kw in os.getenv("EMAIL_SENDER_KEYWORDS", "").split(",") if kw.strip()],
        email_subject_keywords=[kw.strip() for kw in os.getenv("EMAIL_SUBJECT_KEYWORDS", "合同,采购,订单").split(",") if kw.strip()],
        email_mark_read=_as_bool(os.getenv("EMAIL_MARK_READ", "true"), default=True),
    )
    config.ensure_runtime_dirs()
    return config
