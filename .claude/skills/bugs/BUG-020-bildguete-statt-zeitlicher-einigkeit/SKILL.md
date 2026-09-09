---
name: bug-020-bildguete-statt-zeitlicher-einigkeit
description: >
  Verhindert DETECT-Bug: Die "Confidence" eines Ziffernfeldes vermischt zwei
  verschiedene Groessen -- wie gut die Ziffer auf EINEM Bild zu erkennen war
  und ob die Frames dasselbe gesehen haben. Regeln, die auf zeitliche
  Einigkeit bauen, bekamen die Bildguete und konnten nie greifen. Laden bei
  Arbeit an Ziffernaggregation, Confidence-Schwellen, min_confidence,
  min_agreement oder Filtern, die "die Frames sind sich einig" pruefen.
---

# BUG-020 — Bildgüte als „Einigkeit" ausgegeben

| | |
|---|---|
| **Kategorie** | `DETECT` |
| **Gefunden** | 2026-09-04, durch eine Nutzerfrage |
| **Schweregrad** | **hoch** (eine Regel war strukturell wirkungslos, ohne dass es auffiel) |
| **Regressionstest** | `test_field_aggregation.py::TestMehrheitBug020`, `test_throw_analyzer.py::TestEinigkeitStattBildguete`, `::TestNeunWirdNichtZurNull`, `::TestVerworfenerZyklusBehaeltDenSpielwechsel` |

## Symptom

`discard_zero_throw_number` griff im gesamten Spieltag **kein einziges Mal**
(0 Treffer), obwohl die Tafel beim Warmwerf-Sperrzyklus nachweislich 000
zeigte. Der Nutzer bestand darauf, dass dort 000 steht — zu Recht.

## Ursache

GEMESSEN an Bahn 4, F126593, über die zehn echten Sample-Frames:

```
alle zehn Frames lasen '0','0','0'      -> voellig einig
Scores der fuehrenden Stellen: 0,35     -> unter min_confidence (0,5)
```

Zwei Schwellen standen im Weg, hintereinander:

1. **`TemporalAggregator.add()`** verwirft jede Stimme mit
   `confidence < min_confidence`. Bei 0,35 fielen ALLE zehn durch. Die
   verworfenen Stimmen wurden nur GEZÄHLT (`_rejected`), nicht gespeichert —
   die Einigkeit war danach nicht mehr rekonstruierbar.
2. **`FieldAggregator.result()`** liefert `None`, sobald eine Stelle unklar
   ist. Aus zwei schwachen Stellen wurde ein komplett unlesbares Feld.

Und selbst mit gesenkter Schwelle hätte die Regel nicht gegriffen: Das
Aggregat meldet als „Confidence" die **Bildgüte der schwächsten Stelle**
(0,35), die Regel verlangt aber 0,9.

**Der eigentliche Denkfehler:** Eine Zahl namens `confidence` trägt zwei
Bedeutungen, die nichts miteinander zu tun haben:

| | Frage | Wert im Messfall |
|---|---|---|
| Bildgüte | Wie gut ist die Ziffer auf **einem Bild** zu erkennen? | 0,35 |
| Einigkeit | Haben die **Frames dasselbe** gesehen? | 1,00 |

Der Kommentar an der Regel meinte immer schon die zweite — wörtlich: *„Eine
Fehllesung flackert; ein echter Stillstand ist über alle abgetasteten Frames
hinweg felsenfest."* Geliefert wurde die erste. Bei schwach lesbarer Anzeige
kann eine solche Regel deshalb **nie** greifen — obwohl die Einigkeit dort
das einzig Belastbare ist.

## Falsch

```python
# pipeline.py -- der Name sagt Einigkeit, der Wert ist Bildguete
def confidence_of(name):
    return felder[name].result()[1]

# throw_analyzer.py
if throw_number == 0 and throw_number_confidence >= 0.9:
    return None      # unerreichbar, sobald die Anzeige schwach ist
```

## Richtig

```python
# temporal_aggregator.py -- eine eigene Groesse, ohne Confidence-Schwelle
def mehrheit(self) -> tuple[T | None, float]:
    """Was haben die Frames MEHRHEITLICH gesehen -- und wie einig waren sie?"""
    counts = Counter(v.value for v in self._alle)   # ALLE, auch schwache
    best = max(counts, key=counts.get)
    return best, counts[best] / len(self._alle)

# throw_analyzer.py
nummer_mehrheit, nummer_einigkeit = throw_number_majority
if nummer_mehrheit == 0 and nummer_einigkeit >= min_agreement:
    return None
```

`result()` bleibt unverändert — kein bestehender Filter ändert sein Verhalten.

## Die führende Stelle zählt nicht mit

`throw_number_ignore_leading: 1`. Ein Spiel hat 30 Würfe, eine
Hunderterstelle gibt es fachlich nicht (Nutzerangabe). Sie steht dauerhaft
auf einer dunklen Null und wird chronisch schwach gelesen — sie mitzubewerten
hieße, das Feld an einer Stelle scheitern zu lassen, die nichts aussagt.

## Gegenprobe gegen 003 / 008 / 009

Auf Nutzerhinweis geprüft, weil diese Zahlen der 000 ähneln könnten.
GEMESSEN an **24 echten Würfen** mit Nummer 3, 8 oder 9 über alle vier
Bahnen (mit den echten Sample-Frames und der echten Aggregation):

> **0 von 24** würden als „0" durchgehen.

