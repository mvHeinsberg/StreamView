"""Gemeinsames Event-Schema und Basisklasse für alle Datenquellen."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    title: str
    start: datetime               # tz-aware, UTC empfohlen
    channel: str                  # Anzeigename, z.B. "Sky Sport Bundesliga 1"
    provider: str                 # z.B. "openligadb", "f1", "epg", "manual", "ard_radio"
    access: str                   # "free" | "paid"
    end: Optional[datetime] = None
    subtitle: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    channel_id: Optional[str] = None
    medium: str = "tv"             # "tv" | "radio" - steuert z.B. das "Radio-Livestream"-Badge im Frontend
    id: Optional[str] = field(default=None)

    def __post_init__(self) -> None:
        if self.access not in ("free", "paid"):
            raise ValueError(f"access muss 'free' oder 'paid' sein, nicht {self.access!r}")
        if self.medium not in ("tv", "radio"):
            raise ValueError(f"medium muss 'tv' oder 'radio' sein, nicht {self.medium!r}")
        if self.id is None:
            basis = f"{self.provider}|{self.channel}|{self.title}|{self.start.isoformat()}"
            self.id = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat() if self.end else None
        return d


class Provider:
    """Basisklasse für eine Datenquelle. Jede Quelle implementiert fetch()."""

    name = "base"

    def fetch(self, start: datetime, end: datetime) -> list[Event]:
        """Liefert alle Events dieser Quelle im Zeitraum [start, end].

        Muss von Unterklassen überschrieben werden. Fehler einzelner
        Quellen dürfen den Gesamtlauf nicht abbrechen - siehe
        update_data.py, das jede Quelle einzeln abfängt.
        """
        raise NotImplementedError
