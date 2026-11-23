"""REST-API: Rezepte, Wochenplan, Einkaufsliste, Einstellungen."""

import random
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, col, select

from . import planner
from . import settings as st
from .config import VERSION
from .db import get_session
from .foods import CATEGORIES, CATEGORY_KEYS, category_label, category_order, classify
from .importer import ImportError_, import_url
from .ingredients import merge_parts, normalize_key, parse_line, parse_lines, quantity_text
from .models import PlanEntry, Rating, Recipe, ShoppingItem
from .schemas import (
    FromPlanIn,
    GenerateIn,
    ImportIn,
    Ingredient,
    PlanEntryIn,
    PlanEntryOut,
    PlanEntryPatch,
    PlanOut,
    RatingIn,
    RecipeIn,
    RecipeOut,
    RecipePatch,
    ShoppingIn,
    ShoppingOut,
    ShoppingPatch,
)

router = APIRouter(prefix="/api")


def current_user(request: Request) -> Optional[str]:
    """HA Ingress liefert den angemeldeten Benutzer in Headern."""
    return request.headers.get("X-Remote-User-Display-Name") or request.headers.get("X-Remote-User-Name")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- Info & Einstellungen
@router.get("/info")
def info(request: Request, s: Session = Depends(get_session)):
    cfg = st.load(s)
    return {
        "version": VERSION,
        "user": current_user(request),
        "categories": [{**c, "shelf_days": st.shelf_days(cfg)[c["key"]], "default_shelf_days": c["shelf_days"]}
                       for c in CATEGORIES],
    }


@router.get("/settings")
def get_settings(s: Session = Depends(get_session)):
    return st.load(s)


@router.put("/settings")
def put_settings(body: dict[str, Any], s: Session = Depends(get_session)):
    clean: dict[str, Any] = {}
    if "persons" in body:
        clean["persons"] = max(1, min(int(body["persons"]), 20))
    if "pickup_weekday" in body:
        clean["pickup_weekday"] = int(body["pickup_weekday"]) % 7
    if "plan_days" in body:
        clean["plan_days"] = max(1, min(int(body["plan_days"]), 14))
    if "repeat_block_days" in body:
        clean["repeat_block_days"] = max(0, min(int(body["repeat_block_days"]), 90))
    for k in ("exclude_ingredients", "exclude_tags", "prefer_tags", "pantry_staples"):
        if k in body:
            v = body[k]
            items = v.split(",") if isinstance(v, str) else v
            clean[k] = [str(x).strip() for x in items or [] if str(x).strip()][:100]
    if "slots" in body and isinstance(body["slots"], list):
        clean["slots"] = [
            {"key": re.sub(r"[^a-z0-9_]", "", str(x.get("key", "")).lower())[:20] or f"slot{i}",
             "label": str(x.get("label") or "Mahlzeit")[:30], "enabled": bool(x.get("enabled"))}
            for i, x in enumerate(body["slots"][:5]) if isinstance(x, dict)
        ]
    if "shelf_days" in body and isinstance(body["shelf_days"], dict):
        clean["shelf_days"] = {k: max(0, min(int(v), 99)) for k, v in body["shelf_days"].items()
                               if k in CATEGORY_KEYS and v is not None and str(v) != ""}
    return st.save(s, clean)


# ---------------------------------------------------------------- Rezepte
def _ratings(s: Session) -> dict[str, tuple[float, int]]:
    acc: dict[str, list[int]] = {}
    for r in s.exec(select(Rating)).all():
        acc.setdefault(r.recipe_id, []).append(r.stars)
    return {k: (round(sum(v) / len(v), 2), len(v)) for k, v in acc.items()}


def _last_cooked(s: Session) -> dict[str, date]:
    out: dict[str, date] = {}
    for e in s.exec(select(PlanEntry).where(PlanEntry.cooked == True, col(PlanEntry.recipe_id).is_not(None))).all():  # noqa: E712
        if e.recipe_id and (e.recipe_id not in out or e.day > out[e.recipe_id]):
            out[e.recipe_id] = e.day
    return out


