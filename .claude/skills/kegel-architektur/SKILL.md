---
name: kegel-architektur
description: >
  Architektur- und Codekonventionen für Kegel_CV. Laden beim Anlegen neuer Module,
  bei Fragen zu Schichten, Abhängigkeitsrichtung, Interfaces/ABCs, Dependency
  Injection, Konfigurationsparametern, Austauschbarkeit von Detektoren, ResultSink,
  Performance-Budget oder wenn eine Zahl im Code auftauchen soll (Magic Number).
---

# Architektur & Codekonventionen

## 1. Schichten und Abhängigkeitsrichtung

```
        gui/          ← darf alles darunter nutzen
          │
     analysis/        ← orchestriert Detektoren, kennt keine GUI
          │
   detection/  video/  calibration/   ← Fachlogik, kennen nur models/ + config/
          │
      models/  config/  debug/        ← Basis, kennt NICHTS darüber
```

**Harte Regel:** Abhängigkeiten zeigen **immer nach unten**.
`models/` importiert nie aus `detection/`. `detection/` importiert nie aus `gui/`.
Ein `import` gegen die Pfeilrichtung ist ein Architekturbruch, kein Detail.

Prüfbar: `tests/unit/test_architecture.py` verifiziert das automatisch.

## 2. Austauschbarkeit — jeder Detektor hinter einem Protocol

Der Auftrag verlangt, Komponenten später gegen bessere Verfahren tauschen zu können
(klassische CV → Template Matching → OCR → ML). Deshalb:

```python
class GreenLampDetector(Protocol):
    def detect(self, frame: np.ndarray, roi: Roi) -> LampReading: ...
```

Konkrete Implementierungen: `HsvGreenDetector`, später z.B. `MlGreenDetector`.
Die Auswahl erfolgt über **Config + Factory**, nie über `if isinstance(...)`:

```yaml
detection:
  green:
    implementation: "hsv"     # später: "ml"
```

**Nie** eine konkrete Klasse direkt in `analysis/` instanziieren — immer über die
Factory. Sonst ist der Austausch später ein Umbau statt einer Konfigzeile.

## 3. Keine Magic Numbers — niemals

| ❌ | ✅ |
|---|---|
| `if score > 40:` | `if score > cfg.detection.green.on_threshold:` |
| `frame[35:300, 430:1490]` | ROI aus der Kalibrierung |
| `for i in range(15):` | `cfg.scoring.throws_per_cycle` |
| `time.sleep(0.04)` | `1.0 / cfg.video.target_fps` |

Ausnahmen, die keine Magic Numbers sind: mathematische Konstanten (`2` in einer
Mittelwertbildung), Indizes aus der Problemdomäne (`bitmap >> (pin - 1)`),
Array-Dimensionen. Im Zweifel: in die Config.

**Jeder Config-Wert braucht einen Kommentar mit Begründung**, idealerweise mit
gemessenem Beleg:
```yaml
on_threshold: 45.0   # gemessen: AUS 20-24, AN 67-75 -> Mitte mit Reserve
```

## 4. Datenmodelle

- `models/` enthält **nur Daten und reine Funktionen**, keine I/O, kein OpenCV.
- Pydantic für alles, was aus Dateien kommt (Config, Kalibrierung) — Validierung
  beim Laden, nicht beim ersten Zugriff.
- `@dataclass(frozen=True)` für Werte, die im Hot Path erzeugt werden
  (`LampReading`, `FrameRef`) — Pydantic ist dort zu teuer.
- Ergebnisobjekte sind **unveränderlich**. Ein Wurf wird nicht nachträglich mutiert;
  bei Korrektur entsteht ein neues Objekt mit Referenz auf das alte.

## 5. Herkunft mitführen (Prinzip P1)

Jedes Ergebnis muss beantworten können: *„Wie bin ich entstanden?"*

```python
@dataclass(frozen=True)
class ThrowResult:
    ...
    evidence: Evidence        # Frames, Scores, Einzelmessungen, Entscheidungen
```

Ein Ergebnis ohne `evidence` ist unvollständig. Das ist kein Debug-Luxus, sondern
Kernanforderung (Auftrag §27).

## 6. Fehlerbehandlung

```python
# ✅ Fehler bricht die Analyse nicht ab, wird aber sichtbar
try:
    reading = detector.detect(frame, roi)
except DetectionError as e:
    log.warning("Detektion fehlgeschlagen lane=%s roi=%s: %s", lane, roi.name, e)
    reading = LampReading.unknown(reason=str(e))
```

Regeln:
- **Nie** `except: pass`.
- **Nie** einen unklaren Zustand als „gut" durchreichen — dafür gibt es `UNKNOWN`.
- Ein Fehler auf Bahn 2 darf Bahn 1, 3, 4 nicht beeinflussen (P6).
- Exceptions nur für echte Ausnahmen; erwartete Unsicherheit ist ein *Wert*
  (`confidence`, `status`), keine Exception.

## 7. Performance-Budget

Ziel: 25 fps Video in mindestens Echtzeit verarbeiten (≤ 40 ms/Frame gesamt).

Kostenstaffel — teure Schritte nur wenn nötig:
```
JEDER Frame:      Grünlampe prüfen (4 × ~60 px)        ~0.1 ms
NUR bei Event:    Kegellampen (4 × 9 ROIs)             ~1 ms
NUR bei Event:    Ziffern (Segmentierung/Template)     ~5 ms
NIE pro Frame:    ML-Modelle
```

Weitere Regeln:
- Video **sequenziell** lesen. `cap.set(POS_FRAMES, ...)` nur in der GUI-Navigation,
  nie in der Analyse — bei h264 ist Seeking teuer und ungenau.
- ROIs als **Views** (`frame[y0:y1, x0:x1]`), nicht als Kopien.
- Farbraumkonvertierung nur auf dem ROI, nie auf dem ganzen Frame.
- Messen statt vermuten: `PerformanceMonitor` gehört von Anfang an rein.

## 8. Vorbereitung für später (nicht implementieren)

```python
class ResultSink(Protocol):
    def emit(self, throw: ThrowResult) -> None: ...
    def flush(self) -> None: ...
```
Implementiert: `JsonlSink`, `InMemorySink`.
Vorbereitet, aber **nicht** gebaut: `ApiSink`, `LocalDatabaseSink` (Phase 12).

Ebenso `VideoSource` als ABC mit `FileVideoSource` heute und `StreamVideoSource`
später — die Analyse darf nie wissen, woher die Frames kommen.

## 9. Namenskonventionen

| Was | Konvention | Beispiel |
|---|---|---|
| Module | `snake_case`, englisch | `green_detector.py` |
| Klassen | `PascalCase`, englisch | `HsvGreenDetector` |
| Config-Keys | `snake_case`, englisch | `on_threshold` |
| Doku, Kommentare, GUI-Texte, Log-Meldungen | **Deutsch** | `"Wurf erkannt"` |
| Enums | `UPPER_CASE`-Werte | `ThrowStatus.EMPTY` |

Begründung: Code englisch (Werkzeug-Konvention), alles was der Nutzer liest deutsch.
