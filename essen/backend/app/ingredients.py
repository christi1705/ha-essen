"""Zutatenzeilen zerlegen ("200 g Hackfleisch, gemischt") und Mengen zusammenfassen."""

import re
from typing import Optional

from .foods import classify

_FRACTIONS = {"½": 0.5, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 0.25, "¾": 0.75, "⅛": 0.125, "⅕": 0.2}

# Schreibweisen -> einheitliche Einheit
_UNITS: dict[str, str] = {}
for canon, variants in {
    "g": ["g", "gr", "gr.", "gramm"],
    "kg": ["kg", "kilo", "kilogramm"],
    "mg": ["mg"],
    "ml": ["ml", "milliliter"],
    "cl": ["cl"],
    "dl": ["dl"],
    "l": ["l", "liter", "ltr", "ltr."],
    "EL": ["el", "el.", "essl", "essl.", "esslöffel", "eßlöffel", "tbsp"],
    "TL": ["tl", "tl.", "teel", "teel.", "teelöffel", "tsp"],
    "Prise": ["prise", "prisen", "prise(n)"],
    "Msp.": ["msp", "msp.", "messerspitze", "messerspitzen"],
    "Bund": ["bund", "bd", "bd."],
    "Dose": ["dose", "dosen", "dose(n)", "ds", "ds."],
    "Pck.": ["pck", "pck.", "pkg", "pkg.", "päckchen", "packung", "packungen", "pack", "pk", "pk."],
    "Glas": ["glas", "gläser", "glas/gläser"],
    "Becher": ["becher"],
    "Tasse": ["tasse", "tassen", "tasse(n)", "cup", "cups"],
    "Stück": ["stück", "stk", "stk.", "st.", "stck"],
    "Zehe": ["zehe", "zehen", "zehe(n)"],
    "Scheibe": ["scheibe", "scheiben", "scheibe(n)"],
    "Zweig": ["zweig", "zweige", "zweig(e)"],
    "Blatt": ["blatt", "blätter", "blatt/blätter"],
    "Handvoll": ["handvoll", "hand voll"],
    "Würfel": ["würfel"],
    "Stange": ["stange", "stangen", "stange(n)"],
    "Kopf": ["kopf", "köpfe"],
    "Knolle": ["knolle", "knollen"],
    "Schuss": ["schuss", "schuß"],
    "Spritzer": ["spritzer"],
    "Tropfen": ["tropfen"],
    "Beutel": ["beutel"],
    "Flasche": ["flasche", "flaschen"],
    "Netz": ["netz"],
    "Schale": ["schale", "schalen"],
}.items():
    for v in variants:
        _UNITS[v] = canon

# Umrechnung auf Basiseinheit
_BASE = {"kg": ("g", 1000), "mg": ("g", 0.001), "l": ("ml", 1000), "cl": ("ml", 10), "dl": ("ml", 100)}

_SIZE_WORDS = re.compile(
    r"^(m\.-?große?n?|mittelgroße?n?|große?n?|kleine?n?|gehäufte?r?|gestrichene?r?|reife?n?|frische?n?|dicke?n?|dünne?n?)\s+",
    re.IGNORECASE,
)
_NUM = r"(?:\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?|[½⅓⅔¼¾⅛⅕])"
_AMOUNT = re.compile(rf"^\s*(?P<a>{_NUM}(?:\s*[½⅓⅔¼¾⅛⅕])?)(?:\s*(?:-|–|bis)\s*(?P<b>{_NUM}))?\s*")


def _num(s: str) -> Optional[float]:
    s = s.strip().replace(",", ".")
    total = 0.0
    m = re.match(r"^(\d+(?:\.\d+)?)?\s*([½⅓⅔¼¾⅛⅕])?$", s)
    if m and (m.group(1) or m.group(2)):
        if m.group(1):
            total += float(m.group(1))
        if m.group(2):
            total += _FRACTIONS[m.group(2)]
        return total
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", s)
    if m and int(m.group(2)):
        return int(m.group(1)) / int(m.group(2))
    return None


def clean_name(name: str) -> str:
    n = re.sub(r"\((n|e|en|s|er)\)|/(n|e|en)\b", "", name)
    n = re.sub(r"\s+", " ", n).strip(" ,;:-")
    return n


