---
name: messen-vor-bauen
description: >
  Arbeitsregel: Vor jeder Änderung an einem Erkennungsverfahren steht eine
  Messung, die die Änderung trägt — und zwar über den GESAMTEN Datenbestand,
  nicht nur über die auffälligen Fälle. Laden, bevor Schwellwerte, Messzeitpunkte,
  Aggregationsfenster oder Erkennungslogik geändert werden, und immer dann, wenn
  eine Erklärung plausibel klingt, aber nicht belegt ist.
---

# Messen vor Bauen

> „aber erst messen dann bauen, oder?" — Nutzer, 2026-08-25

Das ist Prinzip P1 dieses Projekts. Es steht hier noch einmal als eigener Skill,
weil es in diesem Projekt bereits **dreimal** verletzt wurde — jedes Mal von mir,
jedes Mal mit Kosten.

## Die drei Fälle

| Was ich tat | Was es kostete |
|---|---|
| Aus „Bahn 2 und 5 sind schlechter" auf schlechte Ziffernrahmen geschlossen | Der Nutzer hat 16 Ziffern neu eingerahmt. Ergebnis: **keine Verbesserung.** Die Rahmen waren nie die Ursache. |
| Die Feinausrichtung auf höchste Confidence optimiert | Confidence misst Musterschärfe, nicht Richtigkeit. Aus „001" wurde „081", ganze Bahnen bekamen falsche Wurfnummern. |
| Den Blink-Fix über zehn Frames aggregiert | Die Blinkperiode war **geschätzt**. Gemessen sind die Dunkelphasen bis 15 Frames lang — das Fenster war zu kurz und der Fehler blieb. |

Gemeinsames Muster: **Aus einer Korrelation wurde eine Ursache.** In allen drei
Fällen hätte eine Messung von zwanzig Minuten die Arbeit von Stunden gespart.

## Die Regel

Bevor eine Änderung an einem Erkennungsverfahren gebaut wird:

1. **Die vermutete Ursache belegen.** Nicht „X korreliert mit dem Fehler",
   sondern „X erzeugt den Fehler, hier ist die Messung".
2. **Beide Varianten über den GESAMTEN Bestand vergleichen** — nicht nur über
   die auffälligen Fälle. Wer sechs Fälle repariert und vierhundert nicht prüft,
   weiß nicht, was er angerichtet hat.
3. **Die Wahrheit benennen, gegen die gemessen wird.** In diesem Projekt: die
   Anzeigetafel im Standbild, die Summendifferenz, oder die Angabe des Nutzers.
   Ohne benannte Wahrheit ist jede Quote eine Selbstbestätigung.

## Was als Beleg zählt

| taugt | taugt nicht |
|---|---|
| Zeitreihe über hunderte Frames | ein Standbild |
| A/B über alle Würfe, gegen eine benannte Wahrheit | „ist besser geworden" |
| Vergrößerter Blick auf den Ausschnitt | Schluss aus der Statistik allein |
| Aussage des Nutzers über die Anlage | meine Annahme über die Anlage |

Die vierte Zeile hat sich mehrfach als die wertvollste erwiesen: Räumen, die
30-Wurf-Spiele, der späte Zeitpunkt der Summe und der zeitliche Ablauf eines
Wurfs kamen alle vom Nutzer — und keine dieser Erkenntnisse wäre aus den Daten
allein sicher ableitbar gewesen.

## Werkzeuge dafür

```bash
.venv/Scripts/python.exe tools/run_full_analysis.py [VIDEO] [KALIBRIERUNG]
```

```bash
.venv/Scripts/python.exe tools/report_full_analysis.py ALT.json NEU.json
```

`report_full_analysis.py` mit zwei Dateien stellt zwei Läufe gegenüber — das ist
der A/B-Vergleich aus Punkt 2. Ein Lauf über das 52-Minuten-Video dauert rund
13 Minuten; das ist der Preis für eine belastbare Aussage und fast immer
billiger als eine falsche Änderung.

Für gezielte Fragen lohnt ein eigenes Messskript neben diesen beiden — etwa
`tools/measure_measurement_point.py`, das zwei Messzeitpunkte über alle Würfe
gegeneinander stellt, ohne am Produktivpfad etwas zu ändern.
