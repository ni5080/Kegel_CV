"""Uebersetzt ein Wurfergebnis in eine flache Zeile fuer die Datenbank.

Bewusst FLACH und ohne verschachtelte Strukturen: Die Zeile soll sich in einer
Tabelle ansehen und filtern lassen, ohne dass die lesende Anwendung JSON
auspacken muss. Der Spielleiter vor Ort schaut auf eine Tabelle, nicht auf ein
Dokument.

Die vollstaendige Beweiskette bleibt als `evidence` erhalten -- sie wird
gebraucht, wenn ein Ergebnis angezweifelt wird, steht aber nicht im Weg.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models.throw import ThrowResult


def throw_to_row(throw: ThrowResult, video_id: str = "",
                 mit_bild: bool = True,
                 mit_vorher: bool = False) -> dict[str, Any]:
    """Baut die Datenbankzeile eines Wurfs -- bewusst KNAPP.

    Uebertragen wird nur, was GEMESSEN ist:

        Bahn | Anzahl Kegel | Kegelnummern | Zeitstempel

    Alles andere -- laufende Summe, Zyklus, Spielnummer, Wurfnummer,
    Zwischensummen -- wird zwar weiterhin berechnet und in der Oberflaeche
    angezeigt, aber NICHT gesendet. Der Grund ist die Erfahrung aus diesem
    Projekt: Genau diese abgeleiteten Groessen sind schiefgegangen.

    - Die Wurfnummer aus der Anzeige loeschte 28 % der Wuerfe (BUG-008)
    - Die Spielerkennung nach 30 Wuerfen traf den Bahnwechsel nicht
    - Die laufende Summe driftete von der Tafel ab, sobald ein Wurf fehlte

    Diese Groessen setzen Regelwissen voraus, das die auswertende Anwendung
    besser kennt als die Bilderkennung: wann ein Bahnwechsel ansteht, wann ein
    Spiel endet, wie gewertet wird. Was hier gemessen wird, ist allein: Auf
    dieser Bahn sind zu diesem Zeitpunkt diese Kegel gefallen.

    Vom Nutzer so festgelegt (2026-08-26).
    """
    row = {
        "video_id": video_id,
        "lane": throw.lane,
        "pins_count": throw.pins_count,
        "pins": list(throw.pins),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        # Zeitpunkt IM VIDEO -- ordnet die Wuerfe auch dann richtig, wenn
        # nachtraeglich eine Aufzeichnung ausgewertet wird.
        "video_time_s": round(throw.timestamp, 2),
    }
    # Der Beleg zum Ergebnis: die eingemessene Anzeigetafel als Base64-JPEG.
    # Nur wenn es eines gibt -- ein fehlendes Bild darf den Wurf nicht
    # aufhalten (P8). Der Ticker holt die Spalte nur fuer den Wurf, den
    # jemand anklickt; die Liveliste laedt sie nicht mit.
    if mit_bild and throw.board_image:
        row["board_jpeg"] = throw.board_image
    if mit_bild and mit_vorher and throw.board_image_before:
        row["board_before_jpeg"] = throw.board_image_before
    return row
