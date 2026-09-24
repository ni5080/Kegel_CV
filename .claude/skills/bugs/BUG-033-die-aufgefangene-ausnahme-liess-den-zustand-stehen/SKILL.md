---
name: bug-033-die-aufgefangene-ausnahme-liess-den-zustand-stehen
description: >
  Verhindert, dass eine von P8 aufgefangene Ausnahme halbfertigen Zustand
  hinterlässt. Laden bei Arbeit an der GREEN_OFF-Behandlung, an
  `_result_samples`, an `aggregate_pin_readings` -- und immer dann, wenn in
  einem Zweig, der Zustand zurücksetzt, eine neue Rechnung ergänzt wird.
---

# BUG-033 — Die aufgefangene Ausnahme ließ den Zustand stehen

| | |
|---|---|
| **Kategorie** | `ANALYSE` / Zustandsführung |
| **Gefunden** | 2026-09-24, nach dem Spieltag vom 2026-09-19 |
| **Schweregrad** | **kritisch** (jeder zweite Wurf falsch, alle vier Bahnen, ganzer Spieltag) |
| **Regressionstest** | `test_grundlinie_aus_spur.py::TestGrundlinieAusGruppen::test_nimmt_auch_eine_deque` |
| **Verursacht durch** | die unbelegte Änderung zu BUG-031, die uneingecheckt im Arbeitsbaum lag |

## Symptom

Der Nutzer nach dem Spieltag: *„unser Tool hat leider permanente Abweichungen
gemessen... mitte-ende des ersten Satzes habe ich mal reingeschaut und gesehen,
dass wir konsequent über alle Bahnen zu hoch waren."*

Gemessen an `wuerfe.csv` des Laufs vom 2026-09-19, 1694 Würfe:

```
Bahn Wuerfe beide da        einig  uneinig Ziffer stumm
   2    424      420   208  49.5 %      212            4
   3    426      354   207  58.5 %      147           72
   4    422       71    22  31.0 %       49          351
   5    422      403   183  45.4 %      220           19
```

**628 von 1248 Würfen mit lesbarer Ziffer falsch. 46 von 46 Spielenden zu
hoch, um +20 bis +55.**

## Was die Metadaten sagten — und was sie widerlegten

Der Nutzer hatte zwei Vermutungen, und beide waren falsifizierbar, ohne ein
einziges Bild anzusehen (`tools/abweichungsmuster.py`):

*„die meisten Abweichungen beginnen ab Wurf 15 → dann wird vermutlich Räumen
nicht mehr erkannt"* — nein. Die Quote ist über alle 15 Würfe im Zyklus flach
(44 bis 57 %), über alle Spiele flach, über alle vier Bahnen flach.

*„konsequent wenn das Board eine 2 meldet, melden wir eine 9"* — umgekehrt:

```
Tafel |    0    1    2    3    4    5    6    7    8    9
    1 |    .   32   19    5    .    .    .    .    1    7
    2 |    .    .   68   12    1    .    .    .    .    1
    5 |    .    .    .    .    .    .    .    .    .   37
    6 |    .    .    .    .    .    .    1    .    .   65
    7 |    .    .    .    .    .    .    .    1    .  240
    8 |    .    .    .    .    .    .    .    .    1  176
```

**Alles ab 5 wird zu 9.** Gerade die kleinen Zahlen stimmen — und zwar aus
Versehen: Beim Abräumen ziehen wir eine Grundlinie von 7 oder 8 ab, und
9 − 7 = 2 trifft dann zufällig.

## Der Beweis aus dem Video

Bahn 2, Wurf gebucht bei Frame 14110, Tafel zeigt 7. Die ganze Grünphase
(F13150–14120), 195 Messungen alle 5 Frames, Helligkeit je Kegellampe:

```
  F13150 ... F14030    alle neun dunkel (146-162)      0 hell
  F14035              1,2,3,4,6,8 hell                 6 hell
  F14040 ... F14120   1,2,3,4,6,8,9 hell               7 hell
                      Kegel 5: 161-164   Kegel 7: 157-160
```

**Kegel 5 und 7 sind in der gesamten Grünphase nie hell.** Die Lampen zeigen
durchgehend 7, die Tafel auch — gebucht wurden 9.

