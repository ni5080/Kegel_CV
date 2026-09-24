/**
 * Tests der Abfrage, die der Ticker an PostgREST stellt.
 *
 * Geprueft wird vor allem das ZEITFENSTER. Nutzer, 2026-09-24: *"der Liveticker
 * benoetigt noch die Chance, dass man Wuerfe bis zu einem Zeitpunkt abfragt.
 * Also genau so wie 'Wuerfe ab' benoetigt es noch ein 'Wuerfe bis'... damit man
 * Summen schneller und besser abgleichen kann."*
 *
 * Die Falle dabei: Beide Grenzen stehen auf DERSELBEN Spalte. Mit
 * `URLSearchParams.set` wuerde die zweite die erste ueberschreiben, und die
 * Abfrage haette still nur noch eine Grenze -- niemand wuerde es merken, die
 * Liste waere nur laenger als erwartet.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { ThrowFeed } from "../feed.js";

const basis = { url: "https://x.supabase.co", key: "schluessel" };

/** Die Abfrage als lesbare Parameterliste. */
function parameter(feed) {
    const url = new URL(feed._url());
    return url.searchParams.getAll("recorded_at");
}

test("ohne Grenzen keine Zeitbedingung", () => {
    const f = new ThrowFeed({ ...basis });
    assert.deepEqual(parameter(f), []);
});

test("nur die untere Grenze", () => {
    const f = new ThrowFeed({ ...basis, since: "2026-09-19T15:00:00Z" });
    assert.deepEqual(parameter(f), ["gte.2026-09-19T15:00:00Z"]);
});

test("nur die obere Grenze", () => {
    const f = new ThrowFeed({ ...basis, until: "2026-09-19T16:00:00Z" });
    assert.deepEqual(parameter(f), ["lte.2026-09-19T16:00:00Z"]);
});

test("BEIDE Grenzen stehen nebeneinander und ueberschreiben sich nicht", () => {
    const f = new ThrowFeed({
        ...basis,
        since: "2026-09-19T15:00:00Z",
        until: "2026-09-19T16:00:00Z",
    });
    assert.deepEqual(parameter(f), [
        "gte.2026-09-19T15:00:00Z",
        "lte.2026-09-19T16:00:00Z",
    ], "PostgREST verknuepft mehrfach genannte Spalten mit UND -- genau das "
     + "ist hier gewollt, und genau das zerstoert ein `set`");
});

test("reset setzt die obere Grenze und die Leseposition zurueck", () => {
    const f = new ThrowFeed({ ...basis, since: "2026-09-19T15:00:00Z" });
    f.lastId = 4711;
    f.reset({ until: "2026-09-19T16:00:00Z" });
    assert.equal(f.until, "2026-09-19T16:00:00Z");
    assert.equal(f.lastId, 0, "sonst faengt die Abfrage hinter dem Fenster an");
    assert.equal(f.since, "2026-09-19T15:00:00Z", "die untere Grenze bleibt");
});

test("reset mit null hebt die obere Grenze auf -- der Ticker laeuft live weiter", () => {
    const f = new ThrowFeed({ ...basis, until: "2026-09-19T16:00:00Z" });
    f.reset({ until: null });
    assert.equal(f.until, null);
    assert.deepEqual(parameter(f), []);
});

test("reset ohne Angabe laesst die Grenzen in Ruhe", () => {
    const f = new ThrowFeed({
        ...basis, since: "2026-09-19T15:00:00Z", until: "2026-09-19T16:00:00Z",
    });
    f.reset({ lanes: [2, 3] });
    assert.equal(f.since, "2026-09-19T15:00:00Z");
    assert.equal(f.until, "2026-09-19T16:00:00Z");
});

test("die Bahnen bleiben neben dem Zeitfenster erhalten", () => {
    const f = new ThrowFeed({
        ...basis, lanes: [2, 3],
        since: "2026-09-19T15:00:00Z", until: "2026-09-19T16:00:00Z",
    });
    const url = new URL(f._url());
    assert.equal(url.searchParams.get("lane"), "in.(2,3)");
    assert.equal(parameter(f).length, 2);
});
