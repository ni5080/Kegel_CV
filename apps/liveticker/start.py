"""Startet den Liveticker im Browser.

Die App ist eine reine Browser-Anwendung -- dieses Skript ist KEIN Backend. Es
tut genau zwei Dinge, die der Browser selbst nicht leisten kann:

1. Es liest Projekt-URL, Tabelle und Schluessel aus `config/default.yaml` und
   `.env` und legt sie als `config.local.js` daneben. Sonst muesste man beides
   vor jedem Spieltag von Hand eintippen.
2. Es liefert das Verzeichnis ueber `http://localhost` aus.

Punkt 2 ist nicht bequem, sondern noetig: Ueber `file://` verweigern die Browser
sowohl die Abfrage an Supabase (fremder Ursprung) als auch das Schreiben in
einen Ordner (kein sicherer Kontext). Ohne diesen Umweg bliebe die Seite leer.

    .venv/Scripts/python.exe apps/liveticker/start.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJEKT = APP_DIR.parents[1]

log = logging.getLogger("liveticker")


def lies_env(pfad: Path) -> dict[str, str]:
    """Liest eine `.env`-Datei -- nur `NAME=WERT`, Kommentare werden uebergangen."""
    werte: dict[str, str] = {}
    if not pfad.is_file():
        return werte
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        name, _, wert = zeile.partition("=")
        werte[name.strip()] = wert.strip().strip('"').strip("'")
    return werte


def lies_supabase_config() -> dict[str, object]:
    """Holt URL, Tabelle und Schluesselnamen aus der Projektkonfiguration.

    Faellt das Lesen aus, ist das kein Abbruchgrund: Die Angaben lassen sich in
    der Oberflaeche nachtragen. Ein Ticker, der wegen einer fehlenden Zeile in
    einer YAML-Datei gar nicht erst startet, waere am Spieltag das groessere
    Aergernis.
    """
    vorgabe = {"url": "", "table": "throws", "key_env": "SUPABASE_KEY"}
    yaml_pfad = PROJEKT / "config" / "default.yaml"
    try:
        import yaml  # lokal importiert -- ohne PyYAML laeuft der Rest trotzdem

        daten = yaml.safe_load(yaml_pfad.read_text(encoding="utf-8")) or {}
        abschnitt = (daten.get("output") or {}).get("supabase") or {}
        vorgabe["url"] = abschnitt.get("url", "")
        vorgabe["table"] = abschnitt.get("table", "throws")
        vorgabe["key_env"] = abschnitt.get("api_key_env", "SUPABASE_KEY")
        vorgabe["url_env"] = abschnitt.get("url_env", "SUPABASE_URL")
    except Exception as fehler:  # noqa: BLE001 -- bewusst breit, siehe Docstring
        log.warning("config/default.yaml nicht lesbar (%s) -- Angaben bitte "
                    "in den Einstellungen nachtragen", fehler)

    # DIE ADRESSE HAT VORRANG AUS DER UMGEBUNG. Sie benennt die Datenbank eines
    # bestimmten Vereins und steht seit dem 2026-09-11 in `.env` statt in der
    # geteilten Konfiguration -- siehe `SupabaseConfig.url`.
    umgebung = lies_env(PROJEKT / ".env")
    aus_umgebung = (os.environ.get(vorgabe.get("url_env", "SUPABASE_URL"), "")
                    or umgebung.get(vorgabe.get("url_env", "SUPABASE_URL"), ""))
    if aus_umgebung:
        vorgabe["url"] = aus_umgebung
    return vorgabe


def schreibe_config_js(lanes: list[int]) -> Path:
    """Legt `config.local.js` an -- die Vorbelegung der Oberflaeche.

    Die Datei enthaelt den OEFFENTLICHEN Schluessel. Der steht ohnehin in jeder
    lesenden Anwendung; der geheime Schluessel gehoert hier niemals hinein. Sie
    ist ueber `.gitignore` ausgeschlossen.
    """
    cfg = lies_supabase_config()
    env = lies_env(PROJEKT / ".env")

    # `SUPABASE_READ_KEY` hat Vorrang. Sobald die Tabelle per RLS auf Lesen
    # beschraenkt ist, braucht die Bilderkennung zum Schreiben einen geheimen
    # Schluessel -- der darf hier niemals landen. Zwei Namen halten die
    # schreibende und die lesende Seite sauber auseinander.
    schluessel = ""
    for name in ("SUPABASE_READ_KEY", str(cfg["key_env"])):
        schluessel = os.environ.get(name, "") or env.get(name, "")
        if schluessel:
            break

    if not schluessel:
        log.warning("Kein Schluessel in %s oder der Umgebung gefunden -- die "
                    "Oberflaeche fragt danach", PROJEKT / ".env")
    if schluessel.startswith("sb_secret_") or "service_role" in schluessel:
        log.error("Das sieht nach dem GEHEIMEN Schluessel aus. Er umgeht die "
                  "Zugriffsregeln und darf nicht in eine Browser-Anwendung. "
                  "Abbruch.")
        raise SystemExit(2)

    inhalt = (
        "// Erzeugt von apps/liveticker/start.py -- nicht von Hand pflegen.\n"
        "// Enthaelt den oeffentlichen Schluessel und ist ueber .gitignore\n"
        "// ausgeschlossen.\n"
        "window.LIVETICKER_CONFIG = "
        + json.dumps({"url": cfg["url"], "table": cfg["table"],
                      "key": schluessel, "lanes": lanes}, indent=2)
        + ";\n"
    )
    ziel = APP_DIR / "config.local.js"
    ziel.write_text(inhalt, encoding="utf-8")
    return ziel


class StillerHandler(SimpleHTTPRequestHandler):
    """Wie SimpleHTTPRequestHandler, nur ohne eine Logzeile je Bilddatei."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        log.debug("%s %s", self.address_string(), format % args)

    def end_headers(self) -> None:
        # Waehrend eines Spieltags wird die Seite oefter neu geladen. Eine
        # zwischengespeicherte alte Fassung waere dabei nur verwirrend.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def eigene_adresse() -> str:
    """Die IP-Adresse im lokalen Netz -- damit das Handy die Seite findet."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return str(s.getsockname()[0])
        except OSError:
            return "127.0.0.1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Startet den Liveticker im Browser.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", type=int, default=8000,
                        help="Port des lokalen Dateiservers (Vorgabe: 8000)")
    parser.add_argument("--bahnen", default="2,3,4,5",
                        help="Bahnnummern zur Vorbelegung (Vorgabe: 2,3,4,5)")
    parser.add_argument("--lan", action="store_true",
                        help="auch im lokalen Netz erreichbar machen, damit ein "
                             "Handy oder Tablet mitlesen kann. ACHTUNG: Damit "
                             "ist auch der Schluessel im Netz lesbar.")
    parser.add_argument("--kein-browser", action="store_true",
                        help="Browser nicht automatisch oeffnen")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    lanes = [int(t) for t in args.bahnen.split(",") if t.strip()]
    ziel = schreibe_config_js(lanes)
    log.info("Vorbelegung geschrieben: %s", ziel)

    host = "0.0.0.0" if args.lan else "127.0.0.1"
    handler = partial(StillerHandler, directory=str(APP_DIR))
    try:
        server = ThreadingHTTPServer((host, args.port), handler)
    except OSError as fehler:
        log.error("Port %d ist belegt (%s) -- mit --port einen anderen waehlen",
                  args.port, fehler)
        return 1

    adresse = f"http://localhost:{args.port}/"
    log.info("Liveticker laeuft: %s", adresse)
    if args.lan:
        log.info("Im Netz erreichbar unter: http://%s:%d/", eigene_adresse(), args.port)
        log.warning("Der Schluessel ist damit fuer jeden im selben Netz lesbar.")
    log.info("Beenden mit Strg+C")

    if not args.kein_browser:
        threading.Timer(0.5, webbrowser.open, args=[adresse]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("beendet")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
