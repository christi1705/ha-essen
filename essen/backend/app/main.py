"""Einstiegspunkt: API + ausgeliefertes Frontend (für HA Ingress)."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import api
from .config import STATIC_DIR, VERSION
from .db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Essen", version=VERSION, lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")

# --- Zugriffsschutz -----------------------------------------------------------
# Wie bei Reisen: kein offener Port, nur Anfragen vom HA-Ingress-Gateway (mit HA-Login).
# ESSEN_ALLOW_ALL=1 schaltet das für die Entwicklung ab.
INGRESS_IPS = {"172.30.32.2", "127.0.0.1", "::1"}
ALLOW_ALL = os.environ.get("ESSEN_ALLOW_ALL") == "1"


@app.middleware("http")
async def ingress_only(request: Request, call_next):
    peer = request.client.host if request.client else ""
    if not ALLOW_ALL and peer not in INGRESS_IPS:
        return PlainTextResponse("Zugriff nur über Home Assistant", status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


app.include_router(api.router)


@app.get("/api/health")
def health():
    return {"ok": True}


if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    if path.startswith("api/"):
        raise HTTPException(404)
    f = STATIC_DIR / path
    if path and f.is_file() and STATIC_DIR in f.resolve().parents:
        return FileResponse(f)
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return {"message": "Frontend nicht gebaut"}
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
