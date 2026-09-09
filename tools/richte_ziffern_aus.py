#!/usr/bin/env python
"""Verschiebt die Ziffernrahmen einer Kalibrierung um einen gemessenen Versatz.

WARUM ES DIESES WERKZEUG GIBT

Eine automatisch erzeugte Kalibrierung trifft die Tafelecken auf ein bis drei
Pixel genau. Fuer die Lampen genuegt das -- fuer die Ziffern nicht.

GEMESSEN 2026-09-09 an der YouTube-Aufzeichnung eines Verbandsligaspiels,
66 von Hand abgelesene Stellen:

    Versatz    richtig   falsch   unlesbar
      0 px      54        7         5        <- Ausgangslage
     -1 px      59        4         3        <- Optimum
     -2 px      45       19         2

EIN Pixel entscheidet ueber acht Prozentpunkte. Der Grund steckt im Leser:
Er beschneidet die Ziffer nur SENKRECHT -- eine "1" nutzt nicht die volle
Breite, ein waagerechter Zuschnitt zoege sie auf die ganze Zelle. Dann wird
auf eine feste Zellbreite skaliert. Sitzt der Rahmen ein Pixel zu weit rechts,
rutscht der Balken der "1" zur Zellmitte, und die WAAGERECHTEN Segmente
greifen: aus 1 wird 3. Genau diese Verwechslung war sechs von sieben Fehlern
und verschwindet mit dem Versatz vollstaendig.

WIE DER VERSATZ ZU BESTIMMEN IST

Nicht ueber die Lesesicherheit. `config/overlay.yaml` beschreibt, warum das
ein Denkfehler ist: Confidence misst die Schaerfe eines Mustertreffers, nicht
seine Richtigkeit -- so wurde aus "001" ein selbstbewusstes "081".

Stattdessen: Ausschnitte vergroessert darstellen, mit dem Auge ablesen, und
den Versatz suchen, der am besten mit dieser AEUSSEREN Wahrheit
uebereinstimmt. Das ist Handarbeit, aber sie faellt einmal je Quelle an.

    .venv/Scripts/python.exe tools/richte_ziffern_aus.py \
        --kalibrierung data/calibrations/Quelle.json --dx -1 --dy 0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kegel_cv.calibration.model import Calibration  # noqa: E402

# Diese ROIs tragen Ziffern; alles andere bleibt unberuehrt.
#
# ACHTUNG, HIER LAG EIN FEHLER: Die einzelnen Stellen heissen
# `digit_<feld>_<n>` -- ein Filter auf die Feldnamen allein trifft sie NICHT.
# Er verschiebt dann nur die Sammel-ROI des Feldes, die fuer das Lesen gar
# nicht benutzt wird, und die Messung sieht keinerlei Wirkung.
ZIFFERNFELDER = ("throw_number", "pin_count", "total_a", "total_b",
                 "left_display")
DIGIT_PRAEFIX = "digit_"


def ist_ziffern_roi(name: str, felder: tuple[str, ...]) -> bool:
    """Trifft sowohl das Sammelfeld als auch seine einzelnen Stellen."""
    if name.startswith(felder):
        return True
    if not name.startswith(DIGIT_PRAEFIX):
        return False
    return name[len(DIGIT_PRAEFIX):].startswith(felder)


def tafelbreite(quad) -> float:
    """Mittlere Kantenlaenge des Tafelvierecks in Pixeln."""
    q = np.float32(quad)
    return float((np.linalg.norm(q[1] - q[0])
                  + np.linalg.norm(q[2] - q[3])) / 2)


def tafelhoehe(quad) -> float:
    q = np.float32(quad)
    return float((np.linalg.norm(q[3] - q[0])
                  + np.linalg.norm(q[2] - q[1])) / 2)


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kalibrierung", required=True, type=Path)
    p.add_argument("--dx", type=float, required=True,
                   help="Versatz in Pixeln, negativ = nach links")
    p.add_argument("--dy", type=float, default=0.0,
                   help="Versatz in Pixeln, negativ = nach oben")
    p.add_argument("--ausgabe", type=Path, default=None,
                   help="Vorgabe: die Eingabedatei ueberschreiben")
    p.add_argument("--felder", default=",".join(ZIFFERNFELDER),
                   help="welche ROIs verschoben werden")
    a = p.parse_args()

    felder = tuple(f.strip() for f in a.felder.split(",") if f.strip())
    kal = Calibration.load(a.kalibrierung)
    if not kal.lanes:
        print("Die Kalibrierung enthaelt keine Bahn.")
        return 1

    geaendert = 0
    for bahn in kal.lanes:
        # Pixel -> normierte Tafelkoordinaten. Die ROIs liegen in 0..1 der
        # Tafel, nicht des Bildes -- deshalb durch die TAFELgroesse teilen.
        breite, hoehe = tafelbreite(bahn.quad), tafelhoehe(bahn.quad)
        if breite <= 0 or hoehe <= 0:
            print(f"Bahn {bahn.display_number}: unbrauchbares Viereck")
            continue
        nx, ny = a.dx / breite, a.dy / hoehe
        for roi in bahn.rois:
            if not ist_ziffern_roi(roi.name, felder):
                continue
            x, y, w, h = roi.rect
            neu = (min(max(x + nx, 0.0), 1.0), min(max(y + ny, 0.0), 1.0), w, h)
            roi.rect = neu
            geaendert += 1
        print(f"Bahn {bahn.display_number}: Tafel {breite:.0f}x{hoehe:.0f} px "
              f"-> Versatz {nx:+.5f} / {ny:+.5f} in Tafelkoordinaten")

    ziel = a.ausgabe or a.kalibrierung
    kal.save(ziel)
    print(f"\n{geaendert} Ziffern-ROIs verschoben -> {ziel}")
    print("Nachpruefen: Ausschnitte vergroessern und gegen das Auge halten. "
          "Ein Pixel entscheidet hier ueber acht Prozentpunkte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
