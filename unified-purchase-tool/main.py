from __future__ import annotations

import os
import sys
from pathlib import Path

# PaddlePaddle 3.x 兼容性修复：必须在 import paddle 之前设置
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from PySide6.QtWidgets import QApplication

from unified.shell import UnifiedApp


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("AwaLife")
    app.setApplicationName("采购工作台")

    window = UnifiedApp()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
