---
name: bug-026-wache-haengt-an-einer-bildaenderung
description: >
  Verhindert dauerhaft eingefrorene Bahnen: Eine bewachte Referenz, die nur
  unterhalb einer Schwelle nachlernt, kann sich von einer ECHTEN Aenderung nie
  mehr erholen. Laden bei Arbeit an der Tafelwache, an gleitenden Referenzen,
  Hintergrundmodellen, adaptiven Schwellen -- ueberall dort, wo etwas
  "vorsichtig nachlernt".
---

# BUG-026 — Der Schutz, der sich selbst einsperrt

| | |
|---|---|
| **Kategorie** | `DETECT` / Zustand |
| **Gefunden** | 2026-09-14, beim Nachmessen einer auffaelligen Kostenzahl |
| **Schweregrad** | **hoch** (eine Bahn meldet nie wieder einen Wurf, ohne dass etwas danach aussieht) |
| **Regressionstest** | `test_personen_modell.py::TestDieFesthaengendeWacheWirdGeloest` |

## Symptom

Bahn 5 des Hallenmitschnitts meldete **13 000 Frames lang** nichts. Im
Protokoll stand die ganze Zeit dieselbe Warnung:

```
Bahn 5: seit 2250 Frames (90 s) verdeckt, Gruen-Score 73,4
-- kommt hier nichts mehr, passt womoeglich die Kalibrierung nicht zur Tafel
```

Ein Gruen-Score von 73,4 heisst: Die Lampe ist klar AN und gut sichtbar. Etwas
behauptete, die Tafel sei verdeckt, waehrend sie offen dalag.

Aufgefallen ist es nicht als Fehler, sondern als **Kostenzahl**: Das neue
Personenmodell lief in 94 % aller Frames statt in den erwarteten 20 %.

## Ursache

`TafelWache` haelt eine Referenz der eigenen Tafel und lernt sie NUR unterhalb
`nachlernen_unter` (10 %) nach. Das ist der Kern des Verfahrens und richtig --
so kann kein Mensch, der davorsteht, in die Referenz hineinwandern (BUG-025).

Genau diese Bewachung macht sie aber unfaehig, sich von einer echten Aenderung
zu erholen. GEMESSEN, Abweichung auf Bahn 5:

```
F0   bis F215    0,0 bis 3,4 %     Referenz wird gelernt
F215 bis F220    3,4 -> 13,0 %     <- Sprung ueber die Nachlernschwelle
F220 bis F13530  25,2 %            Median = Maximum, voellig unbewegt
```

Die Referenz war in den ersten Frames gelernt worden, und in denen war die
Szene untypisch — jemand hatte hinten die Klappe geoeffnet. Danach kehrte die
Tafel in ihren Normalzustand zurueck, die Referenz nicht. Das Differenzbild
(`debug/bahn5_referenz.png`) zeigt doppelte Kanten an jedem Rahmen: derselbe
Ausschnitt, um wenige Pixel versetzt.

**Die Wache hatte recht** — die Tafel sah nicht mehr so aus wie ihre Referenz.
Sie konnte nur nicht wissen, dass die Referenz das Falsche zeigte.

## Warum es so lange unentdeckt blieb

Ein eingefrorenes Bahnsegment sieht von aussen aus wie eine Bahn, auf der
gerade nicht gespielt wird. Es gibt keinen Fehler, keine Ausnahme, keinen
roten Test. Die Warnung im Protokoll war da und nannte sogar die richtige
Richtung ("passt womoeglich die Kalibrierung nicht") — nur eben die falsche
Ursache, und niemand ist ihr nachgegangen.

## Die Lehre

**Ein Zustand, der sich nur unter einer Bedingung aendern darf, braucht immer
einen zweiten Weg heraus.** Sonst ist die Schutzbedingung zugleich eine Falle:
Wer erst einmal jenseits der Schwelle steht, kommt nie zurueck.

Das Muster ist nicht auf die Tafelwache beschraenkt. Es steckt in jedem
gleitenden Mittel mit Ausreisser-Schutz, in jedem Hintergrundmodell mit
Lernsperre, in jeder adaptiven Schwelle, die "verdaechtige" Messwerte
verwirft. Die Frage lautet jedes Mal:

> **Was passiert, wenn die Aenderung echt war?**

Und der Ausweg darf nicht dieselbe Groesse benutzen, die feststeckt. Er
braucht einen **unabhaengigen Zeugen**. Hier ist es das Personenmodell:

| | Wache meldet Fremdes | Modell sieht einen Menschen |
|---|---|---|
| Bahn 2 | 1,3 % | 4,2 % |
| Bahn 3 | 0,0 % | 0,0 % |
| Bahn 4 | 0,0 % | 0,0 % |
| **Bahn 5** | **98,3 %** | **0,6 %** |

Wenn ueber 750 Frames dauerhaft etwas gemeldet wird und ein unabhaengiger
Zeuge sagt "da ist niemand", dann liegt es nicht an dem, was davorsteht.

## Der Fix

`TafelWache.vergiss_referenz()` plus
`LaneProcessor._pruefe_festhaengende_wache`. Drei Bedingungen, alle noetig:

1. **Das Modell ist geladen.** Ohne Zeugen passiert nichts — lieber eine
   eingefrorene Bahn als ein Gesicht in der Datenbank.
2. **Es hat ueber die ganze Strecke keinen Menschen auf DIESER Tafel gesehen.**
3. **Die Strecke ist laenger als jede gemessene echte Verdeckung.** GEMESSEN
   ueber denselben Lauf: 118 Verdeckungen, Median 30 Frames, 99. Perzentil
   142, laengste 250. Die Schwelle steht auf 750, dem Dreifachen.

## Pruefmuster fuer die Zukunft

- Wer eine Referenz, ein Modell oder eine Schwelle "vorsichtig" nachfuehrt,
  schreibt im selben Zug den Weg heraus — und einen Test dafuer.
- Eine Dauerwarnung im Protokoll ist ein Befund, kein Rauschen. Wenn dieselbe
  Zeile hundertmal kommt, stimmt etwas nicht mit dem, was sie meldet.
- Eine auffaellige **Kostenzahl** kann ein Korrektheitsproblem sein. Hier war
  "das Modell laeuft viel zu oft" das einzige Signal, das laut genug war.
