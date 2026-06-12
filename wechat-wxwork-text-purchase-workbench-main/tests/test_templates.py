import unittest

from core.templates import render_message


class TemplateTest(unittest.TestCase):
    def test_render_po_message(self):
        message = render_message("PO")

        self.assertIn("最新采购订单", message)
        self.assertIn("收货信息", message)
        self.assertIn("益成工业园A栋5楼503号", message)

    def test_render_reagent_message(self):
        message = render_message("PO", "reagent")

        self.assertIn("最新采购订单", message)
        self.assertIn("鸿鹏中心A栋8楼仓库", message)

    def test_render_statement_message(self):
        message = render_message("对账单")

        self.assertIn("对账提醒", message)
        self.assertIn("快递单号", message)

    def test_render_contract_message(self):
        message = render_message("双章合同")

        self.assertIn("合同归档", message)
        self.assertIn("备货", message)


if __name__ == "__main__":
    unittest.main()
