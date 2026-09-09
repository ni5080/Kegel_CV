---
name: BUG-016-spaetes-gruen-an-verdirbt-die-grundlinie
description: Ein spät erkanntes GREEN_ON verschiebt das Grundlinienfenster in die Zeit, in der die Kegel fallen — der Wurf wird dann als "nichts hat sich geändert" verworfen. Laden bei Arbeit an baseline_offsets, aggregate_pin_readings, discard_unchanged_cycles, an der Grünerkennung oder wenn ein Wurf ohne erkennbaren Grund fehlt.
---

# BUG-016 — Spätes Grün-AN verdirbt die Grundlinie, der Wurf verschwindet

**Gefunden:** 2026-09-01 · **Schwere:** hoch (Wurf geht verloren) · **Status:** behoben (2026-09-01)

## Was passiert ist

Spieltag 2026-08-22, Bahn 2, Satz 2.3: Zwischen Wurf 25 (F180238) und Wurf 27
(F181062) fehlt ein Wurf. Der Nutzer hatte ihn vorhergesagt, bevor die Daten
angesehen waren — nach Wurf 25 stand die 7 (hinten links), nach dem fehlenden
Wurf lag sie. Es war ein Räumwurf auf einen einzelnen Kegel.

Der Zyklus ist nicht etwa übersehen worden. Er wurde ausgewertet und dann
verworfen:

```
Bahn 2: Gruenzyklus bei Frame 180615 ohne Veraenderung der Kegelraute
        ([1,2,3,4,5,6,7,8,9] vorher wie nachher) -- kein Wurf
```

Neun Kegel vorher, neun nachher. Tatsächlich lagen vorher acht.

## Warum — die Messung

Erste Vermutung war „die Grünphase war zu kurz". Das stimmt nicht. Die Phase
dauerte 175 Frames (7,0 s) und liegt damit im Normalbereich der Nachbarzyklen
(180 / 210 / 200 / 248 Frames). Zu kurz war nur der Teil, den der **Detektor**
davon gesehen hat: 106 Frames.

Aus `gruenspur.csv` des Laufs vom 2026-09-01, Bahn 2:

| Zyklus | Frames | Median-Score | Max | UNKNOWN-Anteil |
|---|---|---|---|---|
| Wurf 24 | 210 | 70,0 | 78,8 | 2,4 % |
| Wurf 25 | 200 | 71,2 | 77,5 | 0,0 % |
| **verworfen** | **175** | **60,0** | **70,0** | **57,1 %** |
| Wurf 27 | 248 | 71,2 | 78,8 | 0,0 % |

Der Score kroch über rund 70 Frames langsam nach oben — 22,5 (F180435) → 50,0
(F180438) → 60,0 (F180468) → 61,3 (F180498) → 62,5 (F180507) — statt wie sonst
in ein bis sechs Frames zu springen. Die AN-Schwelle liegt dabei ruhig: über
484 Übergänge nach ON auf Bahn 2 beträgt der erste ON-Score fast immer exakt
62,5. **Nicht der Maßstab ist gewandert, das Signal war schwächer.**

Damit meldete der Zustandsautomat GREEN_ON erst bei F180508 — rund 69 Frames
(2,8 s) nach dem tatsächlichen Einschalten.

Die Grundlinie wird bei GREEN_ON + `baseline_offsets` [0, 6, 12, 18, 25]
gemessen, hier also F180508 … F180533. Aus `lampenspur.csv`:

```
F180500   8 Lampen an   [1,3,4,5,6,7,8,9]   pin_lamp_2: 164,7  OFF
F180525   9 Lampen an   [1,...,9]           pin_lamp_2: 253,4  ON
```

Der geräumte Kegel fiel zwischen F180500 und F180525 — **mitten in das
Grundlinienfenster**. Die Grundlinie las neun statt acht, das Ergebnis las
ebenfalls neun, `neu_gefallen` blieb leer, und `discard_unchanged_cycles`
verwarf den Zyklus.

Gegenprobe: Bei rechtzeitigem GREEN_ON (~F180440) hätte das Fenster
F180440 … F180465 umfasst. Dort lagen nachweislich acht Kegel. Der Wurf wäre
mit einem Kegel gebucht worden.

## Die tiefere Ursache

Ein spätes GREEN_ON allein reicht nicht aus. Es wird erst tödlich, weil die
Grundlinie mit **derselben** Regel zusammengefasst wird wie das Ergebnis:

```python
self._pending_baseline = aggregate_pin_readings(self._baseline_samples)
```

`aggregate_pin_readings` bildet die **Vereinigung über die Frames** — eine
Lampe gilt als an, wenn sie in mindestens einer Messung leuchtete. Für das
Ergebnis ist das gemessen richtig (die Lampen blinken, BUG-007). Für die
Grundlinie ist es die falsche Richtung: Sie soll den Stand am **Anfang** der
Grünphase zeigen, die Vereinigung macht daraus den Stand am **Ende** des
Grundlinienfensters. Eine einzige zu späte Messung genügt.

Das Fenster reicht ohnehin 25 Frames (1 s) in die Grünphase hinein. Es hat also
keine Reserve gegen ein verzögertes GREEN_ON — es hat gar keine Reserve.

## Schaden

Im Lauf über den ganzen Spieltag (1706 Grünzyklen, 1690 Würfe):

- 21 Zyklen ohne Wurf, davon **5 mit langem UNKNOWN-Anlauf** (> 20 Frames
  Totzone vor dem ersten ON): Bahn 2 F180506, Bahn 3 F66750, Bahn 4 F47150 und
  F144401, Bahn 5 F296850.
- 242 Räumwürfe insgesamt; nur 2 mit Abweichung zwischen Lampenzahl und
  Tafelziffer. Die Vereinigungsregel ist im Normalfall harmlos.

Der Schaden entsteht nicht durch den falschen Wert, sondern durch den
**Versatz**: Ein fehlender Wurf schiebt die restliche Wurfnummernkette des
Satzes um eins — derselbe Mechanismus wie bei `discard_static_zero_cycles`.

## Was daraus zu lernen ist

> **Eine Zusammenfassung über Frames hat eine Richtung. Wer sie von einer
> Messung auf eine andere überträgt, überträgt auch diese Richtung — und für
> die andere Messung zeigt sie womöglich falsch herum.**

Die Vereinigung ist für das Ergebnis am Material belegt: Kegel kommen im Lauf
einer Grünphase dazu, also ist das Maximum richtig. Genau deshalb ist sie für
die Grundlinie falsch: Dort ist alles, was dazukommt, bereits der Wurf selbst.

Zweite Lektion, allgemeiner:

> **Ein Zeitfenster, das an einem erkannten Ereignis hängt, erbt dessen
> Verzögerung.** `baseline_offsets` ist gegen den Zeitpunkt des GREEN_ON
> gemessen, nicht gegen den Zeitpunkt, an dem die Lampe wirklich anging. Solange
> die Erkennung schnell ist, fällt der Unterschied nicht auf. Er fällt genau
> dann auf, wenn sie es einmal nicht ist.

## Geprüfte Abhilfen (2026-09-01)

**Schnitt statt Vereinigung für die Grundlinie — verworfen.** Gemessen an 7245
Lampen-Ereignissen: 37,97 % der Lampen blinken innerhalb eines Messfensters,
sind also in einigen der zehn Frames an und in anderen aus. Gegen die
Tafel-Ziffer als Wahrheit (655 Würfe in die Vollen) trifft die Vereinigung
94,05 %, der Schnitt 48,70 % — bei 192 Würfen verliert er alle neun Kegel. Drei
Integrationstests schlagen fehl. Mehrheit (69,92 %) taugt ebenso wenig: Die
Verteilung der AN-Messungen ist breit (2/10 bis 8/10), es gibt kein Tal, in das
man eine Grenze legen könnte.

**Fenster verkürzen — hilft, reicht aber nicht.** Ab fünf Messungen über 16
Frames Spanne ist die Genauigkeit ausgereizt (94,35 %); die heutigen
`baseline_offsets` reichen bis +25 und gewinnen damit nichts mehr. Neun Frames
weniger Angriffsfläche sind billig zu haben. Den Fall auf Bahn 2 hätte es
nicht gerettet: Bei 69 Frames Verspätung liegt auch ein kurzes Fenster
vollständig in der Fallzeit.

**Gebaut: die Grundlinie aus ZWEI Quellen.** Der Stand kurz vor dem Gruen-AN
haengt an keiner Erkennung — beim Raeumen bleiben die Ergebnislampen an, bis
der naechste Wurf abgeschlossen ist. Er wird waehrend der Pause ohnehin
gelesen (Live-Vorschau, alle 5 Frames) und nur noch aufgehoben.

