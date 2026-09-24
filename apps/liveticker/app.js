/**
 * Oberflaeche des Livetickers: Verdrahtung von Abfrage, Anzeige und CSV.
 *
 * Die eigentliche Rechenarbeit steht in ticker.js und ist dort getestet. Hier
 * passiert nur, was ohne Browser ohnehin nicht pruefbar waere.
 */

import {
    LaneTicker, PIN_LAYOUT, ALL_PINS, csvText, formatClock,
    maxVisible, visibleLanes, PHASE_VOLLEN, PHASE_ABRAEUMEN,
} from "./ticker.js";
import { ThrowFeed } from "./feed.js";

const ABFRAGETAKT_MS = 1500;
const SPEICHER = "kegel.liveticker";

/* ------------------------------------------------------------- Zustand */

const zustand = {
    cfg: { url: "", key: "", table: "throws", lanes: [2, 3, 4, 5] },
    fest: false,               // Verbindung fest eingebaut? Dann nur Bahnen fragen
    gewaehlt: new Set(),
    fokus: null,
    since: null,               // ISO-Zeitpunkt, ab dem gelesen wird
    until: null,               // ISO-Zeitpunkt, bis zu dem gelesen wird (null = live)
    ticker: new Map(),         // Bahnnummer -> LaneTicker
    feed: null,
    ordner: null,              // FileSystemDirectoryHandle
    gezeichnet: [],            // welche Bahnen gerade als Karte im DOM stehen
    bekannteIds: new Map(),    // Bahnnummer -> Set der bereits gezeigten Wurf-ids
    csvStand: new Map(),       // Bahnnummer -> zuletzt geschriebener CSV-Text
};

const $ = (sel) => document.querySelector(sel);

/* --------------------------------------------------- Einstellungen sichern */

function ladeGespeichertes() {
    let gespeichert = {};
    try {
        gespeichert = JSON.parse(localStorage.getItem(SPEICHER) || "{}");
    } catch (fehler) {
        // Ein kaputter Eintrag darf den Start nicht verhindern -- er wird beim
        // naechsten Sichern ohnehin ueberschrieben.
        console.warn("Gespeicherte Einstellungen unlesbar, starte mit Vorgaben", fehler);
    }

    // Fest eingebaute Verbindung (von build.py oder start.py). Sie GEWINNT
    // gegen den lokalen Speicher -- andernfalls behielte der Browser nach
    // einem neuen Bau stillschweigend den alten Schluessel, und niemand kaeme
    // darauf, warum die Seite plaetzlich nichts mehr liest.
    //
    // Die Bahnnummern sind davon ausgenommen: Sie sind die eine Einstellung,
    // die der Nutzer vor Ort trifft, und sollen ein Neuladen ueberstehen.
    const ausDatei = window.LIVETICKER_CONFIG || {};
    zustand.fest = Boolean(ausDatei.url && ausDatei.key);
    zustand.cfg = {
        url: ausDatei.url || gespeichert.url || "",
        key: ausDatei.key || gespeichert.key || "",
        table: ausDatei.table || gespeichert.table || "throws",
        lanes: gespeichert.lanes || ausDatei.lanes || [2, 3, 4, 5],
    };
    zustand.gewaehlt = new Set(gespeichert.gewaehlt || zustand.cfg.lanes);
    zustand.fokus = gespeichert.fokus ?? [...zustand.gewaehlt][0] ?? null;

    // Abschnitte ueberleben ein Neuladen. Ohne das waere ein versehentliches
    // F5 mitten im Spiel gleichbedeutend mit dem Verlust der Startmarke.
    for (const [bahn, segmente] of Object.entries(gespeichert.segmente || {})) {
        holeTicker(Number(bahn)).segments = segmente;
    }
    // Phasenmarken und Korrekturen ebenso: Beides ist Handarbeit des Nutzers
    // und darf ein Neuladen nicht kosten.
    for (const [bahn, marken] of Object.entries(gespeichert.phasen || {})) {
        holeTicker(Number(bahn)).phaseMarks = marken;
    }
    for (const [bahn, k] of Object.entries(gespeichert.korrekturen || {})) {
        holeTicker(Number(bahn)).corrections = k;
    }
    return gespeichert;
}

