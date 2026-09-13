"""Kein Gesicht im Tafelbild -- auch nicht im Tafelausschnitt.

DER BEFUND (Nutzer, 2026-09-13):

    "im Liveticker, wo ja mittlerweile Bilder angezeigt werden, sieht man sehr
     haeufig noch Gesichter -> Immer dann, wenn sie Phantomwuerfe erzeugen."

UND SO WAR ES. Die Personenmaske nimmt die Tafelbereiche vom Schwaerzen aus --
zu Recht, dort steht das Signal: Ziffern und Lampen sind selbst bewegter
Vordergrund, wer sie schwaerzt, loescht die Messung. Genau dieses Rechteck geht
aber als `board_jpeg` an die Datenbank und in den Ticker. Wer vor der Tafel
stand, war im ganzen Bild geschwaerzt -- nur nicht dort, wo alle hinsehen.

Und weil dieselbe Person den Phantomwurf ausloest, tragen genau diese Wuerfe
ein Gesicht. BELEGT an der Produktivdatenbank, 1000 Bilder: 21 % der Wuerfe mit
"0 Kegel" zeigen eine verdeckte Tafel, gegen 0,8 % der uebrigen.

DIE TRENNLINIE, die diese Tests festhalten: Geschwaerzt wird im
VEROEFFENTLICHTEN Bild, nie in dem, was gemessen wird.
"""

from __future__ import annotations

import base64

import cv2
import numpy as np
import pytest

from kegel_cv.analysis.board_image import encode_board, schwaerze_menschen
from kegel_cv.detection.person_maske import PersonMaske


def tafelbild() -> np.ndarray:
    """Ein Bild mit einer hellen 'Tafel' auf dunklem Grund."""
    bild = np.full((240, 320, 3), 20, dtype=np.uint8)
    bild[60:140, 100:180] = (150, 160, 170)      # die Tafel
    bild[110:130, 110:170] = (40, 40, 200)       # rote Ziffernzeile
    return bild


TAFEL = (100, 60, 80, 80)


class TestDieMaskeWirktImAusschnitt:
    def test_ohne_maske_bleibt_alles_stehen(self):
        aus = tafelbild()[60:140, 100:180]
        assert schwaerze_menschen(aus, TAFEL, None) is aus

    def test_mit_maske_wird_geschwaerzt(self):
        aus = tafelbild()[60:140, 100:180].copy()
        menschen = np.zeros((240, 320), np.uint8)
        menschen[60:100, 100:180] = 255          # obere Haelfte der Tafel
        neu = schwaerze_menschen(aus, TAFEL, menschen, raster=1)
        assert neu[:40].max() == 0, "die obere Haelfte muss schwarz sein"
        assert neu[40:].max() > 0, "die untere darf es nicht sein"

    def test_das_original_bleibt_unangetastet(self):
        """Geschwaerzt wird eine KOPIE -- die Messung liest den Ausschnitt roh."""
        aus = tafelbild()[60:140, 100:180].copy()
        vorher = aus.copy()
        menschen = np.zeros((240, 320), np.uint8)
        menschen[60:140, 100:180] = 255
        schwaerze_menschen(aus, TAFEL, menschen, raster=1)
        assert np.array_equal(aus, vorher)

    def test_das_raster_wird_hochgerechnet(self):
        """Die Maske liegt verkleinert vor (Raster 4) -- 130 KB je Frame statt
        2 MB, und feiner muss es zum Schwaerzen nicht sein."""
        aus = tafelbild()[60:140, 100:180].copy()
        # Die Tafel (100, 60, 80x80) liegt im Raster 4 bei [15:35, 25:45].
        klein = np.zeros((60, 80), np.uint8)
        klein[15:35, 25:45] = 255
        neu = schwaerze_menschen(aus, TAFEL, klein, raster=4)
        assert neu.max() == 0

    def test_ein_halber_treffer_schwaerzt_auch_nur_halb(self):
        aus = tafelbild()[60:140, 100:180].copy()
        klein = np.zeros((60, 80), np.uint8)
        klein[15:25, 25:45] = 255                # nur die obere Haelfte
        neu = schwaerze_menschen(aus, TAFEL, klein, raster=4)
        assert neu[:40].max() == 0 and neu[40:].max() > 0

    def test_encode_board_reicht_sie_durch(self):
        menschen = np.zeros((240, 320), np.uint8)
        menschen[60:140, 100:180] = 255
        mit = encode_board(tafelbild(), TAFEL, 60, menschen, 1)
        ohne = encode_board(tafelbild(), TAFEL, 60)
        assert mit != ohne
        bild = cv2.imdecode(np.frombuffer(base64.b64decode(mit), np.uint8),
                            cv2.IMREAD_COLOR)
        assert bild.max() < 20, "der Ausschnitt muss schwarz ankommen"