Damit war klar: Die zwei zusätzlichen Kegel stammen aus keiner Messung. Sie
stammen aus Zustand, der stehen geblieben ist.

## Ursache

```python
aus_spur = grundlinie_aus_spur(self._grundlinien_spur, gruppe)
#                              ^^^^^^^^^^^^^^^^^^^^^^ eine deque
...
    zusammen = aggregate_pin_readings(list(messungen[i:i + gruppe]))
#                                          ^^^^^^^^^^^^^^^^^^^^^^ Schnitt
```

Eine `deque` lässt sich nicht schneiden:

```
TypeError: sequence index must be integer, not 'slice'
```

Das fliegt bei **jedem Grün-AUS, auf jeder Bahn**. Und der Aufruf stand VOR
dieser Zeile:

```python
self._result_samples = list(self._green_phase_samples)
```

P8 fängt die Ausnahme ab — die Analyse läuft weiter, genau wie vorgesehen.
Aber die Ergebnisliste wird nie zurückgesetzt. Sie sammelt Zyklus um Zyklus
weiter, und darin steckt das Räumbild des Vorgängers mit allen neun Lampen.
`aggregate_pin_readings` vereinigt — also neun.

**Die Prämisse war nicht das Problem.** Es gab keine fälschlich leuchtende
Lampe. Die Regel „eine Lampe kann fälschlich dunkel erscheinen, nie fälschlich
leuchten" ist wegen des Blinkens richtig und bleibt unangetastet. Falsch war
eine Liste, die stehen blieb.

## Reparatur

1. **Die Folge wird einmal materialisiert**, dann geschnitten. Die Funktion
   nimmt jetzt jede `Sequence`, auch eine `deque`.
2. **Reihenfolge: erst die Pflicht, dann die Kür.** Alles, was den nächsten
   Wurf sauber beginnen lässt (`_result_samples`, `_late_samples`,
   `_grundlinien_spur`), steht jetzt VOR jeder abgeleiteten Rechnung. Fällt die
   Kür aus, ist der Zustand trotzdem heil.
3. **Regressionstest** mit einer echten `deque` — der Typ war das Einzige, was
   im Unittest anders war als im Betrieb.

## Die Regeln, die dieser Bug hinzufügt

**Eine aufgefangene Ausnahme heißt nicht, dass der Zustand heil ist.** P8
(„Fehler beenden die Analyse nicht") schützt den *Lauf*. Es schützt nicht die
*Invarianten* des Objekts, in dem der Fehler passierte. Wer in einem Zweig, der
Zustand zurücksetzt, eine neue Rechnung ergänzt, verschiebt damit möglicherweise
alles Folgende hinter eine mögliche Ausnahme. Reihenfolge ist dort kein Stil,
sondern Schutz.

**Der Unittest lief mit einer Liste, der Betrieb mit einer `deque`.** Elf Tests
waren grün, und keiner hat den Aufruf so gemacht, wie ihn der Aufrufer macht.
Dieselbe Lücke wie in BUG-023: Wer den Rechenkern
testet, hat nicht getestet, dass ihn jemand richtig aufruft.

**Eine Spur, die das Entscheidende wegwirft, beweist nichts.** Die
`lampenspur.csv` schrieb nur jeden 25. Frame; die Messungen der Grünphase
(alle 5 Frames) fielen heraus. In **622 von 628 Streitfällen** zeigte die Spur
den gebuchten Stand nie — der Widerspruch war aus der Datei allein nicht
aufzulösen. Seit dem 2026-09-24 gilt der Takt nur noch für die Anzeige; alles
Ergebnisrelevante wird immer geschrieben, mit der Spalte `Anlass`.

## Und eine Lehre, die nicht im Code steht

Die Änderung lag seit dem 2026-09-18 **uneingecheckt** im Arbeitsbaum. Ich hatte
sie selbst als unbelegt bezeichnet und angekündigt, sie vor dem nächsten Lauf
zurückzubauen — und es dann nicht getan. Der Nutzer ist damit in einen echten
Spieltag gegangen.

Ein Arbeitsbaum ist kein Zwischenlager. Was nicht getragen hat, gehört
zurückgebaut, bevor jemand anderes damit arbeitet.
