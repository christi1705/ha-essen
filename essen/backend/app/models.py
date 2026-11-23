"""Datenmodell: Rezepte, Bewertungen, Wochenplan, Einkaufsliste, Einstellungen."""

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Recipe(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    title: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    servings: int = 2
    prep_minutes: Optional[int] = None
    total_minutes: Optional[int] = None
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    # [{amount, unit, name, note, category}]
    ingredients: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    steps: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    notes: Optional[str] = None
    favorite: bool = False
    archived: bool = False
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Rating(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    recipe_id: str = Field(index=True)
    stars: int
    comment: Optional[str] = None
    by: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class PlanEntry(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    day: date = Field(index=True)
    slot: str = "abend"
    recipe_id: Optional[str] = Field(default=None, index=True)
    title: Optional[str] = None  # freier Eintrag ohne Rezept (z. B. "Reste", "Essen gehen")
    servings: int = 2
    note: Optional[str] = None
    cooked: bool = False
    created_at: datetime = Field(default_factory=_now)


class ShoppingItem(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str
    key: str = Field(index=True)
    # [{amount, unit}] – Mengen in Basiseinheiten, bereits zusammengefasst
    parts: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    category: str = "sonstiges"
    checked: bool = False
    auto: bool = False  # aus dem Wochenplan erzeugt
    sources: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    note: Optional[str] = None
    added_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    checked_at: Optional[datetime] = None


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: Any = Field(default=None, sa_column=Column(JSON))
