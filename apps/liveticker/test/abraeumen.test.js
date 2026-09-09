/**
 * Tests der Bildfuehrung (Vollen / Abraeumen) und der Korrekturen.
 *
 * Die Datenbank sagt nur, WELCHE Kegel gefallen sind -- nie, welche vorher
 * standen. Im Abraeumen wird aber in das stehende Bild geworfen. Diese
 * Fortschreibung entsteht deshalb hier und ist die einzige Stelle, an der ein
 * Fehler das Bild ueber viele Wuerfe hinweg verschleppen koennte.
 *
 * Die Regeln stammen vom Nutzer (2026-09-07) und stehen in keiner anderen
 * Projektunterlage.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
    LaneTicker, automaticPhase, needsFreshPicture, csvText, CSV_HEADER,
    PHASE_VOLLEN, PHASE_ABRAEUMEN, ALL_PINS, KOENIG,
} from "../ticker.js";

function row(id, lane, sekunde, pins) {
    return {
        id, lane, pins,
        pins_count: pins.length,
        recorded_at: new Date(Date.UTC(2026, 8, 7, 19, 0, sekunde)).toISOString(),
        video_time_s: sekunde,
    };
}

const ms = (sekunde) => Date.UTC(2026, 8, 7, 19, 0, sekunde);

/** Bahn mit offenem Abschnitt und `anzahl` Wuerfen zu je `pins`. */
function bahnMit(wuerfe) {
    const t = new LaneTicker(2);
    t.start(ms(0));
    t.ingest(wuerfe.map((pins, i) => row(i + 1, 2, 10 + i, pins)));
    return t;
}

test("Rhythmus: 1 bis 15 Vollen, 16 bis 30 Abraeumen, dann von vorn", () => {
    assert.equal(automaticPhase(1), PHASE_VOLLEN);
    assert.equal(automaticPhase(15), PHASE_VOLLEN, "15 gehoert noch zu den Vollen");
    assert.equal(automaticPhase(16), PHASE_ABRAEUMEN, "ab 16 wird abgeraeumt");
    assert.equal(automaticPhase(30), PHASE_ABRAEUMEN);
    assert.equal(automaticPhase(31), PHASE_VOLLEN, "das naechste Spiel faengt an");
    assert.equal(automaticPhase(45), PHASE_VOLLEN);
    assert.equal(automaticPhase(46), PHASE_ABRAEUMEN);
});

test("neues Bild, wenn nichts mehr steht", () => {
    assert.equal(needsFreshPicture([]), true);
});

test("neues Bild, wenn nur noch der Koenig steht", () => {
    // Vom Nutzer ergaenzt -- folgt NICHT aus der Regel "wenn nichts mehr steht".
    assert.equal(needsFreshPicture([KOENIG]), true);
    assert.equal(needsFreshPicture([1]), false, "ein anderer Kegel allein nicht");
    assert.equal(needsFreshPicture([KOENIG, 1]), false, "zu zweit nicht");
});

test("in die Vollen steht vor jedem Wurf alles", () => {
    const t = bahnMit([[1, 2, 3], [4, 5], [6]]);
    for (const r of t.rows()) {
        assert.deepEqual(r.before, ALL_PINS, `Wurf ${r.throwNumber}`);
        assert.equal(r.phase, PHASE_VOLLEN);
        assert.deepEqual(r.gone, [], "vor dem Wurf fehlt nie ein Kegel");
    }
});

test("im Abraeumen wird in das stehende Bild geworfen", () => {
    // 15 Wuerfe Vollen, dann beginnt das Abraeumen mit vollem Bild.
    const wuerfe = Array.from({ length: 15 }, () => [1]);
    wuerfe.push([1, 2, 3, 4]);   // Wurf 16: vier fallen, fuenf bleiben stehen
    wuerfe.push([6, 7]);         // Wurf 17: aus den fuenf fallen zwei
    const zeilen = bahnMit(wuerfe).rows();

    const w16 = zeilen[15];
    assert.equal(w16.phase, PHASE_ABRAEUMEN);
    assert.deepEqual(w16.before, ALL_PINS, "das Abraeumen beginnt mit vollem Bild");
    assert.deepEqual(w16.standing, [5, 6, 7, 8, 9]);

    const w17 = zeilen[16];
    assert.deepEqual(w17.before, [5, 6, 7, 8, 9], "geworfen wird in das Restbild");
    assert.deepEqual(w17.gone, [1, 2, 3, 4], "diese vier lagen schon");
    assert.deepEqual(w17.standing, [5, 8, 9]);
    assert.equal(w17.value, 2);
});

