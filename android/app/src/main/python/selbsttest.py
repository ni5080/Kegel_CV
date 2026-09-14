"""Laeuft der Erkennungskern auf diesem Telefon -- und wie schnell?

Dieser Stand baut noch keine Anwendung, er beantwortet eine Frage: Traegt
Chaquopy Python samt numpy und OpenCV auf echter Hardware, und wie teuer sind
die Rechenschritte, auf denen alles andere aufsetzt?

Auf dem Entwicklungsrechner laeuft OpenCV 5.0, auf dem Telefon 4.5.1 -- das
Neueste, was Chaquopys Paketquelle anbietet. Deshalb steht die Version hier
oben in der Ausgabe: Sie gehoert zu jedem Messwert dazu.
"""

from __future__ import annotations

import platform
import time


def _messe(was, wiederholungen: int = 5) -> float:
    """Median mehrerer Durchlaeufe in Millisekunden."""
    zeiten = []
    for _ in range(wiederholungen):
        t0 = time.perf_counter()
        was()
        zeiten.append((time.perf_counter() - t0) * 1000)
    zeiten.sort()
    return zeiten[len(zeiten) // 2]


def selbsttest() -> str:
    zeilen: list[str] = []

    zeilen.append(f"Python   {platform.python_version()}")
    zeilen.append(f"Maschine {platform.machine()}")

    try:
        import numpy as np
    except Exception as exc:                       # pragma: no cover
        return "\n".join(zeilen + [f"numpy fehlt: {exc}"])
    zeilen.append(f"numpy    {np.__version__}")

    try:
        import cv2
    except Exception as exc:                       # pragma: no cover
        return "\n".join(zeilen + [f"OpenCV fehlt: {exc}"])
    zeilen.append(f"OpenCV   {cv2.__version__}")
    zeilen.append("")

    # Ein Vollbild in der Groesse, die die Anlage liefert.
    bild = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)

    # 1. Die gruene Lampe: der Schritt, der in JEDEM Frame laeuft.
    ausschnitt = bild[80:130, 600:650]

    def gruen():
        hsv = cv2.cvtColor(ausschnitt, cv2.COLOR_BGR2HSV)
        maske = cv2.inRange(hsv, (35, 80, 80), (85, 255, 255))
        return float(maske.mean())

    zeilen.append(f"Gruenlampe (50x50)      {_messe(gruen, 20):6.2f} ms")

    # 2. Die Entzerrung einer Tafel -- Grundlage jeder ROI-Messung.
    quelle = np.float32([[534, 71], [676, 71], [676, 216], [534, 216]])
    ziel = np.float32([[0, 0], [400, 0], [400, 400], [0, 400]])
    matrix = cv2.getPerspectiveTransform(quelle, ziel)

    def entzerren():
        return cv2.warpPerspective(bild, matrix, (400, 400))

    zeilen.append(f"Tafel entzerren         {_messe(entzerren):6.2f} ms")

    # 3. Das Hintergrundmodell der Personenmaske.
    mog = cv2.createBackgroundSubtractorMOG2(500, 32.0, False)
    klein = cv2.resize(bild, (480, 270))
    for _ in range(5):
        mog.apply(klein)

    def maske():
        return mog.apply(klein)

    zeilen.append(f"Bewegungsmaske (1/4)    {_messe(maske):6.2f} ms")

    # 4. Das Personenmodell -- der teuerste Schritt, und der einzige, der
    #    ueberhaupt nur laeuft, wenn ein billiger Zeuge etwas meldet.
    zeilen.append("")
    try:
        from com.chaquo.python import Python           # type: ignore
        from os.path import join

        ordner = str(Python.getPlatform().getApplication()
                     .getFilesDir().getAbsolutePath())
        pfad = join(ordner, "yolox_tiny.onnx")
        netz = cv2.dnn.readNet(pfad)
        blob = np.zeros((1, 3, 416, 416), np.float32)
        netz.setInput(blob)
        netz.forward()

        def modell():
            netz.setInput(blob)
            return netz.forward()

        zeilen.append(f"Personenmodell (416)  {_messe(modell, 3):8.1f} ms")
    except Exception as exc:
        zeilen.append(f"Personenmodell: {type(exc).__name__} -- {exc}")

    return "\n".join(zeilen)
