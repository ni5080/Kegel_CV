"""Findet eine bekannte Anzeigetafel in einem neuen Bild wieder.

DIE IDEE (vom Nutzer, 2026-09-09)

    "sobald ich einen Bahntyp kalibriert habe, sollte das meines Erachtens
     sehr gut funktionieren, dass ein Algorithmus ueber 'Bild in Bild' Suche
     das mindestens genauso gut kalibrieren kann wie ich. Es reicht ja, dass
     er die Eckpunkte sauber findet, weil die Leuchten und Ziffern sollten ja
     immer an derselben Stelle sein (Beim selben Bahntyp)"

Das trifft genau zu, und zwar aus einem Grund, der im Datenmodell steht: Die
ROIs liegen in NORMIERTEN Tafelkoordinaten (0..1, siehe `Roi`). Sind die vier
Ecken gefunden, folgt jede Lampe und jede Ziffer daraus -- ohne einen einzigen
weiteren Klick.

DAS VERFAHREN

Merkmalsabgleich mit Homographie, nicht Schablonenvergleich. `matchTemplate`
kann nur verschieben und skalieren; eine Tafel steht aber SCHRAEG im Bild, und
zwar je nach Position unterschiedlich schraeg. ORB-Merkmale plus
`findHomography` mit RANSAC koennen die Perspektive mitrechnen -- und liefern
die Ecken als Nebenprodukt.

GEMESSEN am Trainingsmitschnitt vom 2026-09-08 (Vorlage aus einem Frame,
Wiederfinden in einem 6 Minuten spaeteren):

    Vorlage aus Frame 1500    Bahn 2  2,9 px | Bahn 3  0,5 | Bahn 4  1,1 | Bahn 5  1,2
    Vorlage aus Frame 3000    Bahn 2  1,0 px | Bahn 3  0,5 | Bahn 4  1,7 | Bahn 5  0,6
    Vorlage aus Frame 9000    Bahn 2  0,7 px | Bahn 3  1,1 | Bahn 4  1,3 | Bahn 5  0,8

Subpixelgenau -- besser als Klicken von Hand.

DREI DINGE, DIE GEMESSEN WURDEN UND IM ENTWURF STEHEN

**1. Die Vorlage muss in BEOBACHTETER Groesse vorliegen.** Der erste Anlauf
entzerrte auf 440x530, waehrend die Tafel im Bild 192 px misst -- ein
Massstabssprung von 2,3x. Ergebnis: nur eine von vier Bahnen gefunden, die
uebrigen um 160 bis 600 Pixel daneben.

**2. Das Zielbild braucht viele Merkmale.** Mit `nfeatures=2000` verteilen
sich die Merkmale ueber das ganze Bild, und auf eine 192 px kleine Tafel
entfallen zu wenige. Mit 20000 gelingen alle vier.

**3. Eine einzelne Vorlage kann unbrauchbar sein.** Aus Frame 200 scheiterte
Bahn 5 vollstaendig (7 Inlier, 1429 px daneben) -- in genau diesem Frame stand
eine Person neben der Tafel. Deshalb werden MEHRERE Vorlagen angeboten und die
beste genommen. Die Zahl der Inlier trennt dabei sauber: gelungene Treffer
hatten 18 bis 197, der gescheiterte 7.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

log = logging.getLogger(__name__)

# Reihenfolge der Ecken, wie sie das Projekt ueberall verwendet:
# oben links, oben rechts, unten rechts, unten links.
ECKEN_REIHENFOLGE = ("oben links", "oben rechts", "unten rechts", "unten links")


@dataclass(frozen=True)
class Treffer:
    """Eine gefundene Tafel.

    `quad` sind die vier Ecken im Zielbild, `inlier` die Zahl der Merkmale,
    die die Homographie tragen -- das aussagekraeftigste Guetemass.
    """

    quad: list[list[float]]
    inlier: int
    paare: int
    vorlage_index: int

    @property
    def guete(self) -> float:
        """Anteil der Paare, die die Homographie stuetzen (0..1)."""
        return self.inlier / self.paare if self.paare else 0.0


def quad_groesse(quad) -> tuple[int, int]:
    """Kantenlaenge eines Vierecks in Pixeln (Breite, Hoehe).

    Gemittelt ueber die jeweils gegenueberliegenden Kanten -- bei einer
    schraeg gesehenen Tafel sind sie verschieden lang.
    """
    q = np.float32(quad)
    breite = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
    hoehe = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
    return max(1, int(round(breite))), max(1, int(round(hoehe)))


def entzerre(bild: np.ndarray, quad, groesse: tuple[int, int]) -> np.ndarray:
    """Rechnet die schraeg gesehene Tafel auf ein Rechteck gerade."""
    b, h = groesse
    ziel = np.float32([[0, 0], [b, 0], [b, h], [0, h]])
    m = cv2.getPerspectiveTransform(np.float32(quad), ziel)
    return cv2.warpPerspective(bild, m, (b, h))


def ist_plausibel(quad: np.ndarray, bild_form: tuple[int, ...],
                  soll_groesse: tuple[int, int],
                  groessentoleranz: float = 2.5) -> str | None:
    """Prueft, ob ein gefundenes Viereck ueberhaupt eine Tafel sein kann.

    Eine Homographie aus wenigen falschen Paaren liefert bereitwillig ein
    Viereck -- nur eben ein sinnloses: umgestuelpt, winzig oder weit ausserhalb
    des Bildes. GEMESSEN: Der gescheiterte Treffer auf Bahn 5 lag 1429 Pixel
    daneben und haette ohne diese Pruefung als Kalibrierung gegolten.

    Rueckgabe: None, wenn plausibel -- sonst der Grund.
    """
    h, w = bild_form[:2]
    if not np.isfinite(quad).all():
        return "Ecken sind keine Zahlen"

    # Ganz ausserhalb des Bildes ist keine Tafel. Ein Rand von einer halben
    # Tafelbreite ist erlaubt -- eine Tafel darf am Bildrand angeschnitten sein.
    rand = max(soll_groesse)
    if (quad[:, 0].min() < -rand or quad[:, 0].max() > w + rand
            or quad[:, 1].min() < -rand or quad[:, 1].max() > h + rand):
        return "liegt ausserhalb des Bildes"

    flaeche = cv2.contourArea(quad.astype(np.float32))
    soll = soll_groesse[0] * soll_groesse[1]
    if flaeche <= 0:
        return "Ecken sind verdreht (Flaeche null oder negativ)"
    if not (soll / groessentoleranz <= flaeche <= soll * groessentoleranz):
        return (f"Groesse passt nicht: {flaeche:.0f} statt rund {soll} "
                f"Pixel Flaeche")

    if not cv2.isContourConvex(quad.astype(np.float32)):
        return "Viereck ist nicht konvex"
    return None


class BoardFinder:
    """Sucht eine Tafel anhand mehrerer Vorlagen.

    Zustandslos gegenueber dem Bild: Jeder Aufruf steht fuer sich. Die
    Merkmale des Zielbilds werden je Aufruf einmal berechnet und fuer alle
    Vorlagen wiederverwendet -- das ist der teuerste Schritt.
    """

    def __init__(self, *, nfeatures: int = 20000, ratio: float = 0.75,
                 ransac_reproj: float = 4.0, min_inlier: int = 18) -> None:
        self.nfeatures = nfeatures
        self.ratio = ratio
        self.ransac_reproj = ransac_reproj
        self.min_inlier = min_inlier
        self._orb = cv2.ORB_create(nfeatures=nfeatures, scaleFactor=1.2,
                                   nlevels=8)
        self._matcher = cv2.BFMatcher(cv2.NORM_HAMMING)

    def finde(self, ziel: np.ndarray, vorlagen: list[np.ndarray],
              *, versatz: tuple[int, int] = (0, 0)) -> Treffer | None:
        """Sucht die beste Uebereinstimmung unter allen Vorlagen.

        `versatz` wird auf die gefundenen Ecken addiert -- gedacht fuer die
        Suche in einem Ausschnitt des Vollbilds.
        """
        if ziel is None or ziel.size == 0 or not vorlagen:
            return None
        ziel_grau = self._grau(ziel)
        kp_ziel, des_ziel = self._orb.detectAndCompute(ziel_grau, None)
        if des_ziel is None or len(kp_ziel) < 10:
            log.debug("Zielbild traegt zu wenige Merkmale (%d)",
                      0 if kp_ziel is None else len(kp_ziel))
            return None

        bester: Treffer | None = None
        for i, vorlage in enumerate(vorlagen):
            treffer = self._eine_vorlage(vorlage, ziel, kp_ziel, des_ziel,
                                         i, versatz)
            if treffer is None:
                continue
            if bester is None or treffer.inlier > bester.inlier:
                bester = treffer

        if bester is None:
            return None
        if bester.inlier < self.min_inlier:
            # NICHT stillschweigend zurueckgeben. GEMESSEN: Der gescheiterte
            # Treffer hatte 7 Inlier und lag 1429 Pixel daneben, die
            # gelungenen hatten 18 bis 197. Die Zahl trennt sauber.
            log.info("Beste Uebereinstimmung traegt nur %d Merkmale "
                     "(mindestens %d noetig) -- kein verlaesslicher Treffer",
                     bester.inlier, self.min_inlier)
            return None
        return bester

    # ------------------------------------------------------------- intern

    @staticmethod
    def _grau(bild: np.ndarray) -> np.ndarray:
        if bild.ndim == 2:
            return bild
        return cv2.cvtColor(bild, cv2.COLOR_BGR2GRAY)

    def _eine_vorlage(self, vorlage: np.ndarray, ziel: np.ndarray,
                      kp_ziel, des_ziel, index: int,
                      versatz: tuple[int, int]) -> Treffer | None:
        kp, des = self._orb.detectAndCompute(self._grau(vorlage), None)
        if des is None or len(kp) < 10:
            return None

        paare = self._matcher.knnMatch(des, des_ziel, k=2)
        # Lowes Verhaeltnistest: Ein Merkmal zaehlt nur, wenn der beste
        # Partner deutlich besser passt als der zweitbeste. Bei vier fast
        # identischen Tafeln im Bild ist genau das die Huerde, an der ein
        # Treffer auf der falschen Tafel scheitert.
        gut = [a for a, b in (p for p in paare if len(p) == 2)
               if a.distance < self.ratio * b.distance]
        if len(gut) < 8:
            return None

        src = np.float32([kp[m.queryIdx].pt for m in gut]).reshape(-1, 1, 2)
        dst = np.float32([kp_ziel[m.trainIdx].pt
                          for m in gut]).reshape(-1, 1, 2)
        H, maske = cv2.findHomography(src, dst, cv2.RANSAC,
                                      self.ransac_reproj)
        if H is None or maske is None:
            return None

        h, b = vorlage.shape[:2]
        ecken = np.float32([[0, 0], [b, 0], [b, h], [0, h]])
        quad = cv2.perspectiveTransform(ecken.reshape(-1, 1, 2),
                                        H).reshape(4, 2)
        quad[:, 0] += versatz[0]
        quad[:, 1] += versatz[1]

        grund = ist_plausibel(quad, ziel.shape, (b, h))
        if grund is not None:
            log.debug("Vorlage %d verworfen: %s", index, grund)
            return None

        return Treffer(quad=[[float(x), float(y)] for x, y in quad],
                       inlier=int(maske.sum()), paare=len(gut),
                       vorlage_index=index)
