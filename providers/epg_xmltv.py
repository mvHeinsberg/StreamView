"""
Allgemeines TV-Programm (alle Sender: öffentlich-rechtlich, privat und
Pay-TV) über eine frei zugängliche XMLTV-EPG-Quelle.

Standardmäßig wird die Deutschland-Datei von epgshare01.online genutzt
(kostenlos, kein Login, täglich aktualisiert, ~250+ deutsche/deutschsprachige
Sender inkl. Sky- und DAZN-Kanälen):
    https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz

Wichtige Einschränkung: Die meisten frei verfügbaren EPG-Feeds decken nur
ca. 1-3 Wochen im Voraus ab (abhängig vom jeweiligen Sender/Datenlieferant),
nicht die vollen 4 Wochen. Für weiter in der Zukunft liegende Termine
liefern die Sport-Provider (openligadb.py, f1.py) bzw. die manuell
gepflegte Liste (manual_events.py) die Daten.

Aus dem riesigen "normalen" TV-Programm (Filme, Serien, Wiederholungen)
filtert dieser Provider gezielt die Sendungen heraus, die nach den
Regeln in config.py als Live-Event gelten (siehe looks_like_live_event()).
Das Ergebnis ist also KEINE vollständige Programmzeitschrift, sondern nur
die darin enthaltenen Live-Sendungen.
"""

from __future__ import annotations

import gzip
import io
import logging
import re
from datetime import datetime, timezone
from typing import Iterator
from xml.etree import ElementTree as ET

import requests

from .base import Event, Provider
import config

log = logging.getLogger(__name__)

# Kann per Umgebungsvariable EPG_XMLTV_URL überschrieben werden, siehe README
# (z.B. um eine andere/eigene EPG-Quelle einzubinden).
DEFAULT_URL = "https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz"

# XMLTV-Zeitformat, z.B. "20260912200000 +0200"
_TIME_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\s*([+-]\d{4})?$")


def _parse_xmltv_time(value: str | None) -> datetime | None:
    if not value:
        return None
    m = _TIME_RE.match(value.strip())
    if not m:
        return None
    year, month, day, hour, minute, second, offset = m.groups()
    dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    if offset:
        sign = 1 if offset[0] == "+" else -1
        oh, om = int(offset[1:3]), int(offset[3:5])
        from datetime import timedelta

        dt = dt.replace(tzinfo=timezone.utc) - sign * timedelta(hours=oh, minutes=om)
    else:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iter_source(url: str, timeout: int) -> bytes:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    raw = resp.content
    if url.endswith(".gz") or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def _iter_programmes(xml_bytes: bytes) -> Iterator[tuple[str, dict]]:
    """Streamt <channel>- und <programme>-Elemente, ohne den ganzen Baum
    im Speicher zu halten (die Datei kann mehrere hundert MB groß sein)."""
    context = ET.iterparse(io.BytesIO(xml_bytes), events=("end",))
    for _, elem in context:
        if elem.tag == "channel":
            cid = elem.get("id", "")
            name_elem = elem.find("display-name")
            name = name_elem.text if name_elem is not None and name_elem.text else cid
            yield "channel", {"id": cid, "name": name}
            elem.clear()
        elif elem.tag == "programme":
            title_elem = elem.find("title")
            subtitle_elem = elem.find("sub-title")
            desc_elem = elem.find("desc")
            cat_elem = elem.find("category")
            yield "programme", {
                "channel_id": elem.get("channel", ""),
                "start": elem.get("start"),
                "stop": elem.get("stop"),
                "title": (title_elem.text or "") if title_elem is not None else "",
                "subtitle": (subtitle_elem.text or "") if subtitle_elem is not None else "",
                "description": (desc_elem.text or "") if desc_elem is not None else "",
                "category": (cat_elem.text or "") if cat_elem is not None else "",
            }
            elem.clear()


class EPGProvider(Provider):
    name = "epg"

    def __init__(self, url: str | None = None, timeout: int = 60):
        import os

        self.url = url or os.environ.get("EPG_XMLTV_URL", DEFAULT_URL)
        self.timeout = timeout

    def fetch(self, start: datetime, end: datetime) -> list[Event]:
        try:
            xml_bytes = _iter_source(self.url, self.timeout)
        except Exception as exc:
            log.warning("EPG: Abruf von %s fehlgeschlagen: %s", self.url, exc)
            return []

        channels: dict[str, str] = {}
        events: list[Event] = []

        try:
            for kind, data in _iter_programmes(xml_bytes):
                if kind == "channel":
                    channels[data["id"]] = data["name"]
                    continue

                channel_name = channels.get(data["channel_id"], data["channel_id"])
                dt_start = _parse_xmltv_time(data["start"])
                if dt_start is None or not (start <= dt_start <= end):
                    continue

                if not config.looks_like_live_event(
                    title=data["title"],
                    subtitle=data["subtitle"],
                    description=data["description"],
                    category=data["category"],
                    channel_name=channel_name,
                ):
                    continue

                dt_stop = _parse_xmltv_time(data["stop"])
                events.append(
                    Event(
                        title=data["title"] or "(ohne Titel)",
                        subtitle=data["subtitle"] or None,
                        start=dt_start,
                        end=dt_stop,
                        channel=channel_name,
                        channel_id=data["channel_id"],
                        provider=self.name,
                        access=config.classify_access(channel_name),
                        category=data["category"] or "Live",
                        description=data["description"] or None,
                    )
                )
        except ET.ParseError as exc:
            log.warning("EPG: XML von %s konnte nicht geparst werden: %s", self.url, exc)

        return events
