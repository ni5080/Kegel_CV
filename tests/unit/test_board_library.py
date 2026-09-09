"""Die Bibliothek bekannter Tafelbauarten.

WOFUER -- Wunsch des Nutzers am 2026-09-09:

    "cool waere, wenn er standardmaessig wenn ein Stream startet schaut, ob er
     eins der bekannten Kegelboards aus seinem Repertoire kennt. Langfristig
     sollen alle typischen Boards selbststaendig erkannt werden."

Ein Typ besteht aus einem Musterbild und den ROIs darauf. Wird das Muster in
einem neuen Bild wiedergefunden, folgen alle Felder aus den vier Ecken -- die
ROIs liegen in normierten Tafelkoordinaten.

GEMESSEN 2026-09-09 mit dem Typ FUNK_klassisch (Muster von der Hallenkamera,
190x191 px):

    eigene Hallenkamera, Frame 11000     4 Tafeln, 316 tragende Merkmale
    fremdes Overlay-Video, Frame 81000   4 Tafeln, 179 tragende Merkmale

Zwei verschiedene Kameras, Aufloesungen und Blickwinkel -- dasselbe Muster.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from kegel_cv.calibration.board_library import (Erkennung, Tafeltyp, erkenne,
                                                lade_bibliothek, speichere_typ,
                                                uebernimm)
from kegel_cv.calibration.board_finder import Treffer
from kegel_cv.calibration.model import Calibration, LaneCalibration, Roi

BILD_H, BILD_B = 300, 620


def tafel(breite=110, hoehe=120, keim=5) -> np.ndarray:
    rng = np.random.default_rng(keim)
    b = rng.integers(0, 255, (hoehe, breite, 3), dtype=np.uint8)
    v = keim % 5 * 6
    cv2.rectangle(b, (8 + v, 8), (breite - 8, 34 + v), (255, 255, 255), 2)
    cv2.rectangle(b, (16, 50), (breite - 16 - v, hoehe - 12), (0, 0, 0), 2)
    cv2.circle(b, (breite // 2 + v, hoehe // 2), 10 + keim % 3,
               (255, 255, 255), -1)
    for i in range(3):
        cv2.line(b, (5, 45 + i * 18 + v), (breite - 5, 50 + i * 18),
                 (0, 0, 0), 1)
    return b


def szene(t: np.ndarray, stellen=(20, 180, 340)) -> np.ndarray:
    bild = np.full((BILD_H, BILD_B, 3), 55, dtype=np.uint8)
    h, b = t.shape[:2]
    for x in stellen:
        bild[60:60 + h, x:x + b] = t
    return bild


def eine_kalibrierung(breite=110, hoehe=120) -> Calibration:
    return Calibration(lanes=[LaneCalibration(
        lane_id=1,
        quad=[[20.0, 60.0], [20.0 + breite, 60.0],
              [20.0 + breite, 60.0 + hoehe], [20.0, 60.0 + hoehe]],
        real_lane_number=3,
        rois=[Roi(name="green_lamp", rect=(0.4, 0.8, 0.05, 0.05)),
              Roi(name="digit_total_b_1", rect=(0.2, 0.85, 0.06, 0.1))],
    )])


class TestBibliothekLaden:
    def test_ein_typ_wird_gefunden(self, tmp_path):
        speichere_typ(tmp_path, "Testbauart", szene(tafel()),
                      eine_kalibrierung())
        typen = lade_bibliothek(tmp_path)
        assert [t.name for t in typen] == ["Testbauart"]

    def test_ohne_musterbild_wird_uebersprungen(self, tmp_path):
        """Eine unvollstaendige Bibliothek darf den Start nicht verhindern."""
        eine_kalibrierung().save(tmp_path / "ohne_bild.json")
        assert lade_bibliothek(tmp_path) == []

    def test_eine_kaputte_datei_nimmt_die_anderen_nicht_mit(self, tmp_path):
        speichere_typ(tmp_path, "Gut", szene(tafel()), eine_kalibrierung())
        (tmp_path / "Kaputt.json").write_text("{kein json", encoding="utf-8")
        cv2.imwrite(str(tmp_path / "Kaputt.png"), tafel())
        assert [t.name for t in lade_bibliothek(tmp_path)] == ["Gut"]

    def test_ein_leerer_ordner_ist_kein_fehler(self, tmp_path):
        assert lade_bibliothek(tmp_path / "gibtsnicht") == []

    def test_das_muster_hat_beobachtete_groesse(self, tmp_path):
        """GEMESSEN: Eine auf 440x530 entzerrte Vorlage gegen eine 192 px
        grosse Tafel fand nur eine von vier Tafeln."""
        speichere_typ(tmp_path, "T", szene(tafel()), eine_kalibrierung())
        typ = lade_bibliothek(tmp_path)[0]
        h, b = typ.muster.shape[:2]
        assert abs(b - 110) <= 2 and abs(h - 120) <= 2


class TestErkennen:
    def test_die_eigene_szene_wird_erkannt(self, tmp_path):
        bild = szene(tafel())
        speichere_typ(tmp_path, "Testbauart", bild, eine_kalibrierung())
        typen = lade_bibliothek(tmp_path)
        treffer = erkenne(bild, typen, min_inlier=10)
        assert treffer is not None
        assert treffer.typ.name == "Testbauart"
        assert len(treffer.treffer) == 3, "drei gleiche Tafeln im Bild"

    def test_eine_fremde_szene_wird_nicht_erkannt(self, tmp_path):
        speichere_typ(tmp_path, "Testbauart", szene(tafel(keim=5)),
                      eine_kalibrierung())
        typen = lade_bibliothek(tmp_path)
        leer = np.full((BILD_H, BILD_B, 3), 55, dtype=np.uint8)
        assert erkenne(leer, typen, min_inlier=10) is None

    def test_ohne_typen_kein_treffer(self):
        assert erkenne(szene(tafel()), [], min_inlier=10) is None

    def test_ein_leeres_bild_stuerzt_nicht_ab(self, tmp_path):
        speichere_typ(tmp_path, "T", szene(tafel()), eine_kalibrierung())
        typen = lade_bibliothek(tmp_path)
        assert erkenne(np.zeros((0, 0, 3), np.uint8), typen) is None


class TestUebernehmen:
    def _erkennung(self, tmp_path):
        bild = szene(tafel())
        speichere_typ(tmp_path, "T", bild, eine_kalibrierung())
        return erkenne(bild, lade_bibliothek(tmp_path), min_inlier=10)

    def test_die_bahnnummern_werden_gesetzt(self, tmp_path):
        kal = uebernimm(self._erkennung(tmp_path), [2, 3, 4])
        assert [l.display_number for l in kal.lanes] == [2, 3, 4]

    def test_die_rois_des_typs_werden_uebernommen(self, tmp_path):
        """Der ganze Sinn: kein einziger Klick fuer Lampen und Ziffern."""
        kal = uebernimm(self._erkennung(tmp_path), [1, 2, 3])
        namen = {r.name for r in kal.lanes[0].rois}
        assert namen == {"green_lamp", "digit_total_b_1"}
        for bahn in kal.lanes:
            assert {r.name for r in bahn.rois} == namen

    def test_die_position_von_links_wird_zur_lane_id(self, tmp_path):
        kal = uebernimm(self._erkennung(tmp_path), [7, 8, 9])
        assert [l.lane_id for l in kal.lanes] == [1, 2, 3]

    def test_falsche_anzahl_wird_abgelehnt(self, tmp_path):
        with pytest.raises(ValueError, match="Bahnnummern"):
            uebernimm(self._erkennung(tmp_path), [1, 2])


class TestErkennungsGuete:
    def test_merkmale_sind_die_summe(self):
        t = [Treffer(quad=[[0, 0]] * 4, inlier=n, paare=n + 5,
                     vorlage_index=0) for n in (20, 30)]
        e = Erkennung(typ=Tafeltyp("x", np.zeros((2, 2, 3), np.uint8),
                                   eine_kalibrierung()), treffer=t)
        assert e.merkmale == 50
