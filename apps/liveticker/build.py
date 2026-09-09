"""Baut den Liveticker zu EINER HTML-Datei zusammen.

Zweck: eine Datei, die sich irgendwohin legen laesst -- GitHub Pages, ein
Netzlaufwerk, ein USB-Stick. Kein Bauwerkzeug, keine Abhaengigkeiten.

Die Trennung in Module bleibt die QUELLE, die eine Datei ist nur das Erzeugnis.
Das ist keine Zierde: `ticker.js` enthaelt die Wurfnummern-, Summen- und
Fehlwurfrechnung und wird von `test/ticker.test.js` einzeln durchgemessen. Ein
Buendel liesse sich so nicht pruefen.

    .venv/Scripts/python.exe apps/liveticker/build.py

Ergebnis: apps/liveticker/dist/index.html

PROJEKT-URL UND SCHLUESSEL WERDEN FEST EINGEBAUT. Die fertige Seite fragt dann
nur noch nach den Bahnnummern -- vom Nutzer so gewuenscht (2026-09-07).

Das ist vertretbar, weil `anon` auf der Tabelle seit dem 2026-09-07 nur noch
LESEN darf (RLS-Regel plus `revoke insert, update, delete`) und die Daten
anonym sind: Bahn, Kegel, Zeitpunkt -- es steht niemand darin. Genau dafuer ist
ein publishable key gedacht. Wuerde diese Beschraenkung je zurueckgenommen,
duerfte die Datei nicht mehr oeffentlich liegen.

Der GEHEIME Schluessel wird nie eingebaut: `lies_lese_schluessel()` nimmt
`SUPABASE_READ_KEY` mit Vorrang, und ein Wert, der nach `sb_secret_` aussieht,
bricht den Bau ab.

Mit `--ohne-schluessel` entsteht die Fassung, die beim ersten Aufruf fragt.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJEKT = APP_DIR.parents[1]

# Reihenfolge = Abhaengigkeitsreihenfolge. `app.js` ruft am Ende `start()` auf
# und muss deshalb zuletzt stehen.
MODULE = ("ticker.js", "feed.js", "app.js")

log = logging.getLogger("build")

# `import { a, b } from "./x.js";` -- auch ueber mehrere Zeilen.
IMPORT = re.compile(r'^\s*import\s+[^;]*?from\s+["\'][^"\']+["\']\s*;\s*$',
                    re.MULTILINE | re.DOTALL)
# Fuehrendes `export ` vor einer Deklaration.
EXPORT = re.compile(r'^export\s+(?=const|let|var|function|class)', re.MULTILINE)


def buendle_module() -> str:
    """Legt die Module hintereinander und entfernt import/export.

    Das genuegt hier, weil alle Namen auf oberster Ebene eindeutig sind -- ein
    echter Bundler waere fuer drei Dateien ein schlechter Tausch. Damit das so
    bleibt, prueft `pruefe_namen()` es nach.
    """
    teile: list[str] = []
    for name in MODULE:
        quelle = (APP_DIR / name).read_text(encoding="utf-8")
        ohne = EXPORT.sub("", IMPORT.sub("", quelle))
        teile.append(f"/* ===== {name} ===== */\n{ohne.strip()}\n")
    return "\n".join(teile)


def pruefe_namen() -> list[str]:
    """Sucht Namen, die in zwei Modulen auf oberster Ebene vergeben werden.

    Ohne diese Pruefung wuerde ein doppelter Name beim Zusammenlegen entweder
    still das falsche ueberschreiben oder mit einem kaum deutbaren
    `SyntaxError` enden -- und zwar erst im Browser, nicht hier.
    """
    muster = re.compile(r'^(?:export\s+)?(?:const|let|var|function|class)\s+'
                        r'([A-Za-z_$][\w$]*)', re.MULTILINE)
    gesehen: dict[str, str] = {}
    doppelt: list[str] = []
    for name in MODULE:
        quelle = (APP_DIR / name).read_text(encoding="utf-8")
        for treffer in muster.finditer(quelle):
            bezeichner = treffer.group(1)
            if bezeichner in gesehen:
                doppelt.append(f"{bezeichner} (in {gesehen[bezeichner]} und {name})")
            gesehen[bezeichner] = name
    return doppelt


def lies_lese_schluessel() -> str:
    """Holt den Schluessel fuer die LESENDE Seite.

    `SUPABASE_READ_KEY` hat Vorrang vor `SUPABASE_KEY`. Der Grund: Sobald die
    Tabelle per RLS geschuetzt ist, braucht die Bilderkennung einen geheimen
    Schluessel zum Schreiben -- der darf hier auf keinen Fall landen. Zwei
    Namen halten die beiden Seiten sauber auseinander.
    """
    from start import lies_env  # gleiche Logik, nicht zweimal geschrieben

    env = lies_env(PROJEKT / ".env")
    for name in ("SUPABASE_READ_KEY", "SUPABASE_KEY"):
        wert = os.environ.get(name, "") or env.get(name, "")
        if wert:
            return wert
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Baut den Liveticker zu einer einzigen HTML-Datei zusammen.")
    parser.add_argument("--ziel", default=str(APP_DIR / "dist" / "index.html"),
                        help="Ausgabedatei (Vorgabe: apps/liveticker/dist/index.html)")
    parser.add_argument("--bahnen", default="2,3,4,5",
                        help="Bahnnummern zur Vorbelegung (Vorgabe: 2,3,4,5)")
    parser.add_argument("--ohne-schluessel", action="store_true",
                        help="Verbindung NICHT einbauen. Die fertige Seite fragt "
                             "dann beim ersten Aufruf nach URL und Schluessel.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    doppelt = pruefe_namen()
    if doppelt:
        log.error("Doppelte Namen auf oberster Ebene -- so laesst sich nicht "
                  "zusammenlegen: %s", ", ".join(doppelt))
        return 2

    html = (APP_DIR / "index.html").read_text(encoding="utf-8")
    css = (APP_DIR / "styles.css").read_text(encoding="utf-8")

    vorbelegung = ""
    if not args.ohne_schluessel:
        from start import lies_supabase_config

        cfg = lies_supabase_config()
        schluessel = lies_lese_schluessel()
        if schluessel.startswith("sb_secret_") or "service_role" in schluessel:
            log.error("Das sieht nach dem GEHEIMEN Schluessel aus. Er umgeht "
                      "die Zugriffsregeln und darf nicht in eine Datei, die "
                      "jemand herunterladen kann. Abbruch.")
            return 2
        if not schluessel:
            log.warning("Kein Schluessel gefunden -- die Datei fragt danach")
        vorbelegung = ("window.LIVETICKER_CONFIG = " + json.dumps({
            "url": cfg["url"], "table": cfg["table"], "key": schluessel,
            "lanes": [int(t) for t in args.bahnen.split(",") if t.strip()],
        }) + ";")
        log.info("Verbindung fest eingebaut -- die Seite fragt nur noch nach "
                 "den Bahnnummern.")
        log.warning("Der Schluessel steht damit IN der Datei und ist fuer jeden "
                    "lesbar, der sie oeffnet. Das ist bei einem publishable "
                    "key vorgesehen -- ABER NUR, solange `anon` auf der "
                    "Tabelle wirklich nur lesen darf. Pruefen mit: "
                    "select relrowsecurity from pg_class where relname = 'throws';")

    html = html.replace(
        '<link rel="stylesheet" href="styles.css">',
        f"<style>\n{css}\n</style>")
    html = html.replace(
        '<script src="config.local.js" onerror="void 0"></script>',
        f"<script>{vorbelegung}</script>" if vorbelegung else "")
    html = html.replace(
        '<script type="module" src="app.js"></script>',
        f'<script type="module">\n{buendle_module()}\n</script>')

    ziel = Path(args.ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(html, encoding="utf-8")

    groesse = ziel.stat().st_size
    log.info("Gebaut: %s (%.0f KB, eine Datei)", ziel, groesse / 1024)
    if args.ohne_schluessel:
        log.info("Ohne Verbindung gebaut -- die Seite fragt beim ersten Aufruf "
                 "nach URL und Schluessel.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(APP_DIR))
    sys.exit(main())
