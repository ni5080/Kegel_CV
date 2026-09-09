"""Bibliothek bekannter Tafeltypen -- damit eine Halle sich selbst erklaert.

DIE IDEE (vom Nutzer, 2026-09-09)

    "cool waere, wenn er standardmaessig wenn ein Stream startet schaut, ob er
     eins der bekannten Kegelboards aus seinem Repertoire kennt. Langfristig
     sollen alle typischen Boards selbststaendig erkannt werden."

Ein Tafeltyp besteht aus zwei Dingen:

* einem **Musterbild** -- die geradegerechnete Tafel, wie sie einmal
  aufgenommen wurde
* den **ROIs in normierten Tafelkoordinaten** -- wo Lampen und Ziffern auf
  dieser Bauart sitzen

Beides zusammen genuegt: Wird das Muster in einem neuen Bild wiedergefunden,
folgen alle Felder aus den vier gefundenen Ecken. Genau darauf beruht die
automatische Kalibrierung.

WAS EIN TYP NICHT IST: eine Halle. Dieselbe FUNK-Anlage steht in vielen
Vereinen. Der Typ beschreibt die BAUART, nicht den Ort -- deshalb traegt er
auch keine Adresse und keinen Vereinsnamen.

WIE SICHER IST SICHER GENUG

Die Zahl der tragenden Merkmale (RANSAC-Inlier) trennt sauber. GEMESSEN am
2026-09-09 ueber vier Tafeln in zwei verschiedenen Quellen: gelungene Treffer
hatten 15 bis 197 Merkmale, ein Fehltreffer 7 -- und der lag 1429 Pixel
daneben. Deshalb gilt ein Typ erst ab `min_inlier` als erkannt, und ein
erkannter Typ wird dem Nutzer VORGESCHLAGEN, nicht aufgezwungen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .board_finder import BoardFinder, Treffer, entzerre, quad_groesse
from .model import Calibration

log = logging.getLogger(__name__)

# Neben jedem Tafeltyp liegt sein Musterbild unter demselben Namen.
MUSTER_ENDUNG = ".png"


@dataclass
class Tafeltyp:
    """Eine bekannte Bauart: Musterbild plus die ROIs darauf."""

    name: str
    muster: np.ndarray
    kalibrierung: Calibration

    @property
    def bahn(self):
        """Die eine Bahn, die den Typ beschreibt."""
        return self.kalibrierung.lanes[0]


@dataclass
class Erkennung:
    """Ein erkannter Typ samt der gefundenen Tafeln."""

    typ: Tafeltyp
    treffer: list[Treffer]

    @property
    def merkmale(self) -> int:
        return sum(t.inlier for t in self.treffer)


def lade_bibliothek(ordner: str | Path) -> list[Tafeltyp]:
    """Liest alle Tafeltypen aus einem Ordner.

    Ein Typ, dessen Musterbild fehlt, wird uebersprungen statt zu werfen: Eine
    unvollstaendige Bibliothek darf den Programmstart nicht verhindern.
    """
    ordner = Path(ordner)
    if not ordner.is_dir():
        return []

    typen: list[Tafeltyp] = []
    for pfad in sorted(ordner.glob("*.json")):
        bild_pfad = pfad.with_suffix(MUSTER_ENDUNG)
        if not bild_pfad.is_file():
            log.warning("Tafeltyp %s hat kein Musterbild (%s erwartet)",
                        pfad.stem, bild_pfad.name)
            continue
        muster = cv2.imread(str(bild_pfad))
        if muster is None:
            log.warning("Musterbild %s liess sich nicht lesen", bild_pfad.name)
            continue
        try:
            kal = Calibration.load(pfad)
        except Exception as exc:  # noqa: BLE001
            # Eine kaputte Datei darf die uebrigen Typen nicht mitnehmen.
            log.warning("Tafeltyp %s unbrauchbar: %s", pfad.stem, exc)
            continue
        if not kal.lanes:
            log.warning("Tafeltyp %s enthaelt keine Bahn", pfad.stem)
            continue
        typen.append(Tafeltyp(name=pfad.stem, muster=muster, kalibrierung=kal))
    log.info("Tafelbibliothek: %d Typen aus %s", len(typen), ordner)
    return typen


def erkenne(bild: np.ndarray, typen: list[Tafeltyp], *,
            min_inlier: int = 18, max_tafeln: int = 8) -> Erkennung | None:
    """Sucht den Typ, der am besten zu diesem Bild passt.

    Gewertet wird nach der Zahl der TAFELN zuerst und der Summe der tragenden
    Merkmale danach: Ein Typ, der vier Tafeln findet, ist mehr wert als einer,
    der eine einzige besonders sicher trifft.

    Rueckgabe None, wenn keiner passt -- das ist der Normalfall in einer
    unbekannten Halle und kein Fehler.
    """
    if bild is None or bild.size == 0 or not typen:
        return None

    finder = BoardFinder(min_inlier=min_inlier)
    bestes: Erkennung | None = None
    for typ in typen:
        treffer = finder.finde_alle(bild, [typ.muster], max_tafeln=max_tafeln)
        if not treffer:
            continue
        treffer = _verfeinere(bild, treffer, finder, max_tafeln)
        kandidat = Erkennung(typ=typ, treffer=treffer)
        log.debug("Tafeltyp %s: %d Tafeln, %d tragende Merkmale",
                  typ.name, len(treffer), kandidat.merkmale)
        if bestes is None or (len(kandidat.treffer), kandidat.merkmale) > \
                (len(bestes.treffer), bestes.merkmale):
            bestes = kandidat

    if bestes is not None:
        log.info("Tafeltyp erkannt: %s -- %d Tafeln, %d tragende Merkmale",
                 bestes.typ.name, len(bestes.treffer), bestes.merkmale)
    return bestes


def _verfeinere(bild: np.ndarray, treffer: list[Treffer],
                finder: BoardFinder, max_tafeln: int) -> list[Treffer]:
    """Zweiter Durchgang mit einer Vorlage aus dem ZIELBILD selbst.

    Das Muster der Bibliothek stammt aus einer anderen Aufnahme -- anderes
    Licht, andere Kamera, anderer Massstab. Sobald der erste Durchgang eine
    Tafel gefunden hat, laesst sich aus dem Zielbild eine Vorlage schneiden,
    die zu allen uebrigen Tafeln desselben Bildes viel besser passt.

    GEMESSEN 2026-09-09, Muster von der Hallenkamera gegen ein Overlay-Video
    einer anderen Kamera: 92 -> 176 tragende Merkmale, und die am
    schlechtesten sitzende Tafel rueckte um 16 Pixel an die richtige Stelle.

    Uebernommen wird nur, was mindestens so viele Tafeln findet UND mehr
    tragende Merkmale hat -- sonst bleibt es beim ersten Durchgang.
    """
    bester = max(treffer, key=lambda t: t.inlier)
    eigene = entzerre(bild, bester.quad, quad_groesse(bester.quad))
    zweite = finder.finde_alle(bild, [eigene], max_tafeln=max_tafeln)
    if (len(zweite) >= len(treffer)
            and sum(t.inlier for t in zweite) > sum(t.inlier for t in treffer)):
        log.debug("Verfeinerung: %d -> %d Tafeln, %d -> %d Merkmale",
                  len(treffer), len(zweite),
                  sum(t.inlier for t in treffer),
                  sum(t.inlier for t in zweite))
        return zweite
    return treffer


def uebernimm(erkennung: Erkennung, nummern: list[int]) -> Calibration:
    """Baut aus einer Erkennung eine vollstaendige Kalibrierung.

    Die ROIs des Typs werden unveraendert uebernommen -- sie liegen in
    normierten Tafelkoordinaten und gelten deshalb fuer jede Tafel dieser
    Bauart, egal wie gross oder schraeg sie im Bild steht.
    """
    if len(nummern) != len(erkennung.treffer):
        raise ValueError(
            f"{len(nummern)} Bahnnummern fuer {len(erkennung.treffer)} Tafeln")

    kal = erkennung.typ.kalibrierung.model_copy(deep=True)
    muster = erkennung.typ.bahn
    bahnen = []
    for i, (t, nummer) in enumerate(zip(erkennung.treffer, nummern), start=1):
        bahn = muster.model_copy(deep=True)
        bahn.lane_id = i                    # Position von links
        bahn.real_lane_number = int(nummer)
        bahn.quad = t.quad
        bahnen.append(bahn)
    kal.lanes = bahnen
    return kal


def speichere_typ(ordner: str | Path, name: str, bild: np.ndarray,
                  kalibrierung: Calibration, lane_id: int | None = None) -> Path:
    """Legt einen neuen Tafeltyp an -- aus einem Bild und einer Kalibrierung.

    Das Musterbild wird in BEOBACHTETER Groesse abgelegt, nicht in einer
    Normgroesse. GEMESSEN: Eine auf 440x530 entzerrte Vorlage gegen eine im
    Bild 192 Pixel grosse Tafel -- Massstabssprung 2,3fach -- fand nur eine
    von vier Tafeln, die uebrigen lagen 160 bis 600 Pixel daneben.
    """
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    bahn = (next(l for l in kalibrierung.lanes if l.lane_id == lane_id)
            if lane_id is not None else kalibrierung.lanes[0])

    muster = entzerre(bild, bahn.quad, quad_groesse(bahn.quad))
    cv2.imwrite(str(ordner / f"{name}{MUSTER_ENDUNG}"), muster)

    nur_eine = kalibrierung.model_copy(deep=True)
    nur_eine.lanes = [bahn.model_copy(deep=True)]
    nur_eine.name = name
    ziel = ordner / f"{name}.json"
    nur_eine.save(ziel)
    log.info("Tafeltyp %s angelegt: Muster %dx%d px", name,
             muster.shape[1], muster.shape[0])
    return ziel
