import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from gui.app import PurchaseWorkbench, TaskItem


class GuiLogicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_toggle_all_checked(self):
        window = PurchaseWorkbench()
        window.tasks = [
            _task("a.pdf", "迈瑞", "PO"),
            _task("b.pdf", "锦众", "PO"),
        ]
        window._refresh()

        window._toggle_all()

        self.assertTrue(all(task.checked for task in window.tasks))

    def test_groups_cross_supplier_tasks(self):
        window = PurchaseWorkbench()
        tasks = [
            _task("a.pdf", "迈瑞", "PO"),
            _task("b.pdf", "锦众", "PO"),
            _task("c.pdf", "迈瑞", "PO"),
        ]

        groups = window._groups(tasks)

        self.assertEqual(len(groups), 2)
        self.assertEqual(sorted(len(group) for group in groups), [1, 2])

    def test_toggle_all_checked_only_visible_tasks(self):
        window = PurchaseWorkbench()
        window.tasks = [
            _task("a.pdf", "迈瑞", "PO"),
            _task("b.pdf", "锦众", "PO"),
        ]
        window._filter_edit.setText("迈瑞")

        window._toggle_all()

        self.assertTrue(window.tasks[0].checked)
        self.assertFalse(window.tasks[1].checked)

    def test_fill_checked_tasks(self):
        window = PurchaseWorkbench()
        window.tasks = [
            _task("a.pdf", "迈瑞", "PO"),
            _task("b.pdf", "锦众", "PO"),
        ]
        window.tasks[0].checked = True
        window._refresh()
        window._fill_platform.setCurrentIndex(window._fill_platform.findData("wxwork"))
        window._fill_chat.setText("测试企业微信群")

        window.fill_checked_tasks()

        self.assertEqual(window.tasks[0].platform, "wxwork")
        self.assertEqual(window.tasks[0].chat_name, "测试企业微信群")
        self.assertEqual(window.tasks[1].platform, "wechat")


def _task(file_name: str, supplier: str, business_type: str) -> TaskItem:
    return TaskItem(
        path=Path(file_name),
        supplier=supplier,
        business_type=business_type,
        number=file_name,
        source="测试",
        platform="wechat",
        chat_name=f"{supplier}测试群",
    )


if __name__ == "__main__":
    unittest.main()
