from __future__ import annotations

import sys
from pathlib import Path

# 让统一壳的 unified 模块能被找到
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "unified-purchase-tool"))

from gui.app import run


if __name__ == "__main__":
    raise SystemExit(run())
