# Essen

Essensplaner direkt in Home Assistant. Die App erscheint als **Essen** in der Seitenleiste
und ist auch in der HA-App auf dem Handy nutzbar.

## Funktionen (Version 0.1)
- **Kochbuch:** Rezepte selbst anlegen oder per Link von Rezeptseiten importieren (Chefkoch, REWE, Lecker …)
- Zutaten werden automatisch erkannt: Menge, Einheit und Kategorie (z. B. Hackfleisch, Geflügel, Vorrat)
- Portionen umrechnen, Bewertungen, Favoriten, **Kochmodus** Schritt für Schritt (Bildschirm bleibt an)
- **Wochenplan** ab dem Abholtag, automatisch füllen oder einzelne Gerichte neu würfeln
- **Haltbarkeit:** Verderbliches wird früh in der Woche eingeplant (Hackfleisch und frischer Fisch am
  Abholtag, Geflügel bis Tag 1, Fleisch am Stück bis Tag 2 …). Warnung, wenn ein Gericht zu spät liegt.
- Vorschläge berücksichtigen Bewertungen, Favoriten, Schlagworte, Ausschlüsse und Abwechslung
- **Einkaufsliste** aus dem Wochenplan, Mengen zusammengefasst und nach Marktbereichen sortiert;
  eigene Artikel jederzeit dazu

## Einstellungen
Alles wird in der App unter **Einstellungen** eingestellt: Personen, Abholtag, Mahlzeiten,
Ausschlüsse, „immer im Haus“ und die Haltbarkeit pro Kategorie.

## Zugriff über Claude
Claude erreicht die App über den Home-Assistant-Connector und kann z. B. Artikel auf die
Einkaufsliste setzen, Rezepte anlegen oder den Plan abfragen. Die API ist unter `api/docs` beschrieben.

## Daten & Backup
Alle Daten liegen im App-Speicher (`/data`) und sind in den normalen Home-Assistant-Backups enthalten.

## Sicherheit
- Kein offener Port; Zugriff nur über Home Assistant (Ingress) mit HA-Login.
- Anfragen, die nicht vom Ingress-Gateway kommen, werden abgewiesen.
- Der Rezept-Import ruft nur öffentliche Webseiten ab, keine Adressen im Heimnetz.

## Geplant
- **Etappe 2:** REWE: Angebote, Preise pro Gericht und Woche, Warenkorb für die Abholung füllen
- **Etappe 3:** Nährwerte pro Portion und Tag, Reste und angebrochene Packungen einplanen
