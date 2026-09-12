"""
Manuell/kuratiert gepflegte Live-Events.

Für vieles gibt es keine freie, verlässliche API:
- Streaming-exklusive Events auf RTL+, Joyn, WOW, MagentaSport usw.
  (nicht Teil des normalen TV-Programms/EPG)
- Einmalige Großereignisse (Award-Shows, Eurovision Song Contest,
  Box-/UFC-Kämpfe, Wahlabende, Silvester-Shows, ...)
- Alles, wofür sich in providers/epg_xmltv.py keine zuverlässige
  Automatisierung lohnt

Diese Liste in data/manual_events.yaml ist daher die "Fallback"-Quelle:
Du (oder ein Cronjob, der z.B. Presseseiten der Sender ausliest) trägst
hier Termine ein, die die anderen Provider nicht liefern.

Format pro Eintrag:
  - title: "Name des Events"
    start: "2026-09-20T20:15:00+02:00"   # ISO-8601, mit Zeitzone
    end: "2026-09-20T23:00:00+02:00"      # optional
    channel: "RTL+"                       # Sender/Plattform-Anzeigename
    access: "paid"                        # "free" oder "paid" (überschreibt config.py-Heuristik)
    category: "Show"
    medium: "tv"                          # optional: "tv" (Standard) oder "radio"
    description: "Kurzbeschreibung (optional)"
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import yaml

from .base import Event, Provider

log = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "manual_events.yaml"


class ManualEventsProvider(Provider):
    name = "manual"

    def __init__(self, path: Path | None = None):
        self.path = path or DATA_FILE

    def fetch(self, start: datetime, end: datetime) -> list[Event]:
        if not self.path.exists():
            log.info("Manuelle Event-Liste %s existiert nicht, wird übersprungen.", self.path)
            return []

        try:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or []
        except Exception as exc:
            log.warning("Manuelle Event-Liste %s konnte nicht gelesen werden: %s", self.path, exc)
            return []

        events: list[Event] = []
        for i, entry in enumerate(raw):
            try:
                dt_start = datetime.fromisoformat(str(entry["start"]))
                if not (start <= dt_start <= end):
                    continue
                dt_end = None
                if entry.get("end"):
                    dt_end = datetime.fromisoformat(str(entry["end"]))

                events.append(
                    Event(
                        title=entry["title"],
                        subtitle=entry.get("subtitle"),
                        start=dt_start,
                        end=dt_end,
                        channel=entry["channel"],
                        channel_id=entry.get("channel_id", entry["channel"]),
                        provider=self.name,
                        access=entry.get("access", "paid"),
                        category=entry.get("category", "Sonstiges"),
                        description=entry.get("description"),
                        medium=entry.get("medium", "tv"),
                    )
                )
            except (KeyError, ValueError) as exc:
                log.warning("Manuelle Event-Liste: Eintrag #%d ungültig (%s), wird übersprungen.", i, exc)

        return events
