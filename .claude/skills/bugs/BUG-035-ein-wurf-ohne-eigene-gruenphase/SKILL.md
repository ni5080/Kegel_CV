---
name: bug-035-ein-wurf-ohne-eigene-gruenphase
description: >
  „Eine Grünphase = ein Wurf" gilt nicht immer. Laden bei Arbeit an der
  Zustandsmaschine, am Frame-Sampler, am Fehlwurfzähler, an der
  Grünerkennung -- und immer dann, wenn eine Wurfnummer springt oder ein
  Grünzyklus kein Ergebnis liefert.
---

# BUG-035 — Ein Wurf ohne eigene Grünphase

| | |
|---|---|
| **Kategorie** | `ANALYSE` / Zustandsmaschine |
| **Gefunden** | 2026-09-24/25, vom Nutzer in der Datenbank bemerkt |
| **Schweregrad** | **hoch** (seit 2026-10-06 gemessener Schaden: ein Wurf mit 9 Kegeln verloren, der Folgewurf um 2 zu hoch) |
| **Belege** | `debug/streitfaelle/streit_bahn5_f34300-35900.gif`, `streit_bahn5_f137732.gif`, `streit_bahn5_f74415.gif` |

## Symptom

Der Nutzer, über eine Stelle in der Datenbank: *„da wird ein ganzer Wurf
geschluckt."* Zwischen zwei Würfen mit Nummer stehen zwei Zeilen **ohne**
Wurfnummer, die Tafel springt von 26 auf 29.

## Zwei verschiedene Ursachen mit demselben Ergebnis

### A — Die Anlage schaltet Grün gar nicht aus (Fehlwurf)

Bahn 5, Frame 34528 bis 35211: **683 Frames, 34 Sekunden, eine einzige
Grünphase.** Der Grünscore bleibt durchgehend bei 50–60, kein einziger
Einbruch. In dieser einen Phase zählt die Tafel von `026` über `027` auf
`028`.

Der Grund ist physisch: Wurf 27 war ein **Fehlwurf**. Die Kugel kam nicht an,
die Maschine räumte nicht ab, also blieb Grün an. Der Wurf erzeugt kein
Grünsignal — für die Zustandsmaschine existiert er nicht.

Über den ganzen Spieltag, alle fünf über den Fehlwurfzähler nachgetragenen
Würfe, ohne Ausnahme:

```
Bahn Spiel Wurf  Ortszeit  Grünphase    ÷ Median
   5     3   27  12:22:41  683 Frames      3,2x
   3     7    9  12:56:38  510             2,6x
   5    10   20  13:24:39  782             3,7x
   5    13   25  14:06:18  582             2,8x
   4    14   22  13:58:48  606             3,0x
```

### B — Der Grünscore bleibt in der Totzone

Bahn 5, Lauf 1.4, Wurf 19, Frame 74270–74415. Der Zyklus **existiert**, 145
Frames, sauber an und aus — aber:

```
74270  Score 52.5  ON
74273..74414  Score konstant 50.0  UNKNOWN      <- 140 Frames Totzone
74417  Score 38.8  OFF
```

Genau **ein** Messpunkt war stabil AN. Es gibt für diesen Zyklus nicht einmal
ein Ereignis. Die Tafel zeigte `019 / 1`, die Tafelsumme bestätigt den einen
Kegel. Der Wurf ist ersatzlos weg.

Auf Bahn 5 ist das kein Zufall: Anteil UNKNOWN der grünen Lampe je Bahn —
0,3 % / 0,9 % / 1,8 % / **4,0 %**, bei gleichzeitig höchstem Median (66,2).
Nicht zu dunkel, sondern zu unruhig.

## Warum im Lauf trotzdem nichts verlorenging (Fall A)

Der Nutzer fragte zu Recht nach: *„aber haben wir die Fehlwürfe nicht trotzdem
alle erfasst? Also auch ohne Grünspur?"* Ja, lückenlos:

