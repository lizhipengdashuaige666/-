from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class VendorCacheMatch:
    vendor_name: str
    vendor_short_name: str


class VendorCache:
    GENERIC_ALIASES = {
        "北京", "北京市", "上海", "上海市", "天津", "天津市",
        "重庆", "重庆市", "深圳", "深圳市",
        "广东", "浙江", "江苏",
        "广州", "广州市", "杭州", "杭州市",
        "苏州", "苏州市", "南京", "南京市",
        "成都", "成都市", "武汉", "武汉市", "西安", "西安市",
        "合同", "采购", "购销", "销售", "供货", "供方", "需方",
        "甲方", "乙方", "买方", "卖方",
        "有限", "责任", "股份", "集团",
    }

    # 模糊匹配的最低相似度阈值
    FUZZY_THRESHOLD = 0.55

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    # ------------------------------------------------------------------
    # 精确匹配：全文包含供应商名或别名
    # ------------------------------------------------------------------
    MIN_NAME_LENGTH = 2  # 单字简称太容易误匹配（如"票"在"发票"中）

    def match_text(self, text: str) -> VendorCacheMatch | None:
        normalized_text = self._normalize(text)
        best_entry: dict[str, object] | None = None
        best_score = -1

        for entry in self._data.get("vendors", []):
            names = self._entry_names(entry)
            if not names:
                continue

            match_len = self._longest_contained_name(names, normalized_text)
            if match_len >= self.MIN_NAME_LENGTH and match_len > best_score:
                best_entry = entry
                best_score = match_len

        if not best_entry:
            return None

        return VendorCacheMatch(
            vendor_name=str(best_entry.get("vendor_name", "")),
            vendor_short_name=str(best_entry.get("vendor_short_name", "")),
        )

    # ------------------------------------------------------------------
    # 模糊匹配：OCR 可能有错字/漏字时，用字符重叠度匹配
    # ------------------------------------------------------------------
    def fuzzy_match(self, text: str) -> VendorCacheMatch | None:
        """从 OCR 文本中逐行提取候选公司名片段，与缓存做模糊比对。"""
        if not text:
            return None

        # 先从全文提取所有 4-30 字的连续中文片段作为候选
        candidates = self._extract_text_fragments(text)
        if not candidates:
            return None

        best_entry: dict[str, object] | None = None
        best_score = 0.0

        for entry in self._data.get("vendors", []):
            entry_names = self._entry_names(entry)
            if not entry_names:
                continue

            for candidate in candidates:
                for name in entry_names:
                    sim = self._char_similarity(candidate, name)
                    if sim > best_score and sim >= self.FUZZY_THRESHOLD:
                        best_score = sim
                        best_entry = entry

        if not best_entry:
            return None

        return VendorCacheMatch(
            vendor_name=str(best_entry.get("vendor_name", "")),
            vendor_short_name=str(best_entry.get("vendor_short_name", "")),
        )

    def _extract_text_fragments(self, text: str) -> list[str]:
        """从文本中提取所有 4-30 字的连续中文片段。"""
        normalized = self._normalize(text)
        # 提取纯中文 + 字母数字的连续片段
        fragments = re.findall(r"[一-龥A-Za-z0-9]{4,30}", normalized)
        # 去重、过滤纯数字
        seen = set()
        result = []
        for frag in fragments:
            if frag in seen:
                continue
            seen.add(frag)
            # 过滤过于泛化的片段
            if not self._is_generic_alias(frag):
                result.append(frag)
        return result

    def _char_similarity(self, a: str, b: str) -> float:
        """基于 Jaccard 系数的字符级相似度，对 OCR 错字/漏字容忍度高。"""
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        intersection = set_a & set_b
        union = set_a | set_b
        if not union:
            return 0.0
        return len(intersection) / len(union)

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def remember(self, vendor_name: str | None, vendor_short_name: str | None) -> None:
        if not vendor_name or not vendor_short_name:
            return

        normalized_name = self._normalize(vendor_name)
        normalized_short = self._normalize(vendor_short_name)
        if not normalized_name or not normalized_short:
            return
        if len(normalized_short) < self.MIN_NAME_LENGTH:
            return
        if self._is_generic_alias(normalized_short):
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        vendors = self._data.setdefault("vendors", [])

        for entry in vendors:
            aliases = {self._normalize(str(alias)) for alias in entry.get("aliases", [])}
            known = {
                self._normalize(str(entry.get("vendor_name", ""))),
                self._normalize(str(entry.get("vendor_short_name", ""))),
                *aliases,
            }
            if normalized_name in known or normalized_short in known:
                entry["vendor_name"] = vendor_name
                entry["vendor_short_name"] = vendor_short_name
                entry["last_seen"] = now
                entry["count"] = int(entry.get("count", 0)) + 1
                raw_aliases = {
                    str(alias)
                    for alias in entry.get("aliases", [])
                    if not self._is_generic_alias(self._normalize(str(alias)))
                }
                raw_aliases.update({vendor_name, vendor_short_name})
                entry["aliases"] = sorted(raw_aliases)
                self.save()
                return

        vendors.append(
            {
                "vendor_name": vendor_name,
                "vendor_short_name": vendor_short_name,
                "aliases": sorted({vendor_name, vendor_short_name}),
                "count": 1,
                "first_seen": now,
                "last_seen": now,
            }
        )
        self.save()

    def save(self) -> None:
        self.cache_path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _entry_names(self, entry: dict[str, object]) -> list[str]:
        """获取某个缓存条目的所有非泛化名称。"""
        raw = [
            str(entry.get("vendor_name", "")),
            str(entry.get("vendor_short_name", "")),
            *[str(alias) for alias in entry.get("aliases", [])],
        ]
        return [
            self._normalize(name)
            for name in raw
            if name and not self._is_generic_alias(self._normalize(name))
        ]

    def _longest_contained_name(self, names: list[str], text: str) -> int:
        """返回 names 中最长的被 text 包含的名字长度，无匹配返回 0。"""
        best = 0
        for name in names:
            if name and len(name) >= self.MIN_NAME_LENGTH and name in text:
                if len(name) > best:
                    best = len(name)
        return best

    def _load(self) -> dict[str, object]:
        if not self.cache_path.exists():
            return {"vendors": []}

        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("vendors", []), list):
                return data
        except Exception:
            pass
        return {"vendors": []}

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", "", value or "").lower()

    def _is_generic_alias(self, value: str) -> bool:
        return value in {self._normalize(alias) for alias in self.GENERIC_ALIASES}