def recipe_out(r: Recipe, ratings: dict, cooked: dict, shelf: dict[str, int]) -> RecipeOut:
    avg, cnt = ratings.get(r.id, (None, 0))
    dl, cat = planner.recipe_deadline(r, shelf)
    return RecipeOut(
        **r.model_dump(exclude={"ingredients", "tags", "steps", "created_by"}),
        ingredients=[Ingredient(**i) for i in r.ingredients or []],
        tags=r.tags or [],
        steps=r.steps or [],
        rating=avg,
        rating_count=cnt,
        last_cooked=cooked.get(r.id),
        deadline_days=dl,
        deadline_category=cat,
    )


def _one_out(s: Session, r: Recipe) -> RecipeOut:
    return recipe_out(r, _ratings(s), _last_cooked(s), st.shelf_days(st.load(s)))


def _norm_ingredients(items: Optional[list[Ingredient]], text: Optional[str]) -> Optional[list[dict]]:
    if text is not None:
        return parse_lines(text)
    if items is None:
        return None
    out = []
    for i in items:
        d = i.model_dump()
        d["name"] = d["name"].strip()
        if not d["name"]:
            continue
        if d.get("category") not in CATEGORY_KEYS:
            d["category"] = classify(d["name"])
        out.append(d)
    return out


def _clean_tags(tags: list[str]) -> list[str]:
    seen, out = set(), []
    for t in tags:
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t[:30])
    return out[:20]


def get_recipe_or_404(s: Session, rid: str) -> Recipe:
    r = s.get(Recipe, rid)
    if not r:
        raise HTTPException(404, "Rezept nicht gefunden")
    return r


@router.get("/recipes", response_model=list[RecipeOut])
def list_recipes(q: Optional[str] = None, tag: Optional[str] = None, archived: bool = False,
                 s: Session = Depends(get_session)):
    rows = s.exec(select(Recipe).where(Recipe.archived == archived)).all()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in r.title.lower() or any(ql in (i.get("name") or "").lower()
                                                               for i in r.ingredients or [])
                or any(ql in t.lower() for t in r.tags or [])]
    if tag:
        rows = [r for r in rows if tag.lower() in [t.lower() for t in r.tags or []]]
    ratings, cooked, shelf = _ratings(s), _last_cooked(s), st.shelf_days(st.load(s))
    rows = sorted(rows, key=lambda r: (not r.favorite, r.title.lower()))
    return [recipe_out(r, ratings, cooked, shelf) for r in rows]


@router.post("/recipes", response_model=RecipeOut, status_code=201)
def create_recipe(body: RecipeIn, request: Request, s: Session = Depends(get_session)):
    data = body.model_dump(exclude={"ingredients", "ingredients_text", "tags", "steps"})
    r = Recipe(
        **data,
        tags=_clean_tags(body.tags),
        ingredients=_norm_ingredients(body.ingredients, body.ingredients_text) or [],
        steps=[x.strip() for x in body.steps if x.strip()],
        created_by=current_user(request),
    )
    s.add(r)
    s.commit()
    s.refresh(r)
    return _one_out(s, r)


@router.post("/recipes/import", response_model=RecipeOut, status_code=201)
async def import_recipe(body: ImportIn, request: Request, s: Session = Depends(get_session)):
    existing = s.exec(select(Recipe).where(Recipe.source_url == body.url.strip())).first()
    if existing:
        return _one_out(s, existing)
    try:
        data = await import_url(body.url)
    except ImportError_ as e:
        raise HTTPException(422, str(e)) from e
    except Exception as e:  # Netzwerkfehler usw.
        raise HTTPException(502, "Die Seite konnte nicht geladen werden") from e
    r = Recipe(**data, created_by=current_user(request))
    s.add(r)
    s.commit()
    s.refresh(r)
    return _one_out(s, r)


