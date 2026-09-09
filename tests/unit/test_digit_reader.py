"""Der kalibrierte Ziffernleser.

Schwerpunkt: die Faelle, in denen NICHT gelesen werden darf. Die Ziffern sind
Gegenprobe zu den Lampen -- eine falsche Gegenprobe ist schaedlicher als gar
keine, weil sie einen Widerspruch erzeugt, wo keiner ist.
"""

from __future__ import annotations

import numpy as np
import pytest

from kegel_cv.config.schema import DigitDetectionConfig
from kegel_cv.detection.digit_reader import (CELL_HEIGHT, CELL_WIDTH,
                                             CalibratedDigitReader,
                                             segment_candidates,
                                             segment_regions)


def ziffer_patch(segmente: str, teilweise: dict[str, float] | None = None,
                 skalierung: int = 6) -> np.ndarray:
    """Baut den Ausschnitt einer 7-Segment-Ziffer.

    Args:
        segmente: die vollstaendig leuchtenden Segmente, z. B. "bcfg" fuer 4.
        teilweise: Segmente mit ihrem Fuellgrad (0..1) -- fuer Grenzfaelle.
    """
    hoehe, breite = CELL_HEIGHT * skalierung, CELL_WIDTH * skalierung
    patch = np.zeros((hoehe, breite, 3), dtype=np.uint8)
    patch[:, :] = (10, 10, 20)                       # dunkler Hintergrund

    for name, (x, y, w, h) in segment_regions(breite, hoehe).items():
        anteil = 1.0 if name in segmente else (teilweise or {}).get(name, 0.0)
        if anteil <= 0:
            continue
        zeilen = max(1, int(round(h * anteil)))
        if anteil < 1.0 and name in ("a", "d", "g"):
            # Teilweise leuchtende WAAGERECHTE Segmente ueber die volle Breite
            # zeichnen, damit sie die senkrechten Segmente beruehren.
            #
            # Sonst steht der Fleck frei im Bild und wird von
            # `_drop_small_components` als Rauschen verworfen -- der Testfall
            # traefe dann gar nicht das, was er pruefen soll. Im echten Material
            # entsteht der Teilausschlag durch Uebersprechen der benachbarten
            # senkrechten Segmente und haengt deshalb am Ziffernkoerper.
            #
            # Bewusst NICHT ueber die volle Breite: `_trim_vertical` entfernt
            # Zeilen, die zu mehr als 92 % gefuellt sind (Gehaeusestreifen).
            links = int(0.18 * breite)
            x, w = links, breite - 2 * links
        patch[y:y + zeilen, x:x + w] = (20, 20, 255)  # gesaettigtes Rot
    return patch


@pytest.fixture
def cfg() -> DigitDetectionConfig:
    return DigitDetectionConfig()


@pytest.fixture
def reader(cfg) -> CalibratedDigitReader:
    return CalibratedDigitReader(cfg)


class TestGrundlagen:
    @pytest.mark.parametrize("segmente,erwartet", [
        ("abcdef", "0"), ("bc", "1"), ("abdeg", "2"), ("abcdg", "3"),
        ("bcfg", "4"), ("acdfg", "5"), ("acdefg", "6"), ("abc", "7"),
        ("abcdefg", "8"), ("abcdfg", "9"),
    ])
    def test_alle_ziffern(self, reader, segmente, erwartet):
        zeichen, _ = reader.read_digit(ziffer_patch(segmente))
        assert zeichen == erwartet

    def test_bug_009_neun_ohne_unteren_balken(self, reader):
        """Die FUNK-Anlage zeichnet die 9 ohne den unteren Querbalken."""
        zeichen, _ = reader.read_digit(ziffer_patch("abcfg"))
        assert zeichen == "9"

    def test_dunkle_anzeige_wird_nicht_gelesen(self, reader):
        """Otsu normalisiert und macht aus Rauschen eine scheinbare Ziffer."""
        dunkel = np.full((CELL_HEIGHT * 6, CELL_WIDTH * 6, 3), 30, dtype=np.uint8)
        zeichen, confidence = reader.read_digit(dunkel)
        assert zeichen == "?"
        assert confidence == 0.0


class TestUnentschiedeneLesung:
    """Kippt die Ziffer an EINEM Segment auf der Schwelle, ist sie geraten.

    Geprueft wird die Entscheidungsregel selbst -- mit den am Material
    gemessenen Werten, nicht mit nachgebauten Bildern.
    """

    # GEMESSEN: Bahn 5, Frame 22269, Reihenfolge a,b,c,d,e,f,g.
    # Die Anzeigetafel zeigte im selben Frame `005 4 0029` -- also eine 4.
    # Gelesen wurde jedoch 'abcfg' = 9, weil a und f knapp ueber der Schwelle
    # lagen. Seit BUG-009 trennt 4 ("bcfg") von 9 ("abcfg") ein Segment.
    FILLS = [0.3333, 0.5714, 0.5170, 0.0000, 0.0239, 0.3333, 0.8778]
    SCHWELLE = 0.3072

    def test_gemessener_grenzfall_laesst_beide_ziffern_zu(self):
        assert segment_candidates(self.FILLS, self.SCHWELLE, band=0.06) == (4, 9)

    def test_ohne_band_wird_hart_entschieden(self):
        """Ohne Band bleibt die alte, falsche Lesung -- 9 statt 4."""
        assert segment_candidates(self.FILLS, self.SCHWELLE, band=0.0) == (9,)

    def test_eindeutige_ziffer_hat_nur_einen_kandidaten(self):
        """Eine 8: alle sieben Segmente klar aktiv, keines nahe der Schwelle."""
        assert segment_candidates([0.9] * 7, threshold=0.35, band=0.06) == (8,)

    def test_knappes_segment_ohne_alternative_bleibt_eindeutig(self):
        """Nicht jeder Grenzfall ist gefaehrlich: Ergibt das Umkippen KEIN
        gueltiges Muster, bleibt die Lesung eindeutig."""
        # "0" (abcdef) mit grenzwertigem e. Umgekippt ergaebe das "abcdf" --
        # dieses Muster steht in keiner Tabelle.
        fills = [0.9, 0.9, 0.9, 0.9, 0.36, 0.9, 0.0]
        assert segment_candidates(fills, threshold=0.35, band=0.06) == (0,)

    def test_ungueltiges_muster_mit_genau_einer_alternative(self):
        """Ist die direkte Lesung kein gueltiges Muster und fuehrt genau ein
        knappes Segment zu einer gueltigen Ziffer, ist die Auswahl eindeutig."""
        # "bce" ist kein gueltiges Muster; e umgekippt ergibt "bc" = 1
        fills = [0.0, 0.9, 0.9, 0.0, 0.36, 0.0, 0.0]
        assert segment_candidates(fills, threshold=0.35, band=0.06) == (1,)

    def test_ende_zu_ende_eindeutige_ziffer_bleibt_lesbar(self, reader):
        """Das Band darf nicht dazu fuehren, dass klare Ziffern ausfallen."""
        zeichen, confidence = reader.read_digit(ziffer_patch("abcdefg"))

        assert zeichen == "8"
        assert confidence > 0.0
