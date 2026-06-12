from __future__ import annotations

import json
from pathlib import Path

from core.config import BASE_DIR

TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATE_VARS_FILE = BASE_DIR / "config" / "template_vars.json"

DEFAULT_TEMPLATE_VARS = {
    "receiver_name": "杨国祖",
    "receiver_phone": "15361444520",
    "delivery_address": {
        "instrument": "广东省深圳市宝安区西乡街道铁岗社区益成工业园A栋5楼503号 安侣医学科技有限公司",
        "reagent": "广东省深圳市宝安区西乡街道 鸿鹏中心A栋8楼仓库（请勿放快递柜）",
    },
}

DEFAULT_TEMPLATES = {
    "PO.txt": """您好，以下为最新采购订单，请查收。

烦请确认订单内容，盖章回传，并安排发货。

收货信息：

{{receiver_name}}
{{receiver_phone}}

{{delivery_address}}

谢谢。""",
    "reconciliation.txt": """【对账提醒】各位麻烦留意一下本月对账及寄件要求：

需要的单据：盖章A4对账单 + 送货单明细（内容要和账单对得上）+ A5发票。发票上的开票明细每张不能超过5项，且和账单一致。如果当月明细超过5项，请拆成多张发票（每张≤5项），实在拆不了的提前和我说一声。三样对账单据缺一不可，若缺少其中某一项整体的对账付款都会延期。

所有单据整理好，在本月15日前寄到：深圳市宝安区西乡街道鸿鹏中心A栋13楼蓝色货架，李志鹏 17520245946。千万别放快递柜，一定送到货架上。如果15号前寄不出来，也请提前在群里说一声预计哪天寄。

寄出后群里说一声快递单号就行，谢谢配合。""",
    "contract_archive.txt": """【合同归档&备货提醒】各位，盖好双章的合同电子档发在群里了，双方各存一份用于归档。

另外请按合同里的需求物料清单，抓紧完成备货。如交期、缺货等问题请及时在群里反馈。

收到请回复，谢谢。""",
    "file.txt": """您好，相关采购文件已发群里，请查收。谢谢。""",
}


def ensure_default_templates() -> None:
    TEMPLATES_DIR.mkdir(exist_ok=True)
    TEMPLATE_VARS_FILE.parent.mkdir(exist_ok=True)

    for name, content in DEFAULT_TEMPLATES.items():
        path = TEMPLATES_DIR / name
        if not path.exists():
            path.write_text(content, encoding="utf-8")

    if not TEMPLATE_VARS_FILE.exists():
        TEMPLATE_VARS_FILE.write_text(
            json.dumps(DEFAULT_TEMPLATE_VARS, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def render_message(business_type: str | None, delivery_type: str = "instrument") -> str:
    ensure_default_templates()
    template_name = _template_name(business_type)
    template = (TEMPLATES_DIR / template_name).read_text(encoding="utf-8")
    variables = _load_template_vars()

    address_map = variables.get("delivery_address", {})
    values = {
        "receiver_name": str(variables.get("receiver_name", "")),
        "receiver_phone": str(variables.get("receiver_phone", "")),
        "delivery_address": str(address_map.get(delivery_type) or address_map.get("instrument") or ""),
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template.strip()


def _template_name(business_type: str | None) -> str:
    text = (business_type or "").lower()
    if text == "po" or "订单" in text:
        return "PO.txt"
    if "对账" in text:
        return "reconciliation.txt"
    if "合同" in text:
        return "contract_archive.txt"
    return "file.txt"


def _load_template_vars() -> dict[str, object]:
    try:
        data = json.loads(TEMPLATE_VARS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else DEFAULT_TEMPLATE_VARS
    except Exception:
        return DEFAULT_TEMPLATE_VARS
