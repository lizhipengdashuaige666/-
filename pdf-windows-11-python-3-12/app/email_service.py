from __future__ import annotations

import email
import imaplib
import re
from dataclasses import dataclass, field
from pathlib import Path


class EmailFetchError(RuntimeError):
    """邮箱拉取失败"""


@dataclass(slots=True)
class EmailConfig:
    imap_server: str
    imap_port: int
    username: str
    password: str
    sender_keywords: list[str] = field(default_factory=list)
    subject_keywords: list[str] = field(default_factory=list)
    download_dir: Path = Path(".")
    mark_read: bool = True
    unread_only: bool = True


@dataclass(slots=True)
class FetchResult:
    downloaded: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


class EmailService:
    def __init__(self) -> None:
        self._imap: imaplib.IMAP4_SSL | None = None

    def fetch_pdf_attachments(self, config: EmailConfig) -> FetchResult:
        result = FetchResult()
        config.download_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._imap = imaplib.IMAP4_SSL(config.imap_server, config.imap_port)
            self._imap.login(config.username, config.password)
            self._imap.select("INBOX")

            search_criteria = "UNSEEN" if config.unread_only else "ALL"
            _, message_ids = self._imap.search(None, search_criteria)
            if not message_ids or not message_ids[0]:
                return result

            for mid in message_ids[0].split():
                try:
                    ok, data = self._imap.fetch(mid, "(RFC822)")
                    if not ok or not data or not data[0]:
                        result.skipped += 1
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    sender = self._get_sender(msg)
                    subject = self._get_subject(msg)

                    if not self._matches_keywords(sender, config.sender_keywords) and not self._matches_keywords(subject, config.subject_keywords):
                        result.skipped += 1
                        continue

                    saved = self._save_pdf_attachments(msg, config.download_dir)
                    result.downloaded += saved

                    if config.mark_read:
                        self._imap.store(mid, "+FLAGS", "\\Seen")
                except Exception:
                    result.errors.append(f"邮件 {mid.decode() if isinstance(mid, bytes) else mid} 处理失败")
                    result.skipped += 1

        finally:
            if self._imap:
                try:
                    self._imap.logout()
                except Exception:
                    pass

        return result

    def _get_sender(self, msg: email.message.Message) -> str:
        return str(msg.get("From", ""))

    def _get_subject(self, msg: email.message.Message) -> str:
        raw = msg.get("Subject", "")
        try:
            decoded, encoding = email.header.decode_header(raw)[0]
            if isinstance(decoded, bytes):
                return decoded.decode(encoding or "utf-8", errors="replace")
            return str(decoded)
        except Exception:
            return str(raw)

    def _matches_keywords(self, text: str, keywords: list[str]) -> bool:
        if not keywords:
            return True
        lower_text = text.lower()
        return any(kw.lower() in lower_text for kw in keywords if kw)

    def _save_pdf_attachments(self, msg: email.message.Message, download_dir: Path) -> int:
        saved = 0
        for part in msg.walk():
            if part.get_content_maintype() != "multipart" and part.get("Content-Disposition"):
                filename = part.get_filename()
                if not filename or not filename.lower().endswith(".pdf"):
                    continue

                safe_name = re.sub(r'[\\/:*?"<>|]', "_", filename)
                filepath = download_dir / safe_name
                if filepath.exists():
                    stem = filepath.stem
                    suffix = filepath.suffix
                    idx = 1
                    while filepath.exists():
                        filepath = download_dir / f"{stem}_{idx}{suffix}"
                        idx += 1

                try:
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    saved += 1
                except Exception:
                    pass
        return saved
