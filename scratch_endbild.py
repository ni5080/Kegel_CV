# -*- coding: utf-8 -*-
import io, sys
from pathlib import Path
sys.path.insert(0, "src")
import cv2
from kegel_cv.config.loader import load_config
from kegel_cv.video.factory import open_source

src = io.open("C:/Users/nikla/AppData/Local/Temp/claude/C--Users-nikla-Kegel-CV/"
              "6c1098ee-d3b4-4b74-b1f8-74f462de5c0e/scratchpad/quelle_spieltag2.txt").read().strip()
ZIEL = 293575          # 3:15:43 bei 25 fps
cfg = load_config()
q = open_source(src, cfg); q.open()
print("Stream offen, spule zu Frame", ZIEL, flush=True)
q.seek(ZIEL)
frame = q.read()
n = 0
aus = Path("debug/endstand_spieltag2")
while frame is not None and n < 5:
    if frame.index >= ZIEL:
        p = aus / f"frame_{frame.index}.png"
        cv2.imwrite(str(p), frame.image)
        print(f"  {p}  ({frame.image.shape[1]}x{frame.image.shape[0]})", flush=True)
        n += 1
        # ein paar Sekunden weiter, falls die Anzeige wechselt
        for _ in range(75):
            frame = q.read()
            if frame is None:
                break
        continue
    frame = q.read()
q.close()
print("fertig")