function sichere() {
    const segmente = {};
    const phasen = {};
    const korrekturen = {};
    for (const [bahn, t] of zustand.ticker) {
        if (t.segments.length) segmente[bahn] = t.segments;
        if (t.phaseMarks.length) phasen[bahn] = t.phaseMarks;
        if (Object.keys(t.corrections).length) korrekturen[bahn] = t.corrections;
    }
    try {
        localStorage.setItem(SPEICHER, JSON.stringify({
            ...zustand.cfg,
            gewaehlt: [...zustand.gewaehlt],
            fokus: zustand.fokus,
            since: zustand.since,
            until: zustand.until,
            segmente,
            phasen,
            korrekturen,
        }));
    } catch (fehler) {
        console.warn("Einstellungen konnten nicht gesichert werden", fehler);
    }
}

function holeTicker(bahn) {
    if (!zustand.ticker.has(bahn)) zustand.ticker.set(bahn, new LaneTicker(bahn));
    return zustand.ticker.get(bahn);
}

/* --------------------------------------------------------------- Kegelbild */

/**
 * Zeichnet die Raute mit DREI Zustaenden.
 *
 * Im Abraeumen wird in das stehende Bild geworfen. Ein Kegel, der schon vor
 * diesem Wurf lag, muss deshalb anders aussehen als einer, der noch steht --
 * sonst waere aus dem Bild nicht zu erkennen, worauf ueberhaupt geworfen wurde.
 *
 *   gefallen -- in DIESEM Wurf gefallen
 *   steht    -- stand vorher und steht noch
 *   weg      -- lag schon vorher
 */
function rauteSvg(gefallen, breite, weg = []) {
    const unten = new Set(gefallen || []);
    const schonWeg = new Set(weg || []);
    let kreise = "";
    for (const [pin, [spalte, reihe]] of Object.entries(PIN_LAYOUT)) {
        const nr = Number(pin);
        const klasse = unten.has(nr) ? "gefallen" : (schonWeg.has(nr) ? "weg" : "steht");
        kreise += `<circle class="${klasse}" cx="${12 + spalte * 19}" `
                + `cy="${12 + reihe * 21.5}" r="7"></circle>`;
    }
    const liste = (s) => [...s].sort((a, b) => a - b).join(", ");
    const text = (unten.size ? `Gefallen: ${liste(unten)}` : "Kein Kegel gefallen")
        + (schonWeg.size ? `. Lag schon: ${liste(schonWeg)}` : "");
    return `<svg class="raute" viewBox="0 0 100 110" width="${breite}" `
         + `height="${Math.round(breite * 1.1)}" role="img" aria-label="${text}">`
         + `${kreise}</svg>`;
}

/* ------------------------------------------------------------- Bahnkarten */

function zeichneChips() {
    const behaelter = $("#bahn-chips");
    behaelter.innerHTML = "";
    const sichtbar = new Set(zustand.gezeichnet);
    for (const bahn of zustand.cfg.lanes) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip";
        chip.textContent = `Bahn ${bahn}`;
        chip.setAttribute("aria-pressed", String(zustand.gewaehlt.has(bahn)));
        chip.dataset.sichtbar = sichtbar.has(bahn) ? "ja" : "nein";
        chip.addEventListener("click", () => {
            // Ein Tipp waehlt die Bahn aus und holt sie zugleich ins Bild --
            // auf dem Handy ist das der einzige Weg, die Bahn zu wechseln.
            if (zustand.gewaehlt.has(bahn) && zustand.fokus === bahn
                    && zustand.gewaehlt.size > 1) {
                zustand.gewaehlt.delete(bahn);
                zustand.fokus = [...zustand.gewaehlt][0];
            } else {
                zustand.gewaehlt.add(bahn);
                zustand.fokus = bahn;
            }
            neueAbfrage();
            zeichne();
            sichere();
        });
        behaelter.appendChild(chip);
    }
}

