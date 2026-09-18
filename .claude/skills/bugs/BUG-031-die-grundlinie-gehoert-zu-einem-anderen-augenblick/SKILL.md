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
| **Schweregrad** | **mittel** (2 von 910 Würfen; jeder verfälscht den Spielstand dauerhaft. Ein dritter Fall gehörte zu BUG-030 und ist behoben) |
| **Regressionstest** | `test_grundlinie_aus_spur.py` |

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

GIF: `debug/streitfaelle/streit_bahn4_f47227.gif`

Bahn 4, Wurf 26, Frame 47227:

```
GRUEN AN  47210
GRUEN AUS 47225      ->  15 Frames
Grundlinienfenster       25 Frames      -- schliesst nie
```

`_pending_baseline` wird beim Grün-AN **nicht geleert**. Bei GREEN_OFF steht
dort deshalb noch die Grundlinie des *vorigen* Wurfs -- und die war 0. Der
Kranz zeigte neun, abgezogen wurde nichts, gebucht wurden 9 statt 2.

**Die 15 Frames sind nicht die Grünphase der Anlage, sondern nur ihr Ende.**
Das GIF zeigt es Bild für Bild:

```
F47007  Gruen OFF      liegend 7      Tafel  025 / 7 / 0171
F47071  Gruen AN       liegend 7      Tafel  025 / ? / 0171   <- der Ball rollt
F47135  Gruen AN       liegend 9      Tafel  026 / 2 / 0171   <- Tafel hat es
F47210  GREEN_ON erkannt                                      <- 140 Frames spaeter
F47225  GREEN_OFF
```

Die Anlage war ab F47071 grün, die Kegel fielen um F47100–47135, und die Tafel
zeigte das Ergebnis sauber an. Unsere Zustandsmaschine meldete Grün-AN erst
**140 Frames (5,6 Sekunden) später**. Der Grund steht in der Grünspur:

```
F47070  Score 50.0  -> OFF
F47080  Score 52.8  -> UNKNOWN      Totzone
...     Score kriecht 52 -> 58      108 Frames lang UNKNOWN
F47210  Score 59.7  -> ON
```

Bahn 4 hat die schwächste Trennung aller vier Bahnen -- in `default.yaml`
gemessen und dokumentiert: AUS 36,1/41,7 gegen AN 56,5/63,0, Abstand **14,8**,
während die anderen Bahnen 26 bis 33 erreichen. Der Score braucht deshalb über
hundert Frames, um die Totzone zu durchqueren.

Die Kette ist damit vollständig, und keine ihrer Stufen ist eine Lampe:
schwache Grüntrennung → späte Erkennung → Grundlinienfenster öffnet erst nach
dem Wurf → es schliesst nicht mehr → Grundlinie des Vorgängers → 9 statt 2.

Gemessen über den ganzen Lauf: **2 von 933 Grünphasen sind kürzer als 25
Frames** (4 und 15 Frames). Genau eine davon fällt mit einem gebuchten Wurf
zusammen -- und das ist dieser.

**Er ist exakt reproduzierbar.** Der Lauf vom 2026-09-18 07:30 über denselben
Stream bucht bei Frame 47227 wieder Zeile für Zeile dasselbe:

```
31:29;47227;4;9;1 2 3 4 5 6 7 8 9;26;3;2;11;180;;VALID;0.45;2;...;0;...
```

Damit ist dieser Frame der Prüfstein für die Reparatur: Wer die Grundlinie
repariert, muss hier 2 sehen und sonst nichts ändern.

### Fall 2 — die Grünphase war 87 Sekunden lang (bewiesen)

GIF: `debug/streitfaelle/streit_bahn5_f60871.gif`

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

GIF: `debug/streitfaelle/streit_bahn2_f60851.gif`

Bahn 2, Wurf 17, Frame 60851. Grundlinie 0, obwohl bei F60750 sieben Kegel
liegen. Das GIF zeigt, dass sie schon **vor** dem Grün-AN lagen -- die
Grundlinie hätte also gar nicht schwierig zu messen sein dürfen:

```
F60591  Gruen OFF   liegend 7   Tafel  016 / 7 / 0122
F60667  Gruen AN    liegend 7   Tafel  --- unlesbar ---
F60670  GREEN_ON erkannt, Grundlinienfenster beginnt
F60761  Gruen AN    liegend 9   Tafel  017 / 2 / 0122
```

In der `lampenspur.csv` klafft für diese Bahn dennoch ein Loch:

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

### Der vierte Streitfall gehört nicht hierher — aber er gehört notiert

GIF: `debug/streitfaelle/streit_bahn5_f104524.gif`

Bahn 5, Wurf 20, Frame 104524: Lampen 8, Ziffer 0, und die Summe stützt die
**Lampen**. Hier ist nicht die Grundlinie schuld, sondern das Ziffernfeld. Am
Stream nachgemessen, Stelle 0 von `pin_count`:

