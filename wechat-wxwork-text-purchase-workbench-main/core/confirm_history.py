from __future__ import annotations

import json
from pathlib import Path

from core.config import CONFIRM_HISTORY_FILE

REQUIRED_CONFIRMATIONS = 3


def _key(supplier: str, platform: str, chat_name: str) -> str:
    return "\n".join((supplier.strip(), platform.strip(), chat_name.strip()))


def load_history(path: Path = CONFIRM_HISTORY_FILE) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    return data


def save_history(history: dict[str, dict[str, object]], path: Path = CONFIRM_HISTORY_FILE) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_confirmation_count(
    supplier: str,
    platform: str,
    chat_name: str,
    path: Path = CONFIRM_HISTORY_FILE,
) -> int:
    history = load_history(path)
    record = history.get(_key(supplier, platform, chat_name), {})
    try:
        return int(record.get("count", 0))
    except (TypeError, ValueError):
        return 0


def needs_confirmation(
    supplier: str,
    platform: str,
    chat_name: str,
    path: Path = CONFIRM_HISTORY_FILE,
) -> bool:
    return get_confirmation_count(supplier, platform, chat_name, path) < REQUIRED_CONFIRMATIONS


def record_confirmation(
    supplier: str,
    platform: str,
    chat_name: str,
    path: Path = CONFIRM_HISTORY_FILE,
) -> int:
    history = load_history(path)
    key = _key(supplier, platform, chat_name)
    count = get_confirmation_count(supplier, platform, chat_name, path) + 1
    history[key] = {
        "supplier": supplier.strip(),
        "platform": platform.strip(),
        "chat_name": chat_name.strip(),
        "count": min(count, REQUIRED_CONFIRMATIONS),
    }
    save_history(history, path)
    return min(count, REQUIRED_CONFIRMATIONS)
