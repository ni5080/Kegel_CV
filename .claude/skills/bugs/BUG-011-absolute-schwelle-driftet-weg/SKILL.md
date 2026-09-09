---
name: bug-011-absolute-schwelle-driftet-weg
description: >
  Verhindert DETECT-Bug: Absolute Helligkeitsschwellen halten ueber eine lange
  Aufnahme nicht. Das AUS-Niveau der Kegellampen steigt im Lauf von 52 Minuten
  von 151 auf 185 und laeuft aus der Schwelle heraus. Laden bei Arbeit an
  Schwellwerten, Helligkeit, Lampen- oder Ziffernerkennung, langen Aufnahmen
  oder wenn Fehler sich zeitlich haeufen statt zu streuen.
---

# BUG-011 — Die Schwelle stand still, das Signal nicht

| | |
|---|---|
| **Kategorie** | `DETECT` |
| **Gefunden** | 2026-08-25, beim Auswerten eines vollen Trainings |
| **Schweregrad** | mittel — 22 von 476 Wuerfen (4,6 %) mit unsicherem Ergebnis |
| **Regressionstest** | `tests/unit/test_detectors.py` |

## Symptom

Bei 22 Wuerfen blieb mindestens eine Kegellampe im Zustand `UNKNOWN`, wodurch der
Wurf als `ERROR` galt. Es war der haeufigste Fehlergrund des ganzen Laufs — 22
der 31 Fehlerfaelle.

## Die Spur, die sofort trug

Die zeitliche Verteilung war das Entscheidende:

```
alle 22 Faelle:   nach Frame 39000
alle 476 Wuerfe:  gleichmaessig verteilt (50 % vor, 50 % nach Frame 39000)
```

**Null Faelle in der ersten Haelfte.** Bei zufaelliger Ursache waeren rund elf
zu erwarten gewesen. Damit stand fest: Es aendert sich etwas im Lauf der
Aufnahme — und die Suche musste nicht bei den Lampen anfangen, sondern bei der
Zeit.

## Ursache

Das AUS-Niveau der Lampen steigt ueber die Aufnahme:

```
Minute:              1     7    12    17    23    28    33    39    44    49
AUS-Median:        151   160   157   162   167   166   178   176   170   185
ueber Schwelle 195: 0,4%  0,2%  0,4%  1,4%  1,6%  2,6%  8,4%  5,8%  5,1% 23,9%
```

Am Ende liegt fast ein Viertel aller AUS-Messungen ueber der Schwelle. Die Lampe
ist dann weder „aus" noch „an" — `UNKNOWN`.

**Woher die Drift kommt** (gemessen, nicht vermutet):

```
Minute:            1     7    12    17    23    28    33    39    44    49
Tafeln:         94,9  98,8 100,9 100,6 101,5 102,7 104,1 104,9 106,1 109,4
restliches Bild: 100,2 105,6 104,4 106,3 103,3 102,4 102,7 102,7 102,7 100,8
Bahnbereich:     74,8  83,0  83,3  82,5  81,9  81,0  79,2  78,4  77,1  74,7
```

Nur die **Tafeln** werden heller. Das uebrige Bild bleibt flach, der Bahnbereich
wird sogar dunkler. Es ist also weder die Kamera (die wuerde alles aufhellen)
noch die Hallenbeleuchtung, sondern die Anlage selbst.

Das schliesst zugleich die naheliegendste Abhilfe aus: Ein globaler
Helligkeitsausgleich ueber das Bild wuerde nichts nuetzen.

## Richtig

Die Schwellen werden relativ zum **eigenen AUS-Niveau jeder Lampe** gebildet,
das fortlaufend aus den letzten Messungen nachgefuehrt wird:

```yaml
adaptive_baseline: true
baseline_window: 400        # Messungen -> rund 80 Sekunden
baseline_percentile: 15.0   # nicht das Minimum: ein Ausreisser darf nicht bestimmen
baseline_on_margin: 45.0
baseline_off_margin: 28.0
baseline_max_drift: 70.0    # Sicherung gegen Weglaufen
```

Zwei Absicherungen, die nicht fehlen duerfen:

1. **Untergrenze und Obergrenze.** Stuende eine Lampe ungewoehnlich lange an,
   zoege sie ihren eigenen Bezugswert mit nach oben und wuerde am Ende als
   AUS gelesen. Der Bezugswert darf deshalb nicht beliebig wandern.
2. **Rueckfall auf die absoluten Schwellen**, solange das Gedaechtnis duenn ist.
   Ein Bezugswert aus drei Messungen ist schlechter als die belegte Einstellung.

## Die Regel

> **Ein absoluter Schwellwert setzt voraus, dass die Messbedingungen konstant
> bleiben.** Ueber Minuten stimmt das oft; ueber eine Stunde selten. Wo eine
> Groesse driften kann, muss die Schwelle einen Bezugspunkt im Signal haben.

