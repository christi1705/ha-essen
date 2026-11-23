"""Rezept-Import per Link: liest die eingebetteten schema.org-Rezeptdaten (JSON-LD) einer Seite."""

import html
import ipaddress
import json
import re
import socket
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx

from .ingredients import parse_line

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
MAX_BYTES = 5 * 1024 * 1024


class ImportError_(Exception):
    pass


def _check_host(url: str) -> None:
    """Nur öffentliche Adressen abrufen (kein Zugriff aufs Heimnetz über die App)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ImportError_("Bitte einen vollständigen Link (https://…) angeben")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80))
    except socket.gaierror as e:
        raise ImportError_("Seite nicht erreichbar") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ImportError_("Nur öffentliche Webseiten können importiert werden")


async def fetch(url: str) -> tuple[str, str]:
    current = url
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, headers={"User-Agent": UA,
                                 "Accept-Language": "de-DE,de;q=0.9"}) as client:
        for _ in range(5):
            _check_host(current)
            async with client.stream("GET", current) as resp:
                if resp.is_redirect:
                    current = urljoin(current, resp.headers.get("location", ""))
                    continue
                if resp.status_code >= 400:
                    raise ImportError_(f"Seite antwortet mit Fehler {resp.status_code}")
                buf = bytearray()
                async for chunk in resp.aiter_bytes():
                    buf += chunk
                    if len(buf) > MAX_BYTES:
                        raise ImportError_("Seite ist zu groß")
                return str(resp.url), buf.decode(resp.encoding or "utf-8", errors="replace")
    raise ImportError_("Zu viele Weiterleitungen")


def _iter_nodes(data: Any):
    if isinstance(data, list):
        for x in data:
            yield from _iter_nodes(x)
    elif isinstance(data, dict):
        yield data
        for k in ("@graph", "mainEntity", "itemListElement"):
            if k in data:
                yield from _iter_nodes(data[k])


def _is_recipe(node: dict) -> bool:
    t = node.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(isinstance(x, str) and x.lower().endswith("recipe") for x in types)


def find_recipe(page: str) -> Optional[dict]:
    for m in re.finditer(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", page, re.S | re.I):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except ValueError:
            try:
                data = json.loads(re.sub(r"[\x00-\x1f]", " ", raw))
            except ValueError:
                continue
        for node in _iter_nodes(data):
            if _is_recipe(node):
                return node
    return None


def _text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        v = v[0] if v else ""
    if isinstance(v, dict):
        v = v.get("text") or v.get("name") or ""
    s = re.sub(r"<[^>]+>", " ", html.unescape(str(v)))
    return re.sub(r"\s+", " ", s).strip()


def _minutes(v: Any) -> Optional[int]:
    """ISO-8601-Dauer (PT1H30M) in Minuten."""
    if not v or not isinstance(v, str):
        return None
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", v.strip().upper())
    if not m:
        return None
    d, h, mi = (int(x) if x else 0 for x in m.groups())
    total = d * 1440 + h * 60 + mi
    return total or None


def _servings(v: Any) -> int:
    if isinstance(v, list):
        v = next((x for x in v if re.search(r"\d", str(x))), v[0] if v else None)
    m = re.search(r"\d+", str(v or ""))
    n = int(m.group()) if m else 2
    return max(1, min(n, 50))


def _steps(v: Any) -> list[str]:
    out: list[str] = []
    if isinstance(v, str):
        parts = re.split(r"\n\s*\n|\r\n\r\n|(?<=\.)\s*\n", html.unescape(v))
        return [_text(p) for p in parts if _text(p)]
    if isinstance(v, dict):
        v = [v]
    for item in v or []:
        if isinstance(item, str):
            t = _text(item)
            if t:
                out.append(t)
        elif isinstance(item, dict):
            if "itemListElement" in item:  # HowToSection
                name = _text(item.get("name"))
                sub = _steps(item["itemListElement"])
                if name and sub:
                    sub[0] = f"{name}: {sub[0]}"
                out.extend(sub)
            else:
                t = _text(item.get("text") or item.get("name"))
                if t:
                    out.append(t)
    return out


def _image(v: Any, base: str) -> Optional[str]:
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, dict):
        v = v.get("url") or v.get("contentUrl")
    if isinstance(v, str) and v.strip():
        return urljoin(base, v.strip())
    return None


def _tags(node: dict) -> list[str]:
    raw: list[str] = []
    for k in ("recipeCategory", "recipeCuisine", "keywords"):
        v = node.get(k)
        if isinstance(v, str):
            raw.extend(v.split(","))
        elif isinstance(v, list):
            raw.extend(str(x) for x in v)
    seen, out = set(), []
    for t in raw:
        t = _text(t)
        if t and len(t) <= 30 and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out[:8]


def to_recipe(node: dict, url: str) -> dict:
    ingredients = []
    for line in node.get("recipeIngredient") or node.get("ingredients") or []:
        p = parse_line(_text(line))
        if p:
            ingredients.append(p)
    title = _text(node.get("name")) or "Importiertes Rezept"
    return {
        "title": title[:200],
        "description": _text(node.get("description"))[:1000] or None,
        "source_url": url,
        "image_url": _image(node.get("image"), url),
        "servings": _servings(node.get("recipeYield")),
        "prep_minutes": _minutes(node.get("prepTime")),
        "total_minutes": _minutes(node.get("totalTime")) or _minutes(node.get("cookTime")),
        "tags": _tags(node),
        "ingredients": ingredients,
        "steps": _steps(node.get("recipeInstructions")),
    }


async def import_url(url: str) -> dict:
    final_url, page = await fetch(url.strip())
    node = find_recipe(page)
    if not node:
        raise ImportError_("Auf der Seite wurde kein Rezept gefunden")
    return to_recipe(node, final_url)
