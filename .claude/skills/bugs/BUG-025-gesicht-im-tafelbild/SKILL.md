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

## Behebung -- in zwei Anlaeufen, und der erste war falsch

**Erster Anlauf (verworfen):** menschgrosse BEWEGTE Flecken auch auf der Tafel
schwaerzen. Er ging an genau dem Fall vorbei, der den Befund ausgeloest hat.

GEMESSEN am Mitschnitt vom 2026-09-08, Bahn 2, Frame 13489 -- ein Mensch beugt
sich ueber die Tafel und ist im Bild voll zu sehen:

```
Verdeckung (Bewegung)                    0,081   Schwelle 0,14
groesster bewegter Fleck auf der Tafel   0,09 Tafelflaechen
```

**Er steht still.** Das Hintergrundmodell hat ihn aufgenommen; als Vordergrund
bleiben nur seine bewegten Raender. Das ist kein Fehler im Verfahren, sondern
das Verfahren -- die Grenze steht seit jeher in `person_maske.py`, hier zum
ersten Mal mit Folgen.

**Zweiter Anlauf: `analysis/tafel_wache.py`.** Eine Referenz der eigenen Tafel,
die NUR nachlernt, wenn die Tafel normal aussieht. Damit kann niemand
hineinwandern, egal wie lange er steht. Verglichen wird auf den stabilen Pixeln
(Gehaeuse, Fensterrahmen) -- dieselbe Maske, mit der die Tafel gefunden wird.

GEMESSEN ueber 2705 Messungen aus 15 Minuten:

```
Normalbetrieb    Median 1,41 %   95. Perzentil 2,55 %
Mensch davor     11,9 bis 14,1 %   (zugleich das Maximum des Laufs)
```

Die Schwelle liegt bei 5 % in der Luecke. Die Fremdmaske wird geschlossen und
im Verhaeltnis zur Tafelkante verbreitert -- ein halb geschwaerztes Gesicht ist
kein geschwaerztes Gesicht.

## Die dritte Lehre

**Eine Messung an bewegten Menschen beweist nichts ueber stillstehende.** Der
erste Anlauf war gemessen (27,9 % geschwaerzt bei Verdeckung, 0,09 % im
Normalbetrieb) -- die Messung war richtig und die Antwort trotzdem falsch,
weil die Stichprobe den Fall nicht enthielt, um den es ging. Wer eine
Schutzmassnahme misst, muss sie an dem Fall messen, der sie ausgeloest hat.
