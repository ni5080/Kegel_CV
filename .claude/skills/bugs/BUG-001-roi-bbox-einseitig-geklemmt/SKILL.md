---
name: bug-001-roi-bbox-einseitig-geklemmt
description: >
  Verhindert CALIB-Bug: Ein auf Bildgrenzen geklemmtes Rechteck wurde nur nach
  unten (max(0, ...)) begrenzt, nicht nach oben, sodass eine ROI ausserhalb des
  Bildes eine Position ausserhalb des Bildes zurueckgab. Laden bei Arbeit an
  ROI-Ausschnitten, Bounding-Boxen, Clipping, Slicing von Frames, Koordinaten-
  begrenzung -- Stichworte: clamp, clip, bbox, norm_rect_to_frame_bbox, ROI-Crop.
---

# BUG-001 — Bounding-Box nur einseitig geklemmt

| | |
|---|---|
| **Kategorie** | `CALIB` |
| **Gefunden** | 2026-08-24, Phase 3 (durch Test, vor dem ersten Einsatz) |
| **Schweregrad** | mittel |
| **Regressionstest** | `tests/unit/test_calibration.py::TestPerspectiveTransform::test_bbox_wird_auf_bildgrenzen_begrenzt` |

## Symptom

`norm_rect_to_frame_bbox()` lieferte für eine ROI, die vollständig **rechts neben**
dem Bild lag, das Ergebnis `x=200, w=0` bei einer Bildbreite von 150.
Die Breite war korrekt 0, aber die **Position lag ausserhalb des Bildes**.

## Ursache

Beim Klemmen wurde je Kante nur die Seite begrenzt, an der ein Überlauf „erwartet"
wurde: der Startpunkt nach unten, der Endpunkt nach oben.

```python
x0, x1 = max(0, x0), min(width, x1)
```

Das ist stillschweigend an die Annahme gekoppelt, dass die ROI das Bild höchstens
*überlappt*. Liegt sie **vollständig** ausserhalb, greift für `x0` keine Schranke
mehr — `max(0, 200)` ist 200, und das bleibt so stehen.

Warum das trügerisch plausibel aussieht: Für alle Überlappungsfälle — also alle,
die man beim Schreiben im Kopf hat — ist die Formel korrekt. Der Fehler tritt nur
im Randfall auf, und das Ergebnis ist kein Absturz: `frame[y:y+0, 200:200]` liefert
ein leeres Array. Der Fehler wäre also erst weit später als „ROI liefert nie Daten"
aufgefallen — an einer ganz anderen Stelle als seiner Ursache.

## Falsch

```python
x0, x1 = max(0, x0), min(width, x1)
y0, y1 = max(0, y0), min(height, y1)
```

## Richtig

```python
# BEIDE Grenzen beidseitig klemmen
x0 = min(max(0, x0), width)
x1 = min(max(0, x1), width)
y0 = min(max(0, y0), height)
y1 = min(max(0, y1), height)
```

## Regel für die Zukunft

> Beim Klemmen auf einen gültigen Bereich wird **jeder** Wert **beidseitig**
> begrenzt — nie nur an der Seite, an der man den Überlauf erwartet.
> `min(max(low, v), high)` statt `max(low, v)` oder `min(v, high)` allein.

Zusatz für dieses Projekt: Ein leeres ROI-Ergebnis darf **nie** als „0 Kegel" oder
„Lampe aus" interpretiert werden. Ein ROI ausserhalb des Bildes ist ein
Kalibrierungsfehler und gehört als `UNKNOWN` protokolliert, nicht als Messwert.

## Wo gilt diese Regel noch?

- [x] `calibration/geometry.py::norm_rect_to_frame_bbox` — gefixt
- [ ] Detektoren, sobald sie ROI-Ausschnitte schneiden (Phase 4–7): vor dem
      Slicing prüfen, ob `w > 0 and h > 0`, sonst `UNKNOWN` statt Messwert
- [ ] GUI `video_view.widget_to_frame` — liefert bewusst `None` ausserhalb
      des Bildes statt geklemmter Koordinaten; das ist die richtige Wahl für
      Mausklicks und darf nicht auf Klemmen umgestellt werden