@router.post("/ingredients/parse")
def parse_ingredients(body: dict[str, str]):
    return parse_lines(body.get("text", ""))


@router.get("/recipes/{rid}", response_model=RecipeOut)
def get_recipe(rid: str, s: Session = Depends(get_session)):
    return _one_out(s, get_recipe_or_404(s, rid))


@router.patch("/recipes/{rid}", response_model=RecipeOut)
def patch_recipe(rid: str, body: RecipePatch, s: Session = Depends(get_session)):
    r = get_recipe_or_404(s, rid)
    data = body.model_dump(exclude_unset=True, exclude={"ingredients", "ingredients_text", "tags", "steps"})
    for k, v in data.items():
        setattr(r, k, v)
    if "tags" in body.model_fields_set and body.tags is not None:
        r.tags = _clean_tags(body.tags)
    if "steps" in body.model_fields_set and body.steps is not None:
        r.steps = [x.strip() for x in body.steps if x.strip()]
    ing = _norm_ingredients(body.ingredients, body.ingredients_text)
    if ing is not None:
        if body.ingredients_text is not None:
            # Von Hand geänderte Kategorien beim Bearbeiten als Text nicht verlieren
            manual = {normalize_key(i.get("name") or ""): i.get("category") for i in r.ingredients or []
                      if i.get("category") and i.get("category") != classify(i.get("name") or "")}
            for i in ing:
                k = normalize_key(i["name"])
                if k in manual:
                    i["category"] = manual[k]
        r.ingredients = ing
    r.updated_at = _now()
    s.add(r)
    s.commit()
    s.refresh(r)
    return _one_out(s, r)


@router.delete("/recipes/{rid}", status_code=204)
def delete_recipe(rid: str, s: Session = Depends(get_session)):
    r = get_recipe_or_404(s, rid)
    for e in s.exec(select(PlanEntry).where(PlanEntry.recipe_id == rid)).all():
        if e.day >= date.today() and not e.cooked:
            s.delete(e)
        else:  # Vergangenheit behalten, Titel merken
            e.title, e.recipe_id = r.title, None
            s.add(e)
    for x in s.exec(select(Rating).where(Rating.recipe_id == rid)).all():
        s.delete(x)
    s.delete(r)
    s.commit()


@router.post("/recipes/{rid}/ratings", response_model=RecipeOut)
def rate_recipe(rid: str, body: RatingIn, request: Request, s: Session = Depends(get_session)):
    r = get_recipe_or_404(s, rid)
    s.add(Rating(recipe_id=rid, stars=body.stars, comment=body.comment, by=current_user(request)))
    s.commit()
    return _one_out(s, r)


@router.get("/tags")
def list_tags(s: Session = Depends(get_session)):
    counts: dict[str, int] = {}
    for r in s.exec(select(Recipe).where(Recipe.archived == False)).all():  # noqa: E712
        for t in r.tags or []:
            counts[t] = counts.get(t, 0) + 1
    return [{"tag": t, "count": c} for t, c in sorted(counts.items(), key=lambda x: (-x[1], x[0].lower()))]


# ---------------------------------------------------------------- Wochenplan
def _entry_out(e: PlanEntry, recipes: dict[str, Recipe]) -> PlanEntryOut:
    r = recipes.get(e.recipe_id or "")
    return PlanEntryOut(
        **e.model_dump(exclude={"created_at"}),
        recipe_title=r.title if r else None,
        recipe_image=r.image_url if r else None,
        recipe_minutes=(r.total_minutes or r.prep_minutes) if r else None,
    )


def _entries(s: Session, start: date, days: int) -> list[PlanEntry]:
    end = start + timedelta(days=days - 1)
    return list(s.exec(select(PlanEntry).where(PlanEntry.day >= start, PlanEntry.day <= end)).all())


def _recipe_map(s: Session) -> dict[str, Recipe]:
    return {r.id: r for r in s.exec(select(Recipe)).all()}


