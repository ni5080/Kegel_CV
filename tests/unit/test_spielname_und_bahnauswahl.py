"""Spielname und Bahnauswahl -- die Bausteine für ein Multisensor-System.

Nutzer, 2026-09-24: *„ich möchte als Nutzer dem Spiel einen Namen geben, welcher
dann als Spielname in der Datenbank und überall verwendet wird"* und *„ich möchte
auswählen, welche Bahnen überhaupt erfasst und/oder gesendet werden... So kann
ich dann ohne Probleme ein Multisensorsystem bauen."*

Der Aufbau, auf den beides zielt: Der Livestream liefert Bahn 2 und 3, ein
Telefon Bahn 4 und 5. Beide Geräte schreiben in dieselbe Tabelle. Damit das
zusammenfindet, braucht es genau zwei Dinge — denselben **Spielnamen** auf
beiden Geräten, und **disjunkte Bahnen**, damit kein Wurf doppelt ankommt.

Die `video_id` bleibt dabei die Herkunft: Sonst ließe sich später nicht mehr
sagen, welches Gerät eine auffällige Bahn geliefert hat.
"""

from __future__ import annotations

import pytest

from kegel_cv.config import load_config
from kegel_cv.models.throw import ThrowResult, ThrowStatus
from kegel_cv.sinks.base import BahnFilterSink, NullSink, ResultSink
from kegel_cv.sinks.factory import build_sink
from kegel_cv.sinks.payload import throw_to_row


def wurf(lane: int = 2, pins_count: int = 7) -> ThrowResult:
    return ThrowResult(
        lane=lane, throw_number=1, throw_number_in_series=1,
        pins=tuple(range(1, pins_count + 1)), pins_count=pins_count,
        displayed_pin_count=pins_count, status=ThrowStatus.VALID,
        running_total=pins_count, confidence=0.95,
    )


class Mitschreiber(ResultSink):
    """Merkt sich, was durchkam."""

    def __init__(self) -> None:
        self.wuerfe: list[ThrowResult] = []
        self.geschlossen = False

    def send(self, throw: ThrowResult) -> None:
        self.wuerfe.append(throw)

    def close(self) -> None:
        self.geschlossen = True


class TestSpielnameInDerZeile:
    def test_wird_mitgeschickt_wenn_gesetzt(self):
        zeile = throw_to_row(wurf(), video_id="stream_abc",
                             game_name="2. Spieltag Herren")
        assert zeile["game_name"] == "2. Spieltag Herren"

    def test_video_id_bleibt_die_herkunft(self):
        """Der Kern der Entscheidung vom 2026-09-24: Der Spielname tritt NEBEN
        die Herkunft, nicht an ihre Stelle. Sonst ist im Multisensor-Aufbau
        nicht mehr zu sehen, welches Gerät eine Zeile geliefert hat."""
        zeile = throw_to_row(wurf(), video_id="handy_kueche",
                             game_name="2. Spieltag Herren")
        assert zeile["video_id"] == "handy_kueche"
        assert zeile["game_name"] == "2. Spieltag Herren"

    def test_ohne_namen_keine_spalte(self):
        """Eine leere Spalte mitzuschicken hiesse, eine Aussage zu machen, wo
        keine ist -- und wuerde ohne Not eine Spalte verlangen, die es in
        aelteren Tabellen nicht gibt."""
        assert "game_name" not in throw_to_row(wurf(), video_id="x")

    def test_spaltenname_ist_einstellbar(self):
        zeile = throw_to_row(wurf(), game_name="Test",
                             game_name_column="partie")
        assert zeile["partie"] == "Test"
        assert "game_name" not in zeile


