---
name: kegel-debug-logging
description: >
  Debug-Infrastruktur und Logging in Kegel_CV. Laden bei Arbeit an Debug-Frames,
  Frame-Speicherung, Event-Logs, Nachvollziehbarkeit von Ergebnissen, Evidence,
  Log-Levels, Log-Formaten oder wenn die Frage beantwortet werden muss, warum ein
  bestimmter Wurf so erkannt wurde.
---

# Debug & Logging

## 1. Der Anspruch

Diese Frage muss jederzeit beantwortbar sein — **ohne das Video erneut zu laden**:

> Welche Frames wurden für Bahn 2 bei Wurf 17 verwendet, und warum kam dieses
> Ergebnis zustande?

Debug ist in diesem Projekt kein Hilfsmittel, sondern eine Kernanforderung
(Auftrag §14, §27). Ein Ergebnis ohne nachvollziehbare Herkunft gilt als unfertig.

## 2. Debug-Frames

```
debug/
  <video_id>/
    lane_1/
      throw_017/
        t_00184.230_frame_04580_GREEN_OFF.png
        t_00184.350_frame_04583_SAMPLE.png
        t_00184.510_frame_04587_SAMPLE.png
        t_00184.790_frame_04594_GREEN_ON.png
        result.json
```

Der Dateiname trägt alles Wesentliche: Zeit, Frame-Nummer, Rolle im Event.
Sortierung ist dadurch automatisch chronologisch.

`result.json` enthält den `ThrowResult` inklusive `evidence` — Bilder und Ergebnis
liegen zusammen, nicht in getrennten Verzeichnisbäumen.

### Speicherbedarf im Blick behalten

Ein Wurf ≈ 4 PNG. Ein langes Video mit 4 Bahnen à 120 Würfen ⇒ ~2000 Bilder.
Deshalb konfigurierbar:

```yaml
debug:
  save_frames: true
  save_failed_frames: true    # Fehlerfälle IMMER speichern -- die sind wertvoll
  save_roi_crops: true        # kleine Ausschnitte statt Vollframes
  max_events_per_lane: 200
  jpeg_quality: 92            # PNG nur für Fehlerfälle
```

`save_failed_frames` ist bewusst getrennt: Auch wenn das normale Speichern
abgeschaltet ist, sollen Fehlerfälle erhalten bleiben.

## 3. Event-Log — maschinenlesbar

Zusätzlich zum Menschen-Log ein strukturiertes Log (JSONL) pro Lauf:

```
timestamp=184.230 lane=2 frame=4580 event=GREEN_OFF green_state=OFF green_score=21.4
timestamp=184.790 lane=2 frame=4594 event=THROW_CONFIRMED pin_lamps=[1,3,5,6,8]
    pin_count=5 ocr_pin_count=5 throw_number=17 running_total=42 confidence=0.94
```

JSONL, weil es zeilenweise wächst, bei Absturz nicht kaputtgeht und sich mit
Standardwerkzeugen auswerten lässt. `tools/replay_events.py` liest es zurück, um
Läufe zu vergleichen — so wird sichtbar, ob eine Änderung die Erkennung verbessert
oder verschlechtert hat.

## 4. Log-Level — klare Zuordnung

| Level | Wofür | Beispiel |
|---|---|---|
| `DEBUG` | Frame-Ebene, Scores, Zwischenschritte | `green_score=21.4 state=READY` |
| `INFO` | Fachliche Ereignisse | `Wurf erkannt: Bahn 2, Nr 17, 5 Kegel` |
| `WARNING` | Unstimmigkeit, Betrieb läuft weiter | `Lampen=5 aber Ziffer=4` |
| `ERROR` | Auswertung fehlgeschlagen | `Kalibrierung nicht ladbar` |

Faustregel: `INFO` muss ohne Fachkenntnis der Implementierung verständlich sein.
`DEBUG` darf technisch sein. **Deutschsprachige Meldungen** — der Nutzer liest sie.

Pflicht-Events (Auftrag §16): Video gestartet/gestoppt, Bahn kalibriert, ROI geändert,
Green OFF/ON, Wurf erkannt/bestätigt/verworfen, OCR unsicher, Lampen-OCR-Widerspruch,
Summen-Widerspruch, Frame gespeichert, Videofehler.

## 5. Evidence — die Beweiskette am Objekt

```python
@dataclass(frozen=True)
class Evidence:
    frames: list[FrameRef]                  # Nummer, Zeit, Rolle
    green_scores: list[float]
    lamp_readings: list[list[LampReading]]  # je Frame, je Lampe
    digit_readings: dict[str, list[DigitReading]]
    checks: list[PlausibilityCheck]         # Name, erwartet, erhalten, bestanden
    decisions: list[str]                    # menschenlesbare Begründungen
```

Damit lässt sich ein Ergebnis vollständig rekonstruieren:

```
Warum Wurf 17?
  -> GREEN_OFF bei t=184.23 (Score 21.4 unter Schwelle 35, 3 Frames bestätigt)
  -> Frames 4580, 4583, 4587, 4594 ausgewertet
  -> 5 Lampen aktiv (Kegel 1,3,5,6,8), Confidence 0.96
  -> Ziffer = 5 in 3 von 4 Frames, Confidence 0.91
  -> Wurfnummer 17, vorher 16 -> plausibel
  -> Summe 42 = 37 + 5 -> plausibel
  => bestätigt, Gesamt-Confidence 0.94
```

## 6. Isolierte Nachanalyse

Auftrag §23: Gespeicherte Debug-Events müssen einzeln erneut analysierbar sein —
ohne Video, ohne GUI.

```bash
python -m kegel_cv.tools.reanalyze debug/<video>/lane_2/throw_017/
```

Das macht die Entwicklung der Erkennungslogik schnell: Ein Fehlerfall wird zum
Testfall, statt jedes Mal minutenlang durch das Video zu suchen. Jeder gespeicherte
Fehlerfall ist ein potenzielles Test-Fixture.

## 7. Was nicht ins Log gehört

- Vollständige Frames als Base64 — dafür gibt es Dateien.
- Log-Ausgabe in Schleifen ohne Level-Prüfung — bei 25 fps × 4 Bahnen entstehen
  sonst schnell Millionen Zeilen.
- Stille Fehler: `except: pass` ist immer falsch (siehe `kegel-architektur`).
