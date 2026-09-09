# -*- coding: utf-8 -*-
import io, sys
from pathlib import Path
sys.path.insert(0, "src")
import cv2
from kegel_cv.config.loader import load_config
from kegel_cv.video.factory import open_source

src = io.open("C:/Users/nikla/AppData/Local/Temp/claude/C--Users-nikla-Kegel-CV/"
              "6c1098ee-d3b4-4b74-b1f8-74f462de5c0e/scratchpad/quelle_spieltag2.txt").read().strip()
cfg = load_config()
q = open_source(src, cfg); q.open()
print("Info:", q.info.frame_count, "Frames", flush=True)
q.seek(295000)
frame = q.read()
letzter = None
n = 0
while frame is not None:
    letzter = frame
    n += 1
    frame = q.read()
q.close()
if letzter is not None:
    cv2.imwrite("debug/endstand_spieltag2/frame_LETZTER.png", letzter.image)
    print(f"Letzter lesbarer Frame: {letzter.index}  ({n} ab F295000 gelesen)")
