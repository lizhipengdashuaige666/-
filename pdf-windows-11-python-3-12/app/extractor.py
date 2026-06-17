from __future__ import annotations

import re

from app.models import ExtractionResult, OCRResult


class ContractExtractor:
    CONTRACT_LABEL_PATTERN = re.compile(
        r"(?i)(?:合同编号|合同编码|合同号|contract\s*no\.?|编号|订单号|采购单号)\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9\-_/\.]{3,})"
    )
    # 供方标签 + 紧跟的公司名称（限制捕获长度，避免吞掉后续噪音）
    VENDOR_LABEL_RE = re.compile(
        r"(?i)(?:供方|供货方|供应商|乙方|卖方|销售方|承包方|seller|supplier|公司名称|供方名称|单位名称)"
        r"\s*(?:[（(][^\s）)]*[）)])?\s*[:：]?\s*"
    )
    # 显式法律后缀
    COMPANY_SUFFIX_RE = re.compile(
        r"(?:有限公司|有限责任公司|股份有限公司|集团有限公司|集团股份有限公司|公司|经营部|商行)"
    )
    PO_DIRECT_PATTERN = re.compile(r'(?i)\b(PO\d{8,})\b')

    LOCATION_PREFIX_PATTERN = re.compile(
        r"^(?:[一-龥]{2,4}(?:省|市)|[一-龥]{2,8}自治区)(.+)$"
    )

    LEGAL_SUFFIXES = [
        "集团股份有限公司",
        "集团有限责任公司",
        "集团有限公司",
        "股份有限公司",
        "有限责任公司",
        "有限公司",
        "有限合伙",
        "普通合伙",
    ]

    CITY_PREFIXES = [
        "北京市", "北京",
        "上海市", "上海",
        "天津市", "天津",
        "重庆市", "重庆",
        "深圳市", "深圳",
        "广州市", "广州",
        "杭州市", "杭州",
        "苏州市", "苏州",
        "南京市", "南京",
        "成都市", "成都",
        "武汉市", "武汉",
        "西安市", "西安",
        "广东", "浙江", "江苏",
    ]

    TRAILING_NOISE_KEYWORDS = [
        "地址", "产品订货单", "购销合同", "合同编号", "合同专用", "合同",
        "联系人", "电话", "开户行", "开户银行", "账号", "税号",
        "纳税人识别号", "统一社会信用代码",
    ]

    BUYER_NAME_KEYWORDS = [
        "安侣医学", "深圳安侣医学", "深圳安侣医学科技", "深圳安侣医学科技有限公司",
    ]

    BUSINESS_WORDS = [
        "自动化技术", "自动化", "传动设备", "医学科技", "生物科技",
        "科技技术", "技术", "科技", "机电", "电气", "过滤",
        "五金制品", "制品", "包装材料", "包装", "实验器材", "经营部", "印刷", "印副",
        "工业", "精密", "电子", "设备", "贸易", "商贸", "实业", "新材料",
    ]

    INVALID_SHORT_NAMES: set[str] = {
        "合同", "采购", "购销", "销售", "订货", "产品", "供应", "供货",
        "需方", "供方", "甲方", "乙方", "买方", "卖方",
        "有限", "责任", "股份", "集团",
        "编号", "电话", "地址", "联系", "开户", "账号", "税号",
        "日期", "金额", "订单", "备注", "签名", "盖章", "签字",
        "审批", "经办", "部门", "主管",
        "采购部", "财务部", "技术部",
        "合计", "总计", "小计", "人民币", "含税", "不含税", "税率",
        "发票", "专用", "普通", "增值", "验收", "合格", "工作日",
        "付款", "方式", "交货", "运输", "包装", "质量", "标准",
    }

    # 句子/条款特征词 —— 含这些词的文本不可能是公司名
    CLAUSE_KEYWORDS = [
        "验收合格", "增值税", "发票", "工作日", "付款", "交货期",
        "违约责任", "争议", "仲裁", "诉讼", "不可抗力", "保密",
        "知识产权", "送达", "生效", "签订", "签署", "盖章",
        "一式", "副本", "正本", "传真", "扫描件",
        "结算", "支付", "汇款", "转账", "支票", "承兑",
        "质保", "保修", "售后", "维修", "退换", "赔偿",
    ]

    def extract(self, ocr_result: OCRResult) -> ExtractionResult:
        # 过滤低置信度行，仅保留 score >= 0.3 或 score 为 None（旧版兼容）
        lines = [
            self._normalize_line(item.text)
            for item in ocr_result.lines
            if item.text.strip() and (item.score is None or item.score >= 0.3)
        ]
        contract_no = self._extract_contract_no(lines, ocr_result.full_text)
        vendor_name = self._extract_vendor_name(lines)
        vendor_short_name = self.abbreviate_company_name(vendor_name) if vendor_name else None

        reason = None
        if not contract_no and not vendor_short_name:
            reason = "未识别到合同编号和供方名称"
        elif not contract_no:
            reason = "未识别到合同编号"
        elif not vendor_short_name:
            reason = "未识别到供方名称"

        return ExtractionResult(
            vendor_name=vendor_name,
            vendor_short_name=vendor_short_name,
            contract_no=contract_no,
            reason=reason,
        )

    def abbreviate_company_name(self, company_name: str) -> str | None:
        cleaned = self._clean_vendor_candidate(company_name)
        if not cleaned:
            return None

        cleaned = re.sub(r"[（(].*?[）)]", "", cleaned).strip()
        match = self.LOCATION_PREFIX_PATTERN.match(cleaned)
        if match and len(match.group(1)) >= 4:
            cleaned = match.group(1).strip()

        for prefix in self.CITY_PREFIXES:
            if cleaned.startswith(prefix) and len(cleaned) > len(prefix) + 1:
                cleaned = cleaned[len(prefix):].strip()
                break

        for suffix in self.LEGAL_SUFFIXES:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)].strip()
                break

        if cleaned.endswith("工业") and len(cleaned) > 4:
            cleaned = cleaned[:-2].strip()

        cleaned = re.sub(r"\s+", "", cleaned)
        cleaned = cleaned.strip(" _-")

        if self._is_buyer_company(cleaned):
            return None
        if cleaned in self.INVALID_SHORT_NAMES:
            return None

        cleaned = self._trim_business_words(cleaned)
        cleaned = cleaned.strip(" _-")

        if len(cleaned) >= 4:
            cleaned = cleaned[:2]

        if not cleaned or cleaned in self.INVALID_SHORT_NAMES:
            return None
        return cleaned

    # ------------------------------------------------------------------
    # 合同编号提取
    # ------------------------------------------------------------------
    def _extract_contract_no(self, lines: list[str], full_text: str) -> str | None:
        for index, line in enumerate(lines):
            inline_match = self.CONTRACT_LABEL_PATTERN.search(line)
            if inline_match:
                candidate = self._clean_contract_no(inline_match.group(1))
                if self._is_valid_contract_no(candidate):
                    return candidate

            flattened = self._flatten_text(line)
            if self._contains_contract_label(flattened):
                for offset in (1, 2):
                    next_index = index + offset
                    if next_index < len(lines):
                        candidate = self._clean_contract_no(lines[next_index])
                        if self._is_valid_contract_no(candidate):
                            return candidate

        for line in lines:
            if not self._contains_contract_label(self._flatten_text(line)):
                continue
            for chunk in re.split(r"[:：\s]", line):
                candidate = self._clean_contract_no(chunk)
                if self._is_valid_contract_no(candidate):
                    return candidate

        compact_text = self._flatten_text(full_text)
        match = self.CONTRACT_LABEL_PATTERN.search(compact_text)
        if match:
            candidate = self._clean_contract_no(match.group(1))
            if self._is_valid_contract_no(candidate):
                return candidate

        po_match = self.PO_DIRECT_PATTERN.search(compact_text)
        if po_match:
            candidate = po_match.group(1).upper()
            if self._is_valid_contract_no(candidate):
                return candidate

        return None

    # ------------------------------------------------------------------
    # 供方名称提取
    # ------------------------------------------------------------------
    def _extract_vendor_name(self, lines: list[str]) -> str | None:
        # 第一轮：标签引导（同行或下一行）
        for index, line in enumerate(lines):
            label_match = self.VENDOR_LABEL_RE.search(line)
            if not label_match:
                continue

            # 标签之后的剩余文本
            after_label = line[label_match.end():].strip()
            if after_label:
                candidate = self._extract_vendor_from_text(after_label)
                if candidate:
                    return candidate

            # 标签所在行无有效公司名 → 查下一行
            for offset in (1, 2):
                next_index = index + offset
                if next_index >= len(lines):
                    break
                next_line = lines[next_index]
                if self._contains_vendor_label(self._flatten_text(next_line)):
                    continue
                candidate = self._clean_vendor_candidate(next_line)
                if self._looks_like_company(candidate):
                    return candidate

        # 第二轮：无标签时，扫描带法律后缀的行（最可靠的备选）
        suffix_candidates = []
        for line in lines:
            cleaned = self._clean_vendor_candidate(line)
            if self._has_company_suffix(cleaned) and not self._is_buyer_company(cleaned):
                if not self._contains_clause_keywords(cleaned):
                    suffix_candidates.append(cleaned)

        if suffix_candidates:
            suffix_candidates.sort(key=len, reverse=True)
            return suffix_candidates[0]

        return None

    def _extract_vendor_from_text(self, text: str) -> str | None:
        """从标签后的文本片段中提取公司名。"""
        # 尝试提取完整公司名（含法律后缀）
        suffix_match = re.search(
            r"([一-龥A-Za-z0-9（()）\-]{4,40}?"
            r"(?:有限公司|有限责任公司|股份有限公司|集团有限公司|集团股份有限公司|有限合伙|普通合伙|经营部|商行))",
            text,
        )
        if suffix_match:
            candidate = suffix_match.group(1).strip()
            if self._looks_like_company(candidate):
                return candidate

        # 没有后缀时，取前几个字作为候选（限制长度避免吞噪音）
        # 多数无后缀的公司名如 "信步科技"、"元汇实验器材经营部" 等较短
        short = text.split(",")[0].split("，")[0].split("。")[0].split("；")[0].strip()
        short = re.split(r"\s{2,}", short)[0].strip()
        if self._looks_like_company(short):
            return short

        return None

    # ------------------------------------------------------------------
    # 辅助判断
    # ------------------------------------------------------------------
    def _contains_contract_label(self, text: str) -> bool:
        lowered = text.lower()
        return any(label in lowered for label in ["合同编号", "合同编码", "合同号", "contractno", "编号"])

    def _contains_vendor_label(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            label in lowered
            for label in [
                "供方", "供货方", "供应商", "乙方", "卖方", "销售方", "承包方",
                "seller", "supplier", "公司名称", "供方名称", "单位名称",
            ]
        )

    def _has_company_suffix(self, text: str) -> bool:
        """文本是否包含显式的公司法律后缀。"""
        return bool(self.COMPANY_SUFFIX_RE.search(text))

    def _contains_clause_keywords(self, text: str) -> bool:
        """文本是否包含合同条款关键词（用于排除条款被误判为公司）。"""
        return any(kw in text for kw in self.CLAUSE_KEYWORDS)

    def _looks_like_company(self, text: str | None) -> bool:
        if not text:
            return False
        if len(text) < 4:
            return False
        if len(text) > 80:
            return False
        if self._is_buyer_company(text):
            return False
        if self._contains_contract_label(self._flatten_text(text)):
            return False
        if self._contains_clause_keywords(text):
            return False

        # 包含显式法律后缀 → 确定是公司
        if self._has_company_suffix(text):
            return True

        # 无法律后缀但包含噪音词 → 排除
        if any(keyword in text for keyword in self.TRAILING_NOISE_KEYWORDS):
            return False

        # 无后缀时：必须是较短的中文文本（≤12字）
        # 合同条款/句子通常远长于此
        chinese_chars = re.findall(r"[一-龥]", text)
        if len(chinese_chars) < 2 or len(chinese_chars) > 12:
            return False

        # 必须包含至少一个行业词或全程为中文
        has_business = any(word in text for word in self.BUSINESS_WORDS)
        all_chinese = bool(re.fullmatch(r"[一-龥A-Za-z0-9（()）\-]+", text))
        return has_business or all_chinese

    def _clean_vendor_candidate(self, value: str) -> str:
        candidate = self._normalize_line(value)
        candidate = self.VENDOR_LABEL_RE.sub("", candidate).strip()

        for keyword in self.TRAILING_NOISE_KEYWORDS:
            candidate = re.split(rf"{keyword}\s*[：:]", candidate)[0]

        candidate = candidate.strip(" ：:，,。;；")
        return candidate

    def _clean_contract_no(self, value: str) -> str:
        candidate = self._flatten_text(value)
        candidate = re.sub(r"(?i)(?:合同编号|合同编码|合同号|contractno|编号)", "", candidate)
        candidate = re.sub(r"[^A-Za-z0-9\-_/\.]", "", candidate).upper()
        return candidate.strip("._-")

    def _is_valid_contract_no(self, value: str | None) -> bool:
        if not value:
            return False
        if len(value) < 5 or len(value) > 40:
            return False
        return bool(re.search(r"\d", value))

    def _normalize_line(self, value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    def _flatten_text(self, value: str) -> str:
        return re.sub(r"\s+", "", value or "").replace("：", ":")

    def _is_buyer_company(self, value: str | None) -> bool:
        if not value:
            return False
        normalized = self._flatten_text(value)
        return any(keyword in normalized for keyword in self.BUYER_NAME_KEYWORDS)

    def _trim_business_words(self, value: str) -> str:
        cleaned = value
        changed = True
        while changed:
            changed = False
            for word in self.BUSINESS_WORDS:
                if cleaned.endswith(word) and len(cleaned) > len(word):
                    cleaned = cleaned[:-len(word)]
                    changed = True
                    break
        return cleaned
