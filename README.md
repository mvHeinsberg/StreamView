# LIVE Stream Übersicht

Eine selbst gehostete Web-App im Stil einer TV-Zeitschrift, die anstehende
**Live-Events** aller deutschen Sender (öffentlich-rechtlich + privat) der
kommenden 4 Wochen anzeigt – aufgeteilt in zwei Tabs:

- **Frei empfangbar** – ARD/ZDF, Dritte, RTL/SAT.1/ProSieben/VOX & Co.
  (inkl. Radio-Livestream-Konzerte aller ARD-Wellen, z.B. WDR 2, WDR 5, WDR 3, …)
- **Kostenpflichtig** – Sky, DAZN, RTL+, WOW, MagentaSport & Co.

Radio-Events sind im Frontend zusätzlich mit einem 📻-Badge
("Radio-Livestream") gekennzeichnet und über den Filter "Nur
Radio-Livestream" separat auffindbar.

Es werden **keine Links zu Streams** gesetzt und **keine Inhalte** bereit-
gestellt – die App ist eine reine Informationsübersicht (wer sendet was,
wann, auf welchem Sender/welcher Plattform).

---

## Wie es funktioniert

```
providers/          – eine Datei pro Datenquelle, liefert Events
  openligadb.py        Fußball (1./2. Bundesliga, DFB-Pokal) – kostenlose API
  f1.py                 Formel 1 – kostenlose API
  epg_xmltv.py          Alle Sender / allgemeines TV-Programm, gefiltert auf Live-Events
  ard_radio_concerts.py Konzerte auf ARD-Radiowellen (WDR 2/5/3, NDR, BR, HR, MDR, RBB, SWR, SR, DLR, …)
  manual_events.py       Manuell gepflegte Liste (Streaming-Exklusivevents, Sonderfälle)

config.py            – zentrale Klassifizierung: Sender -> frei/kostenpflichtig,
                        Keywords zur Live-Erkennung im allgemeinen TV-Programm

update_data.py        – fragt alle Quellen ab, führt zusammen, schreibt
                         data/events.json

web/                  – statisches Frontend (HTML/CSS/JS), liest events.json
```

Jede Quelle wird einzeln abgefragt und Fehler einer Quelle (z.B. eine API
ist mal kurz nicht erreichbar) stoppen nicht den ganzen Lauf – die übrigen
Quellen liefern trotzdem ihre Daten.

### Woher kommen die Daten – und wo sind die Grenzen?

Es gibt **keine einzelne kostenlose Quelle**, die "alle Live-Events aller
deutschen Sender inkl. Streaming-Exklusivinhalte für 4 Wochen im Voraus"
liefert. Deshalb kombiniert die App mehrere Quellen, jede mit eigenen
Stärken/Grenzen:

