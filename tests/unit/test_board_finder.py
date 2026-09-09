"""Eine bekannte Anzeigetafel im Bild wiederfinden.

WOFUER -- Wunsch des Nutzers am 2026-09-09, Punkt 3:

    "sobald ich einen Bahntyp kalibriert habe, sollte das meines Erachtens
     sehr gut funktionieren, dass ein Algorithmus ueber 'Bild in Bild' Suche
     das mindestens genauso gut kalibrieren kann wie ich. Es reicht ja, dass
     er die Eckpunkte sauber findet, weil die Leuchten und Ziffern sollten ja
     immer an derselben Stelle sein."

Das trifft zu, weil die ROIs in NORMIERTEN Tafelkoordinaten liegen: Sind die
vier Ecken gefunden, folgt der Rest daraus.

GEMESSEN am Trainingsmitschnitt vom 2026-09-08, Wiederfinden 6 Minuten
spaeter: 0,5 bis 2,9 Pixel Eckabweichung auf allen vier Bahnen.

DIE GEFAEHRLICHE STELLE ist nicht der Treffer, sondern der FEHLTREFFER: Eine
Homographie aus wenigen falschen Paaren liefert bereitwillig ein Viereck --
nur eben ein sinnloses. Aus einem Frame mit einer Person neben der Tafel kam
auf Bahn 5 ein Ergebnis, das 1429 Pixel danebenlag. Ohne Pruefung waere das
als Kalibrierung durchgegangen.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from kegel_cv.calibration.board_finder import (BoardFinder, entzerre,
                                               ist_plausibel, quad_groesse)

BILD_H, BILD_B = 400, 700


def tafel(breite: int = 120, hoehe: int = 130, keim: int = 7) -> np.ndarray:
    """Ein Bild mit viel Struktur -- eine echte Tafel hat sie auch.

    Fester Keim: Ein Test, der je nach Zufallszahl faellt oder besteht, ist
    schlimmer als kein Test.

    ACHTUNG, HIER LAG EIN FEHLER IM TESTAUFBAU: Zuerst unterschieden sich
    zwei Tafeln nur im RAUSCHEN, waehrend Rechtecke und Kreis an derselben
    Stelle sassen. ORB lebt aber von Kanten, nicht von Rauschen -- die beiden
    galten dem Verfahren zu Recht als dasselbe Muster. Der Keim verschiebt
    deshalb auch die GEOMETRIE.
    """
    rng = np.random.default_rng(keim)
    b = rng.integers(0, 255, (hoehe, breite, 3), dtype=np.uint8)
    v = keim % 5 * 7          # Versatz der Struktur, aus dem Keim
    # ein paar harte Kanten -- ORB lebt von Ecken, nicht von Rauschen
    cv2.rectangle(b, (10 + v, 10), (breite - 10, 40 + v), (255, 255, 255), 2)
    cv2.rectangle(b, (20, 60 - v // 2), (breite - 20 - v, hoehe - 15),
                  (0, 0, 0), 2)
    cv2.circle(b, (breite // 2 + v, hoehe // 2 - v), 12 + keim % 4,
               (255, 255, 255), -1)
    for i in range(4):
        cv2.line(b, (5, 50 + i * 15 + v), (breite - 5 - v, 55 + i * 15),
                 (0, 0, 0), 1)
    return b


def szene(t: np.ndarray, x: int = 300, y: int = 120) -> tuple[np.ndarray, list]:
    """Setzt die Tafel in ein groesseres Bild und liefert ihr Viereck."""
    bild = np.full((BILD_H, BILD_B, 3), 60, dtype=np.uint8)
    h, b = t.shape[:2]
    bild[y:y + h, x:x + b] = t
    quad = [[x, y], [x + b, y], [x + b, y + h], [x, y + h]]
    return bild, quad


class TestQuadGroesse:
    def test_ein_rechteck_behaelt_seine_masse(self):
        assert quad_groesse([[0, 0], [100, 0], [100, 50], [0, 50]]) == (100, 50)

    def test_gemittelt_ueber_gegenueberliegende_kanten(self):
        """Eine schraeg gesehene Tafel hat verschieden lange Kanten."""
        b, h = quad_groesse([[0, 0], [100, 0], [90, 50], [0, 50]])
        assert b == 95 and h == 50


class TestEntzerren:
    def test_die_tafel_kommt_gerade_heraus(self):
        t = tafel()
        bild, quad = szene(t)
        zurueck = entzerre(bild, quad, (t.shape[1], t.shape[0]))
        assert zurueck.shape == t.shape
        assert float(np.abs(zurueck.astype(int) - t.astype(int)).mean()) < 3


class TestPlausibilitaet:
    """Die Pruefung, die den 1429-Pixel-Fehltreffer abgefangen haette."""

    def gut(self):
        return np.float32([[100, 100], [220, 100], [220, 230], [100, 230]])

    def test_ein_normales_viereck_geht_durch(self):
        assert ist_plausibel(self.gut(), (BILD_H, BILD_B), (120, 130)) is None

    def test_weit_ausserhalb_wird_abgelehnt(self):
        weit = self.gut() + 2000
        grund = ist_plausibel(weit, (BILD_H, BILD_B), (120, 130))
        assert grund is not None and "ausserhalb" in grund

    def test_viel_zu_klein_wird_abgelehnt(self):
        klein = np.float32([[10, 10], [30, 10], [30, 30], [10, 30]])
        grund = ist_plausibel(klein, (BILD_H, BILD_B), (120, 130))
        assert grund is not None and "Groesse" in grund

    def test_verdrehte_ecken_werden_abgelehnt(self):
        q = self.gut()[[0, 2, 1, 3]]         # Ecken vertauscht
        assert ist_plausibel(q, (BILD_H, BILD_B), (120, 130)) is not None

    def test_unendliche_werte_werden_abgelehnt(self):
        q = self.gut().copy()
        q[0, 0] = np.inf
        grund = ist_plausibel(q, (BILD_H, BILD_B), (120, 130))
        assert grund is not None and "Zahlen" in grund


class TestFinden:
    def test_die_tafel_wird_wiedergefunden(self):
        t = tafel()
        bild, quad = szene(t, x=300, y=120)
        finder = BoardFinder(min_inlier=10)
        treffer = finder.finde(bild, [t])
        assert treffer is not None, "die Vorlage steckt unveraendert im Bild"
        abweichung = np.linalg.norm(
            np.float32(treffer.quad) - np.float32(quad), axis=1).max()
        assert abweichung < 3.0, f"Ecken {abweichung:.1f} px daneben"

    def test_auch_an_einer_anderen_stelle(self):
        t = tafel()
        bild, quad = szene(t, x=80, y=200)
        treffer = BoardFinder(min_inlier=10).finde(bild, [t])
        assert treffer is not None
        abweichung = np.linalg.norm(
            np.float32(treffer.quad) - np.float32(quad), axis=1).max()
        assert abweichung < 3.0

    def test_was_nicht_da_ist_wird_nicht_gefunden(self):
        """Der wichtigste Test: ein Fehltreffer muss als solcher enden."""
        leer = np.full((BILD_H, BILD_B, 3), 60, dtype=np.uint8)
        assert BoardFinder(min_inlier=10).finde(leer, [tafel()]) is None

    def test_eine_fremde_tafel_wird_nicht_verwechselt(self):
        fremd = tafel(keim=99)
        bild, _ = szene(fremd)
        treffer = BoardFinder(min_inlier=18).finde(bild, [tafel(keim=7)])
        assert treffer is None, "zwei verschiedene Muster duerfen nicht passen"


class TestMehrereVorlagen:
    """GEMESSEN: Aus einem Frame mit einer Person neben der Tafel scheiterte
    Bahn 5 vollstaendig -- aus jedem anderen Frame gelang sie. Deshalb
    mehrere Vorlagen und die beste nehmen."""

    def test_eine_unbrauchbare_vorlage_verdirbt_nichts(self):
        t = tafel()
        bild, quad = szene(t)
        unbrauchbar = np.full_like(t, 30)          # strukturlos
        treffer = BoardFinder(min_inlier=10).finde(bild, [unbrauchbar, t])
        assert treffer is not None
        assert treffer.vorlage_index == 1, "die brauchbare muss gewinnen"

    def test_ohne_vorlagen_kein_treffer(self):
        bild, _ = szene(tafel())
        assert BoardFinder().finde(bild, []) is None


class TestSchwelleWirkt:
    def test_eine_hohe_schwelle_lehnt_ab(self):
        t = tafel()
        bild, _ = szene(t)
        assert BoardFinder(min_inlier=100000).finde(bild, [t]) is None

    def test_guete_ist_der_anteil_tragender_paare(self):
        t = tafel()
        bild, _ = szene(t)
        treffer = BoardFinder(min_inlier=10).finde(bild, [t])
        assert 0.0 < treffer.guete <= 1.0
        assert treffer.inlier <= treffer.paare


class TestSchlechteEingaben:
    def test_leeres_zielbild(self):
        assert BoardFinder().finde(np.zeros((0, 0, 3), np.uint8),
                                   [tafel()]) is None

    def test_none_als_zielbild(self):
        assert BoardFinder().finde(None, [tafel()]) is None

    def test_graustufen_gehen_auch(self):
        t = tafel()
        bild, _ = szene(t)
        grau = cv2.cvtColor(bild, cv2.COLOR_BGR2GRAY)
        assert BoardFinder(min_inlier=10).finde(grau, [t]) is not None


@pytest.mark.parametrize("versatz", [(0, 0), (50, 30), (200, 100)])
def test_versatz_wird_aufaddiert(versatz):
    """Fuer die Suche in einem Ausschnitt des Vollbilds."""
    t = tafel()
    bild, quad = szene(t)
    treffer = BoardFinder(min_inlier=10).finde(bild, [t], versatz=versatz)
    assert treffer is not None
    erwartet = np.float32(quad) + np.float32(versatz)
    # Der Versatz verschiebt das Ergebnis -- die Plausibilitaetspruefung
    # laeuft VOR der Verschiebung, deshalb bleibt der Treffer gueltig.
    assert np.linalg.norm(np.float32(treffer.quad) - erwartet,
                          axis=1).max() < 3.0
