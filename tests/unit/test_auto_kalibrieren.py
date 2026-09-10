"""Automatisch kalibrieren: Bauart aus Bildern waehlen, Rest misst der Rechner.

WOFUER -- Ansage des Nutzers am 2026-09-10:

    "es fehlt die Bibliothek, ich moechte nicht mehr selbst kalibrieren.
     sondern das soll er selbst machen"
    "Automatisches Kalibrieren (klick) dann kommt ein Fenster 'Waehle dein
     Kegelboardtyp aus' ... und dort gibt es zusaetzlich 'neues Board
     aufnehmen' oder man klickt auf eins und dann wird das gesucht"

ZWEI FEHLER, DIE DIESE TESTS FESTHALTEN. Die Bibliothekspruefung war gebaut,
lief aber nie:

1. `cfg.resolve_path(...)` gibt es nicht -- die Methode heisst `resolve`. Der
   Aufruf haette mit AttributeError abgebrochen.
2. Sie hing an `_on_video_opened`, und dort ist noch KEIN Frame da: Der Player
   meldet `opened` VOR dem ersten `step_forward()`. Die Pruefung sah immer
   `current_frame is None` und kehrte still zurueck -- Fehler 1 blieb dadurch
   sogar unentdeckt.

Beides war ungetestet. Deshalb hier: die Verdrahtung, nicht der
Merkmalsabgleich -- der hat seine Tests in `test_board_finder.py`.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog     # noqa: E402

from kegel_cv.calibration.board_library import (  # noqa: E402
    Tafeltyp, lade_bibliothek, speichere_typ)
from kegel_cv.calibration.model import (Calibration,  # noqa: E402
                                        LaneCalibration, Roi)
from kegel_cv.config import load_config                 # noqa: E402
from kegel_cv.gui import main_window as mw              # noqa: E402
from kegel_cv.gui.boardtype_dialog import TafeltypDialog  # noqa: E402
from kegel_cv.video.source import Frame, VideoInfo      # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fenster(qt_app):
    f = mw.MainWindow(load_config())
    yield f
    f.close()


def bild(wert=90) -> np.ndarray:
    return np.full((200, 300, 3), wert, dtype=np.uint8)


def ein_typ(name="Testbauart") -> Tafeltyp:
    kal = Calibration(lanes=[LaneCalibration(
        lane_id=1,
        quad=[[10.0, 10.0], [90.0, 10.0], [90.0, 90.0], [10.0, 90.0]],
        rois=[Roi(name="green_lamp", rect=(0.4, 0.8, 0.05, 0.05))])])
    return Tafeltyp(name=name, muster=bild(140), kalibrierung=kal)


class UnechterPlayer:
    """Ein Player, der Standbilder liefert und Spruenge mitschreibt."""

    def __init__(self, live=False, gesamt=1000):
        self.current_frame = Frame(index=0, timestamp=0.0, image=bild())
        self.source_id = "test.mp4"
        self.is_live = live
        self.is_loaded = True
        self.position = 400
        self.info = VideoInfo(width=300, height=200, fps=25.0,
                              frame_count=gesamt, source_id="test.mp4")
        self.spruenge: list[int] = []

    def seek(self, index):
        self.spruenge.append(index)
        self.position = index
        self.current_frame = Frame(index=index, timestamp=0.0,
                                   image=bild(90 + index % 40))
        return True

    def step_forward(self):
        return True

    def pause(self):
        pass

    def close(self):
        self.is_loaded = False


# --------------------------------------------------------------- Der Knopf

class TestDerKnopf:
    def test_er_existiert(self, fenster):
        assert hasattr(fenster, "btn_auto_kalibrieren")

    def test_er_erklaert_sich(self, fenster):
        hinweis = fenster.btn_auto_kalibrieren.toolTip()
        assert "Bauart" in hinweis and "Bahnnummern" in hinweis

    def test_ohne_bild_kein_absturz(self, fenster, monkeypatch):
        """Der haeufigste Klick der Welt: auf den Knopf, bevor etwas offen
        ist."""
        gezeigt = []
        monkeypatch.setattr(mw.QMessageBox, "information",
                            lambda *a, **k: gezeigt.append(a))
        fenster._on_auto_kalibrieren()
        assert gezeigt, "es muss eine Erklaerung kommen"


class TestBibliothekWirdGefunden:
    """HIER LAG FEHLER 1: `cfg.resolve_path` gibt es nicht."""

    def test_der_ordner_wird_aufgeloest(self, fenster):
        typen = fenster._tafeltypen()
        assert isinstance(typen, list)

    def test_der_mitgelieferte_typ_ist_dabei(self, fenster):
        """Das Repo bringt FUNK_klassisch mit -- wenn der nicht auftaucht,
        stimmt der Pfad nicht."""
        assert "FUNK_klassisch" in [t.name for t in fenster._tafeltypen()]


class TestBilderSammeln:
    """HIER LAG FEHLER 2 -- und die Antwort darauf, warum EIN Bild nicht
    genuegt: Gemessen ueber 16 Stichproben eines Spiels lieferte ein einzelnes
    Bild nur einmal alle vier Tafeln und fuenfmal gar keine."""

    def test_mehrere_bilder_aus_einer_datei(self, fenster):
        fenster.player = UnechterPlayer()
        bilder = fenster._bilder_fuer_suche()
        assert len(bilder) == fenster.cfg.calibration.boardtype_sample_frames

    def test_die_bilder_sind_verschieden(self, fenster):
        """Sechsmal dasselbe Bild waere sechsmal dieselbe Antwort."""
        fenster.player = UnechterPlayer()
        bilder = fenster._bilder_fuer_suche()
        assert len({b[0, 0, 0] for b in bilder}) > 1

    def test_hinterher_steht_es_wieder_wo_es_war(self, fenster):
        """Wer kalibriert, schaut auf ein bestimmtes Standbild. Das darf ihm
        die Suche nicht wegziehen."""
        player = UnechterPlayer()
        fenster.player = player
        fenster._bilder_fuer_suche()
        assert player.spruenge[-1] == 400

    def test_am_dateiende_wird_rueckwaerts_gesucht(self, fenster):
        """Sonst bleiben am Schluss des Videos alle Stichproben leer."""
        player = UnechterPlayer(gesamt=420)
        player.position = 400
        fenster.player = player
        fenster._bilder_fuer_suche()
        assert all(0 <= s < 420 for s in player.spruenge)

    def test_beim_stream_wird_nicht_gesprungen(self, fenster):
        """Ein Livestream hat keine Vergangenheit -- ein Sprung dorthin
        zerlegt die Uebertragung."""
        player = UnechterPlayer(live=True)
        fenster.player = player
        fenster.cfg.calibration.boardtype_sample_wait_s = 0.0
        bilder = fenster._bilder_fuer_suche()
        assert player.spruenge == []
        assert len(bilder) == fenster.cfg.calibration.boardtype_sample_frames


class TestAuswahlfenster:
    def test_die_typen_stehen_zur_wahl(self, qt_app):
        d = TafeltypDialog([ein_typ("A"), ein_typ("B")])
        assert d.ergebnis is None

    def test_ein_klick_waehlt_den_typ(self, qt_app):
        typ = ein_typ()
        d = TafeltypDialog([typ])
        d._waehle(typ)
        assert d.ergebnis is typ

    def test_neues_board_ist_immer_moeglich(self, qt_app):
        """Auch bei leerer Bibliothek -- sonst gaebe es keinen Anfang."""
        d = TafeltypDialog([])
        d._waehle("neu")
        assert d.ergebnis == "neu"

    def test_eine_leere_bibliothek_ist_kein_fehler(self, qt_app):
        TafeltypDialog([])   # darf nicht werfen


class TestAblauf:
    def _oeffne_mit(self, fenster, monkeypatch, wahl):
        fenster.player = UnechterPlayer()

        def auf(self):
            self.ergebnis = wahl
            return QDialog.Accepted

        monkeypatch.setattr(mw.TafeltypDialog, "exec", auf)

    def test_abbruch_laesst_alles_wie_es_war(self, fenster, monkeypatch):
        self._oeffne_mit(fenster, monkeypatch, None)
        monkeypatch.setattr(mw.TafeltypDialog, "exec",
                            lambda self: QDialog.Rejected)
        fenster._on_auto_kalibrieren()
        assert fenster.session.calibration.lanes == []

    def test_neues_board_fuehrt_zur_aufnahme(self, fenster, monkeypatch):
        self._oeffne_mit(fenster, monkeypatch, "neu")
        gerufen = []
        monkeypatch.setattr(mw.MainWindow, "_on_board_aufnehmen",
                            lambda self: gerufen.append(1))
        fenster._on_auto_kalibrieren()
        assert gerufen == [1]

    def test_ohne_treffer_wird_erklaert_was_zu_tun_ist(self, fenster,
                                                      monkeypatch):
        self._oeffne_mit(fenster, monkeypatch, ein_typ())
        fenster.cfg.calibration.boardtype_sample_frames = 2
        texte = []
        monkeypatch.setattr(mw.QMessageBox, "warning",
                            lambda *a, **k: texte.append(a[2]))
        fenster._on_auto_kalibrieren()
        assert texte and "andere Stelle" in texte[0]

    def test_ein_treffer_wird_uebernommen(self, fenster, monkeypatch):
        """Der ganze Sinn: kein einziger Klick in die Tafel."""
        from kegel_cv.calibration.board_finder import Treffer
        from kegel_cv.calibration.board_library import Erkennung

        self._oeffne_mit(fenster, monkeypatch, ein_typ())
        treffer = [Treffer(quad=[[x, 10.0], [x + 80, 10.0],
                                 [x + 80, 90.0], [x, 90.0]],
                           inlier=40, paare=60, vorlage_index=0)
                   for x in (10.0, 120.0)]
        monkeypatch.setattr(mw, "TafeltypDialog", mw.TafeltypDialog)
        monkeypatch.setattr(
            "kegel_cv.calibration.board_library.erkenne_ueber_frames",
            lambda *a, **k: Erkennung(typ=ein_typ(), treffer=treffer))
        monkeypatch.setattr(mw.QInputDialog, "getText",
                            lambda *a, **k: ("3 4", True))
        fenster._on_auto_kalibrieren()
        assert [l.display_number for l in fenster.session.calibration.lanes] \
            == [3, 4]
        assert {r.name for r in fenster.session.calibration.lanes[0].rois} \
            == {"green_lamp"}


class TestNeueBauartAufnehmen:
    def test_ohne_kalibrierung_wird_erklaert_wie(self, fenster, monkeypatch):
        fenster.player = UnechterPlayer()
        texte = []
        monkeypatch.setattr(mw.QMessageBox, "information",
                            lambda *a, **k: texte.append(a[2]))
        fenster._on_board_aufnehmen()
        assert texte and "Kalibrierung starten" in texte[0]

    def test_sie_landet_in_der_bibliothek(self, fenster, monkeypatch, tmp_path):
        fenster.player = UnechterPlayer()
        fenster.session.calibration = ein_typ().kalibrierung
        fenster.session.active_lane = 1
        fenster.cfg.calibration.boardtype_directory = str(tmp_path)
        monkeypatch.setattr(mw.QInputDialog, "getText",
                            lambda *a, **k: ("FUNK neu", True))
        monkeypatch.setattr(mw.QMessageBox, "information", lambda *a, **k: None)
        fenster._on_board_aufnehmen()
        assert [t.name for t in lade_bibliothek(tmp_path)] == ["FUNK_neu"], \
            "Leerzeichen im Namen wuerden den Dateinamen zerlegen"

    def test_ohne_namen_wird_nichts_angelegt(self, fenster, monkeypatch,
                                             tmp_path):
        fenster.player = UnechterPlayer()
        fenster.session.calibration = ein_typ().kalibrierung
        fenster.cfg.calibration.boardtype_directory = str(tmp_path)
        monkeypatch.setattr(mw.QInputDialog, "getText",
                            lambda *a, **k: ("", False))
        fenster._on_board_aufnehmen()
        assert lade_bibliothek(tmp_path) == []
