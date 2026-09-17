---
name: bug-029-drei-wege-die-alle-an-einer-ziffer-haengen
description: >
  Verhindert übersprungene Spielgrenzen auf Bahnen mit schlecht lesbarem
  Wurfnummernfeld. Laden bei Arbeit am Spielwechsel, an Redundanz zwischen
  Erkennungswegen -- und immer dann, wenn mehrere "unabhängige" Prüfungen in
  Wahrheit an derselben Messung hängen.
---

# BUG-029 — Zwei Wege, die beide an derselben Ziffer hingen

| | |
|---|---|
| **Kategorie** | `STATE` / Spielwechsel |
| **Gefunden** | 2026-09-17, beim Nachgehen eines Nutzerbefunds |
| **Schweregrad** | **mittel** (CSV und Anzeige; die Datenbank ist nicht betroffen, siehe BUG-028) |
| **Regressionstest** | `test_game_reset.py` |

## Symptom

Bahn 5 schleppte über 16 Würfe einen Fehlbetrag von −93 bis −100 mit. Anders
als bei BUG-028 war das kein einzelner verlorener Wurf, sondern eine ganze
übersprungene Spielgrenze.

## Ursache: zwei Wege, eine gemeinsame Schwäche

Es gab zwei Wege zum Spielwechsel, und beide lasen dasselbe Feld:

1. **Nullzustand** — die Wurfnummer muss dreimal `000` zeigen
   (`game_reset_number_only: true`).
2. **Rückfall der Wurfnummer** — von über 30 auf unter 5.

Auf einer Bahn, deren Wurfnummernfeld schlecht sitzt, versagen sie
**gemeinsam**. GEMESSEN auf Bahn 5 (Stream 2026-09-17):

```
F49518  Tafel-Wurfnummer 90   (Fehllesung von 30)
F51552  Tafel-Wurfnummer  -   unlesbar -> "fortgezaehlt auf 31", landet im alten Spiel
F52052  Tafel-Wurfnummer  2   Rueckfall 90 -> 2  =>  neues Spiel, beginnend bei Wurf 2
```

Über 560 Frames vor dem Wechsel wurde die Wurfnummer **kein einziges Mal** als
`000` gelesen (gemessene Werte: 010, 011, 012, einmal 002). Die
Nullzustandserkennung konnte gar nicht greifen.

## Der dritte Zeuge, der offen dalag

Bei F51552 stand die **Summe der Tafel auf 0**. Die Tafel trägt verspätet nach:
Zum Meldezeitpunkt steht dort der Stand VOR diesem Wurf. Eine gelesene Null
heißt also, dass die Anlage vor ihm zurückgesetzt hat — **unabhängig von der
Wurfnummer**.

GEMESSEN am selben Lauf, 315 Würfe: Genau **12 Würfe** hatten `SummeTafel == 0`,
und **11 davon waren der erste Wurf ihres Spiels**. Der zwölfte war der
Fehlerfall von Bahn 5 — also zwölf von zwölf, wenn man ihn als das zählt, was
er hätte sein sollen. **Kein einziger Wurf mitten im Spiel zeigte eine Null.**

## Behebung

`scoring.game_reset_by_zero_total`: Ein Wurf, bei dem die Tafel die Summe 0
zeigt, beginnt ein neues Spiel. Nachgemessen am selben Übergang:

```
vorher   Spiel 2 Wurf 31  F51552  Lauf 203  Tafel 0     -> altes Spiel
         Spiel 3 Wurf  2  F52052  Lauf   9  Tafel 9     Rest -9

nachher  Spiel 2 Wurf  1  F51552  Lauf   9  Tafel 0     Rest +0
         Spiel 2 Wurf  2  F52052  Lauf  18  Tafel 9     Rest +0
```

## Was daraus zu lernen ist

**Redundanz zählt nur, wenn die Quellen wirklich getrennt sind.** Zwei Wege zum
Spielwechsel sahen nach Absicherung aus und waren keine: Beide lasen dasselbe
Ziffernfeld. Wo eine Bahn dieses Feld schlecht zeigt, fallen beide zugleich
aus. Bei jeder „zweiten Prüfung" gehört die Frage gestellt, welche MESSUNG sie
benutzt — nicht, welche Regel.

**Die Summe war die ganze Zeit da.** Sie ist das andere Feld, sie war lesbar,
und ihre Null ist eindeutig. Gebraucht wurde kein neues Verfahren, nur der
Blick auf eine Quelle, die ohnehin schon mitgeschrieben wurde.

## Offen

Die Wurzel bleibt: **Bahn 5s Wurfnummernfeld ist schlecht lesbar.** Der dritte
Zeuge fängt die Folge ab, nicht die Ursache. Mit der Ziffernlupe
(`gui/ziffern_lupe.py`) ließe sich der Rahmen nachziehen.
