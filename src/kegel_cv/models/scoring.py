"""Zaehl- und Zykluslogik.

Reine Funktionen ohne Zustand -- vollstaendig testbar ohne Video, GUI oder OpenCV.

Die 15er-Zyklusrechnung ist die klassische Off-by-one-Falle dieses Projekts:
`throw_number % 15` liefert bei Wurf 15 den Wert 0 statt 15. Deshalb steht die
Rechnung genau einmal hier und wird nirgends dupliziert.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_THROWS_PER_CYCLE = 15


def throw_in_cycle(throw_number: int, throws_per_cycle: int = DEFAULT_THROWS_PER_CYCLE) -> int:
    """Wurfnummer innerhalb des Zyklus (1..throws_per_cycle).

    >>> throw_in_cycle(1), throw_in_cycle(15), throw_in_cycle(16)
    (1, 15, 1)
    """
    _validate(throw_number, throws_per_cycle)
    return (throw_number - 1) % throws_per_cycle + 1


def cycle_number(throw_number: int, throws_per_cycle: int = DEFAULT_THROWS_PER_CYCLE) -> int:
    """Nummer des Zyklus (1-basiert).

    >>> cycle_number(15), cycle_number(16), cycle_number(30)
    (1, 2, 2)
    """
    _validate(throw_number, throws_per_cycle)
    return (throw_number - 1) // throws_per_cycle + 1


def is_cycle_end(throw_number: int, throws_per_cycle: int = DEFAULT_THROWS_PER_CYCLE) -> bool:
    """Schliesst dieser Wurf einen Zyklus ab? Dann ist die Zwischensumme zu pruefen."""
    return throw_in_cycle(throw_number, throws_per_cycle) == throws_per_cycle


def _validate(throw_number: int, throws_per_cycle: int) -> None:
    if throw_number < 1:
        raise ValueError(f"Wurfnummer ist 1-basiert, erhalten: {throw_number}")
    if throws_per_cycle < 1:
        raise ValueError(f"throws_per_cycle muss >= 1 sein, erhalten: {throws_per_cycle}")


def pins_to_bitmap(pins: list[int] | tuple[int, ...]) -> int:
    """Kegelnummern -> 9-Bit-Bitmap. Bit k-1 gesetzt = Kegel k gefallen."""
    bitmap = 0
    for pin in pins:
        if not 1 <= pin <= 9:
            raise ValueError(f"Kegelnummer muss zwischen 1 und 9 liegen, erhalten: {pin}")
        bitmap |= 1 << (pin - 1)
    return bitmap


def bitmap_to_pins(bitmap: int) -> tuple[int, ...]:
    """9-Bit-Bitmap -> sortierte Kegelnummern."""
    if not 0 <= bitmap <= 0x1FF:
        raise ValueError(f"Bitmap muss zwischen 0 und 511 liegen, erhalten: {bitmap}")
    return tuple(pin for pin in range(1, 10) if bitmap & (1 << (pin - 1)))


@dataclass
class LaneScore:
    """Laufender Punktestand einer Bahn.

    Bewusst pro Bahn instanziiert (Prinzip P6): Ein gemeinsamer Zustand fuer alle
    vier Bahnen waere der schwerwiegendste denkbare Architekturfehler in diesem
    Projekt, da die Spieler nicht synchron werfen.
    """

    lane: int
    throws_per_cycle: int = DEFAULT_THROWS_PER_CYCLE
    running_total: int = 0
    last_throw_number: int = 0
    cycle_totals: list[int] = None  # type: ignore[assignment]
    # Endstaende abgeschlossener Spiele (je 30 Wuerfe) -- siehe start_new_game
    game_totals: list[int] = None  # type: ignore[assignment]
    _cycle_start_total: int = 0

    def __post_init__(self) -> None:
        if self.cycle_totals is None:
            self.cycle_totals = []
        if self.game_totals is None:
            self.game_totals = []

    def register(self, throw_number: int, pins_count: int) -> tuple[int, int | None]:
        """Bucht einen Wurf und liefert (laufende Gesamtsumme, Zyklussumme oder None).

        Die Zyklussumme ist nur am Ende eines Zyklus gesetzt.

        Raises:
            ValueError: Wurfnummer nicht groesser als die zuletzt gebuchte --
                das waere Double Counting und muss vom Aufrufer verhindert werden.
        """
        if throw_number <= self.last_throw_number:
            raise ValueError(
                f"Bahn {self.lane}: Wurfnummer {throw_number} ist nicht groesser als "
                f"die zuletzt gebuchte {self.last_throw_number} (Double Counting?)"
            )

        self.running_total += pins_count
        self.last_throw_number = throw_number

        series_total: int | None = None
        if is_cycle_end(throw_number, self.throws_per_cycle):
            series_total = self.running_total - self._cycle_start_total
            self.cycle_totals.append(series_total)
            self._cycle_start_total = self.running_total

        return self.running_total, series_total

    def start_new_game(self) -> int:
        """Schliesst das laufende Spiel ab und beginnt ein neues.

        GEMESSEN ueber 52 Minuten: Die Anlage setzt nach 30 Wuerfen Wurfnummer
        und Summe zurueck. Bis dahin lief die interne Summe einfach weiter und
        driftete von der Tafel ab -- ab Wurf 30 war die Gegenprobe wertlos:

            Wurf 28   Tafel 188   intern 180
            Wurf 29   Tafel   0   intern 189     <- Ruecksetzung
            Wurf 30   Tafel   7   intern 196

        Returns:
            Die Endsumme des abgeschlossenen Spiels -- das ist das
            Spielergebnis, das auf der Tafel stand, bevor sie zuruecksprang.
        """
        endstand = self.running_total
        self.game_totals.append(endstand)
        self.running_total = 0
        self.last_throw_number = 0
        self.cycle_totals = []
        self._cycle_start_total = 0
        return endstand

    def has_gap(self, throw_number: int) -> int:
        """Anzahl der zwischen letztem und diesem Wurf verpassten Wuerfe.

        0 = keine Luecke. Eine Luecke wird nie stillschweigend geschlossen,
        sondern sichtbar gemacht (siehe Skill `kegel-statemachine`).
        """
        if throw_number <= self.last_throw_number + 1:
            return 0
        return throw_number - self.last_throw_number - 1

    def expected_total(self, pins_count: int) -> int:
        """Erwartete Gesamtsumme nach diesem Wurf -- fuer die Plausibilitaetspruefung."""
        return self.running_total + pins_count
