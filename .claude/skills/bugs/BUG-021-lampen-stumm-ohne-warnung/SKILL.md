---
name: bug-021-lampen-stumm-ohne-warnung
description: >
  Verhindert DETECT-Bug: Ein ganzer Lauf buchte auf allen vier Bahnen "0 Kegel"
  und schickte das an die Datenbank, weil eine alte Kalibrierung zu grosse
  Lampen-ROIs mitbrachte -- ohne dass irgendetwas warnte. Laden bei Arbeit an
  Lampenerkennung, ROI-Groessen, Schwellwerten, die ueber Mittelwerte gebildet
  werden, beim Wechsel von Kalibrierungen, und immer dann, wenn ein Ergebnis
  "leer" statt "unbekannt" ist.
---

# BUG-021 — Vier Bahnen messen nichts, und niemand sagt es

| | |
|---|---|
| **Kategorie** | `DETECT` |
| **Gefunden** | 2026-09-07, durch den Nutzer nach einem Testlauf unter realen Bedingungen |
| **Schweregrad** | **hoch** (ein kompletter Lauf unbrauchbar, Ergebnisse bereits versendet) |
| **Regressionstest** | `test_lamp_watchdog.py` (13 Tests, darunter `TestAmEchtenFall`) |

## Symptom

Ein Lauf über 67 Würfe buchte auf **allen vier Bahnen ausschließlich
„0 Kegel"** und schickte jeden dieser Würfe an Supabase. Die Analyse lief
durch, meldete keinen Fehler und schrieb ein vollständiges Protokoll.

Im Log stand der Widerspruch in fast jeder Zeile:

```
Bahn 4 Wurf 15: Lampen zeigen 0, Anzeige 9 (moeglich waren [9])
Bahn 5 Wurf 17: Lampen zeigen 0, Anzeige 9 ... Summe erwartet 0, Tafel zeigt 107
```

Aber nirgends stand, dass hier etwas **grundsätzlich** nicht stimmt.

## Ursache

Geladen war `1Spieltag.json` — eine Kalibrierung vom 1. September, also von
**vor** der Verkleinerung der Lampen-ROIs.

| | 04.09. (lief) | 07.09. (defekt) |
|---|---|---|
| Lampen-ROI (normiert) | 0,040 × 0,0375 | **0,080 × 0,075** |
| Ausschnitt im Bild | 8 × 7 px | **12 × 11 px** |
| Grundlinie | ~140 | ~140 |
| leuchtende Lampe | **250** | **203** |
| AN-Schwelle | 210 | 206 |
| erkannte Lampenzustände | 194 972 | **0** |

Der Detektor bildet den **Mittelwert** über den Ausschnitt (`core_percentile: 0`).
Bei 8 × 7 px füllt die leuchtende Lampe das Fenster fast aus → 250. Bei
12 × 11 px kommt ein dunkler Ring hinzu, der den Mittelwert auf 203 zieht —
knapp unter die Schwelle. Der Wertebereich war an **beiden** Enden gestaucht
(min 107,6 statt 0,0; max 202,9 statt 255,0), die klassische Signatur von
Mittelung über zu viel Fläche.

Die eigentliche Ursache ist aber nicht die falsche Datei — das war eine
Fehlbedienung, die jederzeit wieder vorkommen kann. Die Ursache ist, dass das
Programm **weitermachte, als sei nichts**.

### Die versteckte Kopplung

In `config/default.yaml` stand bereits, als Kommentar:

> `ACHTUNG: Dieser Wert gehoert zur Kalibrierung mit engen Lampen-ROIs. Mit
> einer Kalibrierung im alten Zuschnitt muss er zurueck auf 70.`

`core_percentile: 0` (Mittelwert) und die enge ROI-Größe sind also **gekoppelt**
— aber die Kopplung lebte nur in einem Kommentar. Eine Kalibrierungsdatei und
eine Konfigurationsdatei können unabhängig voneinander gewechselt werden, und
nichts prüfte, ob sie zusammenpassen.

## Fix

Ein Wachhund, der den **Widerspruch zweier unabhängiger Quellen** zählt:
`src/kegel_cv/analysis/lamp_watchdog.py`. Meldet je Bahn einmal als `ERROR`,
wenn `silent_failure_after` Würfe in Folge null Lampen bei einer Anzeige
größer null liefern. Die Analyse läuft weiter (P8).

Am echten Material gemessen:

| Lauf | Würfe | Widersprüche | längste Serie | Wachhund |
|---|---|---|---|---|
| 04.09. 12:31 | 706 | 0 | — | still |
| 04.09. 15:12 | 1677 | 2 | 1 | still |
| 07.09. 13:14 | 67 | 61 | 12–17 | **Alarm auf allen 4 Bahnen, erster nach Wurf 16** |

Die Lücke zwischen 1 und 12 ist breit genug, dass die Schwelle 5 nicht kritisch
ist.

## Die Lektion

**Ein Ergebnis von „null" ist zweideutig, und die Zweideutigkeit ist gefährlich.**
„Null Kegel gefallen" und „ich habe nichts gemessen" sehen im Datenmodell
identisch aus — beides ist `pins_count = 0`. Nur eines davon ist ein Ergebnis.
Solange beide gleich aussehen, ist ein Totalausfall von einem ruhigen Spiel
nicht zu unterscheiden.

**Daraus folgen drei Regeln:**

1. **Ein Detektor, der über einen längeren Zeitraum NIE anspricht, ist
   verdächtig — auch wenn jede Einzelmessung formal gültig ist.** Wo eine
   zweite Quelle existiert, gehört ihr Widerspruch ausgewertet und nicht nur
   protokolliert. Eine Warnung je Wurf ist keine Warnung; sie wird zur
   Tapete. Ein Befund über viele Würfe hinweg ist einer.

2. **Kopplungen zwischen Konfiguration und Kalibrierung müssen geprüft werden,
   nicht kommentiert.** `core_percentile: 0` setzt enge ROIs voraus. Stand nur
   im Kommentar. Ein Kommentar hält niemanden auf.

3. **Bei einem Ausfall zuerst die Spannweite messen, nicht die Schwelle
   verstellen.** Min 107,6 / max 202,9 gegen früher 0,0 / 255,0 hat den Fall in
   einem Schritt geklärt: gestauchter Wertebereich ⇒ zu viel Fläche gemittelt.
   Hätte man stattdessen die Schwelle gesenkt, wäre der Detektor scheinbar
   wieder gelaufen — und hätte fortan Rauschen für Lampen gehalten.

## Verwandt

- [[bug-020-bildguete-statt-zeitlicher-einigkeit]] — dieselbe Klasse: Eine
  Regel war strukturell wirkungslos, und es gab keine Meldung dafür, dass eine
  Bedingung nie erfüllt wurde. Dort lautete die Lehre bereits: *„Ein Filter,
  der nie greift, meldet sich nicht."* Hier ist es ein Detektor statt eines
  Filters — dieselbe blinde Stelle, eine Schicht tiefer.
- [[bug-017-verdeckung-im-fenster-gilt-als-leerer-wurf]] — ebenfalls ein Fall,
  in dem „nichts gemessen" als „null Kegel" gebucht wurde.
