# BUGS_INDEX — Register aller BugSkills

> Schnellübersicht. Details jeweils im zugehörigen `SKILL.md`.
> Workflow: siehe `../BUG_ORCHESTRATION.md`

| Nr. | Kategorie | Titel | Datum | Schweregrad | Regressionstest |
|-----|-----------|-------|-------|-------------|-----------------|
| [001](BUG-001-roi-bbox-einseitig-geklemmt/SKILL.md) | `CALIB` | Bounding-Box nur einseitig geklemmt | 2026-08-24 | mittel | `test_calibration.py::test_bbox_wird_auf_bildgrenzen_begrenzt` |
| [002](BUG-002-sanduhr-viereck-meldet-falsche-ursache/SKILL.md) | `CALIB` | Sanduhr-Viereck meldete falsche Ursache | 2026-08-24 | niedrig/hoch (UX) | `test_calibration.py::test_vertauschte_reihenfolge_wird_erkannt` |
| [003](BUG-003-videoende-als-dropframe-gemeldet/SKILL.md) | `VIDEO` | Videoende als Dropframe gemeldet | 2026-08-24 | niedrig/mittel (Diagnose) | `test_video_source.py::TestDropframes` |
| [004](BUG-004-dokumentierter-startbefehl-nie-ausgefuehrt/SKILL.md) | `CONFIG` | Dokumentierter Startbefehl nie ausgeführt | 2026-08-24 | **hoch** | `test_packaging.py` |
| [005](BUG-005-falsche-wurfnummer-legt-bahn-still/SKILL.md) | `COUNT` | Falsche Wurfnummer hätte Bahn stillgelegt | 2026-08-24 | **hoch** | `test_throw_analyzer.py::TestWurfnummer` |
| [006](BUG-006-und-verknuepfung-laesst-schwaecheres-kriterium-entscheiden/SKILL.md) | `DETECT` | UND-Verknüpfung ließ schwächeres Kriterium entscheiden | 2026-08-25 | **hoch** | `test_detectors.py::test_bug_006_helligkeit_entscheidet_nicht_die_waerme` |
| [007](BUG-007-kegellampen-blinken/SKILL.md) | `DETECT` | Die Kegellampen blinken — ein Messzeitpunkt genügt nicht | 2026-08-25 | **hoch** | `test_lamp_aggregation.py::TestBlinkenBug007` |
| [008](BUG-008-wurf-verworfen-wegen-wurfnummer/SKILL.md) | `COUNT` | Gegenprobe verwarf Würfe statt sie zu prüfen (28 % Verlust) | 2026-08-25 | **kritisch** | `test_throw_analyzer.py::TestWurfnummer` |
| [009](BUG-009-alternative-ziffernform/SKILL.md) | `DETECT` | Anlage zeichnet die 9 ohne unteren Balken — jede 9 wurde zur 4 | 2026-08-25 | mittel | `test_digit_reader.py` |
| [010](BUG-010-summe-zu-frueh-gelesen/SKILL.md) | `TEMPORAL` | Summe erst kurz vor dem nächsten Wurf aktualisiert — immer alter Stand gelesen | 2026-08-25 | **hoch** | `test_field_aggregation.py` |
| [015](BUG-015-aufzeichnung-endet-nicht/SKILL.md) | `STREAM` | Am Ende der Aufzeichnung wird endlos neu verbunden statt beendet — Schlussbilanz fehlt | 2026-08-31 | mittel | `test_stream_source.py` |
| [011](BUG-011-absolute-schwelle-driftet-weg/SKILL.md) | `DETECT` | Absolute Helligkeitsschwelle hält über 52 Minuten nicht — Signal driftet weg | 2026-08-25 | mittel | `test_detectors.py` |
| [012](BUG-012-stream-blockiert-die-oberflaeche/SKILL.md) | `GUI` | Blockierender Stream-Lesevorgang im GUI-Thread fror die Oberfläche ein | 2026-08-26 | **hoch** | `test_stream_reader.py` |
| [013](BUG-013-rauschen-als-zustandswechsel/SKILL.md) | `DETECT` | Adaptive Schwelle trennte Rauschen — ein Wurf wurde als zwei gezählt | 2026-08-27 | **hoch** | `test_detectors.py::TestBug013RauschenAlsWechsel` |
| [014](BUG-014-aufzeichnung-beginnt-nach-abriss-von-vorn/SKILL.md) | `VIDEO` | Aufzeichnung begann nach jedem Verbindungsabriss wieder bei Frame 0 — 1693 Würfe doppelt gebucht | 2026-08-29 | **kritisch** | `test_stream_source.py::TestAbrissMittenInDerAufzeichnung` |
| [016](BUG-016-spaetes-gruen-an-verdirbt-die-grundlinie/SKILL.md) | `TEMPORAL` | Spät erkanntes GREEN_ON schob das Grundlinienfenster in den Kegelfall — der Räumwurf wurde als „nichts geändert“ verworfen | 2026-09-01 | **hoch** | `test_pipeline_smoke.py::TestBug016GrundlinieVorGruen` |
| [017](BUG-017-verdeckung-im-fenster-gilt-als-leerer-wurf/SKILL.md) | `DETECT` | Verdeckung mitten im Sammelfenster wurde als „0 Kegel, EMPTY“ gebucht statt als Lücke (behoben für Verdeckung IM Fenster, offen für Verdeckung DAVOR) | 2026-09-03 | mittel | `test_throw_analyzer.py::TestVerdeckungImFenster` |
| [018](BUG-018-warmwerf-sperrzyklus-als-wurf-21/SKILL.md) | `COUNT` | **OFFEN** — Warmwerf-Sperrzyklus wird als „Wurf 21“ gebucht; Fix am 2026-09-04 zurückgebaut (griff nie, hätte Wurf 21 jedes Satzes mitgefangen) | 2026-09-03 | mittel | keiner |
| [020](BUG-020-bildguete-statt-zeitlicher-einigkeit/SKILL.md) | `DETECT` | Confidence eines Ziffernfeldes lieferte die Bildguete statt der zeitlichen Einigkeit — eine Regel war dadurch strukturell wirkungslos | 2026-09-04 | **hoch** | `test_field_aggregation.py::TestMehrheitBug020` |
| [021](BUG-021-lampen-stumm-ohne-warnung/SKILL.md) | `DETECT` | Alle vier Bahnen meldeten 67 Wuerfe lang null Lampen (zu grosse ROIs aus einer alten Kalibrierung) — ohne jede Warnung, Ergebnisse gingen so an die Datenbank | 2026-09-07 | **hoch** | `test_lamp_watchdog.py::TestAmEchtenFall` |
| [022](BUG-022-zwei-schreiber-auf-einer-anzeige/SKILL.md) | `GUI` | Player und Analyse malten waehrend eines Laufs in dieselbe Videoanzeige — das Bild sprang zwischen zwei 26 s auseinanderliegenden Stellen hin und her | 2026-09-07 | mittel | `test_analyse_sperrt_wiedergabe.py` |
| [023](BUG-023-funktion-nie-ausgefuehrt/SKILL.md) | `GUI` | Die Tafelbibliothek-Pruefung lief nie: Aufruf an `_on_video_opened`, wo noch kein Frame da ist — der stille `return` verdeckte ausserdem einen `AttributeError` dahinter | 2026-09-10 | **hoch** | `test_auto_kalibrieren.py::TestBibliothekWirdGefunden` |
| [024](BUG-024-roi-aenderung-erreicht-die-analyse-nie/SKILL.md) | `GUI` | Eine im laufenden Betrieb verschobene ROI wirkte nicht -- die Analyse liest nur die beim Start vorberechneten Pixelrechtecke, und nichts sagte es | 2026-09-11 | **hoch** | `test_kalibrierung_im_lauf.py` |
| [025](BUG-025-gesicht-im-tafelbild/SKILL.md) | `DETECT` | Die Personenmaske nahm die Tafelbereiche aus -- und genau dieses Rechteck ging als Bild an die Datenbank: Gesichter im Liveticker, gehaeuft bei Phantomwuerfen | 2026-09-13 | **hoch** | `test_menschen_im_tafelbild.py` |
| [026](BUG-026-wache-haengt-an-einer-bildaenderung/SKILL.md) | `DETECT` | Eine Referenz, die nur unterhalb einer Schwelle nachlernt, erholt sich von einer ECHTEN Aenderung nie mehr: Bahn 5 war 13 000 Frames eingefroren, ohne dass etwas davorstand | 2026-09-14 | **hoch** | `test_personen_modell.py` |
| [027](BUG-027-null-ist-nicht-aus/SKILL.md) | `DETECT` | Eine Schranke, die "abgeschaltet" heissen sollte, stand auf 0,0 -- fuer eine Groesse, die negativ werden kann, ist das keine Abschaltung, sondern eine Schwelle mitten im Rauschen. Ein Spieler bekam einen Punkt zu viel | 2026-09-16 | **hoch** | `test_detectors.py` |
| [028](BUG-028-zeichen-kommt-einen-wurf-zu-spaet/SKILL.md) | `STATE` | Ein zwischen zwei Wuerfen gesehener Spielwechsel kam einen Wurf zu spaet: Der erste Wurf des neuen Spiels landete im alten, und sein Betrag fehlte den Rest des Spiels (CSV und Anzeige, nicht die Datenbank) | 2026-09-17 | mittel | `test_game_reset.py` |
| [029](BUG-029-drei-wege-die-alle-an-einer-ziffer-haengen/SKILL.md) | `STATE` | Zwei Wege zum Spielwechsel sahen nach Redundanz aus, lasen aber dasselbe Ziffernfeld -- auf einer Bahn mit schlechter Wurfnummer fielen beide zugleich aus | 2026-09-17 | mittel | `test_game_reset.py` |
| [030](BUG-030-wurf-faellt-in-die-erholungszeit/SKILL.md) | `DETECT` | Die Selbstheilung der festhaengenden Wache wartet 750 Frames -- ein ganzer Wurfzyklus passt hinein, und der Wurf ist weg. Zwei von drei Zeugen sagten die ganze Zeit, dass nichts verdeckt ist | 2026-09-17 | mittel | offen |
| [019](BUG-019-verworfener-spielwechsel-verschiebt-die-kette/SKILL.md) | `COUNT` | Verworfener Spielwechsel-Zyklus stellte die alte Wurfnummer wieder her — 5 von 64 Sätzen begannen bei 31 statt 1 | 2026-09-03 | **hoch** | `test_throw_analyzer.py::TestVerworfenerSpielwechselVerschiebtDieKette` |

