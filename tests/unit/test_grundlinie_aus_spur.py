"""Die Grundlinie kommt aus der laufenden Messung, nicht aus einem Fenster.

BUG-031. Bis hierher wurde die Grundlinie -- wie viele Kegel vor dem Wurf schon
lagen -- in genau einem Fenster von 25 Frames nach dem ERKANNTEN Grün-AN
gemessen. Trifft dieses Fenster den falschen Augenblick, ist die gebuchte
Kegelzahl falsch, und zwar dauerhaft: Sie verschwindet in einer Subtraktion.

An einem Spieltag geschah das dreimal, jedes Mal aus einem anderen Grund --
Fenster kürzer als die Grünphase, Fenster 87 Sekunden vor dem Wurf, Bahn
währenddessen verdeckt. Die Grünzeiten waren also nie die Ursache, sie
entschieden nur, WELCHER falsche Augenblick getroffen wurde.

Die Antwort stand jedes Mal in Messungen, die ohnehin anfallen. Genau die
prüfen diese Tests.
"""

from __future__ import annotations

import numpy as np
import pytest

from kegel_cv.analysis.lane_processor import LaneProcessor
from kegel_cv.calibration.model import LaneCalibration, Roi
from kegel_cv.config import load_config
from kegel_cv.models.readings import (LampReading, LampState, PinLampReading,
                                      grundlinie_aus_spur)

HOEHE, BREITE = 720, 1280


def messung(pins: set[int]) -> PinLampReading:
    lampen = tuple(
        LampReading(name=f"pin_lamp_{i}",
                    state=LampState.ON if i in pins else LampState.OFF,
                    score=250.0 if i in pins else 150.0, confidence=1.0)
        for i in range(1, 10))
    return PinLampReading(lamps=lampen, pins=tuple(sorted(pins)),
                          confidence=1.0)


class TestKleinsterBestaetigterStand:
    def test_raeumwurf_findet_die_liegenden_kegel(self):
        """Beim Räumen bleiben die alten Lampen an -- der kleinste Stand seit
        dem vorigen Wurf IST die Grundlinie."""
        spur = [messung({1, 2, 3, 4, 6, 8, 9})] * 5 + [messung(set(range(1, 10)))] * 4
        assert grundlinie_aus_spur(spur, 3).pins == (1, 2, 3, 4, 6, 8, 9)

    def test_nach_dem_neuaufstellen_ist_sie_leer(self):
        """Der Fall Bahn 5 F60871: Die Anlage stellte während einer 87 Sekunden
        langen Grünphase neu auf. Das Fenster sah davon nichts, die Spur schon."""
        spur = ([messung({1, 2, 3, 6, 7, 8, 9})] * 4      # Ergebnis des Vorwurfs
                + [messung(set())] * 4                    # neu aufgestellt
                + [messung(set(range(1, 10)))] * 4)       # alle neune
        assert grundlinie_aus_spur(spur, 3).pins == ()

    def test_ein_einzelner_ausreisser_zaehlt_nicht(self):
        """Die Kegellampen BLINKEN (BUG-007a): Periode 28-30 Frames,
        Dunkelphase bis 15. Eine einzelne dunkle Messung darf die Grundlinie
        nicht bestimmen -- sonst wäre sie immer leer."""
        spur = ([messung({1, 2, 3, 4, 6, 8, 9})] * 3
                + [messung(set())]                        # Dunkelphase
                + [messung({1, 2, 3, 4, 6, 8, 9})] * 3)
        assert grundlinie_aus_spur(spur, 3).pins == (1, 2, 3, 4, 6, 8, 9)

    def test_ohne_bestaetigung_gewinnt_der_ausreisser(self):
        """Die Gegenprobe zum vorigen Test -- damit belegt ist, dass die
        Bedingung wirkt und nicht nur mitläuft."""
        spur = ([messung({1, 2, 3, 4, 6, 8, 9})] * 3
                + [messung(set())]
                + [messung({1, 2, 3, 4, 6, 8, 9})] * 3)
        assert grundlinie_aus_spur(spur, 1).pins == ()

    def test_zu_kurze_spur_schweigt(self):
        """Lieber der alte Weg als eine geratene Grundlinie."""
        assert grundlinie_aus_spur([messung({1, 2})], 3) is None
        assert grundlinie_aus_spur([], 3) is None

    def test_es_zaehlen_mengen_nicht_anzahlen(self):
        """Zwei gleich grosse, aber verschiedene Stände sind KEINE Bestätigung.

        Wechselt die Anzeige zwischen {1,2} und {3,4}, ist nichts stabil --
        und nichts Stabiles heisst hier: keine Aussage."""
        spur = [messung({1, 2}), messung({3, 4}), messung({1, 2}),
                messung({3, 4})]
        assert grundlinie_aus_spur(spur, 2) is None

    def test_der_kleinste_gewinnt_auch_spaet(self):
        """Die Reihenfolge darf nicht entscheiden."""
        spur = ([messung({1, 2, 3})] * 3 + [messung(set())] * 3
                + [messung({1, 2, 3, 4, 5})] * 3)
        assert grundlinie_aus_spur(spur, 3).pins == ()


def _bahn() -> LaneCalibration:
    rois = [Roi(name="green_lamp", rect=(0.45, 0.75, 0.06, 0.05))]
    rois += [Roi(name=f"pin_lamp_{i}", rect=(0.10 + 0.08 * i, 0.30, 0.04, 0.04),
                 pin_number=i) for i in range(1, 10)]
    return LaneCalibration(
        lane_id=1, quad=[[100.0, 50.0], [300.0, 50.0],
                         [300.0, 250.0], [100.0, 250.0]], rois=rois)


@pytest.fixture
def prozessor() -> LaneProcessor:
    cfg = load_config()
    p = LaneProcessor(_bahn(), cfg)
    assert p.prepare((HOEHE, BREITE, 3))
    return p


class TestVerdrahtung:
    """Dass die Funktion stimmt, heisst nicht, dass sie jemand aufruft.

    Genau diese Lücke war BUG-023: gebaut, committet, getestet -- und nie
    ausgeführt.
    """

    def test_die_laufende_messung_landet_in_der_spur(self, prozessor):
        from kegel_cv.video.source import Frame

        takt = prozessor._live_interval
        assert takt > 0, "ohne Live-Takt gäbe es die Spur gar nicht"
        bild = np.full((HOEHE, BREITE, 3), 40, dtype=np.uint8)
        vorher = len(prozessor._grundlinien_spur)
        for i in range(0, takt * 4 + 1):
            prozessor.process(Frame(index=i, timestamp=i / 25.0, image=bild))
        assert len(prozessor._grundlinien_spur) > vorher, (
            "Die Messungen für die Anzeige müssen in der Grundlinienspur "
            "aufgehoben werden -- sonst ist die ganze Reparatur wirkungslos"
        )

    def test_konfiguration_ist_vorhanden_und_an(self, prozessor):
        """Ein Schalter, den niemand kennt, ist keiner."""
        assert prozessor.cfg.sampling.baseline_from_trace is True
        assert prozessor.cfg.sampling.baseline_trace_confirm >= 1
