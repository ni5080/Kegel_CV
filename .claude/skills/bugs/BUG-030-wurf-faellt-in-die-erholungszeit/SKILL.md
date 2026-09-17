---
name: bug-030-wurf-faellt-in-die-erholungszeit
description: >
  Verhindert verlorene Würfe, während sich eine festhängende Wache erholt.
  Laden bei Arbeit an der Tafelwache, an Verdeckungserkennung, an
  Selbstheilung mit Wartezeit -- und immer dann, wenn eine Erholungsfrist
  länger ist als das Ereignis, das sie verdeckt.
---

# BUG-030 — Der Wurf, der in die Erholungszeit fiel

| | |
|---|---|
| **Kategorie** | `DETECT` / Verdeckung |
| **Gefunden** | 2026-09-17, auf Nutzerhinweis |
| **Schweregrad** | **mittel** (0,8 % der Würfe; der Spielstand bleibt danach dauerhaft falsch) |
| **Regressionstest** | `test_wache_bremst_nicht_allein.py` |

## Symptom

Der Nutzer, beim Blick auf den laufenden Spieltag: *„Bei Spiel 3 nach ungefähr
01:07:30 stimmt Tafel 2 nicht, wir sind sehr konstant 5 hinten dran... das
wirkt auf mich wieder nach einem verlorenen Wurf."*

Es war einer. Bahn 2, Spiel 6: Das Werkzeug springt von Wurf 7 auf Wurf 9, und
der Rest bleibt für den ganzen Rest des Spiels konstant bei −7.

**Über den ganzen Lauf: 4 verlorene Würfe von 522 (0,8 %)**, alle mit demselben
Muster — eine Lücke von 1000 bis 2900 Frames zwischen zwei Buchungen, während
ein normaler Abstand 400 bis 600 beträgt. Das Werkzeug meldet sie bereits
selbst: „4 Grünzyklen ohne Wurfergebnis" — die Zahl stimmt exakt.

## Der Wurf war vollständig sichtbar

Das ist der Kern: Es fehlten keine Daten.

```
64:52  F97300  Ziffern 007 / 9 / 0054   liegend []
64:55  F97370  GRUEN AN
65:08  F97710  Ziffern 008 / 7 / 0054   liegend [1,2,3,4,6,7,9]   <- 7 Kegel
65:12  F97800  GRUEN AUS
65:21  F98030  Ziffern 008 / 7 / 0061   liegend []                <- Summe +7
```

Die Tafel zählt sauber durch (Wurfnummer 007 → 008, Kegelzahl 7, Summe
0054 → 0061), die Lampen zeigen genau diese sieben Kegel, und **keine einzige
Messung war unklar**. Beide Quellen waren sich einig.

## Ursache

```
F96857   Tafel verdeckt (Gruen-Score 0.0) -- Auswertung ausgesetzt
F97607   seit 750 Frames (30 s) verdeckt, Gruen-Score 75.0
F97945   Wache meldet Fremdes, das Personenmodell sieht dort niemanden
         -- Referenz vermutlich vor einer Bildverschiebung gelernt
F97945   Tafel war 1089 Frames verdeckt, ab hier wieder sichtbar
```

Die Tafelwache hing fest — dieselbe Lage wie in BUG-026. Die dort gebaute
Selbstheilung (`_pruefe_festhaengende_wache`) hat gegriffen und die Referenz
neu gelernt. **Sie kam nur zu spät.**

`wache_neustart_frames` steht auf **750**, und die Zahl ist gut begründet: Über
118 gemessene echte Verdeckungen lag der Median bei 30 Frames, die längste bei
250. 750 liegt sicher darüber, also löst die Heilung nie bei einer echten
Verdeckung aus.

Übersehen wurde dabei: **Ein ganzer Wurfzyklus passt in 750 Frames.** Dieser
dauerte 420 (F97374 bis F97794). Die Erholungsfrist ist damit länger als das
Ereignis, das sie verdeckt.

## Der Zeuge, der die ganze Zeit widersprach

