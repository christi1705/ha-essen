"""Planungsalgorithmus: wählt Gerichte für freie Plätze und beachtet die Haltbarkeit.

Grundidee: Jedes Rezept hat eine Frist = die kürzeste Haltbarkeit seiner Zutaten
(Tage nach der Abholung). Ein Rezept darf nur an einem Tag liegen, der höchstens so
viele Tage nach der letzten Abholung liegt. Verderbliches kommt also früh in die Woche.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from .foods import NEVER, PROTEIN_CATEGORIES, category_label
from .models import PlanEntry, Recipe
from .settings import pickup_on_or_before, shelf_days


@dataclass
class Slot:
    day: date
    slot: str
    offset: int  # Tage seit der letzten Abholung
    pickup: date


@dataclass
class Choice:
    slot: Slot
    recipe: Recipe


@dataclass
class Context:
    cfg: dict
    shelf: dict[str, int]
    ratings: dict[str, float] = field(default_factory=dict)
    recent: set[str] = field(default_factory=set)  # kürzlich gekochte Rezept-IDs


def recipe_deadline(r: Recipe, shelf: dict[str, int]) -> tuple[int, Optional[str]]:
    """Kürzeste Haltbarkeit aller Zutaten und die Kategorie, die sie bestimmt."""
    best, cat = NEVER, None
    for ing in r.ingredients or []:
        c = ing.get("category") or "sonstiges"
        d = shelf.get(c, NEVER)
        if d < best:
            best, cat = d, c
    return best, cat


def recipe_main(r: Recipe) -> Optional[str]:
    cats = {(i.get("category") or "") for i in r.ingredients or []}
    for c in PROTEIN_CATEGORIES:
        if c in cats:
            return c
    return None


def _excluded(r: Recipe, cfg: dict) -> bool:
    words = [w.strip().lower() for w in cfg.get("exclude_ingredients") or [] if w.strip()]
    if words:
        for ing in r.ingredients or []:
            n = (ing.get("name") or "").lower()
            if any(w in n for w in words):
                return True
    ex_tags = {t.strip().lower() for t in cfg.get("exclude_tags") or [] if t.strip()}
    return bool(ex_tags & {t.lower() for t in r.tags or []})


def weight(r: Recipe, ctx: Context, chosen_mains: list[Optional[str]]) -> float:
    w = 1.0
    avg = ctx.ratings.get(r.id)
    if avg is not None:
        w *= 0.3 + avg / 4  # 1 Stern ≈ 0.55, 5 Sterne ≈ 1.55
    if r.favorite:
        w *= 1.6
    prefer = {t.strip().lower() for t in ctx.cfg.get("prefer_tags") or [] if t.strip()}
    if prefer & {t.lower() for t in r.tags or []}:
        w *= 1.6
    if r.id in ctx.recent:
        w *= 0.05
    main = recipe_main(r)
    if main:
        w *= 0.35 ** chosen_mains.count(main)  # Abwechslung: nicht dreimal Hähnchen
    return w


def _hall_ok(deadlines: list[int], offsets: list[int]) -> bool:
    """Lassen sich alle Rezepte (Fristen) auf Plätze (Abstände zur Abholung) verteilen?"""
    for d in set(deadlines):
        if sum(1 for x in deadlines if x <= d) > sum(1 for o in offsets if o <= d):
            return False
    return True


def candidates(recipes: list[Recipe], ctx: Context, exclude_ids: set[str]) -> list[Recipe]:
    return [r for r in recipes if not r.archived and r.id not in exclude_ids and not _excluded(r, ctx.cfg)]


def fill(slots: list[Slot], recipes: list[Recipe], ctx: Context, taken: set[str],
         rng: Optional[random.Random] = None) -> list[Choice]:
    """Füllt freie Plätze. `taken` = Rezepte, die im Zeitraum schon eingeplant sind."""
    rng = rng or random.Random()
    out: list[Choice] = []
    by_pickup: dict[date, list[Slot]] = {}
    for sl in slots:
        by_pickup.setdefault(sl.pickup, []).append(sl)
    used = set(taken)
    mains: list[Optional[str]] = []
    for pickup in sorted(by_pickup):
        group = sorted(by_pickup[pickup], key=lambda x: (x.day, x.slot))
        offsets = [g.offset for g in group]
        chosen: list[Recipe] = []
        for _ in group:
            pool = []
            for r in candidates(recipes, ctx, used):
                dl, _cat = recipe_deadline(r, ctx.shelf)
                if not _hall_ok([recipe_deadline(c, ctx.shelf)[0] for c in chosen] + [dl], offsets):
                    continue
                pool.append((r, weight(r, ctx, mains)))
            if not pool:
                break
            total = sum(w for _, w in pool)
            pick = rng.uniform(0, total)
            acc = 0.0
            sel = pool[-1][0]
            for r, w in pool:
                acc += w
                if acc >= pick:
                    sel = r
                    break
            chosen.append(sel)
            used.add(sel.id)
            mains.append(recipe_main(sel))
        # Verteilen: Verderbliches zuerst (frühester Ablauf), Haltbares in zufälliger Reihenfolge
        keyed = [(recipe_deadline(r, ctx.shelf)[0], rng.random(), r) for r in chosen]
        keyed.sort(key=lambda x: (x[0] if x[0] < NEVER else NEVER, x[1]))
        for sl, (_, _, r) in zip(group, keyed):
            out.append(Choice(sl, r))
    return out


def make_slots(start: date, days: int, slot_keys: list[str], cfg: dict) -> list[Slot]:
    wd = int(cfg.get("pickup_weekday", 5))
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        p = pickup_on_or_before(d, wd)
        for k in slot_keys:
            out.append(Slot(day=d, slot=k, offset=(d - p).days, pickup=p))
    return out


WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def check(entries: list[PlanEntry], recipes: dict[str, Recipe], cfg: dict) -> list[dict]:
    """Warnt, wenn ein Gericht zu spät nach der Abholung eingeplant ist."""
    shelf = shelf_days(cfg)
    wd = int(cfg.get("pickup_weekday", 5))
    out = []
    for e in entries:
        r = recipes.get(e.recipe_id or "")
        if not r or e.cooked:
            continue
        dl, cat = recipe_deadline(r, shelf)
        offset = (e.day - pickup_on_or_before(e.day, wd)).days
        if cat and offset > dl:
            when = "am Abholtag" if dl == 0 else f"bis Tag {dl} nach der Abholung"
            out.append({
                "entry_id": e.id,
                "day": e.day.isoformat(),
                "message": f"{r.title} ({WEEKDAYS[e.day.weekday()]}): {category_label(cat)} sollte {when} "
                           f"verbraucht werden, liegt aber an Tag {offset}.",
            })
    return out
