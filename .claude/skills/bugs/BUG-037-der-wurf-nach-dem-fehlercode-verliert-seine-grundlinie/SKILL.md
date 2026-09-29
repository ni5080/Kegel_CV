---
name: bug-037-der-wurf-nach-dem-fehlercode-verliert-seine-grundlinie
description: >
  Nach einem Fehlercode wird die Tafel sekundenlang KOMPLETT dunkel -- der
  kleinste Stand seit dem vorigen Wurf ist damit leer, und der naechste Wurf
  wird mit allen neun Kegeln gebucht statt mit einem. Laden bei Arbeit an
  `grundlinie_aus_spur`, an `_anker_vorstand`, an der Grundlinie ueberhaupt.
---

# BUG-037 — Der Wurf nach dem Fehlercode verliert seine Grundlinie

| | |
|---|---|
| **Kategorie** | `ANALYSE` / Grundlinie |
| **Gefunden** | 2026-09-29, aus der Endstandspruefung zweier Bahn-4-Spiele |
| **Schweregrad** | hoch (2 Spiele je +8 Kegel) |
| **Belege** | `debug/streitfaelle/streit_bahn4_f46576-47220.gif` (182 Bilder, Frame fuer Frame), `debug/streitfaelle/uebersicht_bahn4_wurf22_23.png` |
| **Werkzeuge** | `tools/simuliere_vorstand.py`, `tools/simuliere_plateau.py` |
| **Stand** | **behoben** — `sampling.baseline_from_previous_state`, seit dem Vollauf vom 2026-09-29 die Vorgabe |

## Symptom

Nachdem BUG-036 behoben war, blieben zwei Spiele auf Bahn 4 um je **8 Kegel**
zu hoch. Nicht der Fehlercode-Wurf selbst -- der stimmte jetzt --, sondern
**der Wurf danach**:

```
Spiel  4   Wurf 22 = 7 ✓ (Fehlercode)   Wurf 23 gebucht 9, Tafel sagt 1
Spiel 10   Wurf 20 = 7 ✓ (Fehlercode)   Wurf 21 gebucht 9, Tafel sagt 1
```

Zweimal dasselbe Muster, zweimal genau -8.

## Ursache

Zwei Dinge gehen gleichzeitig schief, und nur beide zusammen erklaeren die 9.

**Erstens: die Tafel wird waehrend des Fehlercodes KOMPLETT dunkel.** Gemessen
auf Bahn 4 zwischen Gruen-AUS von Wurf 22 und Gruen-AN von Wurf 23:

```
46850  123456789   alle neun bei 240
46875  .........   alle neun bei 178-198  (Schwelle 215)
46900  .........   alle neun bei 166-187
46925  .....67.9
```

2,5 Sekunden lang schwarz, im zweiten Fall 3,75. Das ist keine Dunkelphase des
Blinkens -- auch die dauerleuchtenden 6, 7, 9 sind aus. Im Bild des GIF ist
die Ziffernanzeige dabei weiter zu lesen (`022 / 7 / 0170`), es ist also
nicht die Bahn verdeckt, sondern die Lampenreihe selbst aus.

`grundlinie_aus_spur` nimmt den **kleinsten Stand ueber eine Blinkperiode seit
dem vorigen Gruen-AUS**. Der kleinste Stand ist damit leer. Im Protokoll:

```
Bahn 4: Grundlinie aus dem Fenster [1..9], aus der laufenden Spur []
        -- es gilt die Spur
```

**Zweitens: der Fehlercode leuchtet in die Gruenphase nach.** Der wahre Stand
-- die sieben Kegel von Wurf 22 -- steht erst ab Frame 47140:

```
47103  Gruen-AN
47105  .....67.9   Fehlercode
47117  123456789   Fehlercode
47130  ...4567.9   Fehlercode, letztes Aufflackern
47140  123..6789   <- der wahre Stand, 23 Sekunden lang unveraendert
47605  1234.6789   Kegel 4 faellt
47674  Gruen-AUS
```

Leere Grundlinie minus einer Ergebnismenge, die den Code mitnimmt: alle neun.

## Die Loesung — vom Nutzer

*„wie waere es mit, die Grundlinie darf nur 0 sein ODER derselbe Wert wie im
Wurf zuvor?"* (2026-09-29)

Kegel stehen nicht wieder auf. Nach einem Wurf liegt genau das, was vorher
lag, plus was dieser Wurf umwarf. Nur wenn die Anlage neu aufstellt -- bei den
**Vollen** nach jedem Wurf, beim **Abraeumen** nach allen neunen -- liegt
nichts. Es gibt also genau zwei erlaubte Grundlinien.

Welche gerade gilt, muss man nicht wissen: Die Tafel zeigt es zu Beginn der
Gruenphase selbst. Und dieser Augenblick ist zugleich der **Beginn des
Wurfes** -- damit wird an EINER Stelle geschnitten, und der Fehlercode kommt
weder in die Grundlinie noch ins Ergebnis. Die Regel erwaehnt ihn nie.

Implementiert als `LaneProcessor._anker_vorstand` hinter
`sampling.baseline_from_previous_state`. Findet sich in der ganzen Gruenphase
keiner der beiden Staende, schweigt die Regel und das bisherige Verfahren
gilt weiter.

## Was vorher gemessen und verworfen wurde

