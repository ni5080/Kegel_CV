"""Was die Kamera liefert, und was der Erkennungskern damit anfaengt.

Diese Datei ist die Naht zwischen Android und dem Projekt. Sie nimmt Bilder
entgegen, wandelt sie in das Format, das der Kern erwartet, und beantwortet
die eine Frage, an der die ganze Anwendung haengt:

    Findet die automatische Tafelsuche eine FUNK-Anzeigetafel auch im Bild
    eines Handys -- und nicht nur in dem einer fest montierten Hallenkamera?

WARUM RGBA UND NICHT YUV. CameraX liefert von Haus aus YUV_420_888: drei
Ebenen, zwei davon halb aufgeloest, mit Zeilen- und Pixelabstaenden, die sich
von Geraet zu Geraet unterscheiden. Jede Umwandlung davon ist eine Quelle
stiller Farbfehler. RGBA_8888 kostet Android etwas mehr, kommt aber als EINE
Ebene, und daraus wird ein BGR-Bild ohne Rechnerei.

WAS HIER NICHT PASSIERT. Kein Zwischenspeichern ganzer Bildfolgen, keine
Analyse im Hintergrund. Ein Bild wird gehalten -- das zuletzt gesehene --,
und darauf laeuft, was die Oberflaeche anfordert. Alles andere waere
Rechenzeit auf Verdacht.
"""

from __future__ import annotations

import time

ZEILENENDE = chr(10)

_letztes = None            # das zuletzt empfangene Bild, als BGR
_letzte_nummer = 0
_typen = None              # geladene Tafelbibliothek
_zeiten: list[float] = []  # Farbwandlung, fuer die Kostenrechnung
_drehzeiten: list[float] = []
_letzte_drehung = 0        # wie der Sensor gegen die Anzeige stand


# Wie der Sensor gegen die Anzeige verdreht ist, uebersetzt in OpenCVs
# Drehcodes. 0 kommt nicht vor -- dann wird gar nicht gedreht.
_DREHUNG = {}


