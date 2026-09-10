---
name: bug-023-funktion-nie-ausgefuehrt
description: >
  Verhindert GUI-Bug: Eine gebaute Funktion lief nie, weil ihr Aufrufort zu
  früh liegt (Qt-Signal `opened` kommt VOR dem ersten Frame) und ein früher
  `return` jeden weiteren Fehler darin verdeckte. Laden bei Arbeit an
  Qt-Signalreihenfolge, `_on_video_opened`, Wächterklauseln mit stillem
  `return`, oder wenn eine Funktion „gebaut, aber ohne Wirkung" ist.
---

# BUG-023 — Gebaut, gepusht, nie ausgeführt

| | |
|---|---|
| **Kategorie** | `GUI` |
| **Gefunden** | 2026-09-10, durch die Nutzeraussage *„es fehlt die Bibliothek"* |
| **Schweregrad** | **hoch** (ein ganzes Feature war wirkungslos, mit grünen Tests daneben) |
| **Regressionstest** | `test_auto_kalibrieren.py::TestBibliothekWirdGefunden`, `::TestBilderSammeln` |

## Symptom

Am Vortag wurde die Tafelbibliothek gebaut und mit dem Commit *„Tafelbibliothek:
bekannte Bauarten beim Laden selbst erkennen"* abgeschlossen — 795 Tests grün.
Der Nutzer öffnete einen Stream und sah: **nichts**. Kein Vorschlag, keine
Meldung, kein Fehler.

## Ursache — zwei Fehler hintereinander, der zweite unsichtbar

```python
# main_window._on_video_opened(...)
self._pruefe_tafeltyp()

def _pruefe_tafeltyp(self):
    frame = self.player.current_frame
    if frame is None:
        return                                    # (1) hier ging es IMMER raus
    ordner = self.cfg.resolve_path(...)            # (2) AttributeError
```

**(1) Der Aufrufort liegt zu früh.** `VideoPlayer.load()` sendet das Signal,
bevor es den ersten Frame liest:

```python
self.opened.emit(source.info)
self.step_forward()        # erst hier entsteht current_frame
```

`current_frame` ist zu diesem Zeitpunkt **immer** `None`. Die Wächterklausel
griff bei jedem einzelnen Aufruf.

**(2) `AppConfig` hat kein `resolve_path`** — die Methode heißt `resolve`. Der
Aufruf hätte mit `AttributeError` abgebrochen. Er wurde nie erreicht, weil (1)
vorher aussteigt.

**Das ist die eigentliche Bosheit:** Die stille Wächterklausel hat den zweiten
Fehler *konserviert*. Wäre (1) nicht gewesen, hätte Qt beim ersten Öffnen eine
Ausnahme in die Konsole geschrieben und der Fehler wäre in Sekunden gefunden.

## Warum die Tests das nicht fanden

Für `_pruefe_tafeltyp` existierte **kein einziger Test**. Getestet war die
Bibliothek darunter (`test_board_library.py`, alles grün) — also die Zutaten,
nicht das Gericht. Die grünen Tests waren dabei nicht falsch, nur an der
falschen Stelle: Sie belegten, dass die Erkennung *funktioniert*, nicht, dass
sie *aufgerufen wird*.

## Fix

Die Prüfung hängt nicht mehr an einem Signal, sondern an einem Knopf, den der
Nutzer drückt — da ist garantiert ein Bild da. `resolve_path` → `resolve`.
Beides mit Tests, die die **Verdrahtung** prüfen, nicht die Rechenkerne.

## Regel

> **Eine Wächterklausel, die still aussteigt, ist eine Wette darauf, dass der
> Zustand irgendwann eintritt.** Wenn er es nie tut, sieht das Feature aus wie
> gebaut und ist es nicht.

Konkret für dieses Projekt:

| Frage | Warum sie zählt |
|---|---|
| **Wann feuert dieses Signal — vor oder nach dem, was ich brauche?** | Qt-Signale tragen ihren Zeitpunkt nicht im Namen. `opened` heißt nicht „bereit". |
| **Kann ich beweisen, dass die Funktion überhaupt lief?** | Ein Test auf den Rechenkern beweist das nicht. Es braucht einen Test auf den Aufruf. |
| **Was passiert nach dem frühen `return`?** | Alles dahinter ist ungetesteter Code, egal wie oft die Suite grün ist. |

## Verwandt

* **BUG-004** (dokumentierter Startbefehl nie ausgeführt) — dieselbe Familie:
  etwas existiert auf dem Papier und läuft nicht.
* **BUG-020 / BUG-021** — „ein Filter, der nie greift, meldet sich nicht."
  BUG-023 ist die Stufe davor: *eine Funktion, die nie läuft, meldet sich auch
  nicht.*

## Gegenprobe, die den Fehler zeigt

```python
def test_der_mitgelieferte_typ_ist_dabei(self, fenster):
    # scheitert mit AttributeError, solange resolve_path drinsteht
    assert "FUNK_klassisch" in [t.name for t in fenster._tafeltypen()]
```
