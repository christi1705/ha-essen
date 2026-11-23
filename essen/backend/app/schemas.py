from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    amount: Optional[float] = None
    unit: Optional[str] = None
    name: str
    note: Optional[str] = None
    category: Optional[str] = None


class RecipeIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    servings: int = Field(default=2, ge=1, le=50)
    prep_minutes: Optional[int] = Field(default=None, ge=0)
    total_minutes: Optional[int] = Field(default=None, ge=0)
    tags: list[str] = []
    ingredients: Optional[list[Ingredient]] = None
    # Alternativ: Zutaten als Text, eine pro Zeile ("200 g Hackfleisch")
    ingredients_text: Optional[str] = None
    steps: list[str] = []
    notes: Optional[str] = None
    favorite: bool = False


class RecipePatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    servings: Optional[int] = Field(default=None, ge=1, le=50)
    prep_minutes: Optional[int] = None
    total_minutes: Optional[int] = None
    tags: Optional[list[str]] = None
    ingredients: Optional[list[Ingredient]] = None
    ingredients_text: Optional[str] = None
    steps: Optional[list[str]] = None
    notes: Optional[str] = None
    favorite: Optional[bool] = None
    archived: Optional[bool] = None


class RecipeOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    source_url: Optional[str]
    image_url: Optional[str]
    servings: int
    prep_minutes: Optional[int]
    total_minutes: Optional[int]
    tags: list[str]
    ingredients: list[Ingredient]
    steps: list[str]
    notes: Optional[str]
    favorite: bool
    archived: bool
    rating: Optional[float] = None
    rating_count: int = 0
    last_cooked: Optional[date] = None
    deadline_days: int = 99
    deadline_category: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ImportIn(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


class RatingIn(BaseModel):
    stars: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class PlanEntryIn(BaseModel):
    day: date
    slot: str = "abend"
    recipe_id: Optional[str] = None
    title: Optional[str] = None
    servings: Optional[int] = Field(default=None, ge=1, le=50)
    note: Optional[str] = None


class PlanEntryPatch(BaseModel):
    day: Optional[date] = None
    slot: Optional[str] = None
    recipe_id: Optional[str] = None
    title: Optional[str] = None
    servings: Optional[int] = Field(default=None, ge=1, le=50)
    note: Optional[str] = None
    cooked: Optional[bool] = None


class PlanEntryOut(BaseModel):
    id: str
    day: date
    slot: str
    recipe_id: Optional[str]
    title: Optional[str]
    servings: int
    note: Optional[str]
    cooked: bool
    recipe_title: Optional[str] = None
    recipe_image: Optional[str] = None
    recipe_minutes: Optional[int] = None


class PlanOut(BaseModel):
    start: date
    days: int
    pickup_weekday: int
    slots: list[dict]
    entries: list[PlanEntryOut]
    warnings: list[dict]


class GenerateIn(BaseModel):
    start: Optional[date] = None
    days: Optional[int] = Field(default=None, ge=1, le=21)
    replace: bool = False  # True = auch bestehende (nicht gekochte) Einträge neu würfeln


class ShoppingIn(BaseModel):
    # Entweder freier Text ("500 g Hackfleisch") oder strukturiert
    text: Optional[str] = None
    name: Optional[str] = None
    amount: Optional[float] = None
    unit: Optional[str] = None
    note: Optional[str] = None


class ShoppingPatch(BaseModel):
    checked: Optional[bool] = None
    name: Optional[str] = None
    quantity: Optional[str] = None  # z. B. "2 Stück" – wird neu eingelesen
    note: Optional[str] = None
    category: Optional[str] = None


class ShoppingOut(BaseModel):
    id: str
    name: str
    quantity: str
    parts: list[dict]
    category: str
    category_label: str
    checked: bool
    auto: bool
    sources: list[str]
    note: Optional[str]
    added_by: Optional[str]


class FromPlanIn(BaseModel):
    start: date
    days: int = Field(default=7, ge=1, le=21)
