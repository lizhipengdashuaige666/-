from __future__ import annotations

from .base import BaseMessenger


class WXWorkMessenger(BaseMessenger):
    platform = "企业微信"
    process_names = (
        "wxwork.exe",
        "wework.exe",
    )
    title_keywords = (
        "企业微信",
        "WXWork",
        "WeCom",
    )

    def open_chat_by_keyword(self, keyword: str) -> bool:
        return self._search_and_open(keyword, ("搜索", "Search"))
