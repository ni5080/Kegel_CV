---
name: bug-019-verworfener-spielwechsel-verschiebt-die-kette
description: >
  Verhindert COUNT-Bug: Ein verworfener Gruenzyklus stellt die alte
  Wurfnummer wieder her -- auch wenn im selben Aufruf ein Spielwechsel
  gebucht wurde. Der neue Satz beginnt dann bei 31 statt bei 1. Laden bei
  Arbeit an Wurfnummer-Aufloesung, Spielwechsel-Erkennung, Verwerfungs-
  Filtern oder Rollback-Logik -- Stichworte: Spielwechsel, start_new_game,
  Wurfnummer, verworfen, Kette, _last_throw_number.
---

# BUG-019 — Verworfener Spielwechsel-Zyklus verschiebt die Wurfnummernkette

| | |
|---|---|
| **Kategorie** | `COUNT` |
| **Gefunden** | 2026-09-03, voller Spieltag (`lauf_2026-09-03_16-51-04`) |
| **Schweregrad** | **hoch** (5 von 64 Spielen, je 30 Wuerfe mit falscher Nummer) |
| **Regressionstest** | `test_throw_analyzer.py::TestVerworfenerSpielwechselVerschiebtDieKette` |

## Symptom

Der Nutzer meldete an EINEM Wurf: "Bahn 4 Wurfnr. 60? Spiel 11 ist eigentlich
Wurfnr. 30 ist aber ein Leerwurf, also theoretisch korrekt, aber die Wurfnr.
stimmt nicht."

Der Einzelfall war die Spitze eines systematischen Versatzes. GEMESSEN ueber
alle Bahnen -- Spiele, deren erste Wurfnummer nicht 1 ist:

| Bahn | betroffen | Spiele |
|---|---|---|
| 2 | 1 von 16 | Spiel 2: 2-20 |
| 3 | 0 von 16 | — |
| 4 | 3 von 16 | Spiel 4: **31-60**, Spiel 5: **61-90**, Spiel 11: **31-60** |
| 5 | 1 von 16 | Spiel 2: 2-22 |

Die drei Bahn-4-Faelle zeigen das volle Muster: Ein kompletter Satz traegt
durchgehend um 30 (bzw. 60) zu hohe Wurfnummern. Weil `Zyklus` und
`WurfImZyklus` aus der Wurfnummer abgeleitet werden, sitzen auch die
15er-Zwischensummen an der falschen Stelle.

## Ursache (5 Warum)

1. **Symptom:** Spiel 11 traegt Wurfnummern 31-60 statt 1-30.
2. **Warum:** Der erste Wurf des neuen Satzes bekam die Nummer 31.
3. **Warum:** Seine Tafel-Wurfnummer war nicht lesbar, und
   `_resolve_throw_number` zaehlt dann fort:
   `(self._last_throw_number or self.score.last_throw_number) + 1`.
   `_last_throw_number` stand auf **30**.
4. **Warum stand dort 30, obwohl `start_new_game()` lief?** Der Zyklus, in dem
   der Spielwechsel ankam, wurde von `discard_zero_without_digit` verworfen
   (voellig richtig -- es ist das Zuruecksetzen der Anlage, kein Wurf). Beim
   Verwerfen stellt der Filter die Kette wieder her:
   `self._last_throw_number = wurfnummer_vorher` -> 30.
5. **Warum ist das falsch?** Weil im selben Aufruf `_resolve_throw_number`
   BEREITS `start_new_game()` ausgefuehrt hatte. Der gesicherte Stand gehoert
   damit zum ALTEN Spiel -- und wird auf ein NEUES angewandt.

**Die eigentliche Ursache:** Eine Rollback-Massnahme (Kette wiederherstellen)
und eine nicht rollbare Zustandsaenderung (`start_new_game()`) im selben
Aufruf, ohne dass die eine von der anderen weiss.

**Beleg aus dem Log** -- kaputt und heil unterscheiden sich um genau eine
Zeile:

