---
name: kegel-detection
description: >
  Erkennungsverfahren in Kegel_CV. Laden bei Arbeit an Grünlampen-Erkennung,
  Kegellampen, 7-Segment-Ziffern, OCR, Template Matching, Schwellwerten, Hysterese,
  Confidence, zeitlicher Aggregation über mehrere Frames, flackernden Anzeigen oder
  Frame-Sampling rund um ein Ereignis. Enthält die gemessenen Signalwerte.
---

# Erkennung

## 1. Grundhaltung

> Erst klassische Bildverarbeitung. ML nur, wenn nachweislich nötig.

Reihenfolge der Eskalation — jede Stufe erst, wenn die vorherige gemessen versagt:

```
1. Schwellwert auf ROI-Statistik    <- Grünlampe, Kegellampen: hier reicht es
2. Template Matching                <- 7-Segment-Ziffern: erster Versuch
3. Segment-Dekodierung (7-Segment)  <- robuster als OCR bei bekannter Geometrie
4. OCR (Tesseract o.ä.)             <- nur falls 2+3 scheitern
5. ML-Modell                        <- letzte Stufe, nur mit Messbeleg
```

Ein ML-Modell ohne dokumentierten Nachweis, dass Stufe 1–4 versagt haben, ist ein
Architekturbruch (Auftrag §8, §27).

## 2. Grünlampe — gemessene Werte

ROI ca. 6x8 px im 1080p-Frame. Score = Anteil Pixel mit HSV `H in [40,90], S>80, V>80`,
alternativ `mean(G - (R+B)/2)`.

| Zustand | Score (gemessen) |
|---|---|
| AUS | 17.3 – 24.0 |
| AN | 59.9 – 74.3 |

**Die Baseline ist nicht null** — das beige Tafelgehäuse hat einen Grünanteil.
Ein absoluter Schwellwert bei 0 wäre also immer „AN". Konsequenz:

### Hysterese ist Pflicht, nicht Kür

```
Score
  75 |        ****************
     |       *
  45 |- - - -*- - - - - - - - - -  on_threshold   (AUS -> AN)
  35 |- - -*- - - - - - - - - - -  off_threshold  (AN -> AUS)
  20 |*****
     +-------------------------------> Zeit
```

Ein einzelner Schwellwert erzeugt bei Rauschen um die Schwelle ein Flattern —
und jedes Flattern wäre ein Scheinereignis. Zwei Schwellwerte plus eine
Mindestanzahl bestätigender Frames (`min_stable_frames`) verhindern das:

```python
if state is OFF and score > on_threshold:  candidate = ON
if candidate persists for min_stable_frames: state = ON
```

**Nie** einen Zustandswechsel aus einem einzelnen Frame ableiten (Auftrag §9).

## 3. Kegellampen (9 Stück)

Verifizierte Semantik: **leuchtend = Kegel gefallen** (belegt an 4 Tafeln,
Lampenzahl stimmte jeweils exakt mit der angezeigten Ziffer überein).

**GEMESSEN** (Bahn 3, Frame 90, Sollzustand per Sichtprüfung bestätigt:
Lampen 1,3,5,6,8,9 an — Ziffer zeigte 6):

| | Helligkeit | Sättigung | **Wärme (R−B)** |
|---|---|---|---|
| AN | 253–255 | 60–72 | **60–71** |
| AUS | 175–181 | 30–35 | **18–20** |

Die **Wärme trennt am schärfsten** (Faktor 3) und ist deshalb das Hauptkriterium;
die Helligkeit dient als zusätzliche Bedingung. Helligkeit allein genügt nicht:
Auch eine matte Lampe ist hell, weil sie weiß ist und angestrahlt wird.

Gemessen wird nur der **helle Kern** des ROI (oberstes Perzentil, `core_percentile`).
Die runde Lampe füllt das rechteckige ROI nie ganz aus — ein Mittelwert über alles
würde das Signal mit Gehäusefarbe verwässern und die Trennung zunichtemachen.

Ergebnis pro Lampe: `LampReading(state, score, confidence)` mit
`LampState.ON/OFF/UNKNOWN`. **Kein bloßes bool**: `UNKNOWN` muss von `OFF`
unterscheidbar bleiben — eine unlesbare Lampe als „aus" zu werten würde die
Zählung still verfälschen. Die Gesamt-Confidence ist die **schwächste**
Einzelmessung: Eine unsichere Lampe macht die ganze Zählung unsicher.

Auswertung erst, wenn die Grünlampe AUS ist (Auftrag §5A).

## 4. Ziffern — 7-Segment (der schwierigste Teil)

**Stand: rund 60 % Trefferquote.** Der Weg dorthin ist vollständig am Material
gemessen und in `docs/VIDEO_ANALYSIS.md` §8 dokumentiert.

### Was das Material hergibt

Eine Ziffer misst **13 × 18 px**, die Segmente sind **2–3 px dick**. Das ist die
harte Grenze — mehr Information existiert nicht.

