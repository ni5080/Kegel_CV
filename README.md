# Kegel_CV — Automatische Kegelerfassung aus Video

Lokale Desktop-Anwendung, die aus Kegelbahn-Videos (FUNK-Anzeigetafeln, 4 Bahnen)
jeden Wurf automatisch erfasst: gefallene Kegel, Anzahl, Wurfnummer, laufende
Summe und Zwischensummen nach je 15 Würfen.

Leitgedanke: **robust, nachvollziehbar und debugbar** — nicht „möglichst viel KI".
Jedes Ergebnis kann erklären, wie es zustande kam.

---

## Schnellstart

Einmalig nach dem Klonen — ohne diesen Schritt findet Python das Paket nicht:

```bash
.venv/Scripts/python.exe -m pip install -e .
```

```bash
.venv/Scripts/python.exe -m kegel_cv.main
```

Mit direktem Videostart:

```bash
.venv/Scripts/python.exe -m kegel_cv.main --video "kegelVideos/2026-08-22 09-15-50.mp4"
```

Tests:

```bash
.venv/Scripts/python.exe -m pytest tests/unit -q
```

---

## Bedienung

### 1. Video laden
Rechts oben ein Video auswählen und auf **Laden** klicken (oder `Datei → Video öffnen`).

| Taste | Wirkung |
|---|---|
| `Leertaste` | Wiedergabe / Pause |
| `→` | ein Frame vor |
| `←` | ein Frame zurück |
| `Esc` | Kalibrierschritt abbrechen |

### 2. Bahn kalibrieren
Auf **Bahn n kalibrieren** klicken, dann die vier Ecken der Anzeigetafel anklicken —
in dieser Reihenfolge:

```
   1 o-----------o 2      1 = oben links
     |           |        2 = oben rechts
     |  TAFEL    |        3 = unten rechts
   4 o-----------o 3      4 = unten links
```

Die Reihenfolge ist verbindlich. Wird sie vertauscht, meldet die Anwendung das
sofort, statt ein verdrehtes Tafelbild zu erzeugen. Mit **Punkt zurück** lässt sich
der letzte Klick rückgängig machen.

### 3. Bereiche setzen
Nach den Ecken sind alle 15 Bereiche bereits sinnvoll vorbelegt (gemessen am
realen Material). Zum genauen Setzen:

- **Bereiche anklicken (14)** — führt nacheinander durch alle Bereiche.
  Jeweils in die **Mitte** des Elements klicken:
  Kegellampe 1…9 → grüne Lampe → Kegelanzahl → Wurfnummer → Summe A → Summe B
- **nur Raute** — setzt ausschließlich die neun Kegellampen neu
- **überspringen** — lässt den aktuellen Bereich unverändert
- Über die Auswahlliste lässt sich jeder Bereich einzeln neu setzen

Ein Klick außerhalb der Tafel wird abgelehnt statt an den Rand geschoben —
eine falsch platzierte ROI würde sonst erst bei der Erkennung auffallen.

### 4. Live-Analyse

**Analyse starten** wertet das Video durchgehend aus und zeigt pro Bahn live:
grüne Lampe mit Score, Zustand der Zustandsmaschine und die gefallenen Kegel als
Raute. Das Tempo ist umschaltbar (Echtzeit / halb / so schnell wie möglich) —
beim Zuschauen ist Echtzeit meist nützlicher als Vollgas.

Erkannte Würfe erscheinen live in den Tabellen — mit Wurfnummer, Zyklusposition,
Kegelzahl, laufender Summe und Status (farbig hinterlegt). Ein Tooltip auf jeder
Zeile zeigt die vollständige Begründung: welche Frames, welche Messwerte, welche
Prüfungen.

Gemessen an `2026-08-22 09-24-46.mp4`: **1,8 ms pro Frame** für vier Bahnen
inklusive Debug-Ausgabe, **27 Würfe in 4 Minuten Video, alle Summenketten
stimmig**.

**Kalibrierung prüfen** misst die grünen Lampen über mehrere hundert Frames und
meldet pro Bahn, ob das Signal trägt:

```
Bahn 2: SCHWACH  (Score 27-59) -- nur 1 Frame im Zustand AN (Minimum 3),
                  vermutlich Rauschen statt echtem Wechsel; ROI bitte prüfen.
Bahn 3: OK       (Score 20-75) -- klarer Wechsel erkannt (44 AN / 78 AUS)
Bahn 4: KEIN WECHSEL -- durchgehend AUS, auf dieser Bahn wurde nicht geworfen
```