Und zur Fehlersuche, die hier in wenigen Minuten zum Ziel fuehrte:
**Bevor man die Ursache sucht, schaut man auf die zeitliche Verteilung der
Fehler.** Haeufen sie sich, ist die Ursache eine Veraenderung — nicht das
Verfahren. Streuen sie, ist es das Verfahren. Diese eine Abfrage ersetzt viele
Messreihen.

Die Schwellen selbst blieben unangetastet (`brightness_on_threshold: 210`,
`brightness_off_threshold: 195`). Sie stammen aus 3600 Messungen (BUG-006) und
gelten als Ausgangs- und Rueckfallwerte weiter — falsch war nicht ihre Hoehe,
sondern ihre Unbeweglichkeit.

## Nachtrag: dieselbe Ursache an der gruenen Lampe — und sie wog schwerer

Die obige Liste fuehrte die gruene Lampe als **ungepruefte** Stelle. Sie driftet
ebenso, und dort kostete es mehr:

```
Minute:            1     7    12    17    23    28    33    39    44    49
Bahn 2 AUS:     32,3  35,4  36,4  36,4  37,4  34,3  37,4  37,4  38,4  37,4
Bahn 5 AUS:     20,6  22,2  14,4  23,1  28,7  25,9  30,8    -   30,6  28,2
im Graubereich: 4,6%  4,2%  6,2% 10,4% 11,7%  8,8% 11,7% 14,6%  9,4% 16,5%
```

Sauber ausgemessen ueber beide Verteilungen:

```
                AUS 50%  AUS 95% |  AN 5%  AN 50%   Abstand
Min 1-3    B2      28,3     38,4 |   71,7    75,8    +33,3
Min 47-49  B2      36,4     43,4 |   69,7    74,7    +26,3
Min 47-49  B4      36,1     41,7 |   56,5    63,0    +14,8
```

**Beide Niveaus wandern aufeinander zu** — AUS steigt, AN sinkt —, ueberlappen
aber nie. Die feste AUS-Schwelle (35) liegt am Ende mitten in der
AUS-Verteilung, deren 95%-Perzentil auf 43,4 gestiegen ist.

### Warum das schlimmer war als bei den Kegellampen

Die gruene Lampe steuert den **Messzeitpunkt**. Ueber 100 von 130 Messungen
landeten im Graubereich; `GREEN_OFF` loeste erst aus, als ein zufaelliger
Ausreisser die Schwelle unterschritt — gemessen 180 Frames zu spaet:

```
Frame 64075   gruen geht tatsaechlich aus, Kegellampen zeigen 7
Frame 64195   die Anlage stellt neu auf, Kegellampen gehen auf 0
Frame 64255   GREEN_OFF loest erst JETZT aus -> Ergebnis wird als 0 gelesen
Frame 64282   gruen wieder an
```

Ein falscher Messwert verfaelscht eine Zahl. Ein falscher **Zeitpunkt** misst
etwas voellig anderes — hier den Zustand nach dem Aufstellen statt das
Wurfergebnis. Deshalb sahen diese Faelle wie „Lampen zaehlen 0" aus, obwohl mit
den Lampen nichts war.

### Die Loesung unterscheidet sich

Bei den Kegellampen genuegte ein AUS-Bezugswert, weil AN gesaettigt und stabil
ist (254 +- 3). Bei der gruenen Lampe bewegen sich **beide** Niveaus, also muss
die Schwelle anteilig **zwischen** ihnen liegen:

```yaml
adaptive_thresholds: true
adaptive_off_percentile: 20.0   # AUS-Niveau
adaptive_on_percentile: 90.0    # AN-Niveau
adaptive_on_fraction: 0.55      # Lage zwischen beiden
adaptive_off_fraction: 0.40
adaptive_min_span: 12.0         # darunter: feste Schwellen
```

`adaptive_min_span` ist die notwendige Sicherung: War die Lampe im ganzen
Fenster in EINEM Zustand, liegen beide Perzentile dicht beieinander, und eine
Schwelle „zwischen ihnen" laege mitten in diesem einen Zustand.

## Wo gilt diese Regel noch?

- [x] Kegellampen — mitlaufender AUS-Bezugswert
- [x] Gruene Lampe — Schwellen anteilig zwischen beiden Niveaus
- [ ] **Ziffernerkennung**: `min_display_brightness: 230` ist ebenfalls absolut.
      Die Ziffern sind rot und gesaettigt, daher vermutlich unkritisch — aber
      die Zahl der unlesbaren Ziffernfelder ueber die Zeit waere zu pruefen.
- [ ] `segment_floor` im Ziffernleser: bereits relativ zum hellsten Segment
      gebildet, hier also schon richtig geloest.
