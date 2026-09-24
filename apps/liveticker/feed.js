/**
 * Holt neue Wuerfe aus Supabase -- per PostgREST, ohne zusaetzliche Bibliothek.
 *
 * Warum Abfragen im Takt und kein Realtime-Abonnement: Ein Abonnement muss nach
 * jedem Funkloch, jedem Standby und jedem Netzwechsel neu aufgebaut werden, und
 * merkt selbst nicht immer, dass es taub geworden ist. Eine Abfrage alle
 * anderthalb Sekunden ist fuer einen Ticker schnell genug und heilt sich von
 * selbst: Die naechste Runde holt nach, was die vorige verpasst hat.
 *
 * Der Schluessel ist der oeffentliche (publishable/anon) Schluessel. Er steht
 * ohnehin in jeder lesenden Anwendung -- der geheime Schluessel darf hier
 * niemals landen, er umgeht die Zugriffsregeln.
 */

/** Fortlaufend groesste bereits geholte id -- die Marke, ab der weitergelesen wird. */
export class ThrowFeed {
    constructor({ url, key, table = "throws", lanes = [], since = null, until = null, pageSize = 1000 }) {
        if (!url || !key) throw new Error("Liveticker braucht Projekt-URL und Schluessel");
        this.endpoint = `${url.replace(/\/+$/, "")}/rest/v1/${table}`;
        this.key = key;
        this.lanes = [...lanes];
        this.since = since;
        // Obere Zeitgrenze -- null heisst "bis jetzt", also live weiterlesen.
        // Gebraucht zum Abgleichen: Wer eine Summe gegen die Ergebnistafel
        // haelt, will genau das Zeitfenster eines Satzes sehen und nicht
        // alles, was seither dazugekommen ist (Nutzer, 2026-09-24).
        this.until = until;
        this.pageSize = pageSize;
        this.lastId = 0;
    }

    /** Setzt die Leseposition zurueck -- noetig, wenn sich Zeitpunkt oder Bahnen aendern. */
    reset({ lanes, since, until } = {}) {
        if (lanes) this.lanes = [...lanes];
        if (since !== undefined) this.since = since;
        if (until !== undefined) this.until = until;
        this.lastId = 0;
    }

    _url() {
        const p = new URLSearchParams();
        p.set("select", "id,lane,pins,pins_count,recorded_at,video_time_s,video_id");
        p.set("order", "id.asc");
        p.set("limit", String(this.pageSize));
        if (this.lanes.length) p.set("lane", `in.(${this.lanes.join(",")})`);
        // BEIDE Zeitgrenzen stehen auf DERSELBEN Spalte, deshalb `append` und
        // nicht `set`: PostgREST verknuepft mehrfach genannte Spalten mit UND,
        // `set` wuerde die erste Bedingung ueberschreiben.
        if (this.since) p.append("recorded_at", `gte.${this.since}`);
        if (this.until) p.append("recorded_at", `lte.${this.until}`);
        // Die id ist die Leseposition, nicht der Zeitstempel: Nachgelieferte
        // Wuerfe aus dem Versandpuffer haben alte Zeitstempel, aber neue ids.
        // Nach Zeit zu lesen wuerde sie ueberspringen.
        if (this.lastId) p.set("id", `gt.${this.lastId}`);
        return `${this.endpoint}?${p.toString()}`;
    }

    /**
     * Holt das Tafelbild EINES Wurfs -- erst beim Anklicken.
     *
     * Bewusst nicht in `fetchNew`: Das Bild ist um ein Vielfaches groesser als
     * die uebrigen Felder zusammen. In der Liveliste laege es nur herum, in
     * der Korrektur ist es das Entscheidende.
     *
     * Gibt `null` zurueck, wenn es keines gibt -- auch dann, wenn die Spalte in
     * der Tabelle noch fehlt. Ein fehlendes Bild ist kein Grund, den Dialog
     * scheitern zu lassen.
     */
    async fetchBoardImage(id) {
        if (id === null || id === undefined) return null;

        // Erst beide Spalten, dann notfalls nur die eine.
        //
        // PostgREST lehnt die GANZE Abfrage ab, wenn EINE Spalte fehlt
        // (`PGRST204`). Ohne den zweiten Versuch waere mit dem Vorher-Bild auch
        // das Nachher-Bild verschwunden -- an einer Tabelle, der nur die
        // neuere Spalte fehlt. Genau dieser Fall ist am 2026-09-07 eingetreten.
        for (const felder of ["board_jpeg,board_before_jpeg", "board_jpeg"]) {
            const zeile = await this._holeSpalten(id, felder);
            if (zeile !== null) {
                return { nachher: zeile.board_jpeg || null,
                         vorher: zeile.board_before_jpeg || null };
            }
        }
        return null;
    }

    async _holeSpalten(id, felder) {
        const url = `${this.endpoint}?select=${felder}`
                  + `&id=eq.${encodeURIComponent(id)}`;
        try {
            const antwort = await fetch(url, {
                headers: { apikey: this.key, Authorization: `Bearer ${this.key}` },
            });
            if (!antwort.ok) return null;
            const zeilen = await antwort.json();
            return zeilen[0] || {};
        } catch (fehler) {
            console.warn("Tafelbild nicht abrufbar", fehler);
            return null;
        }
    }

    /**
     * Holt alles, was seit dem letzten Aufruf dazugekommen ist.
     *
     * Kommt eine volle Seite zurueck, wird sofort weitergelesen -- sonst
     * haengt die Anzeige nach einer Pause minutenlang hinterher.
     */
    async fetchNew() {
        const rows = [];
        for (let seite = 0; seite < 50; seite += 1) {
            const antwort = await fetch(this._url(), {
                headers: { apikey: this.key, Authorization: `Bearer ${this.key}` },
            });
            if (!antwort.ok) {
                // Den Antworttext mitgeben: PostgREST erklaert darin, WARUM es
                // abgelehnt hat. Ohne ihn bleibt nur eine nackte Zahl.
                const text = (await antwort.text()).slice(0, 200);
                throw new Error(`HTTP ${antwort.status}: ${text}`);
            }
            const seiteRows = await antwort.json();
            for (const r of seiteRows) {
                rows.push(r);
                if ((r.id ?? 0) > this.lastId) this.lastId = r.id;
            }
            if (seiteRows.length < this.pageSize) break;
        }
        return rows;
    }
}
