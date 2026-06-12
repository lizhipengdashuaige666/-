from __future__ import annotations

import os
from pathlib import Path

from core.config import COMTYPES_CACHE_DIR


def prepare_uiautomation_cache(cache_dir: Path = COMTYPES_CACHE_DIR) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    resolved = str(cache_dir.resolve())
    os.environ["COMTYPES_CACHE_DIR"] = resolved

    import comtypes.client
    import comtypes.gen

    comtypes.gen.__path__ = [resolved]
    comtypes.client.gen_dir = resolved


def import_uiautomation():
    prepare_uiautomation_cache()

    import uiautomation as auto

    auto.SetGlobalSearchTimeout(1.0)
    return auto