/** Baut die Karten neu -- nur wenn sich die Menge der sichtbaren Bahnen aendert. */
function baueKarten(bahnen) {
    const ziel = $("#bahnen");
    ziel.innerHTML = "";
    ziel.style.setProperty("--spalten", String(Math.max(1, bahnen.length)));

    for (const bahn of bahnen) {
        const karte = $("#vorlage-bahn").content.firstElementChild.cloneNode(true);
        karte.dataset.bahn = String(bahn);
        karte.querySelector(".bahn-name").textContent = `Bahn ${bahn}`;
        karte.querySelector("button.start").addEventListener("click", () => {
            holeTicker(bahn).start(Date.now());
            zeichne();
            sichere();
        });
        karte.querySelector("button.stopp").addEventListener("click", () => {
            holeTicker(bahn).stop(Date.now());
            zeichne();
            sichere();
        });
        karte.querySelector("button.phase").addEventListener("click", () => {
            // Die Marke gilt AB DEM NAECHSTEN Wurf. Rueckwirkend zu aendern
            // waere gefaehrlich: Das Bild der bereits gezeigten Wuerfe wuerde
            // sich unter der Hand verschieben.
            const t = holeTicker(bahn);
            const naechster = t.stats().count + 1;
            const jetzt = t.phaseAt(naechster);
            t.setPhase(naechster,
                jetzt === PHASE_VOLLEN ? PHASE_ABRAEUMEN : PHASE_VOLLEN);
            zeichne();
            sichere();
        });
        karte.querySelector("button.phase-auto").addEventListener("click", () => {
            const t = holeTicker(bahn);
            t.setPhase(t.stats().count + 1, null);
            zeichne();
            sichere();
        });
        ziel.appendChild(karte);
    }
    zustand.gezeichnet = [...bahnen];
}

function zeichne() {
    const bahnen = visibleLanes(
        zustand.gewaehlt,
        maxVisible(window.innerWidth, window.innerHeight),
        zustand.fokus,
    );
    const gleich = bahnen.length === zustand.gezeichnet.length
        && bahnen.every((b, i) => b === zustand.gezeichnet[i]);
    if (!gleich) {
        baueKarten(bahnen);
        zeichneChips();
    }

    let irgendwas = false;
    for (const bahn of bahnen) {
        const karte = $(`.bahn[data-bahn="${bahn}"]`);
        if (karte) irgendwas = fuelleKarte(karte, bahn) || irgendwas;
    }
    $("#leer").hidden = irgendwas || zustand.gewaehlt.size === 0;
}