Allein taugt er nicht: Beim Aufstellen loescht die Anlage die Lampen, und das
faellt gemessen in 3 von 1610 Faellen in die letzten 17 bis 24 Frames vor dem
Gruen-AN — dann ist der Stand davor zu hoch. Beide Fehler zeigen aber in
dieselbe Richtung: **falsch ist immer der groessere Wert.** Darum die
Schnittmenge (`baseline_aus_zwei`): Ein Kegel gehoert zur Grundlinie, wenn er
vorher UND nachher lag.

| Grundlinie aus | richtig von 1610 | Quote |
|---|---|---|
| nur nachher (bisher) | 1604 | 99,63 % |
| nur vorher | 1601 | 99,44 % |
| **Schnittmenge** | **1604** | **99,63 %** |

Es geht also nichts verloren -- und die verworfenen Zyklen kommen zurueck.

## Verifikation: Vollauf ueber den ganzen Spieltag (2026-09-01)

`lauf_2026-09-01_17-38-42`, dieselbe Quelle wie der Vergleichslauf `14-08-10`,
312 784 Frames. Beide Wurflisten Zeile fuer Zeile verglichen:

| | vorher | nachher |
|---|---|---|
| Wuerfe | 1690 | **1695** |
| davon VALID | 1662 | **1667** |
| EMPTY / ERROR | 13 / 15 | **13 / 15** |
| Raeumwuerfe | 242 | **247** |
| Kegel gesamt | 11 477 | **11 483** |

**Fuenf Wuerfe kamen hinzu, keiner ging verloren** -- die Differenzmenge in der
Gegenrichtung ist leer. EMPTY und ERROR bleiben unveraendert: Der Fix bringt
nur saubere Wuerfe dazu, er verdirbt keinen bestehenden.

Die fuenf, jeder mit der Tafel-Ziffer als unabhaengiger Bestaetigung:

| Bahn | Gruen-AN | Meldung | Grundlinie | Kegel | Wurfbild | Ziffer | Status |
|---|---|---|---|---|---|---|---|
| 4 | 41026 | 41147 | 7 | 2 | 5 7 | **2** | VALID |
| 3 | 66750 | 66871 | 8 | 1 | 8 | **1** | VALID |
| 4 | 144401 | 144523 | 7 | 1 | 4 | **1** | VALID |
| 2 | 180506 | 180615 | 8 | 1 | 7 | **1** | VALID |
| 5 | 296850 | 296973 | 8 | 1 | 6 | **1** | VALID |

Alle fuenf sind Raeumwuerfe, alle fuenf VALID, und bei allen fuenf nennt die
Anzeigetafel dieselbe Kegelzahl wie die Lampen. Das ist die Bestaetigung aus
einer Quelle, die am Fix nicht beteiligt ist.

**Die zweite Quelle greift nur dort ein, wo sie gebraucht wird.** Ueber 1702
Gruenzyklen meldet das Log genau fuenf Widersprueche zwischen vorher und
nachher -- und es sind genau diese fuenf. In den uebrigen 1697 Zyklen sind
beide Messungen einig; die Schnittmenge aendert dort nichts.

**Ein Fall der Vorhersage traf nicht zu.** Die Analyse hatte Bahn 4 F47150
erwartet (langer Anlauf, kein Wurf); zurueck kam stattdessen Bahn 4 F41026, den
die Anlauf-Heuristik nicht gefunden hatte -- sein Anlauf betrug nur 7 Frames.
Was diese fuenf wirklich verbindet, ist nicht der Anlauf, sondern ein
**schwaches Gruensignal**:

| Bahn | Gruen-AN | Anlauf | max. Score der Phase |
|---|---|---|---|
| 4 | 41026 | 7 | 56,2 |
| 3 | 66750 | 50 | 68,1 |
| 4 | 144401 | 46 | 60,0 |
| 2 | 180506 | 56 | 70,0 |
| 5 | 296850 | 92 | 44,4 |

Zum Vergleich: gesunde Zyklen auf Bahn 2 erreichen 77 bis 79. Der lange Anlauf
ist ein *Symptom* der schwachen Phase, nicht die Ursache -- und er ist nicht
das einzige. Damit gilt der Fix breiter als der Fehlerpfad, aus dem er
entstanden ist: Der Stand aus der Pause haengt an **gar keiner** Eigenschaft
der Gruenerkennung, also traegt er auch dort, wo sie auf andere Weise irrt.

