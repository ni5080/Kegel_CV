---
name: bug-005-falsche-wurfnummer-legt-bahn-still
description: >
  Verhindert COUNT-Bug: Eine einzelne falsch gelesene Wurfnummer (703 statt 3)
  haette den Zaehler einer Bahn dauerhaft zerstoert, weil danach jeder echte
  Wurf als "bereits gebucht" verworfen worden waere. Laden bei Arbeit an
  Wurfnummern, Zaehlerstaenden, Double-Counting-Schutz, Plausibilitaetsgrenzen
  oder wenn ein erkannter Wert einen fortlaufenden Zustand fortschreibt.
---

# BUG-005 — Eine falsche Wurfnummer hätte die Bahn stillgelegt

| | |
|---|---|
| **Kategorie** | `COUNT` |
| **Gefunden** | 2026-08-24, erster vollständiger Analyselauf |
| **Schweregrad** | **hoch** — Datenverlust für den Rest des Videos |
| **Regressionstest** | `tests/unit/test_throw_analyzer.py::TestWurfnummer` |

## Symptom

Im Lauf über `2026-08-22 09-24-46.mp4` erschien in der Ergebnisliste:

```
Bahn  Wurf  Kegel  Gesamt  Status
   2   703      2       2  ERROR
```

Nach Wurf 2 sprang die Wurfnummer auf 703. Die Ziffernerkennung hatte
`throw_number` falsch gelesen.

## Ursache

Der Double-Counting-Schutz verwirft jeden Wurf, dessen Nummer **nicht größer**
ist als die zuletzt gebuchte — fachlich richtig und notwendig.

Genau dieser Schutz wird aber zur Falle, sobald ein zu **hoher** Wert
durchrutscht: Nach der Buchung von 703 wäre jeder echte Folgewurf (4, 5, 6 …)
kleiner gewesen und damit als Doppelzählung verworfen worden. **Ein einzelner
Lesefehler hätte die Bahn für den gesamten Rest des Videos stillgelegt** — ohne
Fehlermeldung, denn das Verwerfen ist ja das gewollte Verhalten.

Warum das trügerisch plausibel aussieht: Die Prüfung `throw_number <= last` wirkt
vollständig. Sie deckt aber nur eine Richtung ab. Dass ein *zu großer* Wert
gefährlicher ist als ein zu kleiner, ist beim Schreiben nicht offensichtlich —
der Schaden entsteht erst später und an anderer Stelle.

## Falsch

```python
if throw_number <= last:
    return None          # Doppelzaehlung -- korrekt
# jeder groessere Wert wird uebernommen -- auch 703
```

## Richtig

```python
if throw_number <= last:
    return None

jump = throw_number - last
if last > 0 and jump > self.cfg.scoring.max_throw_number_jump:
    fallback = last + 1
    log.warning("Wurfnummer %d unplausibel (Sprung %d) -- zaehle auf %d fort",
                throw_number, jump, fallback)
    return fallback      # Ziffer verwerfen, Wurf trotzdem buchen
```

Entscheidend ist die Haltung dahinter: **Die Wurfnummer ist eine Hilfsgröße, kein
Selbstzweck.** Dass ein Wurf stattgefunden hat, steht durch die Zustandsmaschine
bereits fest. Ist die abgelesene Nummer unglaubwürdig, wird sie verworfen — nicht
der Wurf.

## Regel für die Zukunft

> Wenn ein **erkannter** Wert einen fortlaufenden Zustand fortschreibt, braucht er
> eine Plausibilitätsgrenze in **beide** Richtungen. Sonst vergiftet ein einzelner
> Fehler den Zustand dauerhaft.
>
> Und: Ein unglaubwürdiger Messwert darf nie das ganze Ereignis verwerfen, wenn
> das Ereignis aus anderer Quelle bereits belegt ist.

## Wo gilt diese Regel noch?

- [x] `analysis/throw_analyzer.py::_resolve_throw_number` — gefixt
- [ ] Laufende Summe (`displayed_total`): Wird derzeit nur geprüft, nicht
      übernommen — die Summe kommt aus den gezählten Kegeln. Sollte sie je als
      Quelle dienen, braucht sie dieselbe Grenze.
- [ ] Fehlwurfzähler (`left_display`, Q2): schreibt `self._foul_count` fort und
      hat noch **keine** Plausibilitätsgrenze. Vor der Aktivierung in Phase 7
      nachrüsten.
- [ ] `LaneScore.register` wirft bei Rückwärtssprung eine Exception — der
      Aufrufer muss sie fangen, sonst stirbt der Analyselauf an einem Lesefehler.
