---
name: kegel-testing
description: >
  Teststrategie und Testkonventionen in Kegel_CV. Laden beim Schreiben von Tests,
  Fixtures, synthetischen Frames, Regressionstests nach einem Bug, beim Testen von
  Zustandsmaschine, Zähllogik, Kalibrierung, Detektoren oder wenn gefragt wird, ob
  eine Änderung ausreichend abgesichert ist.
---

# Testen

## 1. Was getestet wird — und was nicht

| Testen | Nicht testen |
|---|---|
| Zähl- und Zykluslogik | dass OpenCV OpenCV ist |
| Zustandsübergänge | Qt-Rendering |
| Double-Counting-Schutz | exakte Pixelwerte eines Videos |
| Kalibrierungs-Mathematik | Performance in Unit-Tests |
| Config-Validierung | |
| Plausibilitätsregeln | |
| Bahn-Unabhängigkeit | |

Faustregel: Alles, was **ohne Video und ohne GUI** prüfbar ist, gehört in einen
Unit-Test. Genau dafür ist die Schichtung gebaut (siehe `kegel-architektur`).

## 2. Struktur

```
tests/
  unit/          schnell (< 1 s gesamt), keine Dateien, kein Qt, kein Video
  integration/   mit echten Frames aus tests/fixtures/
  fixtures/      kleine PNGs + JSON, im Repo eingecheckt
```

## 3. Synthetische Frames statt echter Videos

Ein Unit-Test darf **nie** ein 2-GB-Video laden. Stattdessen Frames erzeugen:

```python
def make_scoreboard(green_on: bool, lamps: list[int], digits: str) -> np.ndarray:
    """Erzeugt eine synthetische Anzeigetafel mit bekanntem Sollzustand."""
```

Vorteil: Der Sollwert ist per Konstruktion bekannt. Ein Test gegen echtes Material
prüft immer zwei Dinge gleichzeitig (Erkennung *und* Annahme über das Material) —
und beim Fehlschlag ist unklar, welches der beiden falsch war.

Echte Frames kommen zusätzlich zum Einsatz, als **Integrationstest** mit manuell
verifizierter Erwartung:

```python
# fixtures/lane1_throw5_pins.png  -- manuell nachgezählt: 5 Lampen, Ziffer 5
```

## 4. Die kritischen Testfälle (Auftrag §23)

```python
# Zyklus -- die klassische Off-by-one-Falle
@pytest.mark.parametrize("throw,expected_in_cycle,expected_cycle", [
    (1, 1, 1), (14, 14, 1), (15, 15, 1),    # 15 -> 15, nicht 0!
    (16, 1, 2), (30, 15, 2), (31, 1, 3),
])
def test_zyklus_berechnung(throw, expected_in_cycle, expected_cycle): ...

# Double Counting -- derselbe Wurf über viele Frames
def test_kein_double_counting_bei_vielen_frames():
    """40 Frames mit gleicher Wurfnummer ergeben genau EINEN Wurf."""

# Leerwurf -- zählt mit, obwohl 0 Kegel
def test_leerer_wurf_erhoeht_wurfnummer():
    """Wurf 1: 7 Kegel, Wurf 2: 0 Kegel, Wurf 3: 5 Kegel -> alle drei erkannt."""

# Bahn-Unabhängigkeit
def test_bahnen_beeinflussen_sich_nicht():
    """Ereignis auf Bahn 1 ändert den Zustand der Bahnen 2-4 nicht."""

# Störframe
def test_einzelner_stoerframe_kippt_zustand_nicht():
    """Ein Ausreißer-Frame löst keinen Zustandswechsel aus."""

# Lücke
def test_luecke_wird_erkannt_nicht_kaschiert():
    """Sprung 7 -> 9 erzeugt Warnung und UNKNOWN-Platzhalter."""
```

## 5. Regressionstests nach Bugs

Jeder Bug bekommt einen Test — **vor** dem Fix geschrieben (siehe
`BUG_ORCHESTRATION.md`). Namenskonvention macht die Herkunft sichtbar:

```python
def test_bug_007_wurf_nicht_doppelt_bei_gruen_flackern():
    """BUG-007: Grünlampe flackerte 1 Frame, Wurf wurde doppelt gebucht."""
```

Ein Regressionstest ohne Bug-Nummer verliert nach Monaten seinen Sinn — man
streicht ihn dann als „redundant", und der Bug kommt zurück.

## 6. Testdaten aus Debug-Events

Der Debug-Ordner ist die beste Fixture-Quelle: Ein realer Fehlerfall liegt dort
bereits mit Frames und Ergebnis vor.

```
debug/<video>/lane_2/throw_017/  ->  tests/fixtures/bug_007/
```

Dabei nur die tatsächlich nötigen ROI-Ausschnitte übernehmen, keine Vollframes —
Fixtures gehören ins Repo und sollen klein bleiben.

## 7. Was einen Test wertlos macht

| Anti-Muster | Warum schädlich |
|---|---|
| `assert result is not None` | prüft nichts Fachliches |
| Test spiegelt die Implementierung | bricht bei jedem Refactoring, findet keine Bugs |
| Schwellwerte im Test hartkodiert | Config-Änderung bricht Tests statt sie zu prüfen |
| Test braucht das große Video | zu langsam, läuft nicht in CI |
| Zufallsdaten ohne festen Seed | sporadische Fehlschläge zerstören das Vertrauen |

## 8. Ausführung

```bash
.venv/Scripts/python.exe -m pytest tests/unit -q          # schnell, ständig
.venv/Scripts/python.exe -m pytest -q                     # vollständig
.venv/Scripts/python.exe -m pytest --cov=kegel_cv -q      # mit Abdeckung
```

Vor jedem Statuswechsel in `ORCHESTRATION.md` muss die vollständige Suite grün sein.
