---
name: bug-013-rauschen-als-zustandswechsel
description: >
  Verhindert DETECT-Bug: Mitlaufende Schwellen zwischen zwei Perzentilen trennen
  blosses Rauschen, sobald das Signal lange in EINEM Zustand bleibt. Folge war
  ein Wurf, der als zwei gezaehlt wurde. Laden bei Arbeit an adaptiven
  Schwellwerten, Hysterese, Zustandserkennung oder wenn ein Zustand ohne
  erkennbaren Anlass kippt.
---

# BUG-013 — Aus Rauschen wurde ein Zustandswechsel

| | |
|---|---|
| **Kategorie** | `DETECT` |
| **Gefunden** | 2026-08-27, vom Nutzer beobachtet und eingegrenzt |
| **Schweregrad** | **hoch** — ein Wurf wurde als zwei gezaehlt |
| **Regressionstest** | `tests/unit/test_detectors.py::TestBug013RauschenAlsWechsel` |

## Symptom

Der Nutzer: *„es ist definitiv der Wurf 6 der als Wurf 6 und 7 erkannt wird"* --
auf einer Bahn erschien ein Wurf doppelt, Wurfzahl und Summe stimmten dadurch
nicht.

## Ursache

Die Spur der gruenen Lampe zeigt es Frame fuer Frame:

```
16664   Score 85,9   ON
16665   Score 83,8   UNKNOWN
16666   Score 78,8   OFF      <- Wechsel bei 78,8
...
16728   Score 79,8   OFF
16730   Score 79,8   ON       <- und zurueck bei 79,8
```

**Der Score faellt nie.** Er bleibt durchgehend zwischen 78 und 89 -- weit ueber
der absoluten AN-Schwelle von 45. Die Lampe leuchtete die ganze Zeit.

Schuld waren die mitlaufenden Schwellen aus BUG-011. Sie legen die Grenze
anteilig zwischen das beobachtete AUS- und AN-Niveau (20%- und 90%-Perzentil
der letzten 1500 Messungen). Leuchtet die Lampe aber lange durchgehend, liegen
**beide Perzentile in derselben Verteilung** -- und die Schwelle dazwischen
trennt nichts als Rauschen.

Die Sicherung dagegen existierte bereits (`adaptive_min_span: 12`), war aber zu
knapp bemessen: Reines Rauschen erzeugt schon eine Spanne von 3 bis 9, und mit
den Ausreissern reichte es ueber 12 hinaus.

## Die Messung

Ueber 65 896 Messungen (4 Bahnen, 11 Minuten):

```
Spanne 20%..90% bei durchgehend AN     3 .. 9
Spanne 20%..90% bei echtem Wechsel     4 .. 69
```

Die Bereiche **ueberlappen** -- eine saubere Trennung gibt es nicht.

Das ist aber unschaedlich, und darin liegt die Loesung: **Ist die Spanne klein,
sind die absoluten Schwellen ohnehin richtig** -- dann ist nichts gedriftet. Die
Anpassung wird nur gebraucht, wenn beide Zustaende im Fenster vorkommen UND das
Signal gewandert ist, und das zeigt sich als grosse Spanne.

Nachgerechnet ueber dieselbe Spur, alle vier Bahnen:

```
min_span=12:  7 Gruen-AUS-Phasen, davon 1 zu kurz  (16666, 64 Frames)
min_span=30:  6 Gruen-AUS-Phasen, davon 0 zu kurz
```

Keine echte Phase faellt weg. Gesetzt auf **30**.

## Die Regel

> **Eine Schwelle zwischen zwei Perzentilen setzt voraus, dass das Signal
> zweigipflig ist.** Ist es das gerade nicht, trennt sie die Verteilung
> mittendurch und macht aus Rauschen ein Ereignis.

Jede adaptive Schwelle braucht deshalb eine Prüfung, **ob die Anpassung
ueberhaupt anwendbar ist** -- und diese Pruefung muss am Rauschen gemessen sein,
nicht geschaetzt. Meine 12 waren geschaetzt.

## Zweiter Schutz auf anderer Ebene

Unabhaengig davon verwirft die Zustandsmaschine jetzt Wurffenster unter
100 Frames (`state_machine.min_throw_frames`). GEMESSEN ueber 486 Wuerfe: Das
kuerzeste echte Fenster dauerte 158 Frames, neun Fehlausloeser lagen unter 100,
dazwischen liegt nichts.

Beide Schutzmassnahmen greifen an verschiedenen Stellen: Die eine verhindert,
dass der Fehler entsteht; die andere faengt ihn ab, falls er auf anderem Weg
doch entsteht. Das ist beabsichtigt -- eine Fehlerklasse, die einen Wurf
verdoppelt, ist eine doppelte Absicherung wert.

## Was diesen Fehler ueberhaupt auffindbar gemacht hat

Die **Gruenspur** (`debug/<video>/lauf_*/gruenspur.csv`): Score und Zustand der
gruenen Lampe fuer jeden Frame. Ohne sie war die Frage „wieso hat er hier
ausgeloest?" nicht zu beantworten -- der Bilder-Mitschnitt beginnt erst beim
Ausloeser, und die entscheidenden Frames liegen davor.

Ein vorheriger Versuch, den Fehler aus den gespeicherten Bildern zu
rekonstruieren, fuehrte sogar in die Irre: Die Ereignisordner wurden zwischen
Laeufen wiederverwendet, sodass Bilder aus zwei verschiedenen Videos
nebeneinander lagen. Die daraus gebaute Zeitreihe war frei erfunden. Seitdem
bekommt jeder Lauf einen eigenen Ordner.

## Wo gilt das noch?

- [x] Gruene Lampe — `adaptive_min_span: 30`
- [ ] **Kegellampen:** Dort arbeitet die Anpassung anders (nur ein AUS-Niveau,
      AN ist gesaettigt bei 254 +- 3) und hat diese Schwaeche nicht. Die
      Sicherung dort ist `baseline_ignore_above`, die verhindert, dass
      leuchtende Lampen das AUS-Niveau anheben.
- [ ] `segment_relative_ratio` im Ziffernleser: ebenfalls relativ zum hellsten
      Segment. Dort ist die Verteilung aber immer zweigipflig, solange die
      Anzeige ueberhaupt leuchtet -- und das prueft `min_display_brightness`.