function fuelleKarte(karte, bahn) {
    const t = holeTicker(bahn);
    const zeilen = t.rows();
    const kennzahlen = t.stats();
    const letzter = t.latest();

    karte.dataset.laeuft = t.running ? "ja" : "nein";
    karte.querySelector("button.start").textContent = t.running ? "neu starten" : "Start";
    karte.querySelector("button.stopp").disabled = !t.running;
    karte.querySelector(".abschnitt").textContent = t.segments.length
        ? (t.running ? `Abschnitt ${t.segments.length} läuft` : `Abschnitt ${t.segments.length} beendet`)
        : "Warmwerfen — noch nicht gestartet";

    // Phase: was gilt fuer den NAECHSTEN Wurf.
    const naechster = kennzahlen.count + 1;
    const phase = t.phaseAt(naechster);
    const vonHand = t.phaseMarks.some((m) => m.fromThrow <= naechster && m.phase);
    const phasenKnopf = karte.querySelector("button.phase");
    phasenKnopf.textContent = phase === PHASE_ABRAEUMEN ? "Abräumen" : "Vollen";
    phasenKnopf.dataset.phase = phase;
    phasenKnopf.dataset.vonHand = vonHand ? "ja" : "nein";
    phasenKnopf.title = vonHand
        ? "von Hand gesetzt — klicken zum Umschalten"
        : `automatisch (Wurf ${naechster}) — klicken zum Umschalten`;
    karte.querySelector("button.phase-auto").hidden = !vonHand;

    // Kopf: was zuletzt auf dieser Bahn gefallen ist, im Bild jenes Wurfs.
    karte.querySelector(".raute-gross").innerHTML = letzter
        ? rauteSvg(letzter.fallen, 96, letzter.gone)
        : rauteSvg([], 96);
    karte.querySelector(".letzter-text").textContent = letzter
        ? `${letzter.value} gefallen · ${letzter.standing.length} stehen`
          + (letzter.gone.length ? ` · ${letzter.gone.length} lagen schon` : "")
        : "noch kein Wurf";

    karte.querySelector(".k-summe").textContent = String(kennzahlen.total);
    karte.querySelector(".k-fehl").textContent = String(kennzahlen.misses);
    karte.querySelector(".k-anzahl").textContent = String(kennzahlen.count);

    const koerper = karte.querySelector("table.wuerfe tbody");
    const bekannt = zustand.bekannteIds.get(bahn) || new Set();
    koerper.innerHTML = "";

    // Neueste zuerst: Ein Ticker soll den frischen Wurf zeigen, ohne dass
    // jemand scrollen muss.
    for (const z of [...zeilen].reverse()) {
        const tr = document.createElement("tr");
        if (z.segment === 0) tr.classList.add("ausserhalb");
        if (z.miss) tr.classList.add("fehlwurf");
        if (z.corrected) tr.classList.add("korrigiert");
        if (z.conflict) tr.classList.add("widerspruch");
        if (z.id !== null && !bekannt.has(z.id)) tr.classList.add("neu");
        const marke = (z.corrected ? '<span class="marke korr" title="von Hand '
                + 'korrigiert">korr.</span>' : "")
            + (z.conflict ? '<span class="marke konflikt" title="Ein Kegel fiel, '
                + 'der laut Bild nicht mehr stand — fehlt ein Wurf?">?</span>' : "");
        tr.innerHTML =
            `<td class="nr">${z.throwNumber ?? "–"}</td>`
          + `<td class="wert">${z.value}</td>`
          + `<td class="kegel">${z.fallen.length ? z.fallen.join(" ") : "–"}</td>`
          + `<td>${rauteSvg(z.fallen, 34, z.gone)}</td>`
          + `<td class="zeit">${formatClock(z.time)}</td>`
          + `<td class="marken">${marke}</td>`;
        if (z.id !== null) {
            tr.classList.add("klickbar");
            tr.title = "Anklicken zum Korrigieren";
            tr.addEventListener("click", () => oeffneKorrektur(bahn, z));
        }
        koerper.appendChild(tr);
    }
    zustand.bekannteIds.set(bahn, new Set(zeilen.map((z) => z.id)));
    return zeilen.length > 0;
}

/* -------------------------------------------------------------- Korrektur */

// Welcher Wurf gerade im Korrekturdialog liegt, und welche Kegel dort
// angeklickt sind. Bewusst getrennt vom Ticker: Solange nicht uebernommen
// wurde, darf nichts an den Daten haengen bleiben.
let korrekturZiel = null;
let korrekturAuswahl = new Set();

