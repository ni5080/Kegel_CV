---
name: bug-024-roi-aenderung-erreicht-die-analyse-nie
description: >
  Verhindert GUI/Analyse-Bug: Eine im laufenden Betrieb verschobene ROI wirkte
  nicht, weil die Analyse nur die beim Start vorberechneten Pixelrechtecke
  liest -- und nichts sagte es. Laden bei Arbeit an `LaneProcessor.prepare`,
  an vorberechneten Ableitungen aus der Kalibrierung, oder wenn eine Bedienung
  waehrend eines laufenden Vorgangs Wirkung haben soll.
---

# BUG-024 — Die Kalibrierung ändern, ohne etwas zu ändern

| | |
|---|---|
| **Kategorie** | `GUI` |
| **Gefunden** | 2026-09-11, durch die Nutzeraussage *„ich habe Rahmen von Grün weggezogen und von der Pin_Count und es lief einfach weiter, als hätte ich nichts geändert"* |
| **Schweregrad** | **hoch** (an einem Spieltag nicht korrigierbar, und der Versuch sah aus, als hätte er gewirkt) |
| **Regressionstest** | `test_kalibrierung_im_lauf.py` |

## Symptom

Während einer laufenden Live-Analyse zog der Nutzer die Rahmen der Grünlampe
und des `pin_count`-Feldes an eine andere Stelle. Im Bild sprangen die Rahmen
mit. Die Analyse lieferte unverändert dieselben Messwerte.

Es gab **keine Meldung**. Nichts im Protokoll, nichts in der Statuszeile.

## Ursache

`LaneProcessor.prepare(frame_shape)` rechnet die normierten Bereiche **einmal**
in Pixelrechtecke um:

```python
self._green_box = norm_rect_to_frame_bbox(self._transform, green_roi.rect, ...)
self._lamp_boxes = [...]
```

Ab da liest die Analyse nur noch `self._green_box`. Wer die normierten
Koordinaten in der Sitzung verschiebt, verschiebt etwas, das niemand mehr
ansieht. Die beiden Darstellungen — normierte ROI und Pixelrechteck — waren
nach dem Start dauerhaft entkoppelt.

Verschärfend: Oberfläche und Analyse teilen sich dasselbe `Calibration`-Objekt.
Die Änderung *kam also an*, sie wurde nur nirgends mehr ausgewertet. Ein
Blick in die Daten hätte "stimmt doch" gesagt.

## Die Lehre

**Eine vorberechnete Ableitung braucht einen Weg, ungültig zu werden.** Sonst
ist der Zustand der Anwendung in zwei Wahrheiten gespalten: die, die der Nutzer
sieht und ändert, und die, nach der gerechnet wird.

Die zweite Hälfte des Fehlers ist die Stille. Eine Bedienung, die nichts
bewirkt, muss das sagen — sonst zieht der Nutzer weiter an Rahmen und sucht den
Fehler an einer Stelle, an der keiner ist. Genau das geschah, während auf zwei
Bahnen Würfe verloren gingen (siehe die Grünlampen-Messung vom selben Tag).

## Behebung

```
LaneProcessor.uebernimm_kalibrierung(neue_bahn, frame_shape)
AnalysisPipeline.uebernimm_kalibrierung(neue_kalibrierung, frame_shape)
AnalysisWorker.uebernimm_kalibrierung(kalibrierung)   -- als KOPIE, unter Mutex
MainWindow._reiche_kalibrierung_weiter()              -- plus Meldung
```

Drei Entscheidungen, die dazugehören:

1. **Übernommen wird beim nächsten Frame, nicht sofort.** Mitten in der
   Auswertung eines Frames die Messstellen zu tauschen hieße, zwei
   Kalibrierungen in einem Ergebnis zu mischen.
2. **Das Gedächtnis der betroffenen Detektoren wird geleert.** Die
   mitlaufenden Schwellen sind an die Messstelle gebunden; wandert sie,
   beschreiben die gesammelten Werte eine Lage, die es nicht mehr gibt. Eine
   Minute mit den festen Schwellen ist besser als eine Schwelle aus zwei
   verschiedenen Messstellen. Nur geleert wird, was sich wirklich geändert hat.
3. **Der Zustand der Bahn bleibt.** Wurfzähler, Zustandsmaschine und Summen
   hängen nicht an der ROI-Lage. Sie zurückzusetzen hieße, Würfe doppelt oder
   gar nicht zu buchen.

## Warum die Tests das nicht fanden

Es gab Tests für `prepare()` und Tests für das Ziehen in der Oberfläche —
beide grün. Geprüft wurde nie die **Verbindung** zwischen beiden, weil sie nur
im laufenden Betrieb existiert. Der Regressionstest prüft deshalb genau die
Naht: ROI verschieben → `_green_box` muss sich ändern.

## Wonach in Zukunft zu suchen ist

- `prepare`, `_build`, `_cache`, `precompute`: Wird das Ergebnis je erneuert?
- Ein `set_...` in der Oberfläche, dessen Wirkung von einem laufenden Thread
  abhängt.
- Bedienelemente, die während eines langen Vorgangs bedienbar bleiben. Entweder
  sie wirken — oder sie sagen, dass sie es nicht tun.