```
F104480  gelesen '8'  conf 0.35 | 8: 86,2 %  0: 10,2 %
         Segmente a..g = [1.00 0.77 0.62 0.50 0.56 0.28 0.44]
F104510  gelesen '0'  conf 0.54 | 0: 88,4 %  8: 11,4 %
         Segmente a..g = [1.00 0.77 0.62 0.37 0.56 0.40 0.27]
F104520  gelesen '0'  conf 0.54 | 0: 98,3 %  8:  1,6 %
         Segmente a..g = [1.00 0.77 0.62 0.37 0.56 0.40 0.18]
```

**Nur das Mittelsegment bewegt sich**: 0,44 → 0,27 → 0,18. Alles andere steht
still. Eine 8 und eine 0 unterscheiden sich in genau diesem einen Segment -- es
rutscht unter die Schwelle, und aus der 8 wird eine 0.

Zwei Dinge daran sind schlimmer als der Einzelfall:

1. **Die falsche Lesung kommt mit der höheren Confidence.** `0` trifft ein
   gültiges Muster exakt und bekommt 0,54; `8` erreicht man nur über die
   Verteilung und bekommt den Festwert 0,35. Wer nach Confidence sortiert,
   sortiert hier falsch herum.
2. **Das Mittelsegment liegt auf dieser Bahn schon im Normalfall knapp.** Bahn 5
   hat im selben Lauf **35 von 228 unlesbaren Kegelziffern (15 %)**, während die
   anderen drei Bahnen zusammen auf eine kommen. Das riecht nach der Geometrie
   des Feldes, nicht nach diesem einen Wurf.

Beides ist noch nicht untersucht.

## Nachtrag 2026-09-18: Fall 3 gehört gar nicht hierher

Der Nutzer, nachdem er die GIFs gesehen hatte:

> *„schau dir bitte den 3. Fall nochmal an... er macht doch deutlich das das
> Problem systematisch ist und nicht auf verzögerte Grünphasen o.ä.
> zurückzuführen ist, ich könnte mir vorstellen mit einer guten Analyse kommen
> die anderen wieder zurück"*

Beides trifft zu, und beides ist nachgemessen.

**Fall 3 ist im Lauf vom 2026-09-18 verschwunden.** Derselbe Stream, dieselbe
Kalibrierung, aber mit der Reparatur aus BUG-030:

```
alt (17.09.)   F58873 W15 ... | F60851 W17 Kegel 9 Ziffer 2 Grundl 0  ERROR
neu (18.09.)   F58873 W15 ... | F60471 W16 Kegel 7 Ziffer 7 Grundl 0  VALID
                              | F60851 W17 Kegel 2 Ziffer 2 Grundl 7  VALID
```

Der verlorene Wurf 16 ist zurück -- und mit ihm stimmt die Grundlinie von
Wurf 17. Fall 3 war **keine eigene Krankheit, sondern eine Folge von BUG-030**:
Die festhängende Wache fror Bahn 2 über den ganzen Zyklus von Wurf 16 ein,
daher das 450-Frame-Loch in der Lampenspur, daher keine Grundlinie. Die Fälle
1 und 2 sind im neuen Lauf unverändert vorhanden.

## Das gemeinsame Muster -- und es ist nicht die Grünphase

| | Grünphase | Grundlinie | Folge | im neuen Lauf |
|---|---|---|---|---|
| Bahn 4 W26 | 15 Frames (Ende einer 154er) | zu klein (0 statt 7) | 9 statt 2 | unverändert |
| Bahn 5 W16 | 2167 Frames | zu gross (7 statt 0) | 2 statt 9 | unverändert |
| Bahn 2 W17 | normal, 179 Frames | zu klein (0 statt 7) | 9 statt 2 | **behoben (BUG-030)** |

Die Grünzeiten sind Auslöser, nicht Ursache. Sie entscheiden nur, **welcher
falsche Augenblick** getroffen wird. Die Krankheit selbst ist einfacher:

> **Die Grundlinie wird in einem einzigen schmalen Fenster gemessen, obwohl
> nebenher die ganze Zeit Lampen gelesen werden.**

Die Antwort stand in allen drei Fällen in unserer eigenen laufenden Messung:

```
Bahn 4   F47000-47125   liegend 7    <- die Grundlinie, 100 Frames vor dem Fenster
Bahn 5   F60750         liegend 0    <- die Anlage stellte neu auf, wir sahen es
Bahn 2   F60591/F60667  liegend 7    <- schon vor dem Gruen-AN gemessen
```

Wir schauen nur nie wieder hin.

### Gemessen: die laufende Spur trägt besser

Gegenprobe über den ganzen Lauf 2026-09-17 12:53, **874 Würfe mit lesbarer
Kegelziffer**. Verglichen wird die gebuchte Kegelzahl gegen die Ziffer der
Tafel. „Probe" nimmt als Grundlinie den **kleinsten Lampenstand seit dem
vorigen Wurf**, aus der `lampenspur.csv` -- also aus Messungen, die ohnehin
anfallen:

| Weg | richtig | |
|---|---|---|
| heute (Fenster nach Grün-AN) | 870 | 99,54 % |
| Probe, kleinster Stand | 871 | 99,66 % |
| Probe, 2× bestätigt | 871 | 99,66 % |
| **Probe, 3× bestätigt** | **872** | **99,77 %** |

