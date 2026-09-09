/**
 * Ableitungslogik des Livetickers -- reine Funktionen, kein DOM, kein Netz.
 *
 * WARUM DIESE DATEI GETRENNT LIEGT
 *
 * Die Datenbank liefert bewusst nur GEMESSENES: Bahn, Anzahl gefallener Kegel,
 * welche Kegel, Zeitpunkt. Wurfnummer, laufende Summe und Fehlwurfzahl stehen
 * dort NICHT (siehe docs/SUPABASE_SETUP.md) -- genau diese abgeleiteten
 * Groessen sind in der Bilderkennung dreimal schiefgegangen.
 *
 * Sie entstehen deshalb HIER, auf der Seite, die die Spielregeln kennt. Damit
 * das nachpruefbar bleibt, ist diese Datei frei von Oberflaeche und Netzzugriff
 * und wird von test/ticker.test.js durchgemessen.
 */

/**
 * Kegel-Raute: Kegelnummer -> [Spalte 0..4, Zeile 0..4].
 *
 * Zeile 0 ist HINTEN, Zeile 4 ist VORN -- so, wie die Kamera die Bahn sieht.
 * Kegel 1 steht vorn, Kegel 9 hinten. Identisch zu PIN_LAYOUT in
 * src/kegel_cv/gui/lane_panel.py, damit beide Anwendungen dasselbe Bild zeigen.
 *
 *          9
 *       7     8
 *    4    5     6
 *       2     3
 *          1
 */
export const PIN_LAYOUT = {
    9: [2, 0],
    7: [1, 1], 8: [3, 1],
    4: [0, 2], 5: [2, 2], 6: [4, 2],
    2: [1, 3], 3: [3, 3],
    1: [2, 4],
};

export const ALL_PINS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

/** Welche Kegel stehen geblieben sind -- die Gegenmenge der gefallenen. */
export function standingPins(fallen) {
    const down = new Set(fallen || []);
    return ALL_PINS.filter((pin) => !down.has(pin));
}

/** Der Koenig in der Mitte der Raute. */
export const KOENIG = 5;

export const PHASE_VOLLEN = "vollen";
export const PHASE_ABRAEUMEN = "abraeumen";

/** Wuerfe in die Vollen je Satz, und Wuerfe je Spiel. */
export const VOLLEN_WUERFE = 15;
export const SPIEL_WUERFE = 30;

/**
 * In die Vollen oder ins Abraeumen? -- nach dem regulaeren Rhythmus.
 *
 * Vom Nutzer festgelegt (2026-09-07): Wuerfe 1 bis 15 gehen in die Vollen, 16
 * bis 30 ins Abraeumen, danach beginnt es von vorn. Ueberschreiben laesst sich
 * das je Bahn von Hand -- die Anlage haelt sich nicht immer daran, und der
 * Abschnitt kann mitten in einem Spiel beginnen.
 */
export function automaticPhase(throwNumber, vollen = VOLLEN_WUERFE,
                               spiel = SPIEL_WUERFE) {
    const imSpiel = ((throwNumber - 1) % spiel) + 1;
    return imSpiel <= vollen ? PHASE_VOLLEN : PHASE_ABRAEUMEN;
}

/**
 * Stellt die Anlage nach diesem Bild neu auf?
 *
 * Ja, wenn nichts mehr steht -- und ebenso, wenn nur noch der Koenig steht.
 * Den zweiten Fall hat der Nutzer ergaenzt (2026-09-07); er folgt nicht aus
 * der ersten Regel und stand in keiner Projektunterlage.
 */
export function needsFreshPicture(standing) {
    if (standing.length === 0) return true;
    return standing.length === 1 && standing[0] === KOENIG;
}

/**
 * Zeitpunkt eines Wurfs in Millisekunden.
 *
 * Faellt der Zeitstempel aus, ist 0 die ehrlichere Antwort als "jetzt": Der
 * Wurf rutscht dann an den Anfang und faellt auf, statt sich unbemerkt ans Ende
 * zu setzen.
 */
export function throwTime(row) {
    const ms = Date.parse(row.recorded_at);
    return Number.isNaN(ms) ? 0 : ms;
}

/**
 * Sortiert nach Zeitpunkt, bei Gleichstand nach der laufenden `id`.
 *
 * Die id allein genuegt nicht: Nach einem Netzausfall liefert die Erkennung
 * gepufferte Wuerfe nach, die bekommen dann hohe ids bei alten Zeitstempeln.
 * Massgeblich ist, wann geworfen wurde.
 */
