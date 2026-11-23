import os
from pathlib import Path

VERSION = "0.1.0"

DATA_DIR = Path(os.environ.get("ESSEN_DATA_DIR", "/data"))
STATIC_DIR = Path(os.environ.get("ESSEN_STATIC_DIR", Path(__file__).resolve().parent.parent / "static"))
DB_PATH = DATA_DIR / "essen.db"
