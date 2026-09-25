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
| **Stand** | **bewusst nicht behoben** — sechs Gegenmassnahmen gemessen, alle teurer als der Fehler |

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

## Zwei der vier Treffer sind Fehlalarme des Messwerkzeugs

**Korrektur, noch am selben Tag.** Zuerst stand hier, der Code laufe in den
nächsten Wurf hinein, weil zwei der vier Treffer in der Phase `bis` lagen.
Der Nutzer hat widersprochen: *„Bevor der nächste Wurf freigegeben wird, ist
das Problem IMMER behoben!"* — und die Frames geben ihm recht:

```
Zyklus vor Wurf 23: Grün-AN 47103, Grün-AUS 47674
  letzter AN/AUS-Wechsel bei Frame 47605 -- 25,1 s nach Grün-AN,
  danach 3,5 s ruhig, Stand [1,2,3,4,6,7,8,9]
```

Der Wechsel bei 47605 ist **kein Blinken, das ist der fallende Kegel** (7
wird zu 8). Alle übrigen Wechsel dieses Zyklus liegen in den ersten rund 30
Frames nach Grün-AN — dort, wo die Anzeige vom vorigen Stand auf den neuen
umschaltet. Genau deshalb wird die Grundlinie erst *kurz nach* Grün-AN
gemessen.

**Der Klassifikator kann den Umschaltmoment nicht vom Fehlercode trennen**,
weil beide „etwas fest, etwas wechselnd" ergeben. Echte Fehlercodes stehen nur
in den beiden `nach`-Fenstern.

### Was daraus folgt

* Die Regel „Fehlercodes beginnen erst nach Grün-AUS und sind vor der Freigabe
  des nächsten Wurfs behoben" ist **nicht** widerlegt.
* Ein Blinkerkenner braucht einen **Anlauf nach Grün-AN**, sonst meldet er bei
  jedem Wurf den Umschaltmoment. Wie lang, ist ungemessen.
* Ob dann noch vier, zwei oder mehr Treffer übrig bleiben, ist damit ebenfalls
  offen. Die Zahl „vier Treffer, null Fehlalarme" oben gilt nur für das
  Werkzeug in seiner jetzigen, zu groben Form.

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


## Warum nichts gebaut wurde (2026-09-25)

Sechs Varianten gegen die Kegelziffer gemessen, 1243 Wuerfe
(`tools/vergleiche_ergebnisfenster.py`, Einzelheiten in
`docs/VIDEO_ANALYSIS.md`):

```
E1 Vereinigung alles (heute)   1160   93,3%
E2 nur bis Gruen-AUS           1140   91,7%
E3 letzter Stand                816   65,6%
E4 Mehrheit                      97    7,8%
E5 letztes Plateau              751   60,4%
E6 alles, ausser Fehlercode    1157   93,1%
```

Der Fehler kostet zwei Spiele mit je +10 Kegeln. Die billigste Gegenmassnahme
kostet 20 Wuerfe. **Der Befund bleibt stehen, die Analyse bleibt, wie sie
ist.** Die betroffenen Spiele werden von Hand korrigiert; die Tafel meldet die
Stoerung ja selbst.

Liegt die Erkennung damit brach? Nein -- sie ist gemessen und einsatzbereit
(0 Fehlalarme auf 1169 gesunden Wuerfen). Wird eine Bahn stoerungsanfaellig,
ist die Abwaegung neu zu treffen.

Nebenbefund derselben Messung: **E4 ist der Zahlenbeleg fuer die Praemisse des
Nutzers.** Wer statt der Vereinigung die Mehrheit nimmt, faellt von 93 auf
8 Prozent -- beim Blinken ist jede Lampe die halbe Zeit aus.