function compareThrows(a, b) {
    return throwTime(a) - throwTime(b) || (a.id ?? 0) - (b.id ?? 0);
}

/**
 * Fuehrt die Wuerfe EINER Bahn und die vom Nutzer gesetzten Abschnitte.
 *
 * Ein Abschnitt ist ein Start/Stopp-Paar. Abschnitt 0 bedeutet "ausserhalb" --
 * das Warmwerfen und alles nach einem Stopp. Diese Wuerfe werden angezeigt und
 * in die CSV geschrieben, aber NICHT gezaehlt: Das Warmwerfen soll sichtbar
 * bleiben, ohne das Ergebnis zu verfaelschen.
 */
export class LaneTicker {
    constructor(lane) {
        this.lane = lane;
        this.throws = [];
        this.segments = [];
        this._seen = new Set();
        // Handmarken fuer die Spielphase: {fromThrow, phase}. `phase: null`
        // heisst "ab hier wieder automatisch". Sortiert nach `fromThrow`.
        this.phaseMarks = [];
        // Korrekturen des Nutzers, nach Wurf-id: {pins, note}.
        //
        // Sie aendern die DATENBANK NICHT -- dort steht, was gemessen wurde,
        // und das bleibt so. Die Korrektur wirkt nur hier und in der CSV, wo
        // beides nebeneinander steht: das Gemessene und das, was der Nutzer
        // gesehen hat. Genau diese Trennung ist der Zweck.
        this.corrections = {};
    }

    /** Setzt die Phase ab einer Wurfnummer von Hand. `phase: null` = automatisch. */
    setPhase(fromThrow, phase) {
        this.phaseMarks = this.phaseMarks.filter((m) => m.fromThrow !== fromThrow);
        this.phaseMarks.push({ fromThrow, phase });
        this.phaseMarks.sort((a, b) => a.fromThrow - b.fromThrow);
    }

    /** Welche Phase gilt fuer diese Wurfnummer -- Handmarke schlaegt Automatik. */
    phaseAt(throwNumber) {
        let gesetzt = null;
        for (const mark of this.phaseMarks) {
            if (mark.fromThrow <= throwNumber) gesetzt = mark.phase;
        }
        return gesetzt ?? automaticPhase(throwNumber);
    }

    /**
     * Haelt fest, was der Nutzer stattdessen gesehen hat.
     *
     * `pins` ist die Liste der wirklich gefallenen Kegel; `null` nimmt die
     * Korrektur zurueck. Die Datenbank bleibt unberuehrt.
     */
    correct(id, pins, note = "") {
        if (id === null || id === undefined) return;
        if (pins === null) {
            delete this.corrections[id];
            return;
        }
        this.corrections[id] = {
            pins: [...new Set(pins)].filter((p) => ALL_PINS.includes(p))
                .sort((a, b) => a - b),
            note: String(note || ""),
        };
    }

    /**
     * Nimmt Zeilen aus der Datenbank auf und meldet, wie viele neu waren.
     *
     * Doppelte werden an der `id` erkannt. Das ist noetig, weil sich die
     * Abfragefenster ueberlappen duerfen -- lieber eine Zeile zweimal holen als
     * eine verpassen.
     */
    ingest(rows) {
        let added = 0;
        for (const row of rows || []) {
            if (row.lane !== this.lane) continue;
            const key = row.id ?? `${row.recorded_at}|${row.pins_count}`;
            if (this._seen.has(key)) continue;
            this._seen.add(key);
            this.throws.push(row);
            added += 1;
        }
        if (added) this.throws.sort(compareThrows);
        return added;
    }

    /** Der laufende Abschnitt, oder null, wenn gerade keiner offen ist. */
    get openSegment() {
        const last = this.segments[this.segments.length - 1];
        return last && last.stop === null ? last : null;
    }

    get running() {
        return this.openSegment !== null;
    }

    /** Oeffnet einen neuen Abschnitt. Ein bereits offener wird zuvor beendet. */
    start(atMs) {
        if (this.openSegment) this.stop(atMs);
        this.segments.push({ nr: this.segments.length + 1, start: atMs, stop: null });
        return this.segments[this.segments.length - 1];
    }

    /** Schliesst den laufenden Abschnitt. Ohne offenen Abschnitt passiert nichts. */
    stop(atMs) {
        const open = this.openSegment;
        if (!open) return null;
        open.stop = atMs;
        return open;
    }

