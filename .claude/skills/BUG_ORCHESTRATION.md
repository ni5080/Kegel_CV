# BUG-ORCHESTRIERUNG — Kegel_CV

> **Zweck:** Kein Bug darf zweimal passieren. Jeder echte Bug wird nicht nur gefixt,
> sondern hinterlässt zwei dauerhafte Spuren: **einen Regressionstest** (verhindert
> die Wiederkehr technisch) und **einen BugSkill** (verhindert die Wiederkehr in
> Claudes Denkweise — auch in ganz anderem Code).
>
> Regressionstest = Netz. BugSkill = gelernte Lektion.

---

## 1. Wann greift dieser Workflow?

| Situation | Workflow? |
|---|---|
| Falsches Ergebnis, Absturz, Hänger, falsche Erkennung | ✅ Ja |
| Test schlägt fehl, den ich vorher grün hatte | ✅ Ja |
| Nutzer meldet "das stimmt nicht" | ✅ Ja |
| Tippfehler, den ich beim Schreiben sofort bemerke | ❌ Nein — einfach korrigieren |
| Fehlendes Feature | ❌ Nein — das ist Arbeit, kein Bug |
| Bewusst zurückgestellte Einschränkung | ❌ Nein — `docs/OPEN_QUESTIONS.md` |

**Faustregel:** Wenn ich beim Fix denke *„ah, das hätte ich wissen müssen"* → BugSkill.
Wenn ich denke *„das war ein Vertipper"* → kein BugSkill.

---

## 2. Der Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. REPRODUZIEREN                                            │
│    Bug in einen fehlschlagenden Test gießen — VOR dem Fix.  │
│    Kein reproduzierbarer Test ⇒ noch kein Verständnis.      │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 1b. GIF ERZEUGEN — bevor eine Erklaerung entsteht           │
│    tools/streitfall_gif.py: die Tafel Frame fuer Frame, mit │
│    ALLEN dort ausgelesenen Werten (Zeit, Frame, Gruen, jede  │
│    Kegellampe, jedes Ziffernfeld). Regel 7 in CLAUDE.md.    │
│    Wer ohne GIF erklaert, erklaert seine Zahlen, nicht die  │
│    Tafel — und merkt nicht, wenn die Zahlen luegen.         │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. URSACHE FINDEN (nicht Symptom)                           │
│    "5 Warum?" bis zur echten Ursache.                       │
│    Symptom: "Wurf 17 doppelt gezählt"                       │
│    Ursache: "Zustandsmaschine kehrt bei einem Störframe     │
│              nach ANALYZING zurück, weil Hysterese fehlt"   │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. KLASSIFIZIEREN → bestimmt, wie breit der Schutz sein muss│
│    siehe Kategorientabelle §3                               │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. FIXEN — an der Ursache, nicht am Symptom.                │
│    Kein try/except, das den Fehler nur verschluckt.         │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. TEST GRÜN + gesamte Suite grün                           │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. VERALLGEMEINERN — die entscheidende Frage:               │
│    „Wo im Projekt könnte derselbe Denkfehler noch stecken?" │
│    Diese Stellen prüfen und ggf. mitfixen.                  │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. BUGSKILL SCHREIBEN  → .claude/skills/bugs/BUG-NNN-…/     │
│    + Eintrag in bugs/BUGS_INDEX.md                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Bug-Kategorien (projektspezifisch)

Diese Kategorien sind aus den realen Risiken dieses Projekts abgeleitet.
Die Kategorie bestimmt Präfix, Testort und wie weit die Verallgemeinerung gehen muss.