function zeichneKorrekturRaute() {
    const behaelter = $("#korrektur-raute");
    behaelter.innerHTML = "";
    for (const pin of ALL_PINS) {
        const [spalte, reihe] = PIN_LAYOUT[pin];
        const knopf = document.createElement("button");
        knopf.type = "button";
        knopf.className = "kegel-knopf";
        knopf.textContent = String(pin);
        knopf.dataset.gefallen = korrekturAuswahl.has(pin) ? "ja" : "nein";
        // Die Raute soll aussehen wie auf der Tafel -- deshalb absolut
        // gesetzt, nicht als Raster. Angegeben wird der MITTELPUNKT (die CSS
        // verschiebt um die halbe Kantenlaenge): Bei `left: 100%` haetten die
        // Kegel der aeusseren Spalte sonst aus dem Rahmen geragt.
        knopf.style.left = `${10 + spalte * 20}%`;
        knopf.style.top = `${10 + reihe * 20}%`;
        knopf.addEventListener("click", () => {
            if (korrekturAuswahl.has(pin)) korrekturAuswahl.delete(pin);
            else korrekturAuswahl.add(pin);
            zeichneKorrekturRaute();
        });
        behaelter.appendChild(knopf);
    }
    const gewaehlt = [...korrekturAuswahl].sort((a, b) => a - b);
    $("#korrektur-stand").textContent = gewaehlt.length
        ? `${gewaehlt.length} gefallen: ${gewaehlt.join(", ")}`
        : "kein Kegel gefallen (Fehlwurf)";
}

function oeffneKorrektur(bahn, zeile) {
    korrekturZiel = { bahn, id: zeile.id };
    korrekturAuswahl = new Set(zeile.fallen);

    const nummer = zeile.throwNumber === null
        ? "Warmwerfen" : `Wurf ${zeile.throwNumber}`;
    $("#korrektur-kopf").innerHTML =
        `<b>Bahn ${bahn}, ${nummer}</b> um ${formatClock(zeile.time)}. `
      + `Gemessen wurden <b>${zeile.measured.length}</b> Kegel`
      + (zeile.measured.length ? ` (${zeile.measured.join(", ")})` : "")
      + (zeile.gone.length
          ? `. Vor dem Wurf lagen bereits: ${zeile.gone.join(", ")}.` : ".");

    const t = holeTicker(bahn);
    $("#korrektur-notiz").value = (t.corrections[zeile.id] || {}).note || "";
    zeichneKorrekturRaute();
    $("#dlg-korrektur").showModal();

    // Der Beleg kommt NACH dem Oeffnen: Er ist eine eigene Abfrage, und der
    // Dialog soll nicht darauf warten. Die id wird mitgefuehrt, damit ein
    // spaet eintreffendes Bild nicht im falschen Wurf landet.
    const fuer = zeile.id;
    $("#korrektur-beleg").hidden = true;
    $("#korrektur-beleg-fehlt").hidden = false;
    $("#korrektur-beleg-fehlt").textContent = "Tafelbild wird geladen …";
    ladeBeleg(fuer);
}

async function ladeBeleg(fuer) {
    const bilder = zustand.feed ? await zustand.feed.fetchBoardImage(fuer) : null;
    // Inzwischen ein anderer Wurf offen? Dann gehoert dieses Bild nicht hierher.
    if (korrekturZiel === null || korrekturZiel.id !== fuer) return;
    if (bilder && (bilder.nachher || bilder.vorher)) {
        const setze = (sel, wert) => {
            const el = $(sel);
            el.parentElement.hidden = !wert;
            if (wert) el.src = `data:image/jpeg;base64,${wert}`;
        };
        setze("#korrektur-bild-vorher", bilder.vorher);
        setze("#korrektur-bild", bilder.nachher);
        $("#korrektur-beleg").hidden = false;
        $("#korrektur-beleg-fehlt").hidden = true;
    } else {
        $("#korrektur-beleg").hidden = true;
        $("#korrektur-beleg-fehlt").hidden = false;
        $("#korrektur-beleg-fehlt").textContent =
            "Kein Tafelbild zu diesem Wurf — er stammt aus einem Lauf, der noch "
            + "keine Bilder mitgeschickt hat.";
    }
}

function uebernehmeKorrektur(entscheidung) {
    if (korrekturZiel === null) return;
    const t = holeTicker(korrekturZiel.bahn);
    if (entscheidung === "zuruecknehmen") {
        t.correct(korrekturZiel.id, null);
    } else if (entscheidung === "ok") {
        t.correct(korrekturZiel.id, [...korrekturAuswahl],
                  $("#korrektur-notiz").value.trim());
    }
    korrekturZiel = null;
    if (entscheidung !== "abbruch") {
        zustand.csvStand.clear();   // die CSV muss neu geschrieben werden
        zeichne();
        sichere();
        schreibeCsv();
    }
}