| Quelle | Deckt ab | Grenzen |
|---|---|---|
| **OpenLigaDB** (`openligadb.py`) | Bundesliga, 2. Liga, DFB-Pokal – strukturierte, verlässliche Ansetzungen, oft Wochen im Voraus | Nur Fußball; Sender-Zuordnung ist in `config.py`/`openligadb.py` hinterlegt (Rechte können sich ändern – bitte gelegentlich prüfen) |
| **Jolpica F1 API** (`f1.py`) | Formel-1-Rennwochenenden (Training/Quali/Rennen), volle Saison im Voraus | Nur Formel 1 |
| **XMLTV-EPG** (`epg_xmltv.py`) | Alles, was im "normalen" TV-Programm läuft – über **~250 deutsche Sender** inkl. Sky- und DAZN-Kanälen, per Default von [epgshare01.online](https://epgshare01.online) (kostenlos, kein Login) | EPG-Daten reichen bei den meisten frei verfügbaren Quellen nur **~1–3 Wochen** im Voraus, nicht immer die vollen 4 Wochen. Ob ein Programm "live" ist, wird per Stichwort-/Kategorie-Heuristik in `config.py` geraten – nicht jede Quelle markiert das explizit. Bitte `LIVE_KEYWORDS`/`LIVE_CATEGORIES` bei Bedarf ergänzen. |
| **ARD-Radio-Konzerte** (`ard_radio_concerts.py`) | Konzert-Livesendungen auf **allen** ARD-Radiowellen (siehe `config.ARD_ANSTALTEN` – WDR, NDR, BR, HR, MDR, RBB, SWR, SR, Radio Bremen, Deutschlandradio), über die Konzert-Tipps-Seite von [radio-today.de](https://www.radio-today.de/tipps.php?TippArt=Konzerte) (kostenlos, kein Login) | Diese Quelle zeigt i.d.R. nur die **aktuelle Woche**, nicht die vollen 4 Wochen. Das Parsing ist Text-/Keyword-basiert (siehe Docstring in der Datei) und dadurch etwas fragiler als die anderen Quellen – bei 0 Treffern hilft `ARD_RADIO_DEBUG=1` (siehe unten). Konzerte weiter in der Zukunft: in `data/manual_events.yaml` mit `medium: "radio"` eintragen. |
| **Manuelle Liste** (`manual_events.py`, `data/manual_events.yaml`) | Alles, was die anderen Quellen nicht abdecken: Streaming-exklusive Events auf RTL+/Joyn/WOW/MagentaSport (die nicht im normalen TV-Programm laufen), Box-/UFC-Kämpfe, Award-Shows, Wahlabende, weiter in der Zukunft liegende Radio-Konzerte usw. | Muss von Hand gepflegt werden – es gibt für diese Fälle keine freie API. Die mitgelieferten Beispiele sind **Platzhalter**, keine echten Termine (siehe Kommentare in der Datei). |

**Kurz gesagt:** Sport (Fußball, Formel 1) ist zuverlässig und weit im
Voraus automatisiert. Das breite "alles was live läuft"-Programm über alle
Sender ist automatisiert, aber mit den genannten Grenzen bei Reichweite und
Live-Erkennung. ARD-Radio-Konzerte werden für die aktuelle Woche automatisch
gesucht. Streaming-exklusive Sonderevents und weiter vorausliegende
Radio-Konzerte brauchen weiterhin manuelle Pflege – dafür ist
`data/manual_events.yaml` da.

### ARD-Radio-Konzerte debuggen

Falls `ard_radio_concerts.py` auf deinem Server 0 Treffer liefert, obwohl
gerade Konzerte laufen sollten, kannst du dir die rohe Antwort der Quelle
speichern lassen und danach das Muster in `_parse_konzerte()` in
`providers/ard_radio_concerts.py` anpassen:

```bash
ARD_RADIO_DEBUG=1 python3 update_data.py
# rohe HTML-Antworten liegen danach in data/_debug/
```

---

## Installation

Voraussetzung: Python 3.10+.

```bash
cd live-events-app
pip install -r requirements.txt
```

### Daten einmalig abrufen

```bash
python3 update_data.py
```

Das erzeugt `data/events.json`. Beim ersten Lauf lohnt sich ein Blick ins
Log – falls eine Quelle nicht erreichbar ist (z.B. weil dein Server keinen
Internetzugang hat oder eine API gerade down ist), wird das dort vermerkt,
ohne den Lauf abzubrechen.

### Seite lokal ansehen

Die Seite muss über **einen Webserver** aufgerufen werden (nicht per
Doppelklick als `file://…`), sonst blockiert der Browser das Nachladen von
`data/events.json`:

```bash
python3 -m http.server 8000
# dann im Browser: http://localhost:8000/web/
```

Für den produktiven Betrieb reicht jeder normale Webserver (nginx, Apache,
Caddy, …), der den Projektordner ausliefert – die App ist rein statisch
(HTML/CSS/JS + eine JSON-Datei), es ist **kein** Python-Prozess nötig, um
die Seite selbst auszuliefern. Python wird nur für die Datenaktualisierung
gebraucht (`update_data.py`).

### Vorschau als einzelne HTML-Datei (kein Server nötig)

Willst du dir das Layout/Design nur ansehen oder Änderungswünsche
markieren, ohne einen Server zu starten, erzeugt `build_preview.py` eine
einzige, eigenständige `preview.html` mit eingebetteten Daten – lässt sich
per Doppelklick direkt im Browser öffnen:

```bash
python3 update_data.py     # falls noch nicht geschehen
python3 build_preview.py
# preview.html im Browser öffnen
```

Diese Datei ist nur ein Schnappschuss zum Anschauen (die Daten sind
eingebettet, kein Live-Nachladen) – die eigentliche App bleibt `web/`.

### Automatische, regelmäßige Aktualisierung

Im Ordner `cron/` liegen zwei fertige Vorlagen – nutze, was zu deinem
Server passt:

**Cron** (`cron/update-events.cron`): Pfad anpassen, dann per `crontab -e`
einfügen. Läuft standardmäßig alle 6 Stunden.

**systemd-Timer** (`cron/live-events-update.service` + `.timer`): Pfade
anpassen, dann nach `/etc/systemd/system/` kopieren und aktivieren:

```bash
sudo systemctl enable --now live-events-update.timer
```

Wie oft eine Aktualisierung sinnvoll ist, hängt von der Quelle ab – die
EPG-Datei wird i.d.R. täglich neu erzeugt, Sport-Ansetzungen ändern sich
selten kurzfristig. Alle 6 Stunden ist ein guter Kompromiss zwischen
Aktualität und Server-/API-Last.

---

## Eigene Termine ergänzen

Trag Streaming-exklusive Events, Box-/UFC-Kämpfe, Award-Shows usw. in
`data/manual_events.yaml` ein (Format und Beispiele stehen in der Datei
selbst und in `providers/manual_events.py`). Die Platzhalter-Einträge dort
solltest du vor dem produktiven Einsatz durch echte, geprüfte Termine
ersetzen oder entfernen.

## Sender-Klassifizierung anpassen

Falls ein Sender falsch als frei/kostenpflichtig eingeordnet wird oder
fehlt, ist `config.py` der einzige Ort, den du anpassen musst
(`PAID_MARKERS`, `FREE_OVERRIDES`). Für die Live-Erkennung im allgemeinen
TV-Programm sind `LIVE_KEYWORDS`, `LIVE_CATEGORIES`, `EXCLUDE_KEYWORDS` und
`ALWAYS_LIVE_CHANNEL_MARKERS` zuständig. Die Liste aller ARD-Radiowellen
(für die Konzert-Suche) steht in `ARD_ANSTALTEN`, ebenfalls in `config.py`.

## Andere EPG-Quelle nutzen

`providers/epg_xmltv.py` nutzt standardmäßig die Deutschland-XMLTV-Datei
von epgshare01.online. Willst du eine andere Quelle (z.B. eine eigene
oder eine mit mehr Vorlauf), setze die Umgebungsvariable `EPG_XMLTV_URL`
auf eine andere XMLTV-URL (`.xml` oder `.xml.gz`):

```bash
EPG_XMLTV_URL="https://example.org/mein-epg.xml.gz" python3 update_data.py
```

---

## Selbstcheck der Kernlogik

`tests_manual_check.py` prüft die Klassifizierungs-Heuristiken, das
XMLTV-Parsing, die manuelle Event-Liste und die Zusammenführung/
Deduplizierung mit synthetischen Beispieldaten (kein Netzwerkzugriff
nötig):

```bash
python3 tests_manual_check.py
```

---

## Rechtlicher Hinweis

Diese App zeigt ausschließlich **öffentlich bekannte Programm-/Sende-
informationen** (wer überträgt was, wann) an. Es werden weder Links zu
Streams noch Streaming-Inhalte selbst bereitgestellt. Die genutzten
Datenquellen (OpenLigaDB, Jolpica-F1, öffentlich zugängliche EPG-Feeds,
radio-today.de) liefern ausschließlich Metadaten, keine geschützten
Inhalte.
