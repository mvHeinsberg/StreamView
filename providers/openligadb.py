"""
Fußball-Termine über OpenLigaDB (https://www.openligadb.de) - kostenlos,
kein API-Key nötig. Deckt 1./2. Bundesliga und DFB-Pokal ab.

API-Beispiel: https://api.openligadb.de/getmatchdata/bl1/2026
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from .base import Event, Provider
import config

log = logging.getLogger(__name__)

BASE_URL = "https://api.openligadb.de"

# (Liga-Shortcut, Anzeigename, Kategorie)
LEAGUES = [
    ("bl1", "1. Bundesliga", "Fußball"),
    ("bl2", "2. Bundesliga", "Fußball"),
    ("dfb", "DFB-Pokal", "Fußball"),
]

# Sender, auf denen diese Ligen typischerweise live laufen. Da OpenLigaDB
# selbst keine Sender-Info liefert, tragen wir hier die üblichen
# Übertragungswege ein - ACHTUNG: Rechteinhaber ändern sich von Saison zu
# Saison, bitte prüfen/anpassen. Für den DFB-Pokal zeigen ARD/ZDF einzelne
# ausgewählte Spiele im Free-TV; da OpenLigaDB nicht verrät, welches Spiel
# das ist, wird das hier bewusst NICHT pauschal für jedes Spiel behauptet
# (sondern nur als Hinweis in der Beschreibung ergänzt).
LEAGUE_CHANNELS = {
    "bl1": [("Sky Sport Bundesliga", "paid"), ("DAZN", "paid")],
    "bl2": [("Sky Sport Bundesliga", "paid")],
    "dfb": [("Sky Sport Bundesliga", "paid"), ("DAZN", "paid")],
}
DFB_FREE_TV_NOTE = " Einzelne Spiele werden zusätzlich im Free-TV (ARD/ZDF) übertragen – bitte Ansetzung prüfen."


def _current_season(today: datetime) -> int:
    """OpenLigaDB-Saison = Jahr, in dem die Saison beginnt (Juli-Juni)."""
    return today.year if today.month >= 7 else today.year - 1


class OpenLigaDBProvider(Provider):
    name = "openligadb"

    def fetch(self, start: datetime, end: datetime) -> list[Event]:
        events: list[Event] = []
        season = _current_season(start)

        for shortcut, league_name, category in LEAGUES:
            url = f"{BASE_URL}/getmatchdata/{shortcut}/{season}"
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                matches = resp.json()
            except Exception as exc:  # Netzwerk/HTTP-Fehler dürfen den Lauf nicht stoppen
                log.warning("OpenLigaDB: Abruf für %s fehlgeschlagen: %s", shortcut, exc)
                continue

            for m in matches or []:
                dt_raw = m.get("matchDateTimeUTC") or m.get("matchDateTime")
                if not dt_raw:
                    continue
                try:
                    kickoff = datetime.fromisoformat(dt_raw.replace("Z", "+00:00"))
                    if kickoff.tzinfo is None:
                        kickoff = kickoff.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                if not (start <= kickoff <= end):
                    continue

                team1 = (m.get("team1") or {}).get("teamName", "?")
                team2 = (m.get("team2") or {}).get("teamName", "?")
                group = (m.get("group") or {}).get("groupName", "")
                title = f"{team1} - {team2}"
                description = f"{league_name}: {team1} gegen {team2}"
                if shortcut == "dfb":
                    description += DFB_FREE_TV_NOTE

                for channel_name, access in LEAGUE_CHANNELS.get(shortcut, [("TV", "free")]):
                    events.append(
                        Event(
                            title=title,
                            subtitle=f"{league_name} – {group}" if group else league_name,
                            start=kickoff,
                            channel=channel_name,
                            channel_id=channel_name,
                            provider=self.name,
                            access=access,
                            category=category,
                            description=description,
                        )
                    )

        return events