def _drehcodes():
    global _DREHUNG
    if not _DREHUNG:
        import cv2
        _DREHUNG = {90: cv2.ROTATE_90_CLOCKWISE,
                    180: cv2.ROTATE_180,
                    270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return _DREHUNG


def nimm_frame(rohdaten, breite: int, hoehe: int, zeilenabstand: int,
               drehung: int = 0) -> None:
    """Uebernimmt ein Kamerabild.

    `zeilenabstand` ist nicht immer `breite * 4`: Android legt Zeilen gern auf
    glatte Grenzen und fuellt den Rest auf. Wer das uebergeht, bekommt ein
    Bild, das sich mit jeder Zeile weiter nach rechts schiebt -- ein Fehler,
    der wie eine kaputte Kamera aussieht und keine ist.

    `drehung` ist der zweite solche Fallstrick. Der Sensor liefert immer in
    SEINER Lage: Haelt man das Telefon hochkant, kommt trotzdem ein liegendes
    Bild an. Die Vorschau dreht das von selbst, der Bildstrom nicht -- die
    Tafelsuche saehe eine um 90 Grad gekippte Halle und faende nie etwas.

    Gedreht wird HIER und nicht in Android, weil es sichtbar bleiben soll:
    Jede Groesse des Projekts ist in Bildkoordinaten gemessen, und wer die
    Achsen vertauscht, verstellt sie alle.
    """
    global _letztes, _letzte_nummer

    import cv2
    import numpy as np

    t0 = time.perf_counter()
    flach = np.frombuffer(rohdaten, dtype=np.uint8)
    rgba = flach.reshape(hoehe, zeilenabstand // 4, 4)[:, :breite, :]
    bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    t1 = time.perf_counter()
    code = _drehcodes().get(int(drehung) % 360)
    _letztes = cv2.rotate(bgr, code) if code is not None else bgr
    _drehzeiten.append((time.perf_counter() - t1) * 1000)
    if len(_drehzeiten) > 60:
        del _drehzeiten[:-60]
    _letzte_drehung = int(drehung) % 360
    globals()["_letzte_drehung"] = _letzte_drehung
    _letzte_nummer += 1
    _zeiten.append((t1 - t0) * 1000)
    if len(_zeiten) > 60:
        del _zeiten[:-60]


def zustand() -> str:
    """Kurzbericht fuer die Oberflaeche."""
    if _letztes is None:
        return "warte auf das erste Bild ..."
    hoehe, breite = _letztes.shape[:2]
    mittel = sum(_zeiten) / len(_zeiten) if _zeiten else 0.0
    dreh = sum(_drehzeiten) / len(_drehzeiten) if _drehzeiten else 0.0
    lage = "hochkant" if hoehe > breite else "quer"
    return (f"Bild {breite}x{hoehe} ({lage}), {_letzte_nummer} empfangen"
            + ZEILENENDE
            + f"Farbwandlung {mittel:.1f} ms, Drehung um {_letzte_drehung} Grad "
              f"{dreh:.1f} ms")


def _bibliothek(ordner: str):
    global _typen
    if _typen is None:
        from kegel_cv.calibration.board_library import lade_bibliothek
        _typen = lade_bibliothek(ordner)
    return _typen


def suche_tafeln(ordner: str) -> str:
    """Sucht Anzeigetafeln im zuletzt empfangenen Bild.

    Das ist die Probe aufs Exempel: Die Suche vergleicht Merkmale eines
    Musterbildes mit dem Kamerabild. Das Muster stammt von einer fest
    montierten Hallenkamera -- ob es auch auf ein Handybild passt, das schraeg
    und aus anderer Entfernung aufgenommen wurde, ist offen.
    """
    if _letztes is None:
        return "Noch kein Bild von der Kamera."

    # Der Zustand des Bildstroms gehoert zu jedem Ergebnis dazu: Eine Suche,
    # die auf einem 640x480-Bild nichts findet, sagt etwas anderes als eine
    # auf 1920x1080 -- alle gemessenen Groessen dieses Projekts beruhen auf
    # der grossen Aufloesung.
    kopf = zustand()

    typen = _bibliothek(ordner)
    if not typen:
        return kopf + ZEILENENDE + "Keine Tafeltypen geladen (" + ordner + ")"

    from kegel_cv.calibration.board_library import erkenne

    t0 = time.perf_counter()
    erkennung = erkenne(_letztes, typen)
    dauer = (time.perf_counter() - t0) * 1000

    if erkennung is None:
        return (kopf + ZEILENENDE
                + f"Keine Tafel gefunden ({dauer:.0f} ms, "
                f"{len(typen)} Typ(en) geprueft)." + ZEILENENDE
                + "Das ist in einer unbekannten Halle der Normalfall und kein"
                + " Fehler -- die Tafel muss gross und gerade im Bild stehen.")

    zeilen = [kopf,
              f"{erkennung.typ.name}: {len(erkennung.treffer)} Tafel(n), "
              f"{erkennung.merkmale} tragende Merkmale, {dauer:.0f} ms"]
    for i, treffer in enumerate(erkennung.treffer, 1):
        ecken = treffer.quad
        x = sum(p[0] for p in ecken) / 4
        y = sum(p[1] for p in ecken) / 4
        breit = max(p[0] for p in ecken) - min(p[0] for p in ecken)
        hoch = max(p[1] for p in ecken) - min(p[1] for p in ecken)
        zeilen.append(f"  {i}. Mitte ({x:.0f}, {y:.0f}), "
                      f"{breit:.0f}x{hoch:.0f} px, {treffer.inlier} Merkmale")
    return ZEILENENDE.join(zeilen)


def rechteck_der_tafeln(ordner: str):
    """Die gefundenen Tafeln als Liste von Ecken -- fuer die Anzeige.

    Getrennt von `suche_tafeln`, damit die Oberflaeche zeichnen kann, ohne den
    Text auseinanderzunehmen.
    """
    if _letztes is None:
        return []
    typen = _bibliothek(ordner)
    if not typen:
        return []
    from kegel_cv.calibration.board_library import erkenne
    erkennung = erkenne(_letztes, typen)
    if erkennung is None:
        return []
    return [[float(w) for p in t.quad for w in p] for t in erkennung.treffer]