class TestBahnfilterBeimSenden:
    def test_laesst_nur_die_gewaehlten_durch(self):
        innen = Mitschreiber()
        filter_ = BahnFilterSink(innen, [2, 3])
        for bahn in (2, 3, 4, 5):
            filter_.send(wurf(lane=bahn))
        assert [w.lane for w in innen.wuerfe] == [2, 3]

    def test_leere_auswahl_laesst_alles_durch(self):
        """Sonst waere die Vorgabe 'nichts senden', und ein vergessener
        Eintrag brauchte einen ganzen Spieltag, um aufzufallen."""
        innen = Mitschreiber()
        filter_ = BahnFilterSink(innen, [])
        for bahn in (2, 3, 4, 5):
            filter_.send(wurf(lane=bahn))
        assert len(innen.wuerfe) == 4

    def test_reicht_schliessen_durch(self):
        innen = Mitschreiber()
        BahnFilterSink(innen, [2]).close()
        assert innen.geschlossen, (
            "Ein Filter, der das Schliessen verschluckt, laesst die "
            "Warteschlange ungeleert -- die zuletzt erkannten Wuerfe waeren weg"
        )

    def test_zwei_geraete_teilen_sich_die_bahnen_ohne_ueberschneidung(self):
        """Der eigentliche Anwendungsfall, als Test formuliert."""
        stream, handy = Mitschreiber(), Mitschreiber()
        a = BahnFilterSink(stream, [2, 3])
        b = BahnFilterSink(handy, [4, 5])
        for bahn in (2, 3, 4, 5):
            a.send(wurf(lane=bahn))
            b.send(wurf(lane=bahn))
        assert [w.lane for w in stream.wuerfe] == [2, 3]
        assert [w.lane for w in handy.wuerfe] == [4, 5]
        assert not ({w.lane for w in stream.wuerfe}
                    & {w.lane for w in handy.wuerfe}), "kein Wurf doppelt"


class TestVerdrahtung:
    """Dass die Teile stimmen, heisst nicht, dass sie jemand verbindet."""

    def test_fabrik_legt_den_filter_auch_ohne_versand_darum(self):
        """Im Probelauf soll im Log stehen, dass die Auswahl verstanden wurde --
        sonst faellt eine vertippte Bahnnummer erst am Spieltag auf."""
        cfg = load_config()
        cfg.output.supabase.enabled = False
        cfg.output.lanes = [2, 3]
        assert isinstance(build_sink(cfg, video_id="x"), BahnFilterSink)

    def test_ohne_auswahl_kein_filter(self):
        cfg = load_config()
        cfg.output.supabase.enabled = False
        cfg.output.lanes = []
        assert isinstance(build_sink(cfg, video_id="x"), NullSink)

    def test_konfiguration_kennt_beide_schalter(self):
        cfg = load_config()
        assert cfg.processing.lanes == [], "Vorgabe: alle Bahnen erfassen"
        assert cfg.output.lanes == [], "Vorgabe: alle erfassten senden"
        assert cfg.output.supabase.game_name_column == "game_name"


class TestErfassungsfilter:
    """Eine nicht erfasste Bahn bekommt gar keinen Prozessor -- auf einem
    Telefon ist genau das der Punkt."""

    @pytest.fixture
    def kalibrierung(self):
        from kegel_cv.calibration.model import Calibration
        pfad = "data/calibrations/2Spieltag.json"
        try:
            return Calibration.load(pfad)
        except Exception:
            pytest.skip(f"{pfad} nicht vorhanden")

    def test_nur_die_gewaehlten_bahnen_werden_gebaut(self, kalibrierung):
        from kegel_cv.analysis.pipeline import AnalysisPipeline
        cfg = load_config()
        cfg.processing.lanes = [2, 3]
        pipe = AnalysisPipeline(kalibrierung, cfg)
        assert sorted(p.display_number for p in pipe.processors) == [2, 3]

    def test_leere_auswahl_baut_alle(self, kalibrierung):
        from kegel_cv.analysis.pipeline import AnalysisPipeline
        cfg = load_config()
        cfg.processing.lanes = []
        pipe = AnalysisPipeline(kalibrierung, cfg)
        assert len(pipe.processors) == len(kalibrierung.lanes)
