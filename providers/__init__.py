from .base import Event, Provider
from .openligadb import OpenLigaDBProvider
from .f1 import F1Provider
from .epg_xmltv import EPGProvider
from .manual_events import ManualEventsProvider
from .ard_radio_concerts import ARDRadioConcertsProvider

ALL_PROVIDERS = [
    OpenLigaDBProvider(),
    F1Provider(),
    EPGProvider(),
    ManualEventsProvider(),
    ARDRadioConcertsProvider(),
]

__all__ = [
    "Event",
    "Provider",
    "OpenLigaDBProvider",
    "F1Provider",
    "EPGProvider",
    "ManualEventsProvider",
    "ARDRadioConcertsProvider",
    "ALL_PROVIDERS",
]