def _slot_order(cfg: dict) -> dict[str, int]:
    return {x["key"]: i for i, x in enumerate(cfg.get("slots") or [])}


@router.get("/plan", response_model=PlanOut)
def get_plan(start: Optional[date] = None, days: Optional[int] = None, s: Session = Depends(get_session)):
    cfg = st.load(s)
    start = start or st.pickup_on_or_before(date.today(), int(cfg["pickup_weekday"]))
    days = max(1, min(days or int(cfg["plan_days"]), 21))
    entries = _entries(s, start, days)
    recipes = _recipe_map(s)
    order = _slot_order(cfg)
    entries.sort(key=lambda e: (e.day, order.get(e.slot, 99), e.created_at))
    return PlanOut(
        start=start,
        days=days,
        pickup_weekday=int(cfg["pickup_weekday"]),
        slots=st.enabled_slots(cfg),
        entries=[_entry_out(e, recipes) for e in entries],
        warnings=planner.check(entries, recipes, cfg),
    )


@router.post("/plan/entries", response_model=PlanEntryOut, status_code=201)
def add_entry(body: PlanEntryIn, s: Session = Depends(get_session)):
    if not body.recipe_id and not (body.title or "").strip():
        raise HTTPException(422, "Rezept oder Titel angeben")
    if body.recipe_id:
        get_recipe_or_404(s, body.recipe_id)
    cfg = st.load(s)
    e = PlanEntry(day=body.day, slot=body.slot, recipe_id=body.recipe_id,
                  title=(body.title or "").strip() or None, servings=body.servings or int(cfg["persons"]),
                  note=body.note)
    s.add(e)
    s.commit()
    s.refresh(e)
    return _entry_out(e, _recipe_map(s))


def get_entry_or_404(s: Session, eid: str) -> PlanEntry:
    e = s.get(PlanEntry, eid)
    if not e:
        raise HTTPException(404, "Eintrag nicht gefunden")
    return e


@router.patch("/plan/entries/{eid}", response_model=PlanEntryOut)
def patch_entry(eid: str, body: PlanEntryPatch, s: Session = Depends(get_session)):
    e = get_entry_or_404(s, eid)
    data = body.model_dump(exclude_unset=True)
    if data.get("recipe_id"):
        get_recipe_or_404(s, data["recipe_id"])
    for k, v in data.items():
        setattr(e, k, v)
    s.add(e)
    s.commit()
    s.refresh(e)
    return _entry_out(e, _recipe_map(s))


@router.delete("/plan/entries/{eid}", status_code=204)
def delete_entry(eid: str, s: Session = Depends(get_session)):
    s.delete(get_entry_or_404(s, eid))
    s.commit()


def _context(s: Session, cfg: dict, start: date) -> planner.Context:
    block = int(cfg.get("repeat_block_days") or 0)
    recent = {e.recipe_id for e in s.exec(select(PlanEntry).where(
        PlanEntry.day >= start - timedelta(days=block), PlanEntry.day < start)).all() if e.recipe_id}
    return planner.Context(cfg=cfg, shelf=st.shelf_days(cfg),
                           ratings={k: v[0] for k, v in _ratings(s).items()}, recent=recent)


@router.post("/plan/generate", response_model=PlanOut)
def generate(body: GenerateIn, s: Session = Depends(get_session)):
    cfg = st.load(s)
    start = body.start or st.next_pickup(date.today(), int(cfg["pickup_weekday"]))
    days = body.days or int(cfg["plan_days"])
    existing = _entries(s, start, days)
    if body.replace:
        for e in existing:
            if e.recipe_id and not e.cooked and e.day >= date.today():
                s.delete(e)
        s.commit()
        existing = _entries(s, start, days)
    occupied = {(e.day, e.slot) for e in existing}
    keys = [x["key"] for x in st.enabled_slots(cfg)]
    open_slots = [sl for sl in planner.make_slots(start, days, keys, cfg)
                  if (sl.day, sl.slot) not in occupied and sl.day >= date.today()]
    recipes = [r for r in s.exec(select(Recipe).where(Recipe.archived == False)).all()]  # noqa: E712
    taken = {e.recipe_id for e in existing if e.recipe_id}
    for ch in planner.fill(open_slots, recipes, _context(s, cfg, start), taken):
        s.add(PlanEntry(day=ch.slot.day, slot=ch.slot.slot, recipe_id=ch.recipe.id, servings=int(cfg["persons"])))
    s.commit()
    return get_plan(start, days, s)


