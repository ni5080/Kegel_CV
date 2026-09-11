# Kegel_CV — automatische Kegelerfassung aus Video

Lokale Desktop-Anwendung, die aus einem Kegelbahn-Video oder Livestream jeden
Wurf selbst erfasst: **welche Kegel gefallen sind, wie viele, auf welcher Bahn,
wann.** Gelesen wird die Anzeigetafel der Anlage (FUNK), nicht die Kegel selbst.

Leitgedanke: **robust, nachvollziehbar und debugbar** — nicht „möglichst viel
KI". Jedes Ergebnis trägt seine Herkunft mit sich: Frames, Messwerte,
Entscheidungen.

---

## Was dabei herauskommt

Gemessen gegen ein von Hand geführtes Wurfprotokoll (480 Würfe, 4 Bahnen,
52 Minuten):

| Bahn | erfasst | richtig |
|---|---|---|
| 2 | 100 % | **100 %** |
| 3 | 100 % | **100 %** |
| 4 | 100 % | **100 %** |
| 5 | 100 % | 98,3 % |
| **alle** | **100 %** | **99,6 %** |

Alle sechzehn Sätze aufs Kegel genau (3224 gegen 3224). Die zwei Abweichungen
liegen im Protokoll, nicht im Werkzeug — vom Autor des Protokolls bestätigt.

Verarbeitung: rund 20–29 ms je Frame bei 40 ms Budget, also echtzeitfähig.

---

## Schnellstart

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
```

```bash
.venv/Scripts/python.exe -m kegel_cv.main
```

Optional direkt mit einem Video oder einer Kalibrierung:

```bash
.venv/Scripts/python.exe -m kegel_cv.main --video "kegelVideos/spiel.mp4" --calibration data/calibrations/meine.json
```

Als Quelle geht auch eine **Adresse**: HLS (`.m3u8`), RTSP, oder ein
YouTube-Link — der wird mit `yt-dlp` aufgelöst.

Tests:

```bash
.venv/Scripts/python.exe -m pytest tests -q
```

**Ohne Datenbank läuft alles.** Der Versand ist der einzige Teil, der
Zugangsdaten braucht; fehlen sie, meldet das Werkzeug es einmal im Protokoll
und wertet weiter aus.

---

## Bedienung in vier Schritten

### 1. Quelle laden

Video aus der Liste wählen und **Laden**, oder eine Adresse in das Stream-Feld
eintragen.

| Taste | Wirkung |
|---|---|
| `Leertaste` | Wiedergabe / Pause |
| `→` / `←` | ein Frame vor / zurück |
| `Esc` | laufenden Kalibrierschritt abbrechen |

### 2. Automatisch kalibrieren

**Automatisch kalibrieren** zeigt die bekannten Kegelboard-Bauarten als Bilder.
Eine anklicken — der Rest folgt aus dem Musterbild: Tafelecken, neun
Kegellampen, grüne Lampe, alle Ziffernfelder.

Danach wird gefragt, ob die Rahmen sitzen (mit Bild), und welche Bahnnummern
die Tafeln von links nach rechts haben.

Steht die Anlage noch nicht in der Bibliothek: eine Tafel von Hand vermessen
(**Geführt kalibrieren**) und über **Neues Board aufnehmen** dauerhaft merken.
Danach findet das Werkzeug diese Bauart überall wieder — auch in einer anderen
Halle.

### 3. Nachkalibrieren, falls eine Tafel nicht sitzt

**Nachkalibrieren** anklicken, dann die betroffene Tafel im Bild. Sie erscheint
entzerrt und groß; dort lassen sich alle Bereiche ziehen:

- **Mitte ziehen** verschiebt, **Rand ziehen** ändert die Größe
- **Pfeiltasten** verschieben um genau einen Tafelpixel
- **Abbrechen** bleibt folgenlos, es wird auf Kopien gearbeitet

Die Bereiche liegen auch im Livebild und lassen sich dort direkt anfassen —
während der Analyse ebenso, die Änderung wird beim nächsten Frame übernommen.

### 4. Analyse starten

Die Wurftabellen füllen sich live, je Bahn eine. Unter jeder steht, was der
Ziffernleser gerade liest — grau, wenn er unsicher ist.

Jeder Lauf legt unter `debug/<quelle>/lauf_<zeit>/` ab: `wuerfe.csv`,
`gruenspur.csv`, `lampenspur.csv`, Zyklusblätter und die Bildbelege je Ereignis.

---

## Datenbank (optional)

Jeder erkannte Wurf kann sofort als Zeile an eine **Supabase**-Tabelle gehen,
damit ein Ticker oder der Spielleiter live mitliest.

### Zugangsdaten

`.env.example` nach `.env` kopieren und ausfüllen. Die Datei bleibt lokal
(`.gitignore`), die Konfiguration enthält **weder Adresse noch Schlüssel**:

```
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_KEY=sb_secret_...            # schreibend, für die Bilderkennung
SUPABASE_READ_KEY=sb_publishable_...  # lesend, für den Liveticker
```

Dann in `config/default.yaml`:

```yaml
output:
  supabase:
    enabled: true
