---
name: kegel-kalibrierung
description: >
  Kalibrierung und Geometrie in Kegel_CV. Laden bei Arbeit an Eckpunkten,
  Perspektivtransformation, Homographie, warpPerspective, normierten Tafelkoordinaten,
  ROI-Definition und -Verschiebung, Kalibrierungs-Persistenz (JSON), Zuordnung
  Kalibrierung zu Video, oder wenn Koordinaten zwischen Frame und Tafel umgerechnet
  werden.
---

# Kalibrierung & Geometrie

## 1. Warum Kalibrierung zwingend ist

**Gemessen:** Die Overlay-Position unterscheidet sich zwischen Sessions.
2024-09-03: Grünlampen bei x≈538 / 1079 / 1378 — 2026-08-22: x≈572 / 876 / 1105 / 1399.
Eine fest verdrahtete Position wäre für genau ein Video richtig und für alle
anderen falsch. Deshalb: **Kalibrierung pro Session, gespeichert und wiederladbar.**

## 2. Zwei Koordinatensysteme

```
FRAME-KOORDINATEN                    TAFEL-KOORDINATEN (normiert)
(Pixel im Originalvideo)             (0,0) bis (1,1) je Anzeigetafel
1920 x 1080                          auflösungs- und perspektivunabhängig
        |                                     ^
        +------- Homographie H ---------------+
                 H^-1 zurück
```

**Regel:** ROIs werden **ausschließlich in Tafelkoordinaten** gespeichert (0..1).
Nur so bleiben sie gültig, wenn sich Kamera, Zoom oder Auflösung ändern.
Die Umrechnung nach Frame-Pixeln passiert erst zur Laufzeit.

## 3. Die vier Eckpunkte — Reihenfolge ist verbindlich

```
   1 o-----------o 2        1 = oben links
     |           |          2 = oben rechts
     |  TAFEL    |          3 = unten rechts
     |           |          4 = unten links
   4 o-----------o 3        (im Uhrzeigersinn, Start oben links)
```

Diese Reihenfolge stammt aus dem Auftrag (§4) und **muss** eingehalten werden —
`cv2.getPerspectiveTransform` ordnet die Punkte nicht selbst. Vertauschte Punkte
liefern ein gespiegeltes oder verdrehtes Bild, das oft noch plausibel aussieht.

**Schutz:** `Quad.validate()` prüft Konvexität und Umlaufsinn und lehnt
degenerierte Vierecke ab, statt sie stillschweigend zu verarbeiten.

## 4. Homographie

```python
src = np.float32([p1, p2, p3, p4])                    # Frame-Pixel
dst = np.float32([[0,0], [W,0], [W,H], [0,H]])        # normiertes Rechteck
H   = cv2.getPerspectiveTransform(src, dst)
warped = cv2.warpPerspective(frame, H, (W, H))
```

`W` und `H` (Zielauflösung der entzerrten Tafel) kommen aus der Config, nicht aus
dem Code.

### Wann warpen, wann nicht?

| Zweck | Verfahren | Warum |
|---|---|---|
| GUI-Anzeige, ROI-Bearbeitung | `warpPerspective` der ganzen Tafel | Nutzer braucht das entzerrte Bild |
| Analyse im Hot Path | nur ROI-Eckpunkte mit `perspectiveTransform` zurückrechnen | Warpen der ganzen Tafel kostet ~1 ms x 4 Bahnen x 25 fps — unnötig |

Für kleine ROIs (Grünlampe: 6x8 px) ist die Entzerrung ohnehin bedeutungslos.
Dort genügt das achsparallele Bounding-Rechteck der zurücktransformierten Ecken.

## 5. ROI-Typen pro Bahn

| ROI | Anzahl | Zweck |
|---|---|---|
| `green_lamp` | 1 | Zustands-Trigger |
| `pin_lamp_1` bis `pin_lamp_9` | 9 | gefallene Kegel |
| `pin_count` | 1 | Ziffer Kegelanzahl |
| `throw_number` | 1 | Wurfnummer (3-stellig) |
| `total_a` | 1 | Summe A (oben rechts) |
| `total_b` | 1 | Summe B (unten rechts) |

Jede ROI: `name`, `rect` in Tafelkoordinaten, optional `enabled`.
Die 9 Kegellampen tragen zusätzlich `pin_number` — die **Kegelnummer**, nicht
den Lampenindex. Beides fällt nicht zusammen: Der Name zählt die Lampen von
oben nach unten, die Kegelnummer zählt von vorn (Q5, geklärt am 2026-09-01).
Die Zuordnung kommt aus `calibration.pin_number_mapping`; wer eine Lampe von
Hand setzt, bekommt sie automatisch.

## 6. Persistenz

Ablage: `data/calibrations/<name>.json`

```json
{
  "schema_version": 1,
  "name": "session_2026-08-22",
  "created": "2026-08-24T21:30:00",
  "source_hint": {"width": 1920, "height": 1080, "video": "2026-08-22 09-15-50.mp4"},
  "lanes": [
    {"lane_id": 1,
     "quad": [[470,40],[690,42],[688,295],[468,292]],
     "rois": [{"name": "green_lamp", "rect": [0.44, 0.62, 0.06, 0.05]}]}
  ]
}
```

- `schema_version` von Anfang an — spätere Formatänderungen sind sonst nicht migrierbar.
- `source_hint` erlaubt es, beim Laden zu warnen, wenn eine Kalibrierung zu einem
  Video mit anderer Auflösung geladen wird.
- Beim Laden **validieren** (Pydantic), nicht blind vertrauen.

## 7. Typische Fehler

| Fehler | Folge |
|---|---|
| ROI in Pixeln statt normiert speichern | Kalibrierung bricht bei anderer Auflösung |
| Punktreihenfolge nicht prüfen | gespiegelte Tafel, Fehler fällt erst spät auf |
| `warpPerspective` pro Frame und Bahn | Performance-Budget gesprengt |
| Kalibrierung ohne `schema_version` | keine Migration möglich |
| Annehmen, Bahn *n* im Overlay = reale Bahn *n* | offene Frage Q1 — Zuordnung ist konfigurierbar |
