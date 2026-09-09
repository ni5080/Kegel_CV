---
name: bug-010-summe-zu-frueh-gelesen
description: >
  Verhindert TEMPORAL-Bug: Die Anzeigetafel aktualisiert die Gesamtsumme erst
  kurz vor dem naechsten GREEN_ON -- rund 300 Frames nach dem Wurf. Wer im
  Sampling-Fenster liest, bekommt ausnahmslos den ALTEN Stand. Laden bei Arbeit
  an Ziffernfeldern, Sampling-Zeitpunkten, Summenpruefung oder wenn ein Wert
  konstant zum falschen Ereignis zu gehoeren scheint.
---

# BUG-010 — Die Summe stand noch auf dem alten Wert

| | |
|---|---|
| **Kategorie** | `TEMPORAL` |
| **Gefunden** | 2026-08-25, durch einen Hinweis des Nutzers |
| **Schweregrad** | **hoch** — die einzige unabhaengige Gegenprobe war unbrauchbar |
| **Regressionstest** | `tests/unit/test_field_aggregation.py` |

## Symptom

Der Zuwachs der angezeigten Gesamtsumme passte nicht zur gemessenen Kegelzahl.
Nur 34,8 % der Summenketten stimmten — und damit fehlte die einzige Quelle, mit
der sich die Lampenzaehlung unabhaengig belegen liesse.

## Die falsche Fährte

Die Abweichungen sahen nach Lesefehlern aus, und es gab reichlich Belege dafuer:
Zuwaechse von −51 und +69 kamen vor, die vierstellige Summe ist das kleinste
Ziffernfeld. Zwei Verbesserungen wurden daraufhin gebaut — stellenweise
Aggregation und ein breiteres Fenster — und beide halfen ein Stueck. Der
eigentliche Fehler lag woanders.

Ein Warnsignal war vorhanden und wurde falsch gedeutet: Der Zuwachs passte
**18-mal zum vorherigen Wurf** und nur 8-mal zum aktuellen. Das ist kein
Lesefehler-Muster, sondern ein Versatz. Es wurde als Nebenbefund notiert statt
als Hauptspur verfolgt.

## Ursache

**Der Nutzer wusste es:** „der letzte Wurf wird erst im Ergebnis angezeigt, kurz
bevor das grüne Lämpchen angeht."

Nachgemessen ueber drei vollstaendige Wurffenster (Bahn 4):

```
Wurf 1   GREEN_OFF 1152 ......................... GREEN_ON 1490
         frueh (+2 .. +30):  001 6 0000     Summe noch der alte Stand
         spaet (-60 .. -8):  001 6 0006     Summe eingetragen (0 + 6)

Wurf 3   frueh:  003 5 0014      spaet:  003 5 0019      (14 + 5 stimmt)
```

Wurfnummer und Kegelzahl stehen **sofort** richtig da — nur die Summe zieht
spaet nach. Das Sampling-Fenster umfasst rund 34 Frames, das Wurfintervall aber
216–338. Die Summe wurde damit **ausnahmslos** im alten Stand gelesen.

## Richtig

Verschiedene Felder derselben Anzeige brauchen verschiedene Messzeitpunkte:

```yaml
late_fields: [total_a, total_b]   # erst spaet aktualisiert
late_read_interval: 5
late_keep: 14                     # deckt ~70 Frames vor GREEN_ON ab
```

Die spaeten Felder werden waehrend des Fensters mitgelesen und die juengsten
Messungen behalten. Bewusst **nicht** ueber den Ringpuffer: Um 60 Frames
zurueckzugreifen, muesste er bei 1920×1080 auf ueber 500 MB wachsen.

Wirkung: Summenkette von 34,8 % auf 82,4 %.

## Die Regel

> **Ein Anzeigefeld hat einen eigenen Zeitpunkt, zu dem es die Wahrheit sagt.**
> Dass mehrere Felder auf derselben Tafel stehen, heisst nicht, dass sie
> gleichzeitig gueltig sind.

Und zur Fehlersuche: **Ein systematischer Versatz sieht nie aus wie Rauschen.**
Passt ein Wert regelmaessig zum Nachbarereignis, ist die Ursache ein
Zeitpunkt — nicht die Messqualitaet. Diese Unterscheidung haette hier zwei
Umwege gespart.

Und schliesslich: Der Nutzer kennt die Anlage. Ein Satz von ihm loeste, was
mehrere Messreihen nicht gefunden hatten.

## Wo gilt diese Regel noch?

- [x] `total_a` / `total_b` — ueber `late_fields` geloest
- [ ] **Serienstand (Q3, jede 15 Wuerfe)**: Wird vermutlich zum selben Zeitpunkt
      aktualisiert wie die Summe. Noch nicht geprueft.
- [ ] **Fehlwurfzaehler `left_display` (Q2)**: Zeitpunkt unbekannt. Wird derzeit
      aus den fruehen Frames gelesen — wie die Summe zuvor.
- [ ] Kegelzahl und Wurfnummer: gemessen sofort gueltig, hier kein Handlungsbedarf.
