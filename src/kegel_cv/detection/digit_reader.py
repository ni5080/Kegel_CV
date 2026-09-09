"""Ziffernerkennung auf Basis einzeln kalibrierter Stellen.

Der Weg hierher, alles am Material gemessen:

    Segment-Dekodierung, Rot-Maske      0/12
    Segment-Dekodierung, Otsu-Maske     5/12
    Template Matching, Feld geteilt     6/11
    + zeitliche Aggregation             7/12
    + automatisch gemessenes Raster     1/11   (schlechter!)

Alle Varianten scheiterten an derselben Stelle: **der Positionierung der
Ziffernzellen**. Ein Feld in N gleiche Teile zu zerlegen trifft die echten
Ziffergrenzen nicht -- gemessen liegen sie bei x = 5|15|26|38|49, waehrend die
gleichmaessige Teilung 0|13|26|40|53 annimmt. Bei 13x18 px je Ziffer ist das
fast eine halbe Ziffernbreite Versatz.

Dieses Modul dreht den Spiess um: **Der Nutzer rahmt jede Ziffer einzeln ein.**
Damit ist die Position exakt bekannt, und die Segmentflaechen ergeben sich direkt
aus der Ziffernbox -- horizontal gedrittelt, vertikal halbiert:

    +---------+   a = obere Kante          b = rechts oben
    | a  a  a |   g = Mitte                f = links oben
    |f       b|   d = untere Kante         c = rechts unten
    | g  g  g |                            e = links unten
    |e       c|
    | d  d  d |
    +---------+

Der kleine Rand um die Box (`digit_padding`) faengt ab, dass der Nutzer beim
Einrahmen naturgemaess nicht pixelgenau trifft.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from ..config.schema import DigitDetectionConfig
from .digit_detector import DigitReading, SevenSegmentDetector

log = logging.getLogger(__name__)

# Bitmuster je Ziffer: (a, b, c, d, e, f, g)
SEGMENT_PATTERNS: dict[tuple[bool, ...], int] = {
    (True, True, True, True, True, True, False): 0,
    (False, True, True, False, False, False, False): 1,
    (True, True, False, True, True, False, True): 2,
    (True, True, True, True, False, False, True): 3,
    (False, True, True, False, False, True, True): 4,
    (True, False, True, True, False, True, True): 5,
    (True, False, True, True, True, True, True): 6,
    (True, True, True, False, False, False, False): 7,
    (True, True, True, True, True, True, True): 8,
    (True, True, True, True, False, True, True): 9,

    # ALTERNATIVE SCHREIBWEISEN dieser Anlage.
    #
    # GESEHEN im Videomaterial (Bahn 5, Frames 4526/4990/9352; Bahn 2, 4990):
    # Die FUNK-Tafel zeichnet die 9 OHNE den unteren Querbalken -- also
    # "abcfg" statt "abcdfg". Das ist keine Fehlmessung, sondern die Bauform
    # der Anzeige; auf dem Standbild ist die Ziffer eindeutig als 9 zu lesen.
    #
    # Was ohne diesen Eintrag geschah: "abcfg" stand in keiner Tabelle, also
    # suchte die Notfallsuche das naechstliegende bekannte Muster. Das ist
    # "bcfg" = 4, genau ein Segment entfernt -- und aus jeder 9 wurde eine 4.
    # Der Fehler war dadurch besonders tueckisch, dass er wie ein
    # Kalibrierungsproblem aussah: Segment d mass 0.00, als laege es
    # ausserhalb des Rahmens. Es leuchtet schlicht nie.
    (True, True, True, False, False, True, True): 9,

    # Aus demselben Grund mitgefuehrt: die 6 ohne oberen Querbalken. Noch
    # NICHT im Material beobachtet -- wer beide Varianten der 9 baut, baut
    # ueblicherweise auch diese. Eindeutig bleibt es: "cdefg" kollidiert mit
    # keinem anderen Muster.
    (False, False, True, True, True, True, True): 6,
}
SEGMENT_ORDER = ("a", "b", "c", "d", "e", "f", "g")

# Zielgroesse einer einzelnen Ziffer fuer die Auswertung
CELL_WIDTH = 24
CELL_HEIGHT = 40


def segment_regions(width: int = CELL_WIDTH,
                    height: int = CELL_HEIGHT) -> dict[str, tuple[int, int, int, int]]:
    """Segmentflaechen einer exakt eingerahmten Ziffer.

    Die Aufteilung ist rein geometrisch -- moeglich nur, weil die Ziffernbox
    kalibriert ist und nicht geschaetzt werden muss:

        horizontal: Drittel (links | mitte | rechts)
        vertikal:   obere Haelfte | untere Haelfte

    Die Flaechen sind von den Ecken weggerueckt: Dort treffen zwei Segmente
    aufeinander, eine Messung waere mehrdeutig.
    """
    def box(x0: float, y0: float, x1: float, y1: float) -> tuple[int, int, int, int]:
        px0, py0 = int(x0 * width), int(y0 * height)
        px1, py1 = int(x1 * width), int(y1 * height)
        return px0, py0, max(1, px1 - px0), max(1, py1 - py0)

    # Die WAAGERECHTEN Segmente werden bewusst nur im mittleren Drittel gemessen.
    #
    # GEMESSEN und schmerzhaft gelernt: Eine zu breite Messflaeche fuer "g"
    # erfasst die senkrechten Segmente links (e, f) und rechts (b, c) mit. Jede
    # "0" wurde dadurch als "8" gelesen -- die Trefferquote fiel auf 17 %.
    # Am Rand der Ziffer liegen immer Segmente; nur die Mitte ist eindeutig.
    #
    # Die SENKRECHTEN Segmente werden am aeusseren Viertel gemessen und von der
    # Mittellinie weggerueckt, wo sie sich mit "g" beruehren wuerden.
    return {
        "a": box(0.30, 0.00, 0.70, 0.16),
        "g": box(0.34, 0.42, 0.66, 0.58),
        "d": box(0.30, 0.84, 0.70, 1.00),
        "f": box(0.00, 0.14, 0.26, 0.44),
        "b": box(0.74, 0.14, 1.00, 0.44),
        "e": box(0.00, 0.56, 0.26, 0.86),
        "c": box(0.74, 0.56, 1.00, 0.86),
    }


def segment_candidates(fills: list[float], threshold: float,
                       band: float) -> tuple[int, ...]:
    """Welche Ziffern kommen fuer diese Segmentmessung in Frage?

    Zurueckgegeben wird die direkte Lesung plus alle Ziffern, die sich ergaeben,
    wenn ein Segment NAHE DER SCHWELLE anders ausfiele.

    GEMESSEN auf Bahn 5 ueber zehn aufeinanderfolgende Frames: Segment a lag
    konstant bei 0,333, die Schwelle bei 0,288-0,326. Es galt damit als aktiv,
    und aus "bcfg" (4) wurde "abcfg" (9) -- die Anzeigetafel zeigte im selben
    Frame nachweislich `005 4 0029`.

    Seit BUG-009 stehen beide Muster in der Tabelle und unterscheiden sich in
    genau EINEM Segment. Eine solche Messung KANN aus sich heraus nicht
    entscheiden. Statt zu raten oder zu schweigen, wird die Auswahl
    weitergereicht: Eine andere Quelle -- die Kegellampen -- kann sie aufloesen.

    Dass die Pruefung dabei ehrlich bleibt, liegt an der Richtung: Die Lampen
    duerfen nur zwischen den Kandidaten WAEHLEN, nicht einen neuen Wert setzen.
    Melden sie 7, waehrend {4, 9} zur Wahl stehen, bleibt es ein Widerspruch.
    """
    active = tuple(f >= threshold for f in fills)
    moeglich: list[int] = []

    direkt = SEGMENT_PATTERNS.get(active)
    if direkt is not None:
        moeglich.append(direkt)

    if band > 0:
        for i, fill in enumerate(fills):
            if abs(fill - threshold) > band:
                continue
            gekippt = list(active)
            gekippt[i] = not gekippt[i]
            andere = SEGMENT_PATTERNS.get(tuple(gekippt))
            if andere is not None and andere not in moeglich:
                moeglich.append(andere)

    return tuple(sorted(moeglich))


def is_ambiguous(fills: list[float], threshold: float, band: float) -> bool:
    """Laesst die Messung mehr als eine Ziffer zu?"""
    return len(segment_candidates(fills, threshold, band)) > 1


class CalibratedDigitReader:
    """Liest Ziffern aus einzeln kalibrierten Stellen-ROIs."""

    def __init__(self, cfg: DigitDetectionConfig) -> None:
        self.cfg = cfg
        self._preprocessor = SevenSegmentDetector(cfg)
        self._regions = segment_regions()

    def read_digit(self, patch: np.ndarray) -> tuple[str, float]:
        zeichen, confidence, _ = self.read_digit_full(patch)
        return zeichen, confidence

    def read_digit_full(
            self, patch: np.ndarray) -> tuple[str, float, tuple[int, ...]]:
        """Dekodiert eine einzelne, exakt eingerahmte Ziffer."""
        if patch is None or patch.size == 0:
            return "?", 0.0, ()

        # Ist die Anzeige ueberhaupt beleuchtet?
        #
        # Diese Pruefung ist noetig, WEIL Otsu normalisiert: Es findet auch in
        # einem fast schwarzen Ausschnitt eine Schwelle und macht aus blossem
        # Rauschen eine scheinbare Ziffer. GEMESSEN wurde dabei bevorzugt "8" --
        # das Muster mit allen sieben Segmenten -- und dieser Phantomwert
        # widersprach dann der Lampenzaehlung.
        #
        # WORAUF gemessen wird, entscheidet mehr als die Schwelle selbst.
        #
        # Frueher galt das 95. Perzentil ueber die ganze Zelle. Das verwarf
        # lesbare Ziffern: Eine "1" leuchtet mit zwei von sieben Segmenten und
        # bleibt gemittelt dunkler als jede andere Ziffer. GEMESSEN auf Bahn 5,
        # F40903 -- beide Zellen zeigten im Bild eine eindeutige 1:
        #     throw_number[2]   95. Perzentil 220   Maximum 254   verworfen
        #     total_b[2]        95. Perzentil 229   Maximum 255   verworfen
        #
        # GEMESSEN ueber 4800 Zellen, Anteil im unsicheren Bereich 150-245:
        #     95. Perzentil  24,9 %   |   99. Perzentil  6,5 %   |  Maximum  3,6 %
        # Dunkle Zelle: Maximum 114-119. Leuchtende Zelle: 246-255.
        if self.cfg.brightness_percentile >= 100.0:
            helligkeit = float(patch[:, :, 2].max())
        else:
            helligkeit = float(np.percentile(patch[:, :, 2],
                                             self.cfg.brightness_percentile))
        if helligkeit < self.cfg.min_display_brightness:
            return "?", 0.0, ()

        mask = self._preprocessor._red_mask(patch)
        if mask.max() == 0:
            return "?", 0.0, ()

        # Vertikal auf den tatsaechlichen Ziffernumriss beschneiden.
        #
        # Der kalibrierte Rahmen sitzt nie exakt: Er wird von Hand gesetzt und
        # bekommt zusaetzlich `digit_padding` Luft. Diese Luft verschiebt die
        # geometrischen Drittel, und die aeussersten Segmente rutschen aus ihrer
        # Messflaeche.
        #
        # GEMESSEN auf Bahn 5 an drei Wuerfen, deren Tafel klar "9" zeigte:
        #     a=0.24  b=0.61  c=0.51  d=0.00  e=0.00  f=0.30  g=0.70
        # Segment d lag mit 0.00 komplett ausserhalb, a mit 0.17-0.38 auf der
        # Kippe -- gelesen wurde "4" (bcfg) statt "9" (abcdfg). Genau die beiden
        # WAAGERECHTEN Segmente fehlten, also die aeussersten.
        #
        # Der Zuschnitt ist nur VERTIKAL zulaessig, nicht horizontal: Jede
        # 7-Segment-Ziffer nutzt die volle Hoehe (auch die "1" -- b und c
        # zusammen reichen von oben bis unten), aber die "1" nutzt eben NICHT
        # die volle Breite. Ein horizontaler Zuschnitt zoege sie auf die ganze
        # Zelle und machte sie unlesbar.
        trimmed = self._preprocessor._trim_vertical(mask)
        if trimmed.size and trimmed.max() > 0:
            mask = trimmed

        cell = cv2.resize(mask, (CELL_WIDTH, CELL_HEIGHT),
                          interpolation=cv2.INTER_AREA)

        fills: list[float] = []
        for name in SEGMENT_ORDER:
            x, y, w, h = self._regions[name]
            region = cell[y:y + h, x:x + w]
            fills.append(float(region.mean() / 255.0) if region.size else 0.0)

        threshold = self._threshold(fills)
        active = tuple(f >= threshold for f in fills)

        # Haengt das Ergebnis an einem Segment, das auf der Schwelle liegt?
        #
        # GEMESSEN auf Bahn 5: Segment a lag konstant bei 0,333, die Schwelle
        # bei 0,288-0,326. Damit galt es als aktiv, und aus "bcfg" (4) wurde
        # "abcfg" (9) -- die Tafel zeigte nachweislich eine 4.
        #
        # Beide Muster unterscheiden sich seit BUG-009 in genau einem Segment.
        # Wenn ein Umkippen dieses einen Segments eine ANDERE gueltige Ziffer
        # ergaebe, ist die Lesung geraten. Dann lieber "?": Die Ziffer ist
        # Gegenprobe zu den Lampen, und eine falsche Gegenprobe ist schaedlicher
        # als gar keine -- sie erzeugt einen Widerspruch, wo keiner ist.
        # Mehrdeutige Lesungen liefern KEINE Ziffer, aber ihre Kandidaten --
        # eine andere Quelle kann sie aufloesen (siehe segment_candidates).
        kandidaten = segment_candidates(fills, threshold,
                                        self.cfg.segment_ambiguous_band)
        if len(kandidaten) > 1:
            return "?", 0.0, kandidaten

        digit = SEGMENT_PATTERNS.get(active)

        if digit is None:
            # Naechstliegendes Muster suchen, aber die Unsicherheit ausweisen
            best, distance = None, 99
            for pattern, value in SEGMENT_PATTERNS.items():
                d = sum(1 for p, a in zip(pattern, active) if p != a)
                if d < distance:
                    best, distance = value, d
            if best is None or distance > 1:
                return "?", 0.0, kandidaten
            return str(best), 0.35, kandidaten or (best,)

        margins = [abs(f - threshold) for f in fills]
        return (str(digit), min(1.0, 0.5 + 2.0 * min(margins)),
                kandidaten or (digit,))

    def _threshold(self, fills: list[float]) -> float:
        """Schwelle RELATIV zum hellsten Segment der Ziffer.

        Ein fester Wert traegt nicht: Gemessen lagen echte Werte bei 0,25
        (aktiv) und 0,39 (inaktiv) -- beidseitig knapp an einer festen Schwelle
        vorbei.

        Die naheliegende Alternative -- die groesste Luecke in den sortierten
        Fuellgraden -- traegt ebenfalls nicht. GEMESSEN an einer "0":

            g=0,10 | a=0,26  f=0,27 | e=0,49  c=0,61  d=0,64  b=0,69
                              groesste Luecke liegt HIER (0,27 -> 0,49)

        Bei einer "0" sind sechs Segmente aktiv und nur eines aus. Die groesste
        Luecke liegt dann *innerhalb* der aktiven Segmente, und die Schwelle
        landet viel zu hoch -- die Ziffer wurde unlesbar.

        Verlaesslich ist dagegen: Das hellste Segment einer Ziffer ist immer
        aktiv. Alles, was einen nennenswerten Bruchteil davon erreicht, ist es
        auch. Die Untergrenze verhindert, dass bei dunkler Anzeige blosses
        Rauschen als Segment zaehlt.
        """
        peak = max(fills) if fills else 0.0
        if peak <= 0:
            return self.cfg.segment_on_ratio
        return max(self.cfg.segment_floor, self.cfg.segment_relative_ratio * peak)

    def read_field(self, patches: list[np.ndarray]) -> DigitReading:
        """Liest ein Feld aus den Ausschnitten seiner einzelnen Stellen."""
        if not patches:
            return DigitReading.unreadable("keine kalibrierten Stellen")

        characters: list[str] = []
        scores: list[float] = []
        kandidaten: list[tuple[int, ...]] = []
        for patch in patches:
            character, score, moeglich = self.read_digit_full(patch)
            characters.append(character)
            scores.append(score)
            kandidaten.append(moeglich)

        text = "".join(characters)
        value = int(text) if text.isdigit() else None
        confidence = float(np.mean(scores)) if scores else 0.0
        if value is None:
            confidence = min(confidence, 0.3)

        return DigitReading(text=text, value=value, confidence=confidence,
                            candidates=tuple(kandidaten),
                            digits=tuple(characters), scores=tuple(scores))