**F47150 blieb verworfen, aus einem anderen Grund.** Auf Bahn 4 lagen die
beiden stehenden Kegel dauerhaft in der Totzone der Lampenerkennung
(Helligkeit 210 bei AUS-Schwelle 198 und AN-Schwelle 234, ueber 350 Frames
stabil UNKNOWN). Bahn 4 hat ueber alle neun Lampen 6 bis 9 % UNKNOWN, Bahn 2
nur 0,3 %. Warum die zweite Quelle dort trotzdem neun statt sieben Kegel
lieferte, ist aus den vorhandenen Spuren nicht zu belegen -- siehe Q13.
Es ist ein eigener Fehlerpfad, nicht dieser.

**Die Reserve, richtig gemessen.** Der Stand aus der Pause ist sauber, solange
der Kegel erst NACH dem erkannten Gruen-AN faellt. Frueher stand hier "rund 100
Frames (4 s)" -- diese Zahl stammte aus einem Config-Kommentar, der etwas
anderes misst (Wurfzaehler bis GREEN_OFF). Der Nutzer hat sie zu Recht
angezweifelt.

Gemessen wurde daraufhin der Einschlag selbst: vom erkannten Gruen-AN bis zur
ersten neu leuchtenden Lampe, 1448 Zyklen.

| Wurfart | Anzahl | 1. Perzentil | 5. Perzentil | Median | unter 25 F | unter 50 F |
|---|---|---|---|---|---|---|
| in die Vollen | 1207 | 67 F (2,7 s) | 85 F | 166 F (6,6 s) | 0 | 0 |
| **Raeumen** | 235 | **50 F (2,0 s)** | 57 F | 114 F (4,6 s) | 0 | 2 (0,85 %) |

Beim Raeumen wird deutlich zuegiger geworfen -- man zielt auf wenige Kegel.
Das ist genau die Wurfart, die BUG-016 trifft.

**Zwei Vorbehalte zu dieser Tabelle.** Erstens misst sie ab dem ERKANNTEN
Gruen-AN; wo die Erkennung verspaetet war, ist der Wert entsprechend kleiner.
Zweitens fehlen genau die fuenf kritischen Zyklen -- sie wurden ja verworfen
und stehen deshalb in keiner `wuerfe.csv`.

**Was daraus folgt:** Kritisch wird es, wenn der Anlauf der Gruenerkennung
groesser ist als der Einschlagverzug. Der Anlauf liegt bei 90 % der Zyklen
unter 4 Frames, im 99. Perzentil bei 41, im Maximum bei 120. Der Abstand ist
also normalerweise komfortabel und schrumpft nur in den seltenen Faellen mit
langem Anlauf auf null. In diesem Video reichte er in allen fuenf Faellen.

**Bestaetigt am Material** (Vollauf 2026-09-01): +5 Wuerfe, -0 Verluste,
EMPTY und ERROR unveraendert.

**Schalter:** `sampling.baseline_before_green` (Standard an),
`sampling.baseline_before_frames` (50).
**Regressionstests:** `test_pipeline_smoke.py::TestBug016GrundlinieVorGruen` —
drei Faelle: der Raeumwurf kommt an, ohne die zweite Quelle geht er verloren,
und das Aufstellen bleibt unberuehrt.

**Nicht gebaut bleibt der Startzeitpunkt.** Wirksam wäre nur, das Fenster am
tatsächlichen Anstieg des Grünscores auszurichten statt am gemeldeten
Zustandswechsel — oder zu erkennen, dass innerhalb des Grundlinienfensters eine
Lampe von aus auf an gewechselt hat, und den Zyklus dann keinesfalls als
"unverändert" zu verwerfen. Beides ist noch nicht gebaut.

## Wo das sonst noch lauern kann

- `_read_late_fields` und der Fehlwurfzähler hängen ebenfalls an Fensterrändern.
- `green_phase_interval` beginnt erst nach dem Grundlinienfenster — verschiebt
  sich dieses, verschiebt sich auch der Beginn des Mitlesens.
- Jede künftige Messung „kurz nach Ereignis X" hat dasselbe Problem.

## Prüfen, ob es wieder auftritt

`tools/` — aus `gruenspur.csv` die ON-Phasen bilden (UNKNOWN hält den letzten
Zustand), den UNKNOWN-Anlauf vor dem ersten ON zählen und gegen `wuerfe.csv`
prüfen, ob am Phasenende ein Wurf steht. Zyklen mit Anlauf > 20 Frames **und**
ohne Wurf sind Kandidaten für genau diesen Fehler.
