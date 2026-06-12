from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SUPPLIERS_FILE = BASE_DIR / "suppliers.json"
LOG_FILE = BASE_DIR / "purchase_workbench.log"
COMTYPES_CACHE_DIR = BASE_DIR / ".comtypes_cache"
CONFIRM_HISTORY_FILE = BASE_DIR / "confirm_history.json"
TESSDATA_DIR = BASE_DIR / "tessdata"
DEFAULT_OPEN_DIR = Path(r"D:\采购工作\采购订单")
SUPPORTED_PLATFORMS = {"wechat", "wxwork"}
PLATFORM_LABELS = {
    "微信": "wechat",
    "企业微信": "wxwork",
    "wechat": "wechat",
    "wxwork": "wxwork",
}


def load_suppliers() -> dict[str, dict[str, str]]:
    if not SUPPLIERS_FILE.exists():
        default = {"示例供应商": {"platform": "wxwork", "chat_name": "示例供应商采购沟通群"}}
        save_suppliers(default)
        print(f"已创建默认供应商配置: {SUPPLIERS_FILE}", file=sys.stderr)
        return default

    with SUPPLIERS_FILE.open("r", encoding="utf-8") as f:
        suppliers = json.load(f)

    if not isinstance(suppliers, dict):
        raise ValueError("suppliers.json 必须是对象格式")

    clean: dict[str, dict[str, str]] = {}
    changed = False
    for supplier, value in suppliers.items():
        supplier = str(supplier).strip()
        if not supplier:
            continue
        if isinstance(value, str):
            platform = value
            chat_name = ""
            delivery_type = "instrument"
            changed = True
        elif isinstance(value, dict):
            platform = value.get("platform", "")
            chat_name = value.get("chat_name", "")
            delivery_type = value.get("delivery_type", "instrument")
        else:
            print(f"警告: 供应商 {supplier} 配置格式错误，已忽略", file=sys.stderr)
            continue
        platform = normalize_platform(platform)
        if platform not in SUPPORTED_PLATFORMS:
            print(f"警告: 供应商 {supplier} 的平台 {platform} 不支持，已忽略", file=sys.stderr)
            continue
        clean[supplier] = {"platform": platform, "chat_name": str(chat_name).strip(),
                           "delivery_type": str(delivery_type).strip() or "instrument"}
    if changed:
        save_suppliers(clean)
    return clean


def save_suppliers(suppliers: dict[str, dict[str, str]]) -> None:
    ordered = {key: suppliers[key] for key in sorted(suppliers)}
    with SUPPLIERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
        f.write("\n")


def upsert_supplier(supplier: str, platform: str, chat_name: str, delivery_type: str = "instrument") -> dict[str, str]:
    supplier = supplier.strip()
    platform = normalize_platform(platform)
    chat_name = chat_name.strip()
    delivery_type = delivery_type.strip() or "instrument"
    if not supplier:
        raise ValueError("供应商不能为空")
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"不支持的平台: {platform}")
    if not chat_name:
        raise ValueError("群聊名称不能为空")

    suppliers = load_suppliers()
    suppliers[supplier] = {"platform": platform, "chat_name": chat_name, "delivery_type": delivery_type}
    save_suppliers(suppliers)
    return suppliers[supplier]


def normalize_platform(platform: str) -> str:
    return PLATFORM_LABELS.get(str(platform).strip(), str(platform).strip())
