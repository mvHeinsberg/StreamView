"""
Zentrale Konfiguration: welche Sender/Plattformen gelten als
"frei empfangbar" bzw. "kostenpflichtig", und mit welchen Stichwörtern
das allgemeine TV-Programm (EPG) als "Live-Event" erkannt wird.

Diese Datei ist bewusst der einzige Ort, an dem du Klassifizierungen
anpassen musst, wenn ein Sender fehlt oder falsch eingeordnet ist.
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------
# Zeitraum
# --------------------------------------------------------------------------
LOOKAHEAD_DAYS = 28  # "kommende 4 Wochen"

# --------------------------------------------------------------------------
# Sender-/Plattform-Klassifizierung
# --------------------------------------------------------------------------
# Kanal-IDs bzw. -Namen (aus der XMLTV-EPG-Quelle, siehe providers/epg_xmltv.py)
# oder Plattform-Namen (aus data/manual_events.yaml), die EINDEUTIG
# kostenpflichtig sind (Abo/PPV), unabhängig davon ob man selbst ein
# Abo hat oder nicht - es geht nur um die Einordnung im Programm.
#
# Groß-/Kleinschreibung wird beim Abgleich ignoriert; Einträge werden als
# "enthalten in" geprüft, d.h. "Sky Sport" matcht auch "Sky Sport 5 HD".
PAID_MARKERS = [
    "sky sport",
    "sky cinema",
    "sky replay",
    "sky select",
    "sky bundesliga",
    "dazn",
    "wow",
    "magentasport",
    "magenta sport",
    "rtl+",
    "rtl plus",
    "joyn plus",
    "joyn+",
    "paramount+",
    "paramount plus",
    "discovery+",
    "eurosport player",
    "premiere",
]

# Sender, die trotz eines "kritischen" Markers (z.B. im Namen) explizit
# FREI empfangbar sind (Whitelist, hat Vorrang vor PAID_MARKERS).
FREE_OVERRIDES = [
    "eurosport",  # lineares Eurosport 1/2 ist frei empfangbar; "Eurosport Player" (oben) ist es nicht
]

# Bekannte frei empfangbare Sender (öffentlich-rechtlich + privat), nur zur
# Dokumentation/Vollständigkeit - alles, was NICHT auf PAID_MARKERS matcht,
# gilt ohnehin standardmäßig als frei empfangbar.
KNOWN_FREE_CHANNELS = [
    "Das Erste", "ARD", "ZDF", "ZDFneo", "ZDFinfo", "3sat", "ARTE",
    "BR", "WDR", "NDR", "HR", "MDR", "RBB", "SWR", "SR", "Phoenix", "KiKA",
    "RTL", "RTLZWEI", "RTL Zwei", "SAT.1", "SAT1", "ProSieben", "VOX",
    "Kabel Eins", "kabel eins", "Super RTL", "SIXX", "n-tv", "Welt", "ntv",
    "DMAX", "Tele 5", "sport1", "Sport1", "Eurosport 1", "Eurosport 2",
]

# --------------------------------------------------------------------------
# Heuristik: welche Programme im allgemeinen EPG als "Live-Event" gelten
# (siehe providers/epg_xmltv.py). Das normale TV-Programm enthält
# überwiegend Nicht-Live-Inhalte (Filme, Serien, Wiederholungen) - wir
# wollen nur die Live-Ereignisse heraus filtern.
# --------------------------------------------------------------------------

# Kategorien/Genres (aus <category> im XMLTV), die auf Live-Inhalt hindeuten.
LIVE_CATEGORIES = [
    "sport",
    "live",
    "fußball", "fussball",
    "formel 1", "motorsport",
    "boxen", "kampfsport", "mma", "ufc",
    "tennis", "handball", "eishockey", "basketball",
    "wahl", "nachrichten-spezial", "sondersendung",
]

# Schlüsselwörter im Titel/Untertitel/Beschreibung, die auf ein Live-Event
# hindeuten - auch wenn die Kategorie nicht gesetzt oder unspezifisch ist.
LIVE_KEYWORDS = [
    "live", "liveshow", "live aus", "live:", "live-",
    "bundesliga", "champions league", "europa league", "conference league",
    "dfb-pokal", "dfb pokal",
    "formel 1", "formel1", "grand prix", "qualifying", "rennen",
    "boxkampf", "boxen live", "ufc", "mma",
    "wahl 2026", "bundestagswahl", "landtagswahl", "hochrechnung",
    "eurovision", "esc ", "grand final",
    "countdown", "sondersendung", "breaking news", "aktuelle stunde live",
]

# Titel-/Kategorie-Muster, die trotz obiger Treffer NICHT als Live-Event
# gelten sollen (z.B. Wiederholungen, Zusammenfassungen, Dokus über Sport).
EXCLUDE_KEYWORDS = [
    "wiederholung", "zusammenfassung", "highlights", "best of",
    "dokumentation", "doku:", "rückblick", "vorschau",
]

# Sender, auf denen praktisch der komplette Sendeplan aus Live-Sport
# besteht - dort wird jedes Programm im Zeitraum als Live-Event gewertet,
# auch ohne Keyword-Treffer (z.B. "Bundesliga Konferenz", einzelne
# Spielbezeichnungen o.ä., die sich nicht generisch matchen lassen).
ALWAYS_LIVE_CHANNEL_MARKERS = [
    "sky sport",
    "dazn",
    "magentasport",
    "sport1",
    "sport 1",
]


# --------------------------------------------------------------------------
# ARD-Radiowellen nach Anstalt (für providers/ard_radio_concerts.py)
# --------------------------------------------------------------------------
# Vollständige(re) Liste aller Radiowellen der ARD-Landesrundfunkanstalten
# plus Deutschlandradio. Wird genutzt, um Konzert-Ankündigungen einer
# externen Programm-Quelle (radio-today.de) einem bekannten ARD-Sender
# zuzuordnen und private/nicht-ARD-Sender herauszufiltern. Alle diese
# Sender sind öffentlich-rechtlich und damit frei empfangbar (Livestreams
# auf den jeweiligen Sender-Websites, ohne Abo).
#
# Bitte ergänzen/korrigieren, falls sich Wellen umbenennen oder du eine
# fehlende Welle entdeckst.
ARD_ANSTALTEN = {
    "WDR": [
        "1LIVE", "WDR 2", "WDR 3", "WDR 4", "WDR 5", "WDR Event", "COSMO",
    ],
    "NDR": [
        "NDR 1 Welle Nord", "NDR 1 Niedersachsen", "NDR 1 Radio MV",
        "NDR 90,3", "NDR 2", "NDR Kultur", "NDR Info", "NDR Info Spezial",
        "N-JOY", "NDR Blue",
    ],
    "BR": [
        "Bayern 1", "Bayern 2", "Bayern 3", "BR-KLASSIK", "B5 aktuell", "PULS",
    ],
    "HR": [
        "hr1", "hr2-kultur", "hr3", "hr4", "YOU FM", "hr-iNFO",
    ],
    "MDR": [
        "MDR SACHSEN", "MDR SACHSEN-ANHALT", "MDR THÜRINGEN", "MDR JUMP",
        "MDR KULTUR", "MDR KLASSIK", "MDR SPUTNIK", "MDR AKTUELL",
    ],
    "RBB": [
        "Antenne Brandenburg", "radioBERLIN 88,8", "rbb24 Inforadio",
        "Fritz", "radio3",
    ],
    "SWR": [
        "SWR1 Baden-Württemberg", "SWR1 Rheinland-Pfalz", "SWR2", "SWR3",
        "SWR4 Baden-Württemberg", "SWR4 Rheinland-Pfalz", "SWR Kultur", "DASDING",
    ],
    "SR": [
        "SR 1 Europawelle", "SR 2 KulturRadio", "SR 3 Saarlandwelle", "UnserDing",
    ],
    "Radio Bremen": [
        "Bremen Eins", "Bremen Zwei", "Bremen Vier",
    ],
    "Deutschlandradio": [
        "Deutschlandfunk", "Deutschlandfunk Kultur", "Deutschlandfunk Nova",
    ],
}


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def classify_access(channel_name: str) -> str:
    """Ordnet einen Sender-/Plattformnamen 'free' oder 'paid' zu.

    Es gewinnt jeweils der LÄNGSTE (also spezifischste) Treffer aus
    PAID_MARKERS bzw. FREE_OVERRIDES. Das löst Fälle wie "Eurosport 1"
    (frei, kein Treffer in PAID_MARKERS) vs. "Eurosport Player" (Treffer
    "eurosport player" in PAID_MARKERS, länger/spezifischer als der
    allgemeine Override "eurosport") korrekt auf, ohne dass die
    Reihenfolge der Listen eine Rolle spielt.
    """
    name = normalize(channel_name)
    paid_matches = [m for m in PAID_MARKERS if m in name]
    if not paid_matches:
        return "free"
    free_matches = [m for m in FREE_OVERRIDES if m in name]
    longest_paid = max(len(m) for m in paid_matches)
    longest_free = max((len(m) for m in free_matches), default=-1)
    return "free" if longest_free > longest_paid else "paid"


def channel_is_always_live(channel_name: str) -> bool:
    name = normalize(channel_name)
    return any(marker in name for marker in ALWAYS_LIVE_CHANNEL_MARKERS)


def looks_like_live_event(*, title: str, subtitle: str = "", description: str = "",
                           category: str = "", channel_name: str = "") -> bool:
    """Heuristik für providers/epg_xmltv.py: ist dieses Programm ein Live-Event?"""
    haystack = normalize(f"{title} {subtitle} {description}")
    cat = normalize(category)

    for excl in EXCLUDE_KEYWORDS:
        if excl in haystack:
            return False

    if channel_is_always_live(channel_name):
        return True

    if any(c in cat for c in LIVE_CATEGORIES):
        return True

    if any(kw in haystack for kw in LIVE_KEYWORDS):
        return True

    return False


def _normalize_station_key(name: str) -> str:
    """Entfernt Leerzeichen/Satzzeichen für einen toleranten Sender-Abgleich
    (z.B. "SR2 Kulturradio" soll "SR 2 KulturRadio" treffen)."""
    return re.sub(r"[^a-z0-9]", "", normalize(name))


_ARD_STATION_LOOKUP: dict[str, tuple[str, str]] = {
    _normalize_station_key(station): (station, anstalt)
    for anstalt, stations in ARD_ANSTALTEN.items()
    for station in stations
}


def match_ard_station(raw_name: str) -> tuple[str, str] | None:
    """Versucht, einen (aus einer externen Quelle gescrapten) Sendernamen
    einer bekannten ARD-Welle zuzuordnen.

    Gibt (offizieller Anzeigename, Anstalt) zurück oder None, wenn der
    Name zu keiner bekannten ARD-Welle passt (z.B. ein privater Sender).
    """
    key = _normalize_station_key(raw_name)
    if not key:
        return None
    if key in _ARD_STATION_LOOKUP:
        return _ARD_STATION_LOOKUP[key]
    # Toleranter Teilstring-Abgleich (z.B. Zusätze wie "HD" oder Ortsangaben)
    for norm_key, value in _ARD_STATION_LOOKUP.items():
        if norm_key in key or key in norm_key:
            return value
    return None