---

## Statistik

| Kategorie | Anzahl | Bedeutung |
|---|---|---|
| `TEMPORAL` | **1** | Zeitliche Logik / Zustandsmaschine |
| `CALIB` | **2** | Kalibrierung / Geometrie |
| `DETECT` | **3** | Erkennung (Lampen, Ziffern) |
| `COUNT` | **3** (davon 1 offen) | Zähl- und Summenlogik |
| `LANE` | 0 | Bahn-Unabhängigkeit |
| `VIDEO` | **1** | Videoquelle |
| `GUI` | 0 | Oberfläche / Threading |
| `CONFIG` | **1** | Konfiguration |
| `ROBUST` | 0 | Robustheit |

**Häufungen beobachten:** Sammeln sich Bugs in einer Kategorie, ist das ein Signal für
einen strukturellen Mangel — dann nicht nur den Einzelbug fixen, sondern den
zuständigen Fach-Skill überarbeiten.

**Aktuelle Beobachtung:** Alle drei Bugs teilen dasselbe Grundmuster —
**ein Zustand wurde bewertet, bevor die dafür nötige Information vorlag**:

- BUG-001: geklemmt, ohne den Fall „vollständig außerhalb" zu kennen
- BUG-002: Fläche geprüft, bevor die Form geprüft war
- BUG-003: Lesefehler gedeutet, bevor feststand, ob noch ein Frame folgt

