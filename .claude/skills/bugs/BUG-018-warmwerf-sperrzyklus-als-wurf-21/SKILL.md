---
name: bug-018-warmwerf-sperrzyklus-als-wurf-21
description: >
  OFFENER COUNT-Bug (Fix zurueckgebaut): Direkt nach dem Warmwerfen wird ein
  Sperrzyklus der Anlage als "Wurf 21" gebucht. Enthaelt die Diagnose UND die
  Lehre aus einem gescheiterten Fix -- lesen, BEVOR ein neuer Versuch
  unternommen wird. Laden bei Arbeit an Wurfnummer-Aufloesung,
  Spielwechsel-Erkennung oder Nullwurf-Filtern -- Stichworte: Warmwerfen,
  Wurf 21, Sperrzyklus, display_reset, game_reset_min_frames, Zeuge.
---

# BUG-018 — Warmwerf-Sperrzyklus wird als "Wurf 21" gebucht

> **STATUS: OFFEN. Der Fix wurde am 2026-09-04 ZURUECKGEBAUT.**
> Die vier Faelle bestehen weiter. Was hier steht, ist die Diagnose und
> die Lehre aus einem gescheiterten Fix -- kein Loesungsstand.

| | |
|---|---|
| **Kategorie** | `COUNT` |
| **Gefunden** | 2026-09-03, voller Spieltag (`lauf_2026-09-03_16-51-04`) |
| **Schweregrad** | mittel (4 von 1686 Wuerfen, aber verzerrt jeden Warmwerf-Block) |
| **Regressionstest** | keiner -- mit dem Fix zurueckgebaut |

## Symptom

Vier Wuerfe wurden als "0 Kegel, EMPTY" gebucht, direkt als 21. Wurf eines
20-Wurf-Warmwerf-Blocks (Bahn3 F218448, Bahn4 F126593, Bahn4 F218644,
Bahn5 F220170). Der Nutzer bestaetigte per GIF: "da wird zurueckgesetzt, die
gruene Lampe geht an und dann aus um das Spiel zu sperren bzw neu zu
starten." Nach Nutzerangabe hat Warmwerfen aber IMMER genau 20 Wuerfe --
ein "Wurf 21" direkt danach kann nie echt sein.

## Ursache (5 Warum)

1. **Symptom:** Wurf 21 wird gebucht, obwohl kein Kegel fiel und keine
   Tafelziffer/kein Fehlwurfzaehler das stuetzt.
2. **Warum kein Filter griff:** Der Zeugen-Filter (`discard_zero_without_digit`)
   akzeptiert "Wurfnummer um genau 1 gestiegen" (`nummer_stieg`) als
   ausreichenden dritten Zeugen.
3. **Warum `nummer_stieg` hier zutraf:** `throw_number` wurde ALS 21
   gelesen -- nicht 000, wie eine urspruengliche (separate) Regel
   (`discard_zero_throw_number`) unterstellte.
4. **Warum die Anlage 21 zeigt, statt sofort auf 0 zu springen:** Die Anlage
   haelt ihre Wurfnummer-Anzeige beim Sperren des Feldes fuer den ersten Satz
   mehrere Sekunden auf "letzte Warmwerf-Nummer + 1", lange genug, um von
   unserer 10-Frame-Aggregation stabil gelesen zu werden.
5. **Warum unsere eigene Reset-Erkennung das nicht rechtzeitig auffing:**
   `display_reset` (Anzeige auf 000/0000) braucht `game_reset_min_frames`
   (3) aufeinanderfolgende Nullmessungen zur Bestaetigung -- die liegen bei
   diesem Uebergang GEMESSEN e­rst nach diesem Zyklus vor, nicht waehrend
   seines eigenen Sammelfensters.

**Die eigentliche Ursache:** Ein Zeuge ("Wurfnummer weitergezaehlt"), der
grundsaetzlich zuverlaessig ist, versagt GENAU an einer bekannten,
messbaren Grenze (dem Ende von `warmup_throws`) systematisch -- weil die
Anlage dort selbst einen Wert erzeugt, der wie ein echter Fortschritt
aussieht.

