---
name: bug-038-die-bessere-roi-kostet-die-ersten-wuerfe
description: >
  Zu Beginn einer Aufzeichnung ist die Anlage freigegeben und die gruene Lampe
  minutenlang durchgehend an. Ohne zweite Wolke lernt der Detektor nichts und
  faellt auf eine feste globale Schwelle zurueck -- die zu den AUS-Niveaus nur
  zufaellig passt. Laden bei Arbeit an `HsvGreenDetector`, an den Gruenschwellen,
  an Gruenlampen-ROIs oder wenn die ersten Wuerfe einer Aufzeichnung fehlen.
---

# BUG-038 — Die bessere ROI kostet die ersten Würfe

| | |
|---|---|
| **Kategorie** | `DETECT` / Grünerkennung |
| **Gefunden** | 2026-10-06, beim Nachmessen der Grünlampen-ROIs |
| **Schweregrad** | hoch (3 Würfe verloren, 1 Spiel 127 statt 150) |
| **Belege** | `debug/streitfaelle/streit_bahn4_f10380-10620.gif` (91 Bilder, Frame für Frame) |
| **Werkzeuge** | `tools/messe_gruenschwellen.py`, `tools/sammle_gruenfelder.py`, `tools/messe_lampensignal.py` |
| **Stand** | **behoben** — `detection.green.warmup_min_change`, bestätigt im Vollauf vom 2026-10-06 |

## Symptom

Die Grünlampen-ROI auf Bahn 4 wurde nachgemessen und verbessert. Danach fehlten
die **ersten drei Würfe des Spieltags** — und zwar nur auf dieser Bahn:

```
                    Montag (alte ROI)    nach der Verbesserung
Bahn 4 Wurf 1        6 Kegel              fehlt
Bahn 4 Wurf 2        8 Kegel              fehlt
Bahn 4 Wurf 3        9 Kegel              fehlt
Endstand Spiel       150                  127
```

Das ist die verkehrte Richtung: Die neue ROI trennt **besser** (Fisher 16,0 auf
25,7, Graubereich 9,3 auf 5,1 Prozent). Ein nach jedem Maß besseres Signal
kostete drei Würfe.

## Ursache

Der Detektor hat drei Wege zu einer Schwelle, in dieser Reihenfolge:

1. gleitendes Histogramm — nur wenn es ein **Tal** findet
2. adaptive Perzentile — nur wenn die **Spanne** ≥ `adaptive_min_span` (30)
3. feste globale Schwelle `on_threshold` 45 / `off_threshold` 35

Die ersten beiden brauchen **beide Zustände im Fenster**. Zu Beginn einer
Aufzeichnung gibt es die nicht: Die Anlage ist freigegeben, alle vier Bahnen
stehen auf Grün. GEMESSEN am 2. Spieltag, Frame des ersten echten Grün-AUS:

```
Bahn 2   7558       Bahn 4   10480   (achteinhalb Minuten)
Bahn 3  10400       Bahn 5    5607
```

So lange trägt **allein die feste Schwelle**. Und die passt zu den gemessenen
AUS-Niveaus nur zufällig. Dieselben Läufe, `tools/messe_gruenschwellen.py`:

```
          alte ROI                neue ROI
         AUS    AN  Spanne      AUS    AN  Spanne
Bahn 2  24,4  66,7    42,3       --    --      --
Bahn 3  22,2  65,6    43,4       --    --      --
Bahn 4  30,0  65,0    35,0      50,0  89,6    39,6
Bahn 5  23,8  71,2    47,4      32,1  80,4    48,3
```

Die beiden geänderten ROIs, normiert (`rect` = x, y, Breite, Höhe) — die
Kalibrierungsdatei selbst bleibt lokal, deshalb stehen die Werte hier:

```
Bahn 4   vorher  0.46602  0.7547  0.0649  0.0526
         nachher 0.47650  0.7600  0.0519  0.0421
Bahn 5   vorher  0.46602  0.7547  0.0649  0.0526
         nachher 0.49250  0.7640  0.0519  0.0421
```

Die bessere ROI sieht mehr Lampe und weniger Gehäuse — beide Wolken wandern
nach oben. Auf Bahn 4 liegt das AUS-Niveau danach bei **50,0, also über der
festen AN-Schwelle von 45**. Im Anlauf ging die Lampe damit nie aus, und ohne
Grün-AUS gibt es keinen Wurf.

**Die feste Schwelle ist keine Eigenschaft der Anlage, sondern eine der ROI.**
Sie stand in `config/default.yaml` als wäre sie gemessen; gemessen war sie an
genau einer Kalibrierung.

## Was NICHT die Lösung war

**Zwei absolute Schwellen je Bahn** (eine Anlaufschwelle pro Bahn in die
Kalibrierung schreiben). Der Nutzer hat das verworfen, bevor es gebaut war:

> *„wie wäre es, wenn wir Anfangs nur eine Schwelle setzen… denn wir hoffen ja
> nur, dass aus irgendwo drunter liegt und an irgendwo drüber… Und das ist ja
> sehr Kalibrierungsabhängig… Ich halte 2 Schwellen für schwierig"*

