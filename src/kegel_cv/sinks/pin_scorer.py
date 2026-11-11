"""Wurf-Events fuer den pin-scorer -- die Bruecke zum Ende des Eintippens.

Der pin-scorer (Unterprojekt `apps/pin-scorer`) erfasst Spiele bisher von
Hand. Sein Plan `docs/wurferkennung-plan.md` legt fest, was eine Erkennung
liefern soll: EIN Event je Wurf und Bahn, mit dem STEHENDEN Kegelbild vor und
nach dem Wurf. Spieler, Satz und Teilsatz leitet der pin-scorer selbst ab --
das passt zur Haltung dieses Projekts, nur Gemessenes zu senden (siehe
`payload.py`).

Das Event, Kontraktfelder zuerst:

    eventId    eindeutig je Event (Doppelschutz)
    anlage     wie im pin-scorer eingetragen
    bahn       Bahnnummer laut Tafel
    seq        laufend je Aufzeichnungsdatei, ueber Neustarts hinweg
    ts         Erzeugungszeitpunkt, UTC
    art        immer "wurf" -- ein Aufstell-Event erkennen wir (noch) nicht
    bildVor    stehende Kegel vor dem Wurf, oder null
    bildNach   stehende Kegel nach dem Wurf, oder null
    konfidenz  Confidence der Auswertung

Erweiterungen, die der Kontrakt nicht kennt -- er muss sie dulden:

    gefallen   die in DIESEM Wurf gefallenen Kegel. Die gemessene Wahrheit
               dieses Projekts, auch wenn die Bilder null sind.
    status     VALID, EMPTY, INVALID, ERROR
    quelle     welcher Sensor geliefert hat (wie `video_id`)
    videoZeit  Zeitpunkt im Video, Sekunden

`null` bei den Bildern heisst "nicht sicher bekannt" -- ein unklares Bild wird
nicht als gutes weitergegeben. Der pin-scorer kann dann keine Drift pruefen und
muss sich auf `gefallen` stuetzen.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models.throw import ThrowResult
from .base import ResultSink

log = logging.getLogger(__name__)

# Kegelnummern 1..9 (DKB-Standard). Dieselbe Zaehlung wie `KEGEL_LAYOUT` im
# pin-scorer -- verglichen am 2026-11-11, siehe kegel-domain Abschnitt 4.
_ALLE_KEGEL = tuple(range(1, 10))


def stehende_kegel(throw: ThrowResult) -> tuple[list[int] | None,
                                                  list[int] | None]:
    """(bildVor, bildNach) als Listen STEHENDER Kegel -- oder beide None.

    Die Tafel zeigt GEFALLENE Kegel; der Kontrakt will STEHENDE. Ohne sicher
    gelesene Ausgangslage ist keines der beiden Bilder bekannt.
    """
    if throw.pins_down_before is None:
        return None, None
    lagen = set(throw.pins_down_before)
    vor = [p for p in _ALLE_KEGEL if p not in lagen]
    gefallen = set(throw.pins)
    nach = [p for p in vor if p not in gefallen]
    return vor, nach


def throw_to_event(throw: ThrowResult, seq: int, anlage: str = "",
                   quelle: str = "", event_id: str | None = None,
                   now: datetime | None = None) -> dict[str, Any]:
    """Baut das Event eines Wurfs. Rein: kein I/O, alles Variable von aussen."""
    vor, nach = stehende_kegel(throw)
    zeit = now or datetime.now(timezone.utc)
    return {
        "eventId": event_id or str(uuid.uuid4()),
        "anlage": anlage,
        "bahn": throw.lane,
        "seq": seq,
        "ts": zeit.isoformat().replace("+00:00", "Z"),
        "art": "wurf",
        "bildVor": vor,
        "bildNach": nach,
        "konfidenz": round(throw.confidence, 3),
        "gefallen": list(throw.pins),
        "status": throw.status.value,
        "quelle": quelle,
        "videoZeit": round(throw.timestamp, 2),
    }


def letzte_seq(pfad: Path) -> int:
    """Hoechste `seq` einer bestehenden Aufzeichnung, 0 wenn es keine gibt.

    Eine unlesbare Zeile wird uebersprungen und gemeldet, nicht geraten: Sie
    kann ein abgebrochener Schreibvorgang sein, und der Rest der Datei bleibt
    trotzdem gueltig.
    """
    if not pfad.exists():
        return 0
    hoechste = 0
    with pfad.open(encoding="utf-8") as datei:
        for nummer, zeile in enumerate(datei, start=1):
            if not zeile.strip():
                continue
            try:
                hoechste = max(hoechste, int(json.loads(zeile)["seq"]))
            except (ValueError, KeyError, TypeError) as exc:
                log.warning("pin-scorer-Aufzeichnung %s, Zeile %d unlesbar "
                            "(%s) -- uebersprungen", pfad, nummer, exc)
    return hoechste


class PinScorerEventSink(ResultSink):
    """Haengt je Wurf ein Event an eine JSONL-Datei an.

    Eine lokale Datei statt eines Netzwegs: Ein Anhaengen dauert Mikrosekunden
    und blockiert die Analyse nicht. Die Datei ist zugleich die Aufzeichnung,
    gegen die der pin-scorer seine Zuordnung testen kann.

    `seq` setzt eine bestehende Datei fort. Sonst begaenne ein zweiter Lauf
    in dieselbe Datei wieder bei 1, und "alles ab seq N" waere mehrdeutig.
    """

    def __init__(self, pfad: Path, anlage: str = "", quelle: str = "") -> None:
        self.pfad = pfad
        self.anlage = anlage
        self.quelle = quelle
        self._seq = letzte_seq(pfad)
        self._fehler = 0

    def send(self, throw: ThrowResult) -> None:
        event = throw_to_event(throw, self._seq + 1, self.anlage, self.quelle)
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            with self.pfad.open("a", encoding="utf-8") as datei:
                datei.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError as exc:
            # P8: Die Analyse laeuft weiter. Die seq wird NICHT verbraucht --
            # eine Luecke hiesse fuer den pin-scorer "Wurf verpasst".
            self._fehler += 1
            log.error("pin-scorer-Event fuer Bahn %d nicht geschrieben: %s",
                      throw.lane, exc)
            return
        self._seq += 1

    def close(self) -> None:
        if self._fehler:
            log.warning("pin-scorer: %d Events konnten nicht geschrieben "
                        "werden (%s)", self._fehler, self.pfad)