Nebenbefund: Die Ziffernerkennung liest bei diesen Würfen häufig daneben
(3→4, 8→9, 8→2, 9→8, 9→„30", 9→„10") — rund ein Viertel. Aber **nie in
Richtung 0**. Die Fortzähl-Logik fängt das ab, weshalb es nie auffiel. Die
verbreitete Annahme „die Wurfnummer wird zu 100 % erkannt" gilt so nicht.

## NACHTRAG Q16 — was Einigkeit NICHT leistet

Der Nutzer prüfte die Entwarnung nach und fand die Lücke: *"ein 9 als 30 ist
durchaus sehr nah an 00"*. Er hatte recht.

Die beiden auffälligen Fälle der Gegenprobe sahen harmlos aus, waren es aber
nicht:

| Bahn | echter Wurf | gelesen | Einigkeit | gerettet durch |
|---|---|---|---|---|
| 3 | 9 | `('0','3','0')` | 1,00 | Zehnerstelle zufällig falsch (3) |
| 4 | 9 | `('0','1','0')` | 1,00 | Zehnerstelle zufällig falsch (1) |

Die **Einerstelle** wurde als 0 gelesen, obwohl dort eine 9 steht — in zehn
von zehn Frames. Zwei von acht Neunern, also **25 %**.

**Die Grenze des Fixes:** Zeitliche Einigkeit schützt gegen FLACKERN, nicht
gegen SYSTEMATISCHE Fehllesung. Ein Detektor, der eine 9 konsistent als 0
liest, ist sich einig — und falsch. Bei Einigkeit 1,00 sieht beides gleich
aus. Das war in der ersten Fassung dieses Fixes nicht bedacht.

**Die Absicherung:** Die Regel verlangt jetzt ZWEI unabhängige Felder auf
null — Wurfnummer UND Summe, also genau das "000 0000" der Anzeige.
GEMESSEN an denselben 24 Würfen: Summen von 12 bis 71, kein einziger auf
null. Beide kritischen Neuner sind damit durch Konstruktion geschützt statt
durch Zufall.

Die Ziffernverwechslung selbst bleibt offen — siehe `docs/OPEN_QUESTIONS.md`
(Q16), vermutlich dieselbe Wurzel wie BUG-009.

## NACHTRAG: die Regel gehört HINTER die Wurfnummer-Auflösung

Erster Teillauf (F110000-230000, 2026-09-04): Die Regel griff — alle vier
Sperrzyklen verworfen, Kegelsumme unverändert. Aber sie stand VOR
`_resolve_throw_number` und brach dort ab. Damit verschluckte sie den
SPIELWECHSEL: Der verworfene Zyklus ist genau derjenige, der das Zeichen
`display_reset` trägt. Niemand rief `start_new_game()`, das Zeichen verfiel,
zwei Sätze wuchsen zusammen:

    Bahn 4  F183107  Wurf 30      <- Satzende
    Bahn 4  F186293  Wurf 31      <- hätte Wurf 1 sein müssen
    Abschnittslängen: [1, 20, 30, 30, 60, 20, 16]   <- der 60er

Das ist BUG-019 in neuer Gestalt. Behoben, indem die Regel dorthin wandert,
wo alle anderen Verwerfungs-Filter stehen — hinter die Auflösung, mit
`_kette_wiederherstellen()`. Genau dafür wurde die Methode gebaut.

**Belegt durch den Vergleich zweier Läufe über denselben Bereich:**

| | Regel vorn | Regel hinten |
|---|---|---|
| Würfe | 706 | 706 |
| Kegel gesamt | 4923 | 4923 |
| Bahn 4 | `[1,20,30,30,`**`60`**`,20,16]` | `[1,20,30,30,30,30,20,16]` |

**Was daran lehrreich ist:** Kein einziger Unit-Test hatte den Fall erfasst.
Er entsteht erst aus dem Zusammenspiel zweier Regeln, und sichtbar wurde er
nur an einer Abschnittslänge. Der Regressionstest
(`TestVerworfenerZyklusBehaeltDenSpielwechsel`) prüft jetzt direkt, dass
`score.game_totals` nach dem Verwerfen gewachsen ist.

## Regel für die Zukunft

> Wenn eine Zahl `confidence` heißt, frage nach, WORAUF sie sich bezieht.
> Und: Einigkeit ist kein Ersatz für Richtigkeit — zehn gleiche Messungen
> können zehnmal denselben systematischen Fehler zeigen. Wo eine falsche
> Lesung Schaden anrichtet, braucht es einen ZWEITEN, unabhängig
> gelesenen Zeugen.
> „Wie gut war das Bild?" und „waren sich die Messungen einig?" sind zwei
> Fragen. Eine Schwelle, die für die eine gedacht ist, kann an der anderen
> dauerhaft scheitern — lautlos, weil ein Filter, der nie greift, keine
> Fehlermeldung erzeugt.

## Wo gilt diese Regel noch?

- [x] `discard_cycles_without_throw_number` nutzt dieselbe
      `throw_number_confidence`. Der Kommentar dort meint ebenfalls die
      zeitliche Einigkeit. BEWUSST NICHT MITGEÄNDERT: Der Filter ist aktiv
      und greift; eine Umstellung braucht eine eigene Vollauf-Gegenprobe.
- [ ] `pin_count`, `total_b`, `left_display`: Für sie gibt es keine
      einigkeitsbasierte Regel — noch nicht geprüft, ob eine fehlt.
- [ ] Ob `min_confidence: 0.5` für die Ziffern insgesamt zu hoch liegt, ist
      offen. Diese Messung zeigt nur, dass sie bei dunklen Nullen greift.
