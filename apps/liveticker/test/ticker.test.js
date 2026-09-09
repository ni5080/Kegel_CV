/**
 * Tests der Ableitungslogik. Ausfuehren mit:
 *
 *     node --test apps/liveticker/test/
 *
 * Geprueft wird genau das, was die Datenbank NICHT liefert und diese App
 * deshalb selbst bildet: Wurfnummer, Summe, Fehlwurfzahl, Abschnittsgrenzen.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
    LaneTicker, standingPins, csvText,
    maxVisible, visibleLanes, PIN_LAYOUT, ALL_PINS, CSV_HEADER,
} from "../ticker.js";

/** Baut eine Datenbankzeile, wie der SupabaseSink sie schreibt. */
function row(id, lane, sekunde, pins) {
    const zeit = new Date(Date.UTC(2026, 8, 7, 19, 0, sekunde)).toISOString();
    return {
        id, lane, pins,
        pins_count: pins.length,
        recorded_at: zeit,
        video_time_s: sekunde * 1.0,
    };
}

const ms = (sekunde) => Date.UTC(2026, 8, 7, 19, 0, sekunde);

test("Raute: Kegel 1 steht vorn, Kegel 9 hinten", () => {
    // Zeile 4 ist vorn. Waere die Raute gekippt, stuende die Anzeige auf dem
    // Kopf -- genau der Fehler, der in der Desktop-Oberflaeche schon einmal
    // drin war.
    assert.equal(PIN_LAYOUT[1][1], 4, "Kegel 1 gehoert in die vorderste Zeile");
    assert.equal(PIN_LAYOUT[9][1], 0, "Kegel 9 gehoert in die hinterste Zeile");
    assert.equal(PIN_LAYOUT[5][0], 2, "Der Koenig steht mittig");
    assert.equal(Object.keys(PIN_LAYOUT).length, 9);
});

test("stehende Kegel sind die Gegenmenge der gefallenen", () => {
    assert.deepEqual(standingPins([1, 3, 5]), [2, 4, 6, 7, 8, 9]);
    assert.deepEqual(standingPins([]), ALL_PINS);
    assert.deepEqual(standingPins(ALL_PINS), []);
});

test("doppelte Zeilen werden an der id erkannt", () => {
    const t = new LaneTicker(2);
    assert.equal(t.ingest([row(1, 2, 10, [1, 2])]), 1);
    // Dieselbe Zeile noch einmal -- die Abfragefenster duerfen sich ueberlappen.
    assert.equal(t.ingest([row(1, 2, 10, [1, 2])]), 0);
    assert.equal(t.throws.length, 1);
});

test("Zeilen fremder Bahnen werden nicht angenommen", () => {
    const t = new LaneTicker(2);
    assert.equal(t.ingest([row(1, 3, 10, [1])]), 0);
    assert.equal(t.throws.length, 0);
});

test("nachgelieferte Wuerfe werden nach Zeitpunkt einsortiert, nicht nach id", () => {
    // Nach einem Netzausfall liefert die Erkennung Gepuffertes nach: hohe id,
    // alter Zeitstempel. Wuerde nach id sortiert, stuende der Wurf falsch.
    const t = new LaneTicker(2);
    t.ingest([row(10, 2, 30, [1]), row(11, 2, 10, [2, 3])]);
    assert.deepEqual(t.rows().map((r) => r.id), [11, 10]);
});

test("ohne Start bekommt kein Wurf eine Nummer", () => {
    const t = new LaneTicker(2);
    t.ingest([row(1, 2, 10, [1, 2]), row(2, 2, 20, [3])]);
    const rows = t.rows();
    assert.deepEqual(rows.map((r) => r.throwNumber), [null, null]);
    assert.deepEqual(rows.map((r) => r.segment), [0, 0]);
    // Und die Kennzahlen bleiben leer -- das Warmwerfen zaehlt nicht mit.
    assert.deepEqual(t.stats(), { segment: 0, total: 0, misses: 0, count: 0, average: 0 });
});

