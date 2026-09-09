---
name: kegel-domain
description: >
  Fachwissen zur Kegel-Domäne und zur FUNK-Anzeigetafel des Projekts Kegel_CV.
  Laden bei Fragen zu: Bedeutung von Tafel-Elementen, Kegellampen, Kegelnummerierung,
  Wurfnummer, Summenfelder, 15-Wurf-Zyklen, Zwischensummen, Gültigkeit eines Wurfs,
  valid/EMPTY/INVALID, Volle/Abräumen, Plausibilitätsregeln. Immer laden, bevor
  Erkennungs- oder Zähllogik geschrieben oder interpretiert wird.
---

# Kegel-Domänenwissen

## 1. Die Anlage

eine Vereinsanlage. **FUNK**-Anlage, klassisches deutsches
Kegeln mit **9 Kegeln** (nicht Bowling mit 10 Pins).

## 2. Bildaufbau des Videos

```
┌───────────────────────────────────────────────────────────┐
│         ┌───────────────────────────────────┐             │
│         │  OVERLAY: 4 Anzeigetafeln groß    │  ← ANALYSEQUELLE
│         │  [Tafel1][Tafel2][Tafel3][Tafel4] │    (x≈430-1490, y≈35-300)
│         └───────────────────────────────────┘             │
│                                                           │
│      Totale der Halle: 5 Bahnen, kleine Tafeln fern       │  ← NICHT auswerten
│                                                           │
└───────────────────────────────────────────────────────────┘
```

**Regel:** Immer das Overlay auswerten, nie die kleinen Hintergrundtafeln — dort ist
die Auflösung zu gering. Die Overlay-Position ist **nicht** über Sessions konstant.

## 3. Die Anzeigetafel im Detail (gemessen, nicht geraten)

```
┌────────────────────────────────────────┐
│ ▬▬▬▬▬▬▬ Laufschrift-Display ▬▬▬▬▬▬▬▬ │
│ ┌──────┐   ● rot   ● gelb   ┌──────┐  │  Statuslampen — KEINE Kegel!
│ │Name L│                    │Name R│  │
│ └──────┘        ○  ← 1              │  │
│            ○       ○  ← 2,3         │  │  9 KEGELLAMPEN in Raute
│        ○       ○       ○  ← 4,5,6   │  │  LEUCHTEND = KEGEL GEFALLEN
│            ○       ○  ← 7,8         │  │  dunkel/weiß = steht noch
│                 ○  ← 9              │  │
│ ┌────┐        ○ ● ○         ┌──────┐  │
│ │ 00 │     GRÜNE LAMPE      │ 0063 │  │  Summe A (4-stellig)
│ └────┘                      └──────┘  │
│ ┌───────────────────────────────────┐ │
│ │  012        6        0063         │ │  Wurfnr(3) · Kegel(1) · Summe B(4)
│ └───────────────────────────────────┘ │
└────────────────────────────────────────┘
```

### Verifizierte Beispiele aus echten Frames

| Tafel | Leuchtende Lampen | Ziffer | Unteres Display | Lesart |
|---|---|---|---|---|
| 1 | 5 | 5 | `001 5 0005` | Wurf 1 → 5 Kegel → Summe 5 |
| 3 | 6 | 6 | `012 6 0063` | Wurf 12 → 6 Kegel → Summe 63 |
| 2 | 7 | 7 | `004 7 0023` | Wurf 4 → 7 Kegel → Summe 23 |
| 4 | 9 | 9 | `007 9 0028` | Wurf 7 → 9 Kegel → Summe 28 |

**Zentrale Invariante:**
```
Anzahl leuchtender Kegellampen  ==  Ziffer im Kegelfeld
```
Weicht das ab → Plausibilitätsfehler (Status `WARNING`), **nicht** stillschweigend
eine Quelle bevorzugen.

## 4. Kegelnummerierung (DKB-Standard)

```
        1          Vorderkegel
      2   3
    4   5   6      5 = König (Mitte)
      7   8
        9          Hinterkegel
```
`pins` im Datenmodell ist die **sortierte Liste der GEFALLENEN Kegelnummern**.
Zusätzlich `pins_bitmap`: Bit *k-1* gesetzt ⇒ Kegel *k* gefallen (Wert 0…511).

### Q5 geklärt (2026-09-01): Lampenindex ≠ Kegelnummer

Die Lampen der Tafel liegen als Raute. Unsere ROIs zählen sie **von oben nach
unten**, der Sport zählt **von vorn** — und vorn ist auf der Tafel unten:

```
   Tafel (unsere Lampen)        Kegel (Sport)
          L1                           9
       L2    L3                     7     8
    L4   L5    L6                4    5     6
       L7    L8                     2     3
          L9                           1
```

Eine Spiegelung von oben nach unten; links bleibt links. Die Zuordnung steht in
`calibration.pin_number_mapping` und wird je Lampe in der Kalibrierung als
`pin_number` abgelegt.