```
Bahn Spiel   Zähler zuletzt   nachgetragen   0-Kegel-Würfe
   3     7                1              1               1
   4    14                1              1               1
   5     3                1              1               1
   5    10                1              1               1
   5    13                1              1               1
```

Gerettet hat der **Fehlwurfzähler der Tafel** — ein zweiter, unabhängiger
Zeuge, der den Wert gleich mitliefert, weil ein Fehlwurf 0 Kegel hat.

## Die Lücke, die bleibt

Genau daran hängt es aber auch. Fiele in einer verschmolzenen Grünphase auch
nur ein Kegel, bekäme ihn still der Folgewurf zugeschlagen, und **nichts würde
es melden** — der Fehlwurfzähler springt dann nicht. Gerettet hat uns eine
Eigenschaft des Fehlwurfs, nicht eine Eigenschaft unserer Logik.

Zwei Nebenwirkungen, die schon jetzt sichtbar sind: Der nachgetragene Wurf
bekommt **keine Wurfnummer und keine Tafelsumme** (`None` in der Datenbank),
und der am Ende der langen Phase gebuchte Wurf bekommt die **Grundlinie vom
Anfang** der Phase — also von vor dem Fehlwurf.

## Nicht gebaut — der naheliegende Weg

Die Tafel-Wurfnummer wird ohnehin jeden Frame gelesen. Springt sie **während**
einer laufenden Grünphase, ist das ein eigenes, hartes Signal für „hier war
ein Wurf". Damit ließe sich der Wurf anlegen statt ihn vom Fehlwurfzähler
erraten zu lassen, und die Grundlinie ließe sich auf den Sprung neu setzen.

Das ist ein Vorschlag, keine Messung. Vor dem Bauen gehört gezählt, wie oft
die Wurfnummer innerhalb einer Grünphase springt und wie zuverlässig sie
dort gelesen wird.

## Lehre

**Eine Annahme, die in 1673 von 1678 Fällen stimmt, ist trotzdem eine
Annahme.** „Eine Grünphase = ein Wurf" steht nirgends als Prüfung; sie steckt
in der Form der Zustandsmaschine. Dass sie fünfmal nicht galt, hat nur deshalb
nichts gekostet, weil ein anderer Zeuge zufällig genau die fehlende Information
trug.


---

## Fall C — der vorhergesagte Schaden ist eingetreten (2026-10-06)

Oben steht unter „Die Lücke, die bleibt":

> *Fiele in einer verschmolzenen Grünphase auch nur ein Kegel, bekäme ihn
> still der Folgewurf zugeschlagen, und **nichts würde es melden**.*

Genau das ist am 1. Spieltag passiert, und zwar nicht mit einem Kegel,
sondern mit **allen neun**.

**Bahn 5, Spiel 17, Wurf 7.** Die amtliche Ergebnistafel sagt 201 für dieses
Spiel, wir sagten 194.

### Was die Grünspur zeigt

```
F286392   Gruen AUS  Score 53,6     <- Wurf 6 wird gebucht (7 Kegel)
F286570   Gruen AN
F286902   Score 58,9  UNKNOWN
F286950   Score 57,1  UNKNOWN       <- tiefster Punkt der ganzen Phase
F286968   Score 60,7  ON
F287402   Gruen AUS  Score 53,6     <- Wurf 8 wird gebucht
```

Eine einzige Grünphase über **832 Frames**, 33 Sekunden. Der Score musste
unter 52,5 fallen, um AUS zu werden; er kam bis 57,1. Das ist dieselbe
Totzone wie in Fall B — nur reicht sie hier nicht über einen Zyklus, sondern
schluckt den Zyklus ganz.

### Was die Lampenspur zeigt

```
F286390  an=[1,2,3,6,7,8,9]        Wurf 6, 7 Kegel
F286500  an=[]                     die Anlage stellt auf
F286750  an=[1,2,3,6]              WURF 7 faellt
F286775  an=[1..9]  \
F286790  an=[]       |
F286805  an=[1..9]   |  BLINKEN, Takt rund 30 Frames
F286820  an=[]       |  -> Alle Neune
F286835  an=[1..9]   |
F286890  an=[1..9]  /
F287005  an=[]                     die Anlage stellt auf
F287220  an=[1,2,3,6]              WURF 8 faellt
F287225  an=[1,2,3,6,7,8,9]        7 Kegel
F287450  an=[]
```

