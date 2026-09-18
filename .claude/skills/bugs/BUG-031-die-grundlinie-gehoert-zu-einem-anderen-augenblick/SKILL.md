---
name: bug-031-die-grundlinie-gehoert-zu-einem-anderen-augenblick
description: >
  Verhindert falsche Kegelzahlen durch eine Grundlinie, die zu einem anderen
  Zeitpunkt gemessen wurde als der Wurf. Laden bei Arbeit an `baseline_offsets`,
  an `baseline_aus_zwei`, am Räumen -- und immer dann, wenn ein Messfenster an
  einem Ereignis hängt, dessen Dauer nicht garantiert ist.
---

# BUG-031 — Die Grundlinie gehört zu einem anderen Augenblick

| | |
|---|---|
| **Kategorie** | `ANALYSE` / Räumen |
| **Gefunden** | 2026-09-18, aus dem Vergleich Lampen/Ziffer |
| **Schweregrad** | **mittel** (3 von 910 Würfen = 0,3 %; jeder verfälscht den Spielstand dauerhaft) |
| **Regressionstest** | noch offen |

## Der Satz des Nutzers, der die Blickrichtung drehte

> *„also ganz wichtig, die Lampen lügen nie! Es ist immer unsere Auswertung...
> also wenn die Ziffern sich gegenseitig bestätigen, dann wissen wir, der
> Algorithmus der Lampen ausliest, ist kaputt"*

Das ist kein Nebensatz, sondern eine Beweisregel. Widersprechen sich
Kegelkranz und Kegelziffer, war die Frage bisher offen: *Wer hat recht?*
Bestätigen sich aber **Ziffer und Summenanzeige** gegenseitig -- zwei getrennte
Ziffernfelder --, dann ist die Frage entschieden, und der Fehler liegt bei uns.

Genau das war hier der Fall. Und der eigentliche Fund: **Die Lampen waren
jedes Mal richtig gelesen.** Der Kranz zeigte wirklich neun. Falsch war, was
wir davon abgezogen haben.

## Symptom

`tools/vergleiche_lampen_ziffern.py` über den Lauf 2026-09-17 12:53
(910 Würfe, alle vier Bahnen):

```
Bahn Wuerfe beide da        einig  uneinig Ziffer stumm
   2    226      226   225  99.6 %        1            0
   3    229      228   228 100.0 %        0            1
   4    227      227   226  99.6 %        1            0
   5    228      193   191  99.0 %        2           35

Zur Kontrolle -- unstrittige Wuerfe mit Summenzeugen: 714 von 722 (98,9 %)

    Zeit   Frame Bahn Wurf Sp Lampen Ziffer  Summe  Urteil
   31:29   47227    4   26  3      9      2    171 -> Ziffer
   40:34   60851    2   17  4      9      2    122 -> Ziffer
   40:34   60871    5   16  4      2      9    123 -> Ziffer
   69:40  104524    5   20  6      8      0    137 -> Lampen
```

Drei Fälle, in denen sich Ziffer und Summe einig sind und die gebuchte
Kegelzahl widerlegen. (Der vierte geht andersherum aus: Dort stützt die
Summe die Lampen, die Ziffer ist falsch gelesen -- ein Ziffernproblem,
nicht dieses hier.) In allen dreien steht in der `wuerfe.csv` eine
Grundlinie, die zum Wurf nicht passt.

## Die Ursache: das Messfenster hängt an GREEN_ON

Die Grundlinie -- *wie viele Kegel lagen schon vor diesem Wurf* -- wird einmal
gemessen, kurz nach dem erkannten Grün-AN:

```yaml
baseline_offsets: [0, 6, 12, 18, 25]   # Frames nach GREEN_ON
baseline_before_frames: 50             # Gegenprobe davor
```

Übernommen wird sie bei GREEN_OFF (`lane_processor.py`):

```python
if event is not None and event.event is EventType.GREEN_OFF:
    ...
    self._baseline_pins = self._pending_baseline
```

Das setzt still zweierlei voraus: Die Grünphase dauert **mindestens 25 Frames**,
und sie dauert **nicht so lange, dass die Anlage dazwischen neu aufstellt**.
Beides ist nicht garantiert -- und genau dort brach es.

### Fall 1 — die Grünphase war kürzer als das Fenster (bewiesen)

Bahn 4, Wurf 26, Frame 47227:

```
GRUEN AN  47210
GRUEN AUS 47225      ->  15 Frames
Grundlinienfenster       25 Frames      -- schliesst nie
```

`_pending_baseline` wird beim Grün-AN **nicht geleert**. Bei GREEN_OFF steht
dort deshalb noch die Grundlinie des *vorigen* Wurfs -- und die war 0. Der
Kranz zeigte neun, abgezogen wurde nichts, gebucht wurden 9 statt 2.

Gemessen über den ganzen Lauf: **2 von 933 Grünphasen sind kürzer als 25
Frames** (4 und 15 Frames). Genau eine davon fällt mit einem gebuchten Wurf
zusammen -- und das ist dieser.

### Fall 2 — die Grünphase war 87 Sekunden lang (bewiesen)

Bahn 5, Wurf 16, Frame 60871:

```
Wurf 15    F58601   7 Kegel liegen
GRUEN AN   F58702   Grundlinie gemessen: 7   <- damals richtig
...
F60750     Lampenspur: 0 AN   <- die Anlage hat neu aufgestellt
F60850     Lampenspur: 9 AN   <- der Wurf
GRUEN AUS  F60869                           ->  2167 Frames = 87 s
```

