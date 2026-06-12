import os
import sys

# PaddlePaddle 3.3 兼容性修复：必须在 import paddle 之前设置
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from pathlib import Path

# 让本项目和 unified 模块都能被找到
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "unified-purchase-tool"))

from app.config import load_config
from app.gui import ContractRenameApp


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    config = load_config(base_dir)
    app = ContractRenameApp(config)
    app.run()


if __name__ == "__main__":
    main()
