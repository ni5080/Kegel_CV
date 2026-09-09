---
name: bug-017-verdeckung-im-fenster-gilt-als-leerer-wurf
description: >
  Verhindert DETECT-Bug: Eine Verdeckung MITTEN in einem Sammelfenster
  (GREEN_OFF bis GREEN_ON) wird als "0 Kegel, EMPTY" gebucht, obwohl die
  Kamera schlicht nichts gesehen hat. Laden bei Arbeit an der
  Verdeckungsbremse, an Gruenzyklus-Erkennung oder an Nullwurf-Filtern --
  Stichworte: Verdeckung, Occlusion, Person vor der Tafel, Gruen-Score,
  Fenster, Nullwurf.
---

# BUG-017 — Verdeckung mitten im Fenster gilt als leerer Wurf

| | |
|---|---|
| **Kategorie** | `DETECT` |
| **Gefunden** | 2026-09-03, voller Spieltag (`lauf_2026-09-03_16-51-04`) |
| **Schweregrad** | mittel (3 von 1686 Wuerfen betroffen, aber ohne Fix nicht erkennbar) |
| **Regressionstest** | `test_throw_analyzer.py::TestVerdeckungImFenster` |

## Symptom

Drei Wuerfe wurden als "0 Kegel, EMPTY" gebucht, obwohl der Nutzer per GIF
bestaetigte: "Person im Bild, Score = 0 -- das sollte gar nicht als
Gruenzyklus gelten." Alle drei (Bahn5 F15569, Bahn5 F16256, Bahn2 F265724)
zeigten im Log exakt dasselbe Muster:

```
Bahn 5: Tafel ab Frame 15532 verdeckt (Gruen-Score 0.0) -- Auswertung ausgesetzt
Bahn 5: Tafel war 37 Frames verdeckt, ab Frame 15568 wieder sichtbar
Bahn 5: Wurf 3 erkannt -- 0 Kegel [], Gesamt 6, EMPTY (0.45)
```

Die Verdeckungsbremse (`_occlusion_frames >= occlusion_min_frames`) hatte
schon EXISTIERT und schon EINMAL zwei Phantomwuerfe verhindert (siehe
Kommentar in `lane_processor.py` zu F3228/F43514) -- aber nur, wenn die
Verdeckung das GANZE Fenster verschluckte. Endet die Verdeckung GENAU beim
Schliessen des Fensters (Person tritt aus dem Bild, GREEN_ON wird erkannt),
schliesst das Fenster trotzdem "normal" -- nur eben ohne dass irgendetwas
Sinnvolles gemessen wurde.

## Ursache

Die Verdeckungsbremse ist eine reine EINGABE-Bremse: Sie friert waehrend der
Verdeckung Zustandsmaschine, Lampenmessung und Ziffernlesung ein. Sie
hinterlaesst aber keine Spur DANACH -- wenn das Fenster kurz nach dem Ende
der Verdeckung abgeschlossen wird, sieht der Analyzer nur ein ganz normales,
vollstaendiges (`lamps_complete=True`) Ergebnis mit 0 Kegeln. Es gibt nichts,
was diesen Wurf von einem echten Leerwurf unterscheidet -- ausser dem Wissen,
DASS eine Verdeckung stattfand, und das ging beim Zuruecksetzen von
`_occlusion_frames` verloren.

## Wie von BUG-018 (Warmwerf-Sperrzyklus) getrennt

