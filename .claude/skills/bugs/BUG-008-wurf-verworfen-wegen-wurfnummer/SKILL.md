---
name: bug-008-wurf-verworfen-wegen-wurfnummer
description: >
  Verhindert COUNT-Bug: Ein Wurf wurde verworfen, weil die gelesene Wurfnummer
  nicht anstieg -- obwohl der Gruenzyklus den Wurf bereits bewiesen hatte. Kostete
  28 % aller Wuerfe. Laden bei Arbeit an Wurfnummer, Doppelzaehlungsschutz,
  Plausibilitaetspruefungen oder wenn Ergebnisse "einfach fehlen".
---

# BUG-008 — Eine Gegenprobe verwarf, was sie nur pruefen sollte

| | |
|---|---|
| **Kategorie** | `COUNT` |
| **Gefunden** | 2026-08-25, beim Vergleich von Gruenzyklen mit gemeldeten Wuerfen |
| **Schweregrad** | **kritisch** — 20 von 71 Wuerfen (28 %) fehlten in der Ausgabe |
| **Regressionstest** | `tests/unit/test_throw_analyzer.py::TestWurfnummer` |

## Symptom

Wuerfe fehlten vollstaendig in der Tabelle. Nicht falsch gezaehlt — abwesend.
Auf einer Bahn erschienen 8 von 18 Wuerfen. Die Wurfnummern zeigten Luecken:

```
Bahn 4:  3, 4, 5, 6, 10, 13, 14, 15
Bahn 5:  1, 2, 3, 4, 7, 10, 11, 12, 13, 14, 17
```

Das Tueckische: Nichts sah kaputt aus. Die gemeldeten Wuerfe waren korrekt, die
Summenketten in sich stimmig. Der Fehler war nur durch **Zaehlen dessen, was
nicht da war** zu finden.

## Ursache

```python
last = self.score.last_throw_number
if throw_number <= last:
    return None      # verworfen
```

Die Wurfnummer der Tafel wird per Ziffernerkennung gelesen und ist damit
fehleranfaellig. Wurde EIN Wurf zu hoch gelesen — echte 7 als "10" — stand
`last` anschliessend zu weit vorn. Die darauffolgenden **echten** Nummern 8 und
9 lagen darunter und wurden saemtlich als "bereits gebucht" verworfen. Ein
einzelner Lesefehler loeschte den Rest der Serie.

BUG-005 hatte denselben Mechanismus fuer *grosse* Spruenge entschaerft
(`max_throw_number_jump`). Uebersehen wurde, dass ein Sprung von 3 unterhalb der
Schwelle bleibt und trotzdem dieselbe Kettenreaktion ausloest.

## Die Regel

> **Eine Gegenprobe darf niemals loeschen, was eine staerkere Quelle bewiesen
> hat.** Sie darf widersprechen, markieren, die Confidence senken — nicht
> verwerfen.

Der Gruenzyklus ist hier die staerkere Quelle: Er beweist physikalisch, dass
geworfen wurde. Die Wurfnummer ist eine per OCR gelesene Hilfsgroesse. Dass die
schwaechere Quelle die staerkere ueberstimmen konnte, war die eigentliche
Fehlkonstruktion — dieselbe Verwechslung wie in BUG-006, dort zwischen Waerme
und Helligkeit.

Gegen Doppelzaehlung schuetzt die Zustandsmaschine (P3): Sie ruft `analyze()`
genau einmal je Gruenzyklus. Der Schutz ueber die Wurfnummer war Redundanz --
und kostete mehr, als er einbrachte.

## Richtig

```python
if throw_number <= last:
    fallback = last + 1
    decisions.append(f"Wurfnummer {throw_number} nicht plausibel ...")
    checks.append(PlausibilityCheck("Wurfnummer steigt", f"> {last}",
                                    throw_number, False))
    return fallback
```

Der Widerspruch bleibt in der Beweiskette sichtbar. Wirkung: Erfassungsquote
von 71,8 % auf 98,6 %.

## Wie so etwas gefunden wird

Nicht durch Pruefen der Ausgabe — die war plausibel. Sondern durch eine
**unabhaengige Zaehlung der Eingangsereignisse**: 71 Gruenzyklen gegen 51
gemeldete Wuerfe. Diese Gegenueberstellung gehoert in jede Auswertung.

## Wo gilt diese Regel noch?

- [x] `_resolve_throw_number` — gefixt
- [x] Gruenzyklen gegen Wuerfe wird jetzt gemessen
- [ ] `_determine_status`: Setzt Widersprueche auf ERROR. Pruefen, ob ein
      ERROR-Wurf irgendwo aus der Auswertung faellt statt markiert zu werden.
- [ ] Ziffernfelder: `read_digit` gibt bei Zweifel "?" zurueck statt einer
      unsicheren Ziffer. Das ist richtig — aber nur, weil die Ziffer Gegenprobe
      ist und nichts loescht.
