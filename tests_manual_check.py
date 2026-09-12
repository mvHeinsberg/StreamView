"""
Kein offizielles Test-Framework, sondern ein schneller Selbstcheck der
Kernlogik mit synthetischen Daten - die Sandbox, in der dieses Projekt
entstanden ist, hat keinen Zugriff auf externe APIs/Webseiten. Auf einem
Server mit normalem Internetzugang lässt sich stattdessen einfach
`python3 update_data.py` gegen die echten Quellen laufen.

Prüft:
  1. config.classify_access() / looks_like_live_event() Heuristiken
  2. providers/epg_xmltv.py: Parsing einer kleinen Beispiel-XMLTV-Datei
  3. providers/manual_events.py: Laden der YAML-Beispiel-Events
  4. update_data.py: Deduplizierung + JSON-Export mit gemischten Quellen
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
from providers.epg_xmltv import _iter_programmes, _parse_xmltv_time
from providers.manual_events import ManualEventsProvider
from providers.ard_radio_concerts import _parse_konzerte, _extract_date
from providers.base import Event
from update_data import deduplicate

FAILED = []


def check(label: str, condition: bool):
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILED.append(label)


# 1) Heuristiken -------------------------------------------------------
check("Sky Sport -> paid", config.classify_access("Sky Sport Bundesliga 1 HD") == "paid")
check("DAZN -> paid", config.classify_access("DAZN 1") == "paid")
check("Das Erste -> free", config.classify_access("Das Erste HD") == "free")
check("Eurosport (linear) -> free trotz 'sport'-Marker-Nachbarschaft",
      config.classify_access("Eurosport 1") == "free")
check("Eurosport Player -> paid", config.classify_access("Eurosport Player") == "paid")

check(
    "Bundesliga-Titel wird als Live-Event erkannt",
    config.looks_like_live_event(title="Bundesliga: FC Bayern - BVB", category="Sport", channel_name="Sky Sport"),
)
check(
    "Tagesschau (kein Sport/Live-Keyword) wird NICHT als Live-Event erkannt",
    not config.looks_like_live_event(title="Tagesschau", category="Nachrichten", channel_name="Das Erste"),
)
check(
    "Alles auf Sky Sport zählt als live (Always-Live-Channel)",
    config.looks_like_live_event(title="Irgendein Programmtitel", category="", channel_name="Sky Sport Bundesliga 1"),
)
check(
    "Wiederholung wird trotz Sport-Kategorie ausgeschlossen",
    not config.looks_like_live_event(title="Bundesliga Highlights (Wiederholung)", category="Sport", channel_name="Sport1"),
)

# 2) XMLTV-Parsing -------------------------------------------------------
SAMPLE_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="Sky.Sport.Bundesliga.1.de">
    <display-name>Sky Sport Bundesliga 1</display-name>
  </channel>
  <channel id="Das.Erste.de">
    <display-name>Das Erste</display-name>
  </channel>
  <programme start="{{start}}" stop="{{stop}}" channel="Sky.Sport.Bundesliga.1.de">
    <title>Bundesliga Live: FC Bayern - Borussia Dortmund</title>
    <category>Sport</category>
    <desc>Der Top-Ansetzung des Spieltags.</desc>
  </programme>
  <programme start="{{start}}" stop="{{stop}}" channel="Das.Erste.de">
    <title>Tagesschau</title>
    <category>Nachrichten</category>
  </programme>
</tv>
"""

now = datetime.now(timezone.utc)
xmltv_fmt = "%Y%m%d%H%M%S %z"
start_str = (now + timedelta(days=1)).strftime(xmltv_fmt)
stop_str = (now + timedelta(days=1, hours=2)).strftime(xmltv_fmt)
xml_bytes = SAMPLE_XML.format(start=start_str, stop=stop_str).encode("utf-8")

parsed = list(_iter_programmes(xml_bytes))
channels = {d["id"]: d["name"] for k, d in parsed if k == "channel"}
programmes = [d for k, d in parsed if k == "programme"]