Das lohnt sich direkt nach dem Kalibrieren: Eine ungenau gesetzte ROI erzeugt
keinen Fehler, sondern ein schwaches Signal — die Analyse läuft dann scheinbar,
erkennt aber nie einen Wurf.

### 5. Kalibrierung speichern
**Speichern** legt die Kalibrierung in `data/calibrations/` ab. Sie enthält die
Videomaße, sodass beim Laden gewarnt wird, wenn sie nicht zum Video passt.

> **Wichtig:** Die Overlay-Position unterscheidet sich zwischen Aufnahme-Sessions
> (nachgemessen). Deshalb wird zu Beginn jedes Videos neu kalibriert bzw. die
> passende gespeicherte Kalibrierung geladen.

---

## Aufbau

```
Video → Frames → 4 Bahnen → ROIs → zeitliche Zustandsanalyse
      → Ereignis → Frame-Sampling → Lampen/Ziffern → Wurfergebnis
      → Plausibilitätsprüfung → GUI / Log / später API
```

```
src/kegel_cv/
├── config/       Konfiguration (YAML + Validierung)
├── models/       Datenmodelle, Zähl- und Zykluslogik
├── video/        VideoSource-Abstraktion (Datei heute, Stream später)
├── calibration/  Homographie, ROIs, Persistenz
├── detection/    Detektoren (Phase 4–7)
├── analysis/     Sampling, Aggregation, Validierung (Phase 8–9)
├── debug/        Frame- und Event-Logging
├── sinks/        Ergebnisausgabe (API vorbereitet, nicht gebaut)
└── gui/          PySide6-Oberfläche
```

Ausführlich: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Konfiguration

Alle Parameter stehen in [`config/default.yaml`](config/default.yaml) — mit
Begründung, und bei gemessenen Werten mit dem Messbeleg. Im Code stehen keine
Magic Numbers.

```yaml
detection:
  green:
    on_threshold: 45.0   # gemessen: AUS 17-24, AN 60-74 -> Mitte mit Reserve
    off_threshold: 35.0  # Hysterese gegen Flattern bei Rauschen
```

---

## Dokumentation

| Datei | Inhalt |
|---|---|
| [`docs/VIDEO_ANALYSIS.md`](docs/VIDEO_ANALYSIS.md) | **Gemessene** Fakten über Material und Anzeigetafel |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architektur und Technologieentscheidungen |
| [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) | Offene fachliche Fragen (bewusst nicht geraten) |
| [`.claude/skills/ORCHESTRATION.md`](.claude/skills/ORCHESTRATION.md) | Projektzustand, Phasenplan, Skill-Landkarte |
| [`.claude/skills/BUG_ORCHESTRATION.md`](.claude/skills/BUG_ORCHESTRATION.md) | Wie aus Bugs dauerhafter Schutz wird |

---

## Werkzeuge

```bash
# ROI-Platzierung visuell prüfen (Ergebnisse in debug/roi_check/)
.venv/Scripts/python.exe tools/verify_rois.py --frame 90

# gegen eine gespeicherte Kalibrierung
.venv/Scripts/python.exe tools/verify_rois.py --calibration data/calibrations/meine.json
```

---

## Stand

| Phase | Inhalt | Status |
|---|---|---|
| 0 | Analyse von Material und Anzeigetafel | ✅ |
| 1 | Video-Player | ✅ |
| 2 | Kalibrierung (Ecken, Homographie, Speichern) | ✅ |
| 3 | ROI-Konfiguration per Klick, mit Zoom | ✅ |
| 4 | Grünlampen-Erkennung, Zustandsmaschine | ✅ |
| 5 | Frame-Sampling rund um das Ereignis | ✅ |
| 6 | Lampenerkennung (9 Kegel) | ✅ |
| 7 | Ziffernerkennung (7-Segment) | 🔨 ~60 %, siehe `docs/VIDEO_ANALYSIS.md` |
| 8 | Wurferkennung, Double-Counting-Schutz | ✅ |
| 9 | Summen und 15-Wurf-Zyklen | ✅ |
| 10 | Live-Analyse mit Wurftabellen | ✅ |
| 11 | Robustheit & Performance | offen |
| 12 | API-Anbindung | bewusst zurückgestellt |

---

## Voraussetzungen

Python 3.10+, Abhängigkeiten in [`pyproject.toml`](pyproject.toml):
OpenCV, NumPy, PySide6, PyYAML, pydantic. GPU wird nicht vorausgesetzt.
