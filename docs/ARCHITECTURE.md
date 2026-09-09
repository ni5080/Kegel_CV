# Architektur und Technologieentscheidungen

> Stand: 2026-08-24 · Ergänzend: `.claude/skills/kegel-architektur/SKILL.md`

---

## 1. Grundentscheidung: billige Trigger steuern teure Analyse

Der naheliegende, aber falsche Weg wäre, jedes Frame durch ein Modell zu schicken.
Bei 25 fps, 4 Bahnen und einem 2,3-GB-Video ist das weder nötig noch bezahlbar.

```
JEDES Frame:     grüne Lampe prüfen   4 ROIs à ~60 px      ~0,1 ms
NUR bei Event:   Kegellampen          4 × 9 ROIs           ~1 ms
NUR bei Event:   Ziffern              Segment-Dekodierung  ~5 ms
NIE pro Frame:   ML-Modelle
```

Die grüne Lampe ist der Torwächter: Sie kostet fast nichts und entscheidet, wann
sich der teure Teil lohnt. Budget: 40 ms pro Frame (25 fps).

---

## 2. Schichten

```
        gui/                    ← darf alles darunter nutzen
          │
     analysis/                  ← orchestriert, kennt keine GUI
          │
   detection/  video/  calibration/
          │
      models/  config/  debug/  ← kennen nichts über sich
```

Abhängigkeiten zeigen **immer nach unten**. Das ist keine Stilfrage:

- `detection/` ohne Qt ⇒ Erkennung ist ohne GUI testbar
- `analysis/` ohne `cv2.VideoCapture` ⇒ Livestream später ohne Umbau
- `models/` ohne OpenCV ⇒ Zähllogik testbar ohne Bildverarbeitung

`tests/unit/test_architecture.py` prüft das automatisch per AST-Analyse. Ein
Verstoß bricht die Tests, statt nur eine Regel in einem Dokument zu verletzen.

---

## 3. Technologieentscheidungen

| Bereich | Gewählt | Begründung | Verworfen |
|---|---|---|---|
| Sprache | **Python 3.10+** | OpenCV-Ökosystem, schnelle Iteration, vom Nutzer eingesetzt | C++ (Iterationsgeschwindigkeit zählt hier mehr als Laufzeit) |
| Bildverarbeitung | **OpenCV** | Standard für Homographie, Decoding, ROI-Operationen | scikit-image (weniger Videounterstützung) |
| GUI | **PySide6 (Qt)** | Native Desktop-Oberfläche, LGPL, mächtiges Zeichnen für Overlays | Tkinter (zu schwach für Video+Overlays), Web-GUI (zusätzliche Schicht ohne Gewinn) |
| Video-Decoding | **OpenCV** (`VideoCapture`) | Genügt für lokale MP4 | PyAV — wird für Streams relevant, nicht vorher |
| Konfiguration | **YAML + pydantic** | Lesbar für Menschen, validiert beim Laden statt beim ersten Zugriff | JSON (keine Kommentare — bei einer Datei voller begründeter Schwellwerte untragbar) |
| Ziffernerkennung | **7-Segment-Dekodierung** geplant | Die Displays sind 7-Segment, keine Schrift. Jede Entscheidung ist auf ein Segment zurückführbar | OCR (auf Fließtext trainiert), ML (unverhältnismäßig, Stufe 5) |
| Tests | **pytest** | Parametrisierung, Fixtures | unittest |

### Warum kein ML (jetzt)

Der Auftrag ist eindeutig (§8, §27): Erst klassische Verfahren. Die Messungen
stützen das — die grüne Lampe trennt mit Score 17–24 (aus) gegen 60–74 (an)
völlig eindeutig. Ein Modell würde hier nichts verbessern, aber Nachvollziehbarkeit,
Geschwindigkeit und Debugbarkeit kosten.

Eskalationsstufen (jede erst, wenn die vorige **gemessen** versagt):
```
1. Schwellwert auf ROI-Statistik → 2. Template Matching
→ 3. Segment-Dekodierung → 4. OCR → 5. ML
```

Die Architektur hält den Wechsel offen: Jeder Detektor steckt hinter einem
Protocol, die Auswahl erfolgt über eine Konfigzeile (`implementation: "hsv"`),
nicht über einen Codeumbau.

---

## 4. Zwei Koordinatensysteme

```
FRAME-KOORDINATEN                  TAFELKOORDINATEN
Pixel im Video (1920×1080)   ←→    normiert 0..1 je Tafel
        │      Homographie H (pro Bahn)      │
```