Das ist genau das Muster, gegen das die Zustandsmaschine mit `min_stable_frames`
schützt. Bei jeder neuen Bewertungslogik lohnt daher die Frage:
**Liegt jetzt schon alles vor, was ich für diese Entscheidung brauche?**

**BUG-004 und BUG-005 zeigen ein zweites Muster:** Beide entstanden dadurch, dass
ein Mechanismus nur in *eine* Richtung gedacht war.

- BUG-004: Getestet wurde über `pythonpath`/`sys.path` — der Weg, den der Nutzer
  tatsächlich geht, wurde nie beschritten.
- BUG-005: Der Double-Counting-Schutz prüfte nur auf zu *kleine* Wurfnummern.
  Ein zu *großer* Wert war ungleich gefährlicher.

Leitfrage für neue Prüfungen: **Was passiert bei einem Wert am anderen Ende?**

**BUG-006 fügt ein drittes Muster hinzu: zu kleine Stichprobe.** Die
Lampen-Schwellwerte stammten aus **einem einzelnen Frame einer Tafel** und wiesen
in die falsche Richtung. Über 3600 Messungen (4 Tafeln × 9 Lampen × 100 Frames)
kehrte sich das Bild um — das vermeintlich bessere Kriterium war das schlechtere.

Regel: **Schwellwerte nie an einem Standbild festlegen.** Immer über viele Frames
und alle Bahnen messen, und die Trennschärfe beziffern statt sie zu schätzen.

