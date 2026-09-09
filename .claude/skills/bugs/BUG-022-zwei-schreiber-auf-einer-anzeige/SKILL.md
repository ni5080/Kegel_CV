---
name: bug-022-zwei-schreiber-auf-einer-anzeige
description: >
  Verhindert GUI-Bug: Waehrend der Analyse malten Player UND Analyse-Worker in
  dieselbe Videoanzeige, weil die Wiedergabe nur angehalten, aber nicht
  gesperrt war. Das Bild sprang zwischen zwei Stellen der Aufnahme hin und her.
  Laden bei Arbeit an der Videoanzeige, an Vorschaubildern, an Zustaenden, in
  denen zwei Quellen dasselbe Widget bedienen, und immer dann, wenn ein
  Bedienelement waehrend eines laufenden Vorgangs erreichbar bleibt.
---

# BUG-022 — Zwei Schreiber auf einer Anzeige

| | |
|---|---|
| **Kategorie** | `GUI` |
| **Gefunden** | 2026-09-07, durch eine Bildschirmaufnahme des Nutzers |
| **Schweregrad** | **mittel** (Ergebnisse blieben richtig, die Anzeige war unbrauchbar) |
| **Regressionstest** | `test_analyse_sperrt_wiedergabe.py` (12 Tests) |

## Symptom

> „jetzt flackert mein Bild auch wieder zwischen verschiedenen Frames hin und
> her... nur weil ich Analyse starten geklickt habe"

## Ursache

Aus der Aufnahme gemessen. Auf **einem** Standbild standen gleichzeitig:

```
Overlay oben links:   Frame 2898   t=115.92s      <- Analyse
Statusleiste unten:   Frame 2240 / 0  t = 89.60 s <- Player
```

Über mehrere Bilder hinweg liefen in der Statusleiste **zwei Reihen
abwechselnd**, und beide schritten fort:

| Analyse | 2880 · 2895 · 2900 · 2904 · 2909 · 2915 · 2921 · 2925 · 2929 · 2934 · 2940 · 2949 |
|---|---|
| **Player** | **2230 · 2234 · 2282** (rund 650 Frames = 26 s zurück) |

`_start_analysis` ruft zwar `player.pause()`, aber `pause()` hält nur den
Anzeige-Timer an. **Gesperrt wurde nichts.** Ein Druck auf „Play" oder die
Leertaste startete die Wiedergabe wieder — und ab da schrieben `_on_frame`
(Player) und `_on_preview` (Worker) abwechselnd in dasselbe `video_view`.
Jeder Player-Frame riss das Bild 26 Sekunden zurück, der nächste Vorschau-Frame
wieder nach vorn.

Erschwerend: Player und Worker öffnen **je eine eigene Stream-Verbindung**
(zwei `Stream geoeffnet`-Zeilen im Log, 20 Sekunden auseinander). Die beiden
stehen deshalb zwangsläufig an verschiedenen Stellen derselben Aufnahme.

## Fix

Drei Stellen, weil eine allein nicht reicht:

1. **`_on_frame` verwirft Player-Frames**, solange `_analyse_aktiv` gilt. Die
   harte Sperre — sie greift auch, wenn ein Frame von anderer Stelle kommt.
2. **`_update_controls` sperrt Play/Vor/Zurück und den Schieber** während der
   Analyse. Das erklärt sich dem Nutzer, statt Klicks stumm zu verschlucken.
3. **`keyPressEvent` sperrt Leertaste und Pfeiltasten.** Ohne das ließe sich
   die Sperre mit der Tastatur umgehen — gesperrte Knöpfe halten keine Taste
   auf.

Dazu ein eigenes Kennzeichen `_analyse_aktiv` statt `self._worker is not None`:
Der Worker wird nach dem Lauf **nie zurückgesetzt**, die Wiedergabe wäre sonst
für immer gesperrt gewesen. `isRunning()` wiederum ist kurz nach `start()` noch
falsch. Und `_slider_erlaubt` merkt sich, ob der Schieber überhaupt je erlaubt
war — bei einem Stream nicht, dort hätte ein blindes `setEnabled(True)` nach
dem Lauf Erwartungen geweckt, die die Quelle nicht erfüllt.

**Gegenprobe:** Mit entfernten Sperren fallen 4 der 12 Tests. Mit Sperren alle
grün.

## Die Lektion

**„Angehalten" ist nicht „gesperrt".** `pause()` beschreibt einen Zustand, den
der Nutzer im nächsten Moment wieder ändern darf. Wer eine Ressource exklusiv
braucht, muss sie sich nehmen — nicht darauf bauen, dass der Nutzer sie in Ruhe
lässt.

**Drei Fragen, wenn zwei Quellen ein Widget bedienen könnten:**

1. *Wer besitzt es gerade?* Ein Widget mit zwei Schreibern hat keinen Besitzer,
   sondern einen Wettlauf. Der Gewinner ist, wer zuletzt schrieb.
2. *Kommt man an den gesperrten Weg vorbei?* Ein deaktivierter Knopf hält
   Tastenkürzel, Menüeinträge und Programmaufrufe nicht auf. Die Sperre gehört
   an die Stelle, die tatsächlich schreibt — die Bedienelemente sind nur die
   Höflichkeitsform.
3. *Woran erkennt man den Zustand?* `self._worker is not None` sah nach einem
   Kennzeichen aus, war aber keines: nach dem Lauf blieb es stehen. Ein
   Zustand, der nur gesetzt und nie zurückgenommen wird, ist kein Zustand.

## Verwandt

- [[bug-021-lampen-stumm-ohne-warnung]] — am selben Tag, dieselbe Wurzel in
  anderer Gestalt: Etwas lief offensichtlich falsch, und das Programm sagte es
  nicht. Dort ein stummer Detektor, hier eine Anzeige, die sich selbst
  widerspricht — auf einem Bild standen zwei verschiedene Frame-Nummern.