Zwei vollständige Wurfbilder in einer Grünphase, dazwischen geräumt.

### Die Rechnung geht exakt auf

```
Wurf 7 = 9 (Alle Neune)   nicht gebucht          -9
Wurf 8 = 7                gebucht als 9          +2
                                                 --
                                                 -7
194 + 7 = 201 = amtlich
```

Die +2 bei Wurf 8 sind die zweite Hälfte des Schadens und waren in der
Vorhersage noch nicht enthalten: **Die Blinkbilder von Wurf 7 liegen im
Ergebnisfenster von Wurf 8.** Der Filter aus BUG-036 (`ist_fehlercode`)
greift hier nicht — der entfernt Blinken NACH dem Grün-AUS, dieses liegt
mitten in der Phase.

Dass die Kegelziffer `9` zeigte und nicht `7`, steht im GIF bei Frame 287030.
Dieselbe Tafel liest unser Ziffernleser an anderer Stelle desselben Spiels
fünfmal als `7`, wo neun Lampen brennen — das ist BUG-009 (die 9 ohne unteren
Balken) und dort haben die Lampen recht; die Tafelsumme beweist es
(173 vor Wurf 26, 192 vor Wurf 29, Wurf 26 = 1, bleibt 18 für zwei Würfe).

**Beleg:** `debug/fehlwuerfe/streit_bahn5_f286300-287500.gif` (157 Bilder,
Frame für Frame mit Grünscore, allen neun Lampen und allen Ziffernfeldern).

## Woran man es erkennt — gebaut und gemessen

`tools/finde_zwei_wuerfe_in_einer_gruenphase.py`

Blinken und ein zweiter Wurf sehen gleich aus: Licht, dunkel, Licht. Der
Unterschied ist die Pause — Blinken hat rund 30 Frames Takt, zwischen zwei
Würfen räumt die Anlage, stellt auf und der Spieler holt aus. Zusammengelegt
wird alles unter 60 Frames; gemeldet wird nur, was danach noch mindestens
120 Frames Dunkelheit übrig lässt.

Eine dritte Bedingung macht es erst brauchbar: Das erste Bild muss **nach**
dem Räumen entstanden sein. Steht es schon beim Grün-AN, ist es das
Nachleuchten des vorigen Wurfs. Ohne diese Bedingung kommt genau ein
Fehlalarm je Spieltag.

```
GEMESSEN ueber zwei volle Spieltage, 3359 Wuerfe:
   1. Spieltag   1 Fund    Bahn 5, F286570-287402   <- der echte Fall
   2. Spieltag   0 Funde
```

Kein Fehlalarm. Der Sprung der **Tafel-Wurfnummer** (6 → 8) ist in diesem
Fall ein zweiter, unabhängiger Zeuge und findet denselben einen Fall — aus
der Tafelsumme allein ließ sich der Wert aber nicht zurückrechnen, weil die
Summe an dieser Stelle nicht gelesen wurde.

## Was zu bauen wäre

Nicht gebaut, weil es an der Zustandsmaschine ansetzt und ein eigener Lauf
zur Absicherung gehört. Die Richtung ist nach dieser Messung klar:

1. **Ein zweites Kegelbild in derselben Grünphase schließt den vorigen Wurf
   ab.** Die Bedingungen oben sind gemessen und falschalarmfrei.
2. **Das Ergebnisfenster beginnt beim letzten Räumen, nicht beim Grün-AN.**
   Das allein hätte die +2 bei Wurf 8 verhindert, unabhängig davon, ob Wurf 7
   gerettet wird.

Punkt 2 ist der kleinere Eingriff und die größere Sicherheit: Er kann nichts
verlieren, nur Fremdes fernhalten.
