"""월별 Claude API 비용 추적. ~/violet/data/cost.json에 누적 저장."""
import json
import os
from datetime import datetime

_COST_FILE = os.path.expanduser("~/violet/data/cost.json")


def _load() -> dict:
    if os.path.exists(_COST_FILE):
        with open(_COST_FILE) as f:
            return json.load(f)
    return {}


def _save(data: dict) -> None:
    with open(_COST_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add(amount: float) -> None:
    if not amount:
        return
    key = datetime.utcnow().strftime("%Y-%m")
    data = _load()
    data[key] = round(data.get(key, 0.0) + amount, 6)
    _save(data)


def summary() -> str:
    data = _load()
    if not data:
        return "기록된 비용이 없습니다."
    lines = []
    for month, cost in sorted(data.items(), reverse=True)[:6]:
        lines.append(f"{month}: ${cost:.4f}")
    return "\n".join(lines)
