"""Datenmodell fuer Wurfergebnisse.

Kernprinzip (P1): Jedes Ergebnis traegt seine Herkunft mit sich. Ein ThrowResult
ohne `evidence` ist unvollstaendig -- die Frage "Warum wurde Wurf 17 so erkannt?"
muss allein aus diesem Objekt beantwortbar sein.

Dieses Modul enthaelt nur Daten und reine Funktionen: kein I/O, kein OpenCV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThrowStatus(str, Enum):
    """Status eines erkannten Wurfs.

    Die Unterscheidung ist bewusst feiner als ein blosses `valid`-Flag
    (Auftrag Paragraph 10), damit spaeter nachvollziehbar bleibt, was tatsaechlich
    erkannt wurde.
    """

    UNKNOWN = "UNKNOWN"   # noch nicht ausgewertet oder Wurf uebersprungen (Luecke)
    VALID = "VALID"       # gueltiger Wurf mit mindestens einem gefallenen Kegel
    EMPTY = "EMPTY"       # gueltiger Wurf mit 0 Kegeln ("Pumpe") -- KEIN Fehler
    INVALID = "INVALID"   # ungueltiger Wurf (Fehlwurf/Faul)
    ERROR = "ERROR"       # Auswertung nicht moeglich, Quellen widerspruechlich

    @property
    def is_valid_throw(self) -> bool:
        """Zaehlt dieser Wurf als regulaer gewertet?

        VALID und EMPTY sind beide regulaere Wuerfe -- ein Wurf mit 0 Kegeln ist
        fachlich korrekt und zaehlt in der Wurfnummer mit. Nur INVALID und ERROR
        sind keine gewerteten Wuerfe.
        """
        return self in (ThrowStatus.VALID, ThrowStatus.EMPTY)


class FrameRole(str, Enum):
    """Rolle eines Frames innerhalb eines Ereignisses -- fuer Debug-Nachvollzug."""

    GREEN_OFF = "GREEN_OFF"     # Ausloeser
    SAMPLE = "SAMPLE"           # regulaer gesampelter Frame
    GREEN_ON = "GREEN_ON"       # Freigabe des naechsten Wurfs
    CONTEXT = "CONTEXT"         # zusaetzlicher Kontext-Frame


@dataclass(frozen=True)
class FrameRef:
    """Verweis auf einen ausgewerteten Frame."""

    index: int
    timestamp: float
    role: FrameRole = FrameRole.SAMPLE

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.index, "timestamp": round(self.timestamp, 3),
                "role": self.role.value}


@dataclass(frozen=True)
class PlausibilityCheck:
    """Eine einzelne Plausibilitaetspruefung mit ihrem Ausgang."""

    name: str
    expected: Any
    actual: Any
    passed: bool
    # Sagt diese Pruefung etwas ueber das WURFERGEBNIS aus (Anzahl gefallener
    # Kegel)? Pruefungen rund um die Wurfnummer tun das nicht -- sie betreffen
    # die Buchfuehrung. Eine falsch gelesene Wurfnummer darf ein sauber
    # gemessenes Ergebnis nicht entwerten.
    affects_result: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "expected": self.expected,
                "actual": self.actual, "passed": self.passed,
                "affects_result": self.affects_result}

    def describe(self) -> str:
        mark = "OK" if self.passed else "ABWEICHUNG"
        return f"{self.name}: erwartet={self.expected} erhalten={self.actual} -> {mark}"


@dataclass(frozen=True)
class Evidence:
    """Beweiskette eines Wurfergebnisses.

    Enthaelt alle Einzelmessungen und Entscheidungen, die zum Ergebnis gefuehrt
    haben. Ohne diese Angaben laesst sich ein Ergebnis nicht pruefen -- und
    Nachvollziehbarkeit ist in diesem Projekt Kernanforderung, nicht Beiwerk.
    """

    frames: tuple[FrameRef, ...] = ()
    green_scores: tuple[float, ...] = ()
    checks: tuple[PlausibilityCheck, ...] = ()
    decisions: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "frames": [f.to_dict() for f in self.frames],
            "green_scores": [round(s, 2) for s in self.green_scores],
            "checks": [c.to_dict() for c in self.checks],
            "decisions": list(self.decisions),
            "raw": self.raw,
        }

    def explain(self) -> str:
        """Menschenlesbare Begruendung -- das Format aus Auftrag Paragraph 27."""
        lines: list[str] = []
        if self.frames:
            lines.append(
                "Frames: " + ", ".join(f"{f.index} (t={f.timestamp:.2f}s, {f.role.value})"
                                       for f in self.frames)
            )
        lines.extend(f"-> {d}" for d in self.decisions)
        lines.extend(f"-> {c.describe()}" for c in self.checks)
        return "\n".join(lines)


@dataclass(frozen=True)
class ThrowResult:
    """Ergebnis eines einzelnen Wurfs.

    Unveraenderlich: Ein Wurf wird nicht nachtraeglich mutiert. Bei einer Korrektur
    entsteht ein neues Objekt (siehe `corrected`).
    """

    lane: int
    throw_number: int                 # 1-basiert, laufend ueber das ganze Spiel
    throw_number_in_series: int       # 1..throws_per_cycle
    pins: tuple[int, ...]             # gefallene Kegelnummern, sortiert
    pins_count: int                   # Anzahl gefallener Kegel (aus Lampen)
    displayed_pin_count: int | None   # Ziffer der Anzeigetafel (zweite Quelle)
    status: ThrowStatus
    running_total: int
    # WEITERE ABLESUNGEN DER TAFEL, alle nullbar und alle NUR BELEG.
    #
    # Sie gehen in keine Zaehlung ein -- das ist keine Vorsicht, sondern eine
    # Lehre: Die Wurfnummer aus der Anzeige hat einmal 28 % der Wuerfe
    # geloescht (BUG-008). Gezaehlt wird aus den Lampen; diese Werte sagen nur,
    # was auf der Tafel stand, als der Wurf gebucht wurde.
    #
    # `None` heisst "nicht sicher gelesen" und ist ein gueltiger Zustand --
    # eine verdeckte oder flackernde Anzeige liefert keinen Wert, und das darf
    # den Wurf nicht aufhalten (P8).
    displayed_throw_number: int | None = None   # Wurfnummer laut Tafel, roh
    displayed_foul_count: int | None = None     # Fehlwurfzaehler (left_display)
    displayed_total: int | None = None          # Summenfeld B
    series_total: int | None = None   # nur am Ende eines 15er-Zyklus gesetzt
    cycle_number: int = 1
    # Laufende Spielnummer der Bahn. Ein Spiel umfasst 30 Wuerfe; danach setzt
    # die Anlage zurueck (gemessen, siehe docs/VIDEO_ANALYSIS.md). Ohne diese
    # Nummer waeren die vier Spiele einer Bahn in einer Tabelle nicht
    # auseinanderzuhalten.
    game_number: int = 1
    # WIE VIELE KEGELLAMPEN WAREN UNKLAR -- im Ergebnis und in der Ausgangslage.
    #
    # WOFUER (BUG-027, 2026-09-16): Eine Lampe im Zustand UNKNOWN faellt still
    # aus der Kegelliste und wirkt damit wie "steht". Beim Abraeumen ist das
    # Ergebnis die DIFFERENZ zweier Messungen -- ein unklarer Kegel in der
    # AUSGANGSLAGE schlaegt direkt auf den Punktestand durch, und zwar ohne
    # dass am Ergebnis etwas verdaechtig aussieht. Genau so entstand ein Wurf
    # mit 5 statt 4 Kegeln.
    #
    # Die Zahl stand bisher nur tief in `evidence.raw`. Hier steht sie, damit
    # eine Auswertung ueber viele Wuerfe sie ohne Umweg zaehlen kann.
    lamps_unknown: int = 0
    baseline_unknown: int | None = None      # None = keine Ausgangslage noetig
    confidence: float = 0.0
    timestamp: float = 0.0
    source_frame: int | None = None   # Ausloeser-Frame
    # Die Anzeigetafel im Moment des Ergebnisses, als Base64-JPEG.
    # Bewusst ein eigenes Feld und nicht in `evidence.raw`: Das Bild ist
    # gross, und `evidence` landet vollstaendig in den Debug-Protokollen.
    board_image: str | None = None
    # Die Tafel VOR dem Wurf -- das Bild, in das geworfen wurde. Beim
    # Abraeumen die entscheidende Angabe; aus den gefallenen Kegeln
    # allein laesst sie sich nicht rekonstruieren.
    board_image_before: str | None = None
    evidence: Evidence = field(default_factory=Evidence)

    @property
    def valid(self) -> bool:
        """Kompatibles Flag entsprechend Auftrag Paragraph 10."""
        return self.status.is_valid_throw

    @property
    def pins_bitmap(self) -> int:
        """9-Bit-Darstellung der gefallenen Kegel: Bit k-1 gesetzt = Kegel k gefallen."""
        bitmap = 0
        for pin in self.pins:
            bitmap |= 1 << (pin - 1)
        return bitmap

    @property
    def sources_agree(self) -> bool:
        """Stimmen Lampenzaehlung und angezeigte Ziffer ueberein?

        Ist keine Ziffer vorhanden, gilt das nicht als Widerspruch -- eine fehlende
        zweite Quelle ist etwas anderes als eine widersprechende.
        """
        if self.displayed_pin_count is None:
            return True
        return self.pins_count == self.displayed_pin_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "throw_number": self.throw_number,
            "throw_number_in_series": self.throw_number_in_series,
            "cycle_number": self.cycle_number,
            "game_number": self.game_number,
            "pins": list(self.pins),
            "pins_count": self.pins_count,
            "pins_bitmap": self.pins_bitmap,
            "displayed_pin_count": self.displayed_pin_count,
            "valid": self.valid,
            "status": self.status.value,
            "running_total": self.running_total,
            "series_total": self.series_total,
            "confidence": round(self.confidence, 3),
            "timestamp": round(self.timestamp, 3),
            "source_frame": self.source_frame,
            # Das Bild absichtlich NICHT: Es blaeht jedes Debug-JSON um
            # Kilobytes Base64 auf und ist dort nicht lesbar. Nur ein
            # Vermerk, dass es eines gibt.
            "has_board_image": self.board_image is not None,
            "has_board_image_before": self.board_image_before is not None,
            "evidence": self.evidence.to_dict(),
        }

    def explain(self) -> str:
        """Vollstaendige Begruendung im Format aus Auftrag Paragraph 27."""
        header = (
            f"Warum wurde Wurf {self.throw_number} (Bahn {self.lane}) so erkannt?\n"
            f"-> Zeitpunkt t={self.timestamp:.2f}s"
        )
        body = self.evidence.explain()
        footer = (
            f"=> {self.status.value}, {self.pins_count} Kegel {list(self.pins)}, "
            f"Gesamt {self.running_total}, Confidence {self.confidence:.2f}"
        )
        return "\n".join(part for part in (header, body, footer) if part)
