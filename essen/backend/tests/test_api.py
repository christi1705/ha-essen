import os
import tempfile
from datetime import date, timedelta

os.environ["ESSEN_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ESSEN_ALLOW_ALL"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import importer  # noqa: E402
from app.main import app  # noqa: E402

RECIPES = [
    ("Spaghetti Bolognese", "500 g Hackfleisch\n1 Zwiebel\n1 Dose Tomaten\n400 g Spaghetti\nSalz und Pfeffer", ["Pasta"]),
    ("Hähnchen-Curry", "400 g Hähnchenbrust\n400 ml Kokosmilch\n1 Paprika\n200 g Reis", ["Asiatisch"]),
    ("Lachs mit Spinat", "2 Lachsfilets\n300 g Spinat\n500 g Kartoffeln", ["Fisch"]),
    ("Linsensuppe", "250 g Linsen\n2 Karotten\n1 Zwiebel\n1 l Gemüsebrühe", ["Vegetarisch"]),
    ("Ofenkartoffeln mit Quark", "1 kg Kartoffeln\n250 g Quark\n1 Bund Schnittlauch", ["Vegetarisch"]),
    ("Pasta Aglio e Olio", "400 g Spaghetti\n4 Zehen Knoblauch\n1 Chili\n6 EL Olivenöl", ["Pasta", "Schnell"]),
    ("Chili sin Carne", "2 Dosen Kidneybohnen\n1 Dose Mais\n1 Dose Tomaten\n2 Zwiebeln", ["Vegetarisch"]),
    ("Rindergulasch", "800 g Rindfleisch\n3 Zwiebeln\n2 EL Paprikapulver", ["Deftig"]),
    ("Gemüsepfanne", "1 Zucchini\n2 Paprika\n200 g Champignons\n200 g Reis", ["Vegetarisch"]),
]


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        for title, ing, tags in RECIPES:
            r = client.post("/api/recipes", json={"title": title, "servings": 2, "ingredients_text": ing, "tags": tags})
            assert r.status_code == 201, r.text
        yield client


def test_recipe_parsing(c):
    rs = c.get("/api/recipes").json()
    bolo = next(r for r in rs if r["title"] == "Spaghetti Bolognese")
    assert bolo["ingredients"][0] == {"amount": 500, "unit": "g", "name": "Hackfleisch", "note": None, "category": "hack"}
    assert bolo["deadline_days"] == 0 and bolo["deadline_category"] == "hack"
    curry = next(r for r in rs if r["title"] == "Hähnchen-Curry")
    assert curry["deadline_days"] == 1


def test_generate_respects_shelf_life(c):
    c.put("/api/settings", json={"pickup_weekday": date.today().weekday(), "repeat_block_days": 0})
    start = date.today()
    for _ in range(15):
        plan = c.post("/api/plan/generate", json={"start": start.isoformat(), "days": 7, "replace": True}).json()
        # Mit diesen 9 Rezepten passen höchstens 6 in eine Woche (zu viel Verderbliches); der Rest bleibt frei
        assert len(plan["entries"]) == 6
        assert plan["warnings"] == []
        ids = [e["recipe_id"] for e in plan["entries"]]
        assert len(set(ids)) == 6
        by_title = {e["recipe_title"]: (date.fromisoformat(e["day"]) - start).days for e in plan["entries"]}
        if "Spaghetti Bolognese" in by_title:
            assert by_title["Spaghetti Bolognese"] == 0
        if "Lachs mit Spinat" in by_title:
            assert by_title["Lachs mit Spinat"] == 0
        assert not ("Spaghetti Bolognese" in by_title and "Lachs mit Spinat" in by_title)
        if "Hähnchen-Curry" in by_title:
            assert by_title["Hähnchen-Curry"] <= 1


def test_warning_when_moved_late(c):
    start = date.today()
    rs = c.get("/api/recipes").json()
    bolo = next(r for r in rs if r["title"] == "Spaghetti Bolognese")
    e = c.post("/api/plan/entries", json={"day": (start + timedelta(days=4)).isoformat(), "slot": "mittag",
                                          "recipe_id": bolo["id"]}).json()
    plan = c.get(f"/api/plan?start={start.isoformat()}&days=7").json()
    assert any(w["entry_id"] == e["id"] and "Hackfleisch" in w["message"] for w in plan["warnings"])
    c.delete(f"/api/plan/entries/{e['id']}")


def test_swap(c):
    start = date.today()
    plan = c.get(f"/api/plan?start={start.isoformat()}&days=7").json()
    e = plan["entries"][-1]
    new = c.post(f"/api/plan/entries/{e['id']}/swap")
    assert new.status_code in (200, 409)


def test_shopping_from_plan_and_manual(c):
    start = date.today()
    c.post("/api/shopping", json={"text": "Spülmittel\n2 l Milch"})
    c.post("/api/shopping", json={"text": "1 l Milch"})
    items = c.post("/api/shopping/from-plan", json={"start": start.isoformat(), "days": 7}).json()
    milk = [i for i in items if i["name"] == "Milch"]
    assert len(milk) == 1 and milk[0]["quantity"] == "3 l" and not milk[0]["auto"]
    assert any(i["name"] == "Spülmittel" and i["category"] == "drogerie" for i in items)
    assert not any(i["name"].startswith("Salz") for i in items)
    assert any(i["auto"] for i in items)
    # erneutes Erzeugen verdoppelt nichts
    again = c.post("/api/shopping/from-plan", json={"start": start.isoformat(), "days": 7}).json()
    assert len(again) == len(items)
    first = again[0]
    c.patch(f"/api/shopping/{first['id']}", json={"checked": True})
    after = c.post("/api/shopping/clear-checked").json()
    assert len(after) == len(items) - 1


def test_settings_roundtrip(c):
    s = c.put("/api/settings", json={"persons": 4, "exclude_ingredients": "Lachs, Rosinen",
                                     "shelf_days": {"gefluegel": 2}}).json()
    assert s["persons"] == 4 and s["exclude_ingredients"] == ["Lachs", "Rosinen"]
    info = c.get("/api/info").json()
    assert next(x for x in info["categories"] if x["key"] == "gefluegel")["shelf_days"] == 2


PAGE = """<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"WebPage"},{"@type":"Recipe","name":"Käsespätzle",
"recipeYield":"4 Portionen","totalTime":"PT45M","keywords":"Hauptspeise, Vegetarisch",
"image":["https://example.org/a.jpg"],
"recipeIngredient":["500 g Spätzle","200 g Bergkäse, gerieben","3 große Zwiebeln","2 EL Butter"],
"recipeInstructions":[{"@type":"HowToStep","text":"Zwiebeln in Ringe schneiden."},
{"@type":"HowToStep","text":"Spätzle mit Käse schichten &amp; überbacken."}]}]}
</script></head><body></body></html>"""


def test_import(c, monkeypatch):
    async def fake_fetch(url):
        return url, PAGE

    monkeypatch.setattr(importer, "fetch", fake_fetch)
    r = c.post("/api/recipes/import", json={"url": "https://example.org/kaesespaetzle"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["title"] == "Käsespätzle" and d["servings"] == 4 and d["total_minutes"] == 45
    assert d["steps"][1] == "Spätzle mit Käse schichten & überbacken."
    assert d["ingredients"][1]["name"] == "Bergkäse" and d["ingredients"][1]["category"] == "kaese_eier"
    assert d["tags"] == ["Hauptspeise", "Vegetarisch"]


def test_import_blocks_private_hosts():
    with pytest.raises(importer.ImportError_):
        importer._check_host("http://192.168.1.10/rezept")
    with pytest.raises(importer.ImportError_):
        importer._check_host("http://localhost:8123/")