test("Start trennt das Warmwerfen vom Spiel", () => {
    const t = new LaneTicker(2);
    t.ingest([
        row(1, 2, 10, [1, 2, 3]),        // Warmwerfen
        row(2, 2, 20, [4, 5, 6, 7]),     // Warmwerfen
    ]);
    t.start(ms(30));
    t.ingest([
        row(3, 2, 40, [1, 2, 3, 4, 5, 6]),
        row(4, 2, 50, []),               // Fehlwurf
        row(5, 2, 60, [9]),
    ]);

    const rows = t.rows();
    assert.deepEqual(rows.map((r) => r.throwNumber), [null, null, 1, 2, 3]);
    assert.deepEqual(rows.map((r) => r.segment), [0, 0, 1, 1, 1]);

    const s = t.stats();
    assert.equal(s.total, 7, "6 + 0 + 1 -- das Warmwerfen bleibt draussen");
    assert.equal(s.misses, 1);
    assert.equal(s.count, 3);
});

test("ein Wurf mit null Kegeln ist ein Fehlwurf", () => {
    const t = new LaneTicker(2);
    t.start(ms(0));
    t.ingest([row(1, 2, 10, [])]);
    const [wurf] = t.rows();
    assert.equal(wurf.miss, true);
    assert.equal(wurf.value, 0);
    assert.deepEqual(wurf.standing, ALL_PINS, "es steht noch alles");
    assert.equal(t.stats().misses, 1);
    assert.equal(t.stats().count, 1, "ein Fehlwurf ist trotzdem ein Wurf");
});

test("Stopp schliesst den Abschnitt, spaetere Wuerfe zaehlen nicht mehr", () => {
    const t = new LaneTicker(2);
    t.start(ms(0));
    t.ingest([row(1, 2, 10, [1, 2])]);
    t.stop(ms(20));
    t.ingest([row(2, 2, 30, [3, 4, 5])]);

    const rows = t.rows();
    assert.deepEqual(rows.map((r) => r.segment), [1, 0]);
    assert.equal(t.stats(1).total, 2, "der Wurf nach dem Stopp bleibt draussen");
    assert.equal(t.running, false);
});

test("ein zweiter Start beginnt einen neuen Abschnitt bei Wurfnummer 1", () => {
    const t = new LaneTicker(2);
    t.start(ms(0));
    t.ingest([row(1, 2, 10, [1, 2]), row(2, 2, 15, [3])]);
    t.stop(ms(20));
    t.start(ms(30));
    t.ingest([row(3, 2, 40, [4, 5, 6])]);

    const rows = t.rows();
    assert.deepEqual(rows.map((r) => r.throwNumber), [1, 2, 1]);
    assert.deepEqual(rows.map((r) => r.segment), [1, 1, 2]);
    assert.equal(t.stats().segment, 2);
    assert.equal(t.stats().total, 3, "der neue Abschnitt zaehlt von vorn");
    assert.equal(t.stats(1).total, 3, "der alte bleibt abrufbar");
});

test("Start bei bereits laufendem Abschnitt schliesst den alten", () => {
    const t = new LaneTicker(2);
    t.start(ms(0));
    t.start(ms(10));
    assert.equal(t.segments.length, 2);
    assert.equal(t.segments[0].stop, ms(10), "der erste wurde beendet");
    assert.equal(t.running, true);
});

test("Stopp ohne laufenden Abschnitt tut nichts", () => {
    const t = new LaneTicker(2);
    assert.equal(t.stop(ms(10)), null);
    assert.equal(t.segments.length, 0);
});