⚠ **Höhere Auflösung hilft nicht.** Gemessen: identisches Ergebnis bei entzerrten
Tafeln in 440×530, 880×1060 und 1320×1590. Interpolation fügt nichts hinzu.
Wer hier ansetzt, verliert Zeit.

### Die Überstrahlung — der zentrale Befund

| Bereich | B | G | R | R−G |
|---|---|---|---|---|
| Gehäuse (beige) | 153 | 163 | 189 | +26 |
| Display-Hintergrund | 20 | 22 | 24 | +2 |
| **Segment, hellster Punkt** | 178 | 141 | **255** | **+114** |

Die Segmentmitten sind **nahezu weiß**, nur die Ränder bleiben rot. Eine Maske
über die Rot-Dominanz erfasst deshalb nur Umrisse und liefert **hohle** Ziffern.

✅ **Was trägt:** Otsu auf dem Rotkanal — Trennung hell gegen dunkel. Das Display
ist schwarz (24), die Segmente hell (255). Otsu findet die Schwelle selbst und
bleibt unabhängig von Belichtung und Bahnposition.

### Trefferquoten (12 Felder mit bekanntem Sollwert)

| Verfahren | Treffer |
|---|---|
| Segment-Dekodierung, Rot-Maske | 0/12 |
| Segment-Dekodierung, Otsu-Maske | 5/12 |
| Template Matching (synthetische Vorlagen) | 6/11 |
| Template Matching + zeitliche Aggregation | 7/12 |

### Fallstricke, die Zeit gekostet haben

1. **Ein Störfleck am Rand verschiebt alles.** Die Bounding-Box zieht sich auf,
   die Ziffern liegen versetzt in ihren Zellen, jede Segmentmessung danach ist
   falsch. → Komponenten nach **Höhe** filtern (eine „1" ist flächenarm, aber
   voll hoch).
2. **Horizontal zuschneiden ist ein Fehler.** Eine „1" belegt nur die rechte
   Hälfte ihrer Zelle; auf volle Breite gestreckt lägen b und c in der Mitte.
   Vertikal zuschneiden ist dagegen nötig.
3. **Feste Segmentschwellen tragen nicht.** Gemessen lagen echte Werte bei 0,25
   (aktiv) und 0,39 (inaktiv) — beidseitig knapp an einer festen Schwelle von
   0,35 vorbei. → Adaptive Schwelle über die größte Lücke der sortierten
   Füllgrade.
4. **Zahlen sind rechtsbündig mit führenden Nullen.** Jede Ziffer 0–9 hat rechts
   ein Segment, der rechte Rand ist also immer eine echte Ziffernkante. Der
   linke ist es nicht.

### Die Ziffern sind kursiv — Korrektur lohnt trotzdem nicht

Gemessen an 757 Ziffern über alle vier Tafeln, **im entzerrten Bild**:
Neigung −2,0° / −2,3° / −2,4° / −2,9°, Spanne nur 0,9°.

Die Gleichheit über alle Tafeln zeigt: Das kommt **aus der Anlage**, nicht aus
der Perspektive (die wäre links und rechts verschieden und ist ohnehin
herausgerechnet).

**Nicht korrigieren.** Bei 18 px Ziffernhöhe sind das unter 1 px Versatz, und
eine Scherung verschlechtert das Ergebnis (9/13 → 6/13), weil die zusätzliche
Interpolation bei 11×18 px teurer ist als der Fehler.

Merksatz: **Bei sehr kleinen Bildern kostet jede geometrische Transformation
mehr, als sie an Geometriefehler behebt.** Erst rechnen, ob der Fehler überhaupt
größer ist als ein Pixel.

### Einzeln eingerahmte Ziffern — der Weg, der trägt

Der Nutzer rahmt jede Ziffernstelle einzeln ein (zwei Klicks je Stelle in der
GUI). Damit ist die Position exakt bekannt, und die Segmentflächen ergeben sich
geometrisch aus der Box.

Ergebnis über 51 Würfe: **80 % der gelesenen Ziffern korrekt, 5 Falschlesungen.**
Zuvor lasen nicht eingerahmte Bahnen zu 80–88 % falsch.

Drei Fallstricke dabei — jeder hat die Trefferquote zeitweise ruiniert:

1. **Messfläche für `g` zu breit** → erfasst die senkrechten Segmente, jede „0"
   wird zur „8" (17 %). Waagerechte Segmente nur im mittleren Drittel messen.
2. **„Größte Lücke" als Schwelle** → bei einer „0" sind sechs Segmente aktiv,
   die größte Lücke liegt *innerhalb* der aktiven. Schwelle stattdessen
   **relativ zum hellsten Segment** derselben Ziffer.
3. **Otsu normalisiert** → in einem fast schwarzen Ausschnitt entsteht aus
   Rauschen eine scheinbare Ziffer, bevorzugt „8". Vorab die **absolute**
   Helligkeit prüfen (klar 255, verblassend 196–212, erloschen 76–96).

### Nächste Ansätze (noch offen)

