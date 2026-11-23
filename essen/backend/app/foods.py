"""Lebensmittel-Kategorien: Haltbarkeit nach dem Einkauf und Sortierung im Markt.

`shelf_days` = spätestens am wievielten Tag nach der Abholung verbrauchen (0 = am Abholtag).
Die Werte sind Voreinstellungen und in den Einstellungen pro Kategorie änderbar.
"""

import re

NEVER = 99  # praktisch unbegrenzt haltbar

CATEGORIES: list[dict] = [
    {"key": "gemuese", "label": "Obst & Gemüse", "shelf_days": 4},
    {"key": "salat_kraeuter", "label": "Salat, Kräuter, Beeren, Pilze", "shelf_days": 2},
    {"key": "lagergemuese", "label": "Kartoffeln, Zwiebeln, Wurzelgemüse, Kohl", "shelf_days": 7},
    {"key": "brot", "label": "Brot & Backwaren", "shelf_days": 2},
    {"key": "hack", "label": "Hackfleisch", "shelf_days": 0},
    {"key": "gefluegel", "label": "Geflügel", "shelf_days": 1},
    {"key": "fleisch", "label": "Fleisch am Stück", "shelf_days": 2},
    {"key": "fisch", "label": "Frischer Fisch & Meeresfrüchte", "shelf_days": 0},
    {"key": "wurst", "label": "Wurst & Schinken", "shelf_days": 5},
    {"key": "molkerei", "label": "Milch, Sahne, Joghurt, Frischkäse", "shelf_days": 3},
    {"key": "kaese_eier", "label": "Käse, Butter, Eier", "shelf_days": 7},
    {"key": "kuehlregal", "label": "Kühlregal (frische Nudeln, Tofu …)", "shelf_days": 3},
    {"key": "tiefkuehl", "label": "Tiefkühl", "shelf_days": NEVER},
    {"key": "vorrat", "label": "Vorrat (Nudeln, Reis, Konserven …)", "shelf_days": NEVER},
    {"key": "gewuerze", "label": "Gewürze, Öl, Essig, Saucen", "shelf_days": NEVER},
    {"key": "getraenke", "label": "Getränke", "shelf_days": NEVER},
    {"key": "drogerie", "label": "Drogerie & Haushalt", "shelf_days": NEVER},
    {"key": "sonstiges", "label": "Sonstiges", "shelf_days": NEVER},
]
CATEGORY_KEYS = [c["key"] for c in CATEGORIES]
DEFAULT_SHELF = {c["key"]: c["shelf_days"] for c in CATEGORIES}
# Hauptzutat eines Gerichts (für Abwechslung im Plan)
PROTEIN_CATEGORIES = ("hack", "gefluegel", "fisch", "fleisch")

