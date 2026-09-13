---
name: bug-025-gesicht-im-tafelbild
description: >
  Verhindert Datenschutz-Bug: Die Personenmaske nahm die Tafelbereiche vom
  Schwaerzen aus -- und genau dieses Rechteck ging als Bild an die Datenbank.
  Laden bei Arbeit an der Personenmaske, an Tafelbildern, oder wenn irgendwo
  geprueft wird, dass etwas NICHT geschwaerzt wird.
---

# BUG-025 — Ueberall geschwaerzt, nur nicht im veroeffentlichten Bild

| | |
|---|---|
| **Kategorie** | `DETECT` / Datenschutz |
| **Gefunden** | 2026-09-13, durch den Nutzer im Liveticker |
| **Schweregrad** | **hoch** (Gesichter in einer Datenbank, die im Netz gelesen wird) |
| **Regressionstest** | `test_menschen_im_tafelbild.py` |

## Symptom

*"im Liveticker, wo ja mittlerweile Bilder angezeigt werden, sieht man sehr
haeufig noch Gesichter -> Immer dann, wenn sie Phantomwuerfe erzeugen."*

## Ursache

`PersonMaske._schuetze_tafeln` setzt die Maske in den Tafelrechtecken auf null
-- richtig, denn Ziffern und Lampen sind selbst bewegter Vordergrund. Aber
`_tafelbild` schneidet genau dieses Rechteck aus und schickt es als
`board_jpeg` an die Datenbank.

Wer vor der Tafel stand, war im ganzen Bild geschwaerzt, nur nicht dort, wo
alle hinsehen. Und weil dieselbe Person den Phantomwurf ausloest, tragen genau
diese Wuerfe ein Gesicht.

BELEGT an der Produktivdatenbank, 1000 Bilder: 21 % der Wuerfe mit "0 Kegel"
zeigen eine verdeckte Tafel, gegen 0,8 % der uebrigen. Ein Bild (id 5312,
Bahn 2, 0 Kegel) zeigt ein Gesicht formatfuellend.

## Die Lehre

**Meine eigene Pruefung hatte den Befund vor Augen und hat ihn gelobt.** Sie
meldete:

```
Bilder mit Schwaerzung IN einem Tafelbereich: 0  (muss 0 sein)
```

Das war als Erfolgskriterium formuliert -- und war die Ursache. Ein Test, der
prueft, dass irgendwo NICHT geschwaerzt wird, gehoert immer mit der Frage
verbunden, **ob aus genau dieser Stelle etwas hinausgeht**.

Die zweite Lehre: Der Nutzer hat es an der ANWENDUNG gesehen, nicht am Code.
Ein Datenschutzversprechen gehoert dort geprueft, wo die Bilder ankommen.

## Behebung

Zweimal schwaerzen, mit verschiedenen Schranken:

* Analysebild -- Tafelbereiche ausgenommen, unveraendert.
* Veroeffentlichtes Bild -- `board_image.schwaerze_menschen`, mit einer
  Schranke in TAFELFLAECHEN (`person_min_blob_boards`, Vorgabe 0,5).

Gemessen: Mensch 2,86 Tafelflaechen, groesster Nicht-Mensch 0,18. Wirkung an
6000 Ausschnitten: 27,9 % geschwaerzt bei Verdeckung, 0,09 % im Normalbetrieb.

Die Maske eines vergangenen Frames haelt die Pipeline vor
(`menschen_von(frame_index)`) -- ein Tafelbild stammt aus einem gesampelten
Frame, nicht aus dem aktuellen.
