---
name: bug-009-alternative-ziffernform
description: >
  Verhindert DETECT-Bug: Die FUNK-Anzeige zeichnet die 9 OHNE unteren Querbalken
  ("abcfg"). Fehlt die Variante in der Mustertabelle, liefert die Notfallsuche
  das naechstliegende Muster -- aus jeder 9 wurde eine 4. Laden bei Arbeit an
  7-Segment-Erkennung, Mustertabellen oder wenn eine bestimmte Ziffer
  systematisch als eine andere gelesen wird.
---

# BUG-009 — Die Anlage schreibt die 9 anders als das Lehrbuch

| | |
|---|---|
| **Kategorie** | `DETECT` |
| **Gefunden** | 2026-08-25, beim Nachpruefen dreier Widersprueche auf Bahn 5 |
| **Schweregrad** | mittel — die Gegenprobe wurde unbrauchbar |
| **Regressionstest** | `tests/unit/test_digit_reader.py` |

## Symptom

Auf Bahn 5 las die Kegelzahl dreimal "4", waehrend die Tafel klar `9` zeigte
(Frames 4526, 4990, 9352 — im Standbild eindeutig lesbar). Die Summenanzeige
bestaetigte die Lampen: 0034 -> 0043 ist genau +9.

## Ursache

Die Segmentmessung war korrekt. Sie ergab:

```
a=0.24  b=0.61  c=0.51  d=0.00  e=0.00  f=0.30  g=0.70
                        ^^^^^^ Segment d misst exakt null
```

Naheliegende Deutung, und sie war falsch: Der Ziffernrahmen sitze zu tief, das
untere Segment liege ausserhalb. Ein vertikaler Zuschnitt auf den Ziffernumriss
aenderte jedoch nichts.

**Der Blick auf das Bild loeste es:** Die FUNK-Anzeige zeichnet die 9 ohne den
unteren Querbalken — Muster `abcfg` statt `abcdfg`. Segment d leuchtet nie.
Beide Schreibweisen der 9 sind auf 7-Segment-Anzeigen ueblich; in der
Mustertabelle stand nur eine.

Was dann geschah: `abcfg` fand keine Entsprechung, also suchte die Notfallsuche
das naechstliegende bekannte Muster. Das ist `bcfg` = **4**, genau ein Segment
entfernt. Aus jeder 9 wurde eine 4 — mit Confidence 0,35, also korrekt als
unsicher ausgewiesen, aber eben doch als Zahl geliefert.

## Richtig

```python
(True, True, True, False, False, True, True): 9,   # 9 ohne unteren Balken
(False, False, True, True, True, True, True): 6,   # 6 ohne oberen Balken
```

Beide Muster kollidieren mit keinem anderen. Wirkung: lesbare Ziffern von 36 auf
59 von 70 Wuerfen, Confidence in den drei Faellen von 0,35 auf 0,59-0,73.

## Die Regel

> **Ein Segment, das konstant null misst, ist eher nicht vorhanden als falsch
> gemessen.** Eine schlechte Messung rauscht; sie liefert nicht exakt null.

Und allgemeiner: Eine Notfallsuche nach dem "naechstliegenden Muster" verwandelt
eine unbekannte Form stillschweigend in eine falsche Zahl. Sie ist nur so gut wie
die Vollstaendigkeit der Tabelle. Die niedrige Confidence war der einzige
Hinweis -- ihn zu ignorieren waere teuer gewesen.

Zum Vorgehen: Drei Messreihen und ein Umbau (vertikaler Zuschnitt) fuehrten
nicht weiter. Der vergroesserte Blick auf den Ausschnitt loeste es in Sekunden.
**Bei Zweifeln ueber das Material: hinsehen, nicht weiter rechnen** (P1).

## Nachtrag: der Preis dieses Fixes

Mit `abcfg` -> 9 in der Tabelle unterscheiden sich **4 (`bcfg`) und 9 (`abcfg`)
in genau einem Segment**. Damit entscheidet ein einziger Messwert zwischen zwei
Ziffern -- und auf einer Bahn lag genau dieser Wert auf der Schwelle:

```
Bahn 5, Frames 22240-22312 (zehn aufeinanderfolgende Messungen):
    a = 0,333 konstant | Schwelle 0,288-0,326 | gelesen '9'
Die Tafel zeigte im selben Frame:  005 4 0029   -- also eine 4.
```

Vermutliche Ursache des Teilausschlags: Die Ziffern stehen leicht schraeg (vom
Nutzer frueh bemerkt), wodurch die oberen Enden der senkrechten Segmente in die
Messflaeche von `a` ragen. Der Winkel ist je Bahn verschieden -- deshalb trat es
nur auf einer Bahn auf.

**Die Abhilfe war nicht, das Segment besser zu treffen, sondern bei einer
Entscheidung auf Messerschneide nichts zu behaupten** (`segment_ambiguous_band`,
siehe `digit_reader.is_ambiguous`). Wuerde ein knapp gemessenes Segment
umgekippt eine ANDERE gueltige Ziffer ergeben, liefert der Leser `?`.

Die Abwaegung dahinter: Die Ziffer ist Gegenprobe zu den Lampen. Eine **falsche**
Gegenprobe ist schaedlicher als eine fehlende -- sie erzeugt einen Widerspruch,
wo keiner ist, und stellt eine richtige Lampenzaehlung in Frage.

Allgemein: **Wer eine Mustertabelle erweitert, verringert die Abstaende darin.**
Jeder neue Eintrag macht die Erkennung vollstaendiger und zugleich
empfindlicher. Beides gehoert zusammen betrachtet.

## Wo gilt diese Regel noch?

- [x] `SEGMENT_PATTERNS` — beide Varianten eingetragen
- [ ] Weitere Sonderformen (7 mit f-Segment, 1 auf der linken Seite) sind im
      Material noch nicht beobachtet.
- [ ] `digit_templates.py` fuehrt eine EIGENE Tabelle `DIGIT_SEGMENTS` mit den
      Lehrbuchmustern. Sie erzeugt die Vorlagen fuers Template Matching und hat
      dieselbe Luecke -- bisher nicht nachgezogen, weil der kalibrierte Leser
      Vorrang hat.
