# ORCHESTRIERUNG — Kegel_CV

> **Zweck dieses Dokuments:** Es ist der Kompass für Claude. Vor jeder Arbeitseinheit
> hier nachschlagen: *Wo stehen wir? Welcher Skill gilt? Was ist die nächste Aufgabe?*
> Dieses File ist die einzige Quelle der Wahrheit für den Projektzustand.

---

## 1. Projekt in einem Satz

Lokale Desktop-Anwendung, die aus Kegelbahn-Videos (FUNK-Anzeigetafeln, 4 Bahnen)
vollautomatisch jeden Wurf erfasst: gefallene Kegel, Anzahl, Wurfnummer, Summen —
**robust, nachvollziehbar und debugbar**, nicht "möglichst viel KI".

---

## 2. Leitprinzipien (nicht verhandelbar)

| # | Prinzip | Konsequenz im Code |
|---|---|---|
| P1 | **Nachvollziehbarkeit vor Genauigkeit** | Jedes Ergebnis trägt seine Herkunft (Frames, Scores, Entscheidungen) mit sich. |
| P2 | **Kein Frame-für-Frame-ML** | Billige Trigger (Grünlampe) steuern teure Analyse. |
| P3 | **Klein statt groß** | ROIs analysieren, nie ganze Frames. |
| P4 | **Austauschbarkeit** | Jeder Detektor hinter einem Protocol/ABC. Keine Direktaufrufe quer durch Schichten. |
| P5 | **Keine Magic Numbers** | Jeder Schwellwert kommt aus der Config. |
| P6 | **Bahnen sind unabhängig** | Nie synchrone Ereignisse annehmen. Pro Bahn eigener Zustand. |
| P7 | **Nicht raten — messen** | Bei Unklarheit: Frames extrahieren, anschauen, dann implementieren. Sonst TODO in `docs/OPEN_QUESTIONS.md`. |
| P8 | **Fehler ≠ Abbruch** | Analyse läuft weiter, Fehler werden als Status gespeichert. |

---

## 3. Erkenntnisse aus der Videoanalyse (Stand: 2026-08-24)

**Diese Fakten sind gemessen, nicht geraten.** Quelle: `docs/VIDEO_ANALYSIS.md`

- **Videos:** 1920×1080, 25 fps, h264. 2 Sessions: `2024-09-03` (9 Clips à 13–30 s), `2026-08-22` (2 Clips, einer ~2,3 GB).
- **Ort:** eine Vereinsanlage, FUNK-Anlage.
- **Bildaufbau:** Weitwinkel-Totale der Halle. Oben mittig ein **eingeblendetes Overlay-Panel**
  (ca. x 430–1490, y 35–300) mit den **4 Anzeigetafeln in Nahaufnahme**.
  → **Das Overlay ist die Analysequelle**, nicht die kleinen Tafeln im Hintergrund.
- **⚠ Overlay-Position variiert zwischen Sessions** (2024: Grünlampen bei x≈538/1079/1378;
  2026: x≈572/876/1105/1399). → Kalibrierung ist **pro Session/Video** zu speichern.
- **Anzeigetafel-Semantik (gemessen und verifiziert):**

  ```
  ┌──────────────────────────────────────┐
  │  [ Laufschrift-Display, dunkel ]     │
  │  [Name L]   ● (rot) ● (gelb)  [Name R]   ← Statuslampen, KEINE Kegel
  │              9 KEGELLAMPEN            │
  │                   ○                   │   Raute-Anordnung
  │                ○     ○                │   LEUCHTEND = GEFALLEN
  │             ○     ○     ○             │
  │                ○     ○                │
  │                   ○                   │
  │  ┌────┐      ○ ● ○         ┌──────┐  │
  │  │ 00 │      GRÜNE LAMPE   │ 0063 │  │   ← Summe A
  │  └────┘                    └──────┘  │
  │  ┌────────────────────────────────┐  │
  │  │   012      6       0063        │  │   ← Wurfnr · Kegel · Summe B
  │  └────────────────────────────────┘  │
  └──────────────────────────────────────┘
  ```

  Verifiziert an realen Frames:
  | Tafel | Leuchtende Lampen | Ziffer | Unteres Display |
  |---|---|---|---|
  | 1 | 5 | 5 | `001 5 0005` (Wurf 1, 5 Kegel, Summe 5) |
  | 3 | 6 | 6 | `012 6 0063` (Wurf 12, 6 Kegel, Summe 63) |

- **Grünlampe:** ca. 6×8 px im Originalframe, HSV `H∈[40,90] S>80 V>80`.
  Aus ≈ Score 20–24, An ≈ Score 67–75 (Score = Grünpixel-Anteil bzw. `G-(R+B)/2`).
  → Klar separierbar, aber **Baseline ist nicht 0** (beiges Tafelgehäuse) ⇒ relativer
  Schwellwert / Hysterese statt absolutem Cut.

---

## 4. Phasenplan & Status

Legende: ✅ fertig · 🔨 in Arbeit · ⬜ offen · ⏸ bewusst zurückgestellt

| Phase | Inhalt | Status | Zuständiger Skill |
|---|---|---|---|
| 0 | Analyse: Videos, Format, Tafel-Semantik | ✅ | `kegel-domain` |
| 1 | Video-Player (laden, Play/Pause, Frame-Step, Zeit/Frame-Anzeige) | ✅ | `kegel-video-pipeline`, `kegel-gui` |
| 2 | Kalibrierung: 4 Bahnen, 4 Eckpunkte, Homographie, speichern/laden | ✅ | `kegel-kalibrierung` |
| 3 | ROI-Konfiguration per Klick (Grünlampe, 9 Lampen, Kegelzahl, Wurfnr, Summen) | ✅ | `kegel-kalibrierung` |
| 4 | Grünlampen-Erkennung (ON/OFF, Hysterese, Zustandsmaschine) | ✅ | `kegel-detection` |
| 5 | Frame-Sampling rund um das Event | ✅ | `kegel-detection` |
| 6 | Lampenerkennung (9 Kegel, Wärme-Detektor) | ✅ | `kegel-detection` |
| 7 | Ziffernerkennung (7-Segment) + zeitliche Aggregation | 🔨 **~60 %** | `kegel-detection` |
| 8 | Wurferkennung, Zustandsmaschine, Double-Counting-Schutz | ✅ | `kegel-statemachine` |
| 9 | Summen, 15-Wurf-Zyklen, Validierung | ✅ | `kegel-statemachine` |
| 10 | GUI: Live-Analyse, Bahn-Panels, Wurftabellen, Zoom | ✅ | `kegel-gui` |
| 11 | Robustheit & Performance | ⬜ | `kegel-architektur` |
| 12 | Ergebnisversand (`ResultSink` → Supabase, je Wurf) | ✅ | `kegel-architektur` |
| 13 | Liveticker (Unterprojekt `apps/liveticker/`) | ✅ | — |

**→ Phase 11 (Robustheit) ist durchgeführt: 52 Minuten, 482 Würfe, 99,2 %
Erfassung, 3 Fehlerfälle. Bahn 3 und 4 bei 100 % Übereinstimmung.**

### Das System läuft end-to-end

Video laden → kalibrieren → **Analyse starten** liefert erkannte Würfe in den
Live-Tabellen. Gemessen an `2026-08-22 09-24-46.mp4` (4 Minuten Ausschnitt):
**27 Würfe auf 4 Bahnen, alle Summenketten stimmig**, 1,8 ms/Frame.

Beispiel Bahn 4 — Lampen, Ziffern und Summen stimmen durchgängig überein:

```
Wurf 1: 6 Kegel, Anzeige 6, Gesamt  6   conf 1.00
Wurf 3: 5 Kegel, Anzeige 5, Gesamt 11   conf 1.00
Wurf 5: 6 Kegel, Anzeige 6, Gesamt 22   conf 1.00
Wurf 8: 7 Kegel, Anzeige 7, Gesamt 43   conf 1.00
```

### Stand nach dem Durchlauf vom 2026-08-25

Gemessen an `2026-08-22 09-24-46.mp4`, 12 000 Frames (8 Minuten, 4 Bahnen):

| Kennzahl | Ausgangslage | **jetzt** |
|---|---|---|
| Grünzyklen erfasst | 51 von 71 (71,8 %) | **70 von 71 (98,6 %)** |
| Status VALID | 32 | **68 von 70** |
| Fälschlich als Leerwurf | 8 | **0** |
| Kegelziffer stimmt mit Lampen | 84 % | **98,5 %** (64 von 65) |
| Summenkette bestätigt Lampen | 19,4 % | **82,4 %** (28 von 34) |
| Wurfnummern | lückenhaft (3,4,5,6,10,13…) | **lückenlos 1–18 auf allen Bahnen** |
| Tempo | 1,8 ms/Frame | 8,0 ms/Frame (Budget 40) |

