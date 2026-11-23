"""Einstellungen (in der App änderbar, in der Datenbank gespeichert)."""

import copy
from datetime import date, timedelta
from typing import Any

from sqlmodel import Session

from .foods import DEFAULT_SHELF
from .models import Setting

DEFAULTS: dict[str, Any] = {
    "persons": 2,
    "slots": [
        {"key": "mittag", "label": "Mittagessen", "enabled": False},
        {"key": "abend", "label": "Abendessen", "enabled": True},
    ],
    "pickup_weekday": 5,  # 0 = Montag … 5 = Samstag
    "plan_days": 7,
    "exclude_ingredients": [],
    "exclude_tags": [],
    "prefer_tags": [],
    "repeat_block_days": 14,
    "pantry_staples": ["Salz", "Pfeffer", "Wasser", "Öl", "Olivenöl", "Zucker"],
    "shelf_days": {},  # Abweichungen von foods.DEFAULT_SHELF
}

_KEY = "app"


def load(s: Session) -> dict[str, Any]:
    row = s.get(Setting, _KEY)
    merged = copy.deepcopy(DEFAULTS)
    if row and isinstance(row.value, dict):
        merged.update({k: v for k, v in row.value.items() if k in DEFAULTS})
    return merged


def save(s: Session, values: dict[str, Any]) -> dict[str, Any]:
    current = load(s)
    current.update({k: v for k, v in values.items() if k in DEFAULTS})
    row = s.get(Setting, _KEY)
    if row:
        row.value = current
    else:
        row = Setting(key=_KEY, value=current)
    s.add(row)
    s.commit()
    return current


def shelf_days(cfg: dict[str, Any]) -> dict[str, int]:
    out = dict(DEFAULT_SHELF)
    for k, v in (cfg.get("shelf_days") or {}).items():
        if k in out and isinstance(v, (int, float)):
            out[k] = int(v)
    return out


def enabled_slots(cfg: dict[str, Any]) -> list[dict]:
    slots = [x for x in cfg.get("slots") or [] if x.get("enabled")]
    return slots or [{"key": "abend", "label": "Abendessen", "enabled": True}]


def pickup_on_or_before(d: date, weekday: int) -> date:
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def next_pickup(today: date, weekday: int) -> date:
    return today + timedelta(days=(weekday - today.weekday()) % 7)
