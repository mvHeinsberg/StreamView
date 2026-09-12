#!/usr/bin/env python3
"""
Aktualisiert data/events.json mit allen Live-Events der kommenden
LOOKAHEAD_DAYS Tage aus allen konfigurierten Quellen (providers/).

Aufruf:
    python3 update_data.py

Für die automatische, regelmäßige Aktualisierung siehe cron/ (Cronjob-
oder systemd-Timer-Beispiel im README).

Jede Quelle wird einzeln in try/except abgefangen: fällt z.B. die
OpenLigaDB-API einmal aus, bricht der Lauf nicht komplett ab, sondern
liefert weiterhin die Daten der übrigen Quellen.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
from providers import ALL_PROVIDERS, Event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("update_data")

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_FILE = DATA_DIR / "events.json"


def collect_events(start: datetime, end: datetime) -> list[Event]:
    all_events: list[Event] = []
    for provider in ALL_PROVIDERS:
        log.info("Frage Quelle '%s' ab ...", provider.name)
        try:
            events = provider.fetch(start, end)
        except Exception:
            log.exception("Quelle '%s' ist fehlgeschlagen, wird übersprungen.", provider.name)
            continue
        log.info("Quelle '%s': %d Live-Events gefunden.", provider.name, len(events))
        all_events.extend(events)
    return all_events


def deduplicate(events: list[Event]) -> list[Event]:
    """Entfernt Duplikate, die z.B. entstehen können, wenn ein Spiel sowohl
    über die manuelle Liste als auch über das EPG erfasst wird (gleicher
    Titel, gleicher Sender, gleiche Startzeit)."""
    seen: set[tuple[str, str, str]] = set()
    unique: list[Event] = []
    for e in events:
        key = (e.title.strip().lower(), e.channel.strip().lower(), e.start.isoformat())
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    return unique


def main() -> int:
    now = datetime.now(timezone.utc)
    range_start = now
    range_end = now + timedelta(days=config.LOOKAHEAD_DAYS)

    log.info(
        "Sammle Live-Events von %s bis %s ...",
        range_start.date(),
        range_end.date(),
    )

    events = collect_events(range_start, range_end)
    events = deduplicate(events)
    events.sort(key=lambda e: e.start)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": now.isoformat(),
        "range_start": range_start.isoformat(),
        "range_end": range_end.isoformat(),
        "count": len(events),
        "events": [e.to_dict() for e in events],
    }

    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Fertig: %d Events geschrieben nach %s", len(events), OUTPUT_FILE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
