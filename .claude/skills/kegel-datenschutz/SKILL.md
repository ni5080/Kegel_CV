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
| `board_jpeg` in der Datenbank / Liveticker | Tafelausschnitt | `TafelWache` **und** `PersonenModell`, vereinigt in `LaneProcessor.fremdmaske`, ueber `board_image.schwaerze_fremdes` |
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

## Die Loesung: zwei Verfahren fuer zwei verschiedene Faelle

* **Analysebild** -- Tafelbereiche ausgenommen, wie bisher. Was gemessen wird,
  bleibt roh.
* **Veroeffentlichtes Bild** -- der Tafelausschnitt wird ein zweites Mal
  geschwaerzt, und zwar von der `TafelWache` (`analysis/tafel_wache.py`).

WARUM NICHT DIESELBE BEWEGUNGSMASKE: Sie sieht nur, was sich bewegt. Wer
stillsteht, wandert ins Hintergrundmodell. GEMESSEN am Mitschnitt vom
2026-09-08, Frame 13489 -- ein Mensch beugt sich ueber die Tafel und ist im
Bild voll zu sehen:

```
Verdeckung (Bewegung)                    0,081   Schwelle 0,14
groesster bewegter Fleck auf der Tafel   0,09 Tafelflaechen
```

Die Wache haelt stattdessen eine Referenz der eigenen Tafel und **lernt nur
nach, wenn diese normal aussieht**. Damit kann niemand hineinwandern, egal wie
lange er steht. Verglichen wird auf den stabilen Pixeln.

```
Normalbetrieb    Median 1,41 %   95. Perzentil 2,55 %
Mensch davor     11,9 bis 14,1 %
```

## Was das Verfahren nicht kann

* **Wer minutenlang stillsteht**, wandert im uebrigen Bild ins
  Hintergrundmodell und wird dort nicht mehr geschwaerzt (`history`, Vorgabe
  500 Frames). AUF DER TAFEL faengt die Wache ihn -- ausserhalb nicht.
* **Eine langsame Veraenderung** lernt die Wache mit. Wer sich Zentimeter fuer
  Zentimeter vor die Tafel schiebt, kann unter der Nachlernschwelle bleiben.
  Gemessen ist das nicht; es gehoert nachgesehen, wenn Material dazu auftaucht.
* **Die Wache braucht eine Einlernzeit.** Vor der ersten sauberen Referenz
  meldet sie nichts.
* **Namen auf der Tafel.** Die Anlage zeigt in der oberen Leiste den
  Spielernamen. Der steht im Tafelbild und wird nicht geschwaerzt -- er gehoert
  zur Anzeige, nicht zum Hintergrund. Ob das gewollt ist, ist eine
  Entscheidung des Nutzers, keine technische.

## Wonach zu suchen ist, bevor ein neuer Ausgang entsteht

1. Schneidet der neue Weg aus dem **maskierten** Frame? (`pipeline.process`
   ersetzt `frame.image` -- alles danach sieht das geschwaerzte Bild.)
2. Schneidet er aus einem **Tafelbereich**? Dann braucht er zusaetzlich
   `LaneProcessor.fremdmaske(bild)` und `schwaerze_fremdes`.
3. Stammt sein Frame aus dem **Ringpuffer**? Kein Problem: Die Wache vergleicht
   gegen ihre Referenz, nicht gegen den Nachbarframe.


## Das Personenmodell (seit 2026-09-13)

Die Wache erkennt einen Menschen nur daran, dass die Tafel nicht mehr wie sie
selbst aussieht. Das Modell erkennt ihn als Menschen -- und schwaerzt ihn
deshalb auch dann, wenn er so still steht, dass die Referenz ihn fast schon
kennt.

**Was beim Arbeiten daran zu beachten ist:**

1. **Das Modell braucht das UNGESCHWAERZTE Bild.** Die Bewegungsmaske schwaerzt
   alles ausserhalb der Tafeln -- also genau den Rumpf, an dem das Netz einen
   Menschen erkennt. `pipeline.process` haelt `roh` fest, BEVOR maskiert wird,
   und reicht es ueber `setze_rohbild` weiter. Wer das umdreht, macht das
   Modell blind, ohne dass ein Test rot wird.
2. **Der Tafelausschnitt allein genuegt nicht.** GEMESSEN: auf dem blanken
   136x136-Ausschnitt findet das Netz 0 von 2 bekannten Gesichtern. Gesucht
   wird im Band ueber alle vier Tafeln, nach unten verlaengert.
3. **Fehlt die Modelldatei, wird still weniger geschwaerzt.** Sie liegt nicht
   im Repo (20 MB, holt `tools/hole_personenmodell.py`). Beim Start steht eine
   Warnung im Log -- wer Datenschutz prueft, muss ZUERST nachsehen, ob das
   Modell ueberhaupt geladen wurde (`Personenmodell geladen: ...`). Ein Lauf
   ohne Modell sieht sonst genauso aus wie einer mit.
5. **Rohe Bildpunkte von Menschen liegen an genau EINER Stelle im Speicher:**
   im Gedaechtnis von `PersonenModell` (Bandausschnitt der letzten 50 Frames,
   vorskaliert). Sie werden nie geschrieben und nie versendet. Wer dort etwas
   aendert, aendert eine Datenschutzeigenschaft.
4. **Die Streife ist Teil des Schutzes, nicht nur der Bremse.** Ohne sie liefe
   das Modell nur, wenn ein billiger Zeuge ohnehin schon anschlaegt -- und
   damit gerade nicht bei dem Menschen, der auf der Tafel steht, ohne die
   gruene Lampe zu beruehren.
