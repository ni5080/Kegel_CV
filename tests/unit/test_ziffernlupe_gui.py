"""Die Ziffernlupe im Tafeleditor -- Verdrahtung, nicht Aussehen.

DIE KRITIK, DIE DAZU FUEHRTE (Nutzer, 2026-09-15): *"damit kann quasi niemand
arbeiten, weil das Bild die ganze Zeit seine Größe ändert, nutze bitte ein
Standbild und eventuell die Möglichkeit mit Frames hüpfen... und dann fände ich
es sinnvoller wenn wir in der Grafik unten die Anpassungen vornehmen und nicht
oben."*

Drei Dinge müssen deshalb stimmen, und jedes davon ist hier festgehalten:
das Standbild als Vorgabe, das Ziehen IN der Lupe, und eine feste Größe.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication              # noqa: E402

from kegel_cv.calibration.model import LaneCalibration, Roi   # noqa: E402
from kegel_cv.gui.board_editor import TafelEditorDialog  # noqa: E402

pytestmark = pytest.mark.gui

ECKEN = [[100.0, 100.0], [400.0, 100.0], [400.0, 300.0], [100.0, 300.0]]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def bahn() -> LaneCalibration:
    rois = [Roi(name="green_lamp", rect=(0.05, 0.05, 0.06, 0.08))]
    for i in range(4):
        rois.append(Roi(name=f"digit_total_b_{i}",
                        rect=(0.30 + i * 0.10, 0.60, 0.08, 0.20)))
    return LaneCalibration(lane_id=2, real_lane_number=2, quad=ECKEN,
                           rois=rois)


def bild() -> np.ndarray:
    """Ein Bild mit roten Strichen dort, wo die Ziffern liegen."""
    b = np.zeros((480, 640, 3), np.uint8)
    b[100:300, 100:400] = (20, 20, 30)
    for i in range(4):
        x = 190 + i * 30
        b[220:260, x:x + 6] = (40, 40, 240)
    return b


class TestDieLupeIstVerdrahtet:
    def test_standbild_ist_die_vorgabe(self, app):
        """Der Takt lief früher immer -- beim Ziehen war das unbrauchbar."""
        d = TafelEditorDialog(bahn(), bild(), bild_quelle=lambda: bild())
        assert d.standbild.isChecked()
        assert not d._takt.isActive()
        d.deleteLater()

    def test_standbild_abschalten_startet_den_takt(self, app):
        d = TafelEditorDialog(bahn(), bild(), bild_quelle=lambda: bild())
        d.standbild.setChecked(False)
        assert d._takt.isActive()
        d.standbild.setChecked(True)
        assert not d._takt.isActive()
        d.deleteLater()

    def test_ein_ziffernrahmen_fuellt_die_lupe(self, app):
        d = TafelEditorDialog(bahn(), bild())
        d._zeige_bereich("digit_total_b_1")
        assert d.lupe._name == "digit_total_b_1"
        assert d.lupe._rect is not None
        d.deleteLater()

    def test_ein_anderer_bereich_fuellt_sie_nicht(self, app):
        """Nur Ziffern haben Messflächen -- bei einer Lampe wäre die Lupe
        irreführend."""
        d = TafelEditorDialog(bahn(), bild())
        d._zeige_bereich("green_lamp")
        assert d.lupe._name is None
        d.deleteLater()

    def test_ziehen_in_der_lupe_aendert_den_bereich(self, app):
        """Das war der Kern der Kritik: die Anpassung gehört nach unten."""
        d = TafelEditorDialog(bahn(), bild())
        d._zeige_bereich("digit_total_b_1")
        vorher = d.leinwand._roi("digit_total_b_1").rect
        d.lupe._verschiebe(3.0, 0.0, "mitte")
        nachher = d.leinwand._roi("digit_total_b_1").rect
        assert nachher != vorher
        assert nachher[0] > vorher[0]
        assert nachher[2] == pytest.approx(vorher[2])   # Größe unverändert
        d.deleteLater()

    def test_an_der_kante_wird_die_groesse_geaendert(self, app):
        d = TafelEditorDialog(bahn(), bild())
        d._zeige_bereich("digit_total_b_1")
        vorher = d.leinwand._roi("digit_total_b_1").rect
        d.lupe._verschiebe(2.0, 0.0, "rechts")
        nachher = d.leinwand._roi("digit_total_b_1").rect
        assert nachher[2] > vorher[2]
        assert nachher[0] == pytest.approx(vorher[0])   # Lage unverändert
        d.deleteLater()

    def test_ein_bereich_kann_nicht_auf_null_schrumpfen(self, app):
        """Ein Rahmen ohne Fläche ließe sich nicht mehr greifen."""
        d = TafelEditorDialog(bahn(), bild())
        d._zeige_bereich("digit_total_b_1")
        for _ in range(50):
            d.lupe._verschiebe(-5.0, -5.0, "rechts")
            d.lupe._verschiebe(-5.0, -5.0, "unten")
        x, y, w, h = d.leinwand._roi("digit_total_b_1").rect
        assert w > 0 and h > 0
        d.deleteLater()

    def test_ohne_springer_meldet_der_sprung_das_auch(self, app):
        """Beim Stream gibt es keine Frame-Nummer -- das gehört gesagt, nicht
        stillschweigend ignoriert."""
        d = TafelEditorDialog(bahn(), bild())
        d._springe(10)
        assert "Stream" in d.bild_info.text()
        d.deleteLater()

    def test_der_sprung_holt_ein_neues_bild(self, app):
        gerufen = []

        def springer(schritt):
            gerufen.append(schritt)
            neu = bild()
            neu[0, 0] = (1, 2, 3)
            return neu, 4711

        d = TafelEditorDialog(bahn(), bild(), springer=springer)
        d._springe(-10)
        assert gerufen == [-10]
        assert "4711" in d.bild_info.text()
        assert tuple(d._original[0, 0]) == (1, 2, 3)
        d.deleteLater()

    def test_die_lupe_haelt_ihre_hoehe(self, app):
        """Die Größe darf nicht mit dem Ausschnitt springen."""
        d = TafelEditorDialog(bahn(), bild())
        vorher = d.lupe.minimumHeight()
        d._zeige_bereich("digit_total_b_0")
        d._zeige_bereich("digit_total_b_3")
        assert d.lupe.minimumHeight() == vorher
        d.deleteLater()
