"""Wurf-Events fuer den pin-scorer.

Kontrakt: `apps/pin-scorer/docs/wurferkennung-plan.md`, Abschnitt 1. Der
pin-scorer will STEHENDE Kegel vor und nach dem Wurf; die Tafel zeigt
GEFALLENE. Die Uebersetzung ist der Kern dieser Tests -- und dass ein
unsicheres Bild als null ankommt statt als falsches.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from kegel_cv.analysis.throw_analyzer import ThrowAnalyzer
from kegel_cv.config.schema import AppConfig
from kegel_cv.models.throw import ThrowResult, ThrowStatus
from kegel_cv.sinks.base import FanOutSink, NullSink, ResultSink
from kegel_cv.sinks.factory import build_sink
from kegel_cv.sinks.pin_scorer import (PinScorerEventSink, letzte_seq,
                                       stehende_kegel, throw_to_event)
from tests.unit.test_throw_analyzer import make_event, make_pins


def wurf(pins=(1, 2, 3), vorher=(), bahn=3,
         status=ThrowStatus.VALID) -> ThrowResult:
    return ThrowResult(
        lane=bahn, throw_number=1, throw_number_in_series=1,
        pins=tuple(pins), pins_count=len(pins), displayed_pin_count=len(pins),
        status=status, running_total=len(pins), confidence=0.9734,
        timestamp=12.345, pins_down_before=vorher,
    )


class TestStehendeKegel:
    def test_in_die_vollen(self):
        vor, nach = stehende_kegel(wurf(pins=(1, 2, 3), vorher=()))
        assert vor == [1, 2, 3, 4, 5, 6, 7, 8, 9]
        assert nach == [4, 5, 6, 7, 8, 9]

    def test_abraeumen_rechnet_vom_reststand(self):
        """Lagen 1-3 schon, fallen jetzt 4 und 5: vorher stehen 4-9."""
        vor, nach = stehende_kegel(wurf(pins=(4, 5), vorher=(1, 2, 3)))
        assert vor == [4, 5, 6, 7, 8, 9]
        assert nach == [6, 7, 8, 9]

    def test_fehlwurf_laesst_das_bild_stehen(self):
        vor, nach = stehende_kegel(wurf(pins=(), vorher=(1, 2),
                                        status=ThrowStatus.EMPTY))
        assert vor == nach == [3, 4, 5, 6, 7, 8, 9]

    def test_unbekannte_ausgangslage_gibt_keine_bilder(self):
        """Ohne sichere Grundlinie wird kein Bild erfunden."""
        assert stehende_kegel(wurf(vorher=None)) == (None, None)


class TestEvent:
    def test_kontraktfelder(self):
        zeit = datetime(2026, 11, 11, 18, 22, 31, tzinfo=timezone.utc)
        event = throw_to_event(wurf(), seq=147, anlage="Halle", quelle="cam1",
                               event_id="abc", now=zeit)
        assert event["eventId"] == "abc"
        assert event["anlage"] == "Halle"
        assert event["bahn"] == 3
        assert event["seq"] == 147
        assert event["ts"] == "2026-11-11T18:22:31Z"
        assert event["art"] == "wurf"
        assert event["bildNach"] == [4, 5, 6, 7, 8, 9]
        assert event["konfidenz"] == 0.973

    def test_gefallen_auch_ohne_bilder(self):
        """Die gemessene Wahrheit faehrt immer mit -- auch wenn die Bilder
        null sind, kann der pin-scorer die Holzzahl uebernehmen."""
        event = throw_to_event(wurf(pins=(5,), vorher=None), seq=1)
        assert event["bildVor"] is None and event["bildNach"] is None
        assert event["gefallen"] == [5]

    def test_event_ids_sind_eindeutig(self):
        a = throw_to_event(wurf(), seq=1)
        b = throw_to_event(wurf(), seq=2)
        assert a["eventId"] != b["eventId"]


class TestAusgangslageAusDerAuswertung:
    @pytest.fixture
    def analyzer(self):
        return ThrowAnalyzer(lane_id=1, cfg=AppConfig(), display_number=2)

    def test_raeumen_traegt_die_grundlinie(self, analyzer):
        ergebnis = analyzer.analyze(make_event(), make_pins((1, 2, 3, 4)),
                                    baseline=make_pins((1, 2)))
        assert ergebnis.pins_down_before == (1, 2)

    def test_vollen_heisst_nichts_lag(self, analyzer):
        ergebnis = analyzer.analyze(make_event(), make_pins((1, 2)),
                                    baseline=make_pins(()))
        assert ergebnis.pins_down_before == ()

    def test_ohne_grundlinie_unbekannt(self, analyzer):
        ergebnis = analyzer.analyze(make_event(), make_pins((1, 2)))
        assert ergebnis.pins_down_before is None

    def test_unklare_lampe_in_der_grundlinie_unbekannt(self, analyzer):
        """BUG-027: Eine unklare Lampe der Grundlinie macht das Bild unsicher."""
        ergebnis = analyzer.analyze(make_event(), make_pins((1, 2, 3)),
                                    baseline=make_pins((1,), complete=False))
        assert ergebnis.pins_down_before is None

    def test_neuaufstellung_verwirft_auch_die_ausgangslage(self, analyzer):
        """Die Auswertung rechnet dann mit "alle standen" -- das Event auch."""
        ergebnis = analyzer.analyze(make_event(), make_pins((7, 8)),
                                    baseline=make_pins((1, 2, 3)))
        assert ergebnis.pins_down_before == ()


class TestDatei:
    def test_haengt_an_und_zaehlt_seq(self, tmp_path):
        pfad = tmp_path / "events.jsonl"
        sink = PinScorerEventSink(pfad, anlage="Halle")
        sink.send(wurf(bahn=2))
        sink.send(wurf(bahn=4))
        zeilen = [json.loads(z) for z in pfad.read_text("utf-8").splitlines()]
        assert [z["seq"] for z in zeilen] == [1, 2]
        assert [z["bahn"] for z in zeilen] == [2, 4]

    def test_neuer_lauf_setzt_seq_fort(self, tmp_path):
        """Sonst begaenne ein zweiter Lauf wieder bei 1 -- "alles ab seq N"
        waere dann mehrdeutig."""
        pfad = tmp_path / "events.jsonl"
        PinScorerEventSink(pfad).send(wurf())
        PinScorerEventSink(pfad).send(wurf())
        assert letzte_seq(pfad) == 2

    def test_kaputte_zeile_wird_uebersprungen(self, tmp_path):
        pfad = tmp_path / "events.jsonl"
        pfad.write_text('{"seq": 5}\n{abgebrochen\n', encoding="utf-8")
        assert letzte_seq(pfad) == 5

    def test_schreibfehler_haelt_die_analyse_nicht_auf(self, tmp_path):
        """P8 -- und die seq wird nicht verbraucht, sonst saehe der
        pin-scorer eine Luecke, wo kein Wurf fehlt."""
        sperre = tmp_path / "ist_eine_datei"
        sperre.write_text("x", encoding="utf-8")
        sink = PinScorerEventSink(sperre / "events.jsonl")
        sink.send(wurf())          # darf nicht werfen
        assert sink._seq == 0


class TestFactory:
    def test_aus_heisst_nullsink(self):
        cfg = AppConfig()
        cfg.output.pin_scorer.enabled = False
        assert isinstance(build_sink(cfg), NullSink)

    def test_nur_pin_scorer(self, tmp_path):
        cfg = AppConfig()
        cfg.output.pin_scorer.enabled = True
        cfg.output.pin_scorer.events_file = str(tmp_path / "e.jsonl")
        assert isinstance(build_sink(cfg), PinScorerEventSink)

    def test_neben_einem_anderen_abnehmer(self):
        class Kaputt(ResultSink):
            def send(self, throw):
                raise RuntimeError("kaputt")

        class Sammler(ResultSink):
            def __init__(self):
                self.wuerfe = []

            def send(self, throw):
                self.wuerfe.append(throw)

        sammler = Sammler()
        FanOutSink([Kaputt(), sammler]).send(wurf())
        assert len(sammler.wuerfe) == 1, \
            "ein kaputter Abnehmer darf dem anderen nichts wegnehmen"