Beide Bugs erzeugen "0 Kegel, keine Tafelziffer, kein Fehlwurfzaehler". Die
Unterscheidung gelang nur durch Messung (Nutzerhinweis: "muss aber gemessen
werden") -- `tools/messe_gruenscore_um_frame.py` zieht den rohen Gruen-Score
framegenau:

| Fall | Minimum Gruen-Score |
|---|---|
| Bahn5 F15569 (Verdeckung) | **0.00** |
| Bahn5 F16256 (Verdeckung) | **0.00** |
| Bahn2 F265724 (Verdeckung) | **0.00** |
| Bahn4 F126593 (Sperrzyklus) | 26.25 |
| Bahn3 F218448 (Sperrzyklus) | 29.17 |
| Bahn4 F218644 (Sperrzyklus) | 26.25 |
| Bahn5 F220170 (Sperrzyklus) | 17.78 |

Eine echte Verdeckung faellt auf EXAKT 0 (die Kamera sieht buchstaeblich
nichts mehr). Der Sperrzyklus ist kein Verdeckungsphaenomen -- der
Gruen-Score bewegt sich dort im normalen mittleren Bereich.

## Falsch

```python
# lane_processor.py: Verdeckung nur als Freeze, ohne Nachwirkung
if self._occlusion_frames >= self.cfg.detection.green.occlusion_min_frames:
    ...
    return self._observation(green), None, None
# -- sobald die Verdeckung endet, ist keine Spur mehr davon da.
```

## Richtig

```python
# lane_processor.py: Merken, WAEHREND welchem Fenster die Verdeckung war
if self._occlusion_frames >= self.cfg.detection.green.occlusion_min_frames:
    if self._window_open:
        self._occlusion_during_window = True
    ...

# throw_analyzer.py: 0 Kegel + Verdeckung im eigenen Fenster == keine Messung
if (self.cfg.scoring.discard_occluded_zero_throws
        and window_was_occluded and count == 0):
    return None  # Luecke, kein Wurf
```

## NACHTRAG 2026-09-03 21:20 — der Fix ist UNVOLLSTAENDIG

Der Vollauf `lauf_2026-09-03_20-21-33` zeigt: Von den drei Faellen faengt der
Fix nur einen (F16256), F15569 bleibt. Der Unterschied ist die LAGE der
Verdeckung zum Fenster:

| Fall | Verdeckung | Zyklus-Trigger | Fix greift? |
|---|---|---|---|
| F16256 | F16261-16296 | F16256 (davor) | **ja** -- Verdeckung liegt IM Fenster |
| F15569 | F15532-15568 | F15569 (danach) | **nein** -- Verdeckung liegt VOR dem Fenster |

Bei F15569 loeste das GREEN_OFF erst aus, als die Tafel wieder sichtbar war.
`_window_open` war waehrend der Verdeckung False, das Flag wurde nie gesetzt.

**Was daraus folgt:** Ein GREEN_OFF unmittelbar NACH dem Ende einer Verdeckung
ist selbst verdaechtig -- die Zustandsmaschine sieht dort einen Sprung von
"eingefroren" auf "gruen aus", ohne den Uebergang beobachtet zu haben. Der
Fix muesste also auch greifen, wenn das Fenster innerhalb von N Frames nach
einer Verdeckung beginnt.

**Warum das nicht sofort gemacht wurde:** N ist ein neuer Schwellwert und
muss gemessen werden (wie weit nach einer Verdeckung ist ein GREEN_OFF noch
verdaechtig?). Ein geratenes N waere genau der Fehler, den dieses Projekt
nicht macht.

## Regel für die Zukunft

> Eine Schutzmassnahme, die nur WAEHREND eines Ereignisses wirkt, schuetzt
> nicht vor dessen NACHWIRKUNG -- frage bei jeder Freeze-/Bremslogik: "Was
> weiss der Code danach noch davon, dass hier eingefroren wurde?"

## Wo gilt diese Regel noch?

- [x] Kegellampen-Ergebnis (`pins`) -- durch `count == 0`-Beschraenkung
      abgedeckt, ein NICHT-leeres Ergebnis waehrend Verdeckung bleibt
      unangetastet (kein Messbeleg fuer einen Fehler dort).
- [ ] Die spaet gelesene Summe (`_read_late_fields`/`displayed_total`) koennte
      durch dieselbe Randbedingung verfaelscht werden, wenn die Verdeckung
      genau in ihr eigenes Lesefenster faellt -- noch nicht gemessen, siehe
      `docs/OPEN_QUESTIONS.md`.
- [ ] Ein gruenes Trikot als Gegenteil-Risiko (Verdeckung wird NICHT erkannt,
      weil der Score hoch bleibt statt auf 0 zu fallen) ist nicht beobachtet,
      aber auch nicht ausgeschlossen -- siehe `docs/OPEN_QUESTIONS.md`.
