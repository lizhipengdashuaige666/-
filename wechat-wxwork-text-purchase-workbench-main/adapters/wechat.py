from __future__ import annotations

import time

import psutil
import win32con
import win32gui
import win32process

from .base import BaseMessenger
from core.logger import logger


class WeChatMessenger(BaseMessenger):
    platform = "微信"
    process_names = (
        "weixin.exe",
        "wechat.exe",
    )
    title_keywords = (
        "微信",
        "WeChat",
    )

    def activate(self) -> bool:
        candidates = self._find_main_windows()
        if not candidates:
            return super().activate()
        hwnd = max(candidates, key=self._window_score)
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        self._set_foreground(hwnd)
        self.hwnd = hwnd
        logger.info(f"{self.platform}窗口已激活: {win32gui.GetWindowText(hwnd)}")
        return True

    def open_chat_by_keyword(self, keyword: str) -> bool:
        return self._search_and_open(keyword, ("搜索", "Search"))

    def _find_main_windows(self) -> list[int]:
        candidates: list[int] = []

        def callback(hwnd, _):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process_name = psutil.Process(pid).name().lower()
                if process_name not in self.process_names:
                    return True
                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                if right - left < 500 or bottom - top < 400:
                    return True
                if class_name != "Qt51514QWindowIcon":
                    return True
                if title and any(keyword in title for keyword in self.title_keywords):
                    candidates.append(hwnd)
            except Exception:
                return True
            return True

        win32gui.EnumWindows(callback, None)
        return candidates