@router.post("/plan/entries/{eid}/swap", response_model=PlanEntryOut)
def swap_entry(eid: str, s: Session = Depends(get_session)):
    """Würfelt ein einzelnes Gericht neu (unter Beachtung der Haltbarkeit an diesem Tag)."""
    e = get_entry_or_404(s, eid)
    cfg = st.load(s)
    wd = int(cfg["pickup_weekday"])
    pickup = st.pickup_on_or_before(e.day, wd)
    offset = (e.day - pickup).days
    ctx = _context(s, cfg, pickup)
    window = _entries(s, pickup, 7)
    taken = {x.recipe_id for x in window if x.recipe_id}
    if e.recipe_id:
        taken.add(e.recipe_id)
    mains = [planner.recipe_main(r) for r in (s.get(Recipe, x.recipe_id) for x in window
                                               if x.recipe_id and x.id != e.id) if r]
    recipes = list(s.exec(select(Recipe).where(Recipe.archived == False)).all())  # noqa: E712
    pool = [(r, planner.weight(r, ctx, mains)) for r in planner.candidates(recipes, ctx, taken)
            if planner.recipe_deadline(r, ctx.shelf)[0] >= offset]
    if not pool:
        raise HTTPException(409, "Kein passendes anderes Rezept gefunden")
    r = random.choices([p[0] for p in pool], weights=[p[1] for p in pool])[0]
    e.recipe_id, e.title = r.id, None
    s.add(e)
    s.commit()
    s.refresh(e)
    return _entry_out(e, _recipe_map(s))


# ---------------------------------------------------------------- Einkaufsliste
def _shop_out(i: ShoppingItem) -> ShoppingOut:
    return ShoppingOut(
        id=i.id, name=i.name, quantity=quantity_text(i.parts or []), parts=i.parts or [],
        category=i.category, category_label=category_label(i.category), checked=i.checked, auto=i.auto,
        sources=i.sources or [], note=i.note, added_by=i.added_by,
    )


def _list_items(s: Session) -> list[ShoppingOut]:
    order = category_order()
    rows = s.exec(select(ShoppingItem)).all()
    rows = sorted(rows, key=lambda i: (i.checked, order.get(i.category, 99), i.name.lower()))
    return [_shop_out(i) for i in rows]


def _is_staple(name: str, staples: list[str]) -> bool:
    keys = {normalize_key(x) for x in staples}
    parts = [p for p in re.split(r"\s+und\s+|\s*&\s*|\s*,\s*|\s*/\s*", name) if p.strip()]
    return bool(parts) and all(normalize_key(p) in keys for p in parts)


def add_item(s: Session, name: str, parts: list[dict], *, note: Optional[str] = None,
             category: Optional[str] = None, auto: bool = False, sources: Optional[list[str]] = None,
             user: Optional[str] = None) -> ShoppingItem:
    key = normalize_key(name)
    existing = s.exec(select(ShoppingItem).where(ShoppingItem.key == key, ShoppingItem.checked == False,  # noqa: E712
                                                 ShoppingItem.auto == auto)).first()
    if existing:
        existing.parts = merge_parts((existing.parts or []) + parts)
        existing.sources = sorted(set(existing.sources or []) | set(sources or []))
        if note and note not in (existing.note or ""):
            existing.note = f"{existing.note}; {note}" if existing.note else note
        s.add(existing)
        return existing
    item = ShoppingItem(name=name, key=key, parts=merge_parts(parts), category=category or classify(name),
                        auto=auto, sources=sorted(set(sources or [])), note=note, added_by=user)
    s.add(item)
    return item