**Belegt** durch einen Fall am ersten Spieltag: Bahn 2, Frame 180238 fiel eine
Acht, bei der unsere L2 stehen blieb. Der Nutzer sagte unabhängig davon „hinten
links" voraus — seine 7, und L2 bildet auf 7 ab.

**Nicht belegt** ist, dass die Tafel die Raute nicht zusätzlich seitenverkehrt
zeigt. Die Zeilenzuordnung folgt zwingend aus der Anordnung, die
Seitenzuordnung nur aus der Annahme. Ein Fall mit einem stehenden Kegel **links
oder rechts** (nicht mittig) würde es entscheiden.

Die **Zählung** der Kegel berührt das nie — nur ihre Namen.

## 5. Die grüne Lampe — der zentrale Trigger

Sitzt mittig unterhalb des Kegelbilds, zwischen den beiden oberen Displays,
flankiert von zwei kleinen hellen Punkten. Größe ca. **6×8 px** im 1080p-Frame.

Gemessene Werte (HSV `H∈[40,90], S>80, V>80`; Score = Grünpixel-Anteil):
- **AUS:** ~20–24 (Baseline ist *nicht* null — das beige Gehäuse hat Grünanteil)
- **AN:** ~67–75

Bedeutung im Ablauf (Arbeitshypothese, in Phase 4 zu bestätigen):
```
GRÜN AN   → Bahn freigegeben, Spieler darf werfen
GRÜN AUS  → Wurf läuft / wird ausgewertet  ← Trigger für Frame-Sampling
GRÜN AN   → Ergebnis steht, nächster Wurf freigegeben
```
**Die Lampen dürfen erst als Wurfergebnis gelesen werden, wenn Grün AUS ist**
(Vorgabe aus dem Projektauftrag §5A).

## 6. Wurfzählung und 15er-Zyklen

- Die Wurfnummer der Tafel ist **1-basiert** und erhöht sich **auch bei 0 Kegeln**.
  ⇒ Ein Wurf darf **nie** allein an einer Änderung der Kegelzahl erkannt werden.
- Zyklus (Satz) = 15 Würfe.
  ```python
  wurf_im_zyklus = (wurf_nr - 1) % 15 + 1     # 1..15
  zyklus_nr      = (wurf_nr - 1) // 15 + 1    # 1..n
  ```
  Häufige Fehlerquelle: `wurf_nr % 15` liefert bei Wurf 15 den Wert 0. Falsch.
- Nach jedem abgeschlossenen Zyklus: Zwischensumme prüfen.

## 7. Status eines Wurfs

| Status | Bedeutung | Bedingung |
|---|---|---|
| `UNKNOWN` | Noch nicht ausgewertet | Initialzustand |
| `VALID` | Gültiger Wurf, ≥1 Kegel, alle Quellen einig | Lampen == Ziffer, Wurfnr +1, Summe passt |
| `EMPTY` | Gültiger Wurf, **0 Kegel** ("Pumpe") | Wurfnr erhöht sich, 0 Lampen, Ziffer 0 |
| `INVALID` | Ungültiger Wurf (Fehlwurf/Faul) | von der Anlage als ungültig markiert |
| `ERROR` | Auswertung nicht möglich | Quellen widersprüchlich / unlesbar |

**Wichtig:** `EMPTY` ist **kein Fehler**. Ein Wurf mit 0 Kegeln ist regulär und zählt
in der Wurfnummer mit. `valid=true` gilt für `VALID` **und** `EMPTY`; nur
`INVALID`/`ERROR` sind `valid=false`.

## 8. Summen

Zwei Summenfelder auf der Tafel:
- **Summe A** — oben rechts, 4-stellig
- **Summe B** — unten rechts im Zeilendisplay, 4-stellig

In allen bisher untersuchten Frames waren A und B **identisch**. Ob das immer gilt
(oder A = Satzsumme, B = Gesamtsumme) ist offen → Q3.

Erwartete Invariante zwischen Würfen:
```
summe_neu == summe_alt + kegel_gefallen
```
Verletzung ⇒ entweder verpasster Wurf oder Fehlerkennung ⇒ `WARNING` + Log.

## 9. Was NICHT angenommen werden darf

| ❌ Falsche Annahme | Warum falsch |
|---|---|
| „Alle 4 Bahnen werfen gleichzeitig" | Spieler sind unabhängig — Grundprinzip P6 |
| „Kegelzahl ändert sich ⇒ neuer Wurf" | 0-Kegel-Würfe existieren |
| „Ein Frame reicht" | Ziffern flackern (Auftrag §8) |
| „Lampen = Ziffer, also reicht eine Quelle" | Die Redundanz ist der Zweck |
| „Overlay-Position ist fix" | Variiert zwischen Sessions (gemessen!) |
| „Leuchtende Lampe = stehender Kegel" | Umgekehrt — verifiziert an 4 Tafeln |