/* -------------------------------------------------------------------- CSV */

/**
 * Schreibt je Bahn eine CSV in den gewaehlten Ordner.
 *
 * Geschrieben wird immer die VOLLSTAENDIGE Datei, nicht angehaengt. Das ist bei
 * ein paar hundert Zeilen billig und hat einen Vorteil, der den Aufwand wert
 * ist: Nach einem Neuladen stellt der naechste Schreibvorgang die Datei
 * vollstaendig wieder her, statt eine halbe Datei fortzuschreiben.
 */
async function schreibeCsv() {
    if (!zustand.ordner) return;
    for (const [bahn, t] of zustand.ticker) {
        const text = csvText(t.rows());
        if (zustand.csvStand.get(bahn) === text) continue;
        try {
            const datei = await zustand.ordner.getFileHandle(`bahn_${bahn}.csv`, { create: true });
            const strom = await datei.createWritable();
            // BOM voran, sonst zeigt Excel Umlaute falsch an.
            await strom.write("﻿" + text);
            await strom.close();
            zustand.csvStand.set(bahn, text);
        } catch (fehler) {
            melde(`CSV für Bahn ${bahn} nicht geschrieben: ${fehler.message}`);
        }
    }
}

async function waehleOrdner() {
    if (!window.showDirectoryPicker) {
        melde("Dieser Browser kann nicht in einen Ordner schreiben. "
            + "Chrome oder Edge verwenden — oder den Knopf „herunterladen“ nutzen.");
        return;
    }
    try {
        zustand.ordner = await window.showDirectoryPicker({ mode: "readwrite" });
        $("#ordner-text").textContent = `schreibt nach „${zustand.ordner.name}“ — je Bahn eine Datei`;
        zustand.csvStand.clear();
        await schreibeCsv();
    } catch (fehler) {
        if (fehler.name !== "AbortError") melde(`Ordner nicht nutzbar: ${fehler.message}`);
    }
}