**ROIs werden ausschließlich normiert gespeichert.** Grund ist eine Messung:
Die Overlay-Position unterscheidet sich zwischen Aufnahme-Sessions (2024:
Grünlampen bei x≈538/1079/1378, 2026: x≈572/876/1105/1399), und die vier Tafeln
sind unterschiedlich groß und perspektivisch verzerrt. Pixelkoordinaten wären
für genau ein Video richtig.

Im Hot Path wird **nicht** die ganze Tafel entzerrt (~1 ms × 4 Bahnen × 25 fps),
sondern nur die ROI-Eckpunkte zurückgerechnet. Für eine 6×8-px-Lampe ist die
Entzerrung ohnehin bedeutungslos.

---

## 5. Vier unabhängige Bahnen

Die Spieler werfen nicht synchron — belegt durch Messung: Bahn 2 wechselt bei
Frame 78 den Grünzustand, die anderen drei nicht.

Konsequenz: **Pro Bahn eine eigene Zustandsmaschine und ein eigener Punktestand.**
Ein gemeinsamer Zustand wäre der schwerwiegendste denkbare Architekturfehler in
diesem Projekt. `tests/unit/test_scoring.py::test_bahnen_sind_unabhaengig`
sichert das ab.

---

## 6. Frame-Sampling ohne Rückwärtsspringen

Nach dem Ereignis werden Frames davor und danach gebraucht. Zurückspringen wäre
bei h264 langsam **und** ungenau — und bei einem Livestream unmöglich.

```
        +-- Ringpuffer der letzten N Frames --+
   ...  | f-4  f-3  f-2  f-1  f_aktuell       |  → bei Trigger sofort da
        +-------------------------------------+
```

`FrameBuffer` hält die Frames vor. Bei 6 MB/Frame ist die Größe ein bewusster
Kompromiss und steht in der Konfiguration.

---

## 7. Nachvollziehbarkeit als Datenstruktur

Jedes `ThrowResult` trägt eine `Evidence`: Frames, Scores, Einzelmessungen,
Plausibilitätsprüfungen, Entscheidungen. `ThrowResult.explain()` erzeugt daraus
die Begründung aus Auftrag §27:

```
Warum wurde Wurf 17 erkannt?
→ GREEN_OFF bei t=184,23 (Score 21,4 unter Schwelle 35, 3 Frames bestätigt)
→ Frames 4580, 4583, 4587, 4594 ausgewertet
→ 5 Lampen aktiv (Kegel 1,3,5,6,8), Confidence 0,96
→ Ziffer 5 in 3 von 4 Frames, Confidence 0,91
→ Wurfnummer 17, vorher 16 → plausibel
→ Summe 42 = 37 + 5 → plausibel
⇒ bestätigt, Gesamt-Confidence 0,94
```

Ein Ergebnis ohne Beweiskette gilt als unvollständig. Das ist Kernanforderung,
kein Debug-Luxus.

---

## 8. Fehler beenden die Analyse nicht

Ein unscharfes Frame, eine flackernde Lampe, ein unlesbares Display — all das ist
Normalbetrieb (§22), kein Ausnahmefall.

- Erwartete Unsicherheit ist ein **Wert** (`confidence`, `status`), keine Exception
- `UNKNOWN` existiert, damit nichts Unklares als „gut" durchgereicht wird
- `except: pass` ist verboten — automatisch geprüft in `test_architecture.py`
- Ein Fehler auf Bahn 2 lässt Bahn 1, 3, 4 unberührt

---

## 9. Vorbereitet, nicht gebaut (Phase 12)

```python
class ResultSink(Protocol):
    def emit(self, throw: ThrowResult) -> None: ...
    def flush(self) -> None: ...
```

`JsonlSink` und `InMemorySink` sind vorgesehen; `ApiSink` und
`LocalDatabaseSink` bewusst **nicht** implementiert. Ebenso `StreamVideoSource`:
Die Abstraktion steht, die Implementierung kommt, wenn die Anforderung real wird.

---

## 10. Was bewusst offen bleibt

Fachliche Unklarheiten werden nicht durch plausible Annahmen ersetzt, sondern in
`OPEN_QUESTIONS.md` dokumentiert und im Code konfigurierbar gehalten — etwa das
Mapping Lampenindex → Kegelnummer (`Roi.pin_number`) oder die Zuordnung
Overlay-Position → reale Bahn (`LaneCalibration.real_lane_number`).

Eine geratene Annahme, die zufällig auf dem Testmaterial funktioniert, ist
schädlicher als eine dokumentierte Lücke.