check("XMLTV: 2 Sender geparst", len(channels) == 2)
check("XMLTV: 2 Sendungen geparst", len(programmes) == 2)
check("XMLTV: Zeit korrekt geparst (tz-aware, ca. jetzt+1 Tag)",
      abs((_parse_xmltv_time(programmes[0]["start"]) - (now + timedelta(days=1))).total_seconds()) < 5)

# 3) Manuelle Events -----------------------------------------------------
manual_provider = ManualEventsProvider()
manual_events = manual_provider.fetch(now, now + timedelta(days=28))
check(f"Manuelle YAML-Beispiel-Events geladen ({len(manual_events)} im 4-Wochen-Fenster)",
      len(manual_events) >= 1)
if manual_events:
    check("Manuelles Event hat gültiges Access-Feld", manual_events[0].access in ("free", "paid"))

# 4) Deduplizierung + JSON-Export ---------------------------------------
e1 = Event(title="FC Bayern - BVB", start=now + timedelta(days=2), channel="Sky Sport", provider="epg", access="paid")
e2 = Event(title="FC Bayern - BVB", start=now + timedelta(days=2), channel="Sky Sport", provider="openligadb", access="paid")
e3 = Event(title="FC Bayern - BVB", start=now + timedelta(days=2), channel="DAZN", provider="openligadb", access="paid")
deduped = deduplicate([e1, e2, e3])
check("Deduplizierung: identisches Event (gleicher Sender+Titel+Zeit) wird zusammengeführt", len(deduped) == 2)

# 5) ARD-Radio-Konzerte -----------------------------------------------
check(
    "match_ard_station erkennt 'WDR 2' (exakt)",
    config.match_ard_station("WDR 2") == ("WDR 2", "WDR"),
)
check(
    "match_ard_station erkennt 'SR2 Kulturradio' (toleranter Abgleich)",
    config.match_ard_station("SR2 Kulturradio") is not None
    and config.match_ard_station("SR2 Kulturradio")[0] == "SR 2 KulturRadio",
)
check(
    "match_ard_station lehnt privaten Sender ab",
    config.match_ard_station("radio hbw") is None,
)

SAMPLE_HTML = """
<html><body>
<h2>Konzerttipps am Mittwoch, 17. September 2026</h2>
<div class="tipp">
  <h3>13:05 - SWR Kultur: "Mittagskonzert" - Werke von Bach und Vivaldi.</h3>
</div>
<div class="tipp">
  <h3>18:00 - radio hbw: "Live Lounge unplugged" - Akustik-Gitarre.</h3>
</div>
<div class="tipp">
  <h3>20:03 - WDR 3, BR-KLASSIK, SR 2 KulturRadio: "ARD Konzert" - Gewandhausorchester live.</h3>
</div>
</body></html>
"""
page_date = _extract_date(SAMPLE_HTML, datetime.now(timezone.utc))
check("Datum aus Beispiel-HTML korrekt extrahiert (17.09.2026)",
      (page_date.year, page_date.month, page_date.day) == (2026, 9, 17))

parsed = _parse_konzerte(SAMPLE_HTML, page_date)
parsed_channels = {p["channel"] for p in parsed}
check(
    "Radio-Parser findet SWR Kultur, WDR 3 und SR 2 KulturRadio, aber nicht 'radio hbw'",
    {"SWR Kultur", "WDR 3", "SR 2 KulturRadio"} <= parsed_channels
    and "radio hbw" not in parsed_channels,
)
check("Radio-Parser: mind. 4 ARD-Treffer (Mehrfach-Sender-Zeile zählt pro Sender)", len(parsed) >= 4)

payload = {"events": [e.to_dict() for e in deduped]}
try:
    json.dumps(payload, ensure_ascii=False)
    check("JSON-Serialisierung funktioniert", True)
except Exception:
    check("JSON-Serialisierung funktioniert", False)

print()
if FAILED:
    print(f"{len(FAILED)} Check(s) fehlgeschlagen: {FAILED}")
    sys.exit(1)
print("Alle Checks OK.")
