---
name: kegel-datenschutz
description: >
  Datenschutz in Kegel_CV -- wohin Bilder von Menschen gelangen und was sie
  aufhaelt. Laden bei Arbeit an der Personenmaske, an Tafelbildern
  (`board_jpeg`), an Debugbildern, Wurfblaettern, am Liveticker, am Versand an
  die Datenbank, oder immer wenn ein neuer Weg entsteht, auf dem ein Bild das
  Haus verlaesst.
---

# Datenschutz: wohin Bilder gelangen

Die Aufnahmen zeigen eine Halle mit Menschen. Der Nutzer hat das am 2026-09-09
zur ersten Prioritaet erklaert. Diese Datei sammelt, was daraus folgt -- und
den Fehler, der dabei zweimal fast unbemerkt geblieben waere.

## Die eine Regel

**Jeder Weg, auf dem ein Bild das Haus verlaesst, braucht seine eigene
Pruefung.** Es genuegt nicht, an einer Stelle zu schwaerzen und anzunehmen,
dass alle Ausgaenge davon profitieren. Genau diese Annahme ist am 2026-09-13
gebrochen.

## Die Wege, auf denen ein Bild hinausgeht

| Weg | Was drauf ist | Wo geschwaerzt wird |
|---|---|---|
| `board_jpeg` in der Datenbank / Liveticker | Tafelausschnitt | `board_image.schwaerze_menschen` |
| `board_before_jpeg` | Tafelausschnitt vor dem Wurf | dieselbe Stelle |
| Debugbilder je Ereignis (`FrameLogger`) | ganze Frames | `PersonMaske` (Frame ist schon maskiert) |
| Wurfblaetter (`ThrowSheet`) | Ausschnitte | ueber die maskierten Frames |
| Grün-/Lampenspur, `wuerfe.csv` | nur Zahlen | nichts noetig |

## Der Fehler vom 2026-09-13 -- und warum er so schwer zu sehen war

Die Personenmaske schwaerzt bewegten Vordergrund, **nimmt die Tafelbereiche
aber aus**. Das ist richtig und darf nicht geaendert werden: Ziffern und Lampen
sind selbst bewegter Vordergrund; wer sie schwaerzt, loescht die Messung.

Genau dieses ausgenommene Rechteck ist aber das, was als `board_jpeg`
verschickt wird. Wer vor der Tafel stand, war im ganzen Bild geschwaerzt --
nur nicht dort, wo alle hinsehen.

Der Nutzer hat es im Liveticker gesehen: *"sieht man sehr haeufig noch
Gesichter -> immer dann, wenn sie Phantomwuerfe erzeugen."* Die Haeufung hat
denselben Grund wie das Bild: Dieselbe Person, die die Tafel verdeckt, erzeugt
den Phantomwurf.

BELEGT an der Produktivdatenbank, 1000 Bilder: **21 % der Wuerfe mit "0 Kegel"
zeigen eine verdeckte Tafel, gegen 0,8 % der uebrigen.**

Und meine eigene Pruefung hatte den Befund schon vor Augen, ohne ihn zu
erkennen -- sie meldete zufrieden:

```
Bilder mit Schwaerzung IN einem Tafelbereich: 0  (muss 0 sein)
```

Das war als Erfolgskriterium gedacht und war die Ursache. **Ein Test, der
prueft, dass irgendwo NICHT geschwaerzt wird, gehoert immer mit der Frage
verbunden, ob aus genau dieser Stelle etwas hinausgeht.**

## Die Loesung: zweimal schwaerzen, mit verschiedenen Schranken

* **Analysebild** -- Tafelbereiche ausgenommen, wie bisher. Was gemessen wird,
  bleibt roh.
* **Veroeffentlichtes Bild** -- der Tafelausschnitt wird ein zweites Mal
  geschwaerzt, mit einer viel hoeheren Fleckenschranke
  (`person_min_blob_boards`, in TAFELFLAECHEN).

Warum eine zweite, hoehere Schranke: Auf der Tafel ist alles bewegter
Vordergrund, was leuchtet. GEMESSEN 2026-09-13, Flecken, die einen
Tafelbereich beruehren:

```
Mensch                    2,86 Tafelflaechen
groesster Nicht-Mensch    0,18 Tafelflaechen   (wechselnde Ziffernzeile)
```

Warum RELATIV zur Tafel und nicht in Pixeln: Wie viele Pixel ein Mensch
bedeckt, haengt an Kamera, Abstand und Aufloesung -- sein Verhaeltnis zur Tafel
nicht.

Wirkung, gemessen an 6000 Tafelausschnitten:

```
bei gemeldeter Verdeckung   27,9 % der Flaeche geschwaerzt
im Normalbetrieb             0,09 %
```

## Was das Verfahren nicht kann

* **Wer minutenlang stillsteht**, wandert ins Hintergrundmodell und wird nicht
  mehr geschwaerzt (`history`, Vorgabe 500 Frames). Fuer die Verdeckungsbremse
  unerheblich, fuer den Datenschutz eine echte Luecke.
* **Ein Gesicht am Rand der Tafel**, kleiner als eine halbe Tafelflaeche,
  bleibt stehen. Die Schranke trennt Mensch von Ziffernzeile, nicht Mensch von
  Kleinigkeit.
* **Namen auf der Tafel.** Die Anlage zeigt in der oberen Leiste den
  Spielernamen. Der steht im Tafelbild und wird nicht geschwaerzt -- er gehoert
  zur Anzeige, nicht zum Hintergrund. Ob das gewollt ist, ist eine
  Entscheidung des Nutzers, keine technische.

## Wonach zu suchen ist, bevor ein neuer Ausgang entsteht

1. Schneidet der neue Weg aus dem **maskierten** Frame? (`pipeline.process`
   ersetzt `frame.image` -- alles danach sieht das geschwaerzte Bild.)
2. Schneidet er aus einem **Tafelbereich**? Dann braucht er zusaetzlich
   `schwaerze_menschen`.
3. Stammt sein Frame aus dem **Ringpuffer**? Dann braucht er die Maske dieses
   Frames -- `AnalysisPipeline.menschen_von(frame_index)`.