**BUG-007, 008 und 009 stammen aus einer einzigen Frage** — „warum weichen fünf
Würfe ab?" — und ergaben drei verschiedene Ursachen. Das ist der eigentliche
Befund: Ein sichtbares Symptom hatte nichts mit *einem* Fehler zu tun.

| Bug | Was tatsächlich falsch war |
|---|---|
| BUG-007 | Die Lampen **blinken** — ein Messzeitpunkt traf zufällig die Dunkelphase |
| BUG-008 | Eine Gegenprobe **verwarf** Würfe, statt sie nur zu prüfen (28 % Verlust) |
| BUG-009 | Die Anlage zeichnet die **9 ohne unteren Balken** — jede 9 wurde zur 4 |

Gemeinsames Muster über 007–009: **Alle drei entstanden dort, wo aus einer
einzelnen Beobachtung eine Entscheidung wurde.** Ein Frame entschied über das
Wurfergebnis (007), eine Ziffernlesung über die Existenz eines Wurfs (008), eine
Mustertabelle über eine unbekannte Form (009).

Regel: **Frage bei jeder Entscheidung, wie viele unabhängige Beobachtungen sie
trägt — und was passiert, wenn genau die eine falsch ist.**

Und aus BUG-008 die teuerste Lehre: **Fehlendes fällt nicht auf.** Falsche Werte
widersprechen sich irgendwann; ausgelassene Ereignisse hinterlassen eine in sich
stimmige, aber unvollständige Ausgabe. Deshalb wird jetzt gezählt, wie viele
Grünzyklen es gab — nicht nur, wie viele Würfe gemeldet wurden.

---

## Was BUG-014 dem Muster hinzufügt

Alle Bugs davor saßen im eigenen Code. BUG-014 saß in einer **Annahme über die
Gegenseite**: dass hinter einer m3u8-Adresse eine Live-Übertragung steht.

Das Projekt hatte den Rückwärtssprung ausdrücklich verboten — `seek()` gibt
während der Analyse immer False. Abgesichert war damit aber nur, dass *wir*
springen. Dass die *Quelle* es von sich aus tut, war nicht bedacht, obwohl es
denselben Schaden anrichtet.

Regel: **Eine Invariante, die nur der eigene Code einhält, ist keine
Invariante.** Frage bei jeder verbotenen Operation, wer sie sonst noch auslösen
kann.

---

## Was BUG-017/018 dem Muster hinzufügen

Beide entstanden aus DERSELBEN Beobachtung ("elf Nullwürfe, alle ansehen")
und sahen im Log fast identisch aus — "0 Kegel, keine Tafelziffer, kein
Fehlwurfzaehler" — hatten aber VOELLIG verschiedene Ursachen: einmal ein
Messloch (Kamera sieht nichts), einmal ein echtes, stabiles Anlagensignal
(Wurfnummer haelt auf +1). Der Nutzer schlug vor, das ueber den rohen
Gruen-Score zu trennen ("faellt er in einem Frame wirklich auf 0?") — GEMESSEN
bestaetigte sich das sauber (0.00 gegen nie unter 17).

