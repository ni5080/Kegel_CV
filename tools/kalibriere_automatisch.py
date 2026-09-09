#!/usr/bin/env python
"""Kalibriert ein Video automatisch anhand einer bestehenden Kalibrierung.

DIE IDEE (vom Nutzer, 2026-09-09)

    "sobald ich einen Bahntyp kalibriert habe, sollte das meines Erachtens
     sehr gut funktionieren, dass ein Algorithmus ueber 'Bild in Bild' Suche
     das mindestens genauso gut kalibrieren kann wie ich."

Und das stimmt: Die ROIs liegen in NORMIERTEN Tafelkoordinaten. Sind die vier
Ecken gefunden, folgen alle Lampen und Ziffern daraus -- ohne weiteren Klick.

WAS DAS WERKZEUG TUT

1. Aus dem VORLAGENVIDEO mehrere entzerrte Tafelbilder je Bahn schneiden
   (mehrere, weil eine einzelne Vorlage unbrauchbar sein kann -- gemessen:
   aus einem Frame mit einer Person neben der Tafel scheiterte Bahn 5
   vollstaendig).
2. Diese Vorlagen im ZIELVIDEO wiederfinden.
3. Die ROIs der Vorlage unveraendert uebernehmen und als neue Kalibrierung
   speichern.

Bahnen, die nicht sicher gefunden werden, kommen NICHT in die neue
Kalibrierung. Lieber eine fehlende Bahn, die auffaellt, als eine falsch
platzierte, die still Unsinn misst.

    .venv/Scripts/python.exe tools/kalibriere_automatisch.py \
        --vorlage data/calibrations/Training.json \
        --vorlagen-video debug/....mp4 \
        --ziel-video kegelVideos/neu.mp4 \
        --ausgabe data/calibrations/Neu.json
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kegel_cv.calibration.board_finder import (BoardFinder, entzerre,  # noqa: E402
                                               quad_groesse)
from kegel_cv.calibration.model import Calibration  # noqa: E402
from kegel_cv.config import load_config  # noqa: E402
from kegel_cv.video.factory import open_source  # noqa: E402

log = logging.getLogger("kalibriere_automatisch")


def hole_frames(pfad: str, indizes: list[int], cfg) -> dict[int, np.ndarray]:
    """Liest genau die genannten Frames -- ohne zu springen.

    Sequentiell statt `seek`: Bei einem Stream gibt es kein Zurueck, und bei
    einer Datei ist der Sprung auf ein Schluesselbild ungenau. Fuer ein paar
    tausend Frames ist das schnell genug.
    """
    gesucht = set(indizes)
    quelle = open_source(pfad, cfg)
    quelle.open()
    bilder: dict[int, np.ndarray] = {}
    n = 0
    try:
        while n <= max(gesucht):
            f = quelle.read()
            if f is None:
                break
            n += 1
            if n in gesucht:
                bilder[n] = f.image.copy()
    finally:
        quelle.close()
    return bilder


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vorlage", required=True, type=Path,
                   help="bestehende Kalibrierung (JSON)")
    p.add_argument("--vorlagen-video", required=True,
                   help="Video, zu dem die Vorlage passt")
    p.add_argument("--ziel-video", required=True,
                   help="Video, das kalibriert werden soll")
    p.add_argument("--ausgabe", required=True, type=Path)
    p.add_argument("--vorlagen-frames", default="1500,3000,6000,9000",
                   help="aus diesen Frames werden die Vorlagen geschnitten")
    p.add_argument("--ziel-frame", type=int, default=300,
                   help="in diesem Frame des Zielvideos wird gesucht")
    p.add_argument("--min-inlier", type=int, default=18,
                   help="weniger tragende Merkmale gelten als kein Treffer")
    a = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = load_config()
    kal = Calibration.load(a.vorlage)
    if not kal.lanes:
        print("Die Vorlagenkalibrierung enthaelt keine Bahn.")
        return 1

    vorlagen_frames = [int(x) for x in a.vorlagen_frames.split(",")]
    print(f"Vorlagen aus {a.vorlagen_video}, Frames {vorlagen_frames}")
    quelle_bilder = hole_frames(a.vorlagen_video, vorlagen_frames, cfg)
    if not quelle_bilder:
        print("Aus dem Vorlagenvideo kam kein Frame.")
        return 1

    print(f"Zielbild aus {a.ziel_video}, Frame {a.ziel_frame}")
    ziel_bilder = hole_frames(a.ziel_video, [a.ziel_frame], cfg)
    ziel = ziel_bilder.get(a.ziel_frame)
    if ziel is None:
        print("Aus dem Zielvideo kam kein Frame.")
        return 1

    finder = BoardFinder(min_inlier=a.min_inlier)
    gefunden = []
    for bahn in kal.lanes:
        groesse = quad_groesse(bahn.quad)
        vorlagen = [entzerre(b, bahn.quad, groesse)
                    for b in quelle_bilder.values()]
        treffer = finder.finde(ziel, vorlagen)
        if treffer is None:
            print(f"  Bahn {bahn.display_number}: NICHT gefunden "
                  f"-- bleibt aussen vor")
            continue
        abstand = np.linalg.norm(
            np.float32(treffer.quad) - np.float32(bahn.quad), axis=1).mean()
        print(f"  Bahn {bahn.display_number}: gefunden, {treffer.inlier} von "
              f"{treffer.paare} Merkmalen tragen ({treffer.guete:.0%}), "
              f"Vorlage {vorlagen_frames[treffer.vorlage_index]}, "
              f"Verschiebung gegenueber der Vorlage {abstand:.1f} px")
        neu = bahn.model_copy(deep=True)
        neu.quad = treffer.quad
        gefunden.append(neu)

    if not gefunden:
        print("\nKeine einzige Bahn gefunden. Passt der Bahntyp zusammen?")
        return 2

    ergebnis = kal.model_copy(deep=True)
    ergebnis.lanes = gefunden
    ergebnis.name = a.ausgabe.stem
    hoehe, breite = ziel.shape[:2]
    ergebnis.source_hint = type(kal.source_hint)(
        width=breite, height=hoehe, video=str(a.ziel_video))
    a.ausgabe.parent.mkdir(parents=True, exist_ok=True)
    ergebnis.save(a.ausgabe)

    print(f"\n{len(gefunden)} von {len(kal.lanes)} Bahnen -> {a.ausgabe}")
    if len(gefunden) < len(kal.lanes):
        print("Die fehlenden Bahnen von Hand nachkalibrieren -- oder es mit "
              "einem anderen --ziel-frame versuchen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
