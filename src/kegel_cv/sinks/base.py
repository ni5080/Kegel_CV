"""Abnehmer fuer Wurfergebnisse.

Die Analyse kennt nur diese Schnittstelle -- ob dahinter eine Datei, eine
Datenbank oder eine HTTP-Schnittstelle liegt, ist ihr gleichgueltig. Damit
laesst sich das Ziel austauschen, ohne die Erkennung anzufassen (Auftrag
Paragraph 26).

**Ein Abnehmer darf die Analyse niemals aufhalten oder abbrechen.** Ein
ausgefallenes Netz ist ein Problem des Versands, nicht der Auswertung -- die
Kegel sind gefallen, ob die Datenbank erreichbar ist oder nicht. Deshalb faengt
jede Implementierung ihre Fehler selbst ab und meldet sie ueber das Log.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.throw import ThrowResult


class ResultSink(ABC):
    """Nimmt fertige Wurfergebnisse entgegen."""

    @abstractmethod
    def send(self, throw: ThrowResult) -> None:
        """Uebergibt einen Wurf. Darf NICHT blockieren und NICHT werfen."""

    def flush(self) -> None:
        """Wartet, bis alles Uebergebene draussen ist. Standard: nichts zu tun."""

    def close(self) -> None:
        """Gibt Ressourcen frei. Standard: nichts zu tun."""

    def __enter__(self) -> ResultSink:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class NullSink(ResultSink):
    """Verwirft alles -- der Standard, solange kein Ziel eingerichtet ist."""

    def send(self, throw: ThrowResult) -> None:
        return None