Zusaetzlich zeigte BUG-018, dass eine urspruenglich fuer denselben Fall
geschriebene Regel (`discard_zero_throw_number`, Wurfnummer==000) auf einer
Annahme beruhte, die nie am vollen Lauf gemessen wurde — sie griff im Ernstfall
kein einziges Mal. Die vier Faelle, die sie erklaeren sollte, hatten
tatsaechlich `throw_number=21`, nicht `000`.

Regel: **Zwei Symptome, die im Log gleich aussehen, sind nicht automatisch
derselbe Fehler — und eine Regel, die "GEMESSEN" behauptet, muss das an genau
den Faellen belegen, die sie beheben soll, nicht an einer plausiblen Theorie
darueber.**

---

## Was BUG-019 dem Muster hinzufügt

Der Nutzer meldete EINEN falschen Wert ("Wurfnr. 60 statt 30, ist aber
theoretisch korrekt"). Die Messung zeigte dahinter einen systematischen
Versatz über **fünf ganze Sätze**. Der gemeldete Wurf war nicht der Fehler,
sondern die einzige Stelle, an der er auffiel — weil dort zufällig eine
zweite Auffälligkeit (Nullwurf) daneben lag.

Regel: **Wenn ein einzelner Wert falsch ist, prüfe zuerst, ob er allein
falsch ist.** Eine Abfrage über die ganze Ausgabe (hier: „welche Sätze
beginnen nicht bei Wurf 1?") kostet Minuten und entscheidet, ob man einen
Einzelfall oder ein Muster vor sich hat.

Und methodisch: BUG-019 wurde gefunden, weil der ursprüngliche Verdacht
(„die Ziffernerkennung liest falsch") am Log **nachgeprüft** statt geglaubt
wurde. Die Fehllesung existierte tatsächlich — sie war nur nicht die Ursache.

---

## Was der Rückbau von BUG-018 lehrt (2026-09-04)

Der Nutzer fragte nach einem Vollauf: „bauen wir dann die Bugfixes zurück,
die nicht getragen haben?" — eine Frage, die ein ganzes Prüfverfahren
auslöste. Ergebnis:

| Fix | Treffer im Vollauf | Entscheidung |
|---|---|---|
| BUG-019 | 3 Sätze gerettet | bleibt |
| BUG-017 | 1 von 3 Fällen, **kein** gültiger Wurf verloren | bleibt |
| BUG-018 | 0 | **zurückgebaut** |

Beim Prüfen kam heraus, dass BUG-018 nicht nur wirkungslos war, sondern eine
**Falle** enthielt: Er hätte Wurf 21 jedes regulären Satzes mitgefangen. Der
Kommentar im Code behauptete das Gegenteil, und der zugehörige Test prüfte
die Gegenprobe an einem bequemen Wert (25) statt an der Grenze (20).

Regel: **Ein Fix, der nie greift, ist nicht harmlos — er ist ungeprüft.**
Solange er nie lief, ist auch nie getestet worden, was er anrichtet, wenn er
läuft. „Wirkt nicht" ist deshalb ein Grund für Rückbau, nicht für Abwarten.

Und: **Die Trefferzahl eines Filters gehört ins Abschlussprotokoll eines
Laufs.** Zwei der drei Filter dieses Tages waren wirkungslos, und das fiel
erst beim gezielten `grep -c` auf.

---

## Was BUG-020 dem Muster hinzufügt (2026-09-04)

Der Nutzer bestand darauf, dass beim Sperrzyklus 000 auf der Tafel steht —
gegen zwei Erklärungsversuche von Claude, die beide geraten waren. Die
Messung gab ihm recht: Zehn von zehn Frames lasen 000. Die Regel sah sie nur
nie, weil zwischen Anzeige und Regel zwei Schwellen lagen.

Zwei Lehren:

1. **Ein Filter, der nie greift, meldet sich nicht.** Es gibt keine
   Fehlermeldung für "diese Bedingung war nie erfüllt". Deshalb gehört die
   Trefferzahl jedes Filters ins Abschlussprotokoll eines Laufs — sonst
   entsteht Schutz, den es nur auf dem Papier gibt.
2. **Widerspricht der Nutzer der Messung, ist oft die Messung falsch
   zugeordnet.** Dreimal in Folge wurde hier aus einer abgeleiteten Spalte
   (`Wurfnummer` der CSV) auf die Rohlesung geschlossen. Erst der Blick auf
   die tatsächlichen Sample-Frames klärte es.

---

## Nächste freie Nummer: **024**


## Was BUG-021 dem Muster hinzufügt (2026-09-07)

BUG-020 hielt fest: **„Ein Filter, der nie greift, meldet sich nicht."**
BUG-021 ist derselbe Satz eine Schicht tiefer — **ein Detektor, der nie
anspricht, meldet sich auch nicht.**

Der Unterschied ist, wie teuer das wird. Ein wirkungsloser Filter lässt
Fehler durch. Ein stummer Detektor erzeugt Messwerte, die aussehen wie
Ergebnisse: 67 Würfe „0 Kegel", protokolliert, versendet, nicht von einem
ruhigen Spiel zu unterscheiden.

**Die verallgemeinerbare Frage lautet:** *Sieht „ich habe nichts gemessen" in
diesem Datenmodell genauso aus wie ein gültiges Ergebnis?* Wo die Antwort ja
lautet, braucht es eine zweite Quelle und eine Auswertung ihres Widerspruchs
über viele Ereignisse hinweg — nicht je Ereignis, denn eine Warnung pro Wurf
wird zur Tapete.


## Was BUG-022 dem Muster hinzufügt (2026-09-07)

BUG-021 und BUG-022 fielen am selben Tag an, und sie sind dieselbe Wurzel in
zwei Gestalten: **Etwas lief sichtbar falsch, und das Programm sagte es nicht.**
Beim einen ein Detektor, der stumm blieb; beim anderen eine Anzeige, die zwei
verschiedene Frame-Nummern gleichzeitig zeigte, ohne dass das irgendwo auffiel.

Neu ist die Frage nach dem **Besitz**: *Wer darf gerade in dieses Widget
schreiben?* Ein Widget mit zwei Schreibern hat keinen Besitzer, sondern einen
Wettlauf — sichtbar wird er als Flackern, und wer ihn gewinnt, entscheidet der
Zufall der Reihenfolge.

Und die Erkenntnis, dass **„angehalten" nicht „gesperrt"** heißt. `pause()`
beschreibt einen Zustand, den der Nutzer im nächsten Moment zurücknehmen darf.
Wer eine Ressource exklusiv braucht, muss sie sich nehmen — und zwar an der
Stelle, die tatsächlich schreibt. Gesperrte Knöpfe sind nur die
Höflichkeitsform; Tastenkürzel gehen an ihnen vorbei.

## Was BUG-023 dem Muster hinzufügt (2026-09-10)

BUG-020 hielt fest: *„Ein Filter, der nie greift, meldet sich nicht."*
BUG-021: *„Ein Detektor, der nie anschlägt, meldet sich nicht."*
BUG-023 ist die Stufe davor — **eine Funktion, die nie läuft, meldet sich
ebenfalls nicht.** Sie war gebaut, committet, gepusht, und daneben standen 795
grüne Tests.

Neu ist die Rolle der **stillen Wächterklausel**. `if frame is None: return`
sieht aus wie Sorgfalt und ist in Wahrheit eine Wette: darauf, dass dieser
Zustand irgendwann eintritt. Trat er nie ein, war der ganze Rumpf toter Code —
und ein zweiter, viel banalerer Fehler (`resolve_path` statt `resolve`) wurde
davon *konserviert*, statt beim ersten Start aufzufliegen.

Und die Frage, die bei jedem Qt-Signal zu stellen ist: **Wann genau feuert es?**
`opened` klingt nach „bereit" und kommt doch, bevor der erste Frame existiert.
Ein Signalname ist keine Zusage über den Zustand.

Prüfmuster daraus: Wer einen Rechenkern testet, hat noch nicht getestet, dass
ihn jemand aufruft. Die Verdrahtung braucht ihren eigenen Test.
