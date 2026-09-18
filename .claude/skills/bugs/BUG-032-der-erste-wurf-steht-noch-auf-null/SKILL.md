---
name: bug-032-der-erste-wurf-steht-noch-auf-null
description: >
  Verhindert, dass der erste Wurf eines neuen Spiels als "kein Wurf" verworfen
  wird. Laden bei Arbeit an `discard_zero_throw_number`, an Spielwechseln, am
  Nullzustand der Tafel -- und immer dann, wenn zwei Zeugen aus derselben
  Quelle stammen.
---

# BUG-032 — Der erste Wurf steht noch auf Null

| | |
|---|---|
| **Kategorie** | `COUNT` / Spielwechsel |
| **Gefunden** | 2026-09-18, beim Nachgehen der Grünzyklen ohne Wurfergebnis |
| **Schweregrad** | **niedrig** (1 von 1437 Würfen; der Spielstand bleibt danach dauerhaft um diesen Wurf falsch) |
| **Regressionstest** | noch offen |
| **GIF** | `debug/verlorene/streit_bahn5_f71033.gif` |

## Symptom

Bahn 5, Spiel 5 beginnt bei **Wurf 2**. Wurf 1 fehlt — als einziges von 54
Spielen des Spieltags:

```
F68873  W30  Spiel 4   Kegel 2   Zwischensumme 87     <- Spiel 4 zu Ende
                                                      <- Wurf 1 fehlt
F71521  W2   Spiel 5   Kegel 9   SummeTafel 6
```

Die Tafel weiss, was fehlt: `SummeTafel` beim Melden von Wurf 2 ist **6** --
sie hinkt einen Wurf hinterher (BUG-010), also hat Wurf 1 sechs Kegel gelegt.

Im Log:

```
Bahn 5: Anzeige steht bei Frame 71033 auf 000/0000
        (Wurfnummer 100% einig, Summe 100% einig)
        -- kein Wurf hat stattgefunden. Wird verworfen.
```

## Was das GIF zeigt

```
F69684  Gruen OFF   liegend []              Tafel  000 / 0 / 0000
F69754  GRUEN AN    liegend []              Tafel  000 / ? / 0000
F70941  Gruen AN    liegend [1,3,6,9]       Tafel  000 / 8 / 0000
F70953  Gruen AN    liegend [1,3,4,6,9]     Tafel  000 / 9 / 0000
F70965  Gruen AN    liegend [1,2,3,4,6,9]   Tafel  000 / 6 / 0000
F71031  GRUEN AUS   liegend [1,2,3,4,6,9]   Tafel  000 / 6 / 0000
```

**Sechs Kegel fallen sichtbar um, und die Kegelziffer zeigt 6.** Nur
Wurfnummer und Summe stehen weiter auf `000` und `0000`.

Drei Zeugen sagen übereinstimmend *sechs*: die Lampen (sechs liegen), die
Kegelziffer (`6`), und die Summe des nächsten Wurfs (`6`). Verworfen wurde
trotzdem.

## Ursache: zwei Zeugen, die beim ersten Wurf beide schweigen dürfen

Die Regel in `throw_analyzer.py` verlangt bewusst **zwei** Felder:

```python
if (self.cfg.scoring.discard_zero_throw_number
        and nummer_mehrheit == 0
        and nummer_einigkeit >= schwelle
        and summe_null):
```

Die Begründung im Code lautet: *„Beim Spielwechsel zeigt die Anlage '000 0000',
ein echter Wurf hat dagegen eine Summe über null. Damit müssten zwei getrennt
gelesene Felder gleichzeitig falsch sein."*

Das stimmt — **ausser bei genau einem Wurf im Spiel: dem ersten.** Dort ist
`000 / 0000` kein Lesefehler und kein Spielwechsel, sondern der korrekte
Anzeigezustand, solange die Anlage den Wurf noch nicht gebucht hat. Die
Verspätung ist dieselbe wie in BUG-010: Die Anlage trägt das Ergebnis erst
kurz vor dem nächsten Grün-AN ein.

Die zwei Zeugen sind also **nicht unabhängig von der Lage**: Beide schweigen
beim ersten Wurf aus demselben Grund. Das ist das Muster aus
[BUG-029](../BUG-029-drei-wege-die-alle-an-einer-ziffer-haengen/SKILL.md) --
Redundanz, die keine ist.

## Der dritte Zeuge wurde nie gefragt

Die Kegellampen. Sie hängen an keinem Ziffernfeld und an keiner Buchung der
Anlage: Was umfällt, fällt um.

**GEMESSEN über den ganzen Spieltagslauf (1437 Würfe), alle 18 Verwerfungen
dieser Regel gegen die Lampenspur:**

```
17 x  nichts gefallen (max 0 liegende Kegel im Zyklus)  -- zu Recht verworfen
 1 x  sechs Kegel gefallen (Bahn 5, F71033)             -- der verlorene Wurf
```

Die Lampen trennen die Fälle also **vollständig**. Eine Bedingung „nur
verwerfen, wenn nichts umgefallen ist" hätte an diesem Spieltag genau eine von
achtzehn Entscheidungen geändert — und zwar die eine falsche.

## Was zu tun wäre (noch nicht gebaut)

Die Regel um den dritten Zeugen ergänzen: Fiel im Zyklus etwas um, ist
`000/0000` kein Beleg für „kein Wurf", sondern ein noch nicht gebuchter erster
Wurf.

Nicht zu tun: die Regel abschalten. Sie greift 17 von 18 Mal richtig, und ihre
Vorgeschichte ist teuer — ohne sie wachsen zwei Sätze zu einem zusammen
(im Code dokumentiert an Bahn 4 F183107/F186293).

Ebenfalls nicht zu tun: die Summe als Zeugen streichen. Sie fängt die
systematische Fehllesung der `9` als `0` ab (Q16, gemessen 25 % an der
Einerstelle).

## Die Regel, die dieser Bug hinzufügt

BUG-029 hielt fest: *Zwei Wege, die dasselbe Ziffernfeld lesen, sind kein
Beleg.* BUG-032 schärft das:

**Zwei Zeugen aus verschiedenen Feldern können trotzdem abhängig sein — wenn
sie aus demselben Grund schweigen.** Wurfnummer und Summe sind getrennt
gelesen und trotzdem beide null, sobald die Anlage noch nicht gebucht hat.
Unabhängig ist erst ein Zeuge mit einem anderen *Mechanismus*: die Lampen.

Und, zum zweiten Mal an diesem Tag: Der Fehler stand nicht in den Zahlen,
sondern im Bild. Das GIF zeigt sechs fallende Kegel neben einer Anzeige, die
auf null steht — in der `wuerfe.csv` war von diesem Wurf gar nichts zu sehen,
denn er wurde nie geschrieben (P9).
