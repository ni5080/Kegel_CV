"""Umgang mit Quelladressen -- insbesondere mit den Zugangsdaten darin.

WARUM ES DIESE DATEI GIBT

Eine RTSP-Adresse traegt Benutzername und Passwort im Klartext:

    rtsp://admin:GEHEIM@10.0.0.8:554/h265Preview_02_main

Diese Adresse wanderte an drei Stellen weiter, an denen sie nichts zu suchen
hat (2026-09-09 beim Anlegen des Repositories aufgefallen):

* in den NAMEN der Debug-Ordner
      debug/admin_GEHEIM_10.0.0.8_554_h265Preview_02_main/
* in die KALIBRIERUNGSDATEI, als `source_hint.video` -- und die gehoert ins
  Repository, weil sie die Vermessung einer Bahn ist
* als `video_id` an die Datenbank

Ein Passwort in einer versionierten Datei ist auch nach dem Loeschen noch da:
Es steht in der Historie. Deshalb werden Zugangsdaten hier EINMAL entfernt,
und zwar an der Quelle statt bei jedem Aufrufer.

Das Paket `models` hat bewusst keine Abhaengigkeiten -- so duerfen sowohl
`video` als auch `calibration` diese Funktion benutzen.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

# Adressen ohne diese Trennung sind Dateipfade, keine URLs -- ein Windows-Pfad
# wie C:\Videos\a.mp4 darf nicht als URL zerlegt werden.
_SCHEMA_TRENNER = "://"


def ohne_zugangsdaten(quelle: str | None) -> str | None:
    """Entfernt Benutzername und Passwort aus einer Adresse.

    Alles andere bleibt unveraendert: Schema, Rechner, Port, Pfad und
    Abfrage. Der Rechnername ist kein Geheimnis, und ohne ihn liesse sich
    nicht mehr erkennen, von welcher Kamera eine Kalibrierung stammt.

        rtsp://admin:geheim@10.0.0.8:554/haupt  ->  rtsp://10.0.0.8:554/haupt

    Dateipfade und leere Werte gehen unveraendert durch.
    """
    if not quelle or _SCHEMA_TRENNER not in quelle:
        return quelle

    teile = urlsplit(quelle)
    if not teile.hostname:
        # Etwas URL-Aehnliches ohne Rechnernamen -- lieber unveraendert lassen
        # als daran herumzuschneiden.
        return quelle

    ort = teile.hostname
    if teile.port:
        ort = f"{ort}:{teile.port}"
    return urlunsplit((teile.scheme, ort, teile.path, teile.query,
                       teile.fragment))