test("ein Fehlwurf im Abraeumen laesst das Bild stehen", () => {
    const wuerfe = Array.from({ length: 15 }, () => [1]);
    wuerfe.push([1, 2, 3]);
    wuerfe.push([]);            // Fehlwurf
    wuerfe.push([4]);
    const zeilen = bahnMit(wuerfe).rows();

    assert.deepEqual(zeilen[16].before, [4, 5, 6, 7, 8, 9]);
    assert.deepEqual(zeilen[16].standing, [4, 5, 6, 7, 8, 9], "nichts faellt");
    assert.deepEqual(zeilen[17].before, [4, 5, 6, 7, 8, 9], "Bild unveraendert");
});

test("abgeraeumt -> der naechste Wurf geht in ein volles Bild", () => {
    const wuerfe = Array.from({ length: 15 }, () => [1]);
    wuerfe.push([1, 2, 3, 4]);            // steht: 5,6,7,8,9
    wuerfe.push([5, 6, 7, 8, 9]);         // alles weg
    wuerfe.push([2]);
    const zeilen = bahnMit(wuerfe).rows();

    assert.equal(zeilen[16].freshPicture, true);
    assert.deepEqual(zeilen[16].standing, []);
    assert.deepEqual(zeilen[17].before, ALL_PINS, "die Anlage hat neu aufgestellt");
});

test("nur noch der Koenig -> ebenfalls neues Bild", () => {
    const wuerfe = Array.from({ length: 15 }, () => [1]);
    wuerfe.push([1, 2, 3, 4, 6, 7, 8, 9]);   // uebrig: nur die 5
    wuerfe.push([3]);
    const zeilen = bahnMit(wuerfe).rows();

    assert.deepEqual(zeilen[15].standing, [KOENIG]);
    assert.equal(zeilen[15].freshPicture, true, "Kranz -- es wird neu aufgestellt");
    assert.deepEqual(zeilen[16].before, ALL_PINS);
});

test("Widerspruch: ein Kegel faellt, der nicht mehr stand", () => {
    const wuerfe = Array.from({ length: 15 }, () => [1]);
    wuerfe.push([1, 2, 3]);      // steht: 4..9
    wuerfe.push([2, 7]);         // die 2 lag bereits -- das kann nicht sein
    const zeilen = bahnMit(wuerfe).rows();

    const strittig = zeilen[16];
    assert.equal(strittig.conflict, true, "der Widerspruch muss sichtbar sein");
    assert.deepEqual(strittig.before, ALL_PINS,
        "das Bild wird zurueckgesetzt, statt still falsch weiterzulaufen");
    assert.equal(zeilen[15].conflict, false);
});

test("Handmarke schlaegt die Automatik", () => {
    const t = bahnMit([[1], [2], [3]]);
    assert.equal(t.rows()[0].phase, PHASE_VOLLEN);

    t.setPhase(2, PHASE_ABRAEUMEN);
    const zeilen = t.rows();
    assert.equal(zeilen[0].phase, PHASE_VOLLEN, "Wurf 1 bleibt unberuehrt");
    assert.equal(zeilen[1].phase, PHASE_ABRAEUMEN, "ab Wurf 2 von Hand gesetzt");
    assert.equal(zeilen[2].phase, PHASE_ABRAEUMEN, "und danach weiter");
    // Wurf 1 lief noch in die Vollen, danach steht wieder alles. Erst der
    // Kegel aus Wurf 2 fehlt im Bild, das Wurf 3 vorfindet.
    assert.deepEqual(zeilen[2].before, [1, 3, 4, 5, 6, 7, 8, 9],
        "die 2 aus Wurf 2 fehlt jetzt im Bild");
});

test("Handmarke mit null schaltet zurueck auf automatisch", () => {
    const t = bahnMit([[1], [2], [3]]);
    t.setPhase(1, PHASE_ABRAEUMEN);
    assert.equal(t.rows()[2].phase, PHASE_ABRAEUMEN);
    t.setPhase(3, null);
    assert.equal(t.rows()[2].phase, PHASE_VOLLEN, "Wurf 3 wieder nach Rhythmus");
});

/* ------------------------------------------------------------ Korrekturen */

