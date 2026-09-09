---
name: BUG-015-aufzeichnung-endet-nicht
description: Am Ende einer Aufzeichnung erkennt die Stream-Quelle kein Ende, sondern verbindet endlos neu. Laden bei Arbeit an StreamVideoSource, Abrisserkennung, Neuverbindung oder wenn ein Lauf nicht von selbst endet.
---

# BUG-015 — Am Ende der Aufzeichnung endet der Lauf nicht

**Gefunden:** 2026-08-31 · **Schwere:** mittel · **Status:** behoben

## Was passiert ist

Der vollständige Lauf über den Spieltag 2026-08-29 (312 786 Frames) erreichte
Frame 312 784 — also praktisch das Ende — und blieb dann hängen:

```
23:59:41  Stream liefert seit 25 Versuchen nichts -- neu verbinden
23:59:46  Stream riss ab und wurde bei Frame 312784 fortgesetzt
23:59:47  Stream liefert seit 25 Versuchen nichts -- neu verbinden
23:59:53  Stream riss ab und wurde bei Frame 312784 fortgesetzt
...
```

Alle sieben Sekunden eine Runde, unbegrenzt. Der Lauf endete erst, als der
Rechner planmäßig heruntergefahren wurde.

## Warum

`StreamVideoSource` behandelt „keine Frames mehr" grundsätzlich als Abriss —
für einen Livestream ist das richtig, dort ist eine Lücke Alltag. Der
Rücksprung an die alte Stelle (BUG-014) gelingt danach sogar, weil die Quelle
tatsächlich bei 312784 steht. Nur kommt von dort nie wieder ein Frame, weil das
Material zu Ende ist.

Die Quelle KENNT ihre Länge — sie meldet beim Öffnen 312 786 Frames und
protokolliert es sogar. Sie nutzt diese Kenntnis nur nicht.

## Schaden

Begrenzt, aber ärgerlich: Die Wurfdaten sind vollständig (sie werden laufend
geschrieben), aber die **Schlussbilanz fehlt** — Zahl der Grünzyklen ohne
Wurfergebnis (die BUG-008-Kontrolle), Statusverteilung, verlorene Frames. Genau
die Zahlen, für die der Lauf gemacht wurde, entstehen erst am Ende.

Bei einem unbeaufsichtigten Lauf dreht die Schleife außerdem beliebig lange.

## Behebung

`StreamVideoSource._ist_abgespielt()`: Meldet die Quelle eine Länge und steht
der Lesezeiger innerhalb von `stream_end_tolerance_frames` (100) vor dem Ende,
ist das kein Abriss, sondern das Ende — `read()` liefert `None`, ohne dass
überhaupt eine Neuverbindung versucht wird.

Die Prüfung sitzt bewusst **vor** dem Verbindungsaufbau, nicht dahinter: Der
alte Endcheck in `_wieder_aufsetzen()` existierte bereits, griff aber erst
nach der teuren Neuverbindung — und wegen der fehlenden Toleranz bei 312 784
von 312 786 nie. Beide Stellen benutzen jetzt denselben Maßstab.

Für einen echten Livestream ändert sich nichts: Dort meldet die Quelle keine
Länge, und jede Lücke bleibt ein Abriss.

Tests: `tests/unit/test_stream_source.py::TestBug015AufzeichnungEndetNicht`
(4). Gegengeprüft: Ohne die Toleranz fallen zwei davon.

## Regel

**Wer eine Länge kennt, muss sie auch benutzen.** Die Quelle protokollierte
beim Öffnen „die Quelle meldet 312786 Frames (209 min)" und lief trotzdem
endlos weiter, als sie dort ankam.
