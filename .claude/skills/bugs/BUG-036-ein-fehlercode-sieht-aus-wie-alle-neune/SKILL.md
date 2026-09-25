---
name: bug-036-ein-fehlercode-sieht-aus-wie-alle-neune
description: >
  Die Tafel zeigt Störungen als Muster aus dauerleuchtenden und blinkenden
  Kegellampen -- die Vereinigung darüber ergibt „alle neune". Laden bei
  Arbeit an `aggregate_pin_readings`, am Messfenster der Lampen, an der
  Prämisse „eine Lampe kann nicht falsch leuchten".
---

# BUG-036 — Ein Fehlercode sieht aus wie „alle Neune"

| | |
|---|---|
| **Kategorie** | `ANALYSE` / Lampenaggregation |
| **Gefunden** | 2026-09-25, vom Nutzer erklärt |
| **Schweregrad** | hoch (2 Spiele je +10 Kegel) |
| **Belege** | `debug/streitfaelle/streit_bahn5_f137732.gif` (Nachbarfall), Messung in `docs/VIDEO_ANALYSIS.md`, 2026-09-25 |
| **Werkzeug** | `tools/messe_blinken.py` |
| **Noch nicht behoben** | ja — die Erkennung ist gemessen, aber nicht gebaut |

## Symptom

Zwei Spiele auf Bahn 4 lagen je **10 Kegel zu hoch**. Jedes Mal dasselbe
Muster: zwei aufeinanderfolgende Würfe als „alle Neune" gebucht, während die
Tafelsumme 7 und dann 1 zählte.

## Was der Nutzer erklärt hat

*„Bei Wurf 22 auf Bahn 4 fallen 7 Kegel während der Grünphase... Danach fängt
die Anzeige an mit den Kegeln 1,2,3,4,5,8 zu blinken, während 6,7,9
dauerleuchten... das ist ein Fehlercode, den die Tafel an den Spieler sendet.
Es gibt verschiedene Fehlercodes [immer bestehend aus dauerleuchtenden und
blinkenden Lampen] (dieser bedeutet, ein Kegel befindet sich im Kugelkran)."*

Und die entscheidende Ergänzung: *„Blinken (außer beim Fehlercode) bedeutet
immer, mit einem Wurf alle9e oder beim Räumen einen 8er Kranz (alle außer der
5)."* Braucht das Räumen mehrere Würfe, blinkt nichts.

## Ursache

Wir mitteln über das Fenster je Lampe das **Maximum** — richtig, solange die
Tafel ein Ergebnis zeigt. Im Fehlercode leuchtet jede Lampe irgendwann einmal,
also ergibt die Vereinigung alle neun.

```
46600 ... 46675   gruenphase   AN 7: [1,2,3,6,7,8,9]      stabil, 0 Wechsel
------------------------------- GRÜN AUS bei 46676 ---------------------------
46683  abtastung  AN 9: [1,2,3,4,5,6,7,8,9]
46694  abtastung  AN 3: [6,7,9]
46706  abtastung  AN 9: [1,2,3,4,5,6,7,8,9]
46716  abtastung  AN 3: [6,7,9]
```

## Die Unterscheidung — ohne Codekatalog

| Anzeige | dauerleuchtend | blinkend |
|---|---|---|
| normales Ergebnis | die gefallenen | **leer** |
| Alle Neune, 1 Wurf | **leer** | alle neun |
| 8er Kranz, 1 Wurf | **leer** | alle außer der 5 |
| **Fehlercode** | **nicht leer** | **nicht leer** |

Bei den Jubel-Effekten blinkt **alles, was leuchtet**. Nur ein Fehlercode hat
beide Mengen zugleich besetzt.

## Gegenprobe über den ganzen Spieltag

```
Phase  Muster                                Anzahl
bis    FEST UND BLINKEND (Fehlercode)             2
bis    alles Leuchtende blinkt (Jubel)          750
bis    nichts blinkt                            946
nach   FEST UND BLINKEND (Fehlercode)             2
nach   alles Leuchtende blinkt (Jubel)          711
nach   nichts blinkt                            978
```

**Vier Treffer, und es sind genau die vier bekannten Fehlbuchungen.** Null
Fehlalarme über rund 3300 geprüfte Fenster.

## Der Befund, mit dem nicht zu rechnen war

Bei zwei der vier steht der Code in der Phase `bis`, also *während* einer
Grünphase. Der Code beginnt zwar erst nach Grün-AUS — aber er **läuft weiter**,
bis die Störung behoben ist, und damit in den nächsten Wurf hinein.

**Ein bei Grün-AUS abgeschnittenes Lampenfenster hätte nur zwei der vier Fälle
gerettet.** Der Zeitpunkt allein trägt nicht.

## Was dabei widerlegt wurde

Der Nutzer: *„wie willst du echtes blinken erkennen? Wir checken ja immer nur
'eine Lampe hat mal geleuchtet' aber ja nie 'Lampe blinkt'? Dazu müssten wir
doch viel mehr Frames abfragen, oder?"*

Nein. Während der Grünphase wird alle 5 Frames gelesen, die Blinkperiode
beträgt 25 Frames mit etwa 15 Frames Dunkelphase — rund fünf Messungen je
Periode. Die ganze Auswertung stammt aus der Spur, die der Lauf ohnehin
schreibt. **Es fehlt nicht Abtastung, sondern Buchführung:**
`aggregate_pin_readings` bildet je Lampe das Maximum und wirft die
Zeitstruktur genau dort weg. Zwei Zähler je Lampe (AN, AUS) plus die Zahl der
Wechsel würden reichen.

Ein einzelnes AUS darf dabei **nicht** als Blinken gelten — Bahn 5 Kegel 8
(BUG-034) liest sich regelmäßig als AUS, obwohl sie leuchtet. Gewertet werden
**Wechsel**, mindestens zwei. Gemessen: ruhende Lampen 0 Wechsel, blinkende
4 bis 5.

## Folge für die Prämisse

Der Nutzer, 2026-09-19: *„An der Prämisse, ein Kegel kann nicht falsch
leuchten nur falsch aus sein, dürfen wir nicht rütteln, wegen dem Blinken."*

Sie bleibt — **solange die Tafel ein Ergebnis zeigt.** Im Fehlercode gilt sie
nicht. Die Aggregation über das Maximum ist also richtig; sie braucht eine
Grenze, und die Grenze ist der Fehlercode, nicht die Zeit.

## Lehre

**Ein Messfenster, das einen Anzeigenwechsel enthält, misst den Wechsel.** Der
erste Messversuch schnitt die Fenster an den Wurfframes statt an der Grünspur
und umfasste damit das Löschen der Anzeige — er meldete 1455 „Jubel"-Muster,
wo es höchstens ein paar Dutzend geben kann.

**Eine Regel, die man aus zwei Fällen ableitet, hält selten.** Die erste
Fassung dieser Unterscheidung fiel sofort, als der Nutzer „Alle Achte"
einwarf — und stand erst, nachdem er erklärt hatte, dass die 5 dabei **aus**
ist und nicht dauerleuchtet.