```

### Die Tabelle anlegen

Im Supabase-Dashboard unter **SQL Editor**:

```sql
create table if not exists throws (
    id            bigint generated always as identity primary key,

    video_id      text,                 -- welche Aufnahme / Übertragung
    lane          int  not null,        -- Bahnnummer laut Anzeigetafel
    pins_count    int  not null,        -- gefallene Kegel in diesem Wurf
    pins          int[],                -- welche Kegel (Nummern 1..9)
    video_time_s  real,                 -- Zeitpunkt im Video
    recorded_at   timestamptz not null default now(),

    -- Der Beleg zum Wert: die eingemessene Anzeigetafel als Base64-JPEG
    board_jpeg        text,
    board_before_jpeg text
);

create index if not exists throws_lane_time on throws (lane, recorded_at desc);
```

Damit Abonnenten sofort benachrichtigt werden (der Liveticker nutzt das):

```sql
alter publication supabase_realtime add table throws;
```

### Rechte: lesen ja, schreiben nein

Der Liveticker läuft im Browser und trägt seinen Schlüssel offen mit sich. Das
ist genau die Aufgabe eines *publishable key* — **aber nur, solange die Rolle
`anon` wirklich nur lesen darf.** Zwei Schichten, beide empfohlen:

```sql
-- 1. Tabellenrechte: anon darf ausschliesslich lesen
revoke insert, update, delete on public.throws from anon;
grant select on public.throws to anon;

-- 2. Row Level Security als zweite Schicht. Ohne die Policy koennte
--    anschliessend NIEMAND mehr lesen -- beides gehoert zusammen.
alter table public.throws enable row level security;

create policy "throws oeffentlich lesbar"
    on public.throws for select
    to anon
    using (true);
```

Der **geheime** Schlüssel (`sb_secret_…`, Rolle `service_role`) umgeht beides —
deshalb schreibt die Bilderkennung weiterhin. Sie läuft lokal und ist kein
Browser; dort ist er richtig aufgehoben.

Nachsehen, ob es greift:

```sql
select relrowsecurity from pg_class where relname = 'throws';

select grantee, privilege_type
  from information_schema.role_table_grants
 where table_name = 'throws' and grantee = 'anon';
```

Und von außen, mit dem öffentlichen Schlüssel — ein Schreibversuch muss
`401` mit Code `42501` liefern:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  "$SUPABASE_URL/rest/v1/throws" \
  -H "apikey: $SUPABASE_READ_KEY" -H "Content-Type: application/json" \
  -d '{"lane":-1,"pins_count":0,"pins":[]}'
```

### Was in der Tabelle steht — und was nicht

**Übertragen wird nur, was gemessen ist:** Bahn, Anzahl Kegel, Kegelnummern,
Zeitstempel. Wurfnummer, laufende Summe, Zyklus, Spielnummer und
Zwischensummen werden zwar berechnet und angezeigt, aber **nicht gesendet**.

Der Grund ist Erfahrung: Genau diese abgeleiteten Größen sind schiefgegangen.
Die aus der Anzeige gelesene Wurfnummer löschte einmal 28 % der Würfe. Alle
setzen Regelwissen voraus — wann ein Bahnwechsel ansteht, wann ein Spiel endet,
wie gewertet wird —, das die auswertende Anwendung besser kennt als eine
Bilderkennung.

Die Spalten `throw_number`, `running_total`, `status`, `cycle` und `game`
existieren aus der Frühzeit noch und sind bei neuen Zeilen **`null`**. Wer
darauf aufbaut, baut auf Sand.

Nützliche Abfragen für eine lesende Anwendung:

