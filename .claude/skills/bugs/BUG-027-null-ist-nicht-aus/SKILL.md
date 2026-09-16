---
name: bug-027-null-ist-nicht-aus
description: >
  Verhindert falsche Punktestaende durch eine Schranke, die "abgeschaltet"
  heissen sollte und es nicht war. Laden bei Arbeit an Lampenschwellen, an
  Nebenkriterien neben einem Hauptkriterium, an UNKNOWN-Zustaenden, an
  Raeumwuerfen und ihrer Ausgangslage -- und immer dann, wenn eine Null als
  "aus" gemeint ist.
---

# BUG-027 — Null ist nicht aus

| | |
|---|---|
| **Kategorie** | `DETECT` / Schwellwert |
| **Gefunden** | 2026-09-16, durch eine Rückfrage des Nutzers |
| **Schweregrad** | **hoch** (ein Spieler bekam einen Punkt zu viel, ohne dass etwas auffiel) |
| **Regressionstest** | `test_detectors.py::TestWarmthLampDetector::test_ohne_schranke_zaehlt_allein_die_helligkeit` |

## Symptom

Bahn 2, Wurf 21 des Hallenmitschnitts wurde mit **5 gefallenen Kegeln**
gebucht. Die Kegelziffer der Tafel zeigte **4**, und die Summe stieg von 147
auf 151 — ebenfalls **4**. Zwei voneinander unabhängige Quellen widersprachen
gemeinsam dem gebuchten Ergebnis.

Aufgefallen ist es erst, nachdem die Ziffernrahmen nachgezogen waren und die
Summe überhaupt lesbar wurde. Vorher war der Fehler unsichtbar: Es gab keinen
Schiedsrichter.

## Die falsche Fährte

Die erste Diagnose lautete „die Kegellampe flackert" — die Zustandsfolge sah
danach aus:

```
F6600-6624   [1, 3, 6, 9]      Kegel 3 liegt
F6630-6654   [1, 6, 9]         Kegel 3 steht     <- hier holte Wurf 21 seine Ausgangslage
F6660-6684   [1, 3, 6, 9]      Kegel 3 liegt
```

Der Nutzer hielt dagegen: *„aber ich dachte die Lampen passen sich selbst an?
Also müsste dieses 'flackernd' wirkende (ich sehe da keine
Helligkeitsänderungen) doch automatisch die Wolken im Histogram anpassen, oder
nicht?"* — Er hatte recht. Die Messung:

```
Frame   Helligkeit  Waerme  AN-Schwelle  AUS-Schwelle  Zustand
  6624       255.0     0.0        213.0         205.0       ON
  6636       254.9    -0.3        213.0         205.0  UNKNOWN
  6660       255.0     0.0        213.0         205.0       ON
  6696       255.0    -0.2        213.0         205.0  UNKNOWN
```

**Die Helligkeit steht konstant bei 255,0, die Schwellen bewegen sich nie, die
Lampe geht kein einziges Mal auf AUS.** Das gleitende Histogramm arbeitet
einwandfrei — es ist nur nicht zuständig.

## Ursache

```python
if brightness >= an_schwelle and warmth >= self.cfg.warmth_min:   # 0.0
```

`warmth` ist `mittel(rot − blau)`. Eine voll durchgesteuerte Lampe ist **weiß**:
Rot ≈ Blau ≈ 255, also Wärme ≈ 0 mit einem Rauschen von ±0,3. Die Schranke saß
auf exakt 0,0 — **das Vorzeichen eines Rauschwerts entschied** über `ON` oder
`UNKNOWN`.

In der Konfiguration stand darüber wörtlich:

> ABGESCHALTET FUER DIESE KAMERA. Die Helligkeit entscheidet allein.

Abgeschaltet war sie nicht. **Für eine Größe, die negativ werden kann, ist null
keine Abschaltung, sondern eine Schwelle mitten im Rauschen.**

Zwei Fehler kamen zusammen:

1. **Die Schranke feuerte, obwohl sie „aus" sein sollte.** GEMESSEN über den
   ganzen Mitschnitt: 99 von 3685 hellen Messungen der Bahn 2 verworfen
   (2,7 %), auf Bahn 3 und 4 keine einzige. Bahn 2s Lampen erscheinen der
   Kamera fast farblos (Wärme-Median 0,78), Bahn 4s deutlich warm (24,17).
2. **`UNKNOWN` wirkt wie „steht".** Die Kegelliste sammelt nur `is_on`; eine
   unbekannte Lampe fällt still heraus. Bei einem Räumwurf ist das Ergebnis die
   DIFFERENZ zweier Messungen — ein fehlender Kegel in der Ausgangslage
   schlägt direkt auf den Punktestand durch: `8 − 3 = 5` statt `8 − 4 = 4`.

## Behebung

`warmth_min` ist jetzt `float | None`, und die Vorgabe ist `None` = aus. Der
Detektor prüft die Wärme nur, wenn ein Wert gesetzt ist. Anlagen mit farbigen
Kegellampen können sie über das `AnlagenProfil` einschalten.

Ergebnis am Hallenmitschnitt: Wurf 21 wird als **4** gebucht, `lampen_verdaechtig`
fällt von 1 auf 0, die Summendifferenz trifft die Lampen in 31 von 35 Fällen
(vorher 30), die ERROR-Würfe gehen von 2 auf 1 zurück. 64 Würfe unverändert.

## Was daraus zu lernen ist

**Eine Null ist keine Abschaltung.** Bei jeder Schranke gehört gefragt, welchen
Wertebereich die geprüfte Größe hat. Kann sie negativ werden, liegt null
mitten drin — und ein Kommentar, der „abgeschaltet" behauptet, macht den
Fehler unsichtbarer, nicht kleiner. Wo „aus" gemeint ist, muss `None` stehen.

**Ein Nebenkriterium bleibt gefährlich, auch wenn es entschärft wurde.** Die
UND-Verknüpfung von Helligkeit und Wärme war schon einmal als Fehler erkannt
worden; die Antwort damals war, die Schwelle zu senken statt das UND zu
entfernen. Derselbe Fehler kam leiser wieder.

**Ein farbbasiertes Kriterium skaliert nicht.** Der Nutzer sah es sofort:
*„wenn ich jetzt weiter denke, eben an andere Bahnen, die vielleicht mit Grün
oder Roten Lampen die Kegel anzeigen, wäre dann NUR Helligkeit nicht
cleverer?"* — `rot − blau` ist auf ROTE Lampen zugeschnitten. Eine Halle mit
grünen Kegellampen wäre gar nicht gelaufen, und niemand wäre auf die Ursache
gekommen, weil die Helligkeit ja stimmt. GEMESSEN trennt die Helligkeit
ohnehin besser (Trenngüte 8,98 / 18,57 / 3,04 / 7,57 gegen 2,76 / 4,73 / 3,10
/ 1,70).

**`UNKNOWN` darf nicht stillschweigend zu einer Aussage werden.** Wer eine
Liste aus `is_on` baut, verwandelt „ich weiß es nicht" in „nein". Bei
Differenzmessungen ist das direkt ein falsches Ergebnis. Das ist noch NICHT
behoben — siehe unten.

## Offen

Punkt 2 der Ursache steht weiter: Die Ausgangslage eines Räumwurfs wird auch
dann genommen, wenn einzelne Lampen `UNKNOWN` sind. Bisher fiel es nicht auf,
weil die Wärmeschranke die einzige nennenswerte Quelle für `UNKNOWN` war. Ein
eigener Befund, eine eigene Messung.
