---
name: bug-012-stream-blockiert-die-oberflaeche
description: >
  Verhindert GUI-Bug: Ein blockierender Lesevorgang auf einer Netzwerkquelle im
  GUI-Thread friert die gesamte Oberflaeche ein. Laden bei Arbeit an
  Videoquellen im Player, an Streams, an QTimer-gesteuerten Schleifen oder wenn
  die Anwendung "abstuerzt" beziehungsweise nicht mehr reagiert.
---

# BUG-012 — Der Stream legte die Oberfläche lahm

| | |
|---|---|
| **Kategorie** | `GUI` |
| **Gefunden** | 2026-08-26, vom Nutzer beim Kalibrieren eines Livestreams |
| **Schweregrad** | **hoch** — die Anwendung reagierte nicht mehr |
| **Regressionstest** | `tests/unit/test_stream_reader.py` |

## Symptom

„das Programm ist abgestürzt." Nach dem Verbinden mit einem Livestream und rund
zwei Minuten Kalibrierarbeit reagierte die Oberfläche nicht mehr.

## Was das Protokoll zeigte

```
22:53:13  Stream geoeffnet: 960x540
22:53:43  Kalibrierung Bahn 1 gestartet
22:55:43  Kalibrierung gespeichert
[WARN] Stream timeout triggered after 30005 ms
[WARN] Stream timeout triggered after 30000 ms
[WARN] Stream timeout triggered after 30007 ms
```

## Ursache — drei Fehler, die zusammenwirkten

**1. Der Player liest im GUI-Thread.** Er läuft an einer `QTimer`; `read()`
blockiert dort die gesamte Oberfläche. Bei einer Datei fällt das nie auf — eine
Datei antwortet in Mikrosekunden. Bei einer Netzwerkquelle sind es Sekunden, im
Fehlerfall Minuten.

**2. Kein Zeitlimit gesetzt.** FFmpeg wartet ohne
`CAP_PROP_READ_TIMEOUT_MSEC` **30 Sekunden** je Leseversuch. Bei acht
Wiederholungen sind das über vier Minuten Blockade.

**3. Die Verbindung lief weg.** Während des Kalibrierens war die Wiedergabe
pausiert, es wurde also nicht gelesen — und ein Livestream wartet nicht.

## Richtig

Ein eigener Lesefaden (`gui/player.py::_StreamReader`), der **durchgehend**
liest und nur den jüngsten Frame aufbewahrt. Die Oberfläche holt ihn ab, ohne je
zu warten.

Das löst alle drei Punkte zugleich: Die Oberfläche blockiert nie, die Verbindung
bleibt in Betrieb, und es entsteht kein Rückstand.

Vom Nutzer kam dazu die entscheidende Vorgabe: **„während des Kalibrierens darf
das Video gerne weiterlaufen — ein Livestream ist ein Livestream."** Mein erster
Ansatz war das Gegenteil gewesen: die Verbindung während der Pause schlafen
legen. Das hätte die Symptome gelindert und die Sache falsch modelliert — ein
Livestream, den man anhält, ist keiner mehr.

Zusätzlich gesetzt: `CAP_PROP_OPEN_TIMEOUT_MSEC` und
`CAP_PROP_READ_TIMEOUT_MSEC`, damit ein Fehlversuch in Sekunden auffliegt statt
in einer halben Minute.

## Ein zweiter Fehler, den erst der Test fand

```python
self._stop = threading.Event()      # FALSCH
```

`threading.Thread` besitzt eine interne Methode `_stop()`, die `join()` aufruft.
Ein Attribut gleichen Namens überdeckt sie, und **jedes** `join()` bricht ab mit
`TypeError: 'Event' object is not callable`. Im Betrieb wäre das bei jedem
Schließen des Videos passiert.

Aufgefallen ist es nur, weil der Test den Faden auch wieder anhält. **Ein Test,
der nur den Normalfall durchspielt, hätte das nie gesehen.**

## Die Regeln

> **Was über ein Netz geht, gehört nie in den GUI-Thread.** Bei einer lokalen
> Quelle fällt der Unterschied nicht auf — genau deshalb rutscht er durch.

> **Ein Livestream wartet nicht.** Wer ihn anhält, sammelt Rückstand oder
> verliert die Verbindung. Die Quelle muss laufen, auch wenn niemand hinsieht.

> **Attributnamen mit führendem Unterstrich in einer Basisklasse sind belegt.**
> Vor `self._x = ...` in einer abgeleiteten Klasse prüfen, ob `_x` dort schon
> etwas bedeutet.

## Wo gilt das noch?

- [x] `gui/player.py` — Lesefaden
- [x] `StreamVideoSource` — Zeitlimits
- [ ] **`analysis_worker.py`**: liest bereits in einem eigenen QThread, also
      unkritisch. Aber: Er hat KEINEN Lesefaden — bei einem Aussetzer wartet er
      auf das Zeitlimit und verliert dabei Frames. Ob das genügt, ist an einem
      echten Stream noch nicht gemessen.
- [ ] `sinks/` — der Versand hat seinen eigenen Faden (siehe `queued.py`),
      dort ist dieselbe Regel bereits angewandt.
