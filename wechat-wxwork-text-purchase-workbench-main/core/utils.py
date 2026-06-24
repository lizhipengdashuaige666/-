from __future__ import annotations

import struct
import time
from pathlib import Path
from typing import Iterable

import win32clipboard
import win32con


def copy_files_to_clipboard(paths: Iterable[Path]) -> None:
    files = [str(path.resolve()) for path in paths]
    encoded = ("\0".join(files) + "\0\0").encode("utf-16le")
    dropfiles = struct.pack("IiiII", 20, 0, 0, 0, 1)
    data = dropfiles + encoded

    last_error: Exception | None = None
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
                return
            finally:
                win32clipboard.CloseClipboard()
        except Exception as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"写入文件剪贴板失败: {last_error}") from last_error


def clipboard_has_files() -> bool:
    try:
        win32clipboard.OpenClipboard()
        try:
            return bool(win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP))
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        return False


def clipboard_has_text() -> bool:
    try:
        win32clipboard.OpenClipboard()
        try:
            return bool(win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT))
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        return False


def copy_text_to_clipboard(text: str) -> None:
    last_error: Exception | None = None
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                return
            finally:
                win32clipboard.CloseClipboard()
        except Exception as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"写入文本剪贴板失败: {last_error}") from last_error