Richtig — das verschiebt das Problem nur in die Kalibrierungsdatei. Jede
Korrektur an einer ROI hätte dann eine zweite, unsichtbare Pflicht nach sich
gezogen, und genau deren Vergessen ist dieser Bug.

## Die Lösung

Dieselbe Nachricht weiter:

> *„ich denke wir sollten eher mal schauen, ob wir es dadurch schaffen, dass
> wir sagen am Anfang brauchen wir eine Änderung > 10 oder so"*

Eine **Änderung** braucht die absolute Lage nicht und hängt damit an keiner
ROI. Sie braucht nur, dass die Wolken weit genug auseinanderliegen — und das
ist die eine Größe, die über alle vier Bahnen stabil ist (Spanne 35 bis 48).

GEMESSEN über beide Vollläufe, Frame des ersten erkannten Grün-AUS:

```
                     absolut   >5     >10     >15     >20
  alte ROIs  Bahn 2     7558    161   3200    7557    7558
             Bahn 3    10400     40  10392   10392   10399
             Bahn 4    10480     79   1801   10479   14124
             Bahn 5     5607    977   5605    5605    5605
  neue ROI   Bahn 4     KEINS    91   2097   10470   10479
             Bahn 5     5607     87   5605    5605    5605
```

Bei **15** trifft die Regel überall dasselbe AUS wie die absolute Schwelle, auf
wenige Frames genau, ohne Fehlauslöser davor — und sie findet es auch dort, wo
die absolute Schwelle nichts findet. Bei 10 kommen Fehlauslöser, bei 20 wird
Bahn 4 zu spät.

Drei Eigenschaften, die nicht verhandelbar sind:

- **Sie ersetzt die Schwellen nicht, sie kommt hinzu.** Eine erste Fassung
  ersetzte sie — dann hat die Lampe beim ersten Bild kein Niveau und meldet
  `UNKNOWN`. In Produktion wären das acht Minuten „unbekannt" statt „an": ein
  schlimmerer Fehler als der behobene. Sechs bestehende Tests fielen darüber.
- **Sie hält ihren Zustand.** Die zweite Fassung feuerte korrekt bei Frame
  10470 (77,1 auf 64,6) und fiel im nächsten Bild auf das Schwellenurteil
  zurück (56,2 > 45 → AN). Ein einzelnes AUS reicht wegen
  `min_stable_frames: 3` nicht, der Wurf blieb verloren. Das Simulationsskript
  hatte den Zustand gehalten, der Detektor nicht — **dieselbe Regel, zwei
  Bedeutungen.**
- **Sie schweigt, sobald gelernt wird.** Sobald das Histogramm ein Tal hat oder
  die Perzentile eine ausreichende Spanne sehen, ist sie aus dem Weg.

## Nachweis

Vollauf über den ganzen 2. Spieltag (242 255 Frames), verglichen mit dem Lauf
vom 2026-09-29:

```
                              vorher        nachher
Wuerfe                          1679           1680
Luecken                            1              0
Spiele mit falschem Endstand    1/60           0/60
Wurf fuer Wurf        1482 vergleichbar, 1446 richtig in BEIDEN Laeufen
                      keine einzige geaenderte Kegelzahl
```

Die Bahnen 2 und 3 waren Kontrollgruppe — dort ändert die Regel nichts, und
sie hat auch nichts geändert.

## Regressionstest

`tests/unit/test_gruen_anlaufregel.py` (12 Tests), fünf davon halten je eine
der Fallen fest:

| Test | hält fest |
|---|---|
| `test_beide_wolken_ueber_der_festen_schwelle` | der Fall selbst — AUS 50, AN 85, feste Schwelle 45 |
| `test_das_erste_bild_urteilt_nach_der_schwelle` | sie ersetzt die Schwellen nicht |
| `test_rauschen_unter_der_schwelle_kippt_nichts` | BUG-013 in neuem Gewand |
| `test_eine_verdeckte_tafel_zaehlt_nicht` | Verdeckung ist keine Änderung |
| `test_eine_verschobene_roi_vergisst_auch_das_niveau` | BUG-024: `vergiss()` muss das Niveau mitnehmen |

## Muster für das nächste Mal

**Eine Verbesserung an einer Messstelle kann eine Konstante ungültig machen,
die woanders steht.** Die ROI wurde nach Trennschärfe optimiert und war nach
jedem Maß besser; ungültig wurde eine Zahl in einer YAML-Datei, die niemand
angefasst hatte. Wer eine ROI ändert, muss fragen, welche absoluten Werte an
ihr hängen — oder, besser, dafür sorgen, dass keine daran hängen.

**Ein Simulationsskript beweist die Regel, nicht ihre Umsetzung.** Zwischen
„die Regel funktioniert" und „der Detektor tut das" lag hier ein gehaltener
Zustand, und das kostete einen ganzen Prüflauf.
