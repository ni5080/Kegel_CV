"""Bei Gruen-AUS ist die Lampenzaehlung fertig.

Nutzer, 2026-09-28: *„sobald Grünaus geht, müssen wir fertig sein mit unserer
Zählung."* Physisch begruendet und von Anfang an so erklaert: Bei Gruen-AUS
kann kein Kegel mehr fallen.

WARUM ES DEN TEST BRAUCHT. Die Lampen hingen an einem Fenster, das fuer etwas
anderes gebaut ist. Das Abtastfenster beginnt beim Gruen-AUS und reicht rund
40 Frames darueber hinaus -- fuer die ZIFFERN, die spaet nachziehen
(Wurfnummer und Summe stehen erst kurz vor dem naechsten Gruen-AN richtig da).
Die Lampen liefen einfach mit.

Was das kostete: Genau dort beginnt ein Fehlercode der Tafel, gemessen sieben
Frames nach Gruen-AUS (BUG-036). Er besteht aus dauerleuchtenden UND
blinkenden Lampen, und die Vereinigung nahm beide ins Ergebnis. Auf Bahn 4
wurden daraus zweimal alle neun Kegel, wo die Tafel 7 zaehlte -- zwei Spiele
mit je zehn Kegeln zu viel.

Am Material nachgemessen, Bahn 4 Wurf 22 und 23:

    alt        9 Kegel / 9 Kegel
    jetzt      7 Kegel / 1 Kegel      <- was der Nutzer an der Tafel ablas
"""

from __future__ import annotations

import numpy as np
import pytest

from kegel_cv.analysis.pipeline import AnalysisPipeline
from kegel_cv.calibration.model import Calibration, LaneCalibration, Roi
from kegel_cv.config import load_config
from kegel_cv.analysis.frame_sampler import SampledFrame, SampleEvent
from kegel_cv.models.readings import LampReading, LampState, PinLampReading
from kegel_cv.models.throw import FrameRole
from kegel_cv.video.source import Frame

HOEHE, BREITE = 400, 600
GRUEN_AUS = 1000


def _bahn() -> LaneCalibration:
    rois = [Roi(name="green_lamp", rect=(0.45, 0.75, 0.06, 0.05))]
    rois += [Roi(name=f"pin_lamp_{i}", rect=(0.10 + 0.08 * i, 0.30, 0.04, 0.04),
                 pin_number=i) for i in range(1, 10)]
    return LaneCalibration(
        lane_id=1, quad=[[100.0, 50.0], [300.0, 50.0],
                         [300.0, 250.0], [100.0, 250.0]], rois=rois)


def lesung(pins: set[int]) -> PinLampReading:
    lampen = tuple(
        LampReading(state=LampState.ON if i in pins else LampState.OFF,
                    score=250.0 if i in pins else 100.0, confidence=1.0,
                    name=f"pin_lamp_{i}")
        for i in range(1, 10))
    return PinLampReading(lamps=lampen, pins=tuple(sorted(pins)),
                          confidence=1.0)


def bild() -> np.ndarray:
    return np.full((HOEHE, BREITE, 3), 40, dtype=np.uint8)


class Prozessor:
    """Ein Prozessor, dessen Lampenlesung vom Frame abhaengt.

    Bis Gruen-AUS sieben Kegel, danach der Fehlercode mit allen neun -- genau
    das gemessene Verhalten auf Bahn 4.
    """

    def __init__(self) -> None:
        self.lane = _bahn()
        self.display_number = 4
        self.result_samples = [lesung({1, 2, 3, 6, 7, 8, 9})]
        self.result_pins = lesung({1, 2, 3, 6, 7, 8, 9})
        self.gefragt: list[int] = []

    def read_pin_lamps_at(self, frame: Frame) -> PinLampReading:
        self.gefragt.append(frame.index)
        if frame.index <= GRUEN_AUS:
            return lesung({1, 2, 3, 6, 7, 8, 9})
        return lesung(set(range(1, 10)))        # der Fehlercode


def ereignis() -> SampleEvent:
    e = SampleEvent(lane_id=1, event_id=1, trigger_frame=GRUEN_AUS,
                    trigger_timestamp=GRUEN_AUS / 20.0, pending_offsets=[])
    for versatz, rolle in ((0, FrameRole.GREEN_OFF), (2, FrameRole.SAMPLE),
                           (7, FrameRole.SAMPLE), (16, FrameRole.SAMPLE),
                           (30, FrameRole.SAMPLE)):
        nummer = GRUEN_AUS + versatz
        e.frames.append(SampledFrame(
            frame=Frame(index=nummer, timestamp=nummer / 20.0, image=bild()),
            offset=versatz, role=rolle))
    return e


@pytest.fixture
def pipeline() -> AnalysisPipeline:
    kal = Calibration(name="test", lanes=[_bahn()])
    return AnalysisPipeline(kal, load_config())


class TestDieZaehlungEndetBeiGruenAus:
    def test_frames_nach_gruen_aus_gehen_nicht_ins_ergebnis(self, pipeline):
        p = Prozessor()
        ergebnis = pipeline._aggregate_pins(p, ereignis())
        assert set(ergebnis.pins) == {1, 2, 3, 6, 7, 8, 9}, (
            "Der Fehlercode nach Gruen-AUS darf keine Kegel beisteuern")

    def test_sie_werden_gar_nicht_erst_gelesen(self, pipeline):
        """Nicht nur verworfen -- ungelesen. Ein Lesen, dessen Ergebnis man
        wegwirft, kostet Rechenzeit und landet in der Spur."""
        p = Prozessor()
        pipeline._aggregate_pins(p, ereignis())
        assert p.gefragt == [GRUEN_AUS], (
            f"nur der Gruen-AUS-Frame, gefragt wurden {p.gefragt}")

    def test_abgeschaltet_gilt_der_alte_weg(self, pipeline):
        pipeline.cfg.sampling.count_closes_at_green_off = False
        p = Prozessor()
        ergebnis = pipeline._aggregate_pins(p, ereignis())
        assert set(ergebnis.pins) == set(range(1, 10))
        assert len(p.gefragt) == 5

    def test_der_gruen_aus_frame_selbst_zaehlt_noch(self, pipeline):
        """Bei Gruen-AUS steht das Ergebnis -- dieser Frame gehoert dazu."""
        p = Prozessor()
        pipeline._aggregate_pins(p, ereignis())
        assert GRUEN_AUS in p.gefragt