## Wie von BUG-017 (Verdeckung) getrennt

Siehe BUG-017 -- der rohe Gruen-Score trennt beide Bugs sauber: Verdeckung
faellt auf exakt 0.0, der Sperrzyklus bleibt immer ueber 17. Deshalb ist
der Sperrzyklus KEIN Verdeckungsphaenomen und braucht eine andere Regel.

## Falsch

```python
nummer_stieg = throw_number == wurfnummer_vorher + 1
if not (displayed_count is not None or zaehler_stieg or nummer_stieg):
    # verwirft nur, wenn ALLE DREI Zeugen schweigen -- aber an der
    # Warmwerf-Grenze LUEGT der dritte Zeuge (er sieht aus wie ein echter
    # Fortschritt, ist aber die Anlage, die das Feld sperrt).
    return None
```

## Der Versuch — und warum er AUCH falsch war (zurueckgebaut 2026-09-04)

```python
# SO WAR ES GEDACHT -- und so steht es NICHT mehr im Code:
warmwerf_sperre = (wurfnummer_vorher == self.cfg.scoring.warmup_throws
                    and nummer_stieg)
if warmwerf_sperre:
    nummer_stieg = False
```

Zwei Fehler auf einmal: Der Block lief nie (er sass hinter
`throw_number is not None`), und haette er gelaufen, haette er Wurf 21 jedes
regulaeren Satzes mitgefangen -- ein 30er-Satz durchlaeuft
`wurfnummer_vorher == 20` genauso. Details im RUECKBAU-Abschnitt unten.

## NACHTRAG 2026-09-03 21:20 — der Fix greift NICHT, und warum

Im Vollauf `lauf_2026-09-03_20-21-33` steht F126593 unveraendert in der
Tabelle, ohne jede Filtermeldung:

```
Bahn 4: Anzeige steht bei Frame 126600 auf 000/0000 -- die Anlage hat das Spiel beendet
Bahn 4: Wurf 21 erkannt -- 0 Kegel [], Gesamt 130, EMPTY (1.00)
```

**Ursache des Fehlschlags:** Der Filter sitzt in einem Block, der
`throw_number is not None` verlangt. Die rohe Wurfnummer war hier aber NICHT
lesbar -- die 21 entstand erst ueber den Fallback in
`_resolve_throw_number` (`_last_throw_number + 1`).

**Der Denkfehler bei der Diagnose:** Die Annahme "die Anlage haelt ihre
Wurfnummer stabil auf 21" stammte aus der Spalte `Wurfnummer` der
`wuerfe.csv` -- die zeigt aber die AUFGELOESTE Nummer, nicht die rohe
Lesung. Genau derselbe Fehler wie bei der Vorgaengerregel
`discard_zero_throw_number` (dort: "alle vier zeigten 000"), nur eine Ebene
weiter.

**Wie es richtig zu messen waere:** Die rohe `throw_number`, die
`_analyze_sample` an `analyze()` uebergibt, gehoert ins Log oder in eine
eigene CSV-Spalte. Solange nur die aufgeloeste Nummer sichtbar ist, laesst
sich ueber die Rohlesung nichts belegen -- und dieselbe Fehldiagnose
wiederholt sich.

**Wie der Fix aussehen muesste:** Die Warmwerf-Sperre darf nicht an einer
lesbaren Wurfnummer haengen. Die tragenden Merkmale sind:
`wurfnummer_vorher == warmup_throws`, 0 Kegel, keine Tafelziffer, kein
gestiegener Fehlwurfzaehler. Ob die Wurfnummer lesbar war, ist dafuer
unerheblich. ACHTUNG bei der Umsetzung: BUG-008 verlangt, dass Schweigen
allein nichts verwirft -- hier verwirft aber nicht das Schweigen, sondern
die bekannte, gemessene Warmwerf-Grenze.

## RUECKBAU 2026-09-04 — und der zweite, schwerere Grund