```sql
-- Die letzten Würfe, neueste zuerst (ohne die grossen Bildspalten)
select id, lane, pins_count, pins, video_time_s, recorded_at
  from throws
 order by id desc
 limit 50;

-- Gefallene Kegel je Bahn in dieser Übertragung
select lane, count(*) as wuerfe, sum(pins_count) as kegel
  from throws
 where video_id = '...'
 group by lane
 order by lane;

-- Das Tafelbild eines einzelnen Wurfs -- erst auf Anforderung holen,
-- die Spalte ist gross.
select board_jpeg from throws where id = 1234;
```

`recorded_at` ist die Wanduhrzeit des Versands, `video_time_s` die Position in
der Aufzeichnung. Innerhalb eines Laufs sortiert `video_time_s` je `lane`
verlässlicher.

---

## Liveticker

Eine kleine Weboberfläche, die die Tabelle live mitliest:

```bash
.venv/Scripts/python.exe apps/liveticker/start.py --bahnen 2,3,4,5
```

Zum Veröffentlichen als **eine einzige HTML-Datei**, ohne externe Verweise:

```bash
.venv/Scripts/python.exe apps/liveticker/build.py --bahnen 2,3,4,5
```

Beide nehmen `SUPABASE_READ_KEY` mit Vorrang und **brechen ab**, sobald der
Wert nach `sb_secret_` oder `service_role` aussieht. Einzelheiten:
[`apps/liveticker/README.md`](apps/liveticker/README.md).

---

## Wie es arbeitet

```
Video/Stream ─► grüne Lampe (billig, jeder Frame)
                    │  geht sie aus, ist ein Wurf gefallen
                    ▼
               Frames um das Ereignis sammeln
                    │
                    ▼
         9 Kegellampen  +  Ziffernfelder  ─►  Wurf + Beweiskette
```

Vier Grundsätze, die den Aufbau erklären:

- **Billige Trigger steuern teure Analyse.** Kein Frame-für-Frame-ML.
- **Die vier Bahnen sind unabhängig.** Nie synchrone Ereignisse annehmen.
- **Ein einzelner Frame entscheidet nichts.** Ziffern flackern, Lampen blinken
  (gemessen: Periode 28–30 Frames).
- **Widersprüchliche Quellen werden nicht „wegentschieden".** Die Redundanz
  existiert, um Fehler zu zeigen.

Die Kegelzahl kommt aus den **Lampen**, nicht aus den Ziffern; die Ziffern sind
Gegenprobe. Deshalb trägt ein Lesefehler nicht bis ins Ergebnis.

---

## Ordner

```
config/default.yaml    alle Parameter, mit Messbeleg im Kommentar
data/boardtypes/       bekannte Kegelboard-Bauarten (Musterbild + Bereiche)
data/calibrations/     gespeicherte Kalibrierungen
src/kegel_cv/          video/ calibration/ detection/ analysis/ sinks/ gui/
tools/                 Mess- und Prüfwerkzeuge (nicht Teil der Anwendung)
apps/liveticker/       Weboberfläche zum Mitlesen
docs/                  gemessene Fakten, Architektur, offene Fragen
tests/                 über 1000 Tests
```

Nützliche Werkzeuge:

```bash
tools/verify_rois.py              # Bildbeleg der kalibrierten Bereiche
tools/compare_protocol.py         # Lauf gegen ein Wurfprotokoll vergleichen
tools/measure_gruen_trennschaerfe.py   # trennt die grüne Lampe sauber AN/AUS?
tools/measure_lampenmitte.py      # sitzen die Lampen-ROIs auf den Lampen?
```

---

## Stand

Fertig und am Material gemessen: Videoquelle (Datei, Stream, YouTube),
Kalibrierung (automatisch und von Hand), Grün- und Lampenerkennung,
Wurferkennung, Summen und Zyklen, Live-Oberfläche, Versand, Liveticker.

Offen: Die **Ziffernerkennung** liegt bei rund 96 % auf den sicher prüfbaren
Feldern und ist deshalb weiterhin nur Gegenprobe, nicht Quelle. Was sie gerade
liest, steht in der Oberfläche unter jeder Bahn — genau dafür.

Einzelheiten zum Projektzustand: `.claude/skills/ORCHESTRATION.md`.
Gemessene Fakten über das Material: `docs/VIDEO_ANALYSIS.md`.
