"""Hauptfenster.

Phase 1 (Videoplayer) und Phase 2/3 (Kalibrierung, ROI-Konfiguration).
Die Ergebnistabellen sind als Platzhalter angelegt und werden in Phase 10 gefuellt.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..calibration import Calibration, list_calibrations
from ..calibration.geometry import GeometryError
from ..calibration.session import (
    CalibrationSession,
    CalibrationStep,
    GuideStep,
    roi_label,
    single_roi_choices,
)
from ..analysis.calibration_check import CheckVerdict, check_calibration
from ..analysis.pipeline import FrameResult
from ..config.schema import AppConfig
from ..detection.state_machine import EventType
from ..video import Frame, VideoInfo, is_stream, list_videos, open_source
from ..video.file_source import FileVideoSource
from ..video.source import VideoSourceError
from .analysis_worker import SPRUNG_LAEUFT, AnalysisWorker
from .lane_panel import LanePanel
from .player import VideoPlayer
from .video_view import VideoView

log = logging.getLogger(__name__)


class StatusLogHandler(logging.Handler):
    """Zeigt Warnungen und Fehler in der Statusleiste.

    WARUM ES DAS GIBT: Mit dem Reiter "Debug / Events" ist am 2026-09-03 das
    einzige Fenster verschwunden, in dem der Nutzer Log-Meldungen sehen konnte.
    Eine Warnung, die nur in der Konsole steht, existiert fuer ihn nicht -- und
    gerade die Kalibrierungswarnungen ("passt die Kalibrierung zu diesem
    Video?") sind die, auf die es ankommt.

    Nur WARNING und darueber. Info-Meldungen kommen im Sekundentakt und wuerden
    die Leiste zum Flackern bringen, ohne dass jemand sie liest.

    Qt-Widgets duerfen nur im GUI-Thread beruehrt werden. Log-Aufrufe kommen
    aber aus Worker-Threads, daher wird die Ausgabe ueber QTimer.singleShot in
    den GUI-Thread verlagert statt direkt geschrieben.
    """

    def __init__(self, fenster: QMainWindow) -> None:
        super().__init__(level=logging.WARNING)
        self._fenster = fenster
        self.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:  # noqa: BLE001 -- Logging darf die Anwendung nie stoppen
            return
        QTimer.singleShot(
            0, lambda: self._fenster.statusBar().showMessage(message, 8000))


class MainWindow(QMainWindow):
    def __init__(self, cfg: AppConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.player = VideoPlayer(cfg.video.max_consecutive_read_failures, self)
        self.session = CalibrationSession(
            warped_width=cfg.calibration.warped_width,
            warped_height=cfg.calibration.warped_height,
            # Sonst traegt jede frisch kalibrierte Bahn `real_lane_number: null`
            # und wird als 1..4 gemeldet -- auch im Versand.
            lane_number_mapping=cfg.calibration.lane_number_mapping,
        )
        self._current_frame: Frame | None = None
        self._calibration_path: Path | None = None
        self._worker: AnalysisWorker | None = None
        self._last_result: FrameResult | None = None
        self._throw_count = 0
        # Darf der Positionsschieber ueberhaupt bedient werden? Bei einem
        # Stream nicht -- dort gibt es nichts zu spulen. Der Merker haelt
        # das fest, damit `_update_controls` nach der Analyse nicht blind
        # wieder einschaltet, was vorher gesperrt war.
        self._slider_erlaubt = False
        # Laeuft gerade eine Analyse? Bewusst ein eigenes Kennzeichen und
        # nicht `self._worker is not None`: Der Worker wird nach dem Lauf
        # nicht zurueckgesetzt, die Wiedergabe bliebe sonst fuer immer
        # gesperrt. `isRunning()` waere kurz nach `start()` noch falsch.
        self._analyse_aktiv = False
        # Pfad der Vorschau, solange sie fuer die Analyse geschlossen ist.
        self._vorschau_pfad: str | None = None

        self.setWindowTitle("Kegel_CV - Automatische Kegelerfassung")
        self._apply_window_size()

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._refresh_video_list()
        self._refresh_calibration_list()
        self._update_controls()

        log.info("Anwendung gestartet")

    def _apply_window_size(self) -> None:
        """Passt das Fenster an den tatsaechlich verfuegbaren Bildschirm an.

        Eine feste Groesse aus der Konfiguration ist unbrauchbar, sobald der
        Bildschirm kleiner ist oder Windows mit 125/150 % skaliert: Das Fenster
        raegt dann ueber den Rand und Bedienelemente sind nicht erreichbar.
        `availableGeometry` beruecksichtigt bereits Taskleiste und Skalierung.
        """
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(self.cfg.gui.window_width, self.cfg.gui.window_height)
            return

        available = screen.availableGeometry()
        width = min(self.cfg.gui.window_width, int(available.width() * 0.95))
        height = min(self.cfg.gui.window_height, int(available.height() * 0.95))
        self.resize(width, height)

        # Mittig setzen, damit das Fenster nicht halb ausserhalb startet
        self.move(available.center().x() - width // 2,
                  available.center().y() - height // 2)

        if (self.cfg.gui.window_width > available.width()
                or self.cfg.gui.window_height > available.height()):
            log.info("Fenster auf %dx%d begrenzt (Bildschirm: %dx%d)",
                     width, height, available.width(), available.height())

    # ------------------------------------------------------------------- Aufbau

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Vertical)
        root.addWidget(splitter, 1)

        # --- oben: Video + Seitenleiste ---
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.video_view = VideoView()
        top_layout.addWidget(self.video_view, 1)

        # Seitenleiste scrollbar: Reicht die Fensterhoehe nicht, staucht Qt die
        # Widgets sonst bis zur Unkenntlichkeit -- im Extremfall auf Hoehe null,
        # sodass ganze Bedienbloecke unsichtbar werden.
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidget(self._build_sidebar())
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(300)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar_scroll.setFrameShape(QScrollArea.NoFrame)
        top_layout.addWidget(sidebar_scroll)
        splitter.addWidget(top)

        # --- Mitte: Transport ---
        root_transport = self._build_transport()

        # --- unten: Ergebnisse je Bahn ---
        #
        # Frueher lagen hier zwei Reiter, "Ergebnisse" und "Debug / Events".
        # Mit dem Wegfall des Debug-Reiters bleibt nur einer uebrig -- und ein
        # Reiter, der nie wechselt, ist ein Rahmen ohne Inhalt. Warnungen
        # zeigt jetzt die Statusleiste (`StatusLogHandler`).
        splitter.addWidget(self._build_lane_tables())
        splitter.setSizes([int(self.height() * 0.62), int(self.height() * 0.38)])

        root.addWidget(root_transport)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Bereit - bitte ein Video laden")

        # Erst JETZT anhaengen: Der Handler schreibt in die Statusleiste, die
        # es vor dieser Zeile noch nicht gibt.
        logging.getLogger().addHandler(StatusLogHandler(self))

    def _build_sidebar(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(270)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(8)

        # Video-Auswahl
        video_box = QGroupBox("Video")
        video_layout = QVBoxLayout(video_box)
        self.video_combo = QComboBox()
        video_layout.addWidget(self.video_combo)
        btn_load = QPushButton("Laden")
        btn_load.clicked.connect(self._on_load_selected_video)
        video_layout.addWidget(btn_load)

        # Livestream statt Datei. Fuer die Analyse ist das derselbe Weg -- die
        # Videoquelle wird in `video.factory` anhand des Schemas gewaehlt.
        self.stream_edit = QLineEdit()
        self.stream_edit.setPlaceholderText("oder Stream-URL (https://..., rtsp://...)")
        self.stream_edit.setToolTip(
            "Adresse eines laufenden Streams. Kalibrieren funktioniert genauso: "
            "Wiedergabe anhalten, Ecken anklicken, Analyse starten. "
            "Im Stream laesst sich nicht spulen -- ausgewertet wird ab jetzt."
        )
        self.stream_edit.returnPressed.connect(self._on_load_stream)
        video_layout.addWidget(self.stream_edit)
        btn_stream = QPushButton("Stream verbinden")
        btn_stream.clicked.connect(self._on_load_stream)
        video_layout.addWidget(btn_stream)
        self.video_info_label = QLabel("kein Video geladen")
        self.video_info_label.setWordWrap(True)
        self.video_info_label.setStyleSheet("color: #666; font-size: 11px;")
        video_layout.addWidget(self.video_info_label)

        # Die Aufloesung als eigene, farbige Zeile -- siehe `_on_video_opened`.
        # Einem Stream sieht man an der Adresse nicht an, welche Fassung
        # dahinterliegt; die Kalibrierung gilt aber nur fuer eine.
        self.resolution_label = QLabel()
        self.resolution_label.setWordWrap(True)
        self.resolution_label.setVisible(False)
        video_layout.addWidget(self.resolution_label)
        layout.addWidget(video_box)

        # Kalibrierung
        cal_box = QGroupBox("Kalibrierung")
        cal_layout = QVBoxLayout(cal_box)

        # Aktive Bahn waehlen, OHNE die Eckpunkte neu zu setzen.
        # Ohne diese Auswahl waere nach dem Laden einer Kalibrierung keine Bahn
        # aktiv -- und alle folgenden Schritte (Bereiche, Ziffern) waeren
        # unerreichbar, ohne die Ecken erneut zu klicken.
        lane_row = QHBoxLayout()
        lane_row.addWidget(QLabel("aktive Bahn:"))
        self.active_lane_combo = QComboBox()
        self.active_lane_combo.currentIndexChanged.connect(self._on_select_active_lane)
        lane_row.addWidget(self.active_lane_combo, 1)
        cal_layout.addLayout(lane_row)

        # UNTER WELCHER BAHNNUMMER DIESE TAFEL GEMELDET WIRD.
        #
        # Die Tafeln im Bild sind von links durchnummeriert, die Ergebnisse
        # tragen aber die Bahnnummer der Halle. In der Stammhalle sind das die
        # Bahnen 2 bis 5; auswaerts kann dieselbe Anordnung 1 bis 4 heissen.
        # Bisher stand die Zuordnung nur in der Konfigurationsdatei -- also
        # nicht dort, wo man vor Ort steht.
        nummer_row = QHBoxLayout()
        nummer_row.addWidget(QLabel("meldet als Bahn:"))
        self.lane_number_spin = QSpinBox()
        self.lane_number_spin.setRange(1, 99)
        self.lane_number_spin.setToolTip(
            "Diese Zahl steht als Bahnnummer in der Datenbank und im "
            "Liveticker. Sie gilt fuer die oben gewaehlte Tafel und wird mit "
            "der Kalibrierung gespeichert."
        )
        self.lane_number_spin.valueChanged.connect(self._on_lane_number_changed)
        nummer_row.addWidget(self.lane_number_spin, 1)
        cal_layout.addLayout(nummer_row)

        # Die frueheren Knoepfe "Bahn N kalibrieren" sind entfallen: Sie
        # starteten denselben Vorgang wie die gefuehrte Kalibrierung, nur ohne
        # Fuehrung und je Bahn einzeln. Zwei Wege zum selben Ziel, von denen
        # einer schlechter ist, sind eine Falle -- nicht eine Auswahl.

        self.calibration_hint = QLabel("Video laden, dann gefuehrt kalibrieren")
        self.calibration_hint.setWordWrap(True)
        self.calibration_hint.setMinimumHeight(46)
        self.calibration_hint.setStyleSheet(
            "background:#2d2d2d; color:#eee; padding:6px; border-radius:3px;"
        )
        cal_layout.addWidget(self.calibration_hint)

        row = QHBoxLayout()
        btn_undo = QPushButton("Punkt zurueck")
        btn_undo.clicked.connect(self._on_undo_point)
        row.addWidget(btn_undo)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.setToolTip("Aktuellen Schritt abbrechen (Esc)")
        btn_cancel.clicked.connect(self._on_cancel_calibration)
        row.addWidget(btn_cancel)
        cal_layout.addLayout(row)

        self.btn_guide = QPushButton("Gefuehrt kalibrieren")
        self.btn_guide.setToolTip(
            "Fuehrt durch alle vier Bahnen: Bahn 1 vollstaendig, danach werden "
            "ihre Felder auf die uebrigen uebernommen -- nur die Tafelecken "
            "sind dort noch zu setzen. Am Ende laesst sich jedes Feld einzeln "
            "nachziehen."
        )
        self.btn_guide.setStyleSheet("font-weight:bold; padding:6px;")
        self.btn_guide.clicked.connect(self._on_start_guide)
        cal_layout.addWidget(self.btn_guide)

        # EINE TAFEL GENUEGT. Ist eine Bahn vermessen, findet der Rechner die
        # uebrigen desselben Bautyps -- die ROIs liegen in normierten
        # Tafelkoordinaten, also folgen Lampen und Ziffern aus den vier Ecken.
        self.btn_find_lanes = QPushButton("Weitere Bahnen finden")
        self.btn_find_lanes.setToolTip(
            "Nimmt die aktive Bahn als Muster und sucht alle Tafeln desselben "
            "Bautyps im aktuellen Bild. Danach werden die Bahnnummern "
            "abgefragt. Am besten mit einer moeglichst frontal gesehenen "
            "Tafel als Muster."
        )
        self.btn_find_lanes.setStyleSheet("padding:6px;")
        self.btn_find_lanes.clicked.connect(self._on_find_lanes)
        cal_layout.addWidget(self.btn_find_lanes)

        # ENTFALLEN mit dem Umbau vom 2026-09-03: "Bereiche anklicken (14)",
        # "nur Raute" und "Ziffern einzeln einrahmen (8)" samt Feldauswahl.
        #
        # Alle drei setzten Rahmen NEU -- und das ist seit der gefuehrten
        # Kalibrierung ueberfluessig: Sie legt jeden Rahmen an eine gemessene
        # Stelle, und jeder Rahmen laesst sich danach mit der Maus ziehen. Ein
        # zweiter, umstaendlicherer Weg zum selben Ergebnis kostet den Nutzer
        # nur die Entscheidung, welchen er nehmen soll.
        #
        # `ueberspringen` bleibt: Es gehoert zum ABLAUF der Fuehrung, nicht zum
        # Neusetzen -- damit laesst sich ein Bereich unveraendert lassen.
        row_roi = QHBoxLayout()
        btn_skip = QPushButton("ueberspringen")
        btn_skip.setToolTip("Diesen Bereich unveraendert lassen")
        btn_skip.clicked.connect(self._on_skip_roi)
        row_roi.addWidget(btn_skip)
        cal_layout.addLayout(row_roi)

        self.roi_combo = QComboBox()
        self.roi_combo.setToolTip(
            "Einzelnen Bereich gezielt neu setzen. Ziffernstellen sind einzeln "
            "dabei -- sie werden ueber ZWEI Ecken gesetzt (oben links, unten "
            "rechts), alles andere ueber einen Klick in die Mitte."
        )
        self.roi_combo.addItem("-- einzelnen Bereich neu setzen --", None)
        for name in single_roi_choices():
            self.roi_combo.addItem(roi_label(name), name)
        self.roi_combo.currentIndexChanged.connect(self._on_select_single_roi)
        cal_layout.addWidget(self.roi_combo)

        # Stand HIER frueher nicht, sondern unter "Live-Analyse". Dort war er
        # fehl am Platz: Der Knopf misst die gruenen Lampen ueber mehrere
        # Frames und meldet, welche Bahn nachjustiert werden muss -- das ist
        # eine Aussage ueber die Kalibrierung, nicht ueber die Analyse.
        self.btn_check = QPushButton("Kalibrierung pruefen")
        self.btn_check.setMinimumHeight(28)
        self.btn_check.setToolTip(
            "Misst die gruenen Lampen ueber mehrere Frames und meldet, welche "
            "Bahn nachjustiert werden muss"
        )
        self.btn_check.clicked.connect(self._on_check_calibration)
        cal_layout.addWidget(self.btn_check)

        self.calibration_combo = QComboBox()
        cal_layout.addWidget(self.calibration_combo)
        row2 = QHBoxLayout()
        btn_save = QPushButton("Speichern")
        btn_save.clicked.connect(self._on_save_calibration)
        row2.addWidget(btn_save)
        btn_load_cal = QPushButton("Laden")
        btn_load_cal.clicked.connect(self._on_load_calibration)
        row2.addWidget(btn_load_cal)
        cal_layout.addLayout(row2)

        layout.addWidget(cal_box)

        # --- Ansicht / Zoom ---
        zoom_box = QGroupBox("Ansicht")
        zoom_layout = QVBoxLayout(zoom_box)
        self.zoom_label = QLabel("Zoom 1.0x")
        self.zoom_label.setStyleSheet("color:#888; font-size:11px;")
        zoom_layout.addWidget(self.zoom_label)

        zoom_row = QHBoxLayout()
        for text, factor in (("−", 1 / 1.6), ("+", 1.6)):
            btn = QPushButton(text)
            btn.setFixedSize(32, 26)
            btn.clicked.connect(lambda _=False, f=factor: self._on_zoom_step(f))
            zoom_row.addWidget(btn)
        btn_fit = QPushButton("ganzes Bild")
        btn_fit.setMinimumHeight(26)
        btn_fit.clicked.connect(self.video_view.reset_zoom)
        zoom_row.addWidget(btn_fit, 1)
        zoom_layout.addLayout(zoom_row)

        lane_zoom_row = QHBoxLayout()
        lane_zoom_row.addWidget(QLabel("auf Tafel:"))
        for lane_id in range(1, self.cfg.calibration.lane_count + 1):
            btn = QPushButton(str(lane_id))
            btn.setFixedSize(30, 26)
            btn.setToolTip(f"Auf die Anzeigetafel von Bahn {lane_id} zoomen")
            btn.clicked.connect(lambda _=False, n=lane_id: self._zoom_to_lane(n))
            lane_zoom_row.addWidget(btn)
        zoom_layout.addLayout(lane_zoom_row)

        hint = QLabel("Mausrad = Zoom, mittlere Taste = schieben")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#777; font-size:10px;")
        zoom_layout.addWidget(hint)
        layout.addWidget(zoom_box)

        # --- Live-Analyse ---
        analysis_box = QGroupBox("Live-Analyse")
        analysis_layout = QVBoxLayout(analysis_box)

        self.btn_analyze = QPushButton("Analyse starten")
        self.btn_analyze.setStyleSheet(
            "font-weight:bold; padding:6px; background:#1e7d32; color:white;"
        )
        self.btn_analyze.setMinimumHeight(34)
        self.btn_analyze.setToolTip(
            "Wertet das Video durchgehend aus und zeigt die Ergebnisse live an"
        )
        self.btn_analyze.clicked.connect(self._on_toggle_analysis)
        analysis_layout.addWidget(self.btn_analyze)

        # Ab der aktuellen Stelle auswerten. Vor einem Spiel wird warmgespielt,
        # und diese Wuerfe gehoeren nicht in die Auswertung.
        self.chk_ab_hier = QCheckBox("ab aktueller Stelle starten")
        self.chk_ab_hier.setToolTip(
            "Wertet erst ab dem gerade angezeigten Frame aus -- zum "
            "Ueberspringen des Warmspielens. Bei einem Livestream ohne "
            "Wirkung: dort gibt es keinen Anfang."
        )
        analysis_layout.addWidget(self.chk_ab_hier)

        # Versand getrennt schaltbar -- auch WAEHREND die Analyse laeuft.
        # Beim Warmspielen soll nichts in die Datenbank, sichtbar sein soll es
        # trotzdem.
        self.chk_senden = QCheckBox("an Datenbank senden")
        self.chk_senden.setChecked(True)
        self.chk_senden.setToolTip(
            "Aus: Es wird weiterhin ausgewertet, angezeigt und protokolliert "
            "-- nur nicht gesendet. Laesst sich jederzeit umschalten, auch "
            "mitten in der Analyse."
        )
        self.chk_senden.toggled.connect(self._on_toggle_senden)
        analysis_layout.addWidget(self.chk_senden)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Tempo:"))
        self.speed_combo = QComboBox()
        # Echtzeit ist beim Zuschauen oft nützlicher als Vollgas -- man will
        # erkennen, was passiert, nicht nur dass es passiert.
        self.speed_combo.addItem("Echtzeit (25 fps)", 25.0)
        self.speed_combo.addItem("halbes Tempo", 12.5)
        self.speed_combo.addItem("so schnell wie moeglich", 0.0)
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        speed_row.addWidget(self.speed_combo, 1)
        analysis_layout.addLayout(speed_row)

        self.analysis_status = QLabel("nicht gestartet")
        self.analysis_status.setWordWrap(True)
        self.analysis_status.setStyleSheet("color:#888; font-size:11px;")
        analysis_layout.addWidget(self.analysis_status)
        layout.addWidget(analysis_box)

        # Der Kasten "Debug" mit "Frame speichern" und "Entzerrte Tafeln
        # speichern" ist am 2026-09-03 entfallen. Beides sind Werkzeuge fuer
        # die Fehlersuche, nicht fuer den taeglichen Gebrauch -- und beides
        # leistet `tools/export_roi_frames.py` gruendlicher, weil es die
        # Rahmen und die gelesenen Werte gleich mit einzeichnet.

        layout.addStretch(1)
        return panel

    def _build_transport(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.btn_prev = QPushButton("<<")
        self.btn_prev.setFixedWidth(48)
        self.btn_prev.setToolTip("Ein Frame zurueck (Pfeil links)")
        self.btn_play = QPushButton("Play")
        self.btn_play.setFixedWidth(70)
        self.btn_play.setToolTip("Wiedergabe (Leertaste)")
        self.btn_next = QPushButton(">>")
        self.btn_next.setFixedWidth(48)
        self.btn_next.setToolTip("Ein Frame vor (Pfeil rechts)")

        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            layout.addWidget(btn)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setEnabled(False)
        layout.addWidget(self.position_slider, 1)

        self.position_label = QLabel("Frame 0 / 0    t = 0.00 s")
        self.position_label.setFont(QFont("Consolas", 10))
        self.position_label.setMinimumWidth(260)
        layout.addWidget(self.position_label)

        return widget

    def _build_lane_tables(self) -> QWidget:
        """Live-Anzeige je Bahn. Wird beim Laden einer Kalibrierung neu aufgebaut,
        weil erst dann feststeht, welche Bahnen es gibt."""
        self.lane_container = QWidget()
        self.lane_layout = QHBoxLayout(self.lane_container)
        self.lane_layout.setSpacing(6)
        self.lane_panels: dict[int, LanePanel] = {}
        self._rebuild_lane_panels()
        return self.lane_container

    def _on_find_lanes(self) -> None:
        """Sucht alle Tafeln desselben Bautyps anhand der aktiven Bahn.

        WOFUER: In einer fremden Halle genuegt es, EINE Tafel von Hand zu
        vermessen. Die uebrigen findet der Merkmalsabgleich -- an einem
        Trainingsmitschnitt auf ein bis drei Pixel genau, und die daraus
        erzeugte Kalibrierung schnitt in der Analyse besser ab als die von
        Hand gesetzte.

        Welche Bahnnummer welche Tafel traegt, kann der Rechner nicht wissen
        -- das steht an der Wand. Deshalb die Rueckfrage am Ende.
        """
        from ..calibration.board_finder import (BoardFinder, entzerre,
                                                quad_groesse)

        frame = self.player.current_frame
        if frame is None or not self.session.calibration.lanes:
            QMessageBox.information(
                self, "Noch nichts zu suchen",
                "Erst ein Video laden und mindestens eine Tafel kalibrieren "
                "-- sie dient als Muster fuer die uebrigen.")
            return

        aktiv = self.session.active_lane
        muster = next((l for l in self.session.calibration.lanes
                       if l.lane_id == aktiv), self.session.calibration.lanes[0])

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            groesse = quad_groesse(muster.quad)
            vorlage = entzerre(frame.image, muster.quad, groesse)
            finder = BoardFinder()
            treffer = finder.finde_alle(frame.image, [vorlage])
            # Zweiter Durchgang mit dem besten Treffer als Muster: gleiche
            # Kamera, gleiches Licht. GEMESSEN: 92 -> 176 tragende Merkmale.
            if treffer:
                bester = max(treffer, key=lambda t: t.inlier)
                eigene = entzerre(frame.image, bester.quad,
                                  quad_groesse(bester.quad))
                zweite = BoardFinder().finde_alle(frame.image, [eigene])
                if (len(zweite) >= len(treffer)
                        and sum(t.inlier for t in zweite)
                        > sum(t.inlier for t in treffer)):
                    treffer = zweite
        finally:
            QApplication.restoreOverrideCursor()

        if not treffer:
            QMessageBox.warning(
                self, "Keine Tafel gefunden",
                "In diesem Bild liess sich keine weitere Tafel zuordnen.\n\n"
                "Moegliche Gruende: anderer Bautyp, sehr anderer Blickwinkel, "
                "oder das Bild taugt nicht (jemand davor, Bewegungsunschaerfe). "
                "Ein anderes Standbild waehlen und erneut versuchen.")
            return

        vorschlag = " ".join(str(i) for i in range(1, len(treffer) + 1))
        bestehende = [l.display_number for l in self.session.calibration.lanes]
        if len(bestehende) == len(treffer):
            vorschlag = " ".join(str(n) for n in bestehende)

        text, ok = QInputDialog.getText(
            self, "Bahnnummern",
            f"{len(treffer)} Tafeln gefunden, von links nach rechts.\n"
            f"Welche Bahnnummern tragen sie?",
            text=vorschlag)
        if not ok:
            return
        teile = text.replace(",", " ").split()
        if len(teile) != len(treffer) or not all(t.isdigit() for t in teile):
            QMessageBox.warning(
                self, "Eingabe passt nicht",
                f"{len(treffer)} Zahlen erwartet, {len(teile)} bekommen.")
            return

        neu = []
        for i, (t, nummer) in enumerate(zip(treffer, teile), start=1):
            bahn = muster.model_copy(deep=True)
            bahn.lane_id = i
            bahn.real_lane_number = int(nummer)
            bahn.quad = t.quad
            neu.append(bahn)
        self.session.calibration.lanes = neu
        self.session.active_lane = 1

        self._refresh_active_lane_combo()
        self._rebuild_lane_panels()
        self._update_calibration_hint()
        traeger = ", ".join(f"{t.inlier}" for t in treffer)
        self.statusBar().showMessage(
            f"{len(treffer)} Bahnen uebernommen (tragende Merkmale: "
            f"{traeger}). Rahmen pruefen, dann speichern.", 10000)
        log.info("Automatisch gefunden: %d Tafeln, Bahnnummern %s",
                 len(treffer), teile)

    def _refresh_lane_number_spin(self) -> None:
        """Zeigt die Bahnnummer der gerade gewaehlten Tafel an.

        `blockSignals`, damit das Nachfuehren nicht als Nutzereingabe gilt --
        sonst schriebe die Anzeige den Wert zurueck, den sie gerade erst
        gelesen hat.
        """
        if not hasattr(self, "lane_number_spin"):
            return
        aktiv = self.session.active_lane
        bahn = next((l for l in self.session.calibration.lanes
                     if l.lane_id == aktiv), None)
        self.lane_number_spin.blockSignals(True)
        self.lane_number_spin.setEnabled(bahn is not None)
        if bahn is not None:
            self.lane_number_spin.setValue(bahn.display_number)
        self.lane_number_spin.blockSignals(False)

    def _on_lane_number_changed(self, wert: int) -> None:
        aktiv = self.session.active_lane
        if aktiv is None:
            return
        warnung = self.session.set_real_lane_number(aktiv, wert)
        # Die Beschriftungen tragen die Bahnnummer -- sie muessen mit.
        self._refresh_active_lane_combo()
        self._rebuild_lane_panels()
        if warnung:
            self.statusBar().showMessage(warnung, 8000)
            log.warning("%s", warnung)
        else:
            self.statusBar().showMessage(
                f"Tafel {aktiv} von links meldet als Bahn {wert}. "
                f"Nicht vergessen: Kalibrierung speichern.", 5000)

    def _refresh_active_lane_combo(self) -> None:
        """Fuellt die Bahnauswahl passend zur aktuellen Kalibrierung."""
        if not hasattr(self, "active_lane_combo"):
            return
        self.active_lane_combo.blockSignals(True)
        self.active_lane_combo.clear()
        for lane in self.session.calibration.lanes:
            label = (f"Bahn {lane.display_number}" if lane.display_number == lane.lane_id
                     else f"Bahn {lane.display_number} (Tafel {lane.lane_id})")
            self.active_lane_combo.addItem(label, lane.lane_id)
        if not self.session.calibration.lanes:
            self.active_lane_combo.addItem("(noch nicht kalibriert)", None)
        self.active_lane_combo.blockSignals(False)
        self._refresh_lane_number_spin()

        # Erste Bahn automatisch aktiv setzen
        first = self.active_lane_combo.itemData(0)
        if first is not None and self.session.active_lane is None:
            self.session.active_lane = first
            self.session.step = CalibrationStep.EDIT_ROIS
            self._update_calibration_hint()

    def _on_select_active_lane(self, index: int) -> None:
        """Waehlt die Bahn, auf die sich die naechsten Schritte beziehen."""
        lane_id = self.active_lane_combo.itemData(index)
        if lane_id is None:
            return
        self.session.active_lane = lane_id
        self.session.pending_points.clear()
        self.session.roi_queue.clear()
        self.session.active_roi = None
        self.session.step = CalibrationStep.EDIT_ROIS
        self._zoom_to_lane(lane_id)
        # Die Bahnnummer gehoert zur Tafel, nicht zur Sitzung -- beim Wechsel
        # muss die Anzeige mit.
        self._refresh_lane_number_spin()
        self._update_calibration_hint()

    def _rebuild_lane_panels(self) -> None:
        """Erzeugt die Bahn-Panels passend zur aktuellen Kalibrierung."""
        while self.lane_layout.count():
            item = self.lane_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.lane_panels.clear()

        lanes = self.session.calibration.lanes
        if lanes:
            entries = [(l.lane_id, l.display_number) for l in lanes]
        else:
            # Noch keine Kalibrierung: Platzhalter mit der konfigurierten Zuordnung
            mapping = self.cfg.calibration.lane_number_mapping
            entries = [
                (i, mapping[i - 1] if mapping and i <= len(mapping) else i)
                for i in range(1, self.cfg.calibration.lane_count + 1)
            ]

        for lane_id, display_number in entries:
            panel = LanePanel(lane_id, display_number)
            self.lane_panels[lane_id] = panel
            self.lane_layout.addWidget(panel)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&Datei")

        act_open = QAction("Video oeffnen...", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self._on_open_video_dialog)
        file_menu.addAction(act_open)
        file_menu.addSeparator()

        act_quit = QAction("Beenden", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        view_menu = self.menuBar().addMenu("&Ansicht")
        self.act_labels = QAction("ROI-Beschriftungen", self, checkable=True)
        self.act_labels.setChecked(self.cfg.gui.show_roi_labels)
        self.act_labels.toggled.connect(self.video_view.set_show_labels)
        view_menu.addAction(self.act_labels)

        self.act_overlay = QAction("Debug-Overlay", self, checkable=True)
        self.act_overlay.setChecked(self.cfg.gui.show_debug_overlay)
        self.act_overlay.toggled.connect(lambda _: self._update_overlay_text())
        view_menu.addAction(self.act_overlay)

    def _connect_signals(self) -> None:
        self.player.frame_ready.connect(self._on_frame)
        self.player.opened.connect(self._on_video_opened)
        self.player.error.connect(self._on_player_error)
        self.player.state_changed.connect(
            lambda playing: self.btn_play.setText("Pause" if playing else "Play")
        )
        self.player.finished.connect(
            lambda: self.statusBar().showMessage("Videoende erreicht", 4000)
        )

        self.btn_play.clicked.connect(self.player.toggle)
        self.btn_next.clicked.connect(self.player.step_forward)
        self.btn_prev.clicked.connect(self.player.step_backward)
        self.position_slider.sliderMoved.connect(self.player.seek)

        self.video_view.clicked.connect(self._on_video_clicked)
        self.video_view.quad_corner_dragged.connect(self._on_drag_corner)
        self.video_view.roi_dragged.connect(self._on_drag_roi)
        self.video_view.roi_resized.connect(self._on_resize_roi)
        self.video_view.drag_finished.connect(self._on_drag_finished)
        self.video_view.zoom_changed.connect(
            lambda z: self.zoom_label.setText(f"Zoom {z:.1f}x")
        )

    # -------------------------------------------------------------- Videoliste

    def _refresh_video_list(self) -> None:
        directory = self.cfg.resolve(self.cfg.video.directory)
        self.video_combo.clear()
        videos = list_videos(directory)
        for video in videos:
            size_mb = video.stat().st_size / 1e6
            self.video_combo.addItem(f"{video.name}  ({size_mb:.0f} MB)", str(video))
        if not videos:
            self.video_combo.addItem("(keine Videos gefunden)", None)
        log.info("%d Videos gefunden in %s", len(videos), directory)

    def _refresh_calibration_list(self) -> None:
        directory = self.cfg.resolve(self.cfg.calibration.directory)
        self.calibration_combo.clear()
        files = list_calibrations(directory)
        for path in files:
            self.calibration_combo.addItem(path.stem, str(path))
        if not files:
            self.calibration_combo.addItem("(keine Kalibrierung)", None)

    # ------------------------------------------------------------------ Video

    def _on_load_selected_video(self) -> None:
        path = self.video_combo.currentData()
        if path:
            self._load_video(Path(path))

    def _on_open_video_dialog(self) -> None:
        directory = str(self.cfg.resolve(self.cfg.video.directory))
        path, _ = QFileDialog.getOpenFileName(
            self, "Video oeffnen", directory, "Videos (*.mp4 *.mkv *.mov *.avi)"
        )
        if path:
            self._load_video(Path(path))

    def _load_video(self, path: Path) -> None:
        if self.player.load(path, self.cfg.video.playback_fps):
            self.statusBar().showMessage(f"Geladen: {path.name}", 4000)

    def _on_load_stream(self) -> None:
        """Verbindet mit einem Livestream statt einer Datei."""
        url = self.stream_edit.text().strip()
        if not url:
            return
        if not is_stream(url):
            QMessageBox.information(
                self, "Keine Stream-Adresse",
                "Das sieht nicht nach einer Stream-Adresse aus. Erwartet wird "
                "etwas wie https://... oder rtsp://... "
                "Fuer eine Datei den Weg darueber benutzen."
            )
            return

        self.statusBar().showMessage(f"Verbinde mit {url} ...")
        if self.player.load(url, self.cfg.video.playback_fps):
            self.statusBar().showMessage(f"Stream verbunden: {url}", 6000)
            # Im Stream gibt es nichts zu spulen -- der Schieber wuerde nur
            # Erwartungen wecken, die die Quelle nicht erfuellen kann.
            self._slider_erlaubt = False
            self._update_controls()
        else:
            self.statusBar().showMessage("Stream nicht erreichbar", 8000)

    def _on_video_opened(self, info: VideoInfo) -> None:
        duration = info.duration_s or 0

        # Kalibrierung gegen die Videomasse pruefen -- eine unpassende
        # Kalibrierung liefert sonst STILL falsche ROIs.
        warnungen = self.session.calibration.check_against_video(
            info.width, info.height)
        for warning in warnungen:
            log.warning(warning)

        # DIE AUFLOESUNG GEHOERT INS AUGE, nicht ins Log. Bei einem Stream sieht
        # man der Adresse nicht an, welche Fassung dahinter liegt -- eine
        # falsche Wahl faellt sonst erst auf, wenn die Analyse Unsinn liefert.
        # Deshalb: gross, und farblich beantwortet, ob sie zur Kalibrierung passt.
        hint = self.session.calibration.source_hint
        passt = not (hint.width and hint.width != info.width
                     or hint.height and hint.height != info.height)
        if not hint.width:
            farbe, urteil = "#bbb", "keine Kalibrierung geladen"
        elif passt:
            farbe, urteil = "#5cb85c", f"passt zur Kalibrierung ({hint.width}x{hint.height})"
        else:
            farbe, urteil = "#d9534f", (f"PASST NICHT -- Kalibrierung ist fuer "
                                        f"{hint.width}x{hint.height}")
        self.video_info_label.setText(
            f"{info.source_id}\n"
            f"<b>{info.width} x {info.height}</b>, {info.fps:.2f} fps\n"
            f"{info.frame_count or '?'} Frames, {duration:.1f} s"
        )
        self.resolution_label.setText(
            f"{info.width} x {info.height} -- {urteil}")
        self.resolution_label.setStyleSheet(
            f"background:{farbe}; color:#111; padding:4px; border-radius:3px;"
            "font-weight:bold;"
        )
        self.resolution_label.setVisible(True)

        self._slider_erlaubt = True
        self.position_slider.setRange(0, max(0, (info.frame_count or 1) - 1))
        self._update_controls()

    def _on_player_error(self, message: str) -> None:
        QMessageBox.critical(self, "Videofehler", message)
        self.statusBar().showMessage(f"Fehler: {message}", 8000)

    def _on_frame(self, frame: Frame) -> None:
        # Waehrend der Analyse gehoert die Anzeige der Analyse. Die gesperrten
        # Bedienelemente allein genuegen als Schutz nicht: Der Player kann auch
        # von anderer Stelle einen Frame liefern, und ein einziger davon
        # reisst das Bild an eine voellig andere Stelle der Aufnahme.
        if self._analyse_aktiv:
            return
        self._current_frame = frame
        self.video_view.set_frame(frame.image)

        info = self.player.info
        total = (info.frame_count or 0) if info else 0
        self.position_label.setText(
            f"Frame {frame.index} / {total}    t = {frame.timestamp:6.2f} s"
        )
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(frame.index)
        self._update_overlay_text()

    # ------------------------------------------------------------ Kalibrierung


    def _on_zoom_step(self, factor: float) -> None:
        """Zoomt um einen festen Faktor, verankert in der Bildmitte."""
        self.video_view.set_zoom(self.video_view.zoom * factor)

    def _zoom_to_lane(self, lane_id: int) -> None:
        """Zoomt auf die Anzeigetafel einer Bahn.

        Ohne das waere das Setzen der ROIs kaum moeglich: Eine Tafel misst rund
        160x155 px im Originalframe, eine einzelne Kegellampe darin etwa 12 px --
        im eingepassten Video sind das wenige Bildschirmpixel.
        """
        lane = self.session.calibration.get_lane(lane_id)
        if lane is None:
            return
        xs = [p[0] for p in lane.quad]
        ys = [p[1] for p in lane.quad]
        self.video_view.zoom_to_frame_rect(
            min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        )


    def _on_start_guide(self) -> None:
        """Startet die gefuehrte Kalibrierung bei Bahn 1."""
        if self._current_frame is None:
            QMessageBox.information(
                self, "Kein Bild",
                "Bitte zuerst ein Video oder einen Stream laden.")
            return
        self.player.pause()
        self.session.start_guide(self.cfg.calibration.lane_count)
        self._update_calibration_hint()
        self._redraw_overlays()

    def _guide_pruefen(self) -> None:
        """Rueckt die Fuehrung vor, sobald ein Schritt fertig ist.

        Der laufende Schritt meldet sich ueber `session.step`: Steht er wieder
        auf EDIT_ROIS, ist er abgeschlossen.
        """
        if not self.session.guide_active:
            return
        if self.session.step is not CalibrationStep.EDIT_ROIS:
            return
        self.session.guide_advance()
        if self.session.guide_lane:
            self._zoom_to_lane(self.session.guide_lane)
        self._update_calibration_hint()
        self._redraw_overlays()


    def _on_skip_roi(self) -> None:
        if self.session.step is CalibrationStep.PICK_ROIS:
            self.session.skip_roi()
            self._update_calibration_hint()

    def _on_select_single_roi(self, index: int) -> None:
        name = self.roi_combo.itemData(index)
        if not name or self.session.active_lane is None:
            return
        self.player.pause()
        if self.session.select_roi(name):
            self._update_calibration_hint()
        # Auswahl zuruecksetzen, damit dieselbe ROI erneut waehlbar bleibt
        self.roi_combo.blockSignals(True)
        self.roi_combo.setCurrentIndex(0)
        self.roi_combo.blockSignals(False)

    def _on_drag_corner(self, lane_id: int, index: int,
                        x: float, y: float) -> None:
        """Eine Tafelecke ziehen. Die ROIs wandern mit -- sie sind normiert."""
        if self.session.move_quad_corner(lane_id, index, x, y):
            self._redraw_overlays()

    def _on_drag_roi(self, lane_id: int, name: str, x: float, y: float) -> None:
        if self.session.move_roi(lane_id, name, x, y):
            self._redraw_overlays()

    def _on_resize_roi(self, lane_id: int, name: str, kante: str,
                       x: float, y: float) -> None:
        """Einen Rand oder eine Ecke eines Bereichs verziehen."""
        if self.session.resize_roi(lane_id, name, kante, x, y):
            self._redraw_overlays()

    def _on_drag_finished(self) -> None:
        """Nach dem Loslassen pruefen -- waehrend des Ziehens waere jede
        Zwischenlage kurzzeitig ungueltig."""
        for lane in self.session.calibration.lanes:
            ok, meldung = self.session.validate_quad(lane.lane_id)
            if not ok:
                self.statusBar().showMessage(
                    f"Bahn {lane.display_number}: {meldung}", 6000)
                return
        self._redraw_overlays()
        self.statusBar().showMessage("Kalibrierung angepasst", 2000)

    def _on_video_clicked(self, x: float, y: float) -> None:
        if self.session.step is CalibrationStep.FRAME_DIGITS:
            done = self.session.frame_digit(x, y)
            self.video_view.set_pending_points(
                self.session.active_lane, self.session.pending_points
            )
            self._redraw_overlays()
            if done:
                self.statusBar().showMessage(
                    f"Bahn {self.session.active_lane}: alle Ziffern eingerahmt", 5000
                )
                self._guide_pruefen()
            self._update_calibration_hint()
            return

        if self.session.step is CalibrationStep.PICK_ROIS:
            done = self.session.place_roi(x, y)
            self._redraw_overlays()
            if done:
                self.statusBar().showMessage(
                    f"Bahn {self.session.active_lane}: alle Bereiche gesetzt", 4000
                )
                self._guide_pruefen()
            self._update_calibration_hint()
            return

        if self.session.step is not CalibrationStep.PICK_CORNERS:
            return

        complete = self.session.add_point(x, y)
        self.video_view.set_pending_points(self.session.active_lane,
                                           self.session.pending_points)

        if complete:
            ok, message = self.session.try_commit()
            if ok:
                info = self.player.info
                if info:
                    self.session.set_source_hint(info.width, info.height, info.source_id)
                self.statusBar().showMessage(
                    message + " -- jetzt 'Bereiche anklicken' fuer die Raute", 6000
                )
                # Panels an die neue Kalibrierung anpassen -- sonst zeigen sie
                # noch die Platzhalter-Nummern, und erkannte Wuerfe faenden kein
                # Ziel.
                self._rebuild_lane_panels()
                self._refresh_active_lane_combo()
                # Direkt auf die frisch kalibrierte Tafel zoomen
                if self.session.active_lane is not None:
                    self._zoom_to_lane(self.session.active_lane)
                self._guide_pruefen()
            else:
                QMessageBox.warning(self, "Kalibrierung fehlgeschlagen", message)
                # Punkte behalten, damit der Nutzer einzeln korrigieren kann
                self.session.step = CalibrationStep.PICK_CORNERS
            self.video_view.set_pending_points(None, self.session.pending_points)
            self._redraw_overlays()

        self._update_calibration_hint()

    def _on_undo_point(self) -> None:
        if self.session.undo_point():
            self.video_view.set_pending_points(self.session.active_lane,
                                               self.session.pending_points)
            self._update_calibration_hint()

    def _on_cancel_calibration(self) -> None:
        self.session.cancel()
        self.video_view.set_pending_points(None, [])
        self._update_calibration_hint()

    def _update_calibration_hint(self) -> None:
        label = self.session.next_corner_label
        roi_hint = self.session.current_roi_label

        # Waehrend der Fuehrung sagt sie, was zu tun ist -- ein Satz statt
        # dreier Bedienelemente, zwischen denen man selbst waehlen muss.
        if self.session.guide_step is not GuideStep.AUS:
            self.calibration_hint.setText(self.session.guide_hint)
            self.video_view.set_status_text(self.session.guide_hint)
            self.video_view.set_drag_enabled(
                self.session.step in (CalibrationStep.IDLE,
                                      CalibrationStep.EDIT_ROIS))
            return

        # Ziehen und Setzen schliessen sich aus. Solange etwas gesetzt wird,
        # bedeutet ein Klick "hier hin" -- bliebe das Ziehen aktiv, griffe er
        # stattdessen den Bereich darunter, und da jede Ziffer innerhalb ihres
        # Gesamtfeldes liegt, waere keine Ziffer mehr einrahmbar.
        self.video_view.set_drag_enabled(
            self.session.step in (CalibrationStep.IDLE, CalibrationStep.EDIT_ROIS)
        )

        if label:
            self.calibration_hint.setText(
                f"Bahn {self.session.active_lane}:\n"
                f"Punkt {len(self.session.pending_points) + 1} von 4 -- "
                f"{label} anklicken"
            )
        elif self.session.step is CalibrationStep.FRAME_DIGITS and roi_hint:
            done, total = self.session.roi_progress
            ecke = self.session.digit_corner_label or ""
            self.calibration_hint.setText(
                f"Bahn {self.session.active_lane} — Ziffer {done + 1} von {total}\n"
                f"{roi_hint}\n"
                f"Ecke {ecke} anklicken"
            )
        elif roi_hint:
            done, total = self.session.roi_progress
            self.calibration_hint.setText(
                f"Bahn {self.session.active_lane} -- Bereich {done + 1} von {total}:\n"
                f"MITTE von \"{roi_hint}\" anklicken"
            )
        elif self.session.step is CalibrationStep.EDIT_ROIS:
            lane = self.session.calibration.get_lane(self.session.active_lane or 0)
            missing = len(lane.missing_rois()) if lane else 0
            self.calibration_hint.setText(
                f"Bahn {self.session.active_lane} kalibriert.\n"
                f"{len(lane.rois) if lane else 0} ROIs gesetzt"
                + (f", {missing} fehlen noch" if missing else "")
            )
        else:
            done = len(self.session.calibration.lanes)
            self.calibration_hint.setText(
                f"Bahn waehlen, dann 4 Ecken anklicken\n"
                f"({done} von {self.cfg.calibration.lane_count} Bahnen kalibriert)"
            )

    def _redraw_overlays(self) -> None:
        self.video_view.clear_overlays()
        cal_cfg = self.cfg.calibration

        for lane in self.session.calibration.lanes:
            # Dieselbe Beschriftung wie im Panel darunter
            label = (f"Bahn {lane.display_number}" if lane.display_number == lane.lane_id
                     else f"Bahn {lane.display_number} (Tafel {lane.lane_id})")
            self.video_view.set_lane_quad(
                lane.lane_id, [(p[0], p[1]) for p in lane.quad], label
            )

            try:
                transform = lane.transform(cal_cfg.warped_width, cal_cfg.warped_height)
            except GeometryError as exc:
                log.warning("Bahn %d: Transformation ungueltig: %s", lane.lane_id, exc)
                continue

            polygons: list[tuple[str, list[tuple[float, float]]]] = []
            for roi in lane.rois:
                if not roi.enabled:
                    continue
                x, y, w, h = roi.rect
                corners = np.array(
                    [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.float32
                )
                pts = transform.norm_to_frame(corners)
                polygons.append((roi.name, [(float(p[0]), float(p[1])) for p in pts]))
            self.video_view.set_lane_rois(lane.lane_id, polygons)

        self.video_view.set_pending_points(self.session.active_lane,
                                           self.session.pending_points)

    def _on_save_calibration(self) -> None:
        if not self.session.calibration.lanes:
            QMessageBox.information(self, "Nichts zu speichern",
                                    "Es wurde noch keine Bahn kalibriert.")
            return

        directory = self.cfg.resolve(self.cfg.calibration.directory)
        directory.mkdir(parents=True, exist_ok=True)
        default = self._calibration_path or (
            directory / f"kalibrierung_{datetime.now():%Y-%m-%d_%H%M}.json"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Kalibrierung speichern", str(default), "JSON (*.json)"
        )
        if not path:
            return

        self.session.calibration.name = Path(path).stem
        self.session.calibration.save(path)
        self._calibration_path = Path(path)
        self._refresh_calibration_list()
        self.statusBar().showMessage(f"Kalibrierung gespeichert: {Path(path).name}", 4000)

    def _on_load_calibration(self) -> None:
        path = self.calibration_combo.currentData()
        if not path:
            return
        try:
            self.session.calibration = Calibration.load(path)
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.critical(self, "Kalibrierung fehlerhaft", str(exc))
            return

        self._calibration_path = Path(path)
        self.session.cancel()
        self._refresh_active_lane_combo()

        info = self.player.info
        if info:
            for warning in self.session.calibration.check_against_video(
                info.width, info.height
            ):
                log.warning(warning)

        self._rebuild_lane_panels()
        self._redraw_overlays()
        self._update_calibration_hint()
        self.statusBar().showMessage(
            f"Kalibrierung geladen: {Path(path).name} "
            f"({len(self.session.calibration.lanes)} Bahnen)", 4000
        )

    # ------------------------------------------------------------------ Debug



    # --------------------------------------------------------- Live-Analyse

    def _on_toggle_analysis(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._stop_analysis()
        else:
            self._start_analysis()

    def _on_analysis_seeking(self, erreicht: int, ziel: int) -> None:
        """Zeigt das Vorspulen an.

        Ohne diese Rueckmeldung wirkt die Anwendung haengen: Bei einer Quelle,
        die nicht springen kann, dauert das Vorspulen auf eine spaete Stelle
        ueber eine Minute -- gemessen 77 Sekunden fuer Frame 11344.

        Beim SPRUNG gibt es keinen Zwischenstand: `seek` kehrt erst zurueck,
        wenn es fertig ist. Dann eine Prozentzahl zu zeigen waere gelogen --
        sie stand frueher die ganze Zeit auf 0 % und sah nach einem Absturz aus
        (gemeldet am 2026-09-07 an einem Stream ueber Netz).
        """
        if erreicht == SPRUNG_LAEUFT:
            text = f"springt zu Frame {ziel} ..."
        else:
            anteil = 100 * erreicht / max(1, ziel)
            text = f"spult vor ... {erreicht}/{ziel} ({anteil:.0f} %)"
        self.analysis_status.setText(text)
        self.statusBar().showMessage(
            f"Suche die Startposition -- {text}. Zum Abbrechen auf "
            f"'Analyse stoppen' klicken.")

    def _on_toggle_senden(self, aktiv: bool) -> None:
        """Schaltet den Versand um -- ohne die laufende Analyse zu stoeren."""
        if self._worker is not None:
            self._worker.set_sending(aktiv)
        self.statusBar().showMessage(
            "Versand an die Datenbank aktiv" if aktiv
            else "Versand pausiert -- es wird weiter ausgewertet und angezeigt",
            5000)

    def _start_analysis(self) -> None:
        if not self.player.is_loaded:
            QMessageBox.information(self, "Kein Video",
                                    "Bitte zuerst ein Video laden.")
            return

        calibration = self.session.calibration
        if not calibration.lanes:
            QMessageBox.information(
                self, "Keine Kalibrierung",
                "Bitte zuerst mindestens eine Bahn kalibrieren oder eine "
                "gespeicherte Kalibrierung laden."
            )
            return

        missing = [f"Bahn {l.lane_id}" for l in calibration.lanes
                   if l.get_roi("green_lamp") is None]
        if missing:
            QMessageBox.warning(
                self, "Gruene Lampe fehlt",
                "Ohne die gruene Lampe kann kein Wurf erkannt werden.\n\n"
                "Betroffen: " + ", ".join(missing)
            )
            return

        # WAS HIER PASSIEREN MUSS -- und warum nicht nur ein `pause()`:
        #
        # Der Worker liest seine EIGENE Videoquelle, und die Vorschau kommt ab
        # jetzt aus der Analyse (`_on_preview`). Die Frames des Players werden
        # waehrend der Analyse verworfen (`_on_frame` kehrt sofort zurueck).
        #
        # Bei einem Stream haelt `pause()` aber nur die ANZEIGE an -- der
        # Lesefaden holt absichtlich weiter Frames, damit die Verbindung nicht
        # weglaeuft. Bei einer Datei ist das harmlos. Bei einer Kamera nicht:
        # Dann laufen ZWEI volle Dekodierungen desselben Bildes, und beide
        # Verbindungen ringen um dieselbe Kamera.
        #
        # GEMESSEN 2026-09-08 an der Hallenkamera (2304x1296, h264): Ab dem
        # Moment, in dem die Analyse ihre Verbindung oeffnete, standen BEIDE
        # OpenCV-Faeden -- im Protokoll als `WARN:0` und `WARN:1`, beide alle
        # fuenf Sekunden mit "Stream timeout triggered". Die Analyse kam nicht
        # in Gang, die Vorschau blieb stehen.
        #
        # Deshalb wird die Verbindung des Players bei einem Stream GESCHLOSSEN,
        # nicht angehalten. Zu verlieren ist dabei nichts: An eine Stelle im
        # Livestream kann man ohnehin nicht zurueck. Nach der Analyse wird sie
        # in `_reset_analysis_button` wieder aufgebaut.
        video_path = self.player.source_id or ""
        war_live = self.player.is_live
        if war_live:
            log.info("Vorschauverbindung wird fuer die Dauer der Analyse "
                     "geschlossen -- zwei Verbindungen zur selben Kamera "
                     "blockieren sich gegenseitig.")
            self._vorschau_pfad = video_path
            self.player.close()
        else:
            self.player.pause()
        for panel in self.lane_panels.values():
            panel.clear_results()
        self._throw_count = 0

        # Ab der aktuellen Stelle, falls gewuenscht.
        #
        # BEI EINEM LIVESTREAM NICHT. Der Kommentar hier behauptete frueher,
        # das sei "wirkungslos" -- das war falsch, und es hat am 2026-09-08
        # einen Trainingsabend gekostet:
        #
        #     Sprung auf Frame 6081 nicht moeglich (Quelle steht bei 0)
        #     Kein Sprung moeglich -- es wird bis Frame 6081 vorgespult
        #
        # Der Zaehler des Players lief seit dem Laden mit. Bei 15 fps sind
        # 6081 Frames knapp sieben Minuten -- und in einem Livestream gibt es
        # diese Frames noch gar nicht. Der Worker haette sie in Echtzeit
        # abwarten muessen, waehrend im Saal gespielt wird.
        #
        # In einer Aufzeichnung ist das Vorspulen sinnvoll (Warmspielen
        # ueberspringen). In einer Live-Uebertragung ist "hier" immer jetzt.
        start_frame = 0
        if (self.chk_ab_hier.isChecked() and not war_live
                and self.player.current_frame is not None):
            start_frame = self.player.current_frame.index
        elif self.chk_ab_hier.isChecked() and war_live:
            log.info("Livestream: 'ab hier' wird uebergangen -- in einer "
                     "Live-Uebertragung ist der aktuelle Frame der Anfang.")

        self._worker = AnalysisWorker(video_path, calibration, self.cfg,
                                      start_frame=start_frame,
                                      sending_enabled=self.chk_senden.isChecked(),
                                      parent=self)
        self._worker.frame_processed.connect(self._on_frame_processed)
        self._worker.preview_ready.connect(self._on_preview)
        self._worker.progress.connect(self._on_analysis_progress)
        self._worker.seeking.connect(self._on_analysis_seeking)
        self._worker.finished_analysis.connect(self._on_analysis_finished)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.set_throttle_fps(self.speed_combo.currentData())
        self._worker.start()
        self._analyse_aktiv = True
        self._update_controls()

        self.btn_analyze.setText("Analyse stoppen")
        self.btn_analyze.setStyleSheet(
            "font-weight:bold; padding:6px; background:#8a2020; color:white;"
        )
        self.analysis_status.setText("laeuft...")
        log.info("Live-Analyse gestartet: %s", Path(video_path).name)

    def _stop_analysis(self) -> None:
        if self._worker is None:
            return
        self._worker.request_stop()
        # Begrenzt warten: Ein haengender Worker darf die Oberflaeche nicht
        # dauerhaft blockieren.
        if not self._worker.wait(3000):
            log.warning("Analyse-Thread reagiert nicht -- wird verworfen")
        self._reset_analysis_button()

    def _reset_analysis_button(self) -> None:
        # Hier endet die Analyse fuer die Oberflaeche -- ab jetzt darf die
        # Wiedergabe wieder ans Bild.
        self._analyse_aktiv = False
        self._vorschau_wieder_aufbauen()
        self._update_controls()

    def _vorschau_wieder_aufbauen(self) -> None:
        """Holt die Vorschau zurueck, die fuer die Analyse geschlossen wurde.

        Scheitert der Aufbau, bleibt die Oberflaeche ohne Bild -- aber sie
        bleibt bedienbar, und der Grund steht im Protokoll. Ein Fehler hier
        darf den gerade beendeten Lauf nicht nachtraeglich als Absturz
        erscheinen lassen.
        """
        if self._vorschau_pfad is None:
            return
        pfad, self._vorschau_pfad = self._vorschau_pfad, None
        log.info("Vorschauverbindung wird wieder aufgebaut: %s", pfad)
        if not self.player.load(pfad, self.cfg.video.playback_fps):
            log.warning("Vorschau konnte nicht wieder geoeffnet werden. "
                        "Die Quelle laesst sich ueber 'Laden' erneut oeffnen.")
        self.btn_analyze.setText("Analyse starten")
        self.btn_analyze.setStyleSheet(
            "font-weight:bold; padding:6px; background:#1e7d32; color:white;"
        )

    def _on_speed_changed(self, index: int) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.set_throttle_fps(self.speed_combo.itemData(index))

    def _on_check_calibration(self) -> None:
        """Prueft die Gruenlampen-ROIs und meldet Problembahnen konkret."""
        if not self.player.is_loaded or not self.session.calibration.lanes:
            QMessageBox.information(
                self, "Nicht moeglich",
                "Es muss ein Video geladen und mindestens eine Bahn kalibriert sein."
            )
            return

        self.player.pause()
        source = open_source(self.player.source_id or "", self.cfg)
        try:
            source.open()
            report = check_calibration(source, self.session.calibration, self.cfg)
        except VideoSourceError as exc:
            QMessageBox.critical(self, "Videofehler", str(exc))
            return
        finally:
            source.close()

        text = report.summary()
        self.analysis_status.setText(
            "Kalibrierung geprueft -- "
            + ("Probleme gefunden" if report.has_problems else "in Ordnung")
        )

        if report.has_problems:
            QMessageBox.warning(self, "Kalibrierung pruefen", text)
        else:
            QMessageBox.information(self, "Kalibrierung pruefen", text)

    def _panel_for_display_number(self, display_number: int):
        """Findet das Panel zu einer realen Bahnnummer.

        Die Wurfergebnisse tragen die REALE Bahnnummer (2-5), die Panels sind
        nach der Overlay-Position (1-4) abgelegt -- die Zuordnung darf nicht
        verwechselt werden.
        """
        for panel in self.lane_panels.values():
            if panel.display_number == display_number:
                return panel
        return None

    def _on_frame_processed(self, result: FrameResult) -> None:
        """Laeuft im GUI-Thread (Signal aus dem Worker)."""
        for observation in result.observations:
            panel = self.lane_panels.get(observation.lane_id)
            if panel is not None:
                panel.update_observation(observation)

        for event in result.events:
            if event.event in (EventType.GREEN_ON, EventType.GREEN_OFF,
                               EventType.THROW_CONFIRMED):
                log.info("%s", event.describe())

        # Erkannte Wuerfe in die Tabellen eintragen
        for throw in result.throws:
            panel = self._panel_for_display_number(throw.lane)
            if panel is None:
                # Darf nicht stillschweigend passieren: Der Wurf ist erkannt und
                # gebucht -- er wuerde sonst nur in der Oberflaeche fehlen, und
                # das saehe wie eine Erkennungsluecke aus.
                log.error("Bahn %d: kein Panel gefunden -- Wurf %d wird nicht "
                          "angezeigt. Panels: %s. Kalibrierung neu laden?",
                          throw.lane, throw.throw_number,
                          sorted(p.display_number for p in self.lane_panels.values()))
                self.statusBar().showMessage(
                    f"Wurf auf Bahn {throw.lane} erkannt, aber kein passendes "
                    f"Panel vorhanden", 8000)
            else:
                panel.add_throw(throw)
            self._throw_count += 1

        self._last_result = result

    def _on_preview(self, index: int, image) -> None:
        self.video_view.set_frame(image)
        info = self.player.info
        total = (info.frame_count or 0) if info else 0
        timestamp = index / info.fps if info and info.fps else 0.0
        self.position_label.setText(
            f"Frame {index} / {total}    t = {timestamp:6.2f} s"
        )
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(index)
        self._update_overlay_text()

    def _on_analysis_progress(self, current: int, total: int) -> None:
        percent = (current / total * 100.0) if total else 0.0
        fps_text = ""
        if self._last_result is not None and self._last_result.processing_ms > 0:
            fps_text = f" | {1000.0 / self._last_result.processing_ms:.0f} fps"
        self.analysis_status.setText(
            f"{percent:.0f} % ({current}/{total}){fps_text} | {self._throw_count} Wuerfe"
        )

    def _on_analysis_finished(self, summary: str) -> None:
        self._reset_analysis_button()
        self.analysis_status.setText(summary)
        self.statusBar().showMessage("Analyse abgeschlossen", 6000)
        log.info("Analyse abgeschlossen: %s", summary)

    def _on_analysis_error(self, message: str) -> None:
        self._reset_analysis_button()
        self.analysis_status.setText(f"Fehler: {message}")
        QMessageBox.critical(self, "Analysefehler", message)

    def _update_overlay_text(self) -> None:
        if not self.act_overlay.isChecked() or self._current_frame is None:
            self.video_view.set_status_text("")
            return
        frame = self._current_frame
        lanes = len(self.session.calibration.lanes)
        self.video_view.set_status_text(
            f"Frame {frame.index}   t={frame.timestamp:.2f}s\n"
            f"Bahnen kalibriert: {lanes}/{self.cfg.calibration.lane_count}"
        )

    def _update_controls(self) -> None:
        """Sperrt die Wiedergabe, solange die Analyse laeuft.

        WARUM: Waehrend der Analyse kommt das Bild aus dem Worker. Bleibt die
        Wiedergabe daneben bedienbar, malen ZWEI Quellen in dieselbe Anzeige --
        und weil beide an verschiedenen Stellen der Aufnahme stehen, springt
        das Bild zwischen ihnen hin und her.

        GEMESSEN am 2026-09-07 aus einer Bildschirmaufnahme des Nutzers: In der
        Statusleiste wechselten sich zwei Reihen ab, die BEIDE fortschritten --
        die Analyse (2880, 2895, 2900, ... 2949) und der Player rund 650 Frames
        dahinter (2230, 2234, 2282). Zugleich zeigte das Overlay durchgehend
        die Analyse. Ein Bild, zwei Schreiber.
        """
        laeuft = self._analyse_aktiv
        bedienbar = self.player.is_loaded and not laeuft
        for btn in (self.btn_play, self.btn_next, self.btn_prev):
            btn.setEnabled(bedienbar)
        # Der Schieber ist bei einem Stream ohnehin gesperrt -- deshalb wird
        # hier nicht blind wieder eingeschaltet, sondern nur, was vorher
        # erlaubt war.
        self.position_slider.setEnabled(self._slider_erlaubt and not laeuft)

    # -------------------------------------------------------------- Ereignisse

    def keyPressEvent(self, event) -> None:  # noqa: N802
        key = event.key()
        # Die Tastatur umgeht gesperrte Knoepfe. Ohne diese Abfrage liesse sich
        # die Wiedergabe mit der Leertaste mitten in der Analyse wieder
        # starten -- und genau das erzeugt die zwei Schreiber auf einem Bild.
        transport = (Qt.Key_Space, Qt.Key_Right, Qt.Key_Left)
        if key in transport and self._analyse_aktiv:
            self.statusBar().showMessage(
                "Die Wiedergabe ist waehrend der Analyse gesperrt -- das Bild "
                "kommt aus der Analyse.", 4000)
            return
        if key == Qt.Key_Space:
            self.player.toggle()
        elif key == Qt.Key_Right:
            self.player.step_forward()
        elif key == Qt.Key_Left:
            self.player.step_backward()
        elif key == Qt.Key_Escape:
            self._on_cancel_calibration()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        # Laufenden Analyse-Thread beenden, bevor das Fenster verschwindet --
        # sonst greift er auf geloeschte Widgets zu.
        if self._worker is not None and self._worker.isRunning():
            self._stop_analysis()
        # Datei-Handle freigeben -- unter Windows blockiert ein offenes
        # VideoCapture sonst das Verschieben oder Loeschen der Videodatei.
        self.player.close()
        log.info("Anwendung beendet")
        super().closeEvent(event)
