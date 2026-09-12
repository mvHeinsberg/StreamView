"""
Konzert-Übertragungen auf ARD-Radiowellen (WDR 2, WDR 5, und allen anderen
Wellen der ARD-Landesrundfunkanstalten + Deutschlandradio, siehe
config.ARD_ANSTALTEN).

Es gibt keine offizielle, einheitliche API für "welche ARD-Welle sendet
wann ein Konzert". Dieser Provider nutzt daher die öffentliche
Konzert-Tipps-Übersicht von radio-today.de (https://www.radio-today.de/
tipps.php?TippArt=Konzerte), die redaktionell Konzertsendungen über viele
deutsche Radiosender hinweg zusammenstellt, und filtert daraus die
ARD-Wellen heraus.

WICHTIGE EINSCHRÄNKUNGEN (bitte lesen):
  1. Diese Quelle zeigt üblicherweise nur die aktuelle Woche
     (Montag-Sonntag), NICHT die vollen 4 Wochen im Voraus. Für weiter in
     der Zukunft liegende Konzerte bitte data/manual_events.yaml nutzen
     (Kategorie z.B. "Konzert").
  2. Das Parsing ist Text-/Keyword-basiert (kein offizielles JSON/API),
     weil sich die genaue HTML-Struktur der Quelle nicht aus dieser
     Sandbox heraus prüfen ließ (kein Internetzugriff hier). Falls der
     Parser auf deinem Server 0 Treffer liefert, obwohl die Seite Inhalte
     zeigt, setze die Umgebungsvariable ARD_RADIO_DEBUG=1 - dann wird die
     rohe Seiten-Antwort unter data/_debug/ abgelegt, damit du das Muster
     in _parse_konzerte() unten anpassen kannst.
  3. Es werden nur Sendungen übernommen, deren Sender sich eindeutig
     einer ARD-Welle zuordnen lässt (config.match_ard_station). Private
     Sender (z.B. "radio hbw") auf derselben Seite werden ignoriert.

Alle ARD-Wellen sind öffentlich-rechtlich und daher immer "frei
empfangbar" (access="free") - es gibt keine kostenpflichtigen ARD-Radios.
Es werden bewusst KEINE Links zu den Livestreams gesetzt (siehe
Projektbeschreibung) - nur Sender, Titel, Zeit und Kurzbeschreibung.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from .base import Event, Provider
import config

log = logging.getLogger(__name__)

BASE_URL = "https://www.radio-today.de/tipps.php"
BERLIN = ZoneInfo("Europe/Berlin")
DEBUG_DIR = Path(__file__).resolve().parent.parent / "data" / "_debug"

WEEKDAYS = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag",
]

MONTHS_DE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}

_DATE_RE = re.compile(
    r"(\d{1,2})\.\s*(" + "|".join(MONTHS_DE.keys()) + r")\s*(\d{4})", re.IGNORECASE
)

# Muster: "HH:MM - Sender(, Sender2, ...): "Titel" - Beschreibung"
# bewusst tolerant gehalten. WICHTIG: als Trenner zwischen Sender-Liste und
# Titel wird ausschließlich ein Doppelpunkt erwartet (nicht "-"), weil
# manche Sendernamen selbst einen Bindestrich enthalten (z.B.
# "BR-KLASSIK", "hr2-kultur") - ein Bindestrich als Trenner würde die
# Sender-Liste sonst mittendrin abschneiden.
_ENTRY_RE = re.compile(
    r"(?P<time>[01]?\d|2[0-3])[:.](?P<minute>[0-5]\d)\s*(?:Uhr)?\s*[-–]\s*"
    r"(?P<stations>[A-ZÄÖÜ][^:\n]{1,90}):\s*"
    r"[„\"']?(?P<title>[^„\"'\n]{2,120})[„\"']?"
)


def _extract_date(text: str, fallback: datetime) -> datetime:
    m = _DATE_RE.search(text)
    if not m:
        return fallback
    day, month_name, year = m.groups()
    month = MONTHS_DE.get(month_name.lower())
    if not month:
        return fallback
    try:
        return datetime(int(year), month, int(day), tzinfo=BERLIN)
    except ValueError:
        return fallback


def _parse_konzerte(html: str, page_date: datetime) -> list[dict]:
    text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    results = []
    for m in _ENTRY_RE.finditer(text):
        hour = int(m.group("time"))
        minute = int(m.group("minute"))
        stations_raw = m.group("stations")
        title = m.group("title").strip(" -–\"'„")
        if not title:
            continue
        for station_part in re.split(r",|&|/| und ", stations_raw):
            station_part = station_part.strip()
            if not station_part:
                continue
            match = config.match_ard_station(station_part)
            if not match:
                continue
            display_name, anstalt = match
            try:
                start = page_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            except ValueError:
                continue
            results.append(
                {
                    "title": title,
                    "channel": display_name,
                    "anstalt": anstalt,
                    "start": start,
                }
            )
    return results


class ARDRadioConcertsProvider(Provider):
    name = "ard_radio"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.debug = os.environ.get("ARD_RADIO_DEBUG") == "1"

    def _fetch_page(self, weekday: str | None) -> tuple[str, datetime] | None:
        params = {"TippArt": "Konzerte"}
        if weekday:
            params["Wochentag"] = weekday
        try:
            resp = requests.get(BASE_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as exc:
            log.warning("ARD-Radio-Konzerte: Abruf (Wochentag=%s) fehlgeschlagen: %s", weekday, exc)
            return None

        if self.debug:
            DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            fname = f"radio_today_{weekday or 'heute'}.html"
            (DEBUG_DIR / fname).write_text(resp.text, encoding="utf-8")

        fallback_date = datetime.now(BERLIN)
        page_date = _extract_date(resp.text, fallback_date)
        return resp.text, page_date

    def fetch(self, start: datetime, end: datetime) -> list[Event]:
        events: list[Event] = []
        seen_pages: set[str] = set()

        # Die Quelle bietet i.d.R. nur die aktuelle Woche an (Mo-So) - wir
        # fragen "heute" (Default) plus alle Wochentage einmal ab. Für
        # Termine außerhalb dieses Fensters liefert diese Quelle nichts;
        # das ist eine bekannte Einschränkung (siehe Modul-Docstring).
        pages_to_try = [None, *WEEKDAYS]

        for weekday in pages_to_try:
            result = self._fetch_page(weekday)
            if result is None:
                continue
            html, page_date = result
            cache_key = f"{page_date.date()}"
            if cache_key in seen_pages:
                continue  # gleiche Seite (z.B. "heute" == "Mittwoch") nicht doppelt parsen
            seen_pages.add(cache_key)

            entries = _parse_konzerte(html, page_date)
            for entry in entries:
                dt = entry["start"]
                if not (start <= dt <= end):
                    continue
                events.append(
                    Event(
                        title=entry["title"],
                        start=dt,
                        channel=entry["channel"],
                        channel_id=entry["channel"],
                        provider=self.name,
                        access="free",
                        category="Konzert",
                        medium="radio",
                        description=(
                            f"Konzert-Livesendung auf {entry['channel']} ({entry['anstalt']}). "
                            f"Quelle: radio-today.de"
                        ),
                    )
                )

        if not events:
            log.info(
                "ARD-Radio-Konzerte: keine Treffer gefunden. Das kann daran liegen, dass gerade "
                "keine Konzerte anstehen - oder dass sich das Seitenformat geändert hat. "
                "Mit ARD_RADIO_DEBUG=1 die rohe Seite in data/_debug/ speichern und "
                "_parse_konzerte() in providers/ard_radio_concerts.py bei Bedarf anpassen."
            )

        return events
