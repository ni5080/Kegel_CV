---
name: bug-034-eine-lampe-die-nie-hell-genug-wird
description: >
  Eine einzelne Kegellampe, deren ROI zwei Pixel danebensitzt, kostet
  Punkte und ganze Würfe. Laden bei Arbeit an Lampenschwellen, an
  `adaptive_baseline`, an der Kalibrierung von Lampen-ROIs -- und immer
  dann, wenn eine Bahn auffällt und die anderen drei nicht.
---

# BUG-034 — Eine Lampe, die nie hell genug wird

| | |
|---|---|
| **Kategorie** | `KALIBRIERUNG` / Lampenerkennung |
| **Gefunden** | 2026-09-25, vom Nutzer an der Tafel abgelesen |
| **Schweregrad** | hoch (39 Würfe falsch, 1 Wurf ganz verloren, eine Bahn) |
| **Belege** | `debug/streitfaelle/lampe8_pixel.png`, `lampe8_verlorener_wurf27.png`, `streit_bahn5_f228922.gif`, `streit_bahn5_f219041.gif` |
| **Werkzeuge** | `tools/messe_lampenversatz.py`, `tools/lampe_pixel.py` |

## Symptom

Der Nutzer: *„Ebenfalls auf Bahn 5 wird die Lampe 8 manchmal irrtümlich 'AUS'
gelesen, obwohl sie an ist. Bspw. im letzten Spiel bei Wurf 1, bei Wurf 9, bei
Wurf 13, bei Wurf 14 (bei Wurf 15 korrekt AN und bei Wurf 29 korrekt AUS)...
Ich glaube hier saß aber zusätzlich die Kalibrierung leicht ungut."*

Er hatte in allen sechs Fällen recht.

## Messung

Über den ganzen Spieltag: **19 Würfe, bei denen die Ziffer 9 sagt und die
Lampen 8. Alle auf Bahn 5, jedes Mal fehlt Kegel 8.** Auf keiner anderen Bahn
ein einziger Fall.

Anteil der Messungen im Graubereich zwischen AUS- und AN-Schwelle, über 1,49
Mio. Einzelmessungen (Promille):

```
Kegel     Bahn 2    Bahn 3    Bahn 4    Bahn 5
1            1.6       2.1       2.5       1.3
...
8            1.2       1.8       2.3      89.2   <--
9            1.3       1.7       1.9       2.2
```

Fünfzigmal so hoch wie alles andere. Alle übrigen 35 Lampen liegen zwischen
0,9 und 3,6 Promille.

## Ursache — an den rohen Pixeln, ohne jeden Detektor

Der Nutzer hatte den entscheidenden Einwand gegen den ersten Beleg: *„Die GIFs
zeigen doch immer nur an, dass Lampe 8 fehlt?"* Richtig — die
Lampenbeschriftung im Streitfall-GIF stammt aus demselben Detektor, dessen
Messung in Frage steht. Sie kann den Fehler nicht belegen, **sie ist der
Fehler**. Daraufhin `tools/lampe_pixel.py`, das nichts beschriftet, was es
misst:

```
Frame   Lage      K1   K2   K3   K4   K5   K6   K7   K8   K9
228743  AUS      250  244  227  237  154  234  246  146  239
228922  AN       249  243  226  237  241  233  245  207  238
```

Kegel 5 geht von 154 auf 241 — so sieht eine Lampe aus, die angeht. Kegel 8
geht von 146 auf **207** und bleibt damit unter ihrer AN-Schwelle von 209,9.

Und der Grund:

```
Lampe 8, dasselbe Bild, ROI probeweise verschoben:
Frame     dy=0   dy=-1   dy=-2   dy=-3
228922     207     220     223     219
219038     205     219     221     217
```

Das Rechteck ist 7x6 Pixel groß und schneidet unten in den dunklen Rand der
Fassung. Auf `lampe8_pixel.png` ist der dunkelrote Streifen an Kegel 8 zu
sehen, den keine andere Lampe hat.

## Zwei ganz verschiedene Schäden

1. **Ein Kegel zu wenig oder zu viel.** Im Ergebnis fehlt der Kegel; in der
   Grundlinie gilt er als neu gefallen. 39 Würfe, davon 6 in Räumwürfen.
2. **Der ganze Wurf verschwindet.** Bahn 5, Lauf 3.3, Wurf 27. Das
   gespeicherte Ereignis sagt es wörtlich:

   ```
   event_386   gelesen 8 Kegel [1,2,3,4,5,6,7,9]
               complete=False   UNKNOWN: ['pin_lamp_8']   throw: null
   ```

   Eine unvollständige Lampenmessung macht den Zyklus ungültig. Die Tafel
   zeigte `027 / 1`.

## Korrektur der Daten (nicht des Laufs)

`tools/spieltag_tabelle.py` rechnet die 39 Fälle heraus. Schiedsrichter ist
zuerst die **Kegelziffer**, und wo sie schweigt die **Tafelsumme** — nie
beide. Die Tafelsumme steht in einem anderen Ziffernfeld und weiß nichts von
den Lampen; sie stützt jede einzelne Korrektur, und ihre Trefferquote auf
Bahn 5 stieg von 90,4 auf 98,0 Prozent.

## Was noch NICHT behoben ist

Die Kalibrierung selbst. Sie wird je Spieltag neu gemacht — der Nutzer:
*„dann das (-1,-1) nicht korrigieren... denn es wird ja jeder Spieltag immer
neu kalibriert, und das scheint ja zu passen (außer kegel 8)."* Offen ist
damit die Frage, ob die **Kalibrier-Oberfläche** eine Lampe melden sollte,
deren Helligkeit im Vergleich zu ihren Nachbarn zurückbleibt. `p99` je Lampe
gegen den Median der übrigen acht wäre der Test; Bahn 5 Kegel 8 lag bei 217
gegen 244–252.

## Lehre

**Ein Beleg, der aus dem geprüften Verfahren stammt, ist kein Beleg.** Das GIF
zeigte neun Lampen, weil der Detektor neun Lampen meldete — beschriftet mit
genau der Information, die falsch war. Erst die rohen Pixel nebeneinander
haben die Frage entschieden. Regel 7 braucht deshalb eine Ergänzung: Bei jeder
Lampenfrage gehört die **unbeschriftete Pixelgegenüberstellung** dazu.

**Eine adaptive Schwelle verbirgt einen Kalibrierfehler.** Weil das AUS-Niveau
je Lampe mitläuft, sah Lampe 8 nie kaputt aus — sie hatte eine plausible
Schwelle, nur keine Luft darüber. Sichtbar wird so etwas nur im **Vergleich
der Lampen untereinander**, nicht in der einzelnen Messung.
