---
name: kegel-statemachine
description: >
  Zustandsmaschine, Wurferkennung und Zähllogik in Kegel_CV. Laden bei Arbeit an
  Zustandsübergängen, Double Counting, Wurfnummern, 15-Wurf-Zyklen, Zwischensummen,
  laufender Gesamtsumme, Plausibilitätsprüfung, Confidence-Gesamtbewertung oder
  wenn ein Wurf bestätigt, verworfen oder als EMPTY/INVALID eingestuft wird.
---

# Zustandsmaschine & Wurflogik

## 1. Die Zustände

```
                  +----------------------------+
                  |                            |
                  v                            |
   READY --> GREEN_ON --> GREEN_OFF --> ANALYZING
                                              |
                                              v
                                    RESULT_STABILIZATION
                                              |
                                              v
                                      RESULT_CONFIRMED
                                              |
                                              v
                                    WAIT_FOR_NEXT_GREEN
                                              |
                                              +--> READY
```

| Zustand | Bedeutung | Verlassen wenn |
|---|---|---|
| `READY` | Bahn beobachtet, kein Ereignis | Grün geht AN |
| `GREEN_ON` | Bahn freigegeben, Spieler wirft | Grün geht AUS |
| `GREEN_OFF` | Ereignis erkannt, Sampling startet | Sampling-Frames gesammelt |
| `ANALYZING` | Frames werden ausgewertet | Ergebnisse liegen vor |
| `RESULT_STABILIZATION` | Aggregation über mehrere Frames | stabil oder Timeout |
| `RESULT_CONFIRMED` | Wurf gebucht | sofort |
| `WAIT_FOR_NEXT_GREEN` | **Sperre gegen Doppelzählung** | Grün geht wieder AN |

**Pro Bahn eine eigene Instanz.** Nie ein gemeinsamer Zustand für alle vier —
das ist Prinzip P6 und der häufigste denkbare Architekturfehler in diesem Projekt.

## 2. Double Counting — die zentrale Gefahr

Ein Wurf ist über viele Frames sichtbar. Ohne Sperre entstünde pro Frame ein Wurf.

Drei unabhängige Schutzmechanismen, die gemeinsam greifen:

1. **`WAIT_FOR_NEXT_GREEN`** — nach einem bestätigten Wurf kann erst wieder gebucht
   werden, wenn Grün erneut AN und dann AUS war. Ein Zustand allein reicht nicht.
2. **Wurfnummern-Vergleich** — die Tafel liefert die Wurfnummer. Ist sie gleich der
   zuletzt gebuchten, wird **nicht** gebucht, egal was die Zustandsmaschine meint.
3. **Mindestabstand** (`min_frames_between_throws`) — ein physisch unmöglich
   schneller Folgewurf ist eine Fehlerkennung.

```python
if new_throw_number == last_throw_number:
    log.debug("Wurf verworfen (bereits gebucht): nr=%s", new_throw_number)
    return None
```

**Die Wurfnummer der Tafel ist die Autorität** — sie ist die einzige Quelle, die
Doppelzählung fachlich (nicht nur zeitlich) ausschließt.

## 3. Verpasste Würfe erkennen

Der Gegenfehler zum Double Counting: springt die Wurfnummer von 7 auf 9, wurde
Wurf 8 verpasst.

```python
if new_throw_number > last_throw_number + 1:
    log.warning("Lücke erkannt: %s -> %s, %s Wurf/Würfe verpasst",
                last, new, new - last - 1)
    # Platzhalter mit Status UNKNOWN anlegen -- Lücke sichtbar machen, nicht kaschieren
```

Eine Lücke wird **nie stillschweigend geschlossen**. Sie erscheint als Eintrag mit
Status `UNKNOWN` in der Tabelle, damit sie beim Debuggen auffällt.

## 4. Zyklus-Rechnung (15 Würfe)

```python
throw_in_cycle = (throw_number - 1) % 15 + 1     # 1..15
cycle_number   = (throw_number - 1) // 15 + 1    # 1..n
```

| Wurf | throw_in_cycle | cycle |
|---|---|---|
| 1 | 1 | 1 |
| 15 | **15** | 1 |
| 16 | 1 | 2 |
| 30 | **15** | 2 |

Klassischer Fehler: `throw_number % 15` liefert bei Wurf 15 den Wert **0** statt 15.
`throws_per_cycle` kommt aus der Config, nicht als `15` im Code.

## 5. Plausibilitätsprüfung

Vier unabhängige Quellen werden gegeneinander geprüft:

```
   Lampenanzahl  ==  angezeigte Ziffer            -> Gewicht hoch
   Wurfnummer    ==  letzte + 1                   -> Gewicht hoch
   Summe_neu     ==  Summe_alt + gefallene Kegel  -> Gewicht hoch
   Summe A       ==  Summe B                      -> Gewicht mittel
```

| Ergebnis | Status |
|---|---|
| alle vier stimmen | `VALID` (bzw. `EMPTY` bei 0 Kegeln) |
| eine Abweichung | `VALID` mit reduzierter Confidence + `WARNING`-Log |
| mehrere Abweichungen | `ERROR` — Ergebnis **nicht** übernehmen |

**Bei Widerspruch nie blind eine Quelle bevorzugen.** Die Redundanz existiert genau
dafür, Fehler sichtbar zu machen — sie wegzuentscheiden zerstört ihren Zweck.

## 6. Ein Störframe darf nichts kippen

```python
# Falsch -- ein einzelner Frame ändert den Zustand
if green_score < threshold:
    self.state = State.GREEN_OFF

# Richtig -- Zustandswechsel braucht Bestätigung über mehrere Frames
self._off_votes = self._off_votes + 1 if green_score < off_threshold else 0
if self._off_votes >= self.cfg.min_stable_frames:
    self._transition(State.GREEN_OFF)
```

Das gilt für **jeden** Übergang, nicht nur für Grün.

## 7. Timeouts

Jeder Zustand außer `READY` braucht einen Timeout. Sonst bleibt die Bahn nach einer
Fehlerkennung für immer hängen — und die restlichen Würfe fehlen.

```yaml
state_machine:
  analyzing_timeout_s: 5.0
  stabilization_timeout_s: 3.0
  wait_green_timeout_s: 300.0   # Spieler kann lange pausieren -> großzügig
```

Timeout ⇒ Rückfall nach `READY`, Vorfall als `WARNING` protokollieren.
`wait_green_timeout_s` ist bewusst groß: „Spieler werfen lange nicht" ist ein
regulärer Fall (Auftrag §22), kein Fehler.

## 8. Was in jedem Wurfergebnis stehen muss

```python
ThrowResult(
    lane=1, throw_number=17, throw_number_in_series=2,
    pins=[1,3,5,6,8], pins_count=5, displayed_pin_count=5,
    status=ThrowStatus.VALID, running_total=42, series_total=None,
    confidence=0.94, timestamp=184.23, source_frames=[4580,4583,4587,4594],
    evidence=Evidence(...),   # alle Einzelmessungen + Entscheidungen
)
```

Ziel (Auftrag §27): Die Frage *„Warum wurde Wurf 17 so erkannt?"* muss allein aus
diesem Objekt und dem Event-Log beantwortbar sein — ohne das Video erneut zu laden.
