"""Laden und Zusammenfuehren der Konfiguration."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from .schema import AppConfig

log = logging.getLogger(__name__)

DEFAULT_CONFIG_NAME = "default.yaml"


def find_project_root(start: Path | None = None) -> Path:
    """Sucht die Projektwurzel anhand des config-Verzeichnisses.

    Damit funktioniert der Start aus jedem Arbeitsverzeichnis heraus -- sonst
    haengt das Laden davon ab, wo der Nutzer die Anwendung aufgerufen hat.
    """
    current = (start or Path(__file__)).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "config" / DEFAULT_CONFIG_NAME).is_file():
            return candidate
    # Fallback: drei Ebenen ueber diesem Modul (src/kegel_cv/config/loader.py)
    return Path(__file__).resolve().parents[3]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Fuehrt zwei Konfigurations-Dicts zusammen (override gewinnt).

    Verschachtelte Dicts werden rekursiv gemischt, damit eine Nutzerkonfiguration
    einzelne Werte ueberschreiben kann, ohne ganze Bloecke wiederholen zu muessen.
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_env_file(path: Path) -> int:
    """Liest Zugangsdaten aus einer `.env`-Datei in die Umgebung.

    Warum ueberhaupt: Zugangsdaten gehoeren nicht in `config/default.yaml` --
    die Datei liegt in der Versionsverwaltung. Der uebliche Weg unter Windows
    waere `setx`, das schreibt den Wert aber dauerhaft in die Registrierung des
    Benutzers. Eine Datei im Projekt ist sichtbar, jederzeit loeschbar und laesst
    sich ueber `.gitignore` sauber ausschliessen.

    Bereits gesetzte Umgebungsvariablen werden NICHT ueberschrieben: Wer den
    Wert bewusst im System gesetzt hat, soll ihn nicht von einer Datei
    verdraengt bekommen.

    Returns:
        Anzahl der uebernommenen Eintraege.
    """
    if not path.is_file():
        return 0

    uebernommen = 0
    for zeile in path.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        name, _, wert = zeile.partition("=")
        name = name.strip()
        wert = wert.strip().strip('"').strip("'")
        if not name:
            continue
        if name not in os.environ:
            os.environ[name] = wert
            uebernommen += 1
        elif os.environ[name] != wert:
            # Der Vorrang bleibt bei der Umgebung (siehe Docstring) -- aber
            # STILL darf das nicht geschehen. Genau dieser Fall hat einmal
            # einen Nachmittag gekostet: In der Benutzerumgebung stand aus
            # einem frueheren `setx` ein alter Schluessel, jede Aenderung an
            # `.env` blieb wirkungslos, und nichts sagte warum. Waere die
            # Datei dabei auf einen Schreibschluessel umgestellt worden,
            # haette die Analyse einen ganzen Spieltag lang in den
            # Versandpuffer geschrieben, ohne dass es jemand bemerkt.
            log.warning(
                "%s steht in der Umgebung UND in %s -- mit verschiedenen "
                "Werten. Es gilt die Umgebung; die Datei bleibt wirkungslos. "
                "Entfernen mit: [Environment]::SetEnvironmentVariable('%s', "
                "$null, 'User') -- danach ein NEUES Terminal oeffnen, "
                "laufende Prozesse behalten ihre Kopie.",
                name, path.name, name)

    if uebernommen:
        log.debug("%d Eintraege aus %s uebernommen", uebernommen, path.name)
    return uebernommen


def load_config(
    path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> AppConfig:
    """Laedt die Konfiguration und validiert sie.

    Args:
        path: Pfad zur YAML-Datei. None -> config/default.yaml der Projektwurzel.
        overrides: Zusaetzliche Werte, die die Datei uebersteuern (z.B. aus CLI).

    Raises:
        FileNotFoundError: Konfigurationsdatei fehlt.
        ValueError: Konfiguration ist inhaltlich ungueltig.
    """
    root = find_project_root()
    load_env_file(root / ".env")
    config_path = Path(path) if path else root / "config" / DEFAULT_CONFIG_NAME

    if not config_path.is_file():
        raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Konfiguration muss ein YAML-Mapping sein: {config_path}")

    if overrides:
        raw = _deep_merge(raw, overrides)

    raw["project_root"] = root
    raw["config_path"] = config_path

    try:
        cfg = AppConfig.model_validate(raw)
    except Exception as exc:
        # Klarer Hinweis auf die Datei -- eine nackte Pydantic-Meldung laesst
        # offen, welche der moeglichen Konfigurationsdateien gemeint ist.
        raise ValueError(f"Ungueltige Konfiguration in {config_path}:\n{exc}") from exc

    # SICHTBAR, nicht als DEBUG. ACHTUNG: Wer `load_config` VOR dem
    # Aufsetzen des Logging aufruft -- die Oberflaeche tut das, sie braucht
    # die Konfiguration ja erst dafuer --, sieht diese Zeile NICHT. Dafuer
    # traegt `config_path` den Pfad weiter, und `main.py` meldet ihn
    # nochmals, sobald das Log steht.
    #
    # Am 2026-09-08 lief die Oberflaeche einen
    # Trainingsabend lang mit den Overlay-Schwellen, waehrend danebenher mit
    # den Kamera-Schwellen nachgemessen wurde. Beide Laeufe sahen im Protokoll
    # gleich aus -- die einzige Zeile, die den Unterschied verraten haette,
    # stand auf DEBUG und wurde nie geschrieben.
    #
    # Mitgegeben werden die beiden Werte, an denen sich die Profile
    # unterscheiden. Ein Pfad allein sagt nichts, wenn jemand die Datei
    # bearbeitet hat.
    log.info("Konfiguration: %s | Verdeckungsschwelle %.1f | Waermeschranke %.1f",
             config_path, cfg.detection.green.occlusion_score,
             cfg.detection.lamps.warmth_min)
    return cfg
