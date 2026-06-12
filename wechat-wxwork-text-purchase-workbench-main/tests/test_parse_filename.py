import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import fitz

from core.config import upsert_supplier
from core.dispatcher import process_file
from core.parser import parse_document, parse_filename


class ParseFilenameTest(unittest.TestCase):
    def test_parse_po_filename(self):
        self.assertEqual(parse_filename("万度PO20260528001.pdf"), ("万度", "PO", "20260528001"))

    def test_parse_contract_filename(self):
        self.assertEqual(parse_filename("响之震双章合同HT001.pdf"), ("响之震", "双章合同", "HT001"))

    def test_parse_statement_filename(self):
        self.assertEqual(parse_filename("瑞宝对账单202605.pdf"), ("瑞宝", "对账单", "202605"))

    def test_parse_supplier_statement_filename(self):
        self.assertEqual(parse_filename("迈瑞5月供应商往来对账单.pdf"), ("迈瑞", "对账单", "5月"))

    def test_reject_bad_filename(self):
        self.assertEqual(parse_filename("错误文件名.pdf"), (None, None, None))

    def test_parse_configured_supplier_from_loose_name(self):
        parsed = parse_document("万度电气_报价资料_20260528001.pdf")
        self.assertEqual(parsed.supplier, "万度电气")
        self.assertEqual(parsed.source, "文件名")

    def test_parse_supplier_from_pdf_content(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "1218_001.pdf"
            path.write_bytes(b"%PDF-1.4\n%%EOF")

            with patch("core.parser._extract_pdf_text", return_value="供应商：万度电气\n采购订单 PO20260528001"):
                parsed = parse_document(path)

        self.assertEqual(parsed.supplier, "万度电气")
        self.assertEqual(parsed.business_type, "PO")
        self.assertEqual(parsed.number, "PO20260528001")
        self.assertEqual(parsed.source, "PDF内容")

    def test_process_file_accepts_manual_supplier_and_platform(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "1218_001.pdf"
            path.write_bytes(b"%PDF-1.4\n%%EOF")
            adapter = _FakeAdapter()
            with patch.dict("core.dispatcher.ADAPTERS", {"wxwork": lambda: adapter}):
                ok = process_file(
                    path,
                    supplier_override="锦众",
                    platform_override="wxwork",
                    chat_name_override="安侣-锦众沟通群",
                )

        self.assertTrue(ok)
        self.assertEqual(adapter.opened, "锦众")
        self.assertEqual(adapter.sent, path)

    def test_upsert_supplier_saves_group_name(self):
        with TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "suppliers.json"
            with patch("core.config.SUPPLIERS_FILE", temp_file):
                config = upsert_supplier("测试供应商", "微信", "测试群")

                self.assertEqual(config, {"platform": "wechat", "chat_name": "测试群", "delivery_type": "instrument"})


class _FakeAdapter:
    platform = "企业微信"

    def __init__(self):
        self.opened = None
        self.sent = None

    def activate(self):
        return True

    def open_chat_by_keyword(self, supplier):
        self.opened = supplier
        return True

    def send_file(self, path):
        self.sent = path
        return True