| Kat. | Name | Typische Erscheinung | Regressionstest gehört nach |
|---|---|---|---|
| `TEMPORAL` | Zeitliche Logik | Double Counting, verpasster Wurf, Flackern kippt Zustand | `tests/unit/test_state_machine.py` |
| `CALIB` | Kalibrierung/Geometrie | ROI verschoben, Homographie falsch herum, Punktreihenfolge | `tests/unit/test_calibration.py` |
| `DETECT` | Erkennung | Lampe falsch, Ziffer falsch, Schwellwert unpassend | `tests/unit/test_detectors.py` |
| `COUNT` | Zähl-/Summenlogik | 15er-Zyklus falsch, Summe driftet, Wurfnummer springt | `tests/unit/test_scoring.py` |
| `LANE` | Bahn-Unabhängigkeit | Zustand einer Bahn beeinflusst eine andere | `tests/unit/test_lane_isolation.py` |
| `VIDEO` | Videoquelle | Seek ungenau, Dropframes, FPS falsch, Ressourcenleck | `tests/unit/test_video_source.py` |
| `GUI` | Oberfläche/Threads | Freeze, Zugriff auf Qt aus Worker-Thread, Race | `tests/unit/test_gui_logic.py` |
| `CONFIG` | Konfiguration | Magic Number, Parameter greift nicht, Default falsch | `tests/unit/test_config.py` |
| `ROBUST` | Robustheit | Absturz statt Weiterlauf bei Störframe | `tests/unit/test_robustness.py` |

---

## 4. BugSkill-Vorlage

Ablage: `.claude/skills/bugs/BUG-NNN-kurzer-slug/SKILL.md`
Nummerierung: fortlaufend, dreistellig, nie wiederverwendet.

````markdown
---
name: bug-NNN-kurzer-slug
description: >
  Verhindert <Kategorie>-Bug: <ein Satz, was schiefging>. Laden, wenn an
  <konkreter Bereich> gearbeitet wird — Stichworte: <Trigger1>, <Trigger2>.
---

# BUG-NNN — <Titel>

| | |
|---|---|
| **Kategorie** | `TEMPORAL` |
| **Gefunden** | 2026-08-24, Phase 8 |
| **Schweregrad** | hoch / mittel / niedrig |
| **Regressionstest** | `tests/unit/test_state_machine.py::test_...` |

## Symptom
Was war beobachtbar? (konkret, mit Zahlen/Frames — nicht abstrakt)

## Ursache
Der eigentliche Denkfehler. Nicht der Symptomort.

## Falsch
```python
# so war es — und warum das trügerisch plausibel aussah
```

## Richtig
```python
# so ist es — und warum das trägt
```

## Regel für die Zukunft
> Ein Satz, der beim nächsten Mal reicht, um den Fehler zu vermeiden.

## Wo gilt diese Regel noch?
- [ ] `src/…` geprüft
- [ ] `src/…` geprüft
````

---

## 5. Qualitätskriterien für einen BugSkill

Ein BugSkill ist gut, wenn er diese fünf Punkte erfüllt:

1. **Er ist konkret.** „Auf Off-by-one achten" ist wertlos. „Die Wurfnummer der Tafel
   ist 1-basiert, der Zyklusindex 0-basiert — beim Umrechnen `(n-1) % 15 + 1`" ist wertvoll.
2. **Er erklärt, warum der Fehler plausibel aussah.** Sonst mache ich ihn wieder.
3. **Er nennt den Regressionstest namentlich.** Nachvollziehbarkeit.
4. **Seine `description` triggert zuverlässig.** Sie muss die Stichworte enthalten,
   die in einer künftigen Aufgabe vorkommen werden.
5. **Er verallgemeinert.** Mindestens eine Zeile: „Wo gilt das noch?"

---

## 6. Index pflegen

Nach jedem BugSkill: Zeile in `.claude/skills/bugs/BUGS_INDEX.md` ergänzen.
Der Index ist die schnelle Übersicht — der Skill die Tiefe.

---

## 7. Anti-Muster beim Bugfixen

| ❌ Nicht so | ✅ Sondern |
|---|---|
| `try: ... except: pass` um den Fehler herum | Ursache beheben; Fehler als Status (`ERROR`) protokollieren |
| Schwellwert im Code anpassen, bis es passt | Schwellwert in Config, mit Begründung im Kommentar |
| Nur die eine Bahn fixen, die auffiel | Alle 4 Bahnen prüfen — `LANE`-Kategorie existiert genau deshalb |
| Test nach dem Fix schreiben | Test **vor** dem Fix — sonst ist unbewiesen, dass er greift |
| „Passiert nur bei diesem Video" | Genau solche Fälle sind die wertvollen — Fixture aus dem Frame bauen |
| BugSkill für jeden Tippfehler | Nur bei echten Denkfehlern — sonst verwässert der Ordner |
