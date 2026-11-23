# Essen – Essensplaner für Home Assistant

Wochenplan, Kochbuch und Einkaufsliste als Home-Assistant-App (Add-on) mit eigenem Eintrag in der Seitenleiste.
Inspiriert von Choosy. Details: [`essen/DOCS.md`](essen/DOCS.md).

## Installation
1. In Home Assistant: **Einstellungen → Apps → App Store → ⋮ → Repositories**
2. `https://github.com/christi1705/ha-essen` hinzufügen
3. **Essen** installieren, starten, „In Seitenleiste anzeigen“ aktivieren

## Etappen
- [x] **Etappe 1:** Kochbuch mit Link-Import, Wochenplan mit Haltbarkeitsregeln, Einkaufsliste, Kochmodus
- [ ] **Etappe 2:** REWE: Angebote, Preise, Warenkorb für die Abholung
- [ ] **Etappe 3:** Nährwerte, Reste und angebrochene Packungen

## Entwicklung
```bash
# Backend
cd essen/backend && pip install -r requirements.txt pytest && python -m pytest tests
ESSEN_ALLOW_ALL=1 ESSEN_DATA_DIR=./.data uvicorn app.main:app --port 8099 --reload
# Frontend (Proxy auf :8099)
cd essen/frontend && npm install && npm run dev
```
