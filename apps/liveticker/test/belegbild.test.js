/**
 * Welches Bild im Korrekturdialog als "davor" erscheint.
 *
 * Nutzer, 2026-09-24, nach dem 2. Spieltag: *"Wie man auf dem Screenshot
 * sieht, wird oben links das Bild von Wurf 26 auf Wurf 28 angezeigt (im
 * Vorher-Nachher), dazwischen wurde aber korrekterweise der Fehlwurf
 * erkannt... Schöner wäre es dann trotzdem wenn oben der Wurf 27 auf Wurf 28
 * angezeigt wird, das Bild ist bei Wurf 27 nämlich auch hinterlegt."*
 *
 * DIE URSACHE. `board_before_jpeg` entsteht beim Grün-AN. Ein Fehlwurf
 * schaltet die grüne Lampe nicht aus — die Anlage räumt nicht ab. Damit
 * stecken zwei Würfe in einer Grünphase (gemessen: Bahn 5 ab Frame 34528,
 * 683 Frames, die Tafel zählte darin von 026 auf 028), und das Vorher-Bild
 * zeigt den Stand von vor BEIDEN.
 *
 * Das Nachher-Bild des Vorgängers hat dieses Problem nicht: Es wird bei
 * dessen Grün-AUS aufgenommen und ist damit immer der Stand, auf den
 * geworfen wurde.
 */

import test from "node:test";
import assert from "node:assert/strict";

import { ThrowFeed } from "../feed.js";

const basis = { url: "https://x.supabase.co", key: "schluessel" };

/** Ein Feed, dessen Abfragen aus einer Tabelle im Speicher bedient werden. */
function feedMit(tabelle, { fehlendeSpalte = false } = {}) {
    const f = new ThrowFeed({ ...basis });
    const abfragen = [];
    globalThis.fetch = async (url) => {
        abfragen.push(url);
        const felder = new URL(url).searchParams.get("select").split(",");
        if (fehlendeSpalte && felder.includes("board_before_jpeg")) {
            return { ok: false, status: 400 };          // PostgREST: PGRST204
        }
        const ids = /id=in\.\(([^)]*)\)/.exec(url)[1].split(",");
        const treffer = tabelle
            .filter((z) => ids.includes(String(z.id)))
            .map((z) => Object.fromEntries(
                felder.filter((k) => k in z).map((k) => [k, z[k]])));
        return { ok: true, json: async () => treffer };
    };
    return { f, abfragen };
}

const WURF_26 = { id: 26, board_jpeg: "tafel-026", board_before_jpeg: "tafel-025" };
const FEHLWURF_27 = { id: 27, board_jpeg: "tafel-027", board_before_jpeg: null };
// Der Fall aus dem Spieltag: Wurf 28 teilt sich die Grünphase mit Wurf 27,
// sein eigenes Vorher-Bild zeigt deshalb noch 026.
const WURF_28 = { id: 28, board_jpeg: "tafel-028", board_before_jpeg: "tafel-026" };

test("das 'davor' kommt vom Vorgaenger, nicht aus dem eigenen Feld", async () => {
    const { f } = feedMit([WURF_26, FEHLWURF_27, WURF_28]);
    const bilder = await f.fetchBoardImage(28, 27);
    assert.equal(bilder.nachher, "tafel-028");
    assert.equal(bilder.vorher, "tafel-027",
        "das eigene board_before_jpeg zeigt 026 -- der Fehlwurf 027 faellt "
        + "sonst aus dem Vorher-Nachher heraus");
});

test("ohne Vorgaenger bleibt das eigene Feld der Beleg", async () => {
    const { f } = feedMit([WURF_26, FEHLWURF_27, WURF_28]);
    const bilder = await f.fetchBoardImage(28);
    assert.equal(bilder.vorher, "tafel-026");
});

test("ein Vorgaenger ohne eigenes Bild faellt auf das eigene Feld zurueck", async () => {
    const alt = { id: 27, board_jpeg: null, board_before_jpeg: null };
    const { f } = feedMit([alt, WURF_28]);
    const bilder = await f.fetchBoardImage(28, 27);
    assert.equal(bilder.vorher, "tafel-026",
        "aeltere Laeufe haben gar keine Bilder mitgeschickt");
});

test("beide Wuerfe in EINER Abfrage -- nicht zwei", async () => {
    const { f, abfragen } = feedMit([FEHLWURF_27, WURF_28]);
    await f.fetchBoardImage(28, 27);
    assert.equal(abfragen.length, 1);
    assert.match(abfragen[0], /id=in\.\(28,27\)/);
});

test("fehlt die Spalte board_before_jpeg, bleibt das Nachher-Bild erhalten", async () => {
    // Der Fall vom 2026-09-07: PostgREST lehnt die GANZE Abfrage ab, wenn
    // eine Spalte fehlt. Der zweite Versuch rettet den Rest.
    const { f, abfragen } = feedMit([FEHLWURF_27, WURF_28], { fehlendeSpalte: true });
    const bilder = await f.fetchBoardImage(28, 27);
    assert.equal(abfragen.length, 2);
    assert.equal(bilder.nachher, "tafel-028");
    assert.equal(bilder.vorher, "tafel-027", "der Vorgaenger reicht dafuer aus");
});

test("ohne id gar keine Abfrage", async () => {
    const { f, abfragen } = feedMit([WURF_28]);
    assert.equal(await f.fetchBoardImage(null), null);
    assert.equal(abfragen.length, 0);
});

test("Vorgaenger gleich id fragt nicht doppelt", async () => {
    const { f, abfragen } = feedMit([WURF_28]);
    await f.fetchBoardImage(28, 28);
    assert.match(abfragen[0], /id=in\.\(28\)/);
});