Ein normaler Zyklus dauert auf dieser Bahn 250 Frames. Hier lag zwischen
Messung und Wurf ein vollständiges Neuaufstellen. Die Grundlinie war um 87
Sekunden veraltet, und abgezogen wurden 7 Kegel, die längst wieder standen:
gebucht 2 statt 9.

Die vorhandene Schutzklausel greift hier **nicht**:

```python
verschwunden = base_pins - end_pins
if verschwunden:
    ...  # "neu aufgestellt, Grundlinie verworfen"
```

Sie erkennt das Neuaufstellen daran, dass ein Kegel der Grundlinie am Ende
wieder steht. Fällt der Wurf aber *alle neune*, ist `end_pins` vollständig,
`verschwunden` leer -- und die veraltete Grundlinie überlebt ausgerechnet den
Fall, in dem sie am meisten schadet.

### Fall 3 — im Grundlinienfenster war die Bahn blind (wahrscheinlich)

Bahn 2, Wurf 17, Frame 60851. Grundlinie 0, obwohl bei F60750 sieben Kegel
liegen. In der `lampenspur.csv` klafft für diese Bahn ein Loch:

```
F60300 ... F60750    keine einzige Lampenmessung   (450 Frames)
```

Das Grundlinienfenster (F60670–60695) liegt mitten darin. Ohne Messung bleibt
die Grundlinie leer -- und leer heisst im Code *„es lag nichts"*, nicht *„wir
wissen es nicht"*. Derselbe Fehlschluss wie in
[BUG-027](../BUG-027-null-ist-nicht-aus/SKILL.md): **Null ist nicht aus, und
keine Messung ist keine Null.**

Dazu kommt, dass in derselben Bahn kurz zuvor ein Wurf verloren ging
(Grünphase F59073–60469, 1396 Frames; Wurf 16 fehlt, Status `ERROR`,
„Wurfnummer lückenlos" gescheitert) -- das Muster aus
[BUG-030](../BUG-030-wurf-faellt-in-die-erholungszeit/SKILL.md).

Dieser Fall ist **nicht abschliessend belegt**: Die `lampenspur.csv` schreibt
die Messungen des Grundlinienfensters nicht mit, das Loch beweist nur, dass
dort nichts gelesen wurde. Was fehlt, ist eine Wiederholung mit
mitgeschriebenem Fenster.

## Das gemeinsame Muster

Alle drei Fälle sind dieselbe Krankheit in zwei Richtungen:

| | Grünphase | Grundlinie | Folge |
|---|---|---|---|
| Bahn 4 W26 | 15 Frames, zu kurz | zu klein (0 statt 7) | 9 statt 2 |
| Bahn 5 W16 | 2167 Frames, zu lang | zu gross (7 statt 0) | 2 statt 9 |
| Bahn 2 W17 | Bahn blind | zu klein (0 statt 7) | 9 statt 2 |

**Ein Messfenster hängt an einem Ereignis, dessen Dauer niemand zusichert.**
Solange die Grünphase das tut, was der Regelfall vorsieht, stimmt alles. Die
0,3 % sind genau die Zyklen, die es nicht taten.

Und es fällt nicht auf, weil die Grundlinie **kein eigenes Ergebnis** ist: Sie
verschwindet in einer Subtraktion. Ein falscher Abzug sieht aus wie eine
falsche Messung -- und lenkt den Verdacht auf die Lampen, die nichts dafür
können.

## Was daraus für die Reparatur folgt

Noch nicht gebaut. Festgehalten ist die Richtung, nicht die Lösung:

1. **`_pending_baseline` beim Grün-AN leeren.** Eine Grundlinie, deren Fenster
   nicht geschlossen hat, darf nicht die des Vorgängers sein. Lieber „unbekannt"
   als falsch.
2. **Eine unbekannte Grundlinie muss sichtbar bleiben.** `baseline_unknown`
   steht bereits im `ThrowResult` -- der Status zieht daraus noch keine Folge.
3. **Die Grundlinie an den Wurf binden, nicht an das Grün-AN.** Gebraucht wird
   der Lampenstand kurz *bevor* die Kegel fallen. Bei einer 87 Sekunden langen
   Grünphase ist das nicht deren Anfang.
4. **Die Ziffer darf widersprechen.** In allen drei Fällen stand die richtige
   Zahl auf der Tafel, und die Summe bestätigte sie. Heute setzt sich die
   Lampenrechnung durch und die Gegenprobe notiert nur „gescheitert".

## Die Regel, die dieser Bug hinzufügt

BUG-027: *Null ist nicht aus.*
BUG-030: *Eine Erholungsfrist, die länger ist als das Ereignis, verdeckt es.*

BUG-031 fügt hinzu: **Ein Messfenster erbt die Zuverlässigkeit des Ereignisses,
an dem es hängt.** Das Fenster war sauber gewählt und sauber gemessen
(99,63 % über 1610 Würfe, siehe `baseline_before_green`). Es hängt nur an einer
Grünphase, deren Länge niemand zugesichert hat -- und in 0,2 % der Fälle ist
sie kürzer als das Fenster selbst, in anderen zehnmal zu lang.

Zweitens, und das ist die Regel des Nutzers: **Wenn zwei unabhängige Zeugen
sich bestätigen, ist der dritte nicht strittig, sondern widerlegt.** Solange
der Bericht „uneinig" sagte, sah es nach einem Patt aus. Sobald man die Summe
befragt, zeigt er auf die Stelle, an der zu suchen ist -- und das war nicht
der Lampenleser.
