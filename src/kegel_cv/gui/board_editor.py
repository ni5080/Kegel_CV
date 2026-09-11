"""Eine einzelne Tafel gross zeigen und ihre Bereiche von Hand nachziehen.

WOFUER -- Wunsch des Nutzers am 2026-09-11:

    "ich brauche einen Button 'Nachkalibrieren' ... an dem ich jedes Board das
     ich aendern will anklicken kann, das wird mir gross gezeigt und ich kann
     die ROIs anpassen"

WARUM ENTZERRT UND NICHT IM VOLLBILD: Im Originalframe misst eine Tafel rund
250 Pixel, eine Kegellampe darin sechs. Ziehen laesst sich das dort nur im
starken Zoom -- und schraeg, weil die Tafel perspektivisch verzerrt im Bild
steht. Die entzerrte Tafel ist genau der Raum, in dem die ROIs DEFINIERT sind:
normierte Tafelkoordinaten 0..1. Was hier geschoben wird, wird ohne Umweg ueber
eine Homographie gespeichert.

IM WAHREN SEITENVERHAELTNIS, nicht im Rechenformat 440x530 -- dieselbe
Begruendung wie bei `roi_preview.tafelmontage`: Die Analyse rechnet in einem
gestreckten Format, das Auge soll die Tafel sehen.
"""

from __future__ import annotations

import logging

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox,
                               QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from ..calibration.geometry import GeometryError, PerspectiveTransform, Quad
from ..calibration.model import Roi
from ..calibration.roi_preview import quadmasse, roi_farbe
from ..calibration.session import CalibrationSession

log = logging.getLogger(__name__)

# Trefferradius in WIDGET-Pixeln -- dieselbe Ueberlegung wie in `VideoView`:
# Was zielsicher greifbar ist, haengt am Bildschirm, nicht an der Tafelgroesse.
GREIFRADIUS = 9.0

# Wie oft das Bild unter den Rahmen erneuert wird. Im Livestream stehen dort
# wechselnde Ziffern; ein Standbild von vor einer Minute zeigt womoeglich eine
# Anzeige, die es gerade gar nicht gibt.
BILDTAKT_MS = 400


def _qfarbe(name: str) -> QColor:
    """Dieselben Farben wie in der Vorschau -- BGR dort, RGB hier."""
    b, g, r = roi_farbe(name)
    return QColor(r, g, b)


def entzerre(bild: np.ndarray, ecken) -> np.ndarray | None:
    """Schneidet eine Tafel im wahren Seitenverhaeltnis aus dem Frame.

    Gibt None zurueck, wenn das Viereck nichts hergibt -- waehrend des Ziehens
    an einer Tafelecke kann es kurzzeitig entartet sein (P8: kein Abbruch).
    """
    punkte = [(float(p[0]), float(p[1])) for p in ecken]
    breite, hoehe = quadmasse(punkte)
    if breite < 2 or hoehe < 2:
        return None
    try:
        transform = PerspectiveTransform(Quad.from_points(punkte),
                                         int(round(breite)), int(round(hoehe)))
    except GeometryError as exc:
        log.warning("Tafel laesst sich nicht entzerren: %s", exc)
        return None
    return transform.warp(bild)