Während des Einfrierens stand der **Grün-Score auf 75,0** — das steht wörtlich
in der Warnmeldung. Ein Mensch vor der Tafel drückt ihn auf nahe null; 75
heißt, die grüne Lampe war klar zu sehen.

Es sagten also zwei von drei Zeugen, dass nichts verdeckt ist:

| Zeuge | sagte |
|---|---|
| Grün-Score | 75,0 — Tafel klar sichtbar |
| Personenmodell | niemand da |
| **Tafelwache** | **Fremdes** |

Die Wache allein hielt die Bahn 1089 Frames lang an.

## Behebung

Der eigentliche Fund steckt im Kopf von `analysis/tafel_wache.py`, und er stand
dort die ganze Zeit:

> **WAS DAMIT NICHT GEMEINT IST**
> Diese Wache entscheidet **nichts** über Würfe. Sie schwärzt Bilder, die das
> Haus verlassen.

In der Verdeckungsbremse stand sie trotzdem — und mit **derselben Schwelle**
wie fürs Schwärzen (`wache_schwelle: 0.05`). Ein Wert für zwei sehr
verschiedene Fragen.

GEMESSEN am Stream vom 2026-09-17, Bahn 2, Referenz im Normalbetrieb gelernt:

| Fall | Abweichung |
|---|---|
| Normalbetrieb | 0,000 |
| **festhängende Referenz (dieser Fehler)** | **0,123 – 0,198** |
| halb verdeckt | 0,246 |
| alles schwarz | 0,551 |
| **dunkle Tafel am Streamende** | **0,622** |

Die beiden Gruppen liegen weit auseinander. `wache_bremse_schwelle: 0.40`
trennt sie mit Abstand nach beiden Seiten. Das Schwärzen bleibt bei 0,05 — ein
Bild zu viel zu schwärzen kostet nichts, ein Gesicht zu veröffentlichen schon.

Die **Erholung** der festhängenden Referenz hängt weiter am Schwärzungs-Flag:
Eine stehengebliebene Referenz soll geheilt werden, auch wenn sie nicht mehr
bremst — sonst schwärzt sie dauerhaft zu viel.

### Nachgemessen

**Fall B — der verlorene Wurf (F96300–98600):**

```
vorher   Tafel war 1089 Frames verdeckt      -> kein Wurf
nachher  Bahn 2: Wurf 8 erkannt -- 7 Kegel [1,2,3,4,6,7,9], VALID (0.80)
```

Genau die sieben Kegel, die Tafel (008/7/0054→0061) und Lampen gezeigt hatten.
Die Bremse arbeitet weiter: Sie greift in demselben Ausschnitt mehrfach
(Personenmodell 17–32 %), aber nur noch **5 bis 129 Frames** statt 1089.

**Fall A — die dunkle Tafel (F305000–312700):** 7701 Frames, vier Grünzyklen,
**0 Würfe**. Kein Phantomwurf ist durchgekommen.

**Einschränkung, offen benannt:** Der ursprüngliche Fall A (Streamende
2026-09-13, alles schwarz, Wache meldete 61–68 %) ist nicht mehr nachmessbar —
jener Stream-Link ist abgelaufen. Geprüft wurde an der dunklen Tafel des
heutigen Streams (0,622) und an einem künstlich geschwärzten Ausschnitt
(0,551). Beide liegen über der neuen Schwelle.

## Was daraus zu lernen ist

**Eine Erholungsfrist muss kürzer sein als das Ereignis, das sie verdeckt.**
Die 750 Frames wurden gegen die Länge echter Verdeckungen bemessen — richtig,
aber nur die halbe Frage. Die andere Hälfte: Was geht in dieser Zeit verloren?
Ein Wurfzyklus dauert 420 Frames, also fällt im schlimmsten Fall einer hinein.

**Eine Selbstheilung, die zu spät kommt, sieht aus wie keine.** Im Protokoll
steht „Tafel war 1089 Frames verdeckt, ab Frame 97945 wieder sichtbar" — das
liest sich wie ein geordneter Vorgang. Dass dabei ein Wurf verloren ging, steht
nirgends.
