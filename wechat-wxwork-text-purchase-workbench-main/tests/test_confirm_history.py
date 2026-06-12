import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.confirm_history import (
    get_confirmation_count,
    needs_confirmation,
    record_confirmation,
)


class ConfirmHistoryTest(unittest.TestCase):
    def test_supplier_needs_three_confirmations(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "confirm_history.json"

            self.assertTrue(needs_confirmation("迈瑞", "wechat", "迈瑞-测试群", path))
            self.assertEqual(record_confirmation("迈瑞", "wechat", "迈瑞-测试群", path), 1)
            self.assertTrue(needs_confirmation("迈瑞", "wechat", "迈瑞-测试群", path))
            self.assertEqual(record_confirmation("迈瑞", "wechat", "迈瑞-测试群", path), 2)
            self.assertTrue(needs_confirmation("迈瑞", "wechat", "迈瑞-测试群", path))
            self.assertEqual(record_confirmation("迈瑞", "wechat", "迈瑞-测试群", path), 3)
            self.assertFalse(needs_confirmation("迈瑞", "wechat", "迈瑞-测试群", path))

    def test_changed_chat_name_starts_over(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "confirm_history.json"
            for _ in range(3):
                record_confirmation("迈瑞", "wechat", "迈瑞-测试群", path)

            self.assertFalse(needs_confirmation("迈瑞", "wechat", "迈瑞-测试群", path))
            self.assertTrue(needs_confirmation("迈瑞", "wechat", "迈瑞正式群", path))
            self.assertEqual(get_confirmation_count("迈瑞", "wechat", "迈瑞正式群", path), 0)

    def test_load_history_accepts_utf8_bom(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "confirm_history.json"
            path.write_text('{"迈瑞\\nwechat\\n迈瑞-测试群": {"count": 2}}', encoding="utf-8-sig")

            self.assertEqual(get_confirmation_count("迈瑞", "wechat", "迈瑞-测试群", path), 2)


if __name__ == "__main__":
    unittest.main()