| Idee | Ergebnis |
|---|---|
| Rueckwaertsfenster ab Gruen-AUS | verworfen -- die Grundlinie muss frueh liegen, nicht spaet |
| Zaehlung endet bei Gruen-AUS | verworfen -- 97,8 % auf 94,1 %, der Jubel-Blink braucht die Frames danach |
| Breakpoint = Sprung der Wurfnummer | verworfen -- physikalisch richtig, aber nur 6 Frames Marge; 20 Wuerfe verloren |
| Plateau-Regel (`tools/simuliere_plateau.py`) | knapp -- 1410 auf 1411, und laengere Plateaus rasten nach dem Fall ein (5 s: 77,1 %) |
| Nur die Grundlinie ersetzen, Ergebnisbeginn lassen | **2 Kegel statt 1** -- derselbe Code steht auch im Ergebnis |
| **Grundlinie UND Ergebnisbeginn am Vorstand** | **behalten** |

Die vorletzte Zeile ist der Kern: Eine reparierte Grundlinie allein genuegt
nicht.

## Gegenprobe

Offline ueber den Spieltag (`tools/simuliere_vorstand.py`, 1473 Wuerfe mit
lesbarer Tafelsumme): Anker in 1671 von 1678 Wuerfen gefunden, 1410 auf 1412
richtig.

Im echten Video, zwei gezielte Laeufe ueber alle vier Bahnen:

```
Fall 1  F38500-48600   92 vergleichbare Wuerfe   89 -> 91 richtig
  Bahn 4 Wurf 23  alt 9 -> neu 1   Tafel 1
  Bahn 5 Wurf 25  alt 2 -> neu 1   Tafel 1

Fall 2  F130500-140200  58 vergleichbare Wuerfe  51 -> 57 richtig
  Bahn 4 Wurf 21  alt 9 -> neu 1   Tafel 1
  Bahn 5 Wurf  8  alt 6 -> neu 7   Tafel 7
  Bahn 5 Wurf  9  alt 8 -> neu 9   Tafel 9
  Bahn 5 Wurf 10  alt 7 -> neu 8   Tafel 8
  Bahn 5 Wurf 14  alt 8 -> neu 9   Tafel 9
```

Acht besser, keiner schlechter. **Die Bahn-5-Zeilen gehoeren aber nicht der
Regel**: Diese Laeufe benutzten zugleich die korrigierte Kalibrierung
`2Spieltag_neu.json`, in der Kegel 8 um 2,7 px nach oben gerueckt ist
(p99-Helligkeit 216,8 -> 255,0). Nur Bahn 2, 3 und 4 haben eine unveraenderte
Kalibrierung -- was sich dort aendert, ist ausschliesslich die Regel, und dort
liegen beide Zielwuerfe.

### Der Vollauf ueber den ganzen Spieltag (2026-09-29, 110 min)

```
                                   alt (28.09.)      neu
  Wuerfe                           1678              1679
  gegen die Tafelsumme richtig     1410  95,7 %      1437  97,6 %
  Lampen/Ziffer/Summe einig        1099  65,8 %      1131  67,7 %
  Tafelprobe Wurf fuer Wurf        1474  97,2 %      1477  97,4 %
  Spiele mit falschem Endstand        4 von 60          1 von 60
  Luecken                             2                 1
  nachtraegliche Korrekturen         39                 0
  Gruenzyklen ohne Ergebnis          13                12
  Fehlercode-Meldungen               19                 2
```

**Null Wuerfe schlechter** bei 1678 gepaarten. Nach Ursache getrennt:

```
  Bahn 2    0 Unterschiede
  Bahn 3    0 Unterschiede
  Bahn 4    2 Unterschiede -- beide besser, beide die Zielwuerfe  (Regel)
  Bahn 5   39 Unterschiede -- 25 von der Tafelsumme bestaetigt    (Kalibrierung)
```

Die beiden Bahn-4-Spiele stehen jetzt auf **+0** statt +10 beziehungsweise
+8. Die Regel hat sich am ganzen Spieltag **zweimal** gemeldet:

```
Bahn 4: Grundlinie gemessen [] -- erlaubt ist nur leer oder [1,2,3,6,7,8,9],
        es gilt [1,2,3,6,7,8,9] ab Frame  47140
Bahn 4: Grundlinie gemessen [] -- erlaubt ist nur leer oder [1,2,3,6,7,8,9],
        es gilt [1,2,3,6,7,8,9] ab Frame 138770
```

Nebenbefund: **Die nachtraegliche Korrektur der Tabelle findet nichts mehr zu
korrigieren** -- vorher waren es 39 Wuerfe.

## Lehre

**Eine Groesse, die nur ZWEI Werte annehmen kann, sollte man nicht messen.**
Die Grundlinie wurde seit jeher aus den Lampen geschaetzt -- mit Fenster, mit
Spur, mit kleinstem Stand -- obwohl die Physik sie auf zwei Moeglichkeiten
festnagelt. Jede dieser Schaetzungen konnte an einer dunklen Tafel scheitern;
die Auswahl aus zwei erlaubten Werten kann es nicht.

**Wer nur die Grundlinie repariert, repariert die Haelfte.** Dieselbe Stoerung
sitzt im Ergebnis. Der Schnitt muss an EINER Stelle liegen.

**Zwei Aenderungen in einem Lauf trennen sich nur noch nach Bahnen.** Der
Vollauf vom 2026-09-29 enthaelt Regel UND Kalibrierung; ohne die Beobachtung,
dass Bahn 2-4 unveraendert kalibriert sind, waere das Ergebnis nicht mehr
zuzuordnen gewesen.