„3× bestätigt" heisst: Ein Stand zählt nur, wenn er dreimal hintereinander so
gemessen wurde -- sonst bestimmt eine einzelne Lampe in der Dunkelphase des
Blinkens die Grundlinie. Ohne diese Bedingung kippt die Probe zwei andere
Würfe (Bahn 3 F43413, Bahn 2 F85720 mit einem negativen Ergebnis).

Die beiden dann noch verbleibenden Fehler sind **keine Grundlinienfehler**:

```
Bahn 2 F60851   Ziffer 2, Probe 9   -- der verlorene Wurf (BUG-030, behoben)
Bahn 5 F104524  Ziffer 0, Probe 8   -- die Ziffer ist falsch gelesen, nicht wir
```

**Beide Fälle dieses Bugs verschwinden, und es kommt keiner hinzu.**

Zweite, unabhängige Messung am laufenden Lauf 2026-09-18 (erste 408 Würfe mit
lesbarer Ziffer, also anderes Material als oben):

```
heute                406 richtig   99,51 %   2 falsch
min                  408 richtig  100,00 %   0 falsch
min, 2x bestaetigt   408 richtig  100,00 %   0 falsch
min, 3x bestaetigt   408 richtig  100,00 %   0 falsch
```

Der Gedanke trägt also -- gebaut ist er noch nicht. Das Werkzeug dazu:
`tools/messe_grundlinie.py <laufordner>`, gegen jeden Lauf wiederholbar.

Und es fällt nicht auf, weil die Grundlinie **kein eigenes Ergebnis** ist: Sie
verschwindet in einer Subtraktion. Ein falscher Abzug sieht aus wie eine
falsche Messung -- und lenkt den Verdacht auf die Lampen, die nichts dafür
können.

## Behoben und nachgemessen (2026-09-18)

Gebaut: Die Grundlinie kommt aus den laufenden Lampenmessungen
(`grundlinie_aus_spur`, `baseline_from_trace: true`,
`baseline_trace_confirm: 3`). Nachgemessen am Stream, mit dem neuen Code an
dieselben Stellen gesprungen:

| | vorher | nachher | Tafel |
|---|---|---|---|
| Bahn 4 W26 (F47227) | Kegel 9, Grundlinie 0 | **Kegel 2, Grundlinie 7** | Ziffer 2, Summe 171 |
| Bahn 5 W16 (F60871) | Kegel 2, Grundlinie 7 | **Kegel 9, Grundlinie 0** | Ziffer 9 |

Gegenprobe auf Verschlechterung, zwei Abschnitte gegen den alten Lauf:

```
F14000-20000   24 Wuerfe, 4 Bahnen   0 Unterschiede
F43000-48500   40 Wuerfe, 4 Bahnen   genau 1 Unterschied -- der Zielwurf
```

### Wer hier nachmisst, braucht Vorlauf

Der erste Anlauf startete bei F46000, also 1200 Frames vor dem Wurf -- und
Wurf 26 fehlte danach ganz. Das sah nach einer Verschlechterung durch die
Reparatur aus und war der Sprung selbst: Die Gruenschwellen lernen aus einem
gleitenden Histogramm von `adaptive_window: 1500` Frames. Mit zu wenig Vorlauf
stehen sie tiefer, der Score-Einbruch bei F47225 zaehlte als UNKNOWN statt OFF,
und ohne GREEN_OFF gibt es keinen Wurf.

Mit 5200 Frames Vorlauf ist die Gruenspur Frame fuer Frame dieselbe wie im
vollen Lauf. **Ein Sprung braucht mehr als `adaptive_window` Frames Vorlauf,
sonst misst man den Sprung und nicht die Aenderung.**

## Was daraus für die Reparatur folgte

Noch nicht gebaut. Festgehalten ist die Richtung, nicht die Lösung:

1. **Die Grundlinie aus der laufenden Messung ziehen, nicht aus einem
   Fenster.** Kleinster Lampenstand seit dem vorigen Wurf, dreimal bestätigt.
   Zweimal gemessen (siehe oben), beide Male besser, nie schlechter. Das
   Fenster nach dem Grün-AN kann als zweite Quelle bleiben -- aber nicht als
   einzige.
2. **`_pending_baseline` beim Grün-AN leeren.** Eine Grundlinie, deren Fenster
   nicht geschlossen hat, darf nicht die des Vorgängers sein. Lieber „unbekannt"
   als falsch. Unabhängig von 1. richtig.
3. **Eine unbekannte Grundlinie muss sichtbar bleiben.** `baseline_unknown`
   steht bereits im `ThrowResult` -- der Status zieht daraus noch keine Folge.
4. **Die Ziffer darf widersprechen.** In allen drei Fällen stand die richtige
   Zahl auf der Tafel, und die Summe bestätigte sie. Heute setzt sich die
   Lampenrechnung durch und die Gegenprobe notiert nur „gescheitert".

Was **nicht** zu tun ist: an den Grünschwellen drehen, damit Bahn 4 früher
schaltet. Das war meine erste Lesart, und sie hätte genau einen von drei
Fällen berührt.

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
