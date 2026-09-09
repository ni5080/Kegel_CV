---
name: bug-004-dokumentierter-startbefehl-nie-ausgefuehrt
description: >
  Verhindert CONFIG-Bug: Der in README und CLAUDE.md dokumentierte Startbefehl
  scheiterte mit ModuleNotFoundError, weil alle Tests ueber sys.path-Hacks bzw.
  pytests pythonpath liefen und der echte Befehl nie ausgefuehrt wurde. Laden bei
  Arbeit an Projektsetup, Paketinstallation, Einstiegspunkten, src-Layout,
  PYTHONPATH, pyproject.toml oder wenn ein Befehl dokumentiert werden soll.
---

# BUG-004 — Dokumentierter Startbefehl wurde nie ausgeführt

| | |
|---|---|
| **Kategorie** | `CONFIG` |
| **Gefunden** | 2026-08-24, beim ersten echten Start durch den Nutzer |
| **Schweregrad** | **hoch** — die Anwendung war für den Nutzer nicht startbar |
| **Regressionstest** | `tests/unit/test_packaging.py` |

## Symptom

```
pythonw.exe: Error while finding module specification for 'kegel_cv.main'
(ModuleNotFoundError: No module named 'kegel_cv')
```

Der Befehl stand so in `README.md` und `CLAUDE.md`:

```bash
.venv/Scripts/python.exe -m kegel_cv.main
```

## Ursache

Das Projekt nutzt ein **src-Layout** (`src/kegel_cv/`). Damit liegt das Paket
nicht im Arbeitsverzeichnis und ist ohne Installation nicht importierbar.

Der eigentliche Fehler liegt aber nicht in der fehlenden Installation, sondern
darin, **wie ich getestet habe**:

| Was ich ausführte | Warum es funktionierte |
|---|---|
| `pytest tests/unit` | `pyproject.toml` setzt `pythonpath = ["src"]` |
| Alle Smoke-Tests | Ich schrieb `sys.path.insert(0, "src")` an den Anfang |
| Der dokumentierte Befehl | **nie ausgeführt** |

Jeder einzelne Test lief grün — durch einen Mechanismus, den der Nutzer nicht
hat. Ich hatte mir eine Umgebung gebaut, in der der Fehler nicht auftreten
konnte, und dann behauptet, es funktioniere.

Warum das trügerisch plausibel aussieht: 198 grüne Tests fühlen sich wie ein
Beleg an. Sie belegen aber nur, was sie ausführen — und der Startbefehl gehörte
nicht dazu.

## Falsch

```bash
# dokumentiert, nie ausgeführt
.venv/Scripts/python.exe -m kegel_cv.main
```

```python
# in jedem Smoke-Test -- verdeckt genau das Problem
import sys; sys.path.insert(0, "src")
```

## Richtig

Einmalig nach dem Klonen:

```bash
.venv/Scripts/python.exe -m pip install -e .
```

Danach funktioniert `python -m kegel_cv.main` überall. Der Schritt gehört in die
Installationsanleitung, nicht in eine Fußnote.

## Regel für die Zukunft

> **Ein Befehl, den ich dokumentiere, muss ich vorher genau so ausgeführt haben** —
> in derselben Form, ohne Hilfskonstrukte, die nur in meiner Testumgebung
> existieren.

Und allgemeiner: `sys.path`-Manipulation in Testskripten ist ein Warnzeichen.
Sie umgeht ein Setup-Problem, statt es zu lösen — und verschiebt den Fehler zu
dem, der das Projekt zum ersten Mal startet.

## Wo gilt diese Regel noch?

- [x] `README.md` — Installationsschritt ergänzt
- [x] `CLAUDE.md` — Installationsschritt ergänzt
- [x] `tests/unit/test_packaging.py` — prüft, dass `kegel_cv` ohne
      `sys.path`-Eingriff importierbar ist und `main` einen Einstiegspunkt hat
- [ ] Weitere dokumentierte Befehle (`tools/verify_rois.py`,
      `tools/measure_signal.py`): Diese setzen `sys.path` bewusst selbst, weil
      sie Skripte außerhalb des Pakets sind — das ist dort korrekt und
      beabsichtigt, aber jeder neue Befehl in der Doku gehört vorher ausgeführt.