class TafelLeinwand(QWidget):
    """Die entzerrte Tafel mit ihren Bereichen -- anfassbar.

    Die Leinwand rechnet ausschliesslich in normierten Tafelkoordinaten. Sie
    kennt weder Frame noch Homographie; was sie liefert, sind fertige `Roi`.
    """

    geaendert = Signal()
    zeiger = Signal(str)        # Name des Bereichs unter der Maus ("" = keiner)

    def __init__(self, rois: list[Roi], tafel_px: tuple[int, int],
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("background-color:#141414;")

        self.rois: list[Roi] = [r.model_copy(deep=True) for r in rois]
        # Nur fuer die Pfeiltasten: EIN Schritt ist EIN Pixel der Tafel im
        # Originalbild. Das ist die Einheit, in der der Fehler auftritt --
        # gemessen entscheidet ein Pixel ueber neun Prozentpunkte
        # Lesegenauigkeit bei den Ziffern.
        self._tafel_px = (max(1, tafel_px[0]), max(1, tafel_px[1]))
        self._pixmap: QPixmap | None = None
        self._namen = False
        self._gewaehlt: str | None = None
        self._zieht: tuple[str, str] | None = None   # (Name, Kante)

    # ------------------------------------------------------------- Anzeige

    def set_bild(self, tafel: np.ndarray | None) -> None:
        if tafel is None:
            return
        hoehe, breite = tafel.shape[:2]
        rgb = np.ascontiguousarray(tafel[:, :, ::-1])
        bild = QImage(rgb.data, breite, hoehe, 3 * breite, QImage.Format_RGB888)
        self._pixmap = QPixmap.fromImage(bild.copy())
        self.update()

    def set_namen(self, an: bool) -> None:
        self._namen = bool(an)
        self.update()

    def setze_rois(self, rois: list[Roi]) -> None:
        self.rois = [r.model_copy(deep=True) for r in rois]
        self.update()
        self.geaendert.emit()

    # --------------------------------------------------------- Koordinaten

    def _flaeche(self) -> QRectF:
        """Wo die Tafel im Widget liegt -- eingepasst, Seitenverhaeltnis fest."""
        if self._pixmap is None or self._pixmap.isNull():
            return QRectF(0, 0, self.width(), self.height())
        pb, ph = self._pixmap.width(), self._pixmap.height()
        faktor = min(self.width() / pb, self.height() / ph)
        breite, hoehe = pb * faktor, ph * faktor
        return QRectF((self.width() - breite) / 2, (self.height() - hoehe) / 2,
                      breite, hoehe)

    def _nach_norm(self, pos: QPointF) -> tuple[float, float]:
        flaeche = self._flaeche()
        if flaeche.width() <= 0 or flaeche.height() <= 0:
            return 0.0, 0.0
        return ((pos.x() - flaeche.x()) / flaeche.width(),
                (pos.y() - flaeche.y()) / flaeche.height())

    def _kasten(self, roi: Roi) -> QRectF:
        x, y, w, h = roi.rect
        f = self._flaeche()
        return QRectF(f.x() + x * f.width(), f.y() + y * f.height(),
                      w * f.width(), h * f.height())

    # ------------------------------------------------------------- Zeichnen

    def paintEvent(self, event) -> None:      # noqa: N802  (Qt-Konvention)
        maler = QPainter(self)
        maler.setRenderHint(QPainter.Antialiasing)
        flaeche = self._flaeche()
        if self._pixmap is not None and not self._pixmap.isNull():
            maler.drawPixmap(flaeche, self._pixmap,
                             QRectF(self._pixmap.rect()))

        schrift = QFont()
        schrift.setPixelSize(10)
        maler.setFont(schrift)

        for roi in self.rois:
            if not roi.enabled:
                continue
            farbe = _qfarbe(roi.name)
            gewaehlt = roi.name == self._gewaehlt
            kasten = self._kasten(roi)
            maler.setPen(QPen(farbe, 2 if gewaehlt else 1))
            maler.drawRect(kasten)
            if gewaehlt:
                self._griffe(maler, kasten, farbe)
            # Der GEWAEHLTE Bereich zeigt seinen Namen immer -- man muss wissen,
            # was man gerade verschiebt, auch wenn alle anderen Namen aus sind.
            if self._namen or gewaehlt:
                maler.setPen(QPen(farbe))
                maler.drawText(kasten.topLeft() + QPointF(1, -2),
                               roi.name.replace("pin_lamp_", "L")
                               .replace("digit_", ""))
        maler.end()

    @staticmethod
    def _griffe(maler: QPainter, kasten: QRectF, farbe: QColor) -> None:
        """Ecken des gewaehlten Bereichs sichtbar machen.

        Ohne sie ist nicht zu erkennen, dass sich die GROESSE ziehen laesst --
        und eine Ziffernbox muss in der Groesse stimmen, nicht nur in der Lage.
        """
        maler.setBrush(farbe)
        for punkt in (kasten.topLeft(), kasten.topRight(),
                      kasten.bottomRight(), kasten.bottomLeft()):
            maler.drawRect(QRectF(punkt.x() - 2, punkt.y() - 2, 4, 4))
        maler.setBrush(Qt.NoBrush)

    # ---------------------------------------------------------------- Maus

    def _treffer(self, pos: QPointF) -> tuple[str, str] | None:
        """Was liegt unter dem Zeiger -- und an welchem Griff?

        Bei mehreren gewinnt der KLEINSTE Bereich: Eine Ziffernstelle liegt
        innerhalb ihres Gesamtfeldes, gemeint ist dann die Stelle.
        """
        kandidaten = []
        for roi in self.rois:
            if not roi.enabled:
                continue
            k = self._kasten(roi)
            if (k.x() - GREIFRADIUS <= pos.x() <= k.right() + GREIFRADIUS
                    and k.y() - GREIFRADIUS <= pos.y() <= k.bottom() + GREIFRADIUS):
                kandidaten.append((k.width() * k.height(), roi.name, k))
        if not kandidaten:
            return None
        _, name, kasten = min(kandidaten, key=lambda k: k[0])
        return name, self._kante(pos, kasten)

    @staticmethod
    def _kante(pos: QPointF, kasten: QRectF) -> str:
        """Nahe einem Rand wird VERZOGEN, in der Mitte VERSCHOBEN.

        Hoechstens ein Drittel der jeweiligen Seite -- bei einer 12 Pixel
        breiten Ziffer naehme ein fester Randstreifen die ganze Flaeche ein und
        das Verschieben waere unmoeglich.
        """
        rand_x = min(GREIFRADIUS, max(2.0, kasten.width() / 3))
        rand_y = min(GREIFRADIUS, max(2.0, kasten.height() / 3))
        senkrecht = ("t" if pos.y() <= kasten.y() + rand_y
                     else ("b" if pos.y() >= kasten.bottom() - rand_y else ""))
        waagerecht = ("l" if pos.x() <= kasten.x() + rand_x
                      else ("r" if pos.x() >= kasten.right() - rand_x else ""))
        return (senkrecht + waagerecht) or "move"

    def mousePressEvent(self, event) -> None:     # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        treffer = self._treffer(event.position())
        self._zieht = treffer
        self._gewaehlt = treffer[0] if treffer else None
        self.setFocus()
        self.update()

    def mouseMoveEvent(self, event) -> None:      # noqa: N802
        if self._zieht is None:
            treffer = self._treffer(event.position())
            self.zeiger.emit(treffer[0] if treffer else "")
            self.setCursor(Qt.SizeAllCursor if treffer else Qt.ArrowCursor)
            return
        name, kante = self._zieht
        nx, ny = self._nach_norm(event.position())
        self._aendere(name, kante, nx, ny)

    def mouseReleaseEvent(self, event) -> None:   # noqa: N802
        if event.button() == Qt.LeftButton:
            self._zieht = None

    def keyPressEvent(self, event) -> None:       # noqa: N802
        """Pfeiltasten schieben den gewaehlten Bereich um EINEN Tafelpixel.

        Mit der Maus ist ein einzelner Pixel nicht zu treffen -- und genau um
        einen einzelnen Pixel geht es bei den Ziffern.
        """
        schritte = {Qt.Key_Left: (-1, 0), Qt.Key_Right: (1, 0),
                    Qt.Key_Up: (0, -1), Qt.Key_Down: (0, 1)}
        if self._gewaehlt is None or event.key() not in schritte:
            super().keyPressEvent(event)
            return
        dx, dy = schritte[event.key()]
        roi = self._roi(self._gewaehlt)
        if roi is None:
            return
        cx, cy = roi.center
        self._aendere(roi.name, "move",
                      cx + dx / self._tafel_px[0], cy + dy / self._tafel_px[1])

    # ------------------------------------------------------------- Aendern

    def _roi(self, name: str) -> Roi | None:
        return next((r for r in self.rois if r.name == name), None)

    def _aendere(self, name: str, kante: str, nx: float, ny: float) -> None:
        roi = self._roi(name)
        if roi is None:
            return
        neu = (self._verschoben(roi, nx, ny) if kante == "move"
               else self._verzogen(roi, kante, nx, ny))
        if neu is None:
            return
        self.rois[self.rois.index(roi)] = neu
        self.update()
        self.geaendert.emit()

    @staticmethod
    def _verschoben(roi: Roi, nx: float, ny: float) -> Roi:
        """Mittig auf den Punkt, aber nie ueber den Tafelrand hinaus.

        Geklemmt statt verworfen: Wer eine Lampe an den Rand zieht, will sie
        am Rand haben -- ein Bereich, der beim Ueberschreiten stehenbleibt,
        fuehlt sich an, als haenge die Oberflaeche.
        """
        _, _, w, h = roi.rect
        x = min(max(nx - w / 2, 0.0), max(0.0, 1.0 - w))
        y = min(max(ny - h / 2, 0.0), max(0.0, 1.0 - h))
        return roi.model_copy(update={"rect": (x, y, w, h), "enabled": True})

    @staticmethod
    def _verzogen(roi: Roi, kante: str, nx: float, ny: float) -> Roi:
        """Einen Rand oder eine Ecke ziehen -- Mindestkante wie in der Sitzung.

        Derselbe Grenzwert wie beim Ziehen im Video: Ein versehentlich auf
        null gezogener Bereich waere still kaputt statt sichtbar falsch.
        """
        klein = CalibrationSession.MINDESTKANTE
        nx = min(max(nx, 0.0), 1.0)
        ny = min(max(ny, 0.0), 1.0)
        x, y, w, h = roi.rect
        links, oben, rechts, unten = x, y, x + w, y + h
        if "l" in kante:
            links = min(nx, rechts - klein)
        if "r" in kante:
            rechts = max(nx, links + klein)
        if "t" in kante:
            oben = min(ny, unten - klein)
        if "b" in kante:
            unten = max(ny, oben + klein)
        return roi.model_copy(update={
            "rect": (links, oben, rechts - links, unten - oben),
            "enabled": True})


class TafelEditorDialog(QDialog):
    """Nachkalibrieren einer einzelnen Tafel.

    Der Dialog arbeitet auf KOPIEN der Bereiche. Erst "Uebernehmen" schreibt
    sie zurueck -- sonst waere ein versehentliches Verziehen nicht mehr
    ruecknehmbar, und genau deshalb kommt man hierher.
    """

    def __init__(self, lane, bild: np.ndarray, *, tafeln: int = 1,
                 bild_quelle=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Bahn {lane.display_number} nachkalibrieren")
        self._lane = lane
        self._bild_quelle = bild_quelle
        self._ausgang = [r.model_copy(deep=True) for r in lane.rois]
        self.auf_alle = False

        tafel = entzerre(bild, lane.quad)
        px = (tafel.shape[1], tafel.shape[0]) if tafel is not None else (1, 1)

        spalte = QVBoxLayout(self)
        # UMBRECHEN, SONST SPRENGT DIESE ZEILE DEN DIALOG. Ein QLabel ohne
        # Umbruch setzt seine ganze Textbreite als Mindestbreite durch --
        # gemessen 2302 Pixel fuer eine Tafel, die 500 breit dargestellt wird.
        kopf = QLabel(
            f"<b>Bahn {lane.display_number}</b> -- Bereich anklicken und "
            "ziehen. Am Rand eines Bereichs wird seine <b>Groesse</b> "
            "gezogen, in der Mitte seine <b>Lage</b>. Die Pfeiltasten "
            "verschieben den gewaehlten Bereich um je einen Tafelpixel.")
        kopf.setWordWrap(True)
        spalte.addWidget(kopf)

        self.leinwand = TafelLeinwand(lane.rois, px)
        self.leinwand.set_bild(tafel)
        self.leinwand.zeiger.connect(self._zeige_bereich)
        spalte.addWidget(self.leinwand, 1)

        self.info = QLabel(f"{len(lane.rois)} Bereiche -- Tafel {px[0]}x{px[1]} px")
        self.info.setStyleSheet("color:#888;")
        self.info.setWordWrap(True)
        spalte.addWidget(self.info)

        zeile = QHBoxLayout()
        # NAMEN AUS: Bei 25 Bereichen -- neun Lampen und acht Ziffernstellen --
        # legen sich die Beschriftungen uebereinander und verdecken genau die
        # Anzeige, an der man beurteilen soll, ob der Rahmen sitzt. Wer wissen
        # will, was unter dem Zeiger liegt, liest es in der Zeile darueber.
        namen = QCheckBox("Namen einblenden")
        namen.setChecked(False)
        namen.toggled.connect(self.leinwand.set_namen)
        zeile.addWidget(namen)

        if tafeln > 1:
            self.alle = QCheckBox(f"auf alle {tafeln} Tafeln uebertragen")
            self.alle.setToolTip(
                "Die Bereiche liegen in normierten Tafelkoordinaten -- was "
                "hier sitzt, sitzt auf jeder Tafel derselben Bauart. Sinnvoll "
                "bei einem Fehler der Bauart, nicht bei einer einzelnen "
                "schief stehenden Tafel.")
            zeile.addWidget(self.alle)
        else:
            self.alle = None

        zurueck = QPushButton("Zuruecksetzen")
        zurueck.setToolTip("Alle Bereiche wieder so, wie sie beim Oeffnen waren")
        zurueck.clicked.connect(lambda: self.leinwand.setze_rois(self._ausgang))
        zeile.addWidget(zurueck)
        zeile.addStretch(1)
        spalte.addLayout(zeile)

        knoepfe = QDialogButtonBox()
        knoepfe.addButton("Uebernehmen", QDialogButtonBox.AcceptRole)
        knoepfe.addButton("Abbrechen", QDialogButtonBox.RejectRole)
        knoepfe.accepted.connect(self._uebernehmen)
        knoepfe.rejected.connect(self.reject)
        spalte.addWidget(knoepfe)

        self._passe_groesse_an(px)

        # DAS BILD DARF NICHT EINFRIEREN. Im Livestream wechseln die Ziffern;
        # ob ein Rahmen sitzt, entscheidet sich an mehreren Anzeigen, nicht an
        # einem Standbild.
        self._takt = QTimer(self)
        self._takt.timeout.connect(self._bild_erneuern)
        if bild_quelle is not None:
            self._takt.start(BILDTAKT_MS)

    # ------------------------------------------------------------ Innereien

    def _passe_groesse_an(self, px: tuple[int, int]) -> None:
        """So gross wie moeglich, aber innerhalb des Bildschirms.

        Derselbe Fehler wie beim Bestaetigungsdialog soll sich nicht
        wiederholen: "kann man wegen der Fenstergroesse nicht bestaetigen"
        (Nutzer, 2026-09-10).
        """
        from PySide6.QtCore import QRect
        from PySide6.QtWidgets import QApplication
        schirm = QApplication.primaryScreen()
        platz = schirm.availableGeometry() if schirm else QRect(0, 0, 1280, 800)
        hoehe = max(420, int(platz.height() * 0.86))
        # Breite aus dem Seitenverhaeltnis der Tafel plus Rand -- ein breites
        # Fenster um ein quadratisches Bild ist nur leere Flaeche.
        bild_hoehe = hoehe - 170
        breite = min(int(platz.width() * 0.9),
                     max(460, int(bild_hoehe * px[0] / max(1, px[1])) + 60))
        self.resize(breite, hoehe)
        self.setMaximumSize(platz.width(), platz.height())

    def _zeige_bereich(self, name: str) -> None:
        if not name:
            self.info.setText(f"{len(self.leinwand.rois)} Bereiche")
            return
        roi = self.leinwand._roi(name)
        if roi is None:
            return
        x, y, w, h = roi.rect
        self.info.setText(f"{name} -- Lage {x:.3f}/{y:.3f}, "
                          f"Groesse {w:.3f}x{h:.3f}")

    def _bild_erneuern(self) -> None:
        """Neues Bild unter die Rahmen legen -- die Rahmen bleiben stehen."""
        if self._bild_quelle is None:
            return
        bild = self._bild_quelle()
        if bild is None:
            return
        self.leinwand.set_bild(entzerre(bild, self._lane.quad))

    @property
    def rois(self) -> list[Roi]:
        return self.leinwand.rois

    def _uebernehmen(self) -> None:
        self.auf_alle = bool(self.alle is not None and self.alle.isChecked())
        self._takt.stop()
        self.accept()

    def reject(self) -> None:
        self._takt.stop()
        super().reject()
