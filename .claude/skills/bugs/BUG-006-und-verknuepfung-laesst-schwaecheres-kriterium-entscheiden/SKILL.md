---
name: bug-006-und-verknuepfung-laesst-schwaecheres-kriterium-entscheiden
description: >
  Verhindert DETECT-Bug: Zwei Messkriterien wurden mit UND verknuepft, wodurch
  das schlechter trennende das Ergebnis bestimmte -- klar leuchtende Kegellampen
  galten als UNKNOWN. Laden bei Arbeit an Detektoren, Schwellwerten, kombinierten
  Kriterien, Trennguete oder wenn eine Erkennung "manchmal" versagt, obwohl das
  Signal eindeutig aussieht.
---

# BUG-006 — UND-Verknüpfung ließ das schwächere Kriterium entscheiden

| | |
|---|---|
| **Kategorie** | `DETECT` |
| **Gefunden** | 2026-08-25, Nutzermeldung: „dauerhaft leuchtende PinLampen werden teilweise falsch ausgelesen" |
| **Schweregrad** | **hoch** — betraf die Hauptquelle der Kegelzählung |
| **Regressionstest** | `tests/unit/test_detectors.py::test_bug_006_helligkeit_entscheidet_nicht_die_waerme` |

## Symptom

Auf Tafel 1 meldeten **8 von 9 Kegellampen** den Zustand `UNKNOWN`, obwohl im
Bild klar erkennbar war, welche leuchten. Die Wurfauswertung stufte solche Würfe
folgerichtig als `ERROR` ein — die Kegelzählung fiel praktisch aus.

```
Lampe   Wärme   Helligkeit   Zustand
    1    31,7        255,0    UNKNOWN     ← leuchtet eindeutig
    2    33,2        254,8    UNKNOWN
    4    37,6        254,8    UNKNOWN
```

## Ursache

Der Detektor verlangte **beide** Kriterien gleichzeitig:

```python
if warmth >= 40 and brightness >= 215:
    state = LampState.ON
```

Damit entscheidet in der Praxis das **schlechter trennende** Kriterium — es ist
der Flaschenhals. Eine Messung über 3600 Werte (4 Tafeln × 9 Lampen × 100 Frames)
zeigt, wie unterschiedlich gut beide trennen:

| Kriterium | AUS | AN | Trennschärfe |
|---|---|---|---|
| Wärme (R−B) | 19 ± 10 | 57 ± 13 | **3,35** |
| Helligkeit | 154 ± 23 | 254 ± 3 | **7,66** |

Die Helligkeit trennt mehr als doppelt so gut: Eine leuchtende Lampe ist im Bild
**gesättigt**, daher die winzige Streuung von ±3. Die Wärme streut so stark, dass
sich die Verteilungen überlappen.

Warum das trügerisch plausibel aussah: Eine frühere Messung an **einem einzelnen
Frame** hatte das Gegenteil nahegelegt (Wärme 60–71 gegen 18–20, Faktor 3). Diese
Stichprobe war zu klein — sie stammte aus einer Tafel bei einer Beleuchtung. Über
alle Bahnen und viele Frames kehrt sich das Bild um.

## Falsch

```python
# Beide Kriterien gleichwertig verlangt -> das schwaechere dominiert
if warmth >= self.cfg.warmth_on_threshold and \
        brightness >= self.cfg.brightness_threshold:
    state = LampState.ON
```

## Richtig

```python
# Das trennschaerfere Kriterium entscheidet, das andere sichert nur ab
if (brightness >= self.cfg.brightness_on_threshold
        and warmth >= self.cfg.warmth_min):      # locker, nur Plausibilitaet
    state = LampState.ON
elif brightness <= self.cfg.brightness_off_threshold:
    state = LampState.OFF
```

`warmth_min` liegt bewusst weit unter jedem realen AN-Wert. Es fängt nur helle,
**farblose** Reflexe ab und kann das Hauptkriterium nie überstimmen.

## Regel für die Zukunft

> Werden mehrere Kriterien mit **UND** verknüpft, bestimmt das **schwächste** das
> Ergebnis. Vor einer solchen Verknüpfung gehört gemessen, wie gut jedes einzeln
> trennt — und das stärkste wird zum Hauptkriterium, die übrigen zu bewusst
> lockeren Absicherungen.
>
> Trennschärfe = |µ_an − µ_aus| / mittlere Streuung. Alles unter etwa 3 taugt
> nicht als Hauptkriterium.

Und der zweite Teil der Lektion: **Schwellwerte nie an einem Standbild
festlegen.** Die erste Messung stammte aus einem Frame einer Tafel und wies in
die falsche Richtung. Verlässlich wird es erst über viele Frames und alle Bahnen.

## Wo gilt diese Regel noch?

- [x] `detection/lamp_detectors.py::WarmthLampDetector` — gefixt und verifiziert
      (Tafel 1: 6 Kegel erkannt, Anzeige zeigt „6"; Tafel 2: 9, Anzeige „9")
- [ ] `HsvGreenDetector` nutzt eine HSV-Maske mit UND über Farbton, Sättigung und
      Helligkeit. Bisher unauffällig, aber nach demselben Muster gebaut — bei
      Problemen dort zuerst die Trennschärfe der drei Anteile einzeln messen.
- [ ] Ziffernerkennung: Die Prüfung `best_score < template_min_score` ist ein
      einzelnes Kriterium; kommt ein zweites hinzu, gilt diese Regel.