    /** Nummer des Abschnitts, in den dieser Zeitpunkt faellt -- 0 = ausserhalb. */
    segmentOf(ms) {
        for (const seg of this.segments) {
            if (ms >= seg.start && (seg.stop === null || ms <= seg.stop)) return seg.nr;
        }
        return 0;
    }

    /**
     * Alle Wuerfe als Anzeigezeilen, aelteste zuerst.
     *
     * Die Wurfnummer zaehlt INNERHALB des Abschnitts. Wuerfe ausserhalb bekommen
     * keine -- eine Nummer zu vergeben hiesse zu behaupten, sie gehoerten dazu.
     */
    rows() {
        const counter = new Map();
        // Das stehende Bild je Abschnitt. Im Abraeumen wird in das geworfen,
        // was uebrig geblieben ist -- in die Vollen steht immer alles.
        const bild = new Map();

        return this.throws.map((row) => {
            const ms = throwTime(row);
            const segment = this.segmentOf(ms);
            let number = null;
            if (segment > 0) {
                number = (counter.get(segment) || 0) + 1;
                counter.set(segment, number);
            }

            const gemessen = [...(row.pins || [])].sort((a, b) => a - b);
            const korrektur = row.id !== null && row.id !== undefined
                ? this.corrections[row.id] : undefined;
            const fallen = korrektur ? korrektur.pins : gemessen;

            // Ausserhalb eines Abschnitts (Warmwerfen) wird nicht Buch gefuehrt:
            // Dort ist kein Spielstand bekannt, also gilt das volle Bild.
            const phase = number === null ? PHASE_VOLLEN : this.phaseAt(number);

            const stehendVorher = phase === PHASE_ABRAEUMEN
                ? (bild.get(segment) || ALL_PINS)
                : ALL_PINS;

            // Faellt ein Kegel, der laut unserem Bild gar nicht mehr stand, ist
            // etwas nicht in Ordnung -- meist fehlt ein Wurf. Das wird GEZEIGT
            // und das Bild zurueckgesetzt, statt still weiterzurechnen.
            const vorher = new Set(stehendVorher);
            const conflict = fallen.some((p) => !vorher.has(p));
            const basis = conflict ? ALL_PINS : stehendVorher;

            const weg = new Set(fallen);
            const standing = basis.filter((p) => !weg.has(p));
            const fresh = needsFreshPicture(standing);
            if (segment > 0) {
                bild.set(segment, phase === PHASE_VOLLEN || fresh
                    ? ALL_PINS : standing);
            }

            return {
                id: row.id ?? null,
                lane: this.lane,
                time: ms,
                segment,
                throwNumber: number,
                phase,
                value: fallen.length,
                fallen,
                measured: gemessen,
                corrected: Boolean(korrektur),
                note: korrektur ? korrektur.note : "",
                before: basis,          // das Bild, in das geworfen wurde
                standing,               // was danach noch steht
                gone: ALL_PINS.filter((p) => !basis.includes(p)),
                conflict,
                freshPicture: fresh,
                miss: fallen.length === 0,
                videoTime: row.video_time_s ?? null,
            };
        });
    }

    /**
     * Kennzahlen eines Abschnitts: Gesamtsumme, Fehlwuerfe, Anzahl Wuerfe.
     *
     * Ein Fehlwurf ist ein Wurf mit null Kegeln -- abgeleitet, nicht gemeldet.
     * Ohne Angabe gilt der zuletzt geoeffnete Abschnitt; gab es noch keinen,
     * bleiben alle Zahlen bei null, statt heimlich das Warmwerfen mitzuzaehlen.
     */
    stats(segmentNr) {
        const nr = segmentNr ?? (this.segments.length ? this.segments.length : 0);
        const rows = nr > 0 ? this.rows().filter((r) => r.segment === nr) : [];
        const total = rows.reduce((sum, r) => sum + r.value, 0);
        return {
            segment: nr,
            total,
            misses: rows.filter((r) => r.miss).length,
            count: rows.length,
            average: rows.length ? total / rows.length : 0,
        };
    }

    /** Der zuletzt geworfene Wurf der Bahn -- auch wenn er ausserhalb liegt. */
    latest() {
        const rows = this.rows();
        return rows.length ? rows[rows.length - 1] : null;
    }
}

