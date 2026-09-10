"""Auswahl der Kegelboard-Bauart -- mit Bildern statt Namen.

WOFUER -- Wunsch des Nutzers am 2026-09-10:

    "Automatisches Kalibrieren (klick) dann kommt ein Fenster 'Waehle dein
     Kegelboardtyp aus' (da sind dann ganz viele Bilder mit Kegelboards) und
     dort gibt es zusaetzlich 'neues Board aufnehmen' oder man klickt auf eins
     und dann wird das gesucht"

WARUM BILDER UND KEINE LISTE: Eine Bauart erkennt man am Aussehen, nicht am
Namen. `FUNK_klassisch` sagt niemandem etwas, der vor einer fremden Anlage
steht -- das Musterbild dagegen sofort. Deshalb ist das Bild die eigentliche
Schaltflaeche und der Name nur die Unterschrift.
"""

from __future__ import annotations

import logging

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QGridLayout, QLabel,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ..calibration.board_library import Tafeltyp

log = logging.getLogger(__name__)

# Kantenlaenge der Vorschau. Gross genug, dass Lampenraute und Ziffernfelder
# zu erkennen sind -- daran unterscheidet der Nutzer zwei Bauarten.
VORSCHAU_PX = 190
SPALTEN = 3


def _als_pixmap(bild: np.ndarray, kante: int = VORSCHAU_PX) -> QPixmap:
    """Macht aus einem BGR-Musterbild eine Vorschau fuer die Oberflaeche."""
    hoehe, breite = bild.shape[:2]
    rgb = np.ascontiguousarray(bild[:, :, ::-1])
    qbild = QImage(rgb.data, breite, hoehe, 3 * breite, QImage.Format_RGB888)
    return QPixmap.fromImage(qbild).scaled(
        kante, kante, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class TafeltypDialog(QDialog):
    """Zeigt die bekannten Bauarten als Bildkacheln zur Auswahl.

    Drei Ausgaenge, die der Aufrufer an `ergebnis` abliest:

        ein `Tafeltyp`   diese Bauart soll gesucht werden
        "alle"           jede bekannte Bauart durchprobieren
        "neu"            keine passt -- eine neue aufnehmen
    """

    def __init__(self, typen: list[Tafeltyp], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Kegelboard-Bauart waehlen")
        self.ergebnis: Tafeltyp | str | None = None
        self._typen = typen

        aussen = QVBoxLayout(self)
        aussen.addWidget(QLabel(
            "<b>Welche Bauart hat die Anlage im Bild?</b><br>"
            "Die gewaehlte Bauart wird im Bild gesucht; alle Tafeln desselben "
            "Typs werden dabei gefunden."))

        if typen:
            aussen.addWidget(self._kacheln(typen))
        else:
            leer = QLabel(
                "Die Bibliothek ist noch leer.<br><br>"
                "Eine Bahn von Hand kalibrieren und dann "
                "<b>Neues Board aufnehmen</b> -- danach findet das Werkzeug "
                "diese Bauart ueberall wieder.")
            leer.setStyleSheet("padding:24px;")
            aussen.addWidget(leer)

        if len(typen) > 1:
            alle = QPushButton(f"Alle {len(typen)} Bauarten durchprobieren")
            alle.setToolTip("Dauert laenger, dafuer muss nichts gewusst werden.")
            alle.clicked.connect(lambda: self._waehle("alle"))
            aussen.addWidget(alle)

        neu = QPushButton("Neues Board aufnehmen ...")
        neu.setToolTip(
            "Fuer eine Bauart, die hier noch fehlt: eine Tafel von Hand "
            "vermessen, danach merkt sich das Werkzeug sie dauerhaft.")
        neu.setStyleSheet("padding:6px;")
        neu.clicked.connect(lambda: self._waehle("neu"))
        aussen.addWidget(neu)

        knoepfe = QDialogButtonBox(QDialogButtonBox.Cancel)
        knoepfe.rejected.connect(self.reject)
        aussen.addWidget(knoepfe)

    def _kacheln(self, typen: list[Tafeltyp]) -> QWidget:
        inhalt = QWidget()
        gitter = QGridLayout(inhalt)
        for i, typ in enumerate(typen):
            gitter.addWidget(self._kachel(typ), i // SPALTEN, i % SPALTEN)

        bereich = QScrollArea()
        bereich.setWidget(inhalt)
        bereich.setWidgetResizable(True)
        # Drei Kacheln nebeneinander, zwei Reihen sichtbar -- darueber
        # hinaus wird gerollt.
        bereich.setMinimumSize(SPALTEN * (VORSCHAU_PX + 30),
                               2 * (VORSCHAU_PX + 70))
        return bereich

    def _kachel(self, typ: Tafeltyp) -> QWidget:
        hoehe, breite = typ.muster.shape[:2]
        knopf = QPushButton()
        knopf.setIcon(_als_pixmap(typ.muster))
        # Das BILD ist die Schaltflaeche. Ohne gesetzte Icon-Groesse zeigt Qt
        # ein 16-Pixel-Briefmarkenbild, auf dem nichts zu erkennen ist.
        knopf.setIconSize(_als_pixmap(typ.muster).size())
        knopf.setToolTip(f"{typ.name}\n{breite}x{hoehe} px, "
                         f"{len(typ.bahn.rois)} Felder")
        knopf.clicked.connect(lambda _=False, t=typ: self._waehle(t))

        unterschrift = QLabel(f"<b>{typ.name}</b><br>"
                              f"<small>{len(typ.bahn.rois)} Felder</small>")
        unterschrift.setAlignment(Qt.AlignHCenter)

        kachel = QWidget()
        spalte = QVBoxLayout(kachel)
        spalte.setContentsMargins(4, 4, 4, 4)
        spalte.addWidget(knopf)
        spalte.addWidget(unterschrift)
        return kachel

    def _waehle(self, was: Tafeltyp | str) -> None:
        self.ergebnis = was
        self.accept()
