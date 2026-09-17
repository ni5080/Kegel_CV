---
name: bug-028-zeichen-kommt-einen-wurf-zu-spaet
description: >
  Verhindert dauerhaft falsche Spielstände durch ein Signal, das je nach
  Zeitpunkt eine Stufe zu spät ankommt. Laden bei Arbeit am Spielwechsel, an
  Signalen mit Verzögerung ("gilt dem nächsten"), an Prüfungen, die in eigenem
  Takt neben einem Ereignisfenster laufen -- und immer dann, wenn ein Zustand
  sowohl INNERHALB als auch ZWISCHEN zwei Ereignissen auftreten kann.
---

# BUG-028 — Das Zeichen, das einen Wurf zu spät kommt

| | |
|---|---|
| **Kategorie** | `STATE` / Spielwechsel |
| **Gefunden** | 2026-09-17, vom Nutzer an seinem eigenen Lauf |
| **Schweregrad** | **hoch** (der Spielstand einer Bahn bleibt für ein ganzes Spiel falsch) |
| **Regressionstest** | `test_game_reset.py::TestWohinDasZeichenGeht` |

## Symptom

Nach einem Spieltag mit 477 Würfen lag der Punktestand auf jeder Bahn neben
der Tafel — teils über 30 Würfe hinweg mit **konstantem** Betrag. Der Nutzer
brach den Lauf ab: *„die Unterschiede waren zu groß"*.

Die Würfe selbst waren dabei in Ordnung. Lampen und Kegelziffer stimmten in
**358 von 360 Fällen (99,4 %)** überein.

## Die Spur

Der Restfehler `(LaufendeSumme − SummeTafel) − Kegel` ist null, wenn alles
stimmt (die Tafel zeigt zum Meldezeitpunkt den Stand VOR dem Wurf). Nach
Spielen gruppiert:

| Bahn | Spiel | erster gebuchter Wurf | Rest |
|---|---|---|---|
| 2 | 2 | Wurfnummer **2** | konstant −7 |
| 2 | 5 | Wurfnummer **2** | konstant −7 |
| 3 | 2 | Wurfnummer **2** | konstant −9 |
| 4 | 2 | Wurfnummer **2** | konstant −5 |
| 5 | 2, 4, 6 | Wurfnummer **2** | konstant −7 / −9 / −6 |
| alle übrigen | | Wurfnummer **1** | **±0** |

Der Nutzer hatte es vor der Messung gesehen: *„Es scheint mir aber auch bei
späteren Sätzen, dass jeweils immer der erste gefehlt hat."* Genau so ist es —
**jedes Spiel, das bei Wurfnummer 2 beginnt, hat seinen ersten Wurf verloren**,
und der Fehlbetrag ist dessen Kegelzahl.

## Ursache

`_pruefe_nullzustand` läuft in EIGENEM Takt, unabhängig vom Wurffenster — das
war eine frühere, richtige Korrektur (A4): Vorher entschied der Zufall, ob die
Anlage gerade während einer Grünpause zurücksetzte.

Damit kann der Nullzustand aber an zwei verschiedenen Zeitpunkten gesehen
werden, und das ist ein Unterschied:

```
im Wurffenster    Der laufende Wurf gehoert noch zum ALTEN Spiel.
                  Das Zeichen gilt dem naechsten.

dazwischen        Der letzte Wurf des alten Spiels ist laengst gebucht.
                  Der naechste Wurf ist bereits der ERSTE des neuen Spiels.
```

Beides ging in denselben Briefkasten (`_reset_seen`), und der wird von
`_reset_weiterreichen` um eine Stufe geschoben. Der zweite Fall kam dadurch
einen Wurf zu spät:

```
Wurf 30 (letzter von Spiel A)   Fenster zu, gebucht
Anlage setzt zurueck            _reset_seen = True   <- zwischen den Wuerfen
Wurf 1 von Spiel B              pending <- carry (False)  -> landet in Spiel A
Wurf 2 von Spiel B              pending <- carry (True)   -> Spiel B beginnt
```

Ob es auffiel, entschied der Wurfrhythmus — deshalb waren 18 von 25 Spielen
richtig und 7 falsch.

## Behebung

Das Zeichen geht in den Briefkasten, der zum Zeitpunkt passt: bei offenem
Fenster nach `_reset_seen` (eine Stufe Verzug), zwischen zwei Würfen direkt
nach `_reset_carry`. Die Logmeldung sagt jetzt mit, welcher Fall vorlag.

Neu ist `LaneProcessor.reset_unterwegs`: Wer nur wissen will, OB ein Wechsel
erkannt wurde, muss nicht wissen, in welchem der beiden Kästen er liegt.

## Was daraus zu lernen ist

**Eine Prüfung aus dem Ereignisfenster zu lösen, löst sie nicht aus der Zeit.**
Die frühere Korrektur war richtig — sie hat die Erkennung vom Zufall der
Grünphase befreit. Sie hat damit aber einen zweiten Zeitpunkt erzeugt, an dem
derselbe Zustand auftreten kann, und die Zustellung blieb auf den ersten
zugeschnitten. Wer eine Prüfung entkoppelt, muss jeden Zeitpunkt durchgehen,
an dem sie jetzt zuschlagen kann.

**Ein konstanter Fehler über ein ganzes Spiel zeigt auf den Startwert, nicht
auf die Messung.** Wäre eine Messung schuld, schwankte der Fehler. Diese eine
Unterscheidung führte hier direkt zur Ursache, nachdem die Suche zuvor bei den
Ziffern und den Lampen gesucht hatte — beide waren in Ordnung.

**Die Gegenprobe war blind dafür, und das ist ein Befund über sie selbst.** Sie
vergleicht DIFFERENZEN (Summe(N+1) − Summe(N)), und eine Differenz ist gegen
einen falschen Startwert immun. Sie meldete 76,9 % „einig", während der
Punktestand auf jeder Bahn danebenlag. Ein Prüfwerkzeug, das nur Differenzen
sieht, kann einen Versatz nicht finden — dafür braucht es den absoluten
Vergleich `LaufendeSumme` gegen `SummeTafel`.

## Nachgemessen

Die erste Fassung dieses Skills sagte, die Wirkung sei nicht nachmessbar, weil
der Lauf gegen einen Livestream lief. **Das war falsch.** Die Stream-URL liefert
von vorn, nicht vom Live-Rand; ein zweiter Lauf bucht dieselben Würfe. Über die
ersten 98 Würfe, alle vier Bahnen:

| | Rest = 0 (richtig) | Spiele mit konstantem Fehlbetrag |
|---|---|---|
| vorher | 22 von 96 (22,9 %) | 4 (−7, −9, −5, −7) |
| **nachher** | **96 von 96 (100,0 %)** | **0** |

Die Lehre daneben: Bevor man „nicht wiederholbar" in eine Doku schreibt, lohnt
ein zweiter Lauf. Ich hatte es aus der Art der Quelle geschlossen statt es zu
probieren.

## Offen

Der Nutzer hat im selben Lauf beobachtet, dass auf Bahn 2 der Lampenkranz
leuchtete, während die Anzeige zwei Lampen (Kegel 5 und 7) als aus führte.
Über 226.404 Lampenmessungen gab es genau EINEN Fall, in dem eine Lampe hell
genug war und nicht als AN galt — ein Schwellenproblem ist es also nicht.
Bleibt die Lage der beiden ROIs. **Noch nicht untersucht**; dafür wird der
Frame dieses Moments gebraucht.