/** Ortszeit als `TT.MM.JJJJ HH:MM:SS` -- das Format, das Excel hier erwartet. */
export function formatLocal(ms) {
    const d = new Date(ms);
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} `
         + `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/** Nur die Uhrzeit -- fuer die Tabelle, wo das Datum nur Platz kostet. */
export function formatClock(ms) {
    const d = new Date(ms);
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/** Feld fuer die CSV absichern: Trennzeichen und Anfuehrungszeichen entschaerfen. */
function csvField(value) {
    const text = value === null || value === undefined ? "" : String(value);
    return /[;"\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export const CSV_HEADER = [
    // Was gilt -- also mit Korrektur, falls eine gesetzt wurde.
    "Zeitpunkt", "Bahn", "Abschnitt", "Wurfnummer", "Wert",
    "Gefallene Kegel", "Stehende Kegel", "Fehlwurf", "VideoZeit", "Id",
    // Bild und Phase.
    "Phase", "Bild vorher", "Neues Bild",
    // Die Spur der Korrektur: Was die Erkennung GEMESSEN hat, bleibt erhalten.
    // Ohne diese drei Spalten waere hinterher nicht mehr zu sehen, wo ein
    // Mensch eingegriffen hat -- und genau das ist die interessante Stelle.
    "Korrigiert", "Gemessen Wert", "Gemessene Kegel", "Bemerkung",
    "Widerspruch",
];

/**
 * Baut die vollstaendige CSV einer Bahn.
 *
 * Geschrieben werden ALLE Wuerfe, auch die ausserhalb der Abschnitte. Die
 * Spalte `Abschnitt` haelt sie auseinander (0 = Warmwerfen bzw. nach Stopp).
 * Wegzulassen, was nicht gezaehlt wird, hiesse Messwerte zu verlieren, die sich
 * spaeter nicht wiederbeschaffen lassen.
 *
 * Trennzeichen ist das Semikolon und die Dezimalstelle ein Komma: So oeffnet
 * die Datei sich hierzulande in Excel ohne Importdialog.
 */
export function csvText(rows) {
    const lines = [CSV_HEADER.join(";")];
    for (const r of rows) {
        lines.push([
            formatLocal(r.time),
            r.lane,
            r.segment,
            r.throwNumber ?? "",
            r.value,
            r.fallen.join(" "),
            r.standing.join(" "),
            r.miss ? "ja" : "nein",
            r.videoTime === null ? "" : String(r.videoTime).replace(".", ","),
            r.id ?? "",
            r.phase === PHASE_ABRAEUMEN ? "Abraeumen" : "Vollen",
            r.before.join(" "),
            r.freshPicture ? "ja" : "nein",
            r.corrected ? "ja" : "nein",
            r.corrected ? r.measured.length : "",
            r.corrected ? r.measured.join(" ") : "",
            r.note || "",
            r.conflict ? "ja" : "nein",
        ].map(csvField).join(";"));
    }
    // Abschliessender Zeilenumbruch: Ohne ihn haengt beim naechsten Schreiben
    // die erste neue Zeile an der letzten alten.
    return lines.join("\r\n") + "\r\n";
}

/**
 * Wie viele Bahnen gleichzeitig gezeigt werden duerfen.
 *
 * Vom Nutzer vorgegeben: im Hochformat eine, auf kleinen Querformat-Schirmen
 * zwei. Auf grossen Schirmen alle gewaehlten.
 */
export function maxVisible(width, height, largeThreshold = 1100) {
    if (height > width) return 1;
    return width < largeThreshold ? 2 : 4;
}

/**
 * Welche Bahnen tatsaechlich sichtbar sind.
 *
 * `focus` ist die Bahn, die der Nutzer zuletzt ausgewaehlt hat -- sie bleibt
 * auch dann im Bild, wenn der Platz nur noch fuer eine reicht. Sonst waere die
 * Auswahl auf dem Handy wirkungslos.
 */
export function visibleLanes(selected, max, focus) {
    const lanes = [...selected].sort((a, b) => a - b);
    if (lanes.length <= max) return lanes;
    const startAt = lanes.indexOf(focus);
    if (startAt < 0) return lanes.slice(0, max);
    // Ab der Fokusbahn fuellen und bei Bedarf vorne ergaenzen, damit immer
    // genau `max` Bahnen im Bild stehen.
    const chosen = lanes.slice(startAt, startAt + max);
    const missing = max - chosen.length;
    return missing > 0 ? lanes.slice(startAt - missing, startAt).concat(chosen) : chosen;
}
