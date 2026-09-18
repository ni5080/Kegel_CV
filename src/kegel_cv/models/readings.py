"""Messwerte der Detektoren.

Bewusst als eigene Datentypen statt nackter bool/int: Jede Messung traegt ihren
Rohwert und ihre Confidence mit sich. Ohne diese Angaben liesse sich spaeter
nicht mehr nachvollziehen, warum ein Wurf so erkannt wurde -- und genau das ist
Kernanforderung dieses Projekts.

`@dataclass(frozen=True)` statt Pydantic: Diese Objekte entstehen im Hot Path
(bis zu 4 Bahnen x 25 fps), dort waere Pydantic-Validierung zu teuer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class LampState(str, Enum):
    """Zustand einer Lampe."""

    ON = "ON"
    OFF = "OFF"
    UNKNOWN = "UNKNOWN"     # ROI unbrauchbar (ausserhalb des Bildes, leer)

    @property
    def is_known(self) -> bool:
        return self is not LampState.UNKNOWN


@dataclass(frozen=True)
class LampReading:
    """Eine einzelne Lampenmessung."""

    state: LampState
    score: float                  # Rohwert des Detektors
    confidence: float             # 0..1, aus dem Abstand zur Schwelle abgeleitet
    name: str = ""

    @property
    def is_on(self) -> bool:
        return self.state is LampState.ON

    @classmethod
    def unknown(cls, name: str = "", reason: str = "") -> LampReading:
        return cls(state=LampState.UNKNOWN, score=0.0, confidence=0.0, name=name)

    def als_aus(self) -> LampReading:
        """Dieselbe Messung, aber als AUS gewertet.

        Gebraucht, wenn eine zweite Quelle der ersten widerspricht: Der
        Rohwert bleibt erhalten -- er ist ja gemessen worden --, nur die
        Deutung aendert sich. So steht im Beweis noch, was der Detektor sah.
        """
        if self.state is LampState.OFF:
            return self
        return LampReading(state=LampState.OFF, score=self.score,
                           confidence=self.confidence, name=self.name)

    def to_dict(self) -> dict:
        return {"name": self.name, "state": self.state.value,
                "score": round(self.score, 2), "confidence": round(self.confidence, 3)}


@dataclass(frozen=True)
class PinLampReading:
    """Auswertung aller neun Kegellampen einer Bahn."""

    lamps: tuple[LampReading, ...]
    pins: tuple[int, ...]         # Nummern der gefallenen Kegel
    confidence: float

    @property
    def count(self) -> int:
        """Anzahl gefallener Kegel."""
        return len(self.pins)

    @property
    def is_complete(self) -> bool:
        """Konnten alle Lampen gelesen werden?

        Eine unlesbare Lampe macht die Zaehlung unbrauchbar -- sie darf nicht
        stillschweigend als 'aus' gelten.
        """
        return all(lamp.state.is_known for lamp in self.lamps)

    @property
    def bitmap(self) -> int:
        bitmap = 0
        for pin in self.pins:
            bitmap |= 1 << (pin - 1)
        return bitmap

    def to_dict(self) -> dict:
        return {"pins": list(self.pins), "count": self.count,
                "bitmap": self.bitmap, "complete": self.is_complete,
                "confidence": round(self.confidence, 3),
                "lamps": [lamp.to_dict() for lamp in self.lamps]}


def confidence_from_threshold(score: float, on_threshold: float,
                              off_threshold: float, span: float) -> float:
    """Confidence aus dem Abstand zur naechstgelegenen Schwelle.

    Ein Wert weit ausserhalb der Hysteresezone ist eindeutig, einer mittendrin
    unsicher. `span` normiert den Abstand auf 0..1.

    Eine feste Confidence im Code (etwa 0.9) waere eine Erfindung -- sie taeuscht
    Wissen vor, das nicht existiert.
    """
    if span <= 0:
        return 0.0
    if score >= on_threshold:
        distance = score - on_threshold
    elif score <= off_threshold:
        distance = off_threshold - score
    else:
        # In der Hysteresezone: unsicher, aber nicht wertlos
        return 0.25
    return float(min(1.0, 0.5 + 0.5 * min(1.0, distance / span)))


def baseline_aus_zwei(vorher: "PinLampReading | None",
                      nachher: "PinLampReading | None") -> "PinLampReading | None":
    """Grundlinie aus dem Stand vor und nach dem Gruen-AN -- die Schnittmenge.

    Beide Einzelmessungen koennen zu HOCH liegen, nie zu niedrig:

    * `nachher` faengt Kegel mit ein, die waehrend des Messfensters gefallen
      sind -- dann gehoeren sie zum Wurf, nicht zur Grundlinie (BUG-016).
    * `vorher` zeigt den alten Stand, wenn die Anlage erst spaet geloescht hat.

    Ein Kegel gehoert also nur dann zur Grundlinie, wenn er in BEIDEN
    Messungen lag. Fehlt eine von beiden, gilt die andere -- am Anfang eines
    Laufs gibt es noch keine Pause, aus der `vorher` stammen koennte.
    """
    if vorher is None:
        return nachher
    if nachher is None:
        return vorher

    lagen_vorher = {lamp.name for lamp in vorher.lamps if lamp.is_on}
    lampen = tuple(
        lamp if lamp.name in lagen_vorher else lamp.als_aus()
        for lamp in nachher.lamps
    )
    pins = tuple(sorted(
        int(lamp.name.removeprefix("pin_lamp_"))
        for lamp in lampen
        if lamp.is_on and lamp.name.startswith("pin_lamp_")
    ))
    return PinLampReading(lamps=lampen, pins=pins,
                          confidence=min(vorher.confidence, nachher.confidence))


def aggregate_pin_readings(
    messungen: "list[PinLampReading]") -> "PinLampReading | None":
    """Fasst mehrere Lampenmessungen desselben Zustands zusammen.

    Eine Lampe gilt als AN, wenn sie in **mindestens einer** Messung geleuchtet
    hat. Diese Asymmetrie ist gemessen begruendet: Die Kegellampen der Anlage
    BLINKEN (siehe BUG-007). Eine Lampe kann waehrend einer Dunkelphase
    faelschlich als aus erscheinen -- aber nie faelschlich leuchten. Also ist
    das Maximum die richtige Zusammenfassung, nicht Mittelwert oder Mehrheit.
    """
    if not messungen:
        return None

    anzahl = max(len(m.lamps) for m in messungen)
    zusammen: list[LampReading] = []
    for i in range(anzahl):
        kandidaten = [m.lamps[i] for m in messungen if i < len(m.lamps)]
        if not kandidaten:
            continue
        an = [k for k in kandidaten if k.is_on]
        if an:
            zusammen.append(max(an, key=lambda k: k.confidence))
        else:
            bekannt = [k for k in kandidaten if k.state.is_known]
            zusammen.append(max(bekannt, key=lambda k: k.confidence)
                            if bekannt else kandidaten[0])

    # Der NAME traegt die Kegelnummer, nicht den Lampenindex: `detect()` setzt
    # ihn als f"pin_lamp_{pin}" aus den Kegelnummern der Kalibrierung. Die
    # Kopplung ist implizit -- wer den Namen dort aendert, aendert hier die
    # Kegelnummern mit.
    pins = tuple(sorted(
        int(lamp.name.removeprefix("pin_lamp_"))
        for lamp in zusammen
        if lamp.is_on and lamp.name.startswith("pin_lamp_")
    ))
    confidence = min((lamp.confidence for lamp in zusammen), default=0.0)
    return PinLampReading(lamps=tuple(zusammen), pins=pins, confidence=confidence)


def grundlinie_aus_spur(messungen: Sequence["PinLampReading"],
                        wie_oft: int) -> "PinLampReading | None":
    """Grundlinie aus den laufenden Lampenmessungen seit dem vorigen Wurf.

    WARUM ES DIESEN ZWEITEN WEG GIBT (BUG-031). `baseline_aus_zwei` misst in
    einem einzigen Fenster von 25 Frames nach dem ERKANNTEN Gruen-AN. Trifft
    dieses Fenster den falschen Augenblick, ist die Grundlinie falsch, und die
    gebuchte Kegelzahl mit ihr -- dauerhaft, denn sie verschwindet in einer
    Subtraktion. Gemessen an einem Spieltag geschah das dreimal: einmal war das
    Fenster kuerzer als die Gruenphase, einmal lag es 87 Sekunden vor dem Wurf,
    einmal war die Bahn waehrenddessen verdeckt.

    Die Antwort stand jedes Mal in Messungen, die ohnehin anfallen: Fuer die
    Anzeige werden alle paar Frames die Kegellampen gelesen. Beim RAEUMEN
    bleiben die alten Lampen an -- der kleinste Stand seit dem vorigen Wurf IST
    die Grundlinie. Nach dem Neuaufstellen faellt er auf null, und genau das
    ist dann auch die Grundlinie.

    `wie_oft` verlangt, dass derselbe Stand mehrfach hintereinander gemessen
    wurde. Ohne diese Bedingung bestimmt eine einzelne Lampe in der Dunkelphase
    des Blinkens die Grundlinie -- die Blinkperiode betraegt 28-30 Frames, die
    Dunkelphase bis zu 15 (BUG-007a).

    GEMESSEN gegen die Kegelziffer der Tafel, Grundlinie als ANZAHL:

        Lauf 2026-09-17 12:53, 874 Wuerfe    Fenster 99,54 %  Spur 99,77 %
        Lauf 2026-09-18 07:30, 421 Wuerfe    Fenster 99,51 %  Spur 100,00 %

    Beide Faelle von BUG-031 verschwinden damit, ohne dass ein neuer entsteht.
    Ob sich die MENGEN ebenso verhalten wie die Anzahlen, liess sich aus den
    Spurdateien nicht nachrechnen -- das entscheidet der Lauf.

    Gibt `None`, wenn kein Stand oft genug bestaetigt wurde. Dann gilt der
    Fensterwert; eine Grundlinie zu raten waere schlimmer als der alte Weg.
    """
    beste: "PinLampReading | None" = None
    lauf = 0
    vorher: frozenset[int] | None = None
    for messung in messungen:
        jetzt = frozenset(messung.pins)
        lauf = lauf + 1 if jetzt == vorher else 1
        vorher = jetzt
        if lauf >= wie_oft and (beste is None or len(jetzt) < len(beste.pins)):
            beste = messung
    return beste
