---
name: bug-014-aufzeichnung-beginnt-nach-abriss-von-vorn
description: >
  Verhindert VIDEO-Bug: Hinter einer m3u8-Adresse steckt oft eine Aufzeichnung,
  keine Live-Uebertragung. Reisst die Verbindung ab, beginnt sie beim Neuaufbau
  wieder bei Frame 0 -- der eigene Frame-Index laeuft aber weiter, und dasselbe
  Material wird ein zweites Mal als neue Wuerfe gebucht. Laden bei Arbeit an
  StreamVideoSource, Neuverbindung, Frame-Indizes oder wenn Ergebnisse doppelt
  in der Datenbank stehen.
---

# BUG-014 — Die Aufzeichnung begann nach jedem Abriss wieder von vorn

| | |
|---|---|
| **Kategorie** | `VIDEO` |
| **Gefunden** | 2026-08-29 (Schaden), Ursache gemessen 2026-08-30 |
| **Schweregrad** | **kritisch** — 1693 Wiederholungen in der Datenbank |
| **Regressionstest** | `tests/unit/test_stream_source.py::TestAbrissMittenInDerAufzeichnung`, `::TestNeuanfangDerQuelle` |

## Symptom

Der Nutzer: *„leider ist die Aufzeichnung knapp über 3 Stunden lang... warum
wiederholt sie sich nach rd. 46:41 wieder?"*

Im Lauf vom 2026-08-29 12:31 standen **3210 Wuerfe** statt 1517 — 1693 davon
waren Wiederholungen, alle an Supabase gesendet.

## Was die Messung ergab

**Die Aufzeichnung selbst ist einwandfrei.** Die Playlist geprueft:

```
#EXT-X-PLAYLIST-TYPE:VOD     3128 Segmente, lueckenlos 0..3127
Summe EXTINF: 12511,44 s  =  3:28:31
PDT 10:19:30 -> 13:47:58     0 Abweichungen, 0 Discontinuity
```

**Die 46:41 sind keine Eigenschaft des Videos.** Der entscheidende Beleg:
Vorschau und Analyse lasen dieselbe URL parallel und sprangen zur **selben
Wandzeit** zurueck — aber an **verschiedenen Videopositionen**:

| Leser | Wandzeit des Abrisses | Videoposition |
|---|---|---|
| Vorschau (`gui.player`) | 22:24:40 | Frame 98601 = **65:44** |
| Analyse (Worker) | 22:24:47 | Frame 70033 = **46:41** |

Waere es eine Eigenschaft des Videos, muessten beide an derselben Stelle
umspringen. Gemeinsam ist nur der Zeitpunkt: **60,6 Minuten nach dem
Verbindungsaufbau** (Lauf-Start 21:23:43). Beide protokollierten den Abriss:

```
22:24:40 WARNING Stream liefert seit  8 Versuchen nichts -- neu verbinden
22:24:47 WARNING Stream liefert seit 25 Versuchen nichts -- neu verbinden
```

Die 46:41 sind schlicht: 60,6 min Wandzeit x 0,77 (so schnell lief die Analyse).

Der Abstand ist ueber den ganzen Lauf **exakt konstant 70033 Frames**, auf allen
vier Bahnen, ohne Jitter — also stuendlich ein Abriss bei gleichbleibendem Tempo.

## Ursache

`_neu_verbinden()` oeffnete `cv2.VideoCapture(url)` neu. Bei einer VOD-Playlist
beginnt das **bei Segment 0**. Der eigene Frame-Index lief monoton weiter,
also erschien dasselbe Material als neue Wuerfe.

Das Projekt hatte den Rueckwaertssprung ausdruecklich verboten — `seek()` gibt
waehrend der Analyse immer False, damit gebuchte Wuerfe nicht erneut kommen.
**Abgesichert war aber nur, dass WIR springen. Dass die QUELLE es von sich aus
tut, war nicht bedacht, obwohl es derselbe Schaden ist.**

## Der erste Reparaturversuch war zu schwach

Eine Bilderkennung, die **nur nach einer Neuverbindung** prueft. Sie half der
Vorschau und schwieg bei der Analyse. Zwei Fehler:

1. **An das falsche Ereignis gebunden.** Die Pruefung lief nur nach einem
   *bemerkten* Abriss.
2. **Aehnlichkeit statt Reihenfolge.** Ein einzelner passender Fingerabdruck ist
   kein Beleg — eine stehende Szene liefert denselben immer wieder.

## Behebung

**Erste Verteidigung — an die alte Stelle zurueckspringen.** Meldet die Quelle
eine Laenge (`CAP_PROP_FRAME_COUNT > 0`), ist sie eine Aufzeichnung, und der
Sprung ist framegenau. Gemessen 2026-08-30:

```
FRAME_COUNT: 312786  (= 3:28:31, deckt sich mit der Playlist)
set(POS_FRAMES, 50) -> Fingerabdruck == sequentiell gelesener Frame 50
```

Gegenprobe am echten Stream, Abriss bei Frame 200 erzwungen:

```
deckungsgleich: 60   abweichend: 0   fehlend: 0
davon Material vom ANFANG der Quelle: 0
```

**Bei einer Aufzeichnung gibt es nur zwei zulaessige Ausgaenge:** wieder
aufsetzen — oder aufhoeren. Weiterlesen ist keiner. Misslingt der Sprung, endet
die Auswertung.

**Zweite Verteidigung — Bilder wiedererkennen, dauernd und der Reihe nach.**
Entscheidend ist nicht die Aehnlichkeit, sondern die **aufsteigende Folge**:
eine Spielpause liefert denselben Abdruck wiederholt, ein Neuanfang liefert die
gespeicherten Abdruecke in aufsteigender Reihenfolge.

## Regel

**Ein verbotener Sprung ist erst dann verhindert, wenn auch die Gegenseite ihn
nicht ausfuehren kann.** Wer eine Invariante nur im eigenen Code absichert, hat
sie nicht abgesichert — er hat sie nur aufgeschrieben.

Und: **Zwei Leser derselben Quelle sind ein Messinstrument.** Dass Vorschau und
Analyse an verschiedenen Videopositionen, aber zur selben Wandzeit umsprangen,
hat die Ursache in einem Schritt von „liegt am Video" auf „liegt an der
Verbindung" umgestellt.

## Offen

**Warum reisst die Verbindung nach rund einer Stunde ab?** Die Signaturen sind
es nachweislich nicht (Playlist und Chunks 2026-08-30 dekodiert: rund 12 Stunden
gueltig). Siehe `docs/OPEN_QUESTIONS.md` Q11. Fuer die Auswertung ist es nicht
mehr kritisch — der Wiedereinstieg traegt den Fall.