def parse_line(line: str) -> Optional[dict]:
    """Zerlegt eine Zutatenzeile in Menge, Einheit, Name und Notiz."""
    text = re.sub(r"\s+", " ", (line or "").replace(" ", " ")).strip(" -•*\t")
    if not text:
        return None
    amount: Optional[float] = None
    unit: Optional[str] = None
    m = _AMOUNT.match(text)
    if m:
        a = _num(m.group("a"))
        b = _num(m.group("b")) if m.group("b") else None
        if a is not None:
            amount = b if b is not None else a  # bei Spannen ("1-2") lieber genug einkaufen
            text = text[m.end():]
    # Einheit
    um = re.match(r"^([A-Za-zÄÖÜäöüß.()/]+)\s*", text)
    if um:
        cand = re.sub(r"/(n|e|en)$", "", um.group(1).lower())
        if cand in _UNITS and (amount is not None or cand not in ("l", "g")):
            unit = _UNITS[cand]
            text = text[um.end():]
    note_parts = []
    sm = _SIZE_WORDS.match(text)
    if sm:
        note_parts.append(sm.group(1))
        text = text[sm.end():]
    if text.lower().startswith("etwas "):
        note_parts.append("etwas")
        text = text[6:]
    name, _, note = text.partition(",")
    if note.strip():
        note_parts.append(note.strip())
    # "Salz und Pfeffer" / Zusätze in Klammern am Ende als Notiz
    pm = re.search(r"\s*\(([^)]{3,})\)\s*$", name)
    if pm:
        note_parts.append(pm.group(1))
        name = name[: pm.start()]
    name = clean_name(name)
    if not name:
        return None
    category = classify(name)
    if unit in ("Dose", "Glas") and category not in ("gewuerze", "getraenke"):
        category = "vorrat"
    return {
        "amount": round(amount, 3) if amount is not None else None,
        "unit": unit,
        "name": name,
        "note": ", ".join(note_parts) or None,
        "category": category,
    }


def parse_lines(text: str) -> list[dict]:
    out = []
    for line in (text or "").splitlines():
        p = parse_line(line)
        if p:
            out.append(p)
    return out


def normalize_key(name: str) -> str:
    """Schlüssel zum Zusammenfassen gleicher Zutaten."""
    n = clean_name(name).lower()
    # sehr einfache Singularbildung für häufige Endungen
    for suf, rep in (("zwiebeln", "zwiebel"), ("tomaten", "tomate"), ("karotten", "karotte"), ("möhren", "möhre"),
                     ("kartoffeln", "kartoffel"), ("zehen", "zehe"), ("eier", "ei"), ("paprikaschoten", "paprika"),
                     ("paprikaschote", "paprika"), ("zitronen", "zitrone"), ("limetten", "limette"), ("gurken", "gurke"),
                     ("äpfel", "apfel"), ("champignons", "champignon"), ("auberginen", "aubergine")):
        if n.endswith(suf):
            n = n[: -len(suf)] + rep
            break
    if n.startswith("knoblauchzehe"):
        n = "knoblauch"
    return n


def to_base(amount: Optional[float], unit: Optional[str]) -> tuple[Optional[float], Optional[str]]:
    if unit in _BASE and amount is not None:
        base, f = _BASE[unit]
        return amount * f, base
    if unit == "Zehe":
        return amount, "Zehe"
    return amount, unit


def fmt_amount(v: float) -> str:
    if abs(v - round(v)) < 0.01:
        return str(int(round(v)))
    for frac, sym in ((0.5, "½"), (0.25, "¼"), (0.75, "¾")):
        whole = int(v)
        if abs(v - whole - frac) < 0.01:
            return f"{whole} {sym}" if whole else sym
    return f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",")


_PLURAL = {"Zehe": "Zehen", "Dose": "Dosen", "Scheibe": "Scheiben", "Stange": "Stangen", "Knolle": "Knollen",
           "Flasche": "Flaschen", "Tasse": "Tassen", "Zweig": "Zweige", "Glas": "Gläser", "Kopf": "Köpfe",
           "Prise": "Prisen", "Schale": "Schalen"}


def fmt_part(amount: Optional[float], unit: Optional[str]) -> str:
    if amount is None:
        return unit or ""
    if unit == "g" and amount >= 1000:
        return f"{fmt_amount(amount / 1000)} kg"
    if unit == "ml" and amount >= 1000:
        return f"{fmt_amount(amount / 1000)} l"
    if unit:
        return f"{fmt_amount(amount)} {_PLURAL.get(unit, unit) if amount > 1 else unit}"
    return fmt_amount(amount)


def merge_parts(parts: list[dict]) -> list[dict]:
    """Fasst Mengen gleicher Einheit zusammen: [{amount, unit}] -> zusammengefasst."""
    acc: dict[Optional[str], Optional[float]] = {}
    order: list[Optional[str]] = []
    for p in parts:
        a, u = to_base(p.get("amount"), p.get("unit"))
        if u not in acc:
            acc[u] = None
            order.append(u)
        if a is not None:
            acc[u] = (acc[u] or 0) + a
    return [{"amount": round(acc[u], 3) if acc[u] is not None else None, "unit": u} for u in order]


def quantity_text(parts: list[dict]) -> str:
    texts = [t for t in (fmt_part(p.get("amount"), p.get("unit")) for p in parts) if t]
    return " + ".join(texts)