Auf die Frage des Nutzers ("bauen wir die Bugfixes zurueck, die nicht
getragen haben?") wurde der Filter geprueft und ENTFERNT. Der erste Grund
war bekannt: 0 Treffer im Vollauf. Beim Pruefen kam ein zweiter, schwererer
dazu.

**Der Filter haette Wurf 21 JEDES Satzes mitgefangen.** Seine Bedingung war
`wurfnummer_vorher == warmup_throws (20) and nummer_stieg`. Ein regulaerer
30er-Satz durchlaeuft `wurfnummer_vorher == 20` aber selbstverstaendlich --
beim Uebergang von Wurf 20 auf 21. Der Analyzer besitzt KEINE Information,
die Warmwerfen von einem Satz unterscheidet.

Der Kommentar im Code behauptete das Gegenteil:

> "mitten in einem Satz (z.B. 20->21 in einem 30er-Satz) bleibt der Zeuge
> unangetastet, weil `wurfnummer_vorher` dort nicht auf `warmup_throws` steht"

Das ist schlicht falsch. Und der Test, der es haette zeigen muessen
(`test_mitten_im_satz_bleibt_zeuge_gueltig`), prueft mit
`wurfnummer_vorher = 25` -- also genau NICHT an der Grenze, an der die
Verwechslung passiert. Er bestaetigte eine Sicherheit, die es nicht gab.

Dass nie Schaden entstand, war Glueck: Der Filter lief wegen
`throw_number is not None` ohnehin nie.

**Was daraus zu lernen ist** -- zusaetzlich zur Regel unten:

1. Ein Test, der die Gegenprobe an einem BEQUEMEN Wert macht (25 statt 20),
   ist kein Test der Grenze. Die Gegenprobe gehoert genau dorthin, wo die
   Bedingung kippt.
2. Ein Kommentar, der eine Bedingung begruendet ("weil dort nicht ..."),
   ist eine Behauptung ueber den Code und muss wie eine Messung geprueft
   werden. Hier haette ein Blick auf "durchlaeuft ein Satz die 20?" genuegt.

## Wie ein tragfaehiger Fix aussehen muesste

Erst messen: Was zeigt die Tafel bei den vier Faellen wirklich? Die
`wuerfe.csv` hat seit 2026-09-03 die Spalte `WurfnummerRoh` -- der naechste
Lauf beantwortet das.

Und die Bedingung braucht ein Merkmal, das Warmwerfen WIRKLICH von einem
Satz unterscheidet. `wurfnummer_vorher == 20` leistet das nicht. Der
Analyzer muesste dafuer wissen, ob der laufende Abschnitt ein Warmwerf-Block
ist -- eine Information, die es dort heute nicht gibt.

## Regel für die Zukunft

> Ein Zeuge, der "die Anlage hat selbst weitergezaehlt" bedeutet, ist nur so
> gut wie die Annahme, dass die Anlage NUR bei einem echten Wurf weiterzaehlt.
> An bekannten Uebergangspunkten (Satzgrenzen, Warmwerf-Ende) kann die Anlage
> intern eigene Zaehlschritte machen, die wie ein Wurf AUSSEHEN, aber keiner
> sind -- diese Grenzen sind Verdachtsmomente, kein Vertrauensbeweis.

## Wo gilt diese Regel noch?

- [x] Satz-Ende (29-31 Wuerfe) geprueft: Die bestehende
      `discard_zero_without_digit`-Pruefung (ueber `display_reset`) griff
      dort im vollen Lauf korrekt -- kein zusaetzlicher Fix noetig, siehe
      Log-Beleg Bahn2 F218537 ("Gruenzyklus ohne Wurf ... Wird verworfen").
- [ ] Ob derselbe Sperrzyklus auch beim UEBERGANG von einem Satz zum
      naechsten Warmwerf-Block (Ende eines Spieltags-Abschnitts) auftritt,
      ist nicht gemessen -- in diesem Spieltag gab es dafuer keinen Fall.