class TestNurMenschgrosses:
    """Die Ziffernzeile darf NICHT mitgeloescht werden -- sonst zeigt das Bild
    nicht mehr, worauf das Ergebnis beruht."""

    def _maske(self, tafeln) -> PersonMaske:
        m = PersonMaske(history=50, scale=1, min_blob_px=0, dilate_px=1,
                        warmup_frames=0, person_min_blob_boards=0.5)
        m.set_tafeln(tafeln)
        return m

    def test_ein_kleiner_fleck_zaehlt_nicht(self):
        m = self._maske({2: TAFEL})
        klein = np.zeros((240, 320), np.uint8)
        klein[110:130, 110:170] = 255            # die Ziffernzeile, 0,19 Tafeln
        assert m._nur_menschen(klein) is None

    def test_ein_grosser_fleck_zaehlt(self):
        m = self._maske({2: TAFEL})
        gross = np.zeros((240, 320), np.uint8)
        gross[40:160, 80:200] = 255              # 2,25 Tafelflaechen
        ergebnis = m._nur_menschen(gross)
        assert ergebnis is not None and ergebnis.any()

    def test_ohne_tafeln_gibt_es_keine_ausnahme(self):
        """Ohne Schutzbereiche wird ohnehin alles geschwaerzt -- dann braucht
        es die zweite Maske nicht."""
        m = self._maske({})
        gross = np.zeros((240, 320), np.uint8)
        gross[40:160, 80:200] = 255
        assert m._nur_menschen(gross) is None

    def test_abschaltbar(self):
        m = PersonMaske(history=50, scale=1, warmup_frames=0,
                        person_min_blob_boards=0.0)
        m.set_tafeln({2: TAFEL})
        gross = np.zeros((240, 320), np.uint8)
        gross[40:160, 80:200] = 255
        assert m._nur_menschen(gross) is None


class TestDieMessungBleibtRoh:
    """Die wichtigste Eigenschaft: Was gemessen wird, wird nicht geschwaerzt."""

    def test_der_tafelbereich_im_analysebild_bleibt_hell(self):
        m = PersonMaske(history=5, scale=1, min_blob_px=0, dilate_px=1,
                        warmup_frames=0, person_min_blob_boards=0.5)
        m.set_tafeln({2: TAFEL})
        for _ in range(6):                       # Hintergrund lernen
            m.verarbeite(tafelbild())
        # Jetzt ein Mensch quer ueber die Tafel
        mit_mensch = tafelbild()
        mit_mensch[40:200, 60:220] = (90, 90, 90)
        ergebnis = m.verarbeite(mit_mensch)
        x, y, w, h = TAFEL
        assert ergebnis.bild[y:y + h, x:x + w].max() > 0, \
            "im Analysebild darf die Tafel nie geschwaerzt sein"

    def test_die_menschenmaske_kennt_ihn_trotzdem(self):
        m = PersonMaske(history=5, scale=1, min_blob_px=0, dilate_px=1,
                        warmup_frames=0, person_min_blob_boards=0.5)
        m.set_tafeln({2: TAFEL})
        for _ in range(6):
            m.verarbeite(tafelbild())
        mit_mensch = tafelbild()
        mit_mensch[40:200, 60:220] = (90, 90, 90)
        ergebnis = m.verarbeite(mit_mensch)
        assert ergebnis.menschen is not None
        x, y, w, h = TAFEL
        assert ergebnis.menschen[y:y + h, x:x + w].any(), \
            "fuer das veroeffentlichte Bild muss er bekannt sein"
        assert ergebnis.raster == 1