test("eine Korrektur aendert Wert und Bild, nicht aber das Gemessene", () => {
    const t = bahnMit([[1, 2, 3]]);
    t.correct(1, [1, 2], "Nutzer: die 3 stand noch");

    const [r] = t.rows();
    assert.equal(r.corrected, true);
    assert.deepEqual(r.fallen, [1, 2], "es gilt die Korrektur");
    assert.equal(r.value, 2);
    assert.deepEqual(r.measured, [1, 2, 3], "das Gemessene bleibt erhalten");
    assert.equal(r.note, "Nutzer: die 3 stand noch");
    // Die Datenbankzeile selbst wird nicht angefasst.
    assert.deepEqual(t.throws[0].pins, [1, 2, 3]);
    assert.equal(t.throws[0].pins_count, 3);
});

test("die Korrektur zaehlt in Summe und Fehlwuerfen mit", () => {
    const t = bahnMit([[1, 2, 3], [4]]);
    assert.equal(t.stats().total, 4);
    t.correct(1, []);
    assert.equal(t.stats().total, 1, "drei Kegel weniger");
    assert.equal(t.stats().misses, 1, "aus dem Wurf wurde ein Fehlwurf");
});

test("eine Korrektur wirkt auf das Bild der folgenden Wuerfe", () => {
    const wuerfe = Array.from({ length: 15 }, () => [1]);
    wuerfe.push([1, 2, 3]);
    wuerfe.push([4]);
    const t = bahnMit(wuerfe);
    assert.deepEqual(t.rows()[16].before, [4, 5, 6, 7, 8, 9]);

    t.correct(16, [1, 2]);          // die 3 stand doch noch
    assert.deepEqual(t.rows()[16].before, [3, 4, 5, 6, 7, 8, 9],
        "das Restbild waechst um die 3");
});

test("Korrektur zuruecknehmen", () => {
    const t = bahnMit([[1, 2, 3]]);
    t.correct(1, [1]);
    assert.equal(t.rows()[0].value, 1);
    t.correct(1, null);
    assert.equal(t.rows()[0].corrected, false);
    assert.equal(t.rows()[0].value, 3);
});

test("unsinnige Kegelnummern werden abgewiesen", () => {
    const t = bahnMit([[1]]);
    t.correct(1, [0, 3, 10, 3]);
    assert.deepEqual(t.rows()[0].fallen, [3], "nur gueltige, ohne Doppelte");
});

/* ------------------------------------------------------------------- CSV */

test("die CSV traegt Gemessenes und Korrektur nebeneinander", () => {
    const t = bahnMit([[1, 2, 3]]);
    t.correct(1, [1, 2], "war anders");

    const zeilen = csvText(t.rows()).trim().split("\r\n");
    const kopf = zeilen[0].split(";");
    const werte = zeilen[1].split(";");
    const feld = (name) => werte[kopf.indexOf(name)];

    assert.equal(feld("Wert"), "2", "es gilt die Korrektur");
    assert.equal(feld("Gefallene Kegel"), "1 2");
    assert.equal(feld("Korrigiert"), "ja");
    assert.equal(feld("Gemessen Wert"), "3", "die Messung bleibt nachlesbar");
    assert.equal(feld("Gemessene Kegel"), "1 2 3");
    assert.equal(feld("Bemerkung"), "war anders");
    assert.equal(feld("Phase"), "Vollen");
    assert.equal(feld("Bild vorher"), "1 2 3 4 5 6 7 8 9");
});

test("ohne Korrektur bleiben die Korrekturspalten leer", () => {
    const t = bahnMit([[1, 2]]);
    const zeilen = csvText(t.rows()).trim().split("\r\n");
    const kopf = zeilen[0].split(";");
    const werte = zeilen[1].split(";");
    assert.equal(werte[kopf.indexOf("Korrigiert")], "nein");
    assert.equal(werte[kopf.indexOf("Gemessen Wert")], "");
    assert.equal(werte[kopf.indexOf("Gemessene Kegel")], "");
});

test("Semikolon in der Bemerkung zerlegt die Zeile nicht", () => {
    const t = bahnMit([[1]]);
    t.correct(1, [1], 'Schiri sagt; "war anders"');
    const zeilen = csvText(t.rows()).trim().split("\r\n");
    assert.equal(zeilen.length, 2, "es bleibt bei einer Datenzeile");
    assert.ok(zeilen[1].includes('"Schiri sagt; ""war anders"""'));
});

test("die Kopfzeile bleibt vollstaendig", () => {
    assert.equal(csvText([]).trim(), CSV_HEADER.join(";"));
});