```
kaputt (Spiel 3 -> 4):
  Bahn 4: Anzeige stand auf 000/0000 -- voriges Spiel endete mit 195 Kegeln
  Bahn 4: Gruenzyklus bei Frame 50619 ... Wird verworfen.      <-- diese Zeile
  Bahn 4: Wurf 31 erkannt -- 7 Kegel, Gesamt 7, VALID

heil (Spiel 5 -> 6):
  Bahn 4: Anzeige stand auf 000/0000 -- voriges Spiel endete mit 219 Kegeln
  Bahn 4: Wurf 1 erkannt -- 9 Kegel, Gesamt 9, VALID
```

## Falsch

```python
# In jedem Verwerfungs-Zweig, fuenfmal im Analyzer:
self._last_throw_number = wurfnummer_vorher
# -- richtig fuer eine Stoerung mitten im Spiel,
#    falsch, wenn derselbe Aufruf einen Spielwechsel gebucht hat.
```

## Richtig

```python
# In analyze(), um den Aufruf herum:
spiele_vorher = len(self.score.game_totals)
number = self._resolve_throw_number(throw_number, checks, decisions, display_reset)
spielwechsel_gebucht = len(self.score.game_totals) > spiele_vorher

# In jedem Verwerfungs-Zweig:
self._kette_wiederherstellen(wurfnummer_vorher, spielwechsel_gebucht)

def _kette_wiederherstellen(self, wurfnummer_vorher, spielwechsel_gebucht):
    self._last_throw_number = 0 if spielwechsel_gebucht else wurfnummer_vorher
```

`len(self.score.game_totals)` als Kriterium, weil das BEIDE Spielwechsel-Pfade
erfasst (Anzeige auf 000/0000 und Ruecksprung der Wurfnummer) und kein
zusaetzliches Zustandsfeld braucht, das kuenftig vergessen werden koennte.

## Regel für die Zukunft

> Wenn eine Methode Zustand aendert und der Aufrufer sie danach verwerfen darf,
> muss der Aufrufer wissen, WAS geaendert wurde -- ein pauschales
> "Vorher-Stand wiederherstellen" ist nur richtig, solange kein anderer,
> nicht rollbarer Schritt dazwischenlag.

## Was der Fix NICHT behebt

Die Ziffern-Fehllesung, die den Fall sichtbar machte, besteht weiter:
`_wurfnummer_lesen()` las an F202870 eine **20**, wo die Tafel **30** zeigte
(bekanntes Muster "Segment faellt weg", 3 -> 2). Sie faellt nach dem Fix nur
nicht mehr auf: Mit korrekter Kette steht `last` dann auf 29, und der
Fallback `last + 1` liefert zufaellig die richtige 30.

**Warum dieser Pfad anfaelliger ist als der Normalfall:** `_wurfnummer_lesen()`
liest fuer Fehlwurf-Ereignisse bewusst nur EINEN Frame, waehrend der
Gruenzyklus-Pfad ueber 10 Frames aggregiert (`FieldAggregator`). Bewusst so
gebaut (Fehlwuerfe sind selten, drei Ziffernstellen alle zehn Frames waeren
teuer) -- aber damit ist dieser Pfad die einzige Stelle, an der eine einzelne
Fehllesung ungeprueft durchschlaegt. Siehe `docs/OPEN_QUESTIONS.md` (Q15).

## Wo gilt diese Regel noch?

- [x] `analyze_zero_throw` geprueft: ruft `_resolve_throw_number` auf, hat aber
      keinen Verwerfungs-Pfad danach -- nicht betroffen.
- [x] `_throws_since_game_change = 0` beim Spielwechsel geprueft: Wird bewusst
      NICHT zurueckgenommen, denn der Spielwechsel hat stattgefunden. Nur die
      Wurfnummernkette war falsch behandelt.
- [ ] `sinks/` und `debug/`: Ob dort ein bereits versandter/geschriebener Wurf
      nachtraeglich verworfen werden kann, ist nicht geprueft -- bisher kein
      Beleg fuer einen Fall.
