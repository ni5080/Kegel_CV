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
| **Schweregrad** | mittel (im Lauf kein Schaden, aber eine Lücke ohne Alarm) |
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
