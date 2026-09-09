---
name: bug-007-kegellampen-blinken
description: >
  Verhindert DETECT-Bug: Die Kegellampen der FUNK-Anlage BLINKEN. Ein einzelner
  Messzeitpunkt trifft daher zufaellig eine Dunkelphase und meldet 0 gefallene
  Kegel. Laden bei Arbeit an Lampenerkennung, Wurfergebnis, Messzeitpunkten,
  Frame-Sampling oder wenn eine Messung "manchmal" falsch ist, obwohl das Signal
  im Standbild eindeutig aussieht.
---

# BUG-007 — Die Kegellampen blinken

> **Nachtrag zur Ursache (Nutzer, 2026-08-25):** Das Blinken ist kein
> allgemeines Verhalten der Anlage, sondern der **Spezialeffekt für „alle
> Neune"** — fallen alle neun Kegel, blinken die neun Lampen. Die hier
> beschriebene Abhilfe (über das Fenster aggregieren, je Lampe das Maximum)
> bleibt richtig und notwendig; nur die Deutung war zu weit gefasst. Dass in
> frühen Messungen „8 Lampen" im Wechsel mit 0 erschienen, dürfte an
> Übergangsframes liegen, in denen eine Lampe bereits unter der Schwelle lag.

| | |
|---|---|
| **Kategorie** | `DETECT` |
| **Gefunden** | 2026-08-25, beim Nachprüfen widersprüchlicher Würfe auf Nutzerwunsch |
| **Schweregrad** | **hoch** — falsche Kegelzahlen und dadurch falsche Summen |
| **Regressionstest** | `tests/unit/test_pipeline_aggregation.py` |

## Symptom

Würfe wurden als `EMPTY` (0 Kegel) gebucht, obwohl die Anzeigetafel im selben
Moment klar `006 8 0039` zeigte — also 8 gefallene Kegel. Betroffen waren 4 von
51 Würfen; sie verfälschten zusätzlich die laufende Summe.

## Ursache

**Die Kegellampen der Anlage blinken.** Das war nicht erwartet und ist in keinem
Standbild zu erkennen — man sieht es erst in der Zeitreihe:

```
Frame 5800:  8 Lampen   Ziffer 8
Frame 5812:  0 Lampen   Ziffer 8     <- Dunkelphase
Frame 5824:  8 Lampen   Ziffer 8
Frame 5840:  0 Lampen   Ziffer 8
Frame 5844:  0 Lampen   Ziffer 8     <- HIER wurde gemessen
Frame 5852:  8 Lampen   Ziffer 8
Frame 5868:  0 Lampen   Ziffer 8
```

Die Ziffer bleibt konstant, die Lampen springen im Sekundentakt. Der
Messzeitpunkt (`GREEN_OFF`) trifft die Hell- oder Dunkelphase rein zufällig.

Warum das trügerisch plausibel aussah: Die Lampenerkennung selbst war korrekt und
gemessen zuverlässig (Trennschärfe 7,66, siehe BUG-006). Sie maß in diesem
Moment tatsächlich null leuchtende Lampen. Der Fehler lag nicht im *Wie*,
sondern im *Wann*.

## Falsch

```python
# Ein Frame entscheidet ueber das Wurfergebnis
if event.event is EventType.GREEN_OFF:
    self._result_pins = self._read_pin_lamps(frame)
```

## Richtig

Über alle Frames des Ereignisses aggregieren — eine Lampe gilt als gefallen,
wenn sie in **mindestens einem** Frame geleuchtet hat:

```python
for i in range(anzahl):
    kandidaten = [m.lamps[i] for m in messungen]
    an = [k for k in kandidaten if k.is_on]
    zusammen.append(max(an, key=lambda k: k.confidence) if an else ...)
```

Die Asymmetrie ist der Kern: **Eine Lampe kann während des Blinkens fälschlich
dunkel erscheinen, aber nicht fälschlich leuchten.** Deshalb ist das Maximum
über die Frames die richtige Zusammenfassung — nicht der Mittelwert und nicht
die Mehrheit.

Wirkung: `EMPTY` von 8 auf 4, `VALID` von 32 auf 39 (bei 51 Würfen).

## Regel für die Zukunft

> Bevor ein Messwert aus **einem** Frame ein Ergebnis bestimmt: prüfen, ob die
> Quelle über die Zeit konstant ist. Eine Zeitreihe über 100 Frames kostet
> Minuten und deckt auf, was jedes Standbild verschweigt.

Und beim Zusammenfassen: **erst überlegen, in welche Richtung der Fehler geht.**
Ist er einseitig (hier: nur „fälschlich aus"), ist das Extremum die richtige
Zusammenfassung, nicht der Durchschnitt.

Zum Auffinden: Der Widerspruch zweier Quellen war das einzige Warnsignal — die
Lampen sagten 0, die Ziffer 8. Ohne diese Redundanz wäre der Fehler unentdeckt
geblieben und hätte stillschweigend falsche Summen erzeugt. Genau dafür existiert
sie (Prinzip: bei Widerspruch nie eine Quelle wegentscheiden).

## Nachtrag: die Dunkelphase ist länger als das Messfenster

Die erste Fassung des Fixes aggregierte über die vier Sample-Frames — eine Spanne
von rund zehn Frames. Das reichte nicht. **Frame für Frame gemessen** über zwei
Bahnen:

```
Bahn 2   000000000099999999999999900000000000000199999999999999000000000000011999...
Bahn 5   001199999999999990000000000000009999999999999999999999999999999999999999...

Periode 28-30 Frames | Hellphasen 15 | Dunkelphasen 13-15
```

**Die Dunkelphase ist mit bis zu 15 Frames länger als das Messfenster war.** Vier
Frames innerhalb von zehn können daher vollständig im Dunkeln liegen — genau das
geschah bei fünf weiteren Würfen, die zunächst als eigenes Phänomen erschienen
(„Ziffer 9 bei dunklen Lampen", siehe Q8 in `docs/OPEN_QUESTIONS.md`).

Seitdem werden die Lampen über das **gesamte** Fenster zwischen `GREEN_OFF` und
dem nächsten `GREEN_ON` gesammelt (`LaneProcessor._result_samples`) — die
Messungen dafür laufen ohnehin für die Live-Anzeige.

Die Lehre: **Ein Aggregationsfenster muss länger sein als die Störung, gegen die
es schützt — und dafür muss die Störung gemessen sein.** Die erste Fassung war
richtig gedacht und zu kurz bemessen, weil die Periode geschätzt statt gemessen
war.

## Wo gilt diese Regel noch?

- [x] `analysis/pipeline.py::_aggregate_pins` — gefixt
- [ ] **Grüne Lampe:** Blinkt sie ebenfalls? Die Hysterese mit
      `min_stable_frames=3` fängt kurzes Flackern ab, aber eine längere
      Blinkphase wäre ein Problem. Noch nicht über eine Zeitreihe geprüft.
- [ ] **Statuslampen** (rot/gelb, Q7): vor einer Auswertung erst die Zeitreihe
      ansehen.
- [ ] Ziffernfelder: Dort ist das Gegenteil belegt — die Ziffer blieb konstant,
      während die Lampen blinkten. Die zeitliche Aggregation ist trotzdem
      sinnvoll (Flackern, siehe Q4).
