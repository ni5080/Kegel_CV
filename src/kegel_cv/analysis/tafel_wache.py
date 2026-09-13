"""Was auf der Tafel nicht hingehoert -- fuer Bilder, die veroeffentlicht werden.

WARUM ES DIESE DATEI GIBT

Die Personenmaske (`detection/person_maske.py`) findet bewegten Vordergrund.
Sie hat eine Grenze, die dort auch benannt ist: **Wer stillsteht, wandert ins
Hintergrundmodell und wird nicht mehr geschwaerzt.**

Genau dieser Fall ist am 2026-09-13 im Liveticker aufgetaucht. GEMESSEN am
Mitschnitt vom 2026-09-08, Bahn 2, Frame 13489 -- ein Mensch beugt sich ueber
die Tafel und ist im Bild voll zu sehen:

    Verdeckung (Bewegung)                    0,081   unter der Schwelle 0,14
    groesster bewegter Fleck auf der Tafel   0,09 Tafelflaechen
    -> die Bewegungsmaske sieht ihn NICHT

Der Grund ist kein Fehler, sondern das Verfahren: Er bewegt sich nicht mehr.

DIE ANTWORT: EINE BEWACHTE REFERENZ

Ein Hintergrundmodell lernt bedingungslos weiter. Diese Referenz nicht -- sie
lernt **nur nach, wenn die Tafel normal aussieht**. Damit kann ein Mensch nie
hineinwandern, solange er davorsteht.

Verglichen wird nur auf den STABILEN Pixeln: Gehaeuse und Fensterrahmen. Die
Anzeigen aendern sich zu Recht, und die Maske dafuer gibt es schon
(`board_match.stabile_maske`) -- dieselbe, mit der die Tafel gefunden wird.

GEMESSEN am selben Mitschnitt, 2705 Messungen ueber 15 Minuten:

    Normalbetrieb    Median 1,41 %   95. Perzentil 2,55 %
    mit dem Menschen davor          11,9 bis 14,1 %

14,27 % ist zugleich das Maximum des ganzen Mitschnitts -- es gab genau dieses
eine Ereignis, und genau dort steht das Bild mit dem Gesicht.

WAS DAMIT NICHT GEMEINT IST

Diese Wache entscheidet **nichts** ueber Wuerfe. Sie schwaerzt Bilder, die das
Haus verlassen. Ob ein Wurf gilt, klaeren Gruenlampe, Lampen und die
Verdeckungsbremse -- wie bisher.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

log = logging.getLogger(__name__)


class TafelWache:
    """Haelt eine Referenz der eigenen Tafel und meldet, was nicht dazugehoert.

    Eine Wache je Bahn: Die Tafeln stehen verschieden im Bild und werden
    verschieden ausgeleuchtet.
    """

    def __init__(self, stabil: np.ndarray | None, *,
                 abweichung_grau: int = 40, schwelle: float = 0.05,
                 nachlernen_unter: float = 0.10, lernrate: float = 0.05,
                 wachstum: float = 0.10) -> None:
        # Welche Pixel des Ausschnitts vergleichbar sind (Gehaeuse, Rahmen).
        self._stabil = stabil
        self.abweichung_grau = abweichung_grau
        self.schwelle = schwelle
        self.nachlernen_unter = nachlernen_unter
        self.lernrate = lernrate
        self.wachstum = wachstum
        self._referenz: np.ndarray | None = None

    @property
    def bereit(self) -> bool:
        return self._referenz is not None

    def _passend(self, ausschnitt: np.ndarray) -> np.ndarray | None:
        """Die stabile Maske auf die Groesse dieses Ausschnitts."""
        if self._stabil is None or ausschnitt.size == 0:
            return None
        h, b = ausschnitt.shape[:2]
        if self._stabil.shape[:2] != (h, b):
            self._stabil = cv2.resize(self._stabil.astype(np.uint8), (b, h),
                                      interpolation=cv2.INTER_NEAREST).astype(bool)
        return self._stabil

    def abweichung(self, ausschnitt: np.ndarray) -> float:
        """Anteil der stabilen Pixel, die von der Referenz abweichen."""
        stabil = self._passend(ausschnitt)
        if stabil is None or self._referenz is None:
            return 0.0
        if self._referenz.shape != ausschnitt.shape[:2]:
            return 0.0
        grau = cv2.cvtColor(ausschnitt, cv2.COLOR_BGR2GRAY).astype(np.float32)
        anders = (np.abs(grau - self._referenz) > self.abweichung_grau) & stabil
        nenner = int(stabil.sum())
        return float(anders.sum() / nenner) if nenner else 0.0

    def beobachte(self, ausschnitt: np.ndarray) -> float:
        """Einen Ausschnitt ansehen und die Referenz BEDINGT nachfuehren.

        Genau hier liegt der Unterschied zum Hintergrundmodell: Nachgelernt
        wird nur, solange die Tafel normal aussieht. Wer davorsteht, wandert
        deshalb nie hinein -- egal wie lange er steht.
        """
        if ausschnitt is None or ausschnitt.size == 0:
            return 0.0
        grau = cv2.cvtColor(ausschnitt, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if self._referenz is None or self._referenz.shape != grau.shape:
            self._referenz = grau.copy()
            return 0.0
        anteil = self.abweichung(ausschnitt)
        if anteil < self.nachlernen_unter:
            self._referenz = ((1 - self.lernrate) * self._referenz
                              + self.lernrate * grau)
        return anteil

    def fremdmaske(self, ausschnitt: np.ndarray) -> np.ndarray | None:
        """Was auf diesem Ausschnitt nicht hingehoert -- oder None.

        Die rohe Abweichung ist loechrig: Wo die Kleidung zufaellig die Farbe
        des Gehaeuses trifft, bleibt ein Loch. Ein halb geschwaerztes Gesicht
        ist kein geschwaerztes Gesicht -- deshalb wird die Maske geschlossen
        und verbreitert, und zwar im Verhaeltnis zur Tafel (`wachstum`), nicht
        in festen Pixeln.
        """
        if ausschnitt is None or ausschnitt.size == 0 or self._referenz is None:
            return None
        stabil = self._passend(ausschnitt)
        if stabil is None or self._referenz.shape != ausschnitt.shape[:2]:
            return None
        if self.abweichung(ausschnitt) < self.schwelle:
            return None

        grau = cv2.cvtColor(ausschnitt, cv2.COLOR_BGR2GRAY).astype(np.float32)
        # Fuer die MASKE zaehlt jede Abweichung, auch auf den Anzeigen: Steht
        # jemand davor, verdeckt er sie mit. Die stabile Maske entscheidet nur,
        # OB jemand da ist -- nicht, was geschwaerzt wird.
        maske = (np.abs(grau - self._referenz)
                 > self.abweichung_grau).astype(np.uint8) * 255
        kern = max(3, int(self.wachstum * min(ausschnitt.shape[:2]))) | 1
        form = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kern, kern))
        maske = cv2.morphologyEx(maske, cv2.MORPH_CLOSE, form)
        maske = cv2.dilate(maske, form)
        return maske if cv2.countNonZero(maske) else None
