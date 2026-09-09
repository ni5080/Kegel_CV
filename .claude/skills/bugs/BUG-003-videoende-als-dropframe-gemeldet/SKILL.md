---
name: bug-003-videoende-als-dropframe-gemeldet
description: >
  Verhindert VIDEO-Bug: Das normale Videoende wurde als Dropframe-WARNUNG
  geloggt, weil ein fehlgeschlagener read() sofort bewertet wurde, obwohl sich
  Dropframe und Ende erst im Nachhinein unterscheiden lassen. Laden bei Arbeit
  an VideoSource, read(), Frame-Iteration, Dropframes, Videoende, Streamabbruch
  oder wenn Logs mit falschen Warnungen volllaufen.
---

# BUG-003 — Videoende wurde als Dropframe gemeldet

| | |
|---|---|
| **Kategorie** | `VIDEO` |
| **Gefunden** | 2026-08-24, beim ersten Lauf der Live-Analyse |
| **Schweregrad** | niedrig technisch, **mittel für die Diagnose** |
| **Regressionstest** | `tests/unit/test_video_source.py::TestDropframes` |

## Symptom

Jeder vollständige Analysedurchlauf endete mit neun identischen Warnungen:

```
WARNING Frame 122 konnte nicht gelesen werden (Dropframe?)
WARNING Frame 123 konnte nicht gelesen werden (Dropframe?)
...
WARNING Frame 130 konnte nicht gelesen werden (Dropframe?)
```

Das Video hatte 122 Frames — es war schlicht zu Ende. Keine Dropframes.

## Ursache

Ein fehlgeschlagener `cap.read()` ist **zweideutig**: Er bedeutet entweder einen
Dropframe oder das Ende der Quelle. OpenCV unterscheidet das nicht.

Der Code bewertete den Fehlschlag jedoch **sofort** und entschied sich für die
Dropframe-Deutung — die Information, die für die Unterscheidung nötig ist, lag zu
diesem Zeitpunkt noch gar nicht vor.

Warum das trügerisch plausibel aussieht: Die Logik *funktionierte* korrekt — nach
`max_read_failures` Versuchen wurde sauber `None` geliefert und die Analyse
beendet. Nur die Diagnose war falsch. Solche Fehler sind besonders schädlich,
weil sie das Log vergiften: Wer neun Warnungen bei jedem Lauf sieht, gewöhnt sich
daran und übersieht später die eine echte.

## Falsch

```python
if not ok:
    self._consecutive_failures += 1
    self._next_index += 1
    if self._consecutive_failures >= self._max_read_failures:
        return None
    log.warning("Frame %d konnte nicht gelesen werden (Dropframe?)", ...)
    return self.read()      # zusaetzlich: Rekursion statt Schleife
```

## Richtig

```python
skipped = 0
while True:
    ok, image = self._cap.read()
    if ok:
        break
    skipped += 1
    self._consecutive_failures += 1
    self._next_index += 1
    if self._consecutive_failures >= self._max_read_failures:
        return None                      # Ende -- keine Warnung

if skipped:
    # Jetzt erst steht fest: es kam noch ein Frame, also war es ein Dropframe
    log.warning("%d Frame(s) uebersprungen (Dropframe) vor Frame %d", ...)
```

## Regel für die Zukunft

> Ein Ereignis, dessen Bedeutung erst durch das **folgende** Ereignis feststeht,
> darf nicht sofort bewertet werden. Erst die Information abwarten, dann
> protokollieren.

Das gilt in diesem Projekt an mehreren Stellen — es ist dasselbe Muster wie bei
der Zustandsmaschine: Ein einzelner Frame entscheidet nie, erst die Bestätigung
über mehrere Frames.

Zusatz: Wiederholtes Lesen gehört in eine **Schleife**, nicht in Rekursion.
Bei einem großzügig konfigurierten `max_read_failures` wäre die Rekursionstiefe
sonst unnötig ein Risiko.

## Wo gilt diese Regel noch?

- [x] `video/file_source.py::read` — gefixt
- [ ] `StreamVideoSource` (später): Dort ist ein fehlgeschlagener Read noch
      zweideutiger — Netzaussetzer, Pufferleerlauf oder Streamende. Die
      Warteschwelle muss dort deutlich höher liegen als bei einer Datei.
- [ ] Ziffernerkennung (Phase 7): Ein einzelnes unlesbares Frame ist kein Fehler,
      sondern erwartetes Flackern. Erst wenn die Aggregation über alle Frames
      uneindeutig bleibt, ist es ein `ERROR`.