/** Rueckfallweg fuer Browser ohne Ordnerzugriff: eine Datei je Bahn herunterladen. */
function ladeCsvHerunter() {
    for (const [bahn, t] of zustand.ticker) {
        if (!t.rows().length) continue;
        const blob = new Blob(["﻿" + csvText(t.rows())],
                              { type: "text/csv;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `bahn_${bahn}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
    }
}

/* ---------------------------------------------------------------- Abfrage */

function ampel(zustandName, text) {
    $("#ampel").dataset.zustand = zustandName;
    $("#verbindungstext").textContent = text;
}

function melde(text) {
    const p = $("#meldung");
    p.textContent = text;
    p.hidden = !text;
}

function neueAbfrage() {
    if (!zustand.cfg.url || !zustand.cfg.key) {
        zustand.feed = null;
        ampel("aus", "nicht eingerichtet");
        return;
    }
    zustand.feed = new ThrowFeed({
        url: zustand.cfg.url,
        key: zustand.cfg.key,
        table: zustand.cfg.table,
        lanes: [...zustand.gewaehlt],
        since: zustand.since,
        until: zustand.until,
    });
    // Die Wuerfe neu einlesen, die Abschnitte behalten: Der Zeitpunkt aendert,
    // WAS gelesen wird, nicht, wann das Spiel begonnen hat.
    for (const t of zustand.ticker.values()) {
        t.throws = [];
        t._seen = new Set();
    }
    zustand.bekannteIds.clear();
    zustand.csvStand.clear();
}

async function runde() {
    if (!zustand.feed) return;
    try {
        const zeilen = await zustand.feed.fetchNew();
        let neu = 0;
        for (const zeile of zeilen) {
            // Eine Bahn, die in den Daten auftaucht, aber nicht in der Liste
            // steht, wird aufgenommen -- sonst bliebe sie unsichtbar.
            if (!zustand.cfg.lanes.includes(zeile.lane)) {
                zustand.cfg.lanes.push(zeile.lane);
                zustand.cfg.lanes.sort((a, b) => a - b);
                zeichneChips();
            }
            neu += holeTicker(zeile.lane).ingest([zeile]);
        }
        ampel("an", neu ? `${neu} neu · ${formatClock(Date.now())}` : `verbunden · ${formatClock(Date.now())}`);
        melde("");
        if (neu) {
            zeichne();
            await schreibeCsv();
        }
    } catch (fehler) {
        // Ein Aussetzer beendet den Ticker nicht -- die naechste Runde holt
        // nach, was diese verpasst hat.
        ampel("fehler", "keine Verbindung");
        melde(`Abfrage fehlgeschlagen: ${fehler.message}`);
    }
}

/* ------------------------------------------------------------------ Start */

/** `datetime-local` liefert Ortszeit -- die Datenbank rechnet in UTC. */
function ausEingabefeld(wert) {
    if (!wert) return null;
    const d = new Date(wert);
    return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

function insEingabefeld(iso) {
    const d = iso ? new Date(iso) : new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
         + `T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function ausAdresse() {
    // Zeitpunkt und Bahnen lassen sich auch in der Adresse uebergeben:
    //   index.html?ab=2026-09-07T19:00&bis=2026-09-07T20:30&bahnen=2,3
    const p = new URLSearchParams(window.location.search);
    const ab = p.get("ab");
    const bis = p.get("bis");
    const bahnen = p.get("bahnen");
    if (ab) zustand.since = ausEingabefeld(ab) || ab;
    if (bis) zustand.until = ausEingabefeld(bis) || bis;
    if (bahnen) {
        const liste = bahnen.split(",").map((s) => Number(s.trim())).filter(Boolean);
        if (liste.length) {
            zustand.gewaehlt = new Set(liste);
            zustand.fokus = liste[0];
            for (const b of liste) {
                if (!zustand.cfg.lanes.includes(b)) zustand.cfg.lanes.push(b);
            }
            zustand.cfg.lanes.sort((a, b) => a - b);
        }
    }
}

function oeffneEinstellungen() {
    // Ist die Verbindung fest eingebaut, waeren URL und Schluessel hier nur
    // Felder, die nichts bewirken -- die Datei gewinnt ohnehin. Also weg damit.
    $("#cfg-verbindung").hidden = zustand.fest;
    $("#cfg-fest").hidden = !zustand.fest;
    $("#cfg-titel").textContent = zustand.fest ? "Bahnen" : "Verbindung";

    $("#cfg-url").value = zustand.cfg.url;
    $("#cfg-key").value = zustand.cfg.key;
    $("#cfg-table").value = zustand.cfg.table;
    $("#cfg-lanes").value = zustand.cfg.lanes.join(",");
    $("#dlg-einstellungen").showModal();
}

function start() {
    const gespeichert = ladeGespeichertes();

    // Vorgabe: ab heute null Uhr. Ein Spieltag beginnt selten vor Mitternacht,
    // und alles Aeltere waere nur Ballast.
    const heute = new Date();
    heute.setHours(0, 0, 0, 0);
    zustand.since = gespeichert.since || heute.toISOString();
    // Ohne obere Grenze laeuft der Ticker live weiter -- das ist der Regelfall.
    zustand.until = gespeichert.until || null;
    ausAdresse();
    $("#ab-zeit").value = insEingabefeld(zustand.since);
    $("#bis-zeit").value = zustand.until ? insEingabefeld(zustand.until) : "";

    // Ist die Verbindung fest eingebaut, geht es hinter dem Knopf nur noch
    // um die Bahnen -- dann soll er auch das sagen.
    if (zustand.fest) $("#btn-einstellungen").textContent = "Bahnen";
    $("#btn-einstellungen").addEventListener("click", oeffneEinstellungen);
    // Am `submit` des Formulars, NICHT am `close` des Dialogs.
    //
    // GEMESSEN am 2026-09-07: In der Vorschau-Umgebung feuerte `close` gar
    // nicht -- auch nicht bei einem manuellen `dialog.close()`. Die Eingaben
    // wurden dadurch stillschweigend verworfen. `submit` kam zuverlaessig an
    // und ist ohnehin der genauere Anknuepfungspunkt: Es sagt, dass jemand
    // uebernehmen WOLLTE, waehrend `close` auch bei Escape ausgeloest wird.
    $("#cfg-form").addEventListener("submit", (ev) => {
        if (ev.submitter && ev.submitter.value !== "ok") return;
        if (!zustand.fest) {
            zustand.cfg.url = $("#cfg-url").value.trim();
            zustand.cfg.key = $("#cfg-key").value.trim();
            zustand.cfg.table = $("#cfg-table").value.trim() || "throws";
        }
        const liste = $("#cfg-lanes").value.split(",")
            .map((s) => Number(s.trim())).filter((n) => Number.isFinite(n) && n > 0);
        if (liste.length) {
            zustand.cfg.lanes = liste;
            zustand.gewaehlt = new Set(liste);
            zustand.fokus = liste[0];
        }
        neueAbfrage();
        zeichneChips();
        zeichne();
        sichere();
    });

    const zeitGeaendert = () => {
        zustand.since = ausEingabefeld($("#ab-zeit").value);
        // Leeres Feld heisst OFFEN, nicht "bis 1970": `ausEingabefeld` liefert
        // bei leerer Eingabe null, und genau das soll hier ankommen.
        zustand.until = ausEingabefeld($("#bis-zeit").value) || null;
        neueAbfrage();
        zeichne();
        sichere();
    };
    $("#ab-zeit").addEventListener("change", zeitGeaendert);
    $("#bis-zeit").addEventListener("change", zeitGeaendert);
    $("#btn-offen").addEventListener("click", () => {
        $("#bis-zeit").value = "";
        zeitGeaendert();
    });
    $("#btn-jetzt").addEventListener("click", () => {
        $("#ab-zeit").value = insEingabefeld(new Date().toISOString());
        zeitGeaendert();
    });
    $("#btn-heute").addEventListener("click", () => {
        const d = new Date();
        d.setHours(0, 0, 0, 0);
        $("#ab-zeit").value = insEingabefeld(d.toISOString());
        zeitGeaendert();
    });

    $("#btn-alle-start").addEventListener("click", () => {
        const jetzt = Date.now();
        for (const bahn of zustand.gewaehlt) holeTicker(bahn).start(jetzt);
        zeichne();
        sichere();
    });
    $("#btn-alle-stopp").addEventListener("click", () => {
        const jetzt = Date.now();
        for (const bahn of zustand.gewaehlt) holeTicker(bahn).stop(jetzt);
        zeichne();
        sichere();
    });

    // Am `submit`, nicht am `close` -- siehe die Begruendung beim
    // Einstellungsdialog: `close` kommt nicht ueberall an.
    $("#korrektur-form").addEventListener("submit", (ev) => {
        uebernehmeKorrektur(ev.submitter ? ev.submitter.value : "abbruch");
    });

    $("#btn-ordner").addEventListener("click", waehleOrdner);
    $("#btn-download").addEventListener("click", ladeCsvHerunter);
    window.addEventListener("resize", zeichne);
    window.addEventListener("orientationchange", zeichne);

    zeichneChips();
    zeichne();
    neueAbfrage();

    if (!zustand.cfg.url || !zustand.cfg.key) {
        melde("Noch nicht eingerichtet — Projekt-URL und Schlüssel unter „Einstellungen“ eintragen.");
        oeffneEinstellungen();
    }

    setInterval(runde, ABFRAGETAKT_MS);
    runde();
}

start();
