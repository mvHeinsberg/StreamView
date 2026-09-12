#!/usr/bin/env python3
"""
Baut aus web/index.html + web/style.css + web/app.js + data/events.json
eine einzige, eigenständige HTML-Datei (preview.html im Projekt-Hauptordner).

Zweck: Du willst dir das Layout/Design ansehen oder Änderungswünsche
markieren, ohne extra einen Webserver zu starten - preview.html lässt
sich per Doppelklick direkt im Browser öffnen (auch offline), weil CSS,
JavaScript UND die aktuellen Daten alle in die eine Datei eingebettet
sind (kein fetch() auf data/events.json nötig).

Aufruf (nachdem einmal `python3 update_data.py` gelaufen ist):
    python3 build_preview.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DATA_FILE = ROOT / "data" / "events.json"
OUTPUT = ROOT / "preview.html"


def main() -> int:
    if not DATA_FILE.exists():
        print(
            "data/events.json fehlt - bitte zuerst `python3 update_data.py` ausführen, "
            "damit es echte (bzw. die aktuellen Beispiel-)Daten zum Anzeigen gibt.",
            file=sys.stderr,
        )
        return 1

    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "style.css").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    payload_json = DATA_FILE.read_text(encoding="utf-8")

    if '<link rel="stylesheet" href="style.css" />' not in html:
        print("Konnte den style.css-<link> in web/index.html nicht finden - Abbruch.", file=sys.stderr)
        return 1
    if '<script src="app.js"></script>' not in html:
        print("Konnte den app.js-<script>-Tag in web/index.html nicht finden - Abbruch.", file=sys.stderr)
        return 1

    html = html.replace(
        '<link rel="stylesheet" href="style.css" />',
        f"<style>\n{css}\n</style>",
    )
    html = html.replace(
        '<script src="app.js"></script>',
        f"<script>\nwindow.EMBEDDED_DATA = {payload_json};\n</script>\n<script>\n{js}\n</script>",
    )
    html = html.replace(
        "<title>LIVE Stream Übersicht</title>",
        "<title>LIVE Stream Übersicht (Vorschau)</title>",
    )

    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Vorschau geschrieben nach {OUTPUT} - einfach per Doppelklick im Browser öffnen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
