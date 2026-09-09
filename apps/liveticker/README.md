# Liveticker

Zeigt die erkannten Würfe, während gespielt wird. Liest sie aus der
Supabase-Tabelle `throws`, die die Bilderkennung befüllt, und schreibt sie
nebenher als CSV — eine Datei je Bahn.

Reine Browser-Anwendung. Kein Backend, keine Bibliotheken, kein Bauschritt —
zum Veröffentlichen lässt sich alles auf Wunsch zu **einer** HTML-Datei
zusammenlegen (`build.py`), nötig ist das für den Betrieb aber nicht.

---

## Starten

```bash
.venv/Scripts/python.exe apps/liveticker/start.py
```

Das öffnet <http://localhost:8000/>. `start.py` ist **kein Server der
Anwendung** — es liest nur Projekt-URL und Schlüssel aus `config/default.yaml`
und `.env`, legt sie als `config.local.js` daneben und liefert das Verzeichnis
aus.

Der Umweg über `localhost` ist nötig, nicht bequem: Über `file://` verweigert
der Browser sowohl die Abfrage an Supabase (fremder Ursprung) als auch das
Schreiben in einen Ordner (kein sicherer Kontext).

| Schalter | wofür |
|---|---|
| `--port 8080` | anderer Port, falls 8000 belegt ist |
| `--bahnen 2,3,4,5` | Vorbelegung der Bahnnummern |
| `--lan` | auch vom Handy im selben WLAN erreichbar |
| `--kein-browser` | Browser nicht automatisch öffnen |

> `--lan` macht den Schlüssel für jeden im selben Netz lesbar. Es ist der
> öffentliche (publishable) Schlüssel, der ohnehin in jeder lesenden Anwendung
> steht — aber es ist eine bewusste Entscheidung, keine Nebensache.

---

## Was die Datenbank liefert — und was nicht

`throws` enthält **nur Gemessenes**:

| Spalte | |
|---|---|
| `lane` | Bahnnummer |
| `pins_count` | Anzahl gefallener Kegel |
| `pins` | welche Kegel (1..9) |
| `recorded_at` | Zeitpunkt |

**Wurfnummer, laufende Summe und Fehlwurfzahl stehen dort nicht.** Das war eine
ausdrückliche Festlegung (2026-08-26, siehe `docs/SUPABASE_SETUP.md`): Genau
diese abgeleiteten Größen sind in der Bilderkennung dreimal schiefgegangen — die
Wurfnummer der Tafel löschte 28 % der Würfe, die Spielerkennung traf den
Bahnwechsel nicht, die laufende Summe driftete ab, sobald ein Wurf fehlte.

Sie entstehen deshalb **hier**, auf der Seite, die die Spielregeln kennt:

- **Wurfnummer** — laufend innerhalb eines Abschnitts, beginnt bei 1
- **Gesamtsumme** — Summe der gefallenen Kegel des Abschnitts
- **Fehlwürfe** — Würfe mit null Kegeln, abgeleitet aus `pins_count == 0`

Die ganze Rechnung steht in [`ticker.js`](ticker.js), ohne Oberfläche und ohne
Netzzugriff, und ist in [`test/ticker.test.js`](test/ticker.test.js) belegt.

---

## Bedienung

### Würfe ab

Zeitpunkt, ab dem gelesen wird. Vorgabe ist heute 00:00 Uhr. `jetzt` und
`heute` setzen ihn schnell. Ändern lädt die Liste neu — die gesetzten
Abschnitte bleiben erhalten.

### Bahnen

Ein Tipp auf einen Chip wählt die Bahn aus und holt sie ins Bild. Ein zweiter
Tipp auf die bereits sichtbare Bahn nimmt sie wieder heraus.

| Chip | Bedeutung |
|---|---|
| gefüllt | steht gerade im Bild |
| umrandet | ausgewählt, aber kein Platz |
| grau | nicht ausgewählt |

Wie viele Bahnen gleichzeitig passen, entscheidet das Format:

| | |
|---|---|
| Hochformat | **1 Bahn** |
| kleines Querformat (< 1100 px) | **2 Bahnen** |
| großer Schirm | alle ausgewählten |

Taucht in den Daten eine Bahn auf, die nicht in der Liste steht, wird sie
selbsttätig ergänzt — sonst bliebe sie unsichtbar.

### Start / Stopp — Warmwerfen vom Spiel trennen

Jede Bahn hat ihren eigenen Start/Stopp, dazu gibt es „alle starten" und „alle
stoppen". Getrennt je Bahn, weil das Warmwerfen nicht überall gleichzeitig
endet — und weil die vier Bahnen in diesem Projekt grundsätzlich unabhängig
geführt werden.

- **Vor dem ersten Start** läuft das Warmwerfen. Die Würfe werden **gezeigt**
  (gedämpft, ohne Nummer) und in die CSV geschrieben, aber **nicht gezählt**.
- **Start** öffnet einen Abschnitt. Ab hier zählen Wurfnummer und Summe.
- **Stopp** schließt ihn. Spätere Würfe zählen wieder nicht mit.
- **Erneutes Start** öffnet einen **neuen** Abschnitt, Wurfnummer wieder ab 1.
  So lassen sich mehrere Spiele hintereinander führen.