test("der letzte Wurf der Bahn zaehlt auch ausserhalb eines Abschnitts", () => {
    // Der Kopf der Bahn zeigt, was zuletzt gefallen ist -- auch beim Warmwerfen.
    const t = new LaneTicker(2);
    t.ingest([row(1, 2, 10, [1]), row(2, 2, 20, [7, 8, 9])]);
    assert.deepEqual(t.latest().fallen, [7, 8, 9]);
    assert.equal(t.latest().segment, 0);
    assert.equal(new LaneTicker(3).latest(), null);
});

test("Schnitt je Wurf", () => {
    const t = new LaneTicker(2);
    t.start(ms(0));
    t.ingest([row(1, 2, 10, [1, 2, 3]), row(2, 2, 20, [4, 5, 6, 7, 8, 9])]);
    assert.equal(t.stats().average, 4.5);
});

test("CSV enthaelt auch das Warmwerfen, aber als Abschnitt 0", () => {
    const t = new LaneTicker(2);
    t.ingest([row(1, 2, 10, [1])]);
    t.start(ms(20));
    t.ingest([row(2, 2, 30, [2, 3])]);

    const text = csvText(t.rows());
    const zeilen = text.trim().split("\r\n");
    assert.equal(zeilen[0], CSV_HEADER.join(";"));
    assert.equal(zeilen.length, 3, "Kopfzeile plus beide Wuerfe");

    const warm = zeilen[1].split(";");
    assert.equal(warm[2], "0", "Warmwerfen steht in Abschnitt 0");
    assert.equal(warm[3], "", "und hat keine Wurfnummer");

    const spiel = zeilen[2].split(";");
    assert.equal(spiel[2], "1");
    assert.equal(spiel[3], "1");
    assert.equal(spiel[4], "2", "Wert = Anzahl gefallener Kegel");
    assert.equal(spiel[5], "2 3", "gefallene Kegel");
    assert.equal(spiel[6], "1 4 5 6 7 8 9", "stehende Kegel");
    assert.equal(spiel[7], "nein");
});

test("CSV verwendet Semikolon und Dezimalkomma", () => {
    const t = new LaneTicker(2);
    t.start(ms(0));
    t.ingest([{ id: 1, lane: 2, pins: [1], pins_count: 1,
                recorded_at: new Date(ms(10)).toISOString(), video_time_s: 12.5 }]);
    const zeile = csvText(t.rows()).trim().split("\r\n")[1];
    assert.ok(zeile.includes(";12,5;"), `Dezimalkomma fehlt in: ${zeile}`);
});

test("CSV endet mit einem Zeilenumbruch", () => {
    // Sonst klebt beim naechsten Schreiben die erste neue Zeile an der letzten.
    const t = new LaneTicker(2);
    t.ingest([row(1, 2, 10, [1])]);
    assert.ok(csvText(t.rows()).endsWith("\r\n"));
});

test("Bahnenzahl richtet sich nach dem Format des Schirms", () => {
    assert.equal(maxVisible(390, 844), 1, "Hochformat: eine Bahn");
    assert.equal(maxVisible(844, 390), 2, "kleines Querformat: zwei Bahnen");
    assert.equal(maxVisible(1920, 1080), 4, "grosser Schirm: alle");
});

test("die Fokusbahn bleibt im Bild, wenn der Platz knapp wird", () => {
    const gewaehlt = [2, 3, 4, 5];
    assert.deepEqual(visibleLanes(gewaehlt, 4, 2), [2, 3, 4, 5]);
    assert.deepEqual(visibleLanes(gewaehlt, 2, 4), [4, 5]);
    assert.deepEqual(visibleLanes(gewaehlt, 1, 5), [5]);
    // Am Ende der Liste wird nach vorn aufgefuellt, damit der Platz voll wird.
    assert.deepEqual(visibleLanes(gewaehlt, 2, 5), [4, 5]);
    // Unbekannte Fokusbahn: von vorn, statt gar nichts zu zeigen.
    assert.deepEqual(visibleLanes(gewaehlt, 2, 9), [2, 3]);
});