Sechs Ursachen, alle aus einer einzigen Frage entstanden („warum weichen fünf
Würfe ab?"):

1. **Die Kegellampen blinken** (BUG-007) — Periode 28–30 Frames, Dunkelphase bis
   15. Ein Messzeitpunkt traf zufällig die Dunkelphase.
2. **Das Messfenster war kürzer als die Dunkelphase** — vier Frames innerhalb von
   zehn konnten vollständig im Dunkeln liegen. Die Lampen werden jetzt über das
   ganze Fenster zwischen Grün-AUS und Grün-AN gesammelt.
3. **Eine Gegenprobe verwarf Würfe** (BUG-008) — 28 % gingen verloren, ohne dass
   die Ausgabe unstimmig aussah. Größter Einzeleffekt.
4. **Räumen** (Fachwissen des Nutzers) — das Ergebnis ist die Differenz Grün-AUS
   minus Grün-AN, nicht der Endstand.
5. **Die Anlage zeichnet die 9 ohne unteren Balken** (BUG-009) — jede 9 wurde
   zur 4.
6. **Die Summe wird erst kurz vor dem nächsten Wurf aktualisiert** (BUG-010,
   Hinweis des Nutzers) — sie wurde ausnahmslos im alten Stand gelesen.

Zwei Lehren, die über dieses Projekt hinausgehen:

- **Zu Punkt 5:** Genau dieser Fehler stand hier zuvor als *„systematisch, dagegen
  hilft auch Aggregation nicht"* — richtig beobachtet, aber als unlösbar abgelegt
  statt nachgesehen. Ein vergrößerter Blick auf den Ziffernausschnitt klärte ihn
  in Sekunden (P1: nicht raten — messen; und dazu gehört hinsehen).
- **Zu Punkt 6:** Der Versatz war messbar sichtbar (der Zuwachs passte 18-mal zum
  vorherigen Wurf, nur 8-mal zum aktuellen) und wurde als Nebenbefund notiert
  statt als Hauptspur verfolgt. **Ein systematischer Versatz sieht nie aus wie
  Rauschen.**

Verworfen und dokumentiert: die **Feinausrichtung der Ziffernrahmen auf höchste
Confidence** (`refine_radius: 0`). Sie war ein Denkfehler — Confidence misst die
Schärfe des Mustertreffers, nicht die Richtigkeit. Gemessen wurde aus „001" ein
„081", und ganze Bahnen bekamen falsche Wurfnummern.

### Phase 11: der Lauf über das ganze Training (2026-08-25)

`2026-08-22 09-24-46.mp4` — 77 784 Frames, 51,9 Minuten, ausgewertet in
14,6 Minuten (11,3 ms/Frame, rund 3,5× Echtzeit).

| Kennzahl | 1. Lauf | nach BUG-011 (Kegellampen) | **+ grüne Lampe** |
|---|---|---|---|
| erkannte Grünzyklen | 480 | 480 | **486** |
| gemeldete Würfe | 476 | 476 | **482** |
| Erfassung | 99,2 % | 99,2 % | **99,2 %** |
| Status ERROR | 31 | 6 | **3** |
| Status VALID | 442 | 467 | **473** |
| unvollständige Lampenmessung | 22 | 0 | **0** |
| Kegelziffer stimmt mit Lampen | 95,6 % | 97,5 % | **96,9 %** |
| Summenkette | 83,1 % | 86,3 % | **90,3 %** |
| Kegel gesamt | 3172 | 3178 | **3204** |

Bahn 3 und Bahn 4 liegen bei **100 %** Übereinstimmung.

**Spielergebnisse** — je Bahn vier Spiele à 30 Würfe:

```
Bahn 2:  190  210  180  179   | 759 Kegel
Bahn 3:  207  221  221  199   | 848
Bahn 4:  197  192  203  193   | 785
Bahn 5:  198  182  219  213   | 812
```

### Die zwei Befunde, die den Sprung von 31 auf 3 Fehler gebracht haben

Beide sind **derselbe Bug an zwei Stellen** (BUG-011): Eine absolute Schwelle
kann über eine lange Aufnahme nicht tragen, weil das Signal wandert.

**1. Kegellampen.** Ihr AUS-Niveau steigt von Median 151 auf 185; am Ende liegen
24 % aller AUS-Messungen über der festen Schwelle 195 und werden `UNKNOWN`.
Gelöst über einen mitlaufenden AUS-Bezugswert je Lampe.

**2. Grüne Lampe** — sie wog schwerer, weil sie den *Messzeitpunkt* steuert.
Beide Niveaus wandern aufeinander zu (AUS 28,3 → 36,4; AN 75,8 → 74,7),
überlappen aber nie. Über 100 von 130 Messungen landeten im Graubereich, und
`GREEN_OFF` löste erst aus, wenn ein Ausreißer die Schwelle unterschritt —
gemessen 180 Frames zu spät:

```
Frame 64075   grün geht tatsächlich aus, Kegellampen zeigen 7
Frame 64195   die Anlage stellt neu auf, Kegellampen gehen auf 0
Frame 64255   GREEN_OFF löst erst JETZT aus -> Ergebnis wird als 0 gelesen
```

Deshalb sahen diese Fälle wie „Lampen zählen 0" aus, obwohl mit den Lampen
nichts war. Gelöst, indem die Schwellen **anteilig zwischen** beide beobachteten
Niveaus gelegt werden.

**Die Lehre:** Ein falscher Messwert verfälscht eine Zahl — ein falscher
**Zeitpunkt** misst etwas ganz anderes. Und: Die grüne Lampe stand in BUG-011
bereits als ungeprüfte Stelle auf der Liste. Die Liste abzuarbeiten hätte den
zweiten Befund früher gehoben.

### Nachkalibrierung von Bahn 2 und 5 (2026-08-25) — brachte nichts

Der Nutzer hat auf meinen Vorschlag hin die Ziffernrahmen beider Bahnen neu
gesetzt (alle 8 Stellen je Bahn, Koordinaten nachweislich geändert). Das
Ergebnis über die vollen 52 Minuten:

| Kennzahl | alte Kalibrierung | **neu + Unentschieden-Band** |
|---|---|---|
| Würfe / VALID / ERROR | 482 / 473 / 3 | 482 / 473 / 3 |
| Ziffer stimmig | 96,9 % | 96,8 % |
| Summenkette | 90,3 % | **93,8 %** |

**Die Annahme war falsch.** Die handgesetzten Rahmen waren nicht der Engpass —
Bahn 3 und 4 stehen mit der *unveränderten* Kalibrierung bei 100 %. Gewonnen hat
nur die Summenkette. Die Widersprüche sind in beiden Läufen **dieselben Fälle zu
denselben Zeitpunkten**; die Kalibrierung berührt sie gar nicht.

Was die Fehlersuche tatsächlich gebracht hat, war der Blick auf die Bilder: Auf
Bahn 5 las der Leser eine `4` als `9`, weil beide Muster sich seit BUG-009 in
einem einzigen Segment unterscheiden und genau dieses bei 0,333 gegen eine
Schwelle von 0,307 lag. Behoben über `segment_ambiguous_band` — bei einer
Entscheidung auf Messerschneide liefert der Leser jetzt `?` statt zu raten.

**Lehre:** Vor einer Maßnahme, die den Nutzer Arbeit kostet, gehört ein Beleg,
dass die vermutete Ursache die richtige ist. Ich hatte nur eine Korrelation
(„Bahn 2 und 5 sind schlechter") und daraus eine Ursache gemacht.

### Quellen lassen sich gegenseitig auflösen (2026-08-25)

**Vorschlag des Nutzers:** „wenn er eine 4 oder 9 als Text erkennt, und oben 9
Lampen leuchten => 9 … Wir werden es ja dann merken, wenn die Summe steigt."

Umgesetzt: Der Ziffernleser liefert bei knappen Segmentmessungen die
**Kandidatenmenge** (`digit_reader.segment_candidates`). Steht die Lampenzahl
darunter, gilt das als stimmig — steht sie nicht darunter, bleibt es ein
Widerspruch.

| Kennzahl | vorher | **jetzt** |
|---|---|---|
| geprüfte Würfe | 438 von 482 | 438 von 482 |
| stimmig | 424 (96,8 %) | **428 (97,7 %)** |
| Widersprüche | 14 | **10** |

Die Richtung ist das Entscheidende: Die Lampen dürfen zwischen plausiblen
Lesungen **wählen**, aber keinen Wert **setzen**, den der Leser nie in Betracht
zog. Damit bleibt die Gegenprobe in der Lage, die Lampen zu widerlegen — das
unterscheidet sie von einer Scheinprüfung. Die Summenanzeige bleibt ohnehin
vollständig unabhängig (93,8 % Übereinstimmung bei 292 prüfbaren Übergängen).

**Warum das dem Nachjustieren von Schwellen vorzuziehen war:** Die Alternative
hätte an einer Bahn geholfen und an einer anderen geschadet — die Ziffern stehen
je nach Blickwinkel unterschiedlich schräg. Die Auflösung über eine zweite Quelle
ist von der Geometrie unabhängig.

### Phase 12 erledigt: Ergebnisversand je Wurf (2026-08-25)

Auf Wunsch des Nutzers: Jeder erkannte Wurf geht sofort als Zeile an eine
Supabase-Tabelle, damit der Spielleiter vor Ort live mitlesen kann.

```
sinks/base.py       ResultSink (abstrakt) + NullSink
sinks/payload.py    Wurf -> flache Datenbankzeile
sinks/supabase.py   HTTP-POST an PostgREST, ohne zusätzliche Bibliothek
sinks/queued.py     Warteschlange, Wiederholung, Zwischenspeicher
sinks/factory.py    baut den Abnehmer aus der Konfiguration
```

Drei Entscheidungen, die den Aufwand erklären:

1. **Der Versand hängt im GUI-Worker, nicht in der Analyse.** Der
   Architekturtest hat meinen ersten Versuch abgelehnt — `analysis/` darf nicht
   von `sinks/` abhängen. Die Regel hatte recht: Die Auswertung soll nicht
   wissen müssen, wohin ihre Ergebnisse gehen.
2. **`send` blockiert nie.** Die Analyse legt den Wurf in eine Warteschlange und
   ist fertig. Bei 40 ms Budget je Frame würde ein hakendes Netz sonst Frames
   kosten — und damit Würfe.
3. **Nichts geht verloren.** Was nach drei Versuchen nicht rausgeht, landet in
   `debug/versand_puffer.jsonl` und wird beim nächsten Start nachgeliefert. Die
   Kegel sind gefallen, ob die Datenbank erreichbar ist oder nicht.

Der Schlüssel steht in einer Umgebungsvariablen, nicht in der Konfiguration.
Einrichtung samt SQL: `docs/SUPABASE_SETUP.md`.

Neu im Modell: `ThrowResult.game_number` — ohne sie wären die vier Spiele einer
Bahn in der Tabelle nicht auseinanderzuhalten.

**Die Stream-Quelle steht** (`video/stream_source.py`): vorwärtsgerichtet, mit
Neuverbindung bei Aussetzern, kleinem Puffer (der aktuelle Frame zählt, nicht
der älteste) und lückenlos weiterlaufendem Frame-Index — ein Rücksprung darin
wäre für Ringpuffer und Zustandsmaschine eine Zeitreise. Verlorene Frames werden
beziffert, damit im Protokoll steht, wo Würfe fehlen können.

**Frühere Notiz, überholt:** `VideoSource` ist abstrakt, eine
`StreamVideoSource` tritt an dieselbe Stelle. Offen ist vor allem, was bei einem
Verbindungsabriss geschehen soll — bei einer Datei kann man zurückspringen, bei
einem Stream nicht. Das gehört gemessen, bevor es gebaut wird.

### Livestream als Quelle (2026-08-25)

Der Funktionsumfang ist damit vollständig, wie vom Nutzer festgelegt: *„Ich gebe
ihm ein Video (entweder URL oder eine Datei), möchte dann in der UI kalibrieren,
und wenn ich Analyse starten klicke, dann soll alles ausgewertet und an Supabase
gesendet werden."*

```
video/stream_source.py   StreamVideoSource -- vorwärts, mit Neuverbindung
video/factory.py         entscheidet Datei oder Stream, an EINER Stelle
gui/main_window.py       Eingabefeld für die Stream-Adresse
```

**Warum eine Fabrik und nicht zwei Verzweigungen:** Oberfläche und Analyse
öffnen jeweils ihre eigene Quelle (`VideoCapture` ist nicht thread-sicher).
Würden beide selbst entscheiden, könnte dieselbe Adresse an einer Stelle als
Stream und an der anderen als Datei behandelt werden.

Vier Eigenschaften, die ein Stream mitbringt:

| | Verhalten |
|---|---|
| Kein Ende | `read()` liefert erst None, wenn auch Neuverbindungen scheitern |
| Kein Zurückspringen | `seek()` gibt immer False — ein Rücksprung lieferte gebuchte Würfe erneut |
| Aussetzer sind normal | Nach 25 Fehlversuchen neu verbinden, bis zu fünfmal |
| Frame-Index läuft weiter | Ein Sprung darin wäre für Ringpuffer und Zustandsmaschine eine Zeitreise |

Verlorene Frames werden beziffert und protokolliert — dort können Würfe fehlen,
und das soll nicht unsichtbar bleiben.

**Randbedingungen, vom Nutzer geklärt:** Das Overlay bleibt während der ganzen
Übertragung eingeblendet, es gibt keine Werbeunterbrechung und keinen
Kameraschnitt, die Position ist innerhalb einer Übertragung stabil. Deshalb
genügt eine Kalibrierung zu Beginn. Rückspringen im Stream wird bewusst nicht
betrachtet.

### Die Übertragung enthält nur noch Gemessenes (2026-08-26)

Vom Nutzer festgelegt: Übertragen wird `Bahn | Anzahl Kegel | Kegelnummern |
Zeitstempel`. Alles Abgeleitete — Wurfnummer, laufende Summe, Zyklus,
Spielnummer, Zwischensummen — wird **weiterhin gerechnet und in der Oberfläche
angezeigt**, aber nicht gesendet.

Der Grund ist die Fehlerhistorie dieses Projekts: Genau die abgeleiteten Größen
sind schiefgegangen.

| Größe | was sie anrichtete |
|---|---|
| Wurfnummer aus der Anzeige | löschte 28 % der Würfe (BUG-008) |
| Spielerkennung nach 30 Würfen | traf den Bahnwechsel nicht |
| laufende Summe | driftete ab, sobald ein Wurf fehlte |

Alle drei setzen **Regelwissen** voraus — wann ein Bahnwechsel ansteht, wann ein
Spiel endet, wie gewertet wird. Das kennt die auswertende Anwendung, nicht die
Bilderkennung. Was hier gemessen wird, ist allein: *Auf dieser Bahn sind zu
diesem Zeitpunkt diese Kegel gefallen.*

Die Tabelle brauchte dafür eine Anpassung (`throw_number` und `status` waren
`not null`), siehe `docs/SUPABASE_SETUP.md`. Ende-zu-Ende geprüft: 52 Würfe
versendet, 52 Zeilen angekommen, nur die gemessenen Spalten gefüllt.

### Bodenwahrheit: das handgeführte Wurfprotokoll (2026-08-28)

Der Nutzer hat das 52-Minuten-Video von Hand ausgewertet
(`Wurfprotokoll_LangesVideo.pdf`, 4 Spieler × 4 Sätze × 30 Würfe = 480 Würfe).

**Das ist die erste Quelle in diesem Projekt, die nicht aus dem Bild stammt.**
Alle bisherigen Kennzahlen — „Ziffer stimmt mit Lampen", „Summenkette
bestätigt" — vergleichen zwei Lesungen desselben Bildes. Wo die sich einig
sind, kann trotzdem beides falsch sein. Genau daran ist unten `min_throw_frames`
gescheitert.

```
tools/parse_protocol.py     PDF -> data/ground_truth/*.csv (ohne Fremdbibliothek)
tools/compare_protocol.py   richtet die Wurffolge je Bahn aus und vergleicht
```

**Ausgerichtet wird, nicht nach Index verglichen** (Needleman-Wunsch). Fehlt ein
Wurf, verschöbe sich sonst alles dahinter und aus einem Fehler würden hundert.
Die Lückenstrafe ist teurer als ein Zahlendreher, sonst erklärte die Ausrichtung
jede falsche Zahl durch „fehlt + zuviel" und die Statistik sähe künstlich gut aus.

**Endstand am 2026-08-28:**

| Bahn | passt | falsch | fehlt | zuviel | erfasst | richtig |
|---|---|---|---|---|---|---|
| 2 | 120 | 0 | 0 | 0 | 100 % | **100 %** |
| 3 | 120 | 0 | 0 | 0 | 100 % | **100 %** |
| 4 | 120 | 0 | 0 | 0 | 100 % | **100 %** |
| 5 | 118 | 2 | 0 | 0 | 100 % | 98,3 % |
| **alle** | **478** | **2** | **0** | **0** | **100 %** | **99,6 %** |

```
Bahn        Satz 1      Satz 2      Satz 3      Satz 4       gesamt
2      196/196  ok 201/201  ok 189/189  ok 185/185  ok     771/771
3      207/207  ok 221/221  ok 221/221  ok 194/194  ok     843/843
4      197/197  ok 192/192  ok 203/203  ok 200/200  ok     792/792
5      198/198  ok 181/181  ok 219/219  ok 220/220  ok     818/818

Kegel gesamt 3224 gegen 3224 (+0)
```

**Alle sechzehn Sätze aufs Kegel genau. Alle 480 Würfe `VALID`, kein `ERROR`.**

Die zwei verbliebenen Abweichungen liegen im **Protokoll**, nicht im Werkzeug —
vom Nutzer geprüft und bestätigt (Bahn 5 bei 3:56 und 5:13, ein Zahlendreher
und sein Gegenstück; sie heben sich in der Satzsumme auf). Von den 478
unstrittigen Würfen sind 478 richtig.

Der Weg dorthin, jeder Schritt am Protokoll gemessen:

| | Kegel | richtig | fehlt |
|---|---|---|---|
| Ausgangsstand | 3177 | 97,1 % | 9 |
| `min_throw_frames` korrigiert, letzter Wurf nachgetragen | | | |
| + Grünphase mitlesen, früh melden | 3222 | 98,8 % | 2 |
| + Nullwürfe über den Fehlwurfzähler | 3222 | 99,2 % | **0** |
| + verdeckte Tafel erkennen | 3223 | 99,4 % | 0 |
| + anteilige Lampenschwellen, Zyklus ohne Veränderung | **3224** | **99,6 %** | **0** |

### Die letzten zwei Befunde

**1. Ein Spieler steht vor der Tafel.** Der Grün-Score fällt dabei auf exakt
null — das ist keine Lampenaussage, denn die unbeleuchtete Lampe sitzt auf
beigem Gehäuse mit Grünanteil und liegt bei 17–24. Als „aus" gelesen erzeugt
das einen Wurf, den es nie gab; einer davon vergiftete zusätzlich die
Grundlinie des nächsten echten Wurfs (dessen neun Kegel wurden zu null).

```
Score 0-1   Bahn 2 1044 Frames, Bahn 3 169, Bahn 4 und 5 keine
Score 2-3   Bahn 2    5 Frames, Bahn 3   8
```

Acht Abschnitte von 1 bis 18 Sekunden in 52 Minuten. Während der Verdeckung
wird die Bahn eingefroren — lieber eine Lücke als ein erfundener Wurf.

**2. Die AN-Schwelle lag über der physikalisch erreichbaren Helligkeit.** Eine
Lampe mit ungewöhnlich hohem AUS-Niveau (212 statt 164) bekam additiv eine
Schwelle von 212 + 45 = 257. Eine leuchtende Lampe ist aber bei 255 gesättigt:

```
AN    n=3822   min 229,1   Median 253,7   max 255,0
AUS   n= 489   min 134,2   Median 164,3   max 212,1
```

Sie leuchtete mit 254 und galt als `UNKNOWN`, während die Anzeige sie zählte.
Die Schwellen liegen jetzt **anteilig** zwischen Grundlinie und Sättigung: beim
typischen Niveau unverändert (164 → 209), bei hoher Grundlinie erreichbar
(212 → 233).

**Derselbe Fehlertyp wie BUG-011** — eine Größe als konstant angenommen, die es
nicht ist. Damals das Niveau, diesmal der Abstand.

**3. Ein Grünzyklus ohne Veränderung ist kein Wurf.** Zeigt die Kegelraute am
Ende dasselbe wie am Anfang, ist nichts gefallen — und ein Wurf ohne Kegel
erzeugt gar keinen Zyklus (Q10). Gemessen: genau einer von 479, und genau der
stand nicht im Protokoll. Die Regel ist bewusst eng: nur wenn Kegel *lagen* und
dieselben liegen bleiben, und nur bei vollständiger Lampenmessung.

### Was der Tag über das Vorgehen gezeigt hat

Fünf Vermutungen wurden widerlegt, bevor sie Code wurden — „Nullwürfe sind
unsichtbar", „der Ziffernleser ist zu schwach", „ein Wurfnummer-Wechsel verrät
sie", „das Blinken ist die Ursache", „das Abtastraster ist zu grob". Dreimal
war der entscheidende Schritt schlicht, **das Bild anzusehen**.

Zwei stille Fehler in Testvorlagen kamen dabei mit ans Licht: Die synthetischen
Kegellampen waren kaltweiß gemalt und damit **nie** lesbar (der Detektor
verlangt Farbwärme), und „grün aus" war gar kein Grün, sondern eine Verdeckung.
Beide Proben haben jahrelang weniger geprüft, als ihr Name versprach.

### Zwei Befunde, die nur mit der Bodenwahrheit auffindbar waren

**1. `min_throw_frames` warf echte Würfe weg — Korrektur eines eigenen Fixes.**

Der Wert stand auf 100, begründet mit „kürzestes echtes Fenster 158 Frames,
unter 100 nur Fehlauslöser". Diese Messung war **zirkulär**: Als „echtes
Fenster" galt, was das Werkzeug selbst zu einem Wurf gemacht hatte — die kurzen
hatte es bereits verworfen und wurden deshalb als Fehlauslöser gezählt.

```
F73574  51 Frames  ->  Protokoll: Bahn 4, Satz 4, Wurf 22, 2 Kegel
F74452  46 Frames  ->  Protokoll: Wurf 24, 2 Kegel
F76247  44 Frames  ->  Protokoll: Wurf 27, 7 Kegel
```

Echtes Fenster ab **44** Frames, der Fehlauslöser aus BUG-013 war **64** Frames
lang. Die Bereiche überlappen — eine Schwelle auf der Fensterlänge kann beides
grundsätzlich nicht trennen. Auf 0 gesetzt; gegen BUG-013 wirkt allein
`detection.green.adaptive_min_span`, dort liegt die Ursache.

**Lehre:** Ein Schwellwert, der aus der eigenen Ausgabe abgeleitet wird, prüft
nur, ob das Werkzeug mit sich selbst einig ist.

**2. Der letzte Wurf jeder Bahn geht verloren.** Ein Wurf wird erst beim
*nächsten* Grün-AN gemeldet — am Videoende kommt das nie. Genau vier Würfe
fehlten, einer je Bahn, jedes Mal der dreißigste (6, 2, 7, 7 Kegel).
`AnalysisPipeline.finalize()` trägt sie nach.

### Spielwechsel: die Anzeige zeigt `000  0000` (2026-08-28)

Vom Nutzer beschrieben. **Gemessen** mit `tools/measure_display_reset.py`:

| | |
|---|---|
| Standzeit je Bahn | 20 bis 90 Sekunden |
| an allen 3 Satzgrenzen | auf allen 4 Bahnen |
| Kontrolle mitten im Satz | **0 Treffer** in 3000 Frames (2 Fenster, 4 Bahnen) |
| gleichzeitig? | **nein** — bis zu 36 s Abstand zwischen den Bahnen |

Der bisherige Weg (Rücksprung der Wurfnummer) traf bereits **12 von 12**
Satzgrenzen. Der Nullzustand kommt als **zweites, unabhängiges** Zeichen dazu:
Der Rücksprung setzt mindestens `game_reset_after` vorher gezählte Würfe
voraus — endet ein Spiel früher, ist er blind. Der Nutzer weist darauf hin,
dass die Rücksetzung „meistens nach 30 Wurf, aber nicht immer" kommt.

Der Zustand steht in der **Pause**, also im Fenster des *letzten* Wurfs des
alten Spiels. Gemeint ist der *nächste*. Deshalb eine Merkzelle mit genau einem
Wurf Verzögerung — belegt an Bahn 2:

```
F18594   letzter Wurf Satz 1, grün aus
F18900   Nullzustand beginnt      <- Fenster dieses Wurfs
F20025   Nullzustand endet
F20148   erster Wurf Satz 2, grün aus
```

Kostet im laufenden Spiel nichts: Die Wurfnummer wird nur gelesen, wenn die
Summe null zeigt. **Nicht im Versand** — `game_number` war dort nie enthalten.

### Der Stream begann stündlich von vorn (2026-08-29/30) — behoben, BUG-014

Der Lauf vom 29.08. lieferte **3210 Würfe statt 1517**; 1693 davon waren
Wiederholungen, alle an Supabase gesendet.

**Die Aufzeichnung war nicht schuld.** Playlist geprüft: VOD, 3128 Segmente
lückenlos, 3:28:31, keine Discontinuity, keine Zeitabweichung.

**Der Beleg, der die Ursache in einem Schritt festgelegt hat:** Vorschau und
Analyse lasen dieselbe URL parallel und sprangen zur *selben Wandzeit* zurück —
aber an *verschiedenen Videopositionen* (65:44 gegen 46:41). Eine Eigenschaft
des Videos hätte beide an derselben Stelle erwischt. Gemeinsam war nur der
Zeitpunkt: 60,6 Minuten nach dem Verbindungsaufbau riss die Verbindung ab, und
die VOD-Playlist begann beim Neuaufbau wieder bei Segment 0.

Die 46:41 waren also nie eine Videolänge, sondern 60,6 min Wandzeit × 0,77 —
so schnell lief die Analyse.

**Behoben durch Rücksprung an die alte Stelle.** Meldet die Quelle eine Länge
(`CAP_PROP_FRAME_COUNT`), ist sie eine Aufzeichnung, und der Sprung ist
framegenau. Am echten Stream gegengeprüft, Abriss bei Frame 200 erzwungen:
60 von 60 Frames deckungsgleich, 0 Wiederholungen. Bei einer Aufzeichnung gibt
es jetzt nur zwei Ausgänge — wieder aufsetzen oder aufhören.

Warum nach genau einer Stunde abgerissen wird, ist offen (`OPEN_QUESTIONS.md`
Q11) — die Signaturen sind es nachweislich nicht, sie gelten zwölf Stunden.

### Was noch offen ist

- **3 Fehlerfälle**, alle auf Bahn 2 — zwei davon mit dem Muster `Lampen 0`
  gegen eine Ziffer. Die Zeitreihe an genau diesen Stellen ist noch nicht
  angesehen.
- **10 Widersprüche.** Fünf davon zeigen `Lampen = 0`, obwohl im Bild sichtbar
  Lampen leuchten — das ist die dominierende verbliebene Fehlerklasse.

  **Konkrete Spur dazu:** Die Zeitreihe zeigt, dass die Kegellampen bereits
  aufleuchten, **während die grüne Lampe noch an ist** — das Wurfergebnis steht
  also vor `GREEN_OFF` fest. Das Sammelfenster beginnt aber erst bei `GREEN_OFF`.
  Naheliegender nächster Schritt: auch die Frames davor einbeziehen (der
  Ringpuffer hält 50).
- **45 Würfe ohne lesbare Kegelziffer.** Nicht die Rahmen (nachgemessen, siehe
  oben), sondern schlicht Momente, in denen die Anzeige nichts zeigt oder die
  Lesung unentschieden ist. Kein Handlungsbedarf, solange die Lampen tragen.
- **4 verlorene Würfe**, genau einer je Bahn. Riecht nach einem Randfall am
  Videoanfang oder -ende.

### Was Phase 7 noch blockiert

Die Ziffernerkennung liegt bei 59 von 70 lesbaren Feldern. Der Weg dorthin ist
dokumentiert (alle Stufen am Material gemessen, `docs/VIDEO_ANALYSIS.md`):

| Ansatz | Treffer |
|---|---|
| Segment-Dekodierung, Rot-Maske | 0/12 |
| Segment-Dekodierung, Otsu-Maske | 5/12 |
| Template Matching (synthetisch) | 6/11 |
| Template Matching + zeitliche Aggregation | 7/12 |
| Kalibrierte Einzelziffern + Alternativmuster | **59/70** |

Höhere Auflösung half **nicht** (identisches Ergebnis bei 440×530, 880×1060 und
1320×1590) — Interpolation fügt keine Information hinzu.

Verbleibende Schwächen:
1. **Die vierstellige Gesamtsumme** ist bei 39 von 70 Würfen lesbar. Die
   Ziffernrahmen sind handgesetzt und sitzen auf Bahn 2 und 5 ein bis zwei Pixel
   daneben. Eine automatische Ausrichtung braucht ein Kriterium, das **vom
   Leseergebnis unabhängig** ist — etwa die Lage des Ziffernumrisses. Der
   Confidence-Ansatz ist gemessen gescheitert.
2. **Sechs Summenketten** stimmen noch nicht. Zwei davon (Bahn 3, Wurf 14/15)
   sehen nach einer einzelnen falsch gelesenen Summe aus: 8+7 gegen 13+2 ergibt
   beidesmal 15.
3. ~~Q8: Ziffer 9 bei dunklen Lampen~~ — **geklärt**: dasselbe Blinken, der
   Messzeitpunkt fiel in eine Dunkelphase. Belegt in `OPEN_QUESTIONS.md`.

**Wichtig:** Die Kernfunktion hängt nicht daran. Die Kegelanzahl kommt aus den
Lampen (zuverlässig), die Wurferkennung aus der Grünlampe. Die Ziffern sind
Gegenprobe und Wurfnummer — bei Widerspruch sinkt die Confidence, das Ergebnis
geht nicht verloren.

---

## 4a. Arbeitsregel vor allem anderen

**[messen-vor-bauen](messen-vor-bauen/SKILL.md)** — vor jeder Änderung an einem
Erkennungsverfahren steht eine Messung, die sie trägt, und zwar über den
*gesamten* Bestand statt über die auffälligen Fälle. In diesem Projekt dreimal
verletzt, dreimal teuer: eine unnötige Nachkalibrierung durch den Nutzer, eine
Feinausrichtung, die Wurfnummern zerstörte, und ein zu kurz bemessenes
Blink-Fenster.

## 5. Skill-Landkarte — welcher Skill wann?

```
                    ┌──────────────────────┐
                    │  ORCHESTRATION.md    │  ← immer zuerst (dieses File)
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐   ┌─────────▼─────────┐   ┌────────▼─────────┐
│ kegel-domain   │   │ kegel-architektur │   │ BUG_ORCHESTRATION│
│ Fachwissen:    │   │ Schichten, ABCs,  │   │ Bug → Fix →      │
│ Tafel, Regeln, │   │ Config, DI,       │   │ Regressionstest  │
│ 15er-Zyklen    │   │ keine Magic Nums  │   │ → BugSkill       │
└────────────────┘   └───────────────────┘   └──────────────────┘
        │                      │
   ┌────┴──────┬───────────────┼───────────┬─────────────┐
   │           │               │           │             │
┌──▼────────┐ ┌▼────────────┐ ┌▼─────────┐ ┌▼──────────┐ ┌▼────────┐
│kegel-video│ │kegel-       │ │kegel-    │ │kegel-     │ │kegel-   │
│-pipeline  │ │kalibrierung │ │detection │ │statemachine│ │gui      │
└───────────┘ └─────────────┘ └──────────┘ └───────────┘ └─────────┘
                                    │             │           │
                              ┌─────┴─────────────┴───────────┘
                              │
                    ┌─────────▼──────────┐   ┌──────────────┐
                    │ kegel-debug-logging│   │ kegel-testing│
                    └────────────────────┘   └──────────────┘
```

### Trigger-Tabelle

| Ich arbeite an … | Skill laden |
|---|---|
| Bedeutung von Tafel-Elementen, Kegelregeln, Zyklen, `valid`-Definition | `kegel-domain` |
| Neuem Modul, Schichtgrenzen, Interfaces, Config-Parametern | `kegel-architektur` |
| Video laden, seeken, Frames, FPS, Streams, Performance | `kegel-video-pipeline` |
| Eckpunkte, Homographie, ROIs, Kalibrierungs-Persistenz | `kegel-kalibrierung` |
| Grünlampe, Kegellampen, Ziffern, Schwellwerte, Aggregation | `kegel-detection` |
| Zustandsübergänge, Wurfzählung, Double Counting, Plausibilität | `kegel-statemachine` |
| PySide6, Widgets, Threads, Signals, Overlays | `kegel-gui` |
| Debug-Frames, Event-Log, Nachvollziehbarkeit | `kegel-debug-logging` |
| Tests schreiben, Fixtures, synthetische Frames | `kegel-testing` |
| **Ein Bug ist aufgetreten** | `BUG_ORCHESTRATION.md` |

---

## 6. Arbeitsablauf pro Aufgabe

```
1. ORCHESTRATION.md lesen  → Phase & Status prüfen
2. Passenden Skill laden   → Konventionen einhalten
3. Bei Unklarheit über Realdaten:
      NICHT raten → Frames extrahieren → anschauen → docs/VIDEO_ANALYSIS.md ergänzen
      Bleibt es unklar → docs/OPEN_QUESTIONS.md
4. Implementieren (Config statt Magic Numbers, ABC statt Direktkopplung)
5. Tests schreiben (kegel-testing)
6. Tests laufen lassen
7. ORCHESTRATION.md Status aktualisieren
8. Trat ein Bug auf? → BUG_ORCHESTRATION.md → BugSkill anlegen
```

---

## 7. Projektstruktur

```
Kegel_CV/
├── .claude/skills/          ← Skills + diese Orchestrierung
│   ├── ORCHESTRATION.md          (dieses File)
│   ├── BUG_ORCHESTRATION.md      (Bug-Workflow)
│   └── bugs/                     (BugSkills + BUGS_INDEX.md)
├── config/default.yaml      ← alle Parameter, keine Magic Numbers
├── data/calibrations/       ← gespeicherte Kalibrierungen (JSON)
├── debug/                   ← Debug-Frames + Event-Logs (gitignored)
├── docs/
│   ├── VIDEO_ANALYSIS.md         (gemessene Fakten über das Material)
│   ├── ARCHITECTURE.md           (Architekturentscheidungen + Begründung)
│   └── OPEN_QUESTIONS.md         (offene fachliche Fragen)
├── kegelVideos/             ← Quellmaterial
├── src/kegel_cv/
│   ├── config/     Config-Laden & Validierung (pydantic)
│   ├── models/     Datenmodelle (Throw, Lane, Calibration, ...)
│   ├── video/      VideoSource-Abstraktion
│   ├── calibration/Homographie, ROIs
│   ├── detection/  Detektoren + Zustandsmaschine
│   ├── analysis/   Sampling, Aggregation, Validierung
│   ├── debug/      FrameLogger, EventLogger
│   ├── sinks/      ResultSink → Supabase, je Wurf (Phase 12)
│   └── gui/        PySide6-Oberfläche
├── tests/          unit/ integration/ fixtures/
└── tools/          Analyse-/Hilfsskripte (nicht Teil der App)
```

---

## 8. Offene Punkte (Kurzfassung — Details in `docs/OPEN_QUESTIONS.md`)

| # | Frage | Blockiert |
|---|---|---|
| Q1 | Welche realen Bahnnummern (1–5) zeigen die 4 Overlay-Tafeln? | Zuordnung Ergebnis→Bahn |
| Q2 | Bedeutung des linken 2-stelligen Displays (`00`) — Satz? Durchgang? | Satzlogik |
| Q3 | Sind Summe A und Summe B immer identisch, oder A = Satz / B = Gesamt? | Validierungsregel |
| Q4 | Welche Tafel hat die flackernden Ziffern (Auftrag §8)? | OCR-Strategie |
| Q7 | Bedeutung der roten/gelben Statuslampe über dem Kegelbild | Störungserkennung |
| ~~Q5~~ | **Geklärt 2026-09-01:** 1 vorn, 9 hinten. Die Lampen zählen von oben, die Kegel von vorn — Zuordnung `[9,7,8,4,5,6,2,3,1]` in `calibration.pin_number_mapping` | erledigt |
| Q6 | Wird zwischen "Volle" und "Abräumen" unterschieden? | Wurfmodus |
| Q12 | Warum kriecht der Grünscore manchmal durch die Totzone? | nichts, erklärt einen Wurfverlust |
| ~~Q13~~ | **Geklärt und behoben 2026-09-02:** Bahn 4 ist überstrahlt, nicht farbstichig. Enge Lampen-ROIs plus neuer Schwellensatz | erledigt |

---

## Behebungsagenda aus dem Spieltag 2026-08-29 (Stand 2026-08-30)

Vollständig in `docs/AGENDA.md`. Kurzfassung:

| | Thema | Status |
|---|---|---|
| A1 | Eingeschobener Wurf verschiebt die Wurfnummernkette | umgesetzt, greift am Material nicht — Anlass durch A2 entfallen |
| **A2** | **Feste Schwelle durch gleitendes Histogramm ersetzt** | **✅ erledigt, am Material bestätigt** |
| **A3** | **Lampen-ROI verkleinern** | **✅ erledigt 2026-09-02, am Material bestaetigt** — UNKNOWN auf Bahn 4 von 6,73 % auf 0,50 %, ERROR-Wuerfe des Spieltags von 15 auf 0 |
| **A4** | **`000 0000` trug auf keiner Bahn durch** | **✅ erledigt, am Material bestätigt** |
| **A5** | **Helligkeitssperre der Ziffernerkennung** | **✅ erledigt, am Material bestätigt** |

**A4 im Kern:** Zwei getrennte Fehler. (1) Die Nullzustands-Prüfung hing am
Wurffenster — ob ein Spielwechsel erkannt wurde, entschied damit der Zufall,
nämlich ob die Anlage die Anzeige gerade während einer Grünpause zurücksetzte.
Auf Bahn 2 stand `000/0000` 54 Sekunden, das Fenster war noch 62 Frames offen.
(2) Der Zustand steht 40 bis 91 Sekunden und wurde mehrfach gemeldet; jede
zweite Meldung erzeugte einen Geisterlauf. Jetzt eigener Takt (25 Frames,
fensterunabhängig) und eine Sperre, die erst nach 10 Messungen in Folge fällt —
gemessen, weil die längste Fehllesungs-Strähne innerhalb des Zustands 6 betrug.

Ergebnis: zwei Gegenläufe, je 4 Meldungen für 4 Bahnen, keine Doppelmeldung.

**A5 im Kern:** `min_display_brightness` misst jetzt das Maximum des Rotkanals
statt des 95. Perzentils (Schwelle 200 statt 230). Eine `1` leuchtet mit zwei
von sieben Segmenten und blieb gemittelt unter der Schwelle, obwohl sie im Bild
eindeutig ist. Unlesbare Zellen: 13 von 420 auf **1 von 402**.

Gegen eine belastbare Wahrheit (nur Würfe in die Vollen, Bahn 2 und 3) liegt die
Ziffernerkennung bei **96,5 %**. Ein formbasierter Erkenner bringt nichts — er
liegt im selben Bereich. Die Segmentabtastung bleibt.

Neue Werkzeuge: `tools/measure_zero_display.py`, `tools/measure_digit_failures.py`,
`tools/cluster_digits.py`, `tools/collect_digit_samples.py`,
`tools/fit_digit_classifier.py`.

**A2 im Kern:** Die mitlaufenden Schwellen der grünen Lampe wurden aus
Perzentilen gerechnet. Lag eine Bahn 71 % des Fensters auf AN, war das
20. Perzentil kein AUS-Niveau mehr, und die AUS-Schwelle landete *innerhalb*
der AN-Wolke. Gemessen: derselbe Score (47,8) einmal AUS, drei Frames später
AN. Der dabei entstandene GREEN_OFF erzeugte einen Wurf, den es nie gab.

Ersetzt durch ein gleitendes Histogramm über 15 Minuten mit Talsuche zwischen
den beiden Wolken — und der unverhandelbaren Sperre: **bei nur einer Wolke wird
keine Schwelle gerechnet** (wörtlich BUG-013).

Ergebnis am Material (F28000–56000): Spieler A auf Bahn 5 von 16/30 auf
**30/30**, Spieler B auf Bahn 3 bleibt bei 30/30. Kein Wurf erfunden.

Neue Werkzeuge: `tools/export_roi_frames.py` (Bildbeleg mit kalibrierten
Rahmen, verträgt Stream-URLs), `tools/fit_green_histogram.py` (spielt eine
aufgezeichnete Grünspur durch das Verfahren).


---

## Stand nach dem vollstaendigen Lauf (2026-08-31)

Lauf ueber den ganzen Spieltag 2026-08-29 (312 786 Frames, 1731 Wuerfe,
98,7 % VALID). Protokollvergleich ueber alle 24 Saetze:

| Bahn | Treffer | vorher |
|---|---|---|
| 2 | **180/180 (100 %)** | 100 % |
| 3 | **180/180 (100 %)** | 100 % |
| 4 | 156/180 (86,7 %) | — |
| 5 | **179/180 (99,4 %)** | 157/180 (87 %) |

23 von 24 Saetzen sicher zugeordnet, 20 davon mit 30/30. Keine Duplikate,
0 Neuverbindungen waehrend des Laufs.

### Danach behoben (alle mit Tests und Gegenprobe)

* **BUG-015** — Am Ende der Aufzeichnung wurde endlos neu verbunden statt
  beendet. Die Quelle kannte ihre Laenge (312 786) und benutzte sie nicht;
  erreicht wurden 312 784. Jetzt `stream_end_tolerance_frames`.
* **A6 (Bahn 4)** — 42 erfundene Wuerfe ueber den Fehlwurfzaehler. 14 Spruenge
  um drei, alle auf einer Bahn; Bildbeleg F270290: Tafel zeigt `00`, gelesen
  wurde `03`. Jetzt `foul_max_rise` (1) -- zwischen zwei Lesungen (10 Frames)
  kann hoechstens ein Wurf liegen, ein Wurfzyklus dauert 216-338 Frames.
* **A7 (Spielwechsel)** — Zwei Zeugen meldeten denselben Wechsel nacheinander,
  der erste Wurf des neuen Spiels landete allein in einem eigenen Spiel
  (Bahn 2: acht Ein-Wurf-Spiele). Jetzt `game_reset_min_gap_throws` (5).

### Was noch offen ist

Ein **vollstaendiger neuer Lauf** mit allen drei Behebungen. Die bisherigen
Zahlen zu Spielenden je Bahn (12/16/8/17) sind durch A6 verunreinigt.


---

## 2026-08-31: 720 von 720

Vollstaendiger Lauf ueber den Spieltag 2026-08-29 (87,6 min, 312 784 Frames,
1690 Wuerfe, 1702 Gruenzyklen):

    24 von 24 Saetzen sicher zugeordnet
    Getroffene Wuerfe in den sicheren Funden: 720

Alle vier Bahnen bei 180/180. Zum Vergleich der Weg: Bahn 5 stand bei 157/180,
Bahn 4 bei 156/180.

Wuerfe je Bahn 422/420/422/426, keine Duplikate, eine Neuverbindung ohne
Frameverlust, Lauf endet von selbst.

### Was die Strecke gekostet hat -- jeder Schritt am Material belegt

| | |
|---|---|
| BUG-014 | Aufzeichnung begann nach jedem Abriss von vorn (1693 Duplikate) |
| A2 | Perzentil-Schwelle der gruenen Lampe lag in der AN-Wolke |
| A5 | Helligkeitssperre verwarf lesbare Ziffern, vor allem die `1` |
| A4/A7 | `000 0000` hing am Wurffenster; zwei Zeugen zaehlten denselben Wechsel |
| A6 | Fehlwurfzaehler erfand 42 Wuerfe auf Bahn 4 |
| BUG-015 | Lauf endete nie von selbst |
| A8 | AN-Schwelle der Kegellampen lag im Auslaeufer der AUS-Wolke |

### Offen

* 12 Gruenzyklen ohne Wurfergebnis (0,7 %) -- kein Protokollwurf fehlt
* 16 Wuerfe mit Status ERROR (vorher 11) -- Preis der strengeren Schwelle
* Bahn 4 findet nur 8 Spielenden, ein Spiel mit 172 Wuerfen

### A9 (2026-08-31): Die Ziffern-ROIs des Summenfeldes sassen falsch

Bahn 4 fand nur 8 Spielenden. Grund: Waehrend die anderen Bahnen auf `000 0000`
standen, las Bahn 4 stabil `total_b = 3000`. Eine `0` ist abcdef; fehlen die
linken Segmente e und f, bleibt abcd -- naechstliegend die `3`. Fehlt auch d,
bleibt abc: die `7`. Beide Fehlwerte sind dieselbe abgeschnittene Null,
betroffen waren 37 von 234 lesbaren Summen.

**Das Mass, ohne das jede Verschiebung geraten waere:** Die fuehrende Stelle
eines mehrstelligen Feldes ist auf dieser Tafel immer null. Der Anteil der
Lesungen, bei denen sie es nicht ist, sagt ohne jeden Sollwert, ob die ROI
sitzt. Gemessen ueber alle 4 Bahnen und 3 Felder waren nur 2 von 12
Kombinationen betroffen.

Beide Irrwege sind gemessen und im Werkzeug festgehalten: nach LINKS verschieben
hilft nicht (die Richtung ist umgekehrt), und die linke Kante zu verbreitern
macht es schlechter (Leerraum schiebt die Ziffer beim Normieren aus den
Segmentflaechen).

Ergebnis: 720/720 haelt, Spielenden auf Bahn 4 von 8 auf 14, groesstes Spiel
von 172 auf 50 Wuerfe, unmoegliche Summen von 37 auf 1.

Neue Werkzeuge: `tools/fit_digit_offsets.py` (misst), `tools/shift_digit_rois.py`
(schreibt eine neue Kalibrierung, ueberschreibt nie).


## Stand nach dem Vollauf vom 2026-09-01

Quelle: erster Spieltag als HLS-VOD, 312 784 Frames, Lauf
`lauf_2026-09-01_17-38-42`. Gegen den Vergleichslauf `14-08-10` derselben
Quelle gehalten.

| | vorher | nachher |
|---|---|---|
| Wuerfe | 1690 | **1695** |
| davon VALID | 1662 | **1667** |
| EMPTY / ERROR | 13 / 15 | **13 / 15** |
| Raeumwuerfe | 242 | **247** |
| Kegel gesamt | 11 477 | **11 483** |

### In diesem Lauf behoben

| | Thema | Beleg |
|---|---|---|
| Q5 | Kegelnummerierung umgestellt: 1 vorn, 9 hinten | `pin_number_mapping`, Nutzer bestaetigt |
| **BUG-016** | **Grundlinie aus zwei Quellen (Nutzeridee)** | **+5 Wuerfe, -0 Verluste, alle mit passender Tafel-Ziffer** |

Der Fix nimmt die Grundlinie als Schnittmenge aus dem Lampenstand kurz **vor**
dem Gruen-AN und dem Fenster **danach**. Beide Einzelmessungen irren nur nach
oben, deshalb ist der Schnitt sicher. Ueber 1702 Zyklen widersprechen sich die
Quellen genau fuenfmal -- und es sind genau die fuenf verlorenen Wuerfe.

Nebenbefund: Was die fuenf verbindet, ist nicht der lange Anlauf (einer hatte
nur 7 Frames), sondern ein **schwaches Gruensignal** (Maximalscore 44 bis 70,
gesund sind 77 bis 79). Der Fix haengt an keiner Eigenschaft der
Gruenerkennung und traegt deshalb breiter als der Fehlerpfad, aus dem er kam.

### Danach offen

* 16 Gruenzyklen ohne Wurf (vorher 21), 7 davon meldet der Lauf selbst
* Bahn 4 ist signalschwach: 6-9 % UNKNOWN bei den Kegellampen gegen 0,3 % auf
  Bahn 2; kostet mindestens den Zyklus F47150 (Q13)
* Der erste Abschnitt auf Bahn 4 hat 51 Wuerfe -- Warmwerfen und erster Satz
  sind verschmolzen, ein Spielwechsel fehlt
* Bahn 5, Lauf 3.3 hat 31 Wuerfe
* Q12 (kriechender Gruenscore) bleibt ohne Frames unbelegbar


## Bahn 4: warum ein Weissabgleich nicht hilft (2026-09-01)

Der Nutzer fragte, ob ein Weissabgleich die schwache Bahn 4 retten koennte.
Gemessen statt geraten, mit `tools/measure_lamp_channels.py` (5400 Messungen
der einzelnen Farbkanaele) und einem Blick auf die ROI-Ausschnitte:

**Drei Erklaerungen geprueft, zwei widerlegt:**

| | Erklaerung | Ergebnis |
|---|---|---|
| 1 | Farbstich, den ein Weissabgleich behebt | **widerlegt** -- Rot ist in 99,7-100 % aller Messungen der groesste Kanal, auf jeder Bahn, bei AUS wie bei AN. Der Detektor misst `max(B,G,R)`, haengt also nur am Rotkanal. Simuliert bringt ein Abgleich Bahn 4 **-6,6** Kontrastpunkte |
| 2 | Die ROIs sitzen ungueustiger | **widerlegt** -- angesehen bei Frame 20000, die Rahmen sitzen auf beiden Bahnen sauber und sind gleich gross |
| 3 | Die Schwellenformel gibt dort den kleinsten Abstand | **belegt** -- siehe unten |

**Der Kern.** Die adaptive Schwelle rechnet `Niveau + Anteil x (255 - Niveau)`.
Je hoeher das Ruheniveau, desto kleiner der Spielraum -- und desto enger der
Abstand zur Schwelle. Genau dort, wo wegen breiterer Streuung der groesste
Abstand noetig waere, gibt sie den kleinsten: Bahn 2 bekommt 49 Punkte,
Bahn 4 nur 23.

Bahn 4 ist nicht farbstichig, sondern ueberstrahlt: Schwarzwert um 34 Punkte
angehoben (auf allen drei Kanaelen gleich), Weisswert nicht ausgereizt (2,6 %
der AN-Messungen in der Saettigung gegen 84,3 % auf Bahn 2).

**Nicht umgesetzt, weil nur simuliert:** `baseline_off_fraction` von 0,31 auf
0,50 wuerde Bahn 4 von 6,71 % auf 0,87 % UNKNOWN bringen, bei 18 Punkten
Restluecke zur AN-Schwelle. Die Totzone enthaelt auf keiner Bahn eine einzige
Messung im AN-Bereich (0,0 %), es ginge also nichts verloren. Bevor die Zahl in
die Konfiguration wandert, gehoert ein Vollauf mit Gegenprobe gegen die
Tafel-Ziffer dagegen gehalten.

**Auch die gruene Lampe ist kein Farbproblem.** Sie wird ueber eine HSV-Maske
gelesen, die Saettigung >= 80 verlangt; gemessen werden 141 bis 168. Der
Score-Unterschied entsteht am RAND der Lampe (Bahn 2 verliert 4,3 Prozentpunkte
der gruenen Pixel, Bahn 4 12,5) -- ein Fall fuer A3 (ROI verkleinern), nicht
fuer einen Farbeingriff.


## Enge Lampen-ROIs: umgesetzt und bestaetigt (2026-09-02)

`lauf_2026-09-02_18-30-19` gegen den Referenzlauf `2026-09-01_17-38-42`
derselben Quelle:

| | weiter ROI | **enger ROI** |
|---|---|---|
| Wuerfe | 1695 | 1695 |
| VALID | 1667 | **1679** |
| **ERROR** | **15** | **0** |
| Abweichung zur Tafel-Ziffer | 8 von 1621 | **7 von 1621** |
| UNKNOWN Bahn 4 | **6,73 %** | **0,50 %** |

**Was geaendert wurde:**

* `data/calibrations/1Spieltag_enge_lampen.json` (neu) -- 36 Lampen-ROIs auf
  50 % verkleinert und auf die gemessene Lampenmitte zentriert. Die alte
  `1Spieltag.json` ist unberuehrt; der Rueckweg ist ein anderer
  `--calibration`-Pfad plus `core_percentile: 70`.
* `config/default.yaml` -- `core_percentile` 70 -> 0,
  `baseline_off_fraction` 0,31 -> 0,49, `baseline_on_fraction` 0,75 -> 0,70,
  `brightness_off_threshold` 195 -> 198, `brightness_on_threshold` 210 -> 222,
  `baseline_off_margin` 28 -> 75, `baseline_ignore_above` 235 -> 215.
* Kein Eingriff in `src/`. ROI-Geometrie gehoert in die Kalibrierung.

**Zwei Werte haetten die Aenderung still sabotiert:** `baseline_off_margin: 28`
klemmte das Ruheniveau bei 170 fest, waehrend die neuen Niveaus zwischen 132,8
und 159,5 liegen -- die Deckelung haette jede Messung verfaelscht. Und
`baseline_ignore_above: 235` lag ueber dem niedrigsten AN-Perzentil des engen
ROI (236,8), haette also leuchtende Lampen ins AUS-Gedaechtnis gelassen.

**Neue Werkzeuge:** `tools/measure_roi_shrink.py` (sammeln/auswerten),
`tools/fit_lamp_rois.py` (schreibt die Kalibrierung),
`tools/fit_lamp_thresholds.py` (rechnet den Schwellensatz),
`tools/measure_lamp_channels.py` (entscheidet Farbfragen).

**Offen:** Bahn 4 F289308 verliert einen Kegel, den die Tafel zaehlt -- ein
Einzelfall unter 1621 geprueften Wuerfen, aber ungeklaert.


## Spielwechsel nur an der Wurfnummer (2026-09-02)

Nutzeridee: Die Wurfnummer wird zu 100 % gelesen, die Summe nicht -- also nur
die Wurfnummer als Zeugen fuer `000` nehmen.

Der Kern war nicht die Vereinfachung, sondern die REIHENFOLGE: Die Summe wurde
zuerst gelesen und war damit der Torwaechter. War sie unlesbar, kam die
Wurfnummer nie zum Zug -- der schwaechere Zeuge entschied ueber den staerkeren.

Vollauf `lauf_2026-09-02_21-11-00` gegen `18-30-19`:

| | vorher | nachher |
|---|---|---|
| Wuerfe / Kegel | 1695 / 11 479 | **unveraendert** |
| VALID / EMPTY / ERROR | 1679 / 16 / 0 | **unveraendert** |
| Abweichung zur Tafel | 7 von 1621 | **unveraendert** |
| Abschnitte Bahn 4 | **14** | **16** |

Der 51-Wurf-Block auf Bahn 4 zerfaellt in 20 Wuerfe Warmwerfen plus die
Saetze -- dasselbe Muster wie auf den anderen drei Bahnen. Alle vier Bahnen
stehen jetzt auf 16 Abschnitten mit 12 Saetzen.

**Schalter:** `scoring.game_reset_number_only` (an).
**Tests:** `test_game_reset.py::TestNurDieWurfnummer`, mit Gegenprobe.

**Offen:** Die Wurfnummernketten bleiben bei 46 von 48 sauber -- die
Fehlerstelle wandert nur (jetzt Bahn 4 Spiel 3 mit 29 Wuerfen). Die neue
Trennstelle sitzt um einen Wurf verschoben.

### Gemessener Ist-Stand der Erkennung (2026-09-02)

Zur Einordnung, weil der Eindruck taeuschen kann:

| Was | Guete |
|---|---|
| Lampen gegen Tafel-Ziffer | 7 von 1621 abweichend (**99,57 %**) |
| Wurfnummer lesbar | **100 %** auf allen vier Bahnen |
| Kegelzahl-Ziffer lesbar | 90,6 bis 99,5 % |
| Summe (total_b) im Wurffenster | 0,0 bis 97,6 % -- **Zeitpunktproblem** |

Die Summe wird im Wurffenster abgegriffen, also genau waehrend sie sich
aendert; der Aggregator (`min_digit_agreement` 0,5) findet dann keine Mehrheit.
Ein besseres Erkennungsverfahren wuerde daran nichts aendern -- gelernte
Ziffern-Templates zielen an diesem Problem vorbei. Der naheliegende naechste
Schritt waere, die Summe zu lesen, WAEHREND sie stillsteht (kurz vor dem
naechsten Gruen-AN), nicht im Wurffenster.

## GUI-Umbau und Wurfbelege (2026-09-03)

### Die gefuehrte Kalibrierung nutzte noch die alten Rahmen

Der ROI-Umbau vom Vortag steckte nur in `1Spieltag_enge_lampen.json`, nicht in
der Vorlage -- jedes NEUE Video waere wieder mit weiten Rahmen gestartet. Beim
Nachziehen zeigte sich, dass auch die Positionen nicht stimmten: Die Vorlage
stammte aus einer Handkalibrierung und lag bis zu 0,011 zu hoch, was beim
halbierten Rahmen fast ein Drittel der Hoehe ist. Jetzt gemessen und
symmetrisch (`session.py`, `_default_rois`).

### GUI aufgeraeumt (vom Nutzer beauftragt)

Entfernt: "Bahn N kalibrieren", "Bereiche anklicken (14)", "nur Raute",
"Ziffern einzeln einrahmen (8)" samt Feldauswahl, der Debug-Kasten und der
Reiter "Debug / Events" -- dazu fuenf damit tote Methoden und sieben verwaiste
Importe. Alle entfernten Knoepfe setzten Rahmen NEU; seit der gefuehrten
Kalibrierung ist das ueberfluessig, weil jeder Rahmen mit der Maus ziehbar ist.

"Kalibrierung pruefen" ist von "Live-Analyse" nach "Kalibrierung" gewandert --
der Knopf sagt etwas ueber die Kalibrierung, nicht ueber die Analyse.

**Neu, weil der Debug-Reiter fiel:** `StatusLogHandler` zeigt Warnungen und
Fehler in der Statusleiste. Ohne ihn waeren Meldungen wie "passt die
Kalibrierung zu diesem Video?" unsichtbar geworden.

**Neu:** Die Aufloesung steht jetzt als farbige Zeile unter dem Videonamen --
gruen, wenn sie zur geladenen Kalibrierung passt, rot wenn nicht. Einem Stream
sieht man an der Adresse nicht an, welche Fassung dahinterliegt.

### Wurfbelege (Nutzeridee)

Je Wurf ein Bild: entzerrte Tafel mit allen Rahmen, darueber Zeitpunkt und
Herkunft, darunter die gemessenen Werte samt Pruefungen. Eingefaerbt nach
Verlaesslichkeit -- gruen wenn Lampen und Tafelziffer einig sind, rot beim
Widerspruch.

| | je Bild | Spieltag (1695 Wuerfe) |
|---|---|---|
| PNG, Faktor 3 | 1,6 MB | 2,7 GB |
| JPEG q85, Faktor 3 | 295 KB | 0,51 GB |
| **JPEG q85, Faktor 2** | **93 KB** | **0,16 GB** |

Standard AUS (`debug.throw_sheet`). `throw_sheet_only_flagged` legt nur ab, was
auffaellig ist -- Status ungleich VALID oder Lampen und Tafel uneins.

**Neue Dateien:** `debug/board_render.py` (gemeinsame Zeichenlogik fuer Werkzeug
und Beleg), `debug/throw_sheet.py`, `sinks/storage.py`,
`tools/upload_throw_sheets.py`. Tests: `tests/unit/test_throw_sheet.py`.

**Supabase:** Bilder gehen in den STORAGE, nicht als `bytea` in die Tabelle --
dort steht nur der Pfad. Der Upload laeuft NACH dem Lauf, nicht waehrend: Ein
Netzproblem darf die Analyse nicht ausbremsen, und die Belege liegen ohnehin
schon auf der Platte. `--probelauf` ist die Vorgabe fuer den ersten Versuch.

**Noch nicht geschehen:** Es wurde nichts hochgeladen. Dafuer braucht es einen
Bucket, die beiden Umgebungsvariablen und die Freigabe des Nutzers.

## Stand 2026-09-03: 720 von 720 gegen das Wurfprotokoll

`lauf_2026-09-03_11-14-04`. Erstmals in dieser Sitzung wurde gegen die
BODENWAHRHEIT gemessen statt gegen Zwischenkennzahlen -- und das haette frueher
geschehen muessen.

| | weiter ROI | enger ROI | mit drei Aenderungen |
|---|---|---|---|
| **Protokoll** | 720/720 | 719/720 | **720/720** |
| Ziffer weicht ab | 8 von 1621 | 7 von 1621 | **5 von 1620** |
| UNKNOWN Bahn 4 | 6,73 % | 0,50 % | **0,17 %** |

### Die drei Aenderungen

1. **Schwellen mittig statt am Wolkenrand** (`baseline_*_fraction` 0,53/0,61)
2. **Beide Wolken mitfuehren** (`adaptive_on_level`) -- die AN-Seite war bisher
   eine Annahme (255), gemessen liegt sie je Bahn bei 243 bis 253
3. **Verdeckungsschwelle ins Tal** (`occlusion_score` 2,0 -> 12,0)

Alle drei hatten denselben Fehler: Schwelle am RAND einer Wolke statt in der
Luecke dazwischen.

### Methodisch festgehalten

* `tools/compare_protocol.py` nimmt jetzt eine `wuerfe.csv` und ein waehlbares
  Protokoll. **Vor jeder Bewertung einer Aenderung laufen lassen.**
* Die Blockprobe (je Spielerblock die beste Fundstelle) ist noetig, weil das
  Protokoll je Bahn zwei Saetze mit je drei Spielern listet -- diese Bloecke
  liegen im Video verstreut. Eine Ausrichtung ueber die ganze Bahn erzeugt 82
  Scheinfehler.
* **Keine Personenerkennung noetig:** Der Gruenscore verraet die Verdeckung
  selbst. Eine ausgeschaltete Lampe kann nicht auf null fallen (beiges
  Gehaeuse), echtes AUS liegt bei 20-30.

### Offen

* **Fuenf Ziffer-Abweichungen.** Vom Nutzer an Videoclips geprueft: In allen
  Faellen haben die LAMPEN recht, die Ziffernerkennung liest falsch. Fuenf
  uebersehene Segmente (8->2, 9->7, 8->0), einer war eine erfundene Ziffer bei
  dunkler Anzeige -- der ist mit der Verdeckungsschwelle behoben.
  Das ist der Ort fuer gelernte Ziffern-Templates.
* Die Ziffern-Fehlerarten sind systematisch: Es fallen Segmente WEG, es werden
  keine erfunden (ausser bei dunkler Anzeige).

## Stand 2026-09-03 (Abend): Vollauf mit Nullwurf-Filtern, elf Nullwuerfe einzeln gesichtet

`lauf_2026-09-03_16-51-04`, ganzer Spieltag: 1701 Gruenzyklen, 1686 Wuerfe,
1679 VALID / 7 EMPTY, **11 Nullwuerfe**. Jeder einzeln als GIF an den Nutzer
geschickt und bewertet -- drei verschiedene Ursachen, keine einzige Regel
passt auf alle:

| Ursache | Faelle | Status |
|---|---|---|
| Echter Fehlwurf (Fehlwurfzaehler + Ziffer 0) | 3 | korrekt, kein Fix noetig |
| Verdeckung mitten im Sammelfenster | 3 | **BUG-017**, behoben |
| Warmwerf-Sperrzyklus als "Wurf 21" | 4 | **BUG-018**, behoben |
| Wurfnummer-Fehllesung bei echtem Leerwurf (60 statt 30) | 1 | noch offen |

**Wichtige Korrektur:** `discard_zero_throw_number` (Wurfnummer==000, aus dem
vorigen Zwischenstand) hat im GANZEN Lauf kein einziges Mal gegriffen -- die
vier Faelle, die sie beheben sollte, hatten gemessen `throw_number=21`, nicht
`000`. Lehre: Eine Regel, die an einer Theorie statt am tatsaechlichen
Vollauf gemessen wird, kann wirkungslos sein, ohne dass das auffaellt (vier
Zeilen im Log haetten es gezeigt, wurden aber nicht geprueft, bevor der
Nutzer die GIFs ansah).

**Trennung von BUG-017 und BUG-018 gelang erst durch Messung** (Nutzervorschlag:
"faellt der Gruenscore in einem Frame wirklich auf 0?"). Neues Werkzeug
`tools/messe_gruenscore_um_frame.py` zieht den rohen Score frameweise. Ergebnis
glasklar: Verdeckung faellt auf exakt 0.00, der Sperrzyklus nie unter 17.

**Neue Werkzeuge:** `tools/export_alle_nullwuerfe.py` (extrahiert alle
Nullwuerfe einer `wuerfe.csv` und exportiert sie automatisch als GIF-Serie),
`tools/messe_gruenscore_um_frame.py`.

**Offen:** Bug #3 (Wurfnummer-Fehllesung bei Fehlwurf) noch nicht behoben --
`_wurfnummer_lesen()` liest fuer Fehlwurf-Ereignisse NUR einen einzelnen
Frame, ohne die 10-Frame-Aggregation der normalen Gruenzyklus-Pfade. Wirkung
in diesem Fall gering (nur die Wurfnummer-Beschriftung verschiebt sich
kosmetisch, Summe/Anzahl je Satz bleiben korrekt), aber noch nicht als
BugSkill dokumentiert.

## Stand 2026-09-03 (21:47): Bestaetigungslauf VOLLSTAENDIG durchgelaufen

`lauf_2026-09-03_20-21-33`, ganzer Spieltag, 85,6 min, 312784 Frames:
1685 Wuerfe, 1701 Gruenzyklen. Mit BUG-017, BUG-018 und BUG-019 im Code.

**BUG-019 wirkt -- der wichtigste Fix des Tages:**

| | vorher | jetzt |
|---|---|---|
| Saetze, die nicht bei Wurf 1 beginnen | 5 von 64 | **2 von 64** |
| davon Bahn 4 (31-60, 61-90, 31-60) | 3 | **0** |
| Nullwuerfe | 11 | 10 |

**Der vom Nutzer gemeldete Fall ist behoben:** Bahn 4 F202870 stand vorher als
"Wurf 60" in der Tabelle, jetzt als **Wurf 30** -- genau die Nummer, die der
Nutzer beim Sichten der GIFs genannt hatte. Bestaetigt zugleich die Diagnose:
Nicht die Ziffernerkennung war schuld, sondern die verschobene Kette.

Die verbleibenden zwei ("Bahn 2 Spiel 2: 2-20", "Bahn 5 Spiel 2: 2-21") sind
ein ANDERER Fall: Dort fehlt der erste Wurf am Anfang, es wird nicht die
alte Kette fortgezaehlt. Noch nicht untersucht.

**BUG-017 wirkt nur zur Haelfte, BUG-018 gar nicht** (und wurde am
2026-09-04 zurueckgebaut).** Details stehen als
NACHTRAG in den jeweiligen BugSkills. Kurzfassung:

* **BUG-017:** F16256 wird gefangen (Verdeckung liegt IM Fenster), F15569
  nicht (Verdeckung liegt VOR dem Fenster -- das GREEN_OFF loeste erst aus,
  als die Tafel wieder sichtbar war). Fehlt: ein GREEN_OFF kurz NACH einer
  Verdeckung ist ebenfalls verdaechtig. Braucht einen gemessenen Schwellwert
  (wie viele Frames?), deshalb nicht ins Blaue gefixt.
* **BUG-018:** greift nicht, weil der Filter `throw_number is not None`
  verlangt -- die rohe Wurfnummer war bei F126593 NICHT lesbar, die 21 kam
  erst aus dem Fallback.

**Die Lehre, zum zweiten Mal an einem Tag:** Beide Fehldiagnosen stuetzten
sich auf die Spalte `Wurfnummer` der `wuerfe.csv` -- die zeigt aber die
AUFGELOESTE Nummer, nicht die Rohlesung der Tafel. Solange die Rohlesung
nirgends sichtbar ist, laesst sich ueber sie nichts belegen.

**Bereits umgesetzt (2026-09-03 21:30):** Die `wuerfe.csv` hat ab dem
naechsten Lauf zwei neue Spalten -- **`WurfnummerRoh`** (Lesung der Tafel VOR
`_resolve_throw_number`) und **`NummerEinigkeit`**. Der Lauf von 20:21 hat
sie noch nicht, weil Python den Code beim Start laedt.

### Agenda fuer den naechsten Termin (in dieser Reihenfolge)

1. **Erst messen, dann fixen:** Einen Lauf ueber die belegten Stellen mit den
   neuen Spalten fahren und nachsehen, was die Tafel bei den vier
   Sperrzyklen (F126593, F218448, F218644, F220170) und bei F15569 WIRKLICH
   zeigte. Alles Weitere haengt daran.
2. **BUG-018 neu angehen** (der Fix wurde am 2026-09-04 ZURUECKGEBAUT):
   Er griff nie UND haette Wurf 21 jedes regulaeren Satzes mitgefangen --
   `wurfnummer_vorher == 20` trifft auch mitten in einem 30er-Satz zu. Ein
   neuer Versuch braucht ein Merkmal, das Warmwerfen WIRKLICH von einem Satz
   unterscheidet; das kennt der Analyzer heute nicht. Erst Schritt 1.
3. **BUG-017 nachbessern:** GREEN_OFF kurz NACH einer Verdeckung ebenfalls
   als verdaechtig behandeln -- Schwellwert (wie viele Frames?) messen.
4. **Offen geblieben:** "Bahn 2 Spiel 2: 2-20" und "Bahn 5 Spiel 2: 2-21" --
   dort fehlt der ERSTE Wurf, das ist ein anderer Mechanismus als BUG-019
   und noch nicht untersucht.
5. **Q15:** Fehlwurf-Pfad liest die Wurfnummer aus einem einzigen Frame.


## Rueckbau 2026-09-04: was von den drei Fixes bleibt

Auf die Frage "bauen wir die Bugfixes zurueck, die nicht getragen haben?"
wurden alle drei an den Zahlen des Vollaufs geprueft:

| Fix | Treffer | VALID-Wuerfe | Entscheidung |
|---|---|---|---|
| BUG-019 (Kette nach Spielwechsel) | 3 Saetze gerettet | 1679 -> 1679 | **bleibt** |
| BUG-017 (Verdeckung im Fenster) | 1 von 3 Faellen | 1679 -> 1679 | **bleibt** |
| BUG-018 (Warmwerf-Sperrzyklus) | 0 | -- | **zurueckgebaut** |

Entscheidend fuer BUG-017: EMPTY ging von 7 auf 6, VALID blieb bei 1679 --
der Filter hat genau einen falschen Wurf entfernt und keinen einzigen
gueltigen gekostet. Unvollstaendig ist nicht dasselbe wie wirkungslos.

Entscheidend gegen BUG-018: Beim Pruefen kam heraus, dass er nicht nur
wirkungslos war, sondern Wurf 21 JEDES Satzes mitgefangen haette (ein
30er-Satz durchlaeuft `wurfnummer_vorher == 20` ebenso). Dass nichts
passierte, lag allein daran, dass er nie lief.

**Entfernt:** `scoring.discard_warmup_lock_cycle`, `scoring.warmup_throws`,
der Filterblock in `throw_analyzer.analyze()`, die Log-Verzweigung und
`TestWarmwerfSperrzyklus`. Die Diagnose lebt im BugSkill weiter.

**Noch im Code, aber ohne Treffer:** `discard_zero_throw_number` (Wurfnummer
000). Sie bildet eine ausdrueckliche Nutzeraussage ueber die Anlage ab ("es
gibt keinerlei Wuerfe bei 000"), ist eng gefasst und birgt keine
Verwechslungsgefahr -- deshalb stehen geblieben. Ihr Messbeleg fehlt aber
weiterhin.

## 2026-09-04: BUG-020 -- warum `discard_zero_throw_number` nie greifen konnte

Der Nutzer fragte: "du hast gesagt, wir erkennen die Wurfnummer zu 100% ...
dann muesste discard_zero_throw_number eindeutig alle 21. Wuerfe einkassieren,
weil da ja immer schon 000 steht, oder etwa nicht?"

Er hatte recht. GEMESSEN an den zehn echten Sample-Frames von F126593:

    alle zehn lasen '0','0','0'          -> Einigkeit 1,00
    Scores der fuehrenden Stellen 0,35   -> unter min_confidence 0,5

Die Anzeige zeigte 000. Die Regel sah es nie, weil `TemporalAggregator.add()`
jede Stimme unter `min_confidence` verwirft und `result()` daraufhin das ganze
Feld auf None setzt. Und selbst dann haette die Schwelle
`throw_number_min_confidence: 0.9` blockiert -- denn die gelieferte Zahl ist
die BILDGUETE der schwaechsten Stelle (0,35), nicht die zeitliche Einigkeit
(1,00). Beides hiess "confidence".

**Behoben:** `FieldAggregator.mehrheit()` liefert den zeitlichen
Mehrheitswert und die Einigkeit, ohne Confidence-Schwelle. Neue
Konfiguration: `throw_number_min_agreement: 0.9`,
`throw_number_ignore_leading: 1` (es gibt keinen hundertsten Wurf --
Nutzerangabe). `result()` bleibt unveraendert, kein bestehender Filter
aendert sein Verhalten.

**Gegenprobe auf Nutzerhinweis** (koennten 003/008/009 als 000 durchgehen?):
24 echte Wuerfe mit Nummer 3, 8, 9 ueber alle vier Bahnen gemessen --
**0 von 24** wuerden als 0 gelesen.

**Nebenbefund, wichtig:** Die Ziffernerkennung der Wurfnummer liegt bei rund
einem Viertel dieser Wuerfe daneben (3->4, 8->9, 8->2, 9->8, 9->"30",
9->"10"). Nie in Richtung 0, deshalb ungefaehrlich fuer diese Regel -- aber
die Annahme "die Wurfnummer wird zu 100 % erkannt" gilt so nicht und sollte
nirgends mehr als Begruendung dienen.

**Neues Werkzeug:** `tools/ziffern_verlauf.py` legt einen Kontaktbogen an --
je Frame der Tafelausschnitt mit den gelesenen Feldern, das Messfenster
hervorgehoben. Damit ist eine Ziffernfrage in Minuten zu klaeren statt zu
vermuten. Dazu `debug.save_digit_rois` (Standard aus), das die Ziffern-ROIs
mit in die Debug-Ausgabe legt.

**Noch offen:** Ein Vollauf mit dieser Aenderung steht aus. Erwartung: Die
vier Sperrzyklen (BUG-018) verschwinden, ohne dass echte Wuerfe verloren
gehen.


## 2026-09-04 (Nachmittag): BUG-020 belegt -- die vier Sperrzyklen sind weg

Teillauf F110000-230000 (enthaelt alle vier Sperrzyklen), zweimal gefahren.

| | vorher | Regel vorn | Regel hinten |
|---|---|---|---|
| Wuerfe | 710 | 706 | **706** |
| davon 0 Kegel | 6 | 2 | **2** |
| Kegel gesamt | 4923 | 4923 | **4923** |

Alle vier Sperrzyklen (F126593, F218448, F218644, F220170) werden verworfen,
jeweils mit 100 % Einigkeit auf Wurfnummer UND Summe. Die Kegelsumme bleibt
identisch -- es ging nichts verloren, was Kegel trug. Die zwei verbliebenen
Nullwuerfe sind beide echte Fehlwuerfe ueber den Fehlwurfzaehler.

**Der Pruefstein des Nutzers erfuellt** ("Warmwerfen ist immer exakt 20"):

    Bahn 2: [2, 20, 30, 30, 30, 30, 20, 15]
    Bahn 3: [1, 20, 30, 30, 30, 30, 20, 16]
    Bahn 4: [1, 20, 30, 30, 30, 30, 20, 16]
    Bahn 5: [20, 30, 30, 30, 30, 20, 15]

(Die Raender 1, 2, 15, 16 sind angeschnittene Bloecke des Teillaufs.)

**Zwischenfall, der dabei auffiel:** Die Regel stand zunaechst VOR
`_resolve_throw_number` und verschluckte damit den Spielwechsel -- auf Bahn 4
wuchsen zwei Saetze zu einem 60er zusammen. Behoben durch Verschieben hinter
die Aufloesung (siehe BUG-020-Nachtrag). Kein Unit-Test hatte das erfasst;
sichtbar wurde es nur an der Abschnittslaenge.

**Noch offen:** Ein VOLLAUF ueber den ganzen Spieltag steht aus. Die erste
Haelfte (F0-110000) ist ungeprueft -- dort liegen die Verdeckungsfaelle
BUG-017 (F15569 noch offen) und die Bahn-2/5-Bloecke, die nicht bei Wurf 1
beginnen.


## Unterprojekt: Liveticker (2026-09-07)

Liegt in `apps/liveticker/`, eigene Dokumentation in dessen `README.md`.
Reine Browser-Anwendung, kein Backend, keine Bibliotheken, kein Bauschritt.
`start.py` erzeugt nur die Vorbelegung und liefert das Verzeichnis ueber
`localhost` aus -- ueber `file://` verweigert der Browser sowohl die Abfrage an
Supabase als auch das Schreiben in einen Ordner.

**Die Arbeitsteilung ist der Kern.** `throws` enthaelt bewusst nur Gemessenes
(Bahn, Anzahl, welche Kegel, Zeitpunkt). Wurfnummer, Gesamtsumme und
Fehlwurfzahl entstehen erst im Ticker -- auf der Seite, die die Spielregeln
kennt. Das ist dieselbe Festlegung wie am 2026-08-26, jetzt zum ersten Mal auch
auf der lesenden Seite eingeloest.

| Groesse | Herkunft |
|---|---|
| gefallene Kegel, Bahn, Zeitpunkt | gemessen, aus der Datenbank |
| Wurfnummer | gezaehlt ab der Startmarke des Abschnitts |
| Gesamtsumme, Schnitt | gerechnet ueber den Abschnitt |
| Fehlwurf | abgeleitet: `pins_count == 0` |
| stehende Kegel | abgeleitet: Gegenmenge der gefallenen |

**Start/Stopp je Bahn, nicht global** -- P6 (Bahnen sind unabhaengig) gilt auch
hier: Das Warmwerfen endet nicht auf allen Bahnen gleichzeitig. Wuerfe
ausserhalb eines Abschnitts werden gezeigt und in die CSV geschrieben, aber
nicht gezaehlt. Ein zweites Start oeffnet einen neuen Abschnitt ab Wurfnummer 1.

**Nachgelesen wird nach `id`, nicht nach Zeitstempel.** Gepufferte Wuerfe aus
`debug/versand_puffer.jsonl` kommen mit alten Zeitstempeln, aber neuen ids an --
nach Zeit zu lesen wuerde sie ueberspringen. Einsortiert werden sie danach
trotzdem nach Zeitpunkt.

**Getestet:** `node --test apps/liveticker/test/ticker.test.js` -- 19 Tests auf
der reinen Ableitungslogik (`ticker.js`, ohne DOM und ohne Netz). Am echten
Bestand gegengeprueft: Bahn 2 mit 425 Wuerfen, Summe 2728, 6 Fehlwuerfe.

**Offen:** Der Ordner fuer die CSV muss nach einem Neuladen erneut gewaehlt
werden (Browser-Vorgabe). Die Abschnittsmarken ueberstehen es dagegen.

**Nachtrag 2026-09-07 -- eine Datei zum Veroeffentlichen.** `build.py` legt
`index.html`, `styles.css` und die drei Module zu einer Datei zusammen
(`dist/index.html`, ~44 KB, keine externen Verweise). Die Modultrennung bleibt
die Quelle: `ticker.js` traegt die Ableitungslogik und wird einzeln geprueft,
ein Buendel liesse sich so nicht messen. `build.py` prueft vorab auf doppelte
Namen auf oberster Ebene -- beim blossen Verketten wuerde sonst still das eine
das andere ueberschreiben.

**Damit verbunden: die lesende Seite bekommt einen eigenen Schluessel.**
`SUPABASE_READ_KEY` hat in `start.py` und `build.py` Vorrang vor
`SUPABASE_KEY`; beide verweigern einen Schluessel, der nach `sb_secret_` oder
`service_role` aussieht. Hintergrund: Sobald `throws` per RLS auf Lesen
beschraenkt wird, braucht die Bilderkennung zum Schreiben den geheimen
Schluessel -- sie laeuft lokal und ist kein Browser, dort gehoert er hin. Die
noetigen Schritte stehen in `apps/liveticker/README.md`.

**UEBERHOLT** (Stand dieses Absatzes: "noch nicht ausgefuehrt"). Am 2026-09-11
gegen die Produktivdatenbank gemessen: Der oeffentliche Schluessel darf lesen
und sonst nichts -- INSERT, UPDATE und DELETE enden mit HTTP 401 `42501`.
Siehe den Abschnitt "Geklaert: der oeffentliche Schluessel darf nur lesen" am
Ende dieses Dokuments.


## 2026-09-07: Ein Lauf ohne eine einzige erkannte Lampe (BUG-021)

Ein Testlauf unter realen Bedingungen buchte 67 Wuerfe auf allen vier Bahnen
als "0 Kegel" und schickte sie so an die Datenbank. **Ursache war eine alte
Kalibrierung** (`1Spieltag.json`, Stand 1. September) mit Lampen-ROIs im
doppelten Zuschnitt: 0,080 x 0,075 statt 0,040 x 0,0375.

GEMESSEN, und die Kette ist lueckenlos:

| | 04.09. (lief) | 07.09. (defekt) |
|---|---|---|
| Ausschnitt je Lampe | 8 x 7 px | 12 x 11 px |
| Grundlinie | ~140 | ~140 |
| leuchtende Lampe | 250 | 203 |
| AN-Schwelle | 210 | 206 |
| erkannte Lampenzustaende | 194 972 | 0 |

Der Detektor mittelt ueber den Ausschnitt (`core_percentile: 0`); der dunkle
Ring um die Lampe zieht den Mittelwert unter die Schwelle. Der Wertebereich war
an BEIDEN Enden gestaucht (min 107,6 statt 0,0) -- daran war es zu erkennen.

**Die Ziffernerkennung war die ganze Zeit korrekt** und hat den Fehler
angezeigt: "Lampen zeigen 0, Anzeige 9". Es hat nur niemand ausgewertet.

### Was daraus gebaut wurde

`src/kegel_cv/analysis/lamp_watchdog.py` -- zaehlt je Bahn, wie oft Lampen und
Anzeigetafel einander widersprechen (Lampen null, Anzeige groesser null), und
meldet ab `detection.lamps.silent_failure_after` (Vorgabe 5) einmal je Bahn
als ERROR. Reine Logik, ohne I/O, in `test_lamp_watchdog.py` gemessen.

Am echten Material gegengeprueft: Im defekten Lauf Alarm auf allen vier Bahnen,
der erste nach 16 von 67 Wuerfen -- also rund zwei Minuten nach dem Start statt
erst beim Auswerten. In den beiden gesunden Laeufen (2383 Wuerfe zusammen)
bleibt er still.

Dazu behoben: Beim SPRUNG an die Startposition meldete `_vorspulen` einmal
`0` und danach bis zum Ende nichts mehr -- die Oberflaeche zeigte durchgehend
"0 %", was bei einem Stream ueber Netz wie ein Absturz aussieht. Jetzt sagt sie
"springt zu Frame N ..." und am Ende "fertig" (`SPRUNG_LAEUFT`).

### Offen geblieben

**Die Kopplung zwischen `core_percentile` und der ROI-Groesse ist weiterhin nur
ein Kommentar in `config/default.yaml`.** `core_percentile: 0` (Mittelwert)
setzt enge ROIs voraus; mit dem alten Zuschnitt muesste er auf 70. Nichts
prueft beim Laden einer Kalibrierung, ob beides zusammenpasst. Der Wachhund
faengt die Folge, nicht die Ursache.


## 2026-09-07: Das Bild flackerte waehrend der Analyse (BUG-022)

Der Nutzer meldete, das Videobild springe waehrend eines Laufs zwischen
verschiedenen Frames. Aus seiner Bildschirmaufnahme GEMESSEN: Auf einem
Standbild standen gleichzeitig `Frame 2898` (Overlay, Analyse) und
`Frame 2240` (Statusleiste, Player). Ueber mehrere Bilder liefen zwei Reihen
abwechselnd, beide fortschreitend -- die Analyse (2880 ... 2949) und der Player
rund 650 Frames dahinter (2230, 2234, 2282).

Ursache: `_start_analysis` ruft `player.pause()`, aber `pause()` haelt nur den
Anzeige-Timer an und sperrt nichts. Ein Druck auf Play oder die Leertaste
startete die Wiedergabe wieder, und ab da schrieben `_on_frame` und
`_on_preview` abwechselnd in dasselbe `video_view`.

Behoben an drei Stellen: `_on_frame` verwirft Player-Frames waehrend der
Analyse, `_update_controls` sperrt Transport und Schieber, `keyPressEvent`
sperrt Leertaste und Pfeiltasten (gesperrte Knoepfe halten keine Taste auf).
Dazu ein eigenes Kennzeichen `_analyse_aktiv` -- `self._worker` wird nach dem
Lauf nie zurueckgesetzt und taugt nicht als Zustand.

12 Regressionstests am ECHTEN Hauptfenster (offscreen). Gegenprobe: Ohne die
Sperren fallen vier davon.

### Offen geblieben

**Player und Worker oeffnen je eine eigene Stream-Verbindung.** Im Log stehen
zwei `Stream geoeffnet`-Zeilen, 20 Sekunden auseinander. Der Lesefaden des
Players laeuft waehrend der Analyse weiter (so gewollt, damit ein Livestream
nicht weglaeuft) -- bei einer AUFZEICHNUNG ist das aber nur doppelte Last auf
derselben Leitung und ein moeglicher Grund dafuer, dass der Nutzer den Stream
als traege empfindet. Ungemessen; vor einer Aenderung gehoert das gemessen.


## Liveticker: Abraeumen und Korrekturen (2026-09-07)

**Die Bildfuehrung ist neu und faellt nicht vom Himmel.** Ab Wurf 16 wird ins
stehende Bild geworfen; die Datenbank kennt aber nur die GEFALLENEN Kegel, nie
die vorher stehenden. Der Ticker schreibt das Bild deshalb ueber die Wuerfe
hinweg fort -- die einzige Stelle im Projekt, an der ein Fehler sich ueber
viele Wuerfe verschleppen kann. Sie liegt darum in `ticker.js` (rein, ohne DOM
und Netz) und ist mit 20 Tests belegt.

**Fachregeln, die der Nutzer am 2026-09-07 festgelegt hat** und die in keiner
anderen Unterlage stehen -- auch nicht im Skill `kegel-domain`:

| Regel | |
|---|---|
| Rhythmus | Wurf 1-15 Vollen, 16-30 Abraeumen, dann von vorn |
| Neu aufgestellt | wenn NICHTS mehr steht -- **und ebenso, wenn nur noch der Koenig (5) steht** |
| Umschalten | je Bahn von Hand, gilt ab dem naechsten Wurf |
| Widerspruch | faellt ein Kegel, der laut Bild nicht mehr stand: markieren und Bild zuruecksetzen |

Die Koenigsregel folgt NICHT aus der ersten. Sie ist der Grund, warum hier
gefragt statt geraten wurde.

**Korrekturen aendern die Datenbank nicht.** Der Nutzer kann je Wurf angeben,
welche Kegel wirklich fielen; das wirkt auf Anzeige, Kennzahlen und das
weitergefuehrte Bild -- und die CSV traegt BEIDES nebeneinander (`Wert` /
`Gemessen Wert`, `Gefallene Kegel` / `Gemessene Kegel`, `Korrigiert`,
`Bemerkung`). Ohne diese Trennung waere spaeter nicht mehr zu sehen, wo ein
Mensch eingegriffen hat -- und genau das ist die interessante Stelle, wenn die
Erkennung verbessert werden soll.

**Am echten Bestand gegengeprueft** (543 Wuerfe Bahn 2): 45 Zeilen mit
Restbild, in allen stimmt gefallen + steht + lag_schon = 9. Korrektur an einem
Wurf uebernommen, Wert 1 -> 2, Marke gesetzt, im Speicher abgelegt.

**Auffaellig:** In diesem Testlauf trugen 78 von 543 Zeilen die
Widerspruchsmarke. Das ist ein Artefakt der Pruefung -- die Startmarke lag
willkuerlich weit in der Vergangenheit, die Wurfnummern passen deshalb nicht zu
echten Spielgrenzen. Im Betrieb ist eine Haeufung das Zeichen, dass die Phase
verschoben ist und von Hand nachgestellt werden muss.


## Tafelbild je Wurf (2026-09-07)

Jeder Wurf bringt jetzt den Ausschnitt der Anzeigetafel mit, aus dem sein
Ergebnis stammt. Damit erklaert sich ein Ergebnis nicht nur ueber Zahlen (P1),
sondern ueber das Bild -- und im Liveticker sieht der Nutzer beim Korrigieren,
worueber er entscheidet.

| Wurfart | Bildquelle |
|---|---|
| Gruenzyklus | der GREEN_OFF-Frame -- derselbe, aus dem das Ergebnis stammt |
| Nullwurf | der Frame, bei dem der Fehlwurfzaehler gesprungen ist |

**Der zweite Fall war zunaechst als Luecke eingeschaetzt** ("kein Gruenzyklus,
also kein Bild"). Der Nutzer hat widersprochen, und er hatte recht:
`_pruefe_fehlwurfzaehler(frame)` bekommt den ganzen Frame, `lane_box()` liegt
in derselben Klasse. Aus einer halben Tagesarbeit wurden ein paar Zeilen. Die
Lehre: "kein Ereignis" heisst nicht "kein Frame".

**Uebertragen wird NUR die eingemessene Tafel** (`lane_box`), nichts aus der
Halle -- Festlegung des Nutzers. GEMESSEN am Ausschnitt eines echten Wurfs
(152x154 px): JPEG 40 -> 4,8 KB, 55 -> 5,5 KB, 70 -> 6,7 KB, PNG -> 46,4 KB.
Bei 2000 Wuerfen je Spieltag also rund 9 MB.

**Als Base64 in derselben Zeile, nicht in einem Speicher-Dienst.** Begruendung:
Warteschlange, Wiederholversuche und Nachlieferung nach Netzausfall arbeiten
auf Zeilen. Ein Bucket waere ein zweiter Uebertragungsweg mit einem zweiten
Fehlermodus -- ausgerechnet dann, wenn das Netz wackelt. Der Ticker holt die
Spalte nur fuer den angeklickten Wurf; die Liveliste laedt sie nicht mit.

**Noetig in der Datenbank:**
`alter table throws add column if not exists board_jpeg text;`
Fehlt sie, lehnt PostgREST den Insert ab und alles landet im Puffer.

Abschaltbar ueber `output.send_board_image`, Qualitaet ueber
`output.board_image_quality` (Vorgabe 40).

16 Tests in `test_board_image.py`. Der Fehlerweg ist mitgeprueft: Fehlt die
Spalte, meldet der Ticker "Kein Tafelbild zu diesem Wurf" statt zu scheitern
(HTTP 400 im Netzprotokoll, Dialog bleibt bedienbar).


## Zwei Tafelbilder je Wurf, und der Blink-Fund (2026-09-07)

**Der Nutzer meldete leere Bilder bei Achten und Neunern.** GEMESSEN an den
zehn gespeicherten Frames eines Neuners (Bahn 1, Ereignis 7, Wurf 20): FUENF
davon sind voellig dunkel, waehrend das untere Display durchgehend
`020 9 0129` zeigt. Die Anlage laesst die Kegellampen nach einem hohen
Ergebnis blinken. Wer stur den Ausloeser-Frame nimmt, greift mit etwa halber
Wahrscheinlichkeit daneben.

**Kein Mischbild.** Genommen wird der Frame, in dem die Lampen insgesamt am
hellsten sind -- ein echtes Bild statt einer Montage. Eine Montage zeigte
einen Zustand, den es so nie gab; bei einer Erkennung, die genau von solchen
Bildern lebt, waere das ein schlechter Tausch.

Zwei Fallen dabei umgangen:
- **Der Detektor wird NICHT zusaetzlich aufgerufen.** Er fuehrt ein lernendes
  Gedaechtnis (Grundlinie, AN-Niveau); Extra-Aufrufe haetten die Messung selbst
  verfaelscht. `lamp_brightness` liest die Lampen-ROIs roh.
- **Kein neuer Schwellwert.** Es wird nichts als "an" oder "aus" eingestuft,
  sondern nur eine Rangfolge zwischen Frames gebildet (P5).

**Das zweite Bild** ist der letzte Frame, solange Gruen noch an war -- das
Bild, vor dem der Spieler stand. Roh gemerkt (alle `live_preview_interval`
Frames) und erst bei GREEN_OFF kodiert; ein JPEG je Frame und Bahn waere
Verschwendung. Beim Abraeumen ist es die Angabe, die aus den gefallenen Kegeln
allein nicht zu rekonstruieren waere.

**Noetig in der Datenbank -- BEIDE Spalten:**

    alter table throws add column if not exists board_jpeg text;
    alter table throws add column if not exists board_before_jpeg text;

**Zwischenfall dabei:** Die zweite Spalte wurde in den Versand aufgenommen,
bevor sie in der Tabelle existierte. PostgREST lehnte jede Zeile ab
(`PGRST204`), sieben Wuerfe landeten im Puffer und wurden beim naechsten Start
nachgeliefert -- verloren ging nichts. Lehre: Eine neue Spalte im Payload ist
eine Schemaaenderung und gehoert VOR den Lauf, nicht in ihn hinein.

Im Ticker fragt `fetchBoardImage` beide Spalten an und faellt bei einem Fehler
auf `board_jpeg` allein zurueck. Ohne diesen Rueckfall waere an einer Tabelle
ohne die neuere Spalte auch das vorhandene Bild verschwunden -- PostgREST
lehnt die GANZE Abfrage ab, wenn eine Spalte fehlt.

---

## Stand 2026-09-10: YouTube als Quelle, Kalibrierung ohne Handarbeit

### YouTube-Adressen gehen direkt an das Werkzeug

Eine YouTube-Adresse ist eine **Webseite, kein Video**. Gemessen:

```
Link direkt an OpenCV        geoeffnet=False, kein Frame   2,2 s
ueber yt-dlp aufgeloest      1920x1080 @30 fps, Frame da   1,4 s
```

Die Uebersetzung sitzt in `video/factory.open_source` — an der EINEN Stelle,
die entscheidet, was eine Angabe ist. Die aufgeloeste Medienadresse **verfaellt**
nach wenigen Stunden, ein Spieltag dauert laenger; deshalb wird nicht die
Adresse weitergereicht, sondern der Auftrag, sie zu holen
(`StreamVideoSource(url_aufloesung=...)`, neu erfragt bei jedem
Verbindungsaufbau). Sichtbar bleibt ueberall der eingegebene Link — die
aufgeloeste ist ueber 900 Zeichen lang.

Durchsatz ueber die fertige Kette: **65 fps gelesen** (Echtzeit braucht 30),
Sprung auf Frame 81000 und vier geprueste ROI-Bilder in 8 Sekunden.

`source_label` liefert `youtube_<Kennung>` statt `www.youtube.com_watch` —
sonst teilten sich **alle** YouTube-Laeufe einen Debug-Ordner und eine
`video_id`.

### Automatisch kalibrieren — die Bibliothek lief vorher nie (BUG-023)

Die am Vortag gebaute Tafeltyp-Pruefung wurde **kein einziges Mal ausgefuehrt**:
Aufruf an `_on_video_opened`, wo `current_frame` immer `None` ist, und dahinter
ein `AttributeError` (`resolve_path` statt `resolve`), den der stille `return`
konservierte. Siehe BugSkill BUG-023.

An ihre Stelle tritt ein Knopf mit **Bildauswahl** (`gui/boardtype_dialog.py`):
Kacheln der bekannten Bauarten, dazu „Neues Board aufnehmen". Eine Bauart
erkennt man am Aussehen, nicht am Namen.

### Ein Standbild genuegt nicht — zwei Kunstgriffe

16 Stichproben ueber ein Spiel von 3:08 h, vier gleiche Tafeln im Bild:
**einmal alle vier, sechsmal drei, fuenfmal gar keine.** Brennende Kegellampen
und wechselnde Ziffern veraendern genau die Merkmale, an denen der Abgleich
haengt. Die **Lage** aendert sich dagegen nie.

1. **Ueber mehrere Bilder suchen und nach Lage buendeln.** Was in ≥ 2 Bildern
   an derselben Stelle auftaucht, ist eine Tafel. Die Wiederholung ersetzt die
   hohe Einzelbildschranke — deshalb darf `boardtype_anchor_inlier` (8) unter
   `boardtype_min_inlier` (14) liegen.
2. **Ankerkette.** Jede *bestaetigte* Tafel wird selbst zur Vorlage der
   naechsten Runde. Das Overlay ist ein Kameraausschnitt; eine Vorlage von der
   mittleren Tafel passt schlecht zur aeussersten rechten, ihr Nachbar dagegen
   gut. Deshalb wurde die rechte fast immer uebersehen.

```
eine Vorlage    3, 0, 4, 3, 3, 0, 3, 3 Tafeln, schwaechster Treffer 13
Ankerkette      4, 0, 4, 4, 4, 0, 3, 4 Tafeln, schwaechster Treffer 62
```

Voller Durchlauf: 4 Tafeln, 418 tragende Merkmale, 25 Felder je Bahn in
5,7 Sekunden — ohne einen Klick in die Tafel.

### Livestream: die Suche waechst mit, statt zu springen

Ein Stream hat keine Vergangenheit. `LaufendeSuche` nimmt entgegen, was kommt,
und bricht **bei Erfolg** ab, nicht nach Zeit. Gemessen an acht Stellen, ein
Bild je 0,8 s Streamzeit:

| Stelle | bis alle vier |
|---|---|
| 0 / 21187 / 84750 | 3,2 / 4,8 / 2,4 s |
| 127125 / 254250 / 300000 | 8,0 / 14,4 / 4,8 s |
| 169500 / 317812 | Zeitgrenze, 2 bzw. 3 Tafeln |

Sechs von acht erreichen das Ziel, im Mittel nach 4,8 Sekunden. Danach zeigt
`TrefferDialog` die eingezeichneten Rahmen und fragt, ob sie sitzen — Zahlen
ueber tragende Merkmale beantworten diese Frage nicht, ein Bild schon.

**Wie viele Tafeln erwartet werden, sagt der Nutzer** (Feld im Auswahlfenster,
Vorgabe `calibration.lane_count`). Das ist zugleich das Abbruchkriterium.

### Was daran noch nicht gut ist

* An zwei von acht Stellen findet er gar nichts — dort taugt keins der
  angebotenen Bilder als Anker. Bewusst **nicht** mit einer niedrigeren
  Schranke schoengerechnet: Ein falscher Anker vervielfaeltigt seinen Irrtum
  ueber die ganze Kette.
* Die Suche laeuft im GUI-Faden (0,3 s je Bild, mit `processEvents`
  dazwischen). Bei mehr Bauarten in der Bibliothek gehoert sie in einen
  eigenen Faden.
* Der Ziffernversatz (`digit_shift`) bleibt Handarbeit — ein
  ergebnisunabhaengiges Kriterium dafuer fehlt weiterhin.

---

## Automatische Kalibrierung, zweiter Anlauf: Bild in Bild (2026-09-10/11)

Der Merkmalsabgleich wurde **ersetzt**, auf Ansage des Nutzers: *"wir lassen
alle deine Ansaetze und fangen doch an, automatische Kalibrierung darueber,
das Bild in Bild gesucht wird ... dann kann man das Bild auch bisschen
verzerren und verkippen lassen."* Die Abschnitte darueber beschreiben den
alten Weg und gelten nur noch als Historie.

`calibration/board_match.py` sucht das Musterbild mit einer Maske im Frame,
ueber mehrere Skalen und Drehungen, und zieht danach jede Ecke einzeln nach.

### Gemessen: Streuung zwischen den vier gleichen Tafeln

Das ist das richtige Mass -- der Abstand zu einer handgesetzten Referenz
enthaelt deren eigenen, systematischen Fehler. Acht Stellen eines Spiels von
3:08 h:

| Verfahren | Streuung | Dauer |
|---|---|---|
| Merkmalsabgleich | 1,43 px | ~7 s |
| Bild in Bild | 1,00 px | 16 s |
| + getrennte Maskenraender (Lampen 0,022 / Ziffern 0,008) | 0,97 px | 20-24 s |
| **+ Verkippung (Ecken einzeln, ZNCC)** | **0,76 px** | 24-32 s |
| von Hand gesetzt | 0,89 px | Minuten |

Alle acht Stellen finden alle vier Tafeln, kein Wert ueber 1,0 px. Die
automatische Kalibrierung sitzt damit **enger als die von Hand**.

Drei Befunde, die den Weg dorthin erklaeren:

1. `TM_CCORR_NORMED` mit Maske ist **ueber Vorlagengroessen hinweg nicht
   vergleichbar** -- kleinere Vorlagen gewinnen grundlos. Bewertet wird
   deshalb mit maskiertem ZNCC im entzerrten Raum.
2. Die **obere Matrixleiste** ist keine ROI, sondern wechselnder Text. Sie
   muss als eigenes Rechteck maskiert werden; ohne das scheiterten einzelne
   Bilder vollstaendig.
3. **Der Median ueber mehrere Funde schlaegt den besten Einzeltreffer**, und
   Weitersammeln nach dem vollstaendigen Fund halbiert den Fehler.

Verworfen und dokumentiert: Kantenfang (`edge_snap.ziehe_nach`) und ECC --
beide machten es messbar schlechter (1,35 -> 1,90 / 2,34). Der Neuschnitt der
Vorlage war unnoetig: Die Randzeilen sind zu 94-99 % Gehaeuse.

### Nachkalibrieren: eine Tafel gross ziehen (2026-09-11)

*"ich brauche einen Button 'Nachkalibrieren' ... an dem ich jedes Board das ich
aendern will anklicken kann, das wird mir gross gezeigt und ich kann die ROIs
anpassen"*

`gui/board_editor.py` -- Knopf, dann Klick in die Tafel, dann die **entzerrte**
Tafel gross (rund 530 px statt 250 im Vollbild) mit ziehbaren Bereichen.
Gearbeitet wird in normierten Tafelkoordinaten, also genau dort, wo die ROIs
definiert sind: kein Umweg ueber eine Homographie.

* Rand ziehen = Groesse, Mitte ziehen = Lage, Pfeiltaste = ein Tafelpixel.
  Die Ziffern haengen an einzelnen Pixeln (gemessen: 1 px = 9 Prozentpunkte
  Lesegenauigkeit) -- mit der Maus ist ein Pixel nicht zu treffen.
* Der Dialog arbeitet auf **Kopien**; "Abbrechen" bleibt folgenlos.
* Optional auf alle Tafeln uebertragen -- die Koordinaten sind normiert, was
  auf einer Tafel sitzt, sitzt auf jeder derselben Bauart.
* Waehrend der Tafelauswahl ist das Ziehen im Video **abgeschaltet**: Sonst
  griffe der Auswahlklick den Bereich darunter und verschoebe ihn.
* Ein Livestream wird dafuer nicht angehalten -- der Player holt neue Bilder
  nur, solange er laeuft, und ob eine Ziffernbox sitzt, entscheidet sich an
  wechselnden Ziffern.

### Die Gruenlampe war zu klein geschnitten (2026-09-11)

Ein Livelauf mit automatischer Kalibrierung verlor auf zwei Bahnen den ersten
Wurf, spaeter auch mitten im Spiel. Der Nutzer: *"der erkennt ja gerade auf
Bahn 5 gar nicht richtig, ob sie aus ist."*

**Nicht die Erkennung, die Kalibrierung.** GEMESSEN an der Gruenspur des Laufs:

| Bahn | AN | AUS | Abstand | AUS-Frames |
|---|---|---|---|---|
| 2 | 96,7 | 50,0 | 46,7 | 1305 |
| 3 | 97,6 | 33,3 | 64,3 | **309** |
| 4 | 96,7 | 56,7 | 40,0 | 2861 |
| 5 | **73,3** | 33,3 | 40,0 | **398** |

Bei gleich vielen Wuerfen sammelt Bahn 4 das Neunfache an AUS-Frames der Bahn 3
-- dort fehlen ganze Gruenphasen, und das sind die fehlenden Wuerfe.

Zwei Ursachen, beide in der Bauart:

1. Die Gruenlampen-ROI des Typs war **0,0393 x 0,0319**, die von Hand gesetzte
   **0,0650 x 0,0520** -- 2,7fache Flaeche.
2. Sie sass **1,1 bis 1,7 px zu hoch**, auf allen vier Tafeln (Vergleich gegen
   die Handkalibrierung derselben Aufzeichnung).

Klein UND daneben heisst: ein Teil der Flaeche liegt auf dem Gehaeuse, der
AN-Pegel sackt in Richtung AUS, und die Schwelle findet kein Tal mehr.

**Das Mass, das entschieden hat** (`tools/measure_gruen_trennschaerfe.py`):
Otsu trennt die Punktwolke, dann Fisher = Abstand^2 / Streuung. Es haengt an
keinem Kriterium, auf das eine Kalibrierung optimiert wurde. Die **schwaechste**
Bahn entscheidet -- dort geht der Wurf verloren.

| Bahn | von Hand | automatisch | jetzt |
|---|---|---|---|
| 2 | 110,5 | 80,6 | 69,7 |
| 3 | 36,6 | 38,9 | 26,3 |
| 4 | 10,1 | 14,1 | 13,4 |
| 5 | 14,6 | **6,3** | **16,2** |
| **schwaechste** | 10,1 | **6,3** | **13,4** |

Die Groesse wurde durchprobiert, nicht geraten: 1,0x -> 9,1; 1,3x -> 11,5;
**1,65x -> 13,4**; 2,0x -> 12,9; 2,4x -> 12,8. Groesser verwaessert (AN faellt
von 99 auf 37). Das Optimum trifft auf drei Stellen die Groesse, die der Nutzer
von Hand gewaehlt hatte.

### Feinschliff je Tafel -- fuer die Lampen, NICHT fuer die Ziffern

`calibration/roi_feinschliff.py`. Nach dem Fund wird jede Tafel einzeln gegen
das Musterbild nachgezogen, getrennt nach Lampenraute und Gruenlampe. GEMESSEN
an zwei Quellen, Versatz in Vorlagenpixeln:

```
Gruppe        Tafel 1  Tafel 2  Tafel 3  Tafel 4
lampen         -0,07    -0,07    +0,14    -0,11
gruenlampe     -0,94    -0,36    +0,34    +0,69
```

Die Gruenlampe wandert um 1,6 px, die Lampenraute nicht -- **eine Verschiebung
der ganzen Tafel kann das nicht einfangen**, es ist eine Restverzerrung, die
Massstab, Drehung und Eckenkorrektur uebriglassen.

**Fuer die Ziffern gemessen und verworfen.** 7290 beleuchtete Zellen, sauber
gelesen: throw_number 86,1 -> 79,2 %, pin_count 71,5 -> **47,8** %, total_b
26,4 -> 31,9 %, left_display 70,0 -> 77,8 %; insgesamt 56,8 -> 57,2 %. Zwei
Felder besser, zwei schlechter, ein klarer Verlierer. Der Grund ist inhaltlich:
Der Feinschliff richtet an der STRUKTUR aus -- eine Lampe sitzt daran, eine
Ziffernzelle im Fenster nicht. Fuer die Ziffern gilt weiter `digit_zero_fit`
(Ausrichtung an den Nullen, also an einem bekannten Sollwert).

### ROI-Aenderungen wirken jetzt im laufenden Betrieb (BUG-024)

Vorher wirkte ein waehrend der Analyse gezogener Rahmen nicht -- `prepare`
rechnet die Bereiche einmal in Pixelrechtecke um, danach liest die Analyse nur
noch diese. Und es sagte niemand. Jetzt: `uebernimm_kalibrierung` durch alle
drei Schichten, Uebernahme beim naechsten Frame, Gedaechtnis der betroffenen
Detektoren geleert (die Schwellen haengen an der Messstelle), Zustand der Bahn
unangetastet.

### Die Schablone auf die Lampenmitte gezogen (2026-09-11)

Auf Wunsch des Nutzers nach dem Nachkalibrieren-Fenster. `tools/fit_schablone_lampen.py`
misst je Lampe ueber ALLE Tafeln und trennt dabei zwei Dinge:

* was alle Tafeln TEILEN -- ein Fehler der Bauart, gehoert in die Schablone;
* was je Tafel ANDERS ausfaellt -- Schaetzrauschen des Fundes. In die Schablone
  geschrieben, verschlechtert es drei Tafeln, um eine zu verbessern.

Kriterium: korrigiert wird nur, wenn der gemeinsame Versatz groesser ist als
sein Standardfehler (Streuung zwischen den Tafeln / Wurzel ihrer Zahl).
**5 von 9 Lampen** erfuellten das:

```
Lampe   gemeinsam       Streuung   Fehler   korrigiert
1       +0,19/+0,21 %     0,43      0,21      ja
2       -0,18/-0,52 %     0,34      0,17      ja
3       +0,10/-0,16 %     0,45      0,22      nein
5       -0,47/-0,33 %     0,40      0,20      ja
6       +0,11/+0,06 %     0,75      0,38      nein  (Rauschen)
9       -0,08/-0,07 %     0,21      0,10      ja
```

GEMESSEN auf Frames 38000-44000, also unabhaengig von allem Angepassten
(Trennschaerfe der Kegellampen, schwaechste Lampe je Bahn):

| Bahn | vorher | jetzt | von Hand |
|---|---|---|---|
| 2 | 40,9 | **54,0** | 31,6 |
| 3 | 11,9 | 11,9 | 2,8 |
| 4 | 19,3 | **28,7** | 3,7 |
| 5 | 26,0 | 25,0 | 4,9 |

Zwei Bahnen deutlich besser, eine gleich, eine minimal schlechter. Ein kleiner
Schritt -- die Lampen waren schon vorher nicht der Engpass.

**Die Handkalibrierung faellt hier drastisch ab** (2,8 bis 4,9). Sie traegt die
ALTEN, doppelt so grossen Lampen-ROIs (0,080 x 0,075), und die passen nicht zu
`core_percentile: 0` -- genau die Paarung aus BUG-021. `1Spieltag.json` ist
damit fuer den heutigen Konfigurationsstand die falsche Datei;
`1Spieltag_enge_lampen.json` ist die richtige.

### Was beim Nachzentrieren im LAUFENDEN Betrieb herauskam: nichts

Vom Nutzer angeregt, mit der richtigen Sicherheitsfrage versehen (*"das darf
dann natuerlich nicht dazu fuehren, dass eine deaktivierte Lampe ploetzlich an
ist"*). Angepasst auf Frames 20000-26000, gemessen auf 26000-32000:

```
Bahn        Fisher ohne   mit      schwaechste ohne   mit
2              82,7      85,4          55,3          59,1
3              98,6      85,8          48,3          59,0
4              83,9      79,8          56,9          53,1
5              75,4      80,2          58,3          65,3
```

Zwei besser, zwei schlechter. **Verworfen.** Der Grund ist physikalisch: Die
Lampen-ROI ist 6 px gross und liegt ganz innerhalb der leuchtenden Scheibe --
ein halber Pixel Verschiebung laesst dieselben Pixel drin.

Der Hinweis des Nutzers dazu ist gemessen richtig und gilt fuer GRUEN:

```
Gruenlampe klein+mittig   AUS 43,1   AN 94,8   <- sitzt ganz im gruenen Glas
Gruenlampe gross          AUS 25,5   AN 69,5   <- Gehaeusering senkt AUS
```

Nicht die Lage war dort das Problem, sondern die Groesse: Das Lampenglas ist
gruen, ob die Lampe brennt oder nicht. Eine Nachjustierung ZUR Lampenmitte hin
liefe bei Gruen also in genau diese Falle.

### Die gelesenen Ziffern stehen jetzt im Bahnpanel (2026-09-11)

*"ich haette gerne, dass dort auch steht, was er gerade an Ziffern erkannt hat.
Also welche Werte angeblich wo stehen. Das wuerde mir helfen bei der
Evaluierung, ob wir die Ziffern bald wieder reinnehmen, oder nicht."*

Eine Zeile je Bahn, in der Anordnung der TAFEL (Fehl · SummeA · Wurf · Kegel ·
SummeB). Unsichere Lesungen werden grau gezeigt, nicht verschwiegen -- sie sind
die interessanteste Auskunft fuer den, der den Leser beurteilen will.

Drei Eigenschaften, die dazugehoeren:

* **Keine Rueckwirkung.** Diese Lesungen gehen in keine Summe, keine
  Gegenprobe und keinen Versand. Die Ziffern sind seit dem 2026-08-26 aus der
  Wertung genommen; eine Anzeige, die sie stillschweigend wieder einspeist,
  wuerde genau die Frage verwischen, die beantwortet werden soll.
* **Derselbe Leseweg wie in der Auswertung** (`read_digits`) -- eine Anzeige,
  die anders liest als die Analyse, taugte zur Beurteilung nichts.
* **Ohne zeitliche Glaettung**, anders als bei den Lampen: Gezeigt wird, was
  der Leser JETZT sieht, nicht die Mehrheit der letzten zwei Sekunden.

GEMESSEN: eine Lesung kostet 4,25 ms je Bahn. Deshalb lesen die Bahnen
VERSETZT (je Bahn ein anderer Frame) -- alle vier im selben Frame waeren 17 ms
auf einmal, bei 29 ms Grundlast und 40 ms Budget also ein verlorener Frame.

### Die automatische Kalibrierung scheiterte still an ihrer eigenen Zeitgrenze (2026-09-11)

*"es ist gescheitert, weil die automatisierte Kalibrierung nicht lief"* --
und im Protokoll stand dazu NICHTS. Zwischen "Bibliothek geladen" und dem
Programmende lagen 38 stumme Sekunden.

REPRODUZIERT am Stream:

```
Bild 1 (volles Raster)   20,5 s   -> Zeitgrenze (20 s) vorbei
Bild 2 (enges Raster)     1,3 s   -> haette gereicht, kam nie dran
```

Die Suche SAH im ersten Bild alle vier Tafeln (Guete 0,82 / 0,80 / 0,75 /
0,74). Sie zaehlten nur nicht: `boardtype_min_frames: 2` verlangt zwei Bilder.

**Zwei Fehler, beide behoben:**

1. **Die Zeitgrenze wurde beim Umbau nie nachgemessen.** 20 s stammten aus der
   Zeit des Merkmalsabgleichs (7 s je Bild); Bild in Bild braucht 18 s. Jetzt
   30 s -- und der teure Teil ist weg (siehe 2).
2. **Die Suche schwieg.** Jetzt steht Start, Dauer je Bild, Zeitgrenze und
   Misserfolg im Protokoll.

### Zweistufiges Raster: 19 s -> 4,3 s

Der Grobdurchgang sucht dasselbe Raster auf einem HALBIERTEN Bild (Kosten
fallen mit der Flaeche, also auf ein Viertel) und liefert nur Massstab und
Winkel; der feine Durchgang arbeitet dann eng darum in voller Aufloesung.

GEMESSEN an fuenf Stellen: immer 4 Tafeln, Guete praktisch gleich. Und im Mass,
das zaehlt -- Abstand der Lampen-ROI zur gemessenen Lampenmitte:

| Bahn | volles Raster | zweistufig |
|---|---|---|
| 2 | 0,43 px | 0,43 px |
| 3 | 0,46 px | 0,46 px |
| 4 | 0,13 px | 0,24 px |
| 5 | 0,87 px | 0,70 px |
| Mittel | 0,47 px | **0,46 px** |

Der Grobdurchgang gibt auf, wenn seine beste Guete unter `boardmatch_min_guete`
bleibt -- dann wird wie bisher das volle Raster abgesucht. GEMESSEN trennt das
sauber: echte Tafel 0,715 bis 0,728, Bilder ohne Tafel -1,000 / 0,038 / -0,035.

### Geklaert: der oeffentliche Schluessel darf nur lesen (2026-09-11)

Die Doku widersprach sich. `apps/liveticker/README.md` sagte, seit dem
2026-09-07 duerfe `anon` auf `throws` nur noch lesen; der Abschnitt vom selben
Tag weiter oben in DIESEM Dokument sagte "Noch nicht ausgefuehrt -- RLS ist auf
der Tabelle unveraendert". Anlass der Klaerung war eine Rueckfrage von aussen,
vor dem Einbinden des Tickers.

GEMESSEN 2026-09-11 gegen die Produktivdatenbank, mit dem
`sb_publishable_`-Schluessel:

| Aufruf | Antwort |
|---|---|
| SELECT | HTTP 200, liefert Zeilen |
| INSERT | HTTP 401, `42501` |
| UPDATE | HTTP 401, `42501` |
| DELETE | HTTP 401, `42501` |

**Die README hatte recht, dieser Abschnitt war veraltet.** Es wurde nichts
geschrieben: PATCH und DELETE liefen gegen einen Filter, der keine Zeile
trifft, und der INSERT wurde abgewiesen.

WORAUF DER SCHUTZ BERUHT, und das ist der Unterschied zur alten Formulierung:
Der Wortlaut der Absage ist *"permission denied for table throws"* mit dem
Hinweis *"GRANT UPDATE ON public.throws TO anon"*. Das sind die
TABELLENRECHTE (`revoke insert, update, delete`), nicht eine RLS-Regel -- eine
solche meldete "new row violates row-level security policy". Ob `relrowsecurity`
zusaetzlich gesetzt ist, laesst sich von aussen nicht sehen; PostgREST gibt das
Schema fuer oeffentliche Schluessel nicht heraus ("Only secret API keys can be
used for this endpoint").

Fuer den Ticker genuegt das: Die Rolle kann nicht schreiben. Wer es nachsehen
will, braucht SQL-Zugang:

```sql
select relrowsecurity from pg_class where relname = 'throws';
select grantee, privilege_type from information_schema.role_table_grants
 where table_name = 'throws';
```

**`lane` ist die reale Bahnnummer der Anlage.** `ThrowResult.lane` bekommt
`display_number`, und das ist `real_lane_number` aus der Kalibrierung
(Vorgabe `lane_number_mapping: [2, 3, 4, 5]`). VORBEHALT: Wird eine
Kalibrierung ohne Eingabe der Bahnnummern erzeugt, faellt `display_number` auf
die Tafelposition von links zurueck (1..4).

### Mehrere Bereiche zugleich, und gemerkte Feinkorrekturen (2026-09-11)

*"je Tafel die Moeglichkeit, ein Offset von x und y zu setzen ... dafuer soll
er die ROIs anklicken, die er gleichzeitig verschieben moechte. Am besten
waere es, wenn sich der Code das merkt, und wenn das naechste Mal der Tafeltyp
ausgewaehlt wird, dann schlaegt er automatisch vielleicht verschiedene
Kalibrierungen vor."*

**Teil 1 -- gemeinsam verschieben.** Im Nachkalibrieren-Fenster lassen sich
mehrere Bereiche waehlen (Klick, Strg-Klick zum Sammeln, Knoepfe fuer "alle",
"Lampen", "Ziffern") und zusammen versetzen: ueber zwei Eingabefelder in
Tafelpixeln oder mit den Pfeiltasten. Das Ziehen wurde dabei von "Mitte auf den
Zeiger" auf RELATIV umgestellt -- bei mehreren Bereichen gibt es keine
gemeinsame Mitte, und auch ein einzelner sprang vorher, wenn man ihn nicht
mittig anfasste.

Der Grund ist nicht Bequemlichkeit: Was zusammen danebenliegt, gehoert zusammen
verschoben. Die untere Ziffernzeile wandert gemessen als GANZES -- sie einzeln
nachzuziehen hiesse, denselben Fehler achtmal zu schaetzen statt einmal.

**Teil 2 -- `calibration/korrekturen.py`.** Gemerkt wird der Unterschied zur
BAUART, je Tafelposition von links, in normierten Tafelkoordinaten. Drei
Entscheidungen dahinter:

1. **Keine Tafelecken.** Die haengen an Kamera, Zoom und Blickwinkel und sind
   in der naechsten Halle wertlos. Die Versaetze auf der Tafel beschreiben
   dagegen die ANLAGE und gelten wieder. (Wer eine ganze Kalibrierung sichern
   will, hat dafuer weiter "Speichern".)
2. **Je Tafel, nicht gemittelt.** GEMESSEN wandert die Gruenlampe ueber die
   vier Tafeln um 1,6 px, waehrend die Lampenraute stehenbleibt -- ein
   gemeinsamer Mittelwert verschlechterte drei Tafeln, um eine zu verbessern.
3. **Vorgeschlagen, nicht angewandt.** Ob eine Korrektur aus einer anderen
   Halle hier passt, weiss der Mensch davor. Eine still uebernommene waere ein
   Fehler, den niemand sucht, weil niemand von ihr weiss. Sie steht als
   Auswahlfeld unter der Kachel ihrer Bauart.

Fehlt beim Anwenden eine Tafelposition (es wurden weniger Tafeln gefunden als
beim Merken), bleibt sie unveraendert -- sonst landete die Korrektur der
dritten Tafel auf der zweiten.

### Gesichter im Tafelbild -- der Ausgang, den die Maske aussparte (2026-09-13)

Vom Nutzer im Liveticker gesehen: *"sieht man sehr haeufig noch Gesichter ->
immer dann, wenn sie Phantomwuerfe erzeugen."*

Die Personenmaske schwaerzt bewegten Vordergrund, nimmt aber die Tafelbereiche
aus -- zu Recht, dort steht das Signal. Genau dieses Rechteck geht als
`board_jpeg` an die Datenbank. Wer vor der Tafel stand, war im ganzen Bild
geschwaerzt, nur nicht dort, wo alle hinsehen. Die Haeufung hat denselben
Grund wie das Bild: Dieselbe Person erzeugt den Phantomwurf.

BELEGT an der Produktivdatenbank, 1000 Bilder: **21 % der Wuerfe mit "0 Kegel"
zeigen eine verdeckte Tafel, gegen 0,8 % der uebrigen.**

**Meine eigene Pruefung hatte den Befund gelobt** -- sie meldete "Bilder mit
Schwaerzung IN einem Tafelbereich: 0 (muss 0 sein)". Als Erfolgskriterium
formuliert, und es war die Ursache. Siehe BUG-025 und den neuen Skill
`kegel-datenschutz`.

Behoben durch zweimaliges Schwaerzen mit verschiedenen Schranken: Das
Analysebild bleibt wie es war, der VEROEFFENTLICHTE Ausschnitt bekommt eine
zweite Maske mit einer Schranke in TAFELFLAECHEN (`person_min_blob_boards`).

GEMESSEN, Flecken die einen Tafelbereich beruehren:

```
Mensch                    2,86 Tafelflaechen
groesster Nicht-Mensch    0,18 Tafelflaechen   (wechselnde Ziffernzeile)
```

Relativ zur Tafel und nicht in Pixeln, weil die Pixelzahl an Kamera und
Abstand haengt, das Verhaeltnis zur Tafel aber nicht. Wirkung an 6000
Ausschnitten: **27,9 % geschwaerzt bei Verdeckung, 0,09 % im Normalbetrieb** --
die Ziffern bleiben lesbar.

### Nachtrag am selben Tag: der erste Anlauf sah den Stillstehenden nicht

Die Schwaerzung menschgrosser BEWEGTER Flecken (oben) ging an dem Fall vorbei,
der den Befund ausgeloest hat. GEMESSEN am Mitschnitt vom 2026-09-08, Bahn 2,
Frame 13489 -- ein Mensch beugt sich ueber die Tafel und ist im Bild voll zu
sehen:

```
Verdeckung (Bewegung)                    0,081   Schwelle 0,14
groesster bewegter Fleck auf der Tafel   0,09 Tafelflaechen
```

Er steht still und ist ins Hintergrundmodell gewandert -- die Grenze, die in
`person_maske.py` seit jeher steht, hier zum ersten Mal mit Folgen.

**`analysis/tafel_wache.py`** tritt an seine Stelle: eine Referenz der eigenen
Tafel, die NUR nachlernt, wenn die Tafel normal aussieht. Dann kann niemand
hineinwandern, egal wie lange er steht.

| | Abweichung auf den stabilen Pixeln |
|---|---|
| Normalbetrieb (2705 Messungen) | Median 1,41 %, 95. Perzentil 2,55 % |
| Mensch davor | 11,9 bis 14,1 % |

14,27 % ist zugleich das Maximum des ganzen Mitschnitts -- es gab genau dieses
eine Ereignis, und genau dort steht das Bild mit dem Gesicht.

**Die Lehre, die ueber diesen Fall hinausgeht:** Eine Messung an bewegten
Menschen beweist nichts ueber stillstehende. Der erste Anlauf war gemessen und
trotzdem falsch, weil die Stichprobe den Fall nicht enthielt, um den es ging.
Wer eine Schutzmassnahme misst, muss sie an dem Fall messen, der sie ausgeloest
hat.

### Die Verdeckungsschwelle misst sich jetzt selbst (2026-09-13)

Der Nutzer: *"Wir bauen ein Tool, was immer funktioniert, kein 'ja aber wenn'
-- 1 Tool und das muss tragen."* Zu Recht: `occlusion_score` war eine feste
Zahl, und feste Zahlen tragen hier nicht.

**Der Anlass.** Ein Mensch lief durch die Gruenphase von Bahn 2. Die Gruenspur:

```
41747-42218   ON,  Score 75-82   (19 Sekunden stabil)
42224-42233   OFF, Score  0,0    <- Lampe vollstaendig verdeckt, 0,4 s
42235         ON,  Score 70,8
```

Score exakt 0,0 ist die Signatur einer vollstaendigen Verdeckung. Die Bremse
stand auf 0,0 -- also aus -- und es wurde ein Wurf gebucht, mit dem Gesicht
des Menschen als Beleg in der Datenbank.

**Warum sie aus stand.** GEMESSEN, AUS-Niveau der gruenen Lampe:

| | AUS-Niveau | AUS-Messungen unter 8 |
|---|---|---|
| Livestream (Overlay) | 22,5 bis 30,6 | 6 % |
| direkte Hallenkamera | 0,7 bis 11,7 | 94 bis 100 % |

Eine feste 12 friert die Hallenkamera dauerhaft ein, eine feste 0 schaltet die
Bremse ab. **Derselbe Fehlertyp wie BUG-011:** eine Groesse als konstant
angenommen, die es nicht ist.

**Jetzt anteilig** (`occlusion_off_fraction: 0.3`) am Niveau, das die
Gruenerkennung ohnehin misst -- die untere Wolke des gleitenden Histogramms.
Kein Perzentil-Rueckfall: Liegt die Bahn ueberwiegend auf AN, liefert jedes
Perzentil das AN-Niveau (gemessen 73,3 statt 25), und die Schwelle laege
mitten in der AUS-Wolke.

**Drei Zeugen, jeder sieht etwas Eigenes:**

| Zeuge | sieht |
|---|---|
| Gruen-Score gegen das AUS-Niveau | einen Menschen VOR DER LAMPE |
| Personenmaske | einen BEWEGTEN Menschen auf der Tafel |
| Tafelwache | eine Tafel, die nicht mehr wie sie selbst aussieht |

Am Streamende sind die ersten beiden blind: alles schwarz, kein bewegter
Vordergrund, und das gemessene AUS-Niveau selbst null. Die Wache meldet 61 bis
68 % -- ohne sie wurden dort drei Wuerfe gebucht.

GEGENPROBE mit EINER Konfiguration ueber beide Quellen:

| Fall | vorher | jetzt |
|---|---|---|
| Stream, Mensch durch die Gruenphase | 1 Wurf (0 Kegel) | **0** |
| Stream, Streamende | 3 Wuerfe (0 Kegel) | **0** |
| Hallenkamera, normaler Betrieb | 35 Wuerfe | **35**, kein Einfrieren |

### Der vierte Zeuge: ein Personenmodell auf dem Tafelband (2026-09-13)

Der Nutzer: *"YOLOv8n, lad das Modell und miss was es bringt. Das Modell muss
ja auch nur auf den Bereichen der Anzeigetafel laufen."*

**Die Messung, die alles entschieden hat, ist die nach dem ZUSCHNITT.** Auf dem
blanken Tafelausschnitt -- also genau dem Bild, das an die Datenbank geht --
findet das Netz praktisch nichts. Es braucht Umgebung.

| Zuschnitt | Beweisstelle F42177-42246 | Fehlalarme / 600 ruhige Frames | Kosten |
|---|---|---|---|
| Tafel allein (136x136 px), 4 Laeufe | 19 von 70 Frames | 0 | 263 ms |
| Tafel + 100 % Luft, 4 Laeufe | 55 von 70 Frames | 0 | 266 ms |
| **Band ueber alle vier Tafeln, 1 Lauf** | 53 von 70 Frames | 0 | **62 ms** |
| **Band, nach unten verlaengert, 1 Lauf** | **57 von 70 Frames** | **0** | **68 ms** |

Gegenprobe an den 1682 Bildern, die im Vollauf wirklich an Supabase gingen:
auf dem blanken Ausschnitt **0 von 2** bekannten Gesichtern gefunden.

Der Grund ist anschaulich: Im 136x136-Ausschnitt FUELLT der Mensch das Bild,
und ein formatfuellendes Gesicht ohne Umgebung sieht fuer das Netz nach nichts
aus. Deshalb sucht `detection/personen_modell.py` in EINEM Band ueber alle vier
Tafeln -- ein Lauf statt vier, und mit Kontext.

**An der Beweisstelle**, genau den zehn Frames, in denen der Gruen-Score auf
0,0 fiel (F42224 bis F42233): Das Modell rahmt den Menschen in **allen zehn**
ein, Vertrauen 0,71 bis 0,86.

**Warum das Regel 4 nicht bricht.** 68 ms je Frame waeren bei 40 ms Budget das
Ende des Livebetriebs. Das Modell laeuft deshalb nur, wenn ein billiger Zeuge
schon etwas meldet -- plus eine Streife alle 10 Frames fuer den Menschen, der
auf der Tafel steht, ohne die Lampe zu beruehren. GEMESSEN ueber 20 000 Frames
des Livestreams: nur in **1,95 %** der Frames faellt ueberhaupt eine Bahn unter
ihre Verdeckungsschwelle.

**Was er kann, was die anderen drei nicht koennen.** Die drei erkennen einen
Menschen an seiner WIRKUNG und wissen nicht, dass es ein Mensch IST. Deshalb
koennen sie ihn nicht gezielt schwaerzen. Durch den echten `encode_board`-Weg
gemessen, an genau den zwei Bildern, die mit Gesicht in der Datenbank landeten:

| | F42237 | F265727 |
|---|---|---|
| ohne Schwaerzung | 27,6 % dunkel | 21,4 % dunkel |
| nur Tafelwache | 27,6 % | 21,4 % |
| **Wache + Modell** | **47,2 %** | **34,0 %** |

Beide Gesichter vollstaendig verdeckt (`debug/schwaerzung_mit_modell.png`).

**LIZENZ -- und warum sie hier nichts gekostet hat.** Das Projekt steht seit
2026-09-14 unter **MIT** (`LICENSE`); vorher hatte es gar keine Lizenz, war
also trotz oeffentlichem Repo rechtlich "alle Rechte vorbehalten".

YOLOv8n stammt von Ultralytics und steht unter **AGPL-3.0**. Das vertraegt sich
nicht mit MIT: Ein Werk mit AGPL-Teilen kann nicht unter MIT stehen, die
Richtung geht nur andersherum. Gemessen wurde deshalb die ganze Familie --
und der Verzicht kostet nichts:

| Modell | Lizenz | Netz | F42177-42246 | F265667-265736 | Fehlalarme/600 |
|---|---|---|---|---|---|
| YOLOv8n 640 | AGPL-3.0 | 62 ms | 57 / 70 | 69 / 70 | 0 |
| YOLOX-S 640 | Apache-2.0 | 100 ms | 57 / 70 | 69 / 70 | 0 |
| **YOLOX-Tiny 416** | **Apache-2.0** | **28 ms** | **55 / 70** | **68 / 70** | **0** |
| YOLOX-Nano 416 | Apache-2.0 | 13 ms | 55 / 70 | 64 / 70 | 0 |

**YOLOX-Tiny ist mehr als doppelt so schnell** wie das AGPL-Modell. Gegen Nano
entschied der Abstand zur Schwelle: an den zehn Ampel-Null-Frames 0,73 bis 0,83
statt 0,54 bis 0,72.

Die Gewichte liegen trotzdem nicht im Repo (`.gitignore: models/`) -- nicht aus
Lizenzgruenden, sondern weil 20 MB Binaerdaten, die sich nie aendern, nichts in
einer Versionsverwaltung verloren haben. `tools/hole_personenmodell.py` holt
sie mit Pruefsummenkontrolle; es braucht kein PyTorch mehr, nur einen Download.
Fehlt die Datei, laeuft alles mit drei Zeugen weiter -- eine Warnung, kein
Fehler.

**Nebenbefund, dokumentiert im Test:** Solange kein AUS-Niveau gelernt ist,
faellt die Verdeckungsschwelle auf den festen Wert 0 zurueck -- und ein
Gruen-Score von exakt 0,0 ist NICHT kleiner als 0. Am Laufanfang kaeme eine
vollstaendig verdeckte Lampe also an allen drei billigen Zeugen vorbei. Genau
diese Luecke schliesst die Streife.

**Der Preis, gemessen am vollen Hallenmitschnitt** (13 530 Frames):

| | Wuerfe | ms/Frame | Netzlaeufe |
|---|---|---|---|
| ohne Modell | 64 | 31,4 | -- |
| YOLOv8n ohne Mindestabstand | 64 | 88,9 | 94 % der Frames |
| YOLOv8n, Abstand je Bahn | -- | -- | 33 % |
| YOLOv8n, Abstand ueber alle Bahnen | 64 | 48,0 | 20 % |
| **YOLOX-Tiny, Abstand ueber alle Bahnen** | **64** | **37,1** | **20 %** |

Der Aufschlag des ausgelieferten Modells: **5,7 ms je Frame** -- und zwar auf
der Aufnahme mit der festhaengenden Bahn 5, dem schlechtesten bekannten Fall.

Die 64 Wuerfe sind nicht nur der Zahl nach gleich: Frames, Bahnen, Kegelzahlen
und Kegelnummern stimmen Zeile fuer Zeile ueberein.

Die 94 % waren ein Befund, kein Rechenfehler: Auf Bahn 5 dieses Mitschnitts
meldet die **Tafelwache in 2704 von 3000 Frames** Fremdes -- bei einem
Gruen-Score von 73,4, also klar sichtbarer Lampe. Diese Bahn steht dort
dauerhaft in der Bremse. EIN festhaengender Zeuge genuegt, um teure Analyse in
jeden Frame zu ziehen. Deshalb `alarm_interval: 5`, und deshalb zaehlt der
Abstand ueber ALLE Bahnen: Das Netz sucht in einem Band ueber alle vier
Tafeln, seine Antwort gilt fuer alle zugleich.

**OFFEN geblieben:** warum die Wache auf Bahn 5 dieses Mitschnitts festhaengt.
Das Modell koennte es beantworten -- gemessen ist es nicht, und ohne Messung
wird an der Bremse nichts gelockert.

**Noch eine Falle, die beim Bauen auffiel.** Das veroeffentlichte Tafelbild
stammt aus einem Sample-Frame, bis zu 34 Frames zurueck -- der Ringpuffer der
Pipeline haelt aber nur MASKIERTE Bilder. Auf denen verliert das Netz den
Menschen: GEMESSEN an 12 Beweisframes in 2 davon (F265723, F265724, roh beide
sicher gefunden). `PersonenModell` haelt deshalb den ROHEN Bandausschnitt der
letzten 50 Frames vor, vorskaliert auf die Arbeitsaufloesung des Netzes
(0,4 statt 1,7 MB je Frame). Das ist die einzige Stelle im Programm, an der
rohe Bildpunkte von Menschen aufgehoben werden -- sie verlassen den
Arbeitsspeicher nie.