Die Abschnittsmarken überstehen ein Neuladen der Seite — ein versehentliches F5
mitten im Spiel kostet die Startmarke nicht.

### Vollen und Abräumen — das Bild wird mitgeführt

Ab Wurf 16 wird **in das stehende Bild geworfen**: Was vorher liegen blieb,
liegt weiter. Die Datenbank weiß davon nichts — dort steht nur, welche Kegel
gefallen sind. Der Ticker schreibt das Bild deshalb selbst fort.

Die Raute zeigt dafür **drei** Zustände:

| | |
|---|---|
| voll eingefärbt | in **diesem** Wurf gefallen |
| dunkel gefüllt | stand vorher und steht noch |
| gestrichelter Umriss | lag schon vor diesem Wurf |

**Der Rhythmus** ist Wurf 1–15 Vollen, 16–30 Abräumen, dann von vorn. Der
Knopf im Kartenkopf zeigt, was für den **nächsten** Wurf gilt, und schaltet auf
Klick um — nötig, wenn der Abschnitt mitten in einem Spiel beginnt. Ist von
Hand geschaltet, ist der Knopf ausgefüllt und ein `auto` daneben stellt den
Rhythmus wieder her. Die Marke gilt **ab dem nächsten Wurf**; rückwirkend würde
sich das Bild bereits gezeigter Würfe unter der Hand verschieben.

**Neu aufgestellt** wird, wenn nichts mehr steht — und ebenso, wenn nur noch
der König (Kegel 5) steht. Die zweite Regel folgt nicht aus der ersten; sie
stammt vom Nutzer (2026-09-07).

**Widerspruch:** Fällt ein Kegel, der laut Bild gar nicht mehr stand, bekommt
die Zeile ein rotes `?` und das Bild wird auf neun zurückgesetzt. Meist fehlt
dann ein Wurf. Häufen sich die Markierungen, stimmt die Phase nicht — dann von
Hand umschalten.

### Korrigieren — ohne die Datenbank anzufassen

Eine Zeile anklicken öffnet den Korrekturdialog. Dort wird angeklickt, welche
Kegel **wirklich** gefallen sind, dazu wahlweise eine Bemerkung.

**Die Datenbank bleibt unberührt.** Dort steht, was gemessen wurde, und das
bleibt so. Die Korrektur wirkt nur in der Anzeige, in den Kennzahlen, im
weitergeführten Bild — und in der CSV, wo **beides nebeneinander** steht:

| Spalte | |
|---|---|
| `Wert`, `Gefallene Kegel` | was gilt (also korrigiert, falls korrigiert) |
| `Korrigiert` | `ja` / `nein` |
| `Gemessen Wert`, `Gemessene Kegel` | was die Erkennung gemeldet hat |
| `Bemerkung` | der freie Text |

Ohne diese Trennung wäre hinterher nicht mehr zu sehen, wo ein Mensch
eingegriffen hat — und genau das ist die interessante Stelle, wenn man die
Erkennung verbessern will.

Korrekturen und Phasenmarken überstehen ein Neuladen.

### CSV

`Ordner wählen` einmal drücken, danach schreibt die App bei jedem neuen Wurf
selbsttätig `bahn_2.csv`, `bahn_3.csv` und so weiter.

Geschrieben wird jedes Mal die **vollständige** Datei, nicht angehängt. Das
kostet bei ein paar hundert Zeilen nichts und hat einen Vorteil, der den
Aufwand wert ist: Nach einem Neuladen stellt der nächste Schreibvorgang die
Datei vollständig wieder her, statt eine halbe fortzuschreiben.

| Spalte | |
|---|---|
| `Zeitpunkt` | Ortszeit |
| `Bahn` | Bahnnummer |
| `Abschnitt` | 0 = Warmwerfen bzw. nach einem Stopp |
| `Wurfnummer` | leer außerhalb eines Abschnitts |
| `Wert` | Anzahl gefallener Kegel |
| `Gefallene Kegel` | z. B. `1 3 5` |
| `Stehende Kegel` | die Gegenmenge |
| `Fehlwurf` | `ja` / `nein` |
| `VideoZeit`, `Id` | Herkunft, zum Nachschlagen |
| `Phase` | `Vollen` oder `Abraeumen` |
| `Bild vorher` | worauf geworfen wurde |
| `Neues Bild` | `ja`, wenn danach neu aufgestellt wurde |
| `Korrigiert`, `Gemessen Wert`, `Gemessene Kegel`, `Bemerkung` | die Korrekturspur |
| `Widerspruch` | `ja`, wenn ein Kegel fiel, der nicht mehr stand |

Semikolon als Trennzeichen, Komma als Dezimalstelle, BOM voran — damit die
Datei sich hierzulande ohne Importdialog in Excel öffnet.

**Den Ordner können nur Chrome und Edge.** In Firefox und Safari bleibt der Weg
über `herunterladen`; ein Hinweis erscheint, statt still nichts zu tun.

### Adresse mit Parametern