1. Templates aus **echtem Material** statt synthetisch — die realen Ziffern sind
   überstrahlt und weichen von der idealen Segmentform ab.
2. Ziffern-ROIs **pro Stelle einzeln** kalibrieren, statt ein Feld zu teilen.
3. Erst danach ML (Stufe 5) — dann mit belastbarem Nachweis.

**Wichtig für die Priorisierung:** Die Kernfunktion hängt nicht an den Ziffern.
Die Kegelanzahl kommt aus den **Lampen**, die Wurferkennung aus der **Grünlampe**.
Die Ziffern sind Gegenprobe und Wurfnummer.

## 5. Flackernde Anzeigen — zeitliche Aggregation

Auftrag §8: Eine Tafel hat unzuverlässig lesbare Ziffern.

```
Frame 1 -> 7  (conf 0.91)
Frame 2 -> ?  (conf 0.12)   <- verwerfen, nicht raten
Frame 3 -> 7  (conf 0.88)
Frame 4 -> 1  (conf 0.34)   <- Mischbild
                              =>  Ergebnis 7, confidence hoch
```

Regeln:

- **Nie** ein einzelnes OCR-Ergebnis übernehmen.
- Alle Einzelmessungen **mit Confidence speichern**, nicht nur das Endergebnis —
  sie gehören in die `evidence` des Wurfs.
- Aggregation = confidence-gewichtete Mehrheit, nicht einfache Mehrheit.
- Messungen unter `min_confidence` fließen gar nicht erst ein.
- Bleibt die Mehrheit uneindeutig ⇒ Status `ERROR`, **nicht** die häufigste Ziffer raten.

⚠ **Grenze der Aggregation (gemessen):** Sie heilt nur *zufällige* Fehler. Liest
ein Detektor konstant falsch — beobachtet: 25 von 25 Frames „4" statt „9" —,
bestätigt die Aggregation den Fehler und vergibt sogar hohe Confidence. Dagegen
hilft ausschließlich ein besserer Detektor. Festgehalten in
`tests/unit/test_temporal_aggregator.py::test_systematischer_fehler_wird_nicht_geheilt`.

## 6. Frame-Sampling

Nicht hartcodieren (Auftrag §7). Konfigurierbar:

```yaml
sampling:
  frames_after_green_off: [2, 5, 10]   # Offsets in Frames
  frames_before_green_on: [-2]
  max_frames_per_event: 4
```

```
GRÜN AN  --> Wurf --> GRÜN AUS --> [+2] [+5] [+10] --> stabil --> [-2] --> GRÜN AN
                          ^                                         ^
                       Trigger                              kurz vor Freigabe
```

Die Frames kommen aus dem `FrameBuffer` (siehe `kegel-video-pipeline`), **nicht**
über ein Zurückspringen im Video.

## 7. Confidence — Konvention

`0.0` = wertlos, `1.0` = sicher. Jeder Detektor liefert eine Confidence, und zwar
eine **begründete**, keine erfundene Konstante:

| Quelle | Confidence aus |
|---|---|
| Grünlampe | Abstand des Scores zur Schwelle, normiert |
| Kegellampe | Trennschärfe hell/dunkel im ROI |
| Ziffer | Übereinstimmungsgüte der Segmente bzw. Template-Score |
| Aggregat | Anteil übereinstimmender Einzelmessungen |

`confidence = 0.9` als fester Wert im Code ist ein Fehler — er täuscht Wissen vor,
das nicht existiert.

## 8. Kalibrierung von Schwellwerten

Schwellwerte werden **gemessen, nicht geschätzt**. Vorgehen:

1. `tools/measure_signal.py` über repräsentative Videoabschnitte laufen lassen
2. Verteilung AN/AUS ansehen
3. Schwelle in die Lücke legen, mit Reserve zu beiden Seiten
4. Gemessene Werte als Kommentar in die Config schreiben

Verschiebt sich ein Schwellwert später ohne neue Messung, ist das ein Warnsignal
für ein tieferliegendes Problem.

## 9. Schwaches Signal ist schlimmer als gar keins

Eine ungenau platzierte ROI erzeugt **keinen Fehler** — sie erzeugt ein
mehrdeutiges Signal. Die Analyse läuft dann scheinbar, erkennt aber nie einen
Zustandswechsel. Das ist die tückischste Form von Fehlkalibrierung.

Gemessenes Beispiel: Eine leicht verschobene Grünlampen-ROI lieferte Score 27–59
statt 20–75. Ein einzelner Frame überschritt die Schwelle — für die
Zustandsmaschine reines Rauschen, für den Betrachter „sieht doch aus, als ginge es".

Deshalb gibt es `analysis/calibration_check.py`: Es misst über mehrere hundert
Frames und meldet pro Bahn `GOOD` / `WEAK` / `NO_SIGNAL` / `BROKEN`.
Ein Zustand gilt erst als real, wenn er mindestens `min_stable_frames` anhält —
vereinzelte Ausreißer sind ausdrücklich **kein** Wechsel.
