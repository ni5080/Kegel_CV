# Videoanalyse — gemessene Fakten

> **Alles in diesem Dokument wurde am realen Material gemessen, nicht geschätzt.**
> Vermutungen stehen in `OPEN_QUESTIONS.md`. Wer hier etwas ergänzt, nennt die
> Quelle: Video, Frame, Werkzeug.
>
> Stand: 2026-08-25

---

## 1. Das Material

11 Videos in `kegelVideos/`, zwei Aufnahme-Sessions:

| Session | Clips | Länge je Clip | Größe |
|---|---|---|---|
| `2024-09-03` | 9 | 13–30 s | 10–23 MB |
| `2026-08-22` | 2 | 5 s und lang | 3,7 MB und ~2,3 GB |

Einheitlich über alle Clips:

| Eigenschaft | Wert |
|---|---|
| Auflösung | **1920 × 1080** |
| Framerate | **25,00 fps** (konstant) |
| Codec | **h264** |

⇒ Echtzeit-Budget: **40 ms pro Frame**.

---

## 2. Aufnahmeort

**Kegelsportcenter die Anlage**, Halle des **Heimmannschaft**
(Wandaufschrift „…IN OSNABRÜCKER KEGLER e.V."). Anlagentyp: **FUNK**.
Klassisches deutsches Kegeln mit **9 Kegeln**.

Die Halle hat **5 Bahnen** (im Hintergrund nummeriert 1–5 sichtbar), das
Overlay zeigt jedoch nur **4 Anzeigetafeln** → siehe offene Frage Q1.

---

## 3. Bildaufbau

```
┌───────────────────────────────────────────────────────────────┐
│           ┌─────────────────────────────────────┐             │
│           │  OVERLAY (x≈430–1490, y≈35–300)     │             │
│           │  4 Anzeigetafeln in Nahaufnahme     │  ← ANALYSEQUELLE
│           │  [Tafel1][Tafel2][Tafel3][Tafel4]   │             │
│           └─────────────────────────────────────┘             │
│                                                               │
│         Weitwinkel-Totale der Halle, 5 Bahnen                 │
│         kleine Tafeln in der Ferne (unbrauchbar)              │  ← NICHT auswerten
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

Das Overlay ist ein eingeblendetes Bild (zweite Kamera oder digitaler Zoom).
Es ist die einzige brauchbare Quelle — die Tafeln im Hintergrund sind nur wenige
Dutzend Pixel groß.

### ⚠ Die Overlay-Position ist NICHT konstant

Gemessene x-Positionen der grünen Lampen:

| Session | Bahn 1 | Bahn 2 | Bahn 3 | Bahn 4 |
|---|---|---|---|---|
| 2024-09-03 | 538 | – | 1079 | 1378 |
| 2026-08-22 | 572 | 876 | 1105 | 1399 |

Auch die Tafelgrößen unterscheiden sich innerhalb einer Session
(Bahn 1: 157×124 px, Bahn 3: 160×142 px, Bahn 4: 156×105 px).

**Konsequenz:** Feste Koordinaten sind unbrauchbar. Kalibrierung erfolgt pro
Session und wird gespeichert. Die vier Tafeln sind zusätzlich unterschiedlich
perspektivisch verzerrt ⇒ Homographie **pro Bahn**, nicht global.

---

## 4. Die FUNK-Anzeigetafel

```
┌──────────────────────────────────────────┐
│ ▬▬▬▬▬▬▬ Laufschrift-Display ▬▬▬▬▬▬▬▬▬▬ │
│ ┌────────┐   ● rot   ● gelb  ┌────────┐ │  Statuslampen — KEINE Kegel
│ │ Name L │                   │ Name R │ │
│ └────────┘        ○ 1                   │
│              ○ 2      ○ 3               │  9 KEGELLAMPEN (Raute)
│         ○ 4      ○ 5      ○ 6           │  LEUCHTEND = GEFALLEN
│              ○ 7      ○ 8               │
│                   ○ 9                   │
│ ┌──────┐        ○ ● ○        ┌────────┐ │
│ │  00  │     GRÜNE LAMPE     │  0063  │ │  Summe A
│ └──────┘                     └────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │   012        6         0063         │ │  Wurfnr · Kegel · Summe B
│ └─────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

### Verifizierte Ablesungen (Video 2026-08-22, Frame 42 und 90)

| Tafel | Leuchtende Lampen | Ziffer | Unteres Display | Lesart |
|---|---|---|---|---|
| 1 | 5 | 5 | `001 5 0005` | Wurf 1 → 5 Kegel → Summe 5 |
| 2 | 7 | 7 | `004 7 0023` | Wurf 4 → 7 Kegel → Summe 23 |
| 3 | 6 | 6 | `012 6 0063` | Wurf 12 → 6 Kegel → Summe 63 |
| 4 | 9 | 9 | `007 9 0028` | Wurf 7 → 9 Kegel → Summe 28 |

**Dreifach bestätigt:** Anzahl leuchtender Lampen == angezeigte Ziffer.
Bei Tafel 3, Frame 90 sind es konkret die Lampen 1, 3, 5, 6, 8, 9 (sechs Stück,
Anzeige „6"), während 2, 4, 7 matt bleiben.

⇒ **Leuchtend = Kegel gefallen.** Nicht umgekehrt.

Summe A (oben rechts) und Summe B (unten rechts) waren in allen untersuchten
Frames **identisch** → siehe Q3.

---

## 5. Grüne Lampe

- Position: mittig unter dem Kegelbild, zwischen den beiden Displays,
  flankiert von zwei kleinen hellen Punkten.
- Größe: ca. **6 × 8 px** im Originalframe.
- Detektion: HSV `H ∈ [40,90]`, `S > 80`, `V > 80`.

Gemessene Scores (Video 2026-08-22, 122 Frames, alle 4 Bahnen):

| Zustand | Score-Bereich |
|---|---|
| **AUS** | 17,3 – 24,0 |
| **AN** | 59,9 – 74,3 |

Beobachteter Zustandswechsel: **Bahn 2 springt bei Frame ~78 von ~22 auf ~73**
(GREEN ON). Die anderen drei Bahnen bleiben in diesem Zeitraum unverändert —
ein direkter Beleg für die Unabhängigkeit der Bahnen.

⚠ **Die Baseline ist nicht null** (das beige Gehäuse hat Grünanteil). Ein
absoluter Schwellwert nahe 0 würde also immer „AN" melden. Daraus folgt die
Hysterese mit `on_threshold=45` / `off_threshold=35`.

---

## 6. ROI-Positionen (normierte Tafelkoordinaten)

**Quelle: eine echte Nutzerkalibrierung**, gemittelt über alle vier Bahnen
(`data/calibrations/kalibrierung_2026-08-24_2258.json`). Die Streuung zwischen
den Bahnen beträgt nur **0,004–0,012** — rund 1–2 px. Bezugsrahmen ist das beige
Tafelgehäuse, also die Ecken, die der Nutzer anklickt.

### Kegellampen — streng regelmäßige Raute

| Zeile | y | x-Positionen |
|---|---|---|
| 1 | 0,342 | 0,498 |
| 2 | 0,419 | 0,335 · 0,661 |
| 3 | 0,497 | 0,175 · 0,498 · 0,821 |
| 4 | 0,573 | 0,335 · 0,660 |
| 5 | 0,651 | 0,498 |

Der Zeilenabstand ist **konstant 0,0775**, die x-Positionen liegen symmetrisch um
die Mitte. Lampengröße ca. 0,080 × 0,075.

> **Korrektur einer früheren Schätzung:** Eine erste, selbst geschätzte Variante
> lag systematisch zu hoch (erste Zeile bei 0,283 statt 0,342) und war zu weit
> gespreizt (Zeilenabstand 0,091 statt 0,0775). Die Abweichung fiel erst im
> Vergleich mit der Nutzerkalibrierung auf.

### Displays

| ROI | Mitte (x, y) | Größe (w, h) |
|---|---|---|
| `green_lamp` | 0,504 · 0,771 | 0,065 × 0,052 |
| `left_display` (Fehlwürfe) | 0,182 · 0,698 | 0,260 × 0,130 |
| `total_a` | 0,780 · 0,700 | 0,240 × 0,130 |
| `throw_number` | 0,232 · 0,888 | 0,240 × 0,130 |
| `pin_count` | 0,450 · 0,888 | 0,110 × 0,130 |
| `total_b` | 0,715 · 0,888 | 0,330 × 0,130 |

**Die Feldhöhe von 0,130 ist kein Zufallswert:** Die Ziffern selbst sind
normiert **0,099 hoch**. Eine frühere Größe von 0,093 war damit *kleiner als die
Ziffer* — die oberen und unteren Segmente fielen heraus. 0,130 entspricht der
Ziffernhöhe plus rund 30 % Rand; der Rand fängt Klickungenauigkeit und den
Versatz zwischen den vier perspektivisch verschiedenen Tafeln ab.

---

## 7. Automatische Tafelerkennung — nur ein Hilfsmittel

`tools/verify_rois.py` kann Tafeln über ihr helles, warmes Gehäuse finden
(HSV `H∈[10,40]`, `S∈[25,120]`, `V>120`).

**Ergebnis der Prüfung: nicht verlässlich genug für den Produktivbetrieb.**
Bei Bahn 3 lag die erkannte Box gut, bei **Bahn 1 deutlich daneben** — das untere
Zeilendisplay fiel heraus, wodurch sämtliche ROIs verrutschten und die grüne
Lampe außerhalb der Tafel lag.

⇒ Das bestätigt die Architekturentscheidung: **Der Nutzer kalibriert per Klick.**
Die automatische Erkennung bleibt ein Analysewerkzeug für die Entwicklung.

---

## 8. Die 7-Segment-Ziffern — gemessen

### Größe und Auflösung

| Feld | ROI im Frame | je Ziffer |
|---|---|---|
| `throw_number` (3-stellig) | 39 × 22 px | ~13 × 18 px |
| `pin_count` (1-stellig) | 19 × 22 px | ~13 × 18 px |
| `total_b` (4-stellig) | 54 × 22 px | ~13 × 18 px |

**Die Segmente sind nur 2–3 px dick.** Das ist die harte Grenze dieses Materials.

Die Ziffernbreite verhält sich konstant zur Höhe: gemessen **0,53–0,71**,
Schwerpunkt **0,65**. Das lässt sich nutzen, um Ziffernzellen aufzureihen, wenn
sich keine Lücken finden.

### Überstrahlung — der entscheidende Befund

Erwartet wurde eine sattrote Anzeige. Gemessen (Bahn 3, `total_b`, Frame 90):

| Bereich | B | G | R | R−G |
|---|---|---|---|---|
| Gehäuse (beige) | 153 | 163 | 189 | +26 |
| Display-Hintergrund | 20 | 22 | 24 | +2 |
| **Segment, hellster Punkt** | 178 | 141 | **255** | **+114** |

Die Segmentmitten sind **nahezu weiß**; nur die Ränder bleiben gesättigt rot.
Eine Maske über die Rot-Dominanz (`R−G > 45`) erfasst deshalb nur die Umrisse und
liefert **hohle** Ziffern, die kein Segmentmuster ergeben.

Was trägt, ist die Trennung **hell gegen dunkel** per Otsu auf dem Rotkanal:
Das Display ist schwarz (24), die Segmente sind hell (bis 255).

### Trefferquoten der Verfahren

Geprüft gegen 12 Felder mit bekanntem Sollwert (4 Bahnen × 3 Felder, Frame 90):

| Verfahren | Treffer |
|---|---|
| Segment-Dekodierung, Rot-Maske | 0/12 |
| Segment-Dekodierung, Otsu-Maske | 5/12 |
| Template Matching (synthetische Vorlagen) | 6/11 |
| Template Matching + zeitliche Aggregation | 7/12 |

**Höhere Auflösung hilft nicht.** Identisches Ergebnis bei entzerrten Tafeln in
440×530, 880×1060 und 1320×1590 — Interpolation fügt keine Information hinzu.

**Die verbleibenden Fehler sind systematisch, nicht zufällig.** Eine Bahn las in
25 von 25 Frames „4" statt „9". Zeitliche Aggregation hilft gegen Flackern, aber
nicht gegen einen konstant falsch messenden Detektor.

### Einzeln eingerahmte Ziffern — der Durchbruch

Alle automatischen Verfahren scheiterten an der **Positionierung** der
Ziffernzellen. Werden die Stellen dagegen **einzeln kalibriert** (je zwei Klicks
in der GUI), ändert sich das Bild deutlich.

Gemessen an vier Frames mit bekanntem Sollwert:

| Feld | Feld automatisch geteilt | einzeln eingerahmt |
|---|---|---|
| Wurfnummer | 2/4 | **4/4** |
| Kegelanzahl | 2/4 | 2/4 |
| Summe B | 3/4 | 2/4 |
| gesamt | 7/12 (58 %) | **8/12 (67 %)** |

Im vollständigen Analyselauf (8000 Frames, 38 Würfe) zählt vor allem, wie oft
eine **falsch** gelesene Ziffer der Lampenzählung widerspricht:

| Bahn | Ziffern eingerahmt | Würfe | Ziffer gelesen | korrekt | **falsch** |
|---|---|---|---|---|---|
| 2 | **ja** | 8 | 4 | 3 | **1** (13 %) |
| 3 | nein | 10 | 10 | 2 | 8 (80 %) |
| 4 | nein | 12 | 11 | 9 | 2 (17 %) |
| 5 | nein | 8 | 8 | 1 | 7 (88 %) |

Die eingerahmte Bahn liest seltener — meldet dafür aber kaum noch Falsches. Das
ist die gewünschte Richtung: Eine nicht gelesene Ziffer lässt den Wurf `VALID`
(die Lampen zählen), eine falsch gelesene erzeugt `ERROR`.

**Mit allen vier Bahnen eingerahmt** (12 000 Frames, 8 Minuten Video, 51 Würfe):

| Bahn | Würfe | Ziffer gelesen | korrekt | falsch | Summenkette |
|---|---|---|---|---|---|
| 2 | 16 | 7 | 5 | 2 | stimmig |
| 3 | 16 | 10 | 9 | 1 | stimmig |
| 4 | 8 | 5 | 5 | 0 | stimmig |
| 5 | 11 | 3 | 1 | 2 | stimmig |

**80 % der gelesenen Ziffern korrekt, nur 5 Falschlesungen bei 51 Würfen** — und
alle vier Summenketten stimmig. Zuvor lasen die nicht eingerahmten Bahnen 3 und 5
zu 80–88 % falsch.

### Die Ziffern stehen schief — und zwar von Hause aus

Nutzerbeobachtung, nachgemessen an 757 Einzelziffern über alle vier Tafeln,
**im entzerrten Tafelbild** (die Perspektive ist dort bereits herausgerechnet):

| Tafel | Bahn | Proben | Neigung |
|---|---|---|---|
| 1 (links) | 2 | 132 | −2,0° |
| 2 | 3 | 210 | −2,3° |
| 3 | 4 | 210 | −2,4° |
| 4 (rechts) | 5 | 205 | −2,9° |

**Spanne zwischen den Tafeln: 0,9°.** Käme die Neigung aus der Perspektive,
müssten die äußeren Tafeln deutlich abweichen — und die Homographie hätte sie
ohnehin beseitigt. Dass sie *nach* der Entzerrung auf allen Tafeln nahezu gleich
bleibt, belegt: **Die Ziffern der Anlage sind leicht kursiv.**

Praktische Folge: **keine.** Bei 18 px Ziffernhöhe entspricht −2,4° einem Versatz
von unter einem Pixel. Eine Scherungskorrektur verschlechtert das Ergebnis sogar,
weil die zusätzliche Interpolation bei 11×18 px mehr kostet, als der Versatz
ausmacht:

| Korrektur | Treffer |
|---|---|
| keine | **9/13** |
| Scherung −2,4° | 6/13 |
| Scherung −4,6° | 5/13 |

### Drei Fallstricke beim stellenweisen Lesen

1. **Messfläche für Segment `g` zu breit.** Sie erfasste die senkrechten
   Segmente links und rechts mit; jede „0" wurde zur „8", Trefferquote 17 %.
   Waagerechte Segmente nur im mittleren Drittel messen.
2. **„Größte Lücke" als Schwelle trägt nicht.** Bei einer „0" sind sechs
   Segmente aktiv, die größte Lücke liegt dann *innerhalb* der aktiven.
   Gemessen: `g=0,10 | a=0,26 f=0,27 | e=0,49 …` — die Schwelle landete bei 0,38
   statt 0,18. Verlässlich ist eine Schwelle **relativ zum hellsten Segment**.
3. **Otsu normalisiert.** In einem fast schwarzen Ausschnitt findet es trotzdem
   eine Schwelle und macht aus Rauschen eine Ziffer — bevorzugt eine „8".
   Deshalb vorab die absolute Helligkeit prüfen (gemessen: klar lesbar 255,
   verblassend 196–212, fast erloschen 76–96).

### Bestätigung des Flackerns (Q4)

`2026-08-22 09-15-50.mp4`, Bahn 2, Feld `pin_count`:
In **Frame 42** zeigt es klar „7", in **Frame 90** ist es **unbeleuchtet**.
Die Anzeige ist nicht in jedem Frame lesbar — genau das Verhalten aus Auftrag §8.
Der Detektor meldet dort korrekt „nicht lesbar" statt zu raten.

---

## 9. Werkzeuge zur Reproduktion

```bash
.venv/Scripts/python.exe tools/verify_rois.py --frame 90
```

```bash
.venv/Scripts/python.exe tools/verify_rois.py --calibration data/calibrations/meine.json
```

Ergebnisse landen in `debug/roi_check/`.

---

## Räumen — warum die Lampen nicht das Wurfergebnis sind

**Quelle: Nutzer, 2026-08-25.** Fachwissen, das aus dem Videomaterial allein
nicht ableitbar war.

Beim Kegeln gibt es die Bedingung **„Räumen"**: Die nach einem Wurf noch
stehenden Kegel müssen abgeräumt werden. Erkennbar am Zustand beim Einschalten
der grünen Lampe:

| Beim Grün-AN | Bedeutung |
|---|---|
| Kegellampen **aus** | „in die Vollen" — alle neun Kegel stehen |
| Kegellampen **teilweise an** | **Räumen** — die leuchtenden Kegel liegen bereits |

Die leuchtenden Lampen zeigen den **Zustand des Bildes**, nicht das Ergebnis des
laufenden Wurfs. Beim Räumen müssen die bereits liegenden Kegel nicht mehr
getroffen werden; sie zählen nicht zu diesem Wurf.

**Folge für die Auswertung:** Das Wurfergebnis ist die **Differenz**

```
gefallene Kegel = Lampen bei GREEN_OFF  −  Lampen bei GREEN_ON
```

Umgesetzt in `analysis/lane_processor.py::_measure_baseline` und
`analysis/throw_analyzer.py`. Konfiguriert über `sampling.baseline_offsets`.

### Gemessen

Über 12 000 Frames (8 Minuten, 4 Bahnen, 70 Würfe) war die Grundlinie bei jeder
Bahn **genau einmal** ungleich null — beim 17. Wurf, mit 7, 6, 7 bzw. 8 bereits
liegenden Kegeln. Das passt zum Rundenwechsel nach 15 Würfen.

Genau diese vier Würfe waren zuvor als Widerspruch aufgefallen: Die Lampen
meldeten 9, die Tafel 1, 2, 3 bzw. 4. Beide hatten recht — sie maßen
Verschiedenes.

### Was daraus folgt

Ein Widerspruch zwischen zwei Quellen bedeutet nicht, dass eine falsch misst. Er
kann bedeuten, dass sie **verschiedene Dinge messen**. Vor der Fehlersuche steht
die Frage, was die Quelle überhaupt aussagt.

### Erledigt: die vier Fälle „Ziffer 9 bei dunklen Lampen"

Bei vier Würfen zeigte die Tafel `9`, während alle Lampen dunkel waren. Das sah
nach einem eigenen Phänomen aus, war aber dasselbe Blinken (BUG-007): Der
Messzeitpunkt fiel jedes Mal in eine Dunkelphase von 13–15 Frames. Belegt und
abgeschlossen in `OPEN_QUESTIONS.md` (Q8).


---

## Status eines Wurfs: was ihn entwerten darf — und was nicht

**Auf Hinweis des Nutzers geändert (2026-08-25):** „nur weil die Wurfnummer
nicht richtig erkannt wird, soll bitte das Ergebnis noch nicht direkt als ERROR
ausgegeben werden."

Vorher zählte jede fehlgeschlagene Plausibilitätsprüfung gleich viel; ab zwei
Verstößen galt ein Wurf als `ERROR`. Zwei davon betrafen aber gar nicht das
Ergebnis:

| Prüfung | betrifft |
|---|---|
| Lampen == angezeigte Kegelzahl | **das Ergebnis** |
| Summe alt + Kegel == Summe neu | **das Ergebnis** |
| Wurfnummer steigt / plausibel / lückenlos | die Buchführung |

Die Wurfnummer sagt nichts darüber, wie viele Kegel gefallen sind. Sie ist
dreistellig, flackert entsprechend häufig, und ein sauber gemessener Wurf wurde
allein dadurch entwertet.

Seitdem trägt `PlausibilityCheck` das Feld `affects_result`. Nur ergebnis-
relevante Verstöße führen zu `ERROR`; Buchführungsfehler bleiben in der
Beweiskette sichtbar und kosten 0,05 statt 0,15 Confidence.

**Die dahinterliegende Regel:** Ein Status beschreibt die Verlässlichkeit einer
bestimmten Aussage — hier: wie viele Kegel gefallen sind. Prüfungen, die eine
*andere* Aussage betreffen, dürfen ihn nicht senken. Sonst sammelt sich
Misstrauen aus unbeteiligten Quellen an.


---

## Spielstruktur: 30 Würfe, dann setzt die Tafel zurück

**Vom Nutzer angekündigt, über 52 Minuten bestätigt.** Der Hinweis lautete: „die
Ergebniszeile unten wird nach (ich glaube 30 Wurf) zurückgesetzt. DAS ist ein
Zeichen dafür, dass hier zuvor ein Endergebnis stand."

Gemessen über das ganze Training, drei Bahnen unabhängig:

```
Bahn 2:  Wurf 30 (189 -> 0)   Wurf 60 (185 -> 0)   Wurf 92 (182 -> 5)
Bahn 3:  Wurf 30 (199 -> 0)                        Wurf 90 (216 -> 0)
Bahn 4:  Wurf 29 (188 -> 0)   Wurf 59 (191 -> 0)   Wurf 89 (200 -> 0)
```

Ein **Spiel** umfasst 30 Würfe — zwei 15er-Runden. Danach springt die Tafel auf
Wurf 1 und Summe 0 zurück. **Der letzte Stand vor der Rücksetzung ist das
Spielergebnis.**

### Warum das keine Lesefehler sind

Zwei Bahnen sprangen im Abstand von zwei Sekunden gemeinsam von 33 auf 4:

```
16:02:23  Bahn 3: Wurfnummer 4 liegt nicht über der letzten (33)
16:02:25  Bahn 5: Wurfnummer 4 liegt nicht über der letzten (33)
```

Zwei unabhängige OCR-Fehler treffen nicht gleichzeitig denselben Wert.

### Abgrenzung zur Regel aus BUG-008

BUG-008 verlangt, eine zurückfallende Wurfnummer **nicht** zu glauben, sondern
fortzuzählen — sonst löscht ein Lesefehler die restliche Serie. Beim Spielwechsel
ist der Rückfall aber echt. Unterschieden wird an der **Höhe**:

| Rückfall | Deutung |
|---|---|
| um wenige Stellen (12 → 11) | Lesefehler, wird fortgezählt |
| von über 10 auf unter 5 (33 → 4) | Spielwechsel, Zählung beginnt neu |

Konfiguriert über `scoring.game_reset_after` und `scoring.game_reset_below`.

### Was ohne diese Erkennung falsch war

Die interne Summe lief über die Rücksetzung hinweg weiter und driftete von der
Tafel ab:

```
Wurf 28   Tafel 188   intern 180
Wurf 29   Tafel   0   intern 189     <- Rücksetzung
Wurf 30   Tafel   7   intern 196
```

Ab dem 30. Wurf war die Gegenprobe gegen die Summenanzeige damit wertlos — also
für rund 80 % des Trainings.


---

## Die Lampenhelligkeit driftet über die Aufnahme

**Gemessen über 52 Minuten** (siehe BUG-011). Die Helligkeit der
*ausgeschalteten* Kegellampen steigt stetig:

```
Minute:              1     7    12    17    23    28    33    39    44    49
AUS-Median:        151   160   157   162   167   166   178   176   170   185
über Schwelle 195: 0,4%  0,2%  0,4%  1,4%  1,6%  2,6%  8,4%  5,8%  5,1% 23,9%
```

Am Ende liegt fast ein Viertel aller AUS-Messungen über der festen Schwelle.

**Woher die Drift kommt** — nur die Tafeln werden heller:

```
Minute:            1     7    12    17    23    28    33    39    44    49
Tafeln:         94,9  98,8 100,9 100,6 101,5 102,7 104,1 104,9 106,1 109,4
restliches Bild: 100,2 105,6 104,4 106,3 103,3 102,4 102,7 102,7 102,7 100,8
Bahnbereich:     74,8  83,0  83,3  82,5  81,9  81,0  79,2  78,4  77,1  74,7
```

Das übrige Bild bleibt flach, der Bahnbereich wird sogar dunkler. Damit sind
Kamera-Nachregelung und Hallenbeleuchtung ausgeschlossen — die Anlage selbst
wird heller. (Eine erste Vermutung, es werde draußen hell, war falsch: Die
Aufnahme entstand abends gegen 21:25. Hinweis des Nutzers.)

**Folge:** Ein globaler Helligkeitsausgleich über das Bild würde nichts nützen.
Der Bezugspunkt muss von der Lampe selbst kommen — umgesetzt als mitlaufendes
AUS-Niveau je Lampe (`detection.lamps.adaptive_baseline`).


---

## Die grüne Lampe driftet ebenfalls — und dort kostet es den Messzeitpunkt

Gemessen über 52 Minuten je Bahn (Score der grünen Lampe):

```
                AUS 50%  AUS 95% |  AN 5%  AN 50%   Abstand
Min 1-3    B2      28,3     38,4 |   71,7    75,8    +33,3
Min 47-49  B2      36,4     43,4 |   69,7    74,7    +26,3
Min 47-49  B4      36,1     41,7 |   56,5    63,0    +14,8
```

Beide Verteilungen wandern aufeinander zu, überlappen aber nie. Die feste
AUS-Schwelle (35) liegt am Ende **mitten in der AUS-Verteilung** — der Anteil
der Messungen im Graubereich steigt von 4,6 % auf 16,5 %.

**Folge:** `GREEN_OFF` löste erst aus, wenn ein zufälliger Ausreißer die
Schwelle unterschritt — gemessen bis zu 180 Frames zu spät. Bis dahin hatte die
Anlage die Kegellampen bereits zurückgesetzt:

```
Frame 64075   grün geht tatsächlich aus, Kegellampen zeigen 7
Frame 64195   die Anlage stellt neu auf, Kegellampen gehen auf 0
Frame 64255   GREEN_OFF löst erst JETZT aus  -> Ergebnis wird als 0 gelesen
Frame 64282   grün wieder an
```

Diese Fälle sahen wie „die Lampen zählen 0" aus, obwohl mit den Lampen nichts
war. **Ein falscher Messwert verfälscht eine Zahl; ein falscher Zeitpunkt misst
etwas ganz anderes.**

Gelöst über `detection.green.adaptive_thresholds`: Die Schwellen liegen anteilig
zwischen den beiden beobachteten Niveaus statt auf festen Werten.

### Nebenbefund

Mit der korrigierten Flankenerkennung wurden **sechs zusätzliche Grünzyklen**
sichtbar (486 statt 480) — Würfe, die zuvor mit dem Nachbarzyklus verschmolzen.


---

## Uneindeutige Ziffern von den Lampen auflösen lassen

**Vorschlag des Nutzers (2026-08-25):** „wenn er eine 4 oder 9 als Text erkennt,
und oben 9 Lampen leuchten => 9 … Wir werden es ja dann merken, wenn die Summe
steigt."

Der Gedanke: Statt einzelne Messwerte immer weiter zu verfeinern, lässt man die
**Quellen einander auflösen** — und behält die Summenanzeige als unabhängige
Kontrolle.

### Der Anlass, gemessen

Bahn 5, Frame 22269. Die Anzeigetafel zeigte `005 4 0029` — also eine 4:

```
fills = [a 0,333  b 0,571  c 0,517  d 0,000  e 0,024  f 0,333  g 0,878]
Schwelle 0,3072   ->  aktiv 'abcfg' = 9
```

Segment `a` und `f` liegen beide knapp über der Schwelle. Seit BUG-009 trennt
die 4 (`bcfg`) von der 9 (`abcfg`) ein einziges Segment. Die Messung **kann**
aus sich heraus nicht entscheiden.

### Wie es umgesetzt ist — und warum die Prüfung ehrlich bleibt

Der Leser liefert bei Uneindeutigkeit die **Kandidatenmenge** statt nur `?`
(`digit_reader.segment_candidates`). Der Analyzer prüft dann:

| Fall | Ergebnis |
|---|---|
| Lampenzahl steht unter den Kandidaten | stimmig, aufgelöst — in der Beweiskette vermerkt |
| Lampenzahl steht **nicht** darunter | echter Widerspruch, bleibt sichtbar |

Entscheidend ist die **Richtung**: Die Lampen dürfen zwischen den Kandidaten
*wählen*, aber keinen neuen Wert *setzen*. Melden sie 7, während {4, 9} zur Wahl
steht, bleibt es ein Widerspruch. Die Gegenprobe ist also weiterhin in der Lage,
die Lampen zu widerlegen — genau das unterscheidet sie von einer Scheinprüfung.

Vollständig unabhängig bleibt ohnehin die **Summenanzeige**: Sie stammt aus einem
anderen Ziffernfeld und muss um genau die gezählte Kegelzahl steigen.

### Warum das dem Nachjustieren von Schwellen vorzuziehen ist

Die Alternative wäre gewesen, die Segmentflächen oder die Schwelle so lange zu
verschieben, bis dieser eine Fall stimmt. Das hätte an einer Bahn geholfen und
an einer anderen geschadet — die Ziffern stehen je nach Blickwinkel
unterschiedlich schräg. Die Auflösung über eine zweite Quelle ist unabhängig von
der Geometrie und trägt damit auch für Bahnen und Videos, die noch nicht
vermessen sind.


---

## Der zeitliche Ablauf eines Wurfs

**Vom Nutzer erklärt (2026-08-25)** — die Grundlage dafür, wann welcher Wert
gültig ist:

```
grün AN ─────────────────────────────────────► grün AUS
   │                                              │
   │  Kegel fallen in dieser Zeit                 │  jetzt kann kein Kegel
   │  Wurfzähler springt hoch                     │  mehr fallen: die Lampen
   │  └── ab da genau 4 Sekunden ────────────────►│  zeigen das Ergebnis
```

Drei Folgerungen für die Auswertung:

1. **Die Lampen leuchten bereits, während grün an ist.** Das ist normal und kein
   Fehler — die Kegel fallen ja in dieser Phase.
2. **Gemessen wird bei Grün-AUS**, denn erst dann steht das Ergebnis fest.
3. **Die Räum-Grundlinie gehört kurz NACH Grün-AN**, nicht davor. Vor Grün-AN
   steht noch das Ergebnis des vorherigen Wurfs auf der Tafel.

### Was Punkt 3 gekostet hat

Die Grundlinie wurde mit den Offsets `[0, -4, -8, -12, -16]` **rückwärts**
gemessen — also im Fenster des vorherigen Wurfs. Sie enthielt dadurch dessen
Kegel, und die Differenz ergab null:

```
Bahn 2, Frame 44352:
   Grundlinie (bei Grün-AN):  9 Kegel [1..9]
   Endstand:                  9 Kegel [1..9]
   Differenz = 0  ->  "Räumen: 9 Kegel lagen bereits vor dem Wurf"
```

Alle neun Lampen wurden dabei mit Helligkeit 254 klar als AN erkannt — die
Messung war einwandfrei, nur der **Bezugszeitpunkt** falsch. Betroffen waren acht
Würfe, und 92 Würfe wurden fälschlich als Räumen eingestuft.

Seitdem gilt `baseline_offsets: [0, 6, 12, 18, 25]` — Frames **nach** Grün-AN,
gesammelt während des Wurfs. 25 Frames sind eine Sekunde, deutlich vor dem
Aufschlag des Balls.

### Blinken heißt „alle Neune"

Ebenfalls vom Nutzer: Das Blinken der Lampen ist der **Spezialeffekt für einen
Wurf mit neun Kegeln**, kein allgemeines Verhalten. Die Abhilfe aus BUG-007
(über das Fenster aggregieren, je Lampe das Maximum) bleibt davon unberührt —
sie war richtig, die Deutung war nur zu weit gefasst.


---

## Der Livestream ist dieselbe Produktion

**Vom Nutzer belegt (2026-08-25):** Die vorhandenen Aufnahmen sind Mitschnitte
eines Livestreams auf sporteurope.tv. Overlay-Panel, Tafelmodell und Bildgröße
sind identisch.

```
Aufnahmen:      Panel bei x 493..1481, y  50..215
Livestream:     Panel bei x 445..1465, y   5..310
```

Die leichte Verschiebung ist bekannt und der Grund, weshalb pro Übertragung
kalibriert wird.

### Randbedingungen, vom Nutzer geklärt

| Frage | Antwort |
|---|---|
| Bleibt das Overlay eingeblendet? | **Immer.** Keine Werbeunterbrechung, kein Kameraschnitt. |
| Verschiebt es sich während einer Übertragung? | Nein, innerhalb einer Übertragung stabil. |
| Rückspringen im Stream? | Technisch möglich, aber **nicht betrachtet**. |

Damit entfallen die schwierigen Fälle: Es genügt **eine** Kalibrierung zu Beginn,
und die Analyse muss nicht erkennen, ob gerade etwas anderes im Bild ist.

### Ein Irrtum meinerseits, und was daraus folgt

Aus dem **Vorschaubild** der Seite hatte ich geschlossen, die Übertragung zeige
nur einen Weitwinkel auf Tafeln ohne Kegelraute — und daraus, dass das ganze
Verfahren dort nicht trägt. Das war falsch: Das Vorschaubild ist ein Werbestill,
kein Ausschnitt der Übertragung. Ein Screenshot des Nutzers aus dem laufenden
Stream zeigt das Overlay mit allen vier FUNK-Tafeln samt Kegelraute.

Derselbe Fehler wie in `messen-vor-bauen` beschrieben: **aus einem einzelnen
Bild eine Eigenschaft der Quelle geschlossen.**

### Was der Stream zusätzlich hergibt

Links und rechts stehen Mannschaftstabellen mit **Spielernamen**, und über jeder
Tafel steht, wer gerade auf welcher Bahn spielt:

```
Bahn 2: KV Gelsenkirchen 2 / Erich Wolf
Bahn 5: Heimmannschaft    / Spieler A
```

Diese Felder werden **heute von Hand gepflegt** und nur alle 15 Würfe
nachgetragen — sie automatisch zu füllen ist laut Nutzer der eigentliche Zweck
dieses Werkzeugs. Die Namen stehen in normaler Schrift statt als 7-Segment und
dürften für OCR leichter sein als die Ziffern. Noch nicht umgesetzt.


---

## Negatives Ergebnis: das Maximum-Fenster bringt nichts

**Gemessen 2026-08-26** über alle 486 Wurffenster des 52-Minuten-Videos.

Die Überlegung war: Während eines Wurfs können Lampen nur dazukommen — Kegel
stehen nicht wieder auf. Blinken zieht die Zahl kurz nach unten, das Aufstellen
auf null, aber nie nach oben. Also müsste das **Maximum über das ganze Fenster
von Grün-AN bis zum nächsten Grün-AN** das Ergebnis sein, unabhängig davon, wann
genau `GREEN_OFF` erkannt wird. Damit verschwände der Messzeitpunkt als
Fehlerquelle.

```
A  ab GREEN_OFF (heutiges Verhalten)     380 von 454
B  ab GREEN_ON  (Vorschlag)              380 von 454

A und B unterscheiden sich bei 0 von 486 Fenstern.
```

**Kein einziger Unterschied.** Der Grund ist einleuchtend, sobald man ihn sieht:
Die Lampen halten ihr Ergebnis noch lange nach Grün-AUS — das Aufstellen kommt
erst viel später. Was während der Grünphase gefallen ist, leuchtet bei Grün-AUS
weiterhin. Das bestehende Fenster erfasst also bereits alles.

Der ursprünglich beobachtete Fehler (`GREEN_OFF` bis zu 180 Frames zu spät) war
real, ist aber durch die mitlaufenden Schwellen der grünen Lampe behoben —
deshalb misst sich heute kein Unterschied mehr. **Nicht umgebaut.**

### Ein Fehler in der Messung selbst, der fast zur falschen Deutung geführt hätte

Die 83,7 % sehen alarmierend aus, sind aber ein Artefakt: Als Bezug diente die
Kegelziffer aus **einem einzelnen Frame**, ohne die zeitliche Aggregation der
Pipeline. Die Abweichungen zeigen es deutlich:

```
Differenz Messung minus Ziffer:   +6: 56x   (von 74 Abweichungen)
Beispiele: gemessen 8 / Ziffer 2      gemessen 9 / Ziffer 3
```

8→2 und 9→3 sind beide genau minus 6 — der bekannte Ziffernfehler, konzentriert
auf Bahn 2 und 5. Nicht die Lampen lagen daneben, sondern meine Referenz. In der
Pipeline liegt die Übereinstimmung bei 98,6 %.

**Lehre:** Eine Messung ist nur so gut wie die Wahrheit, gegen die sie misst.
Wer als Referenz eine Größe wählt, die selbst fehleranfällig ist, misst am Ende
diese Größe.

---

## Die grüne Lampe: Perzentile taugen nicht als Wolkentrennung (2026-08-30)

Anlass war ein Phantomwurf auf Bahn 5 bei Frame 40903, der die gesamte folgende
Wurfnummernkette um eins verschob (Spieler A: 16 von 30 Würfen richtig
zugeordnet statt 30 von 30).

### Der Befund im Bild

Ausgegeben mit `tools/export_roi_frames.py`, mit allen kalibrierten Rahmen:
**Die grüne Lampe leuchtet bei F40903 sichtbar.** Sie ging nie aus.

### Der Befund in der Grünspur

```
Frame   Score    P20    P90  Spanne  AUS-Schwelle  Zustand
40894    56,7   37,6   70,0    32,4          50,5  ON
40898    55,6   39,8   70,0    30,2          51,9  UNKNOWN
40903    47,8   40,0   70,0    30,0          52,0  OFF
40906    47,8   41,8   70,0    28,2  fest: 35,0    ON
```

Derselbe Score (47,8) ist einmal AUS und drei Frames später AN. Zwei Ursachen
greifen ineinander:

1. Die Bahn lag **71 % des Fensters auf AN**. Damit ist das 20. Perzentil kein
   AUS-Niveau mehr, sondern der untere Rand der AN-Wolke. Die daraus
   errechnete AUS-Schwelle (52,0) liegt **innerhalb** der AN-Wolke.
2. Die Spanne P90−P20 wackelte um die Sperre `adaptive_min_span` (30,0). Fällt
   sie darunter, gelten schlagartig die festen Schwellen (45/35) — die Schwelle
   springt um 17 Punkte.

Perzentile setzen voraus, dass beide Zustände im Fenster im erwarteten
Verhältnis vorkommen. Diese Voraussetzung ist am Material nicht erfüllt.

### Das Histogramm desselben Fensters

```
18-20   26 | 20-22   24 | 22-24   56 | 24-26  127     <- AUS-Wolke
26-28    6 | 28-30    1 | 30-32   11 | 32-34   32
34-36    6 | 36-38    5 | 38-40    1 | 40-42    8     <- Tal
42-44   45 | 44-46    5 | 46-48   54 | 48-50    9
50-52   15 | 52-54   70 | 54-56  164 | 56-58  176     <- AN-Wolke
58-60  118 | 60-62  120 | ... | 76-78    5
```

Zweigipflig und eindeutig. Geglättet über drei Bins liegt das tiefste Tal bei
**37**. Damit ist 47,8 durchgehend AN, und der Phantomwurf entsteht nicht.

### Gegenrechnung über die volle Grünspur

`tools/fit_green_histogram.py` spielt die aufgezeichnete Spur (297 715 Frames
je Bahn) durch das Verfahren:

```
Fenster   Bahn 2   Bahn 3   Bahn 4   Bahn 5     GREEN_OFF-Ereignisse
   1500      426      422      431      418
   7500      425      420      425      431
  22500      425      421      425      430
  45000      426      420      425      426
im Lauf      431      424      425      417
```

Höchstens 13 Ereignisse Unterschied über eine Spanne von 1 zu 30 in der
Fensterlänge — das Verfahren hängt nicht an dieser Zahl. Gewählt wurden 22500
Frames (15 min) nach Vorgabe des Nutzers.

Der Anteil zweigipfliger Fenster liegt auf Bahn 2–4 bei 96–97 %, auf Bahn 5 nur
bei 83 %. Das ist kein Mangel, sondern die richtige Antwort: Bahn 5 hat das
schwächste Signal, und dort greift die Sperre häufiger.

### Ergebnis am Material

Lauf F28000–56000, gleiche Kalibrierung, nur der Detektor geändert:

| | vorher | nachher |
|---|---|---|
| Spieler A, Bahn 5 | 16/30 | **30/30** |
| Spieler B, Bahn 3 | 30/30 | **30/30** |

Kein Wurf erfunden, keiner verloren.

---

## Ziffernerkennung: Wie gut ist sie wirklich? (2026-08-30)

Beobachtung des Nutzers am Bildbeleg: Die Ziffern sind in der Rotmaske
eindeutig zu lesen, die Erkennung liefert trotzdem `?`.

### Wo der Weg abbricht (4320 beleuchtete Zellen)

```
gueltiges Sieben-Segment-Muster gelesen            58,0 %
kein gueltiges Muster -- auf das naechste geraten  32,1 %
von der Helligkeitssperre verworfen                 9,8 %
mehrdeutig / kein Muster in Reichweite              0,1 %
```

Die 32 % beschreiben den **Weg**, nicht die Fehlerquote — gegen eine belastbare
Wahrheit gemessen landet die Reparatur auf Abstand 1 fast immer richtig.

### Eine belastbare Wahrheit — und wie man sie verfehlt

Die Idee (Nutzer, 2026-08-30): Nur Würfe **in die Vollen** nehmen. Dort standen
vorher alle neun Kegel, also zeigen Lampen und Ziffer dieselbe Zahl. Erkennbar
ohne jede Ziffernlesung: Der bestätigte Lampenstand war vorher leer.

Der naive Weg — einfach die leuchtenden Lampen zählen — geht schief, weil die
Lampen **kumulativ** zeigen, was liegt, die Ziffer aber nur den aktuellen Wurf:

```
leuchtende Lampen   Ziffer   in Wahrheit
          9            2     7, dann Raeumung 2
          9            1     8, dann Raeumung 1
          9            4     5, dann 4
          9            9     alle neune, erster Wurf
```

Von 288 so als `9` beschrifteten Bildern waren nur 45 wirklich eine 9. Die
Pipeline rechnet das längst richtig (`neu_gefallen = end_pins - base_pins`);
das Messwerkzeug tat es nicht. **Eine Wahrheit, die man nicht prüft, misst am
Ende die eigene Annahme.**

Auf Bahn 4 und 5 bleibt die Beschriftung auch dann unsicher: Dort ist die
Lampenlesung Frame für Frame unzuverlässig (Bahn 5, Label 7: nur 37 % stimmen
mit dem Bild überein; Bahn 2 und 3: 92–100 %). Die Pipeline fängt das über ihre
zeitliche Aggregation ab — ein Einzelbild-Werkzeug nicht.

### Ergebnis auf Bahn 2 und 3

| Erkenner | vorher | nach der Änderung |
|---|---|---|
| Segmentabtastung | 95,7 % | **96,5 %** |
| davon unlesbar | 13 von 420 | **1 von 402** |
| nächster Mittelpunkt | 96,9 % | 95,8 % |
| 3 nächste Nachbarn | 96,4 % | — |

Ein formbasierter Erkenner (Form als Ganzes statt sieben Flächen) bringt
nichts — er liegt im selben Bereich. Die Segmentabtastung bleibt.

### Die Änderung

`min_display_brightness` wird auf das **Maximum** des Rotkanals angewandt statt
auf das 95. Perzentil, Schwelle 200 statt 230. Eine `1` leuchtet mit zwei von
sieben Segmenten und bleibt gemittelt dunkler als jede andere Ziffer:

```
Bahn 5, F40903    angezeigt   P95   Maximum   gelesen
throw_number [2]      1       220     254       ?  -> jetzt 1
total_b      [2]      1       229     255       ?  -> jetzt 1
pin_count    [1]   (dunkel)    97     114       ?     bleibt ?
```

Über 4800 Zellen, Anteil im unsicheren Bereich 150–245: 95. Perzentil 24,9 %,
99. Perzentil 6,5 %, **Maximum 3,6 %**. Dunkle Zelle 114–119, leuchtende
246–255 — die Schwelle 200 liegt in der Lücke.

Gegenlauf gegen das Protokoll (F28000–56000): Spieler A 30/30, Spieler B 30/30 — unverändert.


---

## Spielwechsel: Wann steht `000 0000` — und wann sieht jemand hin? (2026-08-30)

Die Erkennung zählte bei nahezu gleicher Wurfzahl (~370 je Bahn) völlig
verschieden viele Spielenden: Bahn 2 nur zwei, Bahn 3 dreizehn.

### Was die Tafel wirklich zeigt

`tools/measure_zero_display.py` liest Wurfnummer und Summe **ohne jede
Bedingung**, Frame für Frame, für alle vier Bahnen:

```
Abschnitt um F126600           Abschnitt um F164600
  Bahn 2  F127115-F128475  54 s   Bahn 2  F164535-F166780  90 s
  Bahn 3  F126680-F128715  81 s   Bahn 3  F165220-F166735  61 s
  Bahn 4  F126535-F128820  91 s   Bahn 4  F165695-F166745  42 s
  Bahn 5  F126825-F128915  84 s   Bahn 5  F165590-F166600  40 s
```

Der Nullzustand steht also auf allen Bahnen, 40 bis 91 Sekunden lang, und er
ist lesbar (Bahn 3 und 5: 100 % der Messungen darin, Bahn 2: 53–67 %).

### Warum er trotzdem nicht erkannt wurde

Die Pipeline las die späten Felder nur bei offenem Wurffenster — also zwischen
GREEN_OFF und dem nächsten GREEN_ON. Aus der Grünspur:

```
Bahn 2   GREEN_OFF F126877 -> GREEN_ON F127177 -> GREEN_OFF F128593
         000/0000 begann F127115. Fenster noch 62 Frames offen. Verpasst.
         Danach 1416 Frames Gruen AN -- niemand sah hin.
Bahn 3   GREEN_OFF F126108 -> GREEN_ON F126964
         000/0000 begann F126680. Fenster noch 284 Frames offen. Erkannt.
```

**Nicht die Ziffernerkennung war schuld, sondern die Bedingung, unter der
gelesen wurde.**

### Wie lang sind die Fehllesungs-Strähnen?

Eine Sperre gegen Doppelmeldungen muss wissen, wann die Anzeige den
Nullzustand wirklich verlassen hat. Gemessen im Abschnitt F164535–F166780,
Takt 25 Frames — Strähnen von Nicht-Null-Messungen **innerhalb** des
Nullzustands:

```
Bahn 2   17 Straehnen, laengste 3   Verteilung {1: 14, 2: 1, 3: 2}
Bahn 3    0 Straehnen
Bahn 4    4 Straehnen, laengste 6   Verteilung {1: 1, 2: 1, 4: 1, 6: 1}
Bahn 5    0 Straehnen
```

Mit einer Schwelle von 3 meldete Bahn 4 denselben Wechsel dreimal. Bei 10 ist
vier Messungen Luft über dem Maximum.

### Ergebnis

```
F124000-F131000:  4 Meldungen -- Bahn 4, 3, 5, 2, je genau eine
F163000-F168500:  4 Meldungen -- Bahn 2, 3, 5, 4, je genau eine
```

Die erkannten Frames liegen 30 bis 135 Frames nach dem unabhängig gemessenen
Beginn — das ist die Bestätigungszeit. Protokoll unverändert bei 30/30.


---

## Der Fehlwurfzähler auf Bahn 4: ein Störwert, der die Stabilitätsprüfung übersteht (2026-08-31)

Im vollständigen Lauf über den Spieltag zählte Bahn 4 **463 Würfe bei 426
Grünzyklen** — mehr Würfe als Zyklen. Die anderen Bahnen lagen bei 420–431.

### Wo die Würfe herkamen

```
Wuerfe mit 0 Kegeln je Bahn:   Bahn 2: 4 | Bahn 3: 1 | Bahn 4: 48 | Bahn 5: 8
Nullwuerfe im Protokoll:       Bahn 2: 0 | Bahn 3: 0 | Bahn 4:  1 | Bahn 5: 1
```

Alle Anstiege des Fehlwurfzählers nach Sprunghöhe:

```
Bahn 2   +1: 1
Bahn 3   keine
Bahn 4   +1: 1,  +3: 14
Bahn 5   +1: 2
```

Vierzehn Sprünge um drei, alle auf einer Bahn, jeder als drei Nullwürfe
gebucht: **42 erfundene Würfe**.

### Der Bildbeleg

Frame 270290, Bahn 4, `left_display`:

```
Tafel zeigt:      0 0
Erkenner liest:   0 3      (Helligkeit 244 / 255 -- die Zelle ist hell)
```

Die zweite Stelle wird als 3 gelesen. Der Wert 3 ist für dieses Feld seit dem
2026-08-25 als Störwert bekannt — die damalige Messung über 52 Minuten auf
Bahn 2 ergab Rohwerte `{0: 10711, 1: 776, 3: 147, 7: 3, 70: 1}`. Dort hielt der
Stabilitätsfilter (5 gleiche Lesungen in Folge) ihn ab. Auf Bahn 4 hält er nicht.

### Warum eine Plausibilitätsgrenze trägt, wo der Filter versagt

Der Zähler wird alle 10 Frames gelesen. Ein Wurfzyklus dauert gemessen 216 bis
338 Frames. Zwischen zwei Lesungen kann also **höchstens ein Wurf** liegen —
unabhängig davon, wie stabil ein Messwert aussieht.

Das ist der Unterschied zwischen einem Filter und einem Argument: Der Filter
fragt „habe ich das oft genug gesehen", das Argument fragt „kann das überhaupt
sein".

### Ergebnis

Gegenlauf F268000–280000, dasselbe Fenster:

```
5 x verworfen als Fehllesung
Wuerfe je Bahn: {2: 17, 3: 19, 4: 18, 5: 18}   davon 0 Kegel: keine
```

---

## Der Anlauf der grünen Lampe (2026-09-01)

**Anlass:** Auf Bahn 2 fehlte im Satz 2.3 ein Räumwurf zwischen Wurf 25
(F180238) und Wurf 27 (F181062). Vermutet wurde eine zu kurze Grünphase.

**Quelle:** `gruenspur.csv` und `lampenspur.csv` des Laufs
`lauf_2026-09-01_14-08-10` über den Spieltag 2026-08-22.

### Die Grünphase war nicht zu kurz

| Zyklus (Bahn 2) | Frames | Median-Score | Max | UNKNOWN |
|---|---|---|---|---|
| Wurf 23 | 180 | 68,8 | 73,8 | 2,2 % |
| Wurf 24 | 210 | 70,0 | 78,8 | 2,4 % |
| Wurf 25 | 200 | 71,2 | 77,5 | 0,0 % |
| **verworfen** | **175** | **60,0** | **70,0** | **57,1 %** |
| Wurf 27 | 248 | 71,2 | 78,8 | 0,0 % |

Die Dauer liegt im Normalbereich. Auffällig ist der Score: Median 60,0 gegen
sonst 68 bis 74, und mehr als die Hälfte der Frames in der Totzone zwischen
AUS- und AN-Schwelle.

### Die Schwelle steht ruhig

Über **484 Übergänge nach ON** auf Bahn 2 beträgt der erste ON-Score fast immer
exakt **62,5** (Median aller ersten ON-Scores: 63,7; Min 51,2; Max 78,8). Die
AN-Schwelle des gleitenden Histogramms ist also stabil — das Signal dieses
Zyklus war schwächer, nicht der Maßstab verrutscht.

### Der Anlauf als Kennzahl

Der Score kroch über rund 70 Frames durch die Totzone:

```
F180435  22,5   F180438  50,0   F180468  60,0   F180498  61,3   F180507  62,5
```

Gesunde Zyklen springen in ein bis sechs Frames über die Schwelle. Diese
Differenz — die Zahl der UNKNOWN-Frames unmittelbar vor dem ersten ON — heißt
hier **Anlauf** und ist mit `tools/measure_green_onset.py` messbar.

Über den ganzen Spieltag (1706 Zyklen, 1690 Würfe):

```
Bahn  Zyklen  ohne Wurf   Anlauf>20   beides
   2     429          8          10        1
   3     421          2           9        1
   4     426          4          12        2
   5     430          7          25        1
```

Fünf Zyklen vereinen langen Anlauf und fehlenden Wurf: Bahn 2 F180506 (Anlauf
56), Bahn 3 F66750 (50), Bahn 4 F47150 (78) und F144401 (46), Bahn 5 F296850
(92).

### Warum daraus ein verlorener Wurf wird

Der Zustandsautomat meldete GREEN_ON erst bei F180508, rund 69 Frames (2,8 s)
nach dem tatsächlichen Einschalten. Die Grundlinie wird bei GREEN_ON plus
`baseline_offsets` [0, 6, 12, 18, 25] gemessen, hier also F180508 … F180533.
Aus der Lampenspur:

```
F180500   8 Lampen an   pin_lamp_2: 164,7  OFF
F180525   9 Lampen an   pin_lamp_2: 253,4  ON
```

Der geräumte Kegel fiel **innerhalb** des Grundlinienfensters. Da
`aggregate_pin_readings` über die Frames vereinigt, hob eine einzige Messung
die Grundlinie auf neun. Ergebnis neun, Grundlinie neun, nichts neu gefallen —
`discard_unchanged_cycles` verwarf den Zyklus. Siehe BUG-016.

Gegenprobe: Bei GREEN_ON um F180440 hätte das Fenster F180440 … F180465
umfasst; dort lagen nachweislich acht Kegel.

### Wie oft die Vereinigungsregel sonst stört

242 Räumwürfe (Grundlinie > 0) im Lauf, davon **2** mit Abweichung zwischen
Lampenzahl und Tafelziffer. Die Regel ist im Normalfall harmlos — sie hat nur
keine Reserve gegen ein verspätetes GREEN_ON.

### Offen

Warum der Score in diesem Zyklus langsam anstieg statt zu springen, ist nicht
entschieden. Ein allmählich weichender Teilverdecker passt zum Verlauf, ist aber
ohne Blick in die Frames nicht belegt — das Material lag nur als Stream vor.
Siehe `docs/OPEN_QUESTIONS.md`.

### Probe: Was passiert, wenn die Grundlinie geschnitten statt vereinigt wird?

**Anlass:** Naheliegende Abhilfe gegen BUG-016 — für die Grundlinie nicht das
Maximum über die Frames nehmen. Vor dem Einbau geprüft.

**Wie gemessen:** Die gespeicherten ROI-Ausschnitte der Ereignisse
(4 Bahnen × ~200 Ereignisse × 9 Lampen = 7245 Lampen-Ereignisse, je 10 Frames
über 38 Frames Spanne) — dasselbe Zeitmaß wie das Grundlinienfenster. Während
eines Ereignisses fällt kein Kegel mehr, jede Abweichung zwischen den zehn
Messungen ist Blinken.

```
alle aus       970  13,39 %
alle an       3524  48,64 %
geteilt       2751  37,97 %     <- hier entscheiden die Regeln verschieden
```

**Fast vier von zehn Lampen blinken innerhalb des Fensters.** Damit ist der
Schnitt erledigt, bevor er gebaut ist. Gegen die Tafel-Ziffer als Wahrheit,
655 Würfe in die Vollen:

| Regel | richtig | Quote | häufigster Fehler |
|---|---|---|---|
| Vereinigung (heute) | 616 | 94,05 % | +1 Kegel: 19× |
| mindestens 2 Messungen | 619 | 94,50 % | +1 Kegel: 16× |
| Mehrheit | 458 | 69,92 % | −9 Kegel: 90× |
| Schnitt | 319 | 48,70 % | −9 Kegel: 192× |

Der Schnitt verliert bei 192 Würfen **alle neun** Kegel: Neun Lampen brannten,
keine einzige durchgehend. In der Testsuite schlagen mit dem Schnitt drei
Integrationstests fehl (`test_pipeline_smoke.py`), darunter der einfachste
Durchlauf überhaupt.

> Die absoluten Quoten sind eine Nachbildung mit fester Trennschwelle (204)
> statt der gleitenden Grundlinie des echten Detektors — der Lauf selbst
> erreicht 720/720. Der **Vergleich** der Regeln trägt trotzdem, weil alle vier
> dieselbe Nachbildung benutzen.

### Wie lang muss das Grundlinienfenster sein?

Vereinigung über die ersten *n* Messungen, gegen dieselbe Wahrheit:

| Messungen | Spanne | richtig | Quote |
|---|---|---|---|
| 3 | 5 F | 508 | 77,56 % |
| 4 | 10 F | 567 | 86,56 % |
| **5** | **16 F** | **618** | **94,35 %** |
| 6 | 22 F | 618 | 94,35 % |
| 8 | 32 F | 617 | 94,20 % |
| 10 | 38 F | 616 | 94,05 % |

Ab fünf Messungen über 16 Frames ist nichts mehr zu gewinnen — danach wird es
minimal schlechter. Das heutige Grundlinienfenster reicht mit
`baseline_offsets` bis +25 also **neun Frames weiter in die Grünphase hinein,
als es müsste**, ohne dafür etwas zu bekommen.

Gerettet hätte das den Wurf auf Bahn 2 trotzdem nicht: Der Kegel fiel zwischen
F180500 und F180525, das verkürzte Fenster hätte F180508 … F180524 umfasst. Bei
69 Frames Verspätung liegt auch ein kurzes Fenster mitten in der Fallzeit. Die
Länge ist die Angriffsfläche, der Startzeitpunkt ist die Ursache.

### Die Grundlinie aus zwei Quellen (2026-09-01)

Nutzeridee: Beim Räumen bleiben die Ergebnislampen leuchten, bis der nächste
Wurf abgeschlossen ist — der Stand kurz **vor** dem Grün-AN müsste derselbe
sein wie kurz danach, und er hängt an keiner Erkennung.

Der Einwand stand im Code („vor GREEN_ON steht noch das Ergebnis des vorherigen
Wurfs"). Gegen 1610 Würfe geprüft, mit der Tafel-Ziffer als Wahrheit:

| Grundlinie aus | richtig | Quote |
|---|---|---|
| nur nachher (bisher) | 1604 | 99,63 % |
| nur vorher | 1601 | 99,44 % |
| **Schnittmenge beider** | **1604** | **99,63 %** |

Die beiden Einzelmessungen unterscheiden sich bei 3 von 1610 Würfen — dort
hatte die Anlage erst 17 bis 24 Frames vor dem Grün-AN gelöscht, der Stand
davor war also noch der alte. Beide Fehlerarten machen die Grundlinie zu
**groß**, nie zu klein. Deshalb die Schnittmenge.

Verworfene Zyklen kommen damit zurück — nachgewiesen im Vollauf weiter unten.

**Reserve — korrigiert.** Zuerst stand hier "der Ball braucht rund 100
Frames"; die Zahl kam aus einem Kommentar, der den Abstand Wurfzähler →
GREEN_OFF meint, nicht den Einschlag. Nachgemessen, 1448 Zyklen vom erkannten
Grün-AN bis zur ersten neu leuchtenden Lampe:

| Wurfart | Anzahl | 1. Perzentil | Median | unter 25 F | unter 50 F |
|---|---|---|---|---|---|
| in die Vollen | 1207 | 67 F (2,7 s) | 166 F (6,6 s) | 0 | 0 |
| Räumen | 235 | 50 F (2,0 s) | 114 F (4,6 s) | 0 | 2 (0,85 %) |

Beim Räumen wird zügiger geworfen — genau die Wurfart, die BUG-016 trifft. Die
Tabelle misst ab dem *erkannten* Grün-AN und enthält die fünf verworfenen
Zyklen nicht, die stehen ja in keiner `wuerfe.csv`.

**Blinken die Lampen synchron?** Nein — von 30 415 Messungen mit null
brennenden Lampen haben nur 204 (0,67 %) unmittelbar davor *und* danach
brennende Lampen. Eine Null ist also fast immer ein echtes Löschen, kein
gemeinsamer Aussetzer.


## Der Fix an zwei Quellen, am ganzen Spieltag nachgemessen (2026-09-01)

Der Lauf `lauf_2026-09-01_17-38-42` über 312 784 Frames, Zeile für Zeile gegen
den Vergleichslauf `14-08-10` derselben Quelle gehalten:

| | vorher | nachher |
|---|---|---|
| Würfe | 1690 | **1695** |
| davon VALID | 1662 | **1667** |
| EMPTY / ERROR | 13 / 15 | **13 / 15** |
| Räumwürfe | 242 | **247** |
| Kegel gesamt | 11 477 | **11 483** |

**Fünf Würfe kamen hinzu, keiner ging verloren.** Die Differenzmenge in der
Gegenrichtung ist leer — kein einziger Wurf des alten Laufs fehlt im neuen.
EMPTY und ERROR bleiben Zahl für Zahl gleich: Der Fix bringt nur saubere Würfe
hinzu, er verdirbt keinen bestehenden.

Die fünf, jeder mit der Tafel-Ziffer als unabhängiger Bestätigung:

| Bahn | Grün-AN | Meldung | Grundlinie | Kegel | Wurfbild | Ziffer |
|---|---|---|---|---|---|---|
| 4 | 41026 | 41147 | 7 | 2 | 5 7 | **2** |
| 3 | 66750 | 66871 | 8 | 1 | 8 | **1** |
| 4 | 144401 | 144523 | 7 | 1 | 4 | **1** |
| 2 | 180506 | 180615 | 8 | 1 | 7 | **1** |
| 5 | 296850 | 296973 | 8 | 1 | 6 | **1** |

Alle fünf sind Räumwürfe, alle fünf VALID, und bei allen fünf nennt die
Anzeigetafel dieselbe Kegelzahl wie die Lampen — eine Quelle, die am Fix nicht
beteiligt ist.

### Die zweite Quelle greift nur dort ein, wo sie gebraucht wird

Über 1702 Grünzyklen meldet das Log genau **fünf** Widersprüche zwischen dem
Stand vor dem Grün-AN und dem danach — und es sind genau diese fünf. In den
übrigen 1697 sind beide Messungen einig, die Schnittmenge ändert dort nichts.
Der Eingriff ist also so eng, wie er sein soll.

### Was die fünf verbindet, ist nicht der Anlauf

Die Vorhersage aus der Analyse traf in vier von fünf Fällen. Bahn 4 F47150 war
erwartet worden und kam nicht zurück; stattdessen kam Bahn 4 F41026, den die
Anlauf-Heuristik nicht gefunden hatte — sein Anlauf betrug nur 7 Frames.

Der gemeinsame Nenner ist ein **schwaches Grünsignal**:

| Bahn | Grün-AN | Anlauf | max. Score der Phase |
|---|---|---|---|
| 4 | 41026 | 7 | 56,2 |
| 3 | 66750 | 50 | 68,1 |
| 4 | 144401 | 46 | 60,0 |
| 2 | 180506 | 56 | 70,0 |
| 5 | 296850 | 92 | **44,4** |

Gesunde Zyklen auf Bahn 2 erreichen 77 bis 79. Der lange Anlauf ist ein
*Symptom* der schwachen Phase, nicht die Ursache — und nicht das einzige.
Daraus folgt etwas Beruhigendes über den Fix: Der Stand aus der Pause hängt an
**gar keiner** Eigenschaft der Grünerkennung. Er trägt deshalb auch dort, wo
sie auf eine Weise irrt, die noch niemand vorhergesehen hat.

### Bahn 4 hat ein Lampenproblem, das hiermit nichts zu tun hat

Bei F47150 lagen die beiden stehenden Kegel dauerhaft in der Totzone: Lampe 5
und 7 messen über 350 Frames stabil 210, bei AUS-Schwelle 198 und AN-Schwelle
234 — also durchgehend UNKNOWN, während die sieben liegenden Kegel bei 252
klar ON sind.

UNKNOWN-Anteil je Bahn, über alle neun Lampen und den ganzen Spieltag:

| Bahn | UNKNOWN |
|---|---|
| 2 | 0,14 – 0,34 % |
| 3 | 0,78 – 5,72 % |
| 4 | **5,71 – 9,04 %** |
| 5 | 0,53 – 7,13 % |

Das Helligkeitshistogramm über alle 438 813 Messungen zeigt, warum: Die
AUS-Wolke reicht von 130 bis 219 und läuft flach aus, die AN-Wolke sitzt scharf
bei 240–259. Dazwischen liegt bei 220–239 ein Tal mit 0,93 %. Ein Wert von 210
ist also eine **helle AUS-Lampe**, keine halb leuchtende — die AUS-Schwelle bei
198 ist für diese ROIs nur zu tief angesetzt.

Warum die zweite Quelle bei F47150 trotzdem neun statt sieben Kegel lieferte,
lässt sich aus den vorhandenen Spuren nicht belegen: Die Lampenspur schreibt
alle 25 Frames, die Pause-Messungen laufen alle 5. Offen als Q13.
## Bahn 4: kein Farbstich, sondern eine Schwelle an der falschen Stelle (2026-09-01)

Anlass war die Frage, ob ein Weißabgleich Bahn 4 helfen würde. Sie lässt sich
aus der Lampenspur nicht beantworten — die schreibt nur `value`, nicht die
Kanäle. Also 5400 Messungen der einzelnen Farbkanäle direkt an der Quelle
(`tools/measure_lamp_channels.py`, Frames 15000–30000, alle 100):

| Bahn | Zustand | B | G | R | value |
|---|---|---|---|---|---|
| 2 | AUS | 120,0 | 128,4 | 147,9 | 147,9 |
| 3 | AUS | 138,4 | 146,6 | 166,7 | 166,8 |
| **4** | **AUS** | **159,6** | **163,0** | **181,1** | **181,4** |
| 5 | AUS | 138,8 | 145,4 | 160,3 | 160,4 |
| 2 | AN | 202,6 | 240,2 | 254,2 | 254,8 |
| **4** | **AN** | **190,8** | **215,6** | **250,4** | **250,4** |

Bahn 4 ist auf allen drei Kanälen um rund 34 Punkte angehoben — gleichmäßig.
Das ist ein **Schwarzwert-Versatz**, kein Farbstich.

**Warum ein Weißabgleich hier nichts ausrichtet.** Der Detektor misst
`value = max(B,G,R)`. Gemessen ist **Rot in 99,7 bis 100 % aller Fälle der
größte Kanal** — auf jeder Bahn, bei AUS wie bei AN:

| Bahn | AUS | Totzone | AN |
|---|---|---|---|
| 2 | 100,0 % | 100,0 % | 100,0 % |
| 3 | 100,0 % | 100,0 % | 100,0 % |
| 4 | 99,7 % | 100,0 % | 100,0 % |
| 5 | 100,0 % | — | 100,0 % |

Der Messwert hängt damit ausschließlich am Rotkanal. Blau und Grün zu
skalieren ändert ihn nicht; Rot zu skalieren verschiebt AUS und AN gemeinsam.
Ein Weißabgleich ist multiplikativ, der Fehler ist additiv — das falsche
Werkzeug. Simuliert bringt er Bahn 4 **−6,6** Kontrastpunkte.

### Die Formel arbeitet gegen sich selbst

Die adaptive Schwelle rechnet `Niveau + Anteil × (255 − Niveau)`. Je höher das
Ruheniveau, desto kleiner der Spielraum — und desto enger der Abstand zur
Schwelle. Genau dort, wo wegen der breiteren Streuung der größte Abstand nötig
wäre, gibt sie den kleinsten:

| Bahn | Niveau | AUS-Schwelle | Abstand | AUS p95 | Reserve |
|---|---|---|---|---|---|
| 2 | 145,2 | 194,3 | 49,1 | 170,7 | **+23,6** |
| 3 | 165,6 | 194,3 | 28,7 | 196,7 | −2,4 |
| 4 | 182,1 | 204,7 | **22,6** | 213,5 | **−8,8** |
| 5 | 162,2 | 194,3 | 32,1 | 201,4 | −7,1 |

Bahn 2 bekommt 49 Punkte Abstand, Bahn 4 nur 23 — bei breiterer Streuung. Ist
die Reserve negativ, landen über 5 % der AUS-Messungen in der Totzone. Genau
das misst die UNKNOWN-Rate.

**Der Platz ist da, er wird nur nicht genutzt.** Zwischen AUS p95 (213,5) und
AN p5 (245,7) liegen auf Bahn 4 volle 32 Punkte brach. Und in der Totzone
steckt nichts, was verloren ginge: Von allen UNKNOWN-Messungen liegt auf
**keiner** Bahn eine einzige im AN-Bereich (0,0 %), auf Bahn 4 dagegen 63 % im
normalen AUS-Bereich.

| `baseline_off_fraction` | Bahn 2 | Bahn 3 | Bahn 4 | Bahn 5 |
|---|---|---|---|---|
| 0,31 (heute) | 0,49 % | 2,88 % | **6,71 %** | 5,10 % |
| 0,50 | 0,24 % | 0,36 % | **0,87 %** | 0,53 % |
| 0,55 | 0,22 % | 0,29 % | **0,51 %** | 0,37 % |

Das ist eine Simulation über die aufgezeichneten Werte, kein Lauf — die Zahl
gehört erst nach einem Vollauf mit Gegenprobe in die Konfiguration. Siehe Q13.

**Was das Kegeln angeht:** Bahn 4 trägt 11 der 15 ERROR-Würfe des Spieltags
(2,6 % ihrer Würfe gegen 0,0 % auf den Bahnen 2 und 3). Gegen die Tafel-Ziffer
gehalten liegt sie mit 0,25 % Abweichung dagegen im Feld — der Schaden zeigt
sich als Unentschiedenheit, nicht als falsche Zahl.

### Die ROIs sitzen richtig — angesehen, nicht vermutet

Die zweite Erklärung war, dass die ROIs von Bahn 4 ungünstiger sitzen. Frame
20000 auf beiden Bahnen exportiert (`tools/export_roi_frames.py`, Bilder unter
`debug/roi_bahn2/` und `debug/roi_bahn4/`): Die Rahmen sitzen auf beiden Bahnen
sauber und zentriert auf den Lampen, sind gleich groß (80 × 75 normiert auf
allen vier Bahnen) und die Bilder sind gleich unscharf.

Was der Vergleich stattdessen zeigt: **Die Tafel auf Bahn 4 ist überstrahlt.**
Gehäuse und Lampenkappen sind heller und blasser, wo dieselbe Tafel auf Bahn 2
bräunlich und satt erscheint. Die ausgeschalteten Lampen sind glänzende
Halbkugeln — sie spiegeln die hellere Umgebung, und genau das hebt ihren
AUS-Wert.

Die Farbsättigung `(max − min) / max` bestätigt es, und zwar gegenläufig:

| Bahn | AUS | AN | AN-Messungen bei ≥ 254 |
|---|---|---|---|
| 2 | **18,2 %** | 20,3 % | **84,3 %** |
| 3 | 16,2 % | 21,9 % | 51,2 % |
| 4 | **11,6 %** | 23,6 % | **2,6 %** |
| 5 | 13,4 % | 25,4 % | 11,6 % |

Bei AUS ist Bahn 4 am flachsten — Streulicht hebt alle Kanäle gemeinsam. Bei AN
ist sie am gesättigtsten, weil sie als einzige nicht in die Sättigung läuft; wo
alle Kanäle gegen 255 gehen, verschwindet der Farbabstand ohnehin.

Bahn 4 ist also nicht anders gefärbt, sondern hat den engeren nutzbaren
Bereich: Schwarzwert angehoben, Weißwert nicht ausgereizt.

### Die grüne Lampe folgt demselben Muster — aber über einen anderen Mechanismus

Sie wird nicht über `max(B,G,R)` gelesen, sondern über eine HSV-Maske
(`inRange(40,80,80 … 90,255,255)`); der Score ist der Anteil passender Pixel.
Dort zählt die **Sättigung**, und die Maske verlangt mindestens 80:

| Bahn | AUS p95 | AN p5 | Lücke | UNKNOWN |
|---|---|---|---|---|
| 2 | 37,5 | 66,2 | **28,7** | 0,67 % |
| 3 | 45,8 | 68,1 | 22,3 | 0,96 % |
| 4 | 40,0 | 55,0 | **15,0** | 1,36 % |
| 5 | 31,1 | 42,2 | **11,1** | 3,20 % |

Bahn 5 ist hier die schwächste, nicht Bahn 4 — die Rangfolge der Kegellampen
überträgt sich also nicht.

**Auch hier ist die Sättigung nicht der Engpass.** Gemessen über 10 000 Frames,
über die grün getönten Pixel der Lampe:

| Bahn | Zustand | Score | Sättigung | Helligkeit | grüner Anteil |
|---|---|---|---|---|---|
| 2 | AN | 71,9 | 167,8 | 180,2 | 76,2 % |
| 3 | AN | 77,8 | 167,3 | 193,8 | 80,6 % |
| 4 | AN | **62,5** | **151,7** | 184,4 | 75,0 % |
| 5 | AN | **58,9** | **141,2** | 178,3 | 83,3 % |

Die Maske verlangt Sättigung ≥ 80. Gemessen werden 141 bis 168 — die Reserve
ist auf jeder Bahn mehr als doppelt so groß wie die Anforderung. Der
Score-Unterschied entsteht nicht im Kern der Lampe, sondern an ihrem **Rand**:
Auf Bahn 2 fallen 4,3 Prozentpunkte der grün getönten Pixel durch die Maske,
auf Bahn 4 sind es 12,5.

Damit zielt auch hier ein Weißabgleich am Problem vorbei. Der begrenzende
Faktor ist die Randschärfe, nicht die Farbe — und die Lücke zwischen AUS (28,8)
und AN (62,5) ist auf Bahn 4 immer noch vorhanden, nur schmaler.

## Der Kegellampen-ROI: 12 × 11 Pixel, und was ein engerer bringt (2026-09-01)

Anlass war die Frage, ob ein kleinerer Rahmen — „nur noch die mittleren Pixel"
— die Trennung verbessert. Gemessen mit `tools/measure_roi_shrink.py` über
10 800 Ausschnitte auf zwei Strecken (Frames 15000–30000 und 250000–265000).

**Erste Überraschung: Der Rahmen ist bereits winzig.** Die 80 × 75 der
Kalibrierung sind normierte Einheiten; im Bild sind es **12 × 11 Pixel**. Eine
Verkleinerung auf 30 % ließe 3 × 3 Pixel übrig, und davon nähme der
Kernfilter nochmals die hellsten 30 % — drei Pixel.

**Die Kennzahl** ist die Trennlücke `p5(AN) − p95(AUS)`: der Abstand zwischen
dem dunkelsten Zwanzigstel der leuchtenden und dem hellsten der dunklen
Messungen. Der Kontrast der Mediane taugt nicht — er kann groß sein, während
sich die Ränder berühren.

### Befund 1: Der halbe Gewinn kommt vom Nachzentrieren

Bahn 4, Zuschnitt auf 80 %, frühe Strecke:

| | Trennlücke |
|---|---|
| heute (100 %) | 44,8 |
| 80 %, geometrisch zentriert | 49,0 |
| 80 %, **auf den Lampenschwerpunkt zentriert** | **54,3** |

Die Lampen sitzen im Median 4–10 % oberhalb und links der Rahmenmitte, im
Extremfall 15 % daneben — bei 12 Pixeln knapp zwei Pixel. Der Gewinn zeigt
sich an der AN-Seite: Bahn 4 steigt von 245,3 auf 253,5 (p5), die Lampen
**sättigen endlich** wie auf Bahn 2. Die AUS-Seite bleibt fast unverändert.

### Befund 2: Kernfilter und Rahmengröße ersetzen einander

Bahn 4, frühe Strecke:

| Zuschnitt | mit Kernfilter (70) | ohne Kernfilter |
|---|---|---|
| 100 % | 44,8 | 16,3 |
| 80 % | 54,3 | 30,1 |
| 60 % | 42,6 | 48,7 |
| **50 %** | 42,1 | **61,8** |
| 40 % | 38,0 | 61,7 |

Bei weitem Rahmen braucht es den Filter, bei engem schadet er — er nimmt einer
ohnehin kleinen Pixelmenge nochmals 70 %. **`core_percentile` ist ein Notbehelf
für einen zu weiten Rahmen.** Sitzt der Rahmen eng, wird er überflüssig, und
das Ergebnis ist besser als beides einzeln.

### Befund 3: Die Position ist stabil, die Helligkeit nicht

Zwischen den beiden Strecken liegen rund 2,6 Stunden:

| Bahn | Versatz des Schwerpunkts | größter |
|---|---|---|
| 2 | −0,2 % / +2,0 % | 4,8 % |
| 3 | +0,1 % / +2,2 % | 3,9 % |
| 4 | +0,1 % / +1,7 % | **2,9 %** |
| 5 | −0,2 % / +2,4 % | 4,8 % |

Die Einblendung wandert also praktisch nicht — ein 50 %-Zuschnitt lässt 25 %
Rand je Seite und hat davon reichlich Reserve. **Das AUS-Niveau steigt im
selben Zeitraum dagegen um 10 bis 23 Punkte**, und die Trennlücke schrumpft
entsprechend:

| Trennlücke Bahn 4 | früh | spät |
|---|---|---|
| heute | 44,8 | **33,7** |
| 80 % + Kern 70 | 54,3 | 37,5 |
| **50 % ohne Kern** | **61,8** | **44,8** |
| 40 % ohne Kern | 61,7 | **51,2** |

Der schlechteste Fall über alle vier Bahnen und beide Strecken: heute 33,7 —
bei 50 % ohne Kernfilter 44,8, bei 40 % 47,1. **Der Zuschnitt löst die Drift
nicht, er vergrößert nur den Abstand, den sie aufzehrt.**

### Was daraus nicht folgt

Dass die Zahl einfach eingetragen werden kann. Ein anderer Zuschnitt verschiebt
**alle** Niveaus: Bei 50 % ohne Kernfilter fällt AN p5 auf Bahn 4 spät auf
240,0, während die heutige AN-Schwelle anteilig bei 233 bis 237 landet — das
wäre zu knapp. `brightness_on_threshold`, `brightness_off_threshold` und beide
Fractions müssten mitbestimmt und ein Vollauf dagegen gehalten werden.

Die Rohdaten liegen unter `debug/roi_proben/`, damit die Frage ohne neuen
Quellzugriff weiterverfolgt werden kann — der Stream-Zugang läuft am
2026-09-02 ab.

## Der enge ROI im Vollauf bestätigt (2026-09-02)

`lauf_2026-09-02_18-30-19`, ganzer Spieltag über die Stream-Quelle, mit
`1Spieltag_enge_lampen.json` und dem neu bestimmten Schwellensatz. Gegen den
Referenzlauf `2026-09-01_17-38-42` derselben Quelle gehalten:

| | weiter ROI | **enger ROI** |
|---|---|---|
| Grünzyklen / Würfe | 1702 / 1695 | 1702 / **1695** |
| Status VALID | 1667 | **1679** |
| Status EMPTY | 13 | 16 |
| **Status ERROR** | **15** | **0** |
| Kegel gesamt | 11 483 | 11 479 |
| Abweichung zur Tafel-Ziffer | 8 von 1621 | **7 von 1621** |

**Die Zielgröße, UNKNOWN-Anteil der Kegellampen über den ganzen Spieltag:**

| Bahn | weiter ROI | enger ROI |
|---|---|---|
| 2 | 0,27 % | **0,11 %** |
| 3 | 1,83 % | **0,26 %** |
| 4 | **6,73 %** | **0,50 %** |
| 5 | 3,01 % | **0,28 %** |

Bahn 4 fällt um den Faktor 13. Damit liegen alle vier Bahnen erstmals im selben
Bereich — die Sonderrolle von Bahn 4 ist verschwunden.

**Alle 15 ERROR-Würfe sind aufgelöst, ohne dass sich eine Zahl änderte.** 13
wurden VALID, 2 blieben als EMPTY stehen (sie waren schon vorher 0 Kegel). Die
Kegelzahl ist in jedem der 15 Fälle dieselbe geblieben, und wo eine Tafel-Ziffer
vorlag, stimmt sie überein. Der ERROR-Status kam also nicht von einer falschen
Zahl, sondern von unlesbaren Lampen — 11 der 15 lagen auf Bahn 4.

### Die vier abweichenden Würfe, mit der Tafel als Schiedsrichter

| Bahn | Frame | alt | neu | Tafel | Urteil |
|---|---|---|---|---|---|
| 3 | 14502 | 8 | **9** | 9 | enger ROI |
| 4 | 14327 | 8 | **5** | 5 | enger ROI |
| 4 | 289308 | **9** | 8 | 9 | weiter ROI |
| 5 | 16256 | 1 | 0 | — | offen |

Zwei gewonnen, eine verloren, eine ohne Zeugen. Die Gesamtabweichung zur Tafel
sinkt von 8 auf 7 von 1621.

**Was offen bleibt:** Bahn 4 F289308 verliert einen Kegel, den die Tafel zählt.
Ein Einzelfall unter 1621 geprüften Würfen, aber ungeklärt — mit dem engen
Rahmen kann eine Lampe verfehlt werden, deren Leuchtfläche außermittig sitzt.
Dasselbe gilt womöglich für Bahn 5 F16256.

## Spielwechsel nur an der Wurfnummer (2026-09-02)

Nutzeridee: Die Wurfnummer wird zu 100 % gelesen, die Summe nicht — also nur
die Wurfnummer als Zeugen nehmen. Wo `000` steht, muss ein neuer Zyklus
beginnen; einen ersten Wurf mit einer Summe über null kann es nicht geben.

**Warum das mehr ist als eine Vereinfachung:** Die Summe wurde ZUERST gelesen
und war damit der Torwächter — bei `not summe.is_readable` brach die Prüfung
ab, und die Wurfnummer kam nie zum Zug. Der schwächere Zeuge entschied über
den stärkeren.

Vollauf `lauf_2026-09-02_21-11-00` gegen `18-30-19`, gleiche Kalibrierung:

| | vorher | nachher |
|---|---|---|
| Würfe / Kegel | 1695 / 11 479 | **1695 / 11 479** |
| VALID / EMPTY / ERROR | 1679 / 16 / 0 | **1679 / 16 / 0** |
| Abweichung zur Tafel-Ziffer | 7 von 1621 | **7 von 1621** |

**Nichts verändert sich — außer der Abschnittsstruktur auf Bahn 4:**

| Bahn | vorher | nachher |
|---|---|---|
| 2 | 16 Abschnitte | 16 |
| 3 | 16 | 16 |
| **4** | **14** | **16** |
| 5 | 16 | 16 |

Der 51-Wurf-Block auf Bahn 4 zerfällt in `1 + 19 + 29 + 31 …` — also 20 Würfe
Warmwerfen und dann die Sätze, dasselbe Muster wie auf den anderen drei
Bahnen. Nach dem Streichen der Nullwürfe stehen alle vier Bahnen auf
**16 Abschnitten mit 12 Sätzen**.

**Was offen bleibt:** Die Wurfnummernketten laufen weiterhin in 46 von 48
langen Abschnitten sauber 1…30 durch — die Zahl ändert sich nicht, die
Fehlerstelle wandert nur (vorher Bahn 4 Spiel 1 mit 51 Würfen, jetzt Bahn 4
Spiel 3 mit 29). Die neue Trennstelle sitzt also um einen Wurf verschoben. Das
ist ein kleinerer Fehler als ein verschmolzenes Spiel, aber kein perfekter
Schnitt.

**Schalter:** `scoring.game_reset_number_only` (an).
**Regressionstests:** `test_game_reset.py::TestNurDieWurfnummer` — vier Fälle,
darunter die Gegenprobe, dass es ohne den Schalter beim alten Verhalten bleibt.

## Enge Lampen-ROIs in der geführten Kalibrierung (2026-09-03)

Die geführte Kalibrierung legte weiterhin die alten weiten Rahmen an
(0,080 × 0,075) — der Umbau vom Vortag steckte nur in der einen
Kalibrierungsdatei, nicht in der Vorlage. Damit wäre jedes neue Video wieder
mit dem alten Verhalten gestartet.

**Nachgemessen wurden dabei auch die Positionen.** Die Vorlage stammte aus
einer Nutzerkalibrierung von Hand und lag systematisch zu hoch:

| | Vorlage alt | gemessen | Abweichung |
|---|---|---|---|
| erste Zeile y | 0,342 | 0,353 | +0,011 |
| Zeilenabstand | 0,0775 | 0,0753 | −0,0022 |
| Mittelachse x | 0,498 | 0,501 | +0,003 |

Beim weiten Rahmen fiel das nicht auf. Beim halbierten wären 0,011 fast ein
Drittel der Höhe — der Rahmen hätte die Leuchtfläche angeschnitten. Die neue
Vorlage ist zudem sauber symmetrisch: Der Mittelpunkt der äußeren wie der
mittleren Lampen liegt auf 0,501, die Abstände sind ±0,322 und ±0,161.

Die Streuung zwischen den vier Bahnen liegt bei 0,006 bis 0,012 — die Vorlage
kann also nur ein Ausgangspunkt sein, den der Nutzer nachzieht. Genau dafür
sind die Rahmen mit der Maus verschiebbar.

## Der erste Wurfbeleg findet gleich etwas (2026-09-03)

Erster Einsatz von `debug.throw_sheet` am echten Material (Frames 14000–24000,
50 Würfe, 6,7 MB). Zwei Beobachtungen aus den Bildern:

**Die engen Lampen-ROIs sitzen sichtbar mittig** auf den Leuchtflächen — die
gemessene Vorlage trifft, was sich vorher nur aus Zahlen ableiten ließ.

**Bahn 4, Spiel 2, Wurf 2: Die Ziffer ist klar lesbar, wird aber verworfen.**
Im Belegbild zeigt `pin_count` eine unübersehbare **9**, alle neun Lampen
leuchten, und die Wurfzeile trägt trotzdem „Tafel unlesbar". Die Lampenlesung
(9 Kegel) ist richtig — nur die zweite Quelle fällt aus, obwohl sie im Bild
steht.

Das ist genau der Fall, für den der Beleg gebaut wurde: Aus `wuerfe.csv` allein
wäre nur zu sehen, dass die Ziffernspalte leer ist — nicht, dass die Ziffer
dastand. Es stützt die Vermutung des Nutzers, dass an der Ziffernerkennung noch
etwas zu holen ist, und grenzt sie zugleich ein: Nicht die *Lampen* sind das
Problem, sondern die Segment-Dekodierung bei gut lesbaren Ziffern.

Passend dazu die frühere Messung: Die Kegelzahl-Ziffer ist auf Bahn 4 nur zu
92,9 % verfügbar, auf Bahn 2 zu 99,5 %.

**Was der Beleg nicht klärt:** Die Tafelsumme steht bei Wurf 2 auf 0014,
während der Lauf 18 zählt. Der Ausschnitt beginnt mitten im Spiel, die Summen
sind deshalb nicht vergleichbar — ein Vollauf müsste das entscheiden.

## Drei Schwellen, die am falschen Ort standen (2026-09-03)

Anlass waren zwei Beobachtungen des Nutzers an den Videoclips der Streitfälle.
Beide führten auf denselben Fehlertyp: eine Schwelle am **Rand** einer Wolke
statt in der Lücke zwischen zweien.

### 1. Die AN-Schwelle klebte an der AN-Wolke

Nutzerfrage: „Warum ist unsere Grenze für AN so nah an den AN-Werten? Dann
setze ich die Schwelle doch bitte möglichst mittig dazwischen."

Gemessen am Lauf `2026-09-02_21-11-00`:

| Bahn | AUS-Wolke bis | AN-Wolke ab | Mitte wäre | AN-Schwelle war | zu hoch |
|---|---|---|---|---|---|
| 2 | 160,8 | 248,1 | 204,4 | 220,0 | +15,6 |
| 3 | 179,9 | 244,3 | 212,1 | 224,2 | +12,1 |
| **4** | 190,6 | **232,2** | 211,4 | **226,4** | **+15,0** |
| 5 | 179,4 | 239,1 | 209,2 | 221,4 | +12,2 |

Auf Bahn 4 blieben **5,8 Punkte** zwischen Schwelle und Wolke. Genau dort ging
der einzige Wurf verloren, der gegen das Wurfprotokoll falsch war.

Der Denkfehler steckte in der Herleitung: Die Bedingung lautete „AN-Schwelle
unter dem 5. Perzentil der AN-Messungen" — das erfüllt auch eine Schwelle, die
*gerade eben* darunter liegt.

### 2. Die obere Seite war gar nicht gemessen, sondern angenommen

Nutzerfrage: „Ich dachte, wir machen, dass das sich live anpasst?"

Halb richtig — und das war das Problem:

```
Schwelle = Niveau + (255 − Niveau) × Anteil
           ~~~~~~   ~~~
           gemessen  feste Annahme
```

Das AUS-Niveau läuft je Lampe mit. Die obere Seite ist `brightness_saturated`,
also die Annahme, eine leuchtende Lampe sei im Bild gesättigt. Gemessen:

| Bahn | AN-Wolke (Median) | angenommen | Fehler |
|---|---|---|---|
| 2 | 252,6 | 255 | +2,4 |
| 3 | 249,0 | 255 | +6,0 |
| **4** | **243,3** | 255 | **+11,7** |
| 5 | 246,2 | 255 | +8,8 |

Weil die Schwelle als *Anteil dieses Abstands* gerechnet wird, rutscht sie
genau dort nach oben, wo die Lampen am schwächsten leuchten — der Fehler
verstärkt sich selbst.

**Abhilfe (`adaptive_on_level`):** ein zweites Gedächtnis für die leuchtenden
Messungen. Die Schwellen liegen dann mittig zwischen zwei *gemessenen*
Wolkenrändern, ohne jede Annahme über Sättigung.

**Die Rückkopplung ist bewusst durchbrochen:** Das AN-Gedächtnis wird an einer
festen Schranke gefüllt (`an_ignore_below`), nicht an der Klassifikation. Sonst
entschiede die Schwelle darüber, welche Messungen sie selbst bestimmen — ein
Kreis, der beliebig weit driften kann, ohne aufzufallen. Zwei weitere Sperren:
`min_wolken_abstand` (berühren sich die Wolken, wird zurückgefallen) und
mindestens 50 Messungen je Seite.

**Ergebnis am Streitfall F289308:**

| | vorher | nachher |
|---|---|---|
| Kegel | 8 (falsch) | **9** (richtig) |
| Confidence | **0,09** | **1,00** |

Alle zehn Würfe des geprüften Abschnitts stimmen danach mit der Tafel-Ziffer
überein, neun davon mit Confidence 1,00.

### 3. Die Verdeckungsschwelle stand am Rand statt im Tal

Nutzerbeobachtung: In zwei Clips läuft eine Person durchs Bild und unterbricht
die Grünphase. Die Frage war, ob man dafür Personenerkennung braucht.

**Man braucht keine.** Über 512 049 als AUS gelesene Grünscores des ganzen
Spieltags:

| Score | Messungen | Bedeutung |
|---|---|---|
| 0–1 | **32 298** | Tafel verdeckt |
| 2–11 | **286** | Tal (0,06 %) |
| 12–41 | **479 465** | echtes Grün-AUS |

Eine ausgeschaltete Lampe **kann nicht auf null fallen** — das beige Gehäuse
hat immer Grünanteil, echtes AUS liegt bei 20 bis 30. Ein Wert unter 12 heißt
zwingend, dass etwas davor ist. Das ist Eskalationsstufe 1 (Schwellwert auf
ROI-Statistik); ein Modell zur Personenerkennung wäre Stufe 5 und wüsste
nichts, was diese eine Zahl nicht schon sagt.

Die Schwelle stand bei **2,0**, also am Rand der Verdeckungswolke. Auf Bahn 2
fiel der Score bei F265718 auf **6,2** — zu hoch für „verdeckt", zu niedrig für
„aus". Die Zustandsmaschine löste GREEN_OFF aus und buchte einen Wurf, zwei
Frames bevor der Score 0,0 erreichte. Jetzt steht sie bei **12,0**.

**Zwei Fehler mit einer Änderung behoben:** Der Phantomwurf ist weg — und mit
ihm die erfundene Tafel-Ziffer „1". Sie entstand aus einem Ausschnitt, in dem
eine Person stand; während einer erkannten Verdeckung wird auch die
Ziffernlesung eingefroren.

### Was der Nutzer an den Clips gesehen hat

Seine Bewertung der zehn Streitfälle, als Bodenwahrheit festgehalten:

| Fall | Tafel zeigt | wir lasen | Urteil |
|---|---|---|---|
| Bahn 5, F148152 | 8 | 2 | Ziffernerkennung falsch |
| Bahn 5, F208871 | 8 | 2 | Ziffernerkennung falsch |
| Bahn 5, F210507 | 9 | 7 | Ziffernerkennung falsch |
| Bahn 5, F252902 | 9 | 7 | Ziffernerkennung falsch |
| Bahn 2, F265720 | 0 | 1 | **erfunden**, Anzeige war dunkel |
| Bahn 5, F272689 | 8 | 0 | Ziffernerkennung falsch |
| Bahn 4, F14327 | 5 | 5 | enger ROI richtig, weiter falsch |
| Bahn 3, F14502 | 9 | 9 | enger ROI richtig |
| Bahn 5, F16256 | — | — | enger ROI richtig, Verdeckung |

**In allen sechs Ziffernfällen hatten die Lampen recht.** Fünf davon sind
übersehene Segmente (8→2, 9→7, 8→0), einer ist eine erfundene Ziffer bei
dunkler Anzeige. Der enge ROI ist in allen drei Vergleichsfällen bestätigt.

### Der Vollauf mit allen drei Änderungen (2026-09-03)

`lauf_2026-09-03_11-14-04`, ganzer Spieltag, gegen das Wurfprotokoll geprüft:

| | weiter ROI (01.09.) | enger ROI (02.09.) | **mit den drei Änderungen** |
|---|---|---|---|
| **gegen das Protokoll** | 720/720 | 719/720 | **720/720** |
| Würfe | 1695 | 1695 | 1694 |
| Kegel gesamt | 11 483 | 11 479 | 11 480 |
| VALID / EMPTY / ERROR | 1667/13/15 | 1679/16/0 | 1679/**15**/0 |
| Abweichung zur Tafel-Ziffer | 8 von 1621 | 7 von 1621 | **5 von 1620** |

Der eine Wurf weniger ist der **Phantomwurf aus der Verdeckung** — ein EMPTY,
das es nie gab. Zwei der verschwundenen Ziffer-Abweichungen waren erfundene
Ziffern aus verdeckten Ausschnitten.

**UNKNOWN-Anteil der Kegellampen**, die Wirkung der zweiseitigen Anpassung:

| Bahn | 01.09. | 02.09. | **03.09.** |
|---|---|---|---|
| 2 | 0,27 % | 0,11 % | **0,06 %** |
| 3 | 1,83 % | 0,26 % | **0,12 %** |
| **4** | **6,73 %** | 0,50 % | **0,17 %** |
| 5 | 3,01 % | 0,28 % | **0,13 %** |

**Verdeckungen:** 48 Phasen, 2611 Frames — 0,8 % der Aufzeichnung. Die
schärfere Schwelle friert selten ein und kostet keine echten Würfe.

### Was diese Sitzung methodisch gezeigt hat

Alle drei Schwellen hatten denselben Fehler: Sie standen am **Rand** einer
Wolke statt in der Lücke zwischen zweien. Dreimal wurde geprüft, ob die
Schwelle die eine Wolke *knapp* verfehlt — statt zu fragen, wo zwischen beiden
sie hingehört. Der Erkennungs-Skill fordert unter §8 genau das Gegenteil
(„Schwelle in die Lücke legen, mit Reserve zu beiden Seiten").

Und: Sieben Zwischenkennzahlen wurden verbessert (Trennlücke, UNKNOWN-Rate,
ERROR-Zahl), bevor überhaupt jemand die einzige Kennzahl ansah, die zählt. Der
Vergleich gegen das Protokoll lief seit Wochen nicht — dabei hätte er sofort
gezeigt, dass der Stand bereits bei 100 % lag und der ROI-Umbau einen Wurf
kostete.

**Konsequenz:** `tools/compare_protocol.py` nimmt jetzt eine `wuerfe.csv` und
ein wählbares Protokoll. Die Blockprobe (je Spielerblock die beste Fundstelle
suchen, statt die Bahn am Stück auszurichten) läuft in Sekunden und gehört vor
jede Bewertung einer Änderung.

## Falsche Nullwürfe: das Zurücksetzen ist kein Wurf (2026-09-03)

Nutzerwunsch: „Wir brauchen eher etwas, was falsche 0en rausnimmt."

**Die 19 Nullwürfe des Spieltags, nach Herkunft getrennt:**

| Herkunft | Anzahl | Tafel-Ziffer | Lage im Abschnitt |
|---|---|---|---|
| `fehlwurfzaehler` | 4 | **immer 0** | mitten im Satz |
| `gruenzyklus` | 15 | **nie vorhanden** | Rand des Abschnitts |

Die Trennung ist vollständig: Jeder echte Nullwurf kommt vom Fehlwurfzähler und
trägt die Ziffer 0 als Beleg.

### Was die acht häufigsten sind

Das Log sagt es in zwei Zeilen direkt untereinander:

```
Bahn 4: Anzeige stand auf 000/0000 -- voriges Spiel endete mit 195 Kegeln
Bahn 4: Wurf 1 erkannt -- 0 Kegel [], Gesamt 0, EMPTY (1.00)
```

Der Grünzyklus, in dem die Anlage **zurücksetzt**, wird als erster Wurf des
neuen Spiels gebucht — mit null Kegeln, weil die Raute leer ist. Dadurch hatten
die betroffenen Sätze 31 statt 30 Würfe.

**Warum `discard_static_zero_cycles` das nicht fing:** Jene Regel verlangt eine
*unveränderte* Wurfnummer. Beim Spielwechsel springt sie von 30 auf 1 — das ist
eine Änderung, also greift sie nicht.

### Zwei Fehlversuche, beide lehrreich

**Erster Versuch — nur die Tafel-Ziffer als Zeugen.** Fünf bestehende Tests
fielen durch. Sie hielten fest, dass es *drei* Zeugen gibt: die Ziffer 0, ein
gestiegener Fehlwurfzähler oder eine um eins weitergezählte Wurfnummer.

**Zweiter Versuch — über die Wurfnummer urteilen** („springt sie von 30 auf 1
zurück?"). Formal richtig, aber **wirkungslos**: Der Vollauf ergab 19 Nullwürfe
vorher, 19 nachher. Genau dort, wo die Fälle entstehen, ist die Wurfnummer
nicht lesbar — die Anzeige steht ja auf null. Und Schweigen darf nichts
verwerfen (BUG-008, dort kostete diese Verwechslung 28 % der Würfe).

**Dritter Versuch — das Spielwechsel-Zeichen.** `display_reset` sagt genau, was
in diesem Moment geschehen ist, und war längst vorhanden. Geprüft an
F48000–72000: Beide Nullwürfe des Abschnitts (F50619, F69502) sind weg, kein
anderer Wurf ging verloren.

**Die Lehre:** Ich habe zweimal nach einem Merkmal in den Zahlen gesucht, statt
zu lesen, was die Anwendung selbst über den Moment sagt. Das Kriterium stand
die ganze Zeit im Log.

### Was offen bleibt

Von den 19 bleiben nach diesem Filter:

* **4 echte** vom Fehlwurfzähler — sollen bleiben
* **5** am Ende eines Warmwerf-Blocks (Wurfnummer 21 nach 20)
* **2** auf Bahn 5 mitten im Block (F15569, F16256)

Bei den Warmwerf-Fällen zählt die Anzeige laut Lesung auf 21 weiter. Ob die
Anlage dort wirklich zählt oder die 21 eine Fehllesung ist, entscheidet nur ein
Blick auf die Stelle.

**Nutzerangabe vom 2026-09-03: Warmwerfen sind immer exakt 20 Würfe.** Geprüft
an den zwölf Blöcken des Spieltags: 11 von 12 stimmen nach Abzug der
Nullwürfe. Das ist ein Prüfstein, der ohne Bodenwahrheit auskommt.

## 2026-09-08 — Direkte Hallenkamera (Reolink, RTSP): Photometrie passt nicht

Gemessen an `rtsp://…10.0.0.8…/h265Preview_02_main`, Kalibrierung
`Training.json`, 464 Frames, laufender Trainingsbetrieb.

**Quelle:** 2304x1296, **15 fps**, h264 (nicht h265, trotz des Pfadnamens).
Kein Overlay — rohes Hallenbild, Tafeln im Hintergrund. Die Bahn-Quads sind
mit 192x192 px sogar groesser als im Overlay (152x154), die GEOMETRIE ist also
in Ordnung. Das Problem ist die Helligkeit.

### Transportweg (Ursache des Hakelns)

Je 12 s, dieselbe Kamera, dieselbe Minute:

| Transport | gelesen | groesste Luecke | Decoder |
|---|---|---|---|
| udp |  4,7 fps | 5089 ms | `error while decoding MB 72 18` |
| tcp | 15,9 fps |  235 ms | fehlerfrei |

Behoben ueber `video.stream_rtsp_transport: "tcp"`.

### Gruene Lampe — Verdeckungsschwelle greift ins Leere

`occlusion_score: 12.0` friert den Zustand ein. Anteil der Frames darunter:

| Bahn | min | p25 | median | p75 | max | Anteil < 12,0 |
|---|---|---|---|---|---|---|
| 2 | 0,0 |  1,3 | 57,1 | 65,6 | 76,6 | **48,3 %** |
| 3 | 3,9 | 11,7 | 65,6 | 72,1 | 79,2 | **25,4 %** |
| 4 | 12,6 | 15,4 | 16,8 | 18,4 | 83,2 | 0,0 % |
| 5 | 0,0 | 54,8 | 64,3 | 66,1 | 68,5 | **23,5 %** |

Im Overlay konnte echtes AUS nicht auf null fallen — das beige Gehaeuse hatte
Gruenanteil, AUS lag bei 20-30, und alles darunter hiess zwingend "verdeckt".
An dieser Kamera faellt AUS auf **0-1**. Die Schwelle liegt damit MITTEN in der
AUS-Wolke statt darunter, und die Bahnen 2, 3 und 5 sind ein Viertel bis die
Haelfte der Zeit eingefroren. Eine eingefrorene Bahn bucht keinen Wurf --
das erklaert "erfasst super wenig Wuerfe".

Bahn 4 liegt mit median 16,8 knapp darueber, aber ohne Reserve.

### Kegellampen — Waermeschranke verwirft fast alles

`score()` liefert `(Waerme, Helligkeit)`. Mediane je Bahn ueber alle 9 Lampen:

| Bahn | Waerme | Helligkeit | gegen `warmth_min: 12,0` |
|---|---|---|---|
| 2 | 3,1 - 17,1 | 137 - 255 | fast alles darunter |
| 3 | 1,2 -  27,3 | 146 - 255 | fast alles darunter |
| 4 | 12,8 - 29,4 | 130 - 255 | knapp darueber |
| 5 | 14,6 - 22,9 |  90 - 103 | darueber, aber dunkel |

Referenz aus dem Overlay: **AUS 154+-23 / AN 254+-3** Helligkeit,
**AUS 19+-10 / AN 57+-13** Waerme.

Zwei Befunde:

1. Auf Bahn 2 und 3 ist die Tafel **ausgebrannt** — Helligkeit 250+ bei Waerme
   unter 8. Die Kamera belichtet auf die dunkle Halle, die LED-Flaeche saettigt
   ins Weisse, und Weiss hat keine Waerme. Die Plausibilitaetsschranke
   `warmth_min` verwirft diese Lampen als UNKNOWN — unabhaengig davon, ob sie
   leuchten. Das ist das "willkuerlich" aus der Nutzermeldung.
2. Bahn 5 liegt bei Helligkeit ~100, Bahn 2 bei ~250. Im Overlay waren alle
   vier Tafeln vom Produzenten angeglichen; hier trennen sie 150 Helligkeits-
   stufen. Eine globale Schwelle kann beide nicht zugleich bedienen.

### Schlussfolgerung

Die Schwellwerte sind samt und sonders am Overlay eingemessen. Fuer diese
Kamera muessen sie NEU gemessen werden -- nicht geschaetzt. Ohne Ground Truth
ist jede Anpassung geraten, und eine geratene Schwelle, die zufaellig auf
zwanzig Frames passt, ist schlimmer als eine dokumentierte Luecke.

Offen: eigener Schwellensatz je Quelle (Overlay / Hallenkamera), und die Frage,
ob die Kamerabelichtung so eingestellt werden kann, dass die Tafel nicht
saettigt.

### Nachtrag desselben Abends: geloest

Die Schlussfolgerung oben ("muss neu gemessen werden") war richtig -- die
Messung liess sich aber noch am selben Abend machen. Ergebnis: DREI Werte, alle
belegt. Sie stehen in `config/hallenkamera.yaml`; `default.yaml` bleibt
unveraendert fuer das Overlay.

**Korrektur an der Zwischendiagnose oben.** Der erste Befund lautete "Waerme
trennt, Helligkeit ist gesaettigt". Das war ein Artefakt meines groben
Histogrammtests ueber ZUSAMMENGELEGTE Lampen. Mit einem echten Trennmass
(Abstand der Wolken durch ihre Streuung), je Lampe gerechnet ueber 354 Muster:

| Bahn | 2 | 3 | 4 | 5 | Overlay-Referenz |
|---|---|---|---|---|---|
| Helligkeit | 8,98 | 18,57 | 3,04 | 7,57 | 7,66 |
| Waerme | 2,76 | 4,73 | 3,10 | 1,70 | 3,35 |

Die Helligkeit traegt hier auf drei von vier Bahnen BESSER als im Overlay. Sie
bleibt das Hauptkriterium; die Regel dahinter war nie falsch.

Der Kernfilter aendert daran nichts -- geprueft mit `core_percentile` 0/50/70/85
an denselben Mustern, Unterschiede unter 1,5 Punkte. Er bleibt auf 0.

**Was tatsaechlich blockierte:** die Waermeschranke. Anteil der LEUCHTENDEN
Messungen, den `warmth_min` verwirft:

| warmth_min | median verworfen | Lampen mit >50 % Verlust |
|---|---|---|
| 12,0 (default) | 89,5 % | 22 von 36 |
| 6,0 | 48,2 % | 18 von 36 |
| **0,0** | **0,0 %** | **0 von 36** |

Je Bahn: Bahn 2 verlor 93-100 %, Bahn 3 92-99 %, Bahn 4 **0 %**, Bahn 5 0-90 %.
Daher der Eindruck "willkuerlich" -- eine Bahn ging, die andere nie. Ursache:
Auf Bahn 2 und 3 brennt die Tafel aus, die leuchtende Lampe saettigt ins
Weisse, und Weiss hat keine Waerme.

Gegenprobe an denselben 12 744 Messungen, alter gegen neuer Satz:

| | AN | AUS | UNBEKANNT |
|---|---|---|---|
| default.yaml | 621 (4,9 %) | 8341 | 3782 (29,7 %) |
| hallenkamera.yaml | 4292 (33,7 %) | **8341** | 111 (0,9 %) |

Die AUS-Zahl ist IDENTISCH. Es wurde keine erloschene Lampe zu "AN"
umgedeutet -- der Fix holt ausschliesslich vorher unentscheidbare zurueck.

**Dritter Wert: `stream_restart_check: false`.** Der erste Lauf mit den neuen
Schwellen brach nach 1,5 min ab: "Der Stream hat wieder von vorn begonnen
(Frame 1333)". Fehlalarm. Eine feste Kamera auf eine unbewegte Halle liefert so
aehnliche Anfangsbilder, dass mehrere denselben Fingerabdruck bekommen und eine
zufaellig aufsteigende Kette entsteht. Beim Overlay wechselte staendig das
Kamerabild; dort trat das nie auf. Eine RTSP-Kamera hat ohnehin keine
Aufzeichnung, zu der sie zurueckspringen koennte.

**Ergebnis im Betrieb**, 1,5 min live gegen die Kamera:
12 Gruenzyklen, 12 Wuerfe, Status `{'VALID': 12}`. Vorher nahezu nichts.