```
http://localhost:8000/?ab=2026-09-07T19:00&bahnen=2,3
```

---

## Als eine einzige Datei veröffentlichen

```bash
.venv/Scripts/python.exe apps/liveticker/build.py --bahnen 2,3,4,5
```

Ergebnis: `dist/index.html` — rund 47 KB, CSS und JavaScript eingebettet, keine
externen Verweise. Läuft überall, wo sie über `http(s)` ausgeliefert wird:
GitHub Pages, ein Netzlaufwerk, ein beliebiger Webspace.

**Projekt-URL und Schlüssel sind fest eingebaut.** Die Seite verbindet sich
sofort; einzustellen sind nur noch die **Bahnnummern** — der Knopf oben rechts
heißt dann „Bahnen" und der Dialog zeigt auch nur die.

Die Bahnvorgabe steckt in `--bahnen`. Ändern lässt sie sich jederzeit in der
Seite selbst; die Auswahl überlebt ein Neuladen.

Wer die fragende Fassung will: `--ohne-schluessel`.

### Warum das vertretbar ist

Der eingebaute Schlüssel ist für jeden lesbar, der die Datei öffnet. Genau
dafür ist ein *publishable key* gedacht — **aber nur, solange `anon` auf der
Tabelle wirklich nur lesen darf.**

Seit dem 2026-09-07 ist das der Fall (RLS-Regel plus `revoke insert, update,
delete`). Nachgemessen: Lesen liefert HTTP 206, ein Schreibversuch mit
demselben Schlüssel HTTP 401 `42501 permission denied`. Die Daten sind anonym —
Bahn, Kegel, Zeitpunkt, es steht niemand darin.

**Würde diese Beschränkung je zurückgenommen, dürfte die Datei nicht mehr
öffentlich liegen.** Prüfen:

```sql
select relrowsecurity from pg_class where relname = 'throws';
```

Der **geheime** Schlüssel wird nie eingebaut: `build.py` nimmt
`SUPABASE_READ_KEY` mit Vorrang und bricht ab, sobald der Wert nach
`sb_secret_` oder `service_role` aussieht.

### Zur Bauweise

Die Modultrennung bleibt die **Quelle**, die eine Datei ist nur das Erzeugnis.
`ticker.js` enthält die Wurfnummern-, Summen- und Fehlwurfrechnung und wird
einzeln durchgemessen; ein Bündel ließe sich so nicht prüfen. `build.py` prüft
vor dem Zusammenlegen, dass kein Name doppelt vergeben ist — sonst überschriebe
beim Verketten still das eine das andere.

---

## Was wo steht

| Datei | |
|---|---|
| `ticker.js` | Wurfnummer, Summen, Abschnitte, CSV — **rein und getestet** |
| `feed.js` | Abfrage an Supabase (PostgREST) |
| `app.js` | Oberfläche, CSV-Schreiben, Speichern der Einstellungen |
| `start.py` | Vorbelegung erzeugen, Verzeichnis ausliefern |
| `build.py` | alles zu einer einzigen HTML-Datei zusammenlegen |

### Tests

```bash
node --test apps/liveticker/test/ticker.test.js
```

Geprüft wird die Ableitungslogik: Wurfnummer je Abschnitt, Warmwerfen zählt
nicht, Fehlwurf bei null Kegeln, nachgelieferte Würfe nach Zeitpunkt statt nach
`id`, CSV-Format, Bahnenzahl je Bildschirmformat.

---

## Warum abgefragt und nicht abonniert

Supabase kann Realtime, und die Tabelle ist dafür freigeschaltet. Der Ticker
fragt trotzdem alle 1,5 Sekunden nach. Ein Abonnement muss nach jedem Funkloch,
jedem Standby und jedem Netzwechsel neu aufgebaut werden und merkt selbst nicht
zuverlässig, dass es taub geworden ist. Eine Abfrage heilt sich von selbst: Die
nächste Runde holt nach, was die vorige verpasst hat.

Gelesen wird dabei nach `id`, nicht nach Zeitstempel. Nach einem Netzausfall
liefert die Erkennung gepufferte Würfe nach — die haben alte Zeitstempel, aber
neue `id`. Nach Zeit zu lesen würde sie überspringen.

---

## Grenzen

- **Die Kegelnummern sind eine Zuordnung, keine Messung.** Die Raute ist
  identisch zu `src/kegel_cv/gui/lane_panel.py` (Kegel 1 vorn, Kegel 9 hinten).
  Dass die Tafel die Raute nicht zusätzlich seitenverkehrt zeigt, ist bislang
  nur angenommen — siehe `calibration.pin_number_mapping`. Die **Anzahl** ist
  davon nicht berührt, nur die Namen.
- **Stehende Kegel gelten je Wurf**, gebildet als Gegenmenge der gefallenen.
  Über mehrere Würfe hinweg fortgeschrieben wird nichts.
- Der Ordner für die CSV muss nach einem Neuladen erneut gewählt werden. Die
  Daten gehen dabei nicht verloren — sie stehen in der Datenbank, und der
  nächste Schreibvorgang stellt die Datei vollständig wieder her.
