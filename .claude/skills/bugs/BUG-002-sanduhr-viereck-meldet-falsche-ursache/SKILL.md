---
name: bug-002-sanduhr-viereck-meldet-falsche-ursache
description: >
  Verhindert CALIB-Bug: Ein Viereck mit vertauschten Eckpunkten hat nach der
  Gauss'schen Trapezformel die Flaeche null, weshalb die Pruefreihenfolge eine
  irrefuehrende Fehlermeldung erzeugte ("zu klein" statt "falsche Reihenfolge").
  Laden bei Arbeit an Eckpunkten, Polygonpruefung, Flaechenberechnung,
  Konvexitaet, Validierungsreihenfolge oder Fehlermeldungen fuer Bedienfehler.
---

# BUG-002 — Sanduhr-Viereck meldete die falsche Ursache

| | |
|---|---|
| **Kategorie** | `CALIB` |
| **Gefunden** | 2026-08-24, Phase 2 (durch Test) |
| **Schweregrad** | niedrig technisch, **hoch für die Bedienbarkeit** |
| **Regressionstest** | `tests/unit/test_calibration.py::TestQuad::test_vertauschte_reihenfolge_wird_erkannt` |

## Symptom

Der Nutzer klickt die vier Tafelecken in falscher Reihenfolge (Punkt 3 und 4
vertauscht — ein sehr naheliegender Bedienfehler). Die Anwendung meldete:

```
Viereck ist zu klein oder entartet (Flaeche 0.0 < 100.0)
```

Der Nutzer sucht daraufhin den Fehler bei der Größe seiner Auswahl — und klickt
dieselbe falsche Reihenfolge nur größer nach.

## Ursache

Ein sanduhrförmiges Viereck hat nach der Gauss'schen Trapezformel die
**Fläche exakt null**: Die beiden entstehenden Dreiecke haben entgegengesetzten
Umlaufsinn und heben sich rechnerisch auf.

```
   1 o---------o 2         1 o---------o 2
     |         |            \         /
     |  gut    |      vs.    \   X   /      Flaeche = 0, nicht "klein"
     |         |            /         \
   4 o---------o 3         4 o---------o 3   (3 und 4 vertauscht)
```

Da `validate()` die Fläche **vor** der Konvexität prüfte, schlug immer die
Flächenprüfung zuerst an — und deren Meldung beschreibt ein ganz anderes Problem.

Warum das trügerisch plausibel aussieht: Beide Prüfungen sind einzeln korrekt und
der Fehler wird zuverlässig *erkannt*. Nur die **Diagnose** ist falsch. Solche
Fehler bestehen jeden Test, der nur `pytest.raises(...)` prüft — erst ein Test auf
den Meldungstext deckt sie auf.

## Falsch

```python
if self.area < min_area:
    raise GeometryError("Viereck ist zu klein oder entartet ...")
if not self.is_convex():
    raise GeometryError("Viereck ist nicht konvex ...")
```

## Richtig

```python
# Konvexitaet VOR Flaeche: Die spezifischere Diagnose zuerst.
if not self.is_convex():
    raise GeometryError(
        "Viereck ist nicht konvex -- vermutlich wurden die Eckpunkte in "
        "falscher Reihenfolge gesetzt (erwartet: oben links, oben rechts, "
        "unten rechts, unten links)"
    )
if self.area < min_area:
    raise GeometryError("Viereck ist zu klein oder entartet ...")
```

## Regel für die Zukunft

> Bei mehreren Validierungen entscheidet die **Reihenfolge über die Diagnose**.
> Die spezifischere Prüfung kommt zuerst, die allgemeinere danach — sonst
> verdeckt eine generische Meldung die eigentliche Ursache.
>
> Und: Bei Fehlern, die aus **Bedienung** entstehen, wird der Meldungstext
> mitgetestet, nicht nur die Tatsache, dass eine Exception fliegt.

## Wo gilt diese Regel noch?

- [x] `calibration/geometry.py::Quad.validate` — gefixt
- [ ] `config/schema.py` — Pydantic prüft Feldgrenzen vor `model_validator`;
      bei kombinierten Bedingungen (z.B. Hysterese) auf verständliche Texte achten
- [ ] Plausibilitätsprüfung der Würfe (Phase 9): Bei mehreren gleichzeitig
      verletzten Regeln muss die Meldung die **aussagekräftigste** nennen,
      nicht die zuerst geprüfte
