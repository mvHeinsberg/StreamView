"""
Formel-1-Terminkalender über die kostenlose Jolpica-F1-API
(https://api.jolpi.ca/ergast/), dem Nachfolger der eingestellten
Ergast-API. Kein API-Key nötig.

API-Beispiel: https://api.jolpi.ca/ergast/f1/2026.json
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from .base import Event, Provider

log = logging.getLogger(__name__)

BASE_URL = "https://api.jolpi.ca/ergast/f1"

# Session-Schlüssel im Ergast/Jolpica-Format -> (Anzeigename, Kategorie)
SESSION_KEYS = {
    "FirstPractice": "Freies Training 1",
    "SecondPractice": "Freies Training 2",
    "ThirdPractice": "Freies Training 3",
    "SprintQualifying": "Sprint-Qualifying",
    "Sprint": "Sprint",
    "Qualifying": "Qualifying",
}

# Formel 1 läuft in Deutschland aktuell exklusiv bei Sky (+ teils RTL im Free-TV
# für ausgewählte Rennen). Bitte bei Rechte-Wechseln anpassen.
CHANNELS = [
    ("Sky Sport F1", "paid"),
]


def _parse_session(date_str: str | None, time_str: str | None) -> datetime | None:
    if not date_str:
        return None
    time_str = time_str or "00:00:00Z"
    try:
        return datetime.fromisoformat(f"{date_str}T{time_str.replace('Z', '+00:00')}")
    except ValueError:
        return None


class F1Provider(Provider):
    name = "f1"

    def fetch(self, start: datetime, end: datetime) -> list[Event]:
        events: list[Event] = []
        seasons = {start.year, end.year}

        for season in seasons:
            url = f"{BASE_URL}/{season}.json"
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                races = (
                    resp.json()
                    .get("MRData", {})
                    .get("RaceTable", {})
                    .get("Races", [])
                )
            except Exception as exc:
                log.warning("F1 (Jolpica): Abruf für Saison %s fehlgeschlagen: %s", season, exc)
                continue

            for race in races:
                race_name = race.get("raceName", "Formel 1")
                circuit = (race.get("Circuit") or {}).get("circuitName", "")

                sessions = {"Race": (race.get("date"), race.get("time"))}
                for key in SESSION_KEYS:
                    block = race.get(key)
                    if block:
                        sessions[key] = (block.get("date"), block.get("time"))

                for key, (date_str, time_str) in sessions.items():
                    dt = _parse_session(date_str, time_str)
                    if dt is None or not (start <= dt <= end):
                        continue

                    label = "Rennen" if key == "Race" else SESSION_KEYS.get(key, key)

                    for channel_name, access in CHANNELS:
                        events.append(
                            Event(
                                title=f"Formel 1: {race_name} – {label}",
                                subtitle=circuit,
                                start=dt,
                                channel=channel_name,
                                channel_id=channel_name,
                                provider=self.name,
                                access=access,
                                category="Formel 1",
                                description=f"{race_name} ({circuit}): {label}",
                            )
                        )

        return events
