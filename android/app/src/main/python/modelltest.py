"""Welches Personenmodell kann das OpenCV DIESES Telefons ueberhaupt lesen?

ANLASS (2026-09-14): YOLOX-Tiny laedt auf dem Entwicklungsrechner (OpenCV 5.0)
und auf 4.5.5 anstandslos, scheitert aber auf dem Geraet an OpenCV 4.5.1:

    Slice layer only supports steps = 1

Das ist die Focus-Schicht am Netzeingang, die das Bild mit Schrittweite 2
zerlegt. Neuere ONNX-Importer koennen das, 4.5.1 nicht. Die Lehre: Eine
Modelldatei ist erst dann geprueft, wenn sie auf der Zielhardware geladen hat.

Dieses Modul probiert reihum alles durch, was an Modellen dabei ist, und misst
gleich mit.
"""

from __future__ import annotations

import os
import time

ZEILENENDE = chr(10)


def pruefe(ordner: str) -> str:
    import cv2
    import numpy as np

    zeilen = ["OpenCV " + cv2.__version__, ""]
    dateien = sorted(d for d in os.listdir(ordner) if d.endswith(".onnx"))
    if not dateien:
        return "keine Modelle in " + ordner

    for name in dateien:
        pfad = os.path.join(ordner, name)
        groesse = os.path.getsize(pfad) / 1e6
        try:
            netz = cv2.dnn.readNet(pfad)
        except Exception as exc:
            kurz = str(exc).strip().splitlines()
            grund = kurz[-1].strip() if kurz else type(exc).__name__
            zeilen.append("%-28s %5.1f MB  LAEDT NICHT" % (name, groesse))
            zeilen.append("      " + grund[:110])
            continue

        # Eingangskante aus dem Dateinamen ableiten, sonst 416 versuchen.
        kante = 640 if "640" in name or "yolox_2022" in name else 416
        blob = np.zeros((1, 3, kante, kante), np.float32)
        try:
            netz.setInput(blob)
            netz.forward()
            zeiten = []
            for _ in range(3):
                t0 = time.perf_counter()
                netz.setInput(blob)
                netz.forward()
                zeiten.append((time.perf_counter() - t0) * 1000)
            zeiten.sort()
            zeilen.append("%-28s %5.1f MB  %4d px  %7.0f ms"
                          % (name, groesse, kante, zeiten[1]))
        except Exception as exc:
            zeilen.append("%-28s %5.1f MB  laedt, rechnet nicht" % (name, groesse))
            zeilen.append("      " + str(exc).strip().splitlines()[-1][:110])

    return ZEILENENDE.join(zeilen)