@router.get("/shopping", response_model=list[ShoppingOut])
def get_shopping(s: Session = Depends(get_session)):
    return _list_items(s)


@router.post("/shopping", response_model=list[ShoppingOut], status_code=201)
def add_shopping(body: ShoppingIn, request: Request, s: Session = Depends(get_session)):
    """Fügt einen oder mehrere Artikel hinzu. `text` darf mehrere Zeilen oder Kommas enthalten."""
    user = current_user(request)
    if body.text:
        lines = [x for x in re.split(r"\n|;", body.text) if x.strip()]
        for line in lines:
            p = parse_line(line)
            if p:
                add_item(s, p["name"], [{"amount": p["amount"], "unit": p["unit"]}], note=p["note"],
                         category=p["category"], user=user)
    elif body.name and body.name.strip():
        add_item(s, body.name.strip(), [{"amount": body.amount, "unit": body.unit}], note=body.note, user=user)
    else:
        raise HTTPException(422, "Artikel angeben")
    s.commit()
    return _list_items(s)


def get_item_or_404(s: Session, iid: str) -> ShoppingItem:
    i = s.get(ShoppingItem, iid)
    if not i:
        raise HTTPException(404, "Artikel nicht gefunden")
    return i


@router.patch("/shopping/{iid}", response_model=ShoppingOut)
def patch_shopping(iid: str, body: ShoppingPatch, s: Session = Depends(get_session)):
    i = get_item_or_404(s, iid)
    if body.checked is not None:
        i.checked = body.checked
        i.checked_at = _now() if body.checked else None
    if body.name is not None and body.name.strip():
        i.name = body.name.strip()
        i.key = normalize_key(i.name)
    if body.quantity is not None:
        p = parse_line(f"{body.quantity} x") if body.quantity.strip() else None
        i.parts = [{"amount": p["amount"], "unit": p["unit"]}] if p else []
    if body.note is not None:
        i.note = body.note or None
    if body.category in CATEGORY_KEYS:
        i.category = body.category
    s.add(i)
    s.commit()
    s.refresh(i)
    return _shop_out(i)


@router.delete("/shopping/{iid}", status_code=204)
def delete_shopping(iid: str, s: Session = Depends(get_session)):
    s.delete(get_item_or_404(s, iid))
    s.commit()


@router.post("/shopping/clear-checked", response_model=list[ShoppingOut])
def clear_checked(s: Session = Depends(get_session)):
    for i in s.exec(select(ShoppingItem).where(ShoppingItem.checked == True)).all():  # noqa: E712
        s.delete(i)
    s.commit()
    return _list_items(s)


@router.post("/shopping/from-plan", response_model=list[ShoppingOut])
def shopping_from_plan(body: FromPlanIn, s: Session = Depends(get_session)):
    """Erzeugt die Zutaten aus dem Wochenplan neu. Selbst hinzugefügte Artikel bleiben erhalten."""
    cfg = st.load(s)
    for i in s.exec(select(ShoppingItem).where(ShoppingItem.auto == True)).all():  # noqa: E712
        s.delete(i)
    s.flush()
    recipes = _recipe_map(s)
    staples = cfg.get("pantry_staples") or []
    for e in _entries(s, body.start, body.days):
        r = recipes.get(e.recipe_id or "")
        if not r or e.cooked:
            continue
        factor = (e.servings or r.servings) / max(r.servings or 1, 1)
        for ing in r.ingredients or []:
            name = ing.get("name") or ""
            if not name or _is_staple(name, staples):
                continue
            amt = ing.get("amount")
            add_item(s, name, [{"amount": round(amt * factor, 3) if amt is not None else None, "unit": ing.get("unit")}],
                     category=ing.get("category"), auto=True, sources=[r.title])
            s.flush()
    s.commit()
    return _list_items(s)
