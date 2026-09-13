"""Die Verdeckungsschwelle misst sich am AUS-Niveau, nicht an einer Zahl.

DER ANLASS (2026-09-13): Ein Mensch lief durch die Gruenphase von Bahn 2. Der
Gruen-Score fiel zehn Frames lang auf exakt 0,0 -- die Signatur einer
vollstaendigen Verdeckung. Die Bremse stand auf `occlusion_score: 0.0`, also
aus, und es wurde ein Wurf gebucht: 0 Kegel, und sein Gesicht als Beleg in der
Datenbank.

WARUM SIE AUS STAND, und warum eine feste Zahl das nicht loest -- GEMESSEN
ueber ganze Laeufe, AUS-Niveau der gruenen Lampe:

    Livestream (Overlay)      22,5 bis 30,6
    direkte Hallenkamera       0,7 bis 11,7

Eine feste 12 friert die Hallenkamera ein: Dort liegen 94 bis 100 % aller
ECHTEN AUS-Messungen darunter, jede Bahn gilt dauerhaft als verdeckt. Eine
feste 0 laesst im Stream jeden durch, der vor die Lampe laeuft.

DER ANTEIL traegt beides. Der Nutzer dazu: *"Wir bauen ein Tool, was immer
funktioniert, kein 'ja aber wenn' -- 1 Tool und das muss tragen."*
"""

from __future__ import annotations

import numpy as np
import pytest

from kegel_cv.analysis.lane_processor import LaneProcessor
from kegel_cv.calibration.model import LaneCalibration, Roi
from kegel_cv.config import load_config


def bahn() -> LaneCalibration:
    rois = [Roi(name="green_lamp", rect=(0.45, 0.75, 0.06, 0.05))]
    rois += [Roi(name=f"pin_lamp_{i}", rect=(0.10 + 0.08 * i, 0.30, 0.04, 0.04),
                 pin_number=i) for i in range(1, 10)]
    return LaneCalibration(
        lane_id=1, quad=[[100.0, 50.0], [300.0, 50.0],
                         [300.0, 250.0], [100.0, 250.0]], rois=rois)


def prozessor(anteil: float = 0.3, fest: float = 0.0) -> LaneProcessor:
    cfg = load_config()
    cfg.detection.green.occlusion_off_fraction = anteil
    cfg.detection.green.occlusion_score = fest
    p = LaneProcessor(bahn(), cfg)
    p.prepare((720, 1280, 3))
    return p


def lerne(p: LaneProcessor, aus: float, an: float, n: int = 4000) -> None:
    """Fuettert das Histogramm mit zwei sauber getrennten Wolken."""
    h = p.green_detector._histogramm
    for i in range(n):
        h.hinzufuegen(aus if i % 3 else an)
    h._seit_takt = 10 ** 6
    h.schwellen()


class TestDieSchwelleFolgtDemNiveau:
    def test_hoher_aus_pegel_gibt_hohe_schwelle(self):
        """Livestream: AUS liegt bei rund 25, Verdeckung faellt auf 0."""
        p = prozessor()
        lerne(p, aus=25.0, an=70.0)
        schwelle = p._verdeckungsschwelle()
        assert 5.0 < schwelle < 12.0, schwelle
        assert schwelle < 25.0, "ein echtes AUS darf nie als verdeckt gelten"

    def test_niedriger_aus_pegel_gibt_niedrige_schwelle(self):
        """Hallenkamera: AUS liegt selbst bei rund 3 -- eine feste 12 wuerde
        die Bahn dauerhaft einfrieren."""
        p = prozessor()
        lerne(p, aus=3.0, an=60.0)
        schwelle = p._verdeckungsschwelle()
        assert schwelle < 3.0, schwelle

    def test_ohne_gemessenes_niveau_gilt_der_feste_wert(self):
        """Am Anfang eines Laufs gibt es noch keine zwei Wolken."""
        p = prozessor(fest=7.0)
        assert p.green_detector.aus_niveau is None
        assert p._verdeckungsschwelle() == 7.0

    def test_der_feste_wert_ist_eine_untergrenze(self):
        p = prozessor(fest=20.0)
        lerne(p, aus=3.0, an=60.0)
        assert p._verdeckungsschwelle() == 20.0

    def test_abschaltbar(self):
        p = prozessor(anteil=0.0, fest=4.0)
        lerne(p, aus=25.0, an=70.0)
        assert p._verdeckungsschwelle() == 4.0


class TestDasNiveauKommtAusDemHistogramm:
    """NICHT aus einem Perzentil des gleitenden Fensters."""

    def test_das_histogramm_findet_die_untere_wolke(self):
        p = prozessor()
        lerne(p, aus=25.0, an=70.0)
        assert p.green_detector.aus_niveau == pytest.approx(25.0, abs=2.0)

    def test_kein_perzentil_rueckfall(self):
        """GEMESSEN an 1100 Frames: Liegt die Bahn ueberwiegend auf AN,
        liefert jedes Perzentil das AN-Niveau -- 73,3 statt der wahren 25.
        Die Schwelle laege dann mitten in der AUS-Wolke."""
        p = prozessor()
        for _ in range(3000):
            p.green_detector._history.append(75.0)
        assert p.green_detector.aus_niveau is None, \
            "ohne zwei Wolken darf kein Niveau geraten werden"


class TestDreiZeugen:
    """Jeder sieht etwas, das die anderen nicht sehen."""

    def test_die_wache_ist_der_dritte(self):
        """Am Streamende ist alles schwarz: kein bewegter Vordergrund, und das
        gemessene AUS-Niveau ist selbst null. Gruen-Score und Personenmaske
        sind beide blind -- die Wache meldete dort 61 bis 68 %."""
        p = prozessor()
        assert hasattr(p, "_wache_meldet_fremdes")
        assert p._wache_meldet_fremdes is False

    def test_sie_meldet_erst_wenn_sie_bereit_ist(self):
        """Vor der ersten Referenz weiss sie nichts -- und darf dann auch
        nichts behaupten, sonst friert jeder Laufstart ein."""
        p = prozessor()
        assert not p.wache.bereit or p.wache.abweichung(
            np.zeros((10, 10, 3), np.uint8)) == 0.0
