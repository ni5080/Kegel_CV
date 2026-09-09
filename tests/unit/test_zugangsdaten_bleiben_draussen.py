"""Zugangsdaten duerfen weder in Dateinamen noch in Kalibrierungen landen.

WARUM ES DIESEN TEST GIBT -- 2026-09-09 beim Anlegen des Repositories:

Eine RTSP-Adresse traegt Benutzer und Passwort im Klartext. Diese Adresse
wanderte an drei Stellen weiter, an denen sie nichts zu suchen hat:

    debug/admin_<PASSWORT>_10.0.0.8_554_h265Preview_02_main/
    data/calibrations/Training.json  ->  "video": "rtsp://admin:<PASSWORT>@..."

(Das echte Passwort steht hier bewusst NICHT -- diese Datei gehoert ins
Repository, und was einmal in der Historie steht, bleibt dort.)

Die Kalibrierungsdatei gehoert ins Repository -- sie ist die Vermessung einer
Bahn. Ein Passwort darin waere auch nach dem Loeschen noch in der Historie.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kegel_cv.calibration.session import CalibrationSession
from kegel_cv.models.quellen import ohne_zugangsdaten
from kegel_cv.video.factory import source_label

GEHEIM = "rtsp://admin:streng-geheim@10.0.0.8:554/haupt"


class TestOhneZugangsdaten:
    def test_benutzer_und_passwort_verschwinden(self):
        assert ohne_zugangsdaten(GEHEIM) == "rtsp://10.0.0.8:554/haupt"

    def test_der_rechner_bleibt(self):
        """Ohne ihn liesse sich nicht mehr erkennen, von welcher Kamera eine
        Kalibrierung stammt."""
        assert "10.0.0.8" in ohne_zugangsdaten(GEHEIM)

    @pytest.mark.parametrize("unveraendert", [
        "https://beispiel.de/stream.m3u8",
        r"C:\Videos\spieltag.mp4",
        "kegelVideos/a.mp4",
        "",
    ])
    def test_was_kein_geheimnis_traegt_bleibt_gleich(self, unveraendert):
        assert ohne_zugangsdaten(unveraendert) == unveraendert

    def test_none_bleibt_none(self):
        assert ohne_zugangsdaten(None) is None

    def test_auch_ohne_port(self):
        assert ohne_zugangsdaten("rtsp://u:p@kamera/live") == "rtsp://kamera/live"


class TestDebugOrdnerName:
    def test_der_ordnername_traegt_kein_passwort(self):
        name = source_label(GEHEIM)
        assert "streng-geheim" not in name
        assert "admin" not in name

    def test_er_bleibt_unterscheidbar(self):
        """Zwei Uebertragungen desselben Anbieters muessen verschiedene
        Ordner bekommen."""
        a = source_label("rtsp://u:p@10.0.0.8:554/bahn_a")
        b = source_label("rtsp://u:p@10.0.0.8:554/bahn_b")
        assert a != b and "10.0.0.8" in a


class TestKalibrierung:
    def test_der_quellhinweis_wird_beim_setzen_bereinigt(self):
        sitzung = CalibrationSession()
        sitzung.set_source_hint(1920, 1080, GEHEIM)
        gespeichert = sitzung.calibration.source_hint.video
        assert "streng-geheim" not in gespeichert
        assert gespeichert == "rtsp://10.0.0.8:554/haupt"

    def test_keine_abgelegte_kalibrierung_traegt_zugangsdaten(self):
        """Prueft den Bestand: Was heute im Repository liegt, muss sauber sein."""
        belastet = []
        for pfad in Path("data/calibrations").glob("*.json"):
            hinweis = (json.loads(pfad.read_text(encoding="utf-8"))
                       .get("source_hint") or {})
            video = hinweis.get("video")
            if video and "@" in str(video).split("://")[-1].split("/")[0]:
                belastet.append(pfad.name)
        assert not belastet, f"Zugangsdaten in: {belastet}"