# Reihenfolge zählt: spezielle Begriffe vor allgemeinen (z. B. "Fischsauce" vor "Fisch").
_RULES: list[tuple[str, str]] = [
    # Ausnahmen / zusammengesetzte Begriffe
    (r"tiefkühl|tk[- ]|\(tk\)|gefroren", "tiefkuehl"),
    (r"fischsauce|fischsoße|austernsauce|sojasauce|sojasoße|worcester|ketchup|senf|mayonnaise|sriracha|tabasco|"
     r"pesto|tahin|essig|balsamico|\böl\b|olivenöl|rapsöl|sesamöl|sonnenblumenöl|bratöl|gewürz|paprikapulver|"
     r"curry(pulver|paste)|currypaste|kreuzkümmel|kümmel|zimt|muskat|oregano, getr|getrocknet|chiliflocken|"
     r"chilipulver|cayenne|kurkuma|garam|salz|pfeffer\b|pfefferkörner|lorbeer|nelke|vanille|brühe|fond|"
     r"bouillon|gemüsebrühe|hefe|backpulver|natron|speisestärke|stärke|honig|ahornsirup|sirup|zucker|"
     r"marmelade|konfitüre|tomatenmark|harissa|miso|sambal|kapern", "gewuerze"),
    (r"kokosmilch|kokosnussmilch|dose|konserve|passiert|stückige tomaten|gehackte tomaten|pizzatomaten|"
     r"kichererbsen|kidneybohnen|bohnen, weiß|weiße bohnen|linsen|mais\b|maiskörner|thunfisch|sardellen|"
     r"oliven|getrocknete tomaten|nudeln|spaghetti|penne|fusilli|tagliatelle|lasagne|makkaroni|farfalle|"
     r"rigatoni|orzo|reis\b|basmati|risotto|couscous|bulgur|quinoa|hirse|polenta|mehl|haferflocken|"
     r"semmelbrösel|paniermehl|nüsse|mandeln|walnüsse|haselnüsse|cashew|erdnüsse|pinienkerne|sesam|"
     r"rosinen|schokolade|kakao|glasnudeln|reisnudeln|mie[- ]nudeln|udon|tortilla|wraps|tacos|"
     r"zwieback|cracker|chips", "vorrat"),
    (r"frische nudeln|frische pasta|gnocchi|tortellini|ravioli|maultaschen|tofu|tempeh|blätterteig|"
     r"pizzateig|quicheteig|hefeteig|filoteig|yufka|frischhefe", "kuehlregal"),
    # Fleisch & Fisch
    (r"hack|faschiert|tatar|mett|bratwurstbrät|brät\b|cevapcici|frikadelle", "hack"),
    (r"hähnchen|hühnchen|huhn|hühner|geflügel|pute|puten|truthahn|ente|gans|chicken", "gefluegel"),
    (r"lachs|forelle|kabeljau|seelachs|dorsch|zander|barsch|scholle|thunfischsteak|garnele|shrimp|scampi|"
     r"krabbe|muschel|tintenfisch|calamari|fisch", "fisch"),
    (r"schinken|speck|salami|chorizo|wurst|würstchen|wiener|lyoner|pancetta|guanciale|prosciutto|"
     r"bacon|aufschnitt|kassler|kasseler", "wurst"),
    (r"rind|kalb|schwein|lamm|steak|filet|schnitzel|gulasch|braten|kotelett|rippchen|spareribs|"
     r"wild\b|reh|hirsch|fleisch", "fleisch"),
    # Molkerei
    (r"milch|sahne|schmand|crème fraîche|creme fraiche|saure sahne|joghurt|quark|frischkäse|mascarpone|"
     r"ricotta|mozzarella|burrata|feta|hirtenkäse|halloumi|buttermilch|kefir|skyr|schlagsahne|kochsahne", "molkerei"),
    (r"butter|ei\b|eier|eigelb|eiweiß|parmesan|pecorino|gouda|emmentaler|bergkäse|cheddar|grana|"
     r"hartkäse|reibekäse|geriebener käse|käse", "kaese_eier"),
    # Brot
    (r"brot|brötchen|baguette|ciabatta|toast|fladenbrot|naan|pita|brezel|laugen|burger[- ]?bun|buns", "brot"),
    # Gemüse
    (r"salat|rucola|feldsalat|spinat|mangold|basilikum|petersilie|koriander|schnittlauch|dill|minze|"
     r"thymian|rosmarin|salbei|oregano|estragon|kerbel|kresse|beeren|erdbeer|himbeer|heidelbeer|"
     r"brombeer|johannisbeer|pilz|champignon|pfifferling|steinpilz|shiitake|kräuter|sprossen|frühlingszwiebel|"
     r"lauchzwiebel", "salat_kraeuter"),
    (r"kartoffel|zwiebel|schalotte|knoblauch|karotte|möhre|möhren|rübe|sellerie|knollensellerie|pastinake|"
     r"petersilienwurzel|rote bete|kürbis|kohl|weißkohl|rotkohl|wirsing|kohlrabi|rosenkohl|ingwer|"
     r"süßkartoffel|apfel|äpfel|zitrone|limette|orange", "lagergemuese"),
    (r"tomate|paprika|gurke|zucchini|aubergine|brokkoli|blumenkohl|lauch|porree|fenchel|spargel|"
     r"erbsen|bohnen|zuckerschoten|mais|chili|peperoni|avocado|banane|birne|mango|ananas|traube|"
     r"pfirsich|nektarine|kiwi|melone|pak choi|chinakohl|radieschen|rettich|artischocke|okra|"
     r"obst|gemüse|staudensellerie|stangensellerie", "gemuese"),
    (r"wasser|saft|wein|bier|cola|limo|sprudel|sekt|prosecco|kaffee|tee\b", "getraenke"),
    (r"spülmittel|waschmittel|klopapier|toilettenpapier|küchenrolle|zahnpasta|shampoo|duschgel|seife|"
     r"müllbeutel|alufolie|frischhaltefolie|backpapier|schwamm|tücher|windeln|deo", "drogerie"),
]
_COMPILED = [(re.compile(p, re.IGNORECASE), cat) for p, cat in _RULES]


def classify(name: str) -> str:
    """Ordnet eine Zutat einer Kategorie zu (Stichwortsuche, erster Treffer gewinnt)."""
    n = (name or "").strip().lower()
    if not n:
        return "sonstiges"
    for rx, cat in _COMPILED:
        if rx.search(n):
            return cat
    return "sonstiges"


def category_order() -> dict[str, int]:
    return {k: i for i, k in enumerate(CATEGORY_KEYS)}


def category_label(key: str) -> str:
    for c in CATEGORIES:
        if c["key"] == key:
            return c["label"]
    return key
