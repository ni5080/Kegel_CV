# -*- coding: utf-8 -*-
import csv, io, sys, glob
from pathlib import Path
sys.path.insert(0, "src")
import cv2, numpy as np
from kegel_cv.analysis.lane_processor import LaneProcessor
from kegel_cv.calibration import Calibration
from kegel_cv.config.loader import load_config
from kegel_cv.video.factory import open_source

p = sorted(glob.glob("debug/manifest*/lauf_2026-09-04_15-12*/wuerfe.csv"))[0]
wuerfe = [r for r in csv.DictReader(io.open(p, encoding="utf-8-sig", newline=""), delimiter=";")
          if r["Bahn"] == "5" and 80818 <= int(r["Frame"]) <= 104452]
ziele = {int(r["Frame"]): r for r in wuerfe}
src = io.open("C:/Users/nikla/AppData/Local/Temp/claude/C--Users-nikla-Kegel-CV/"
              "6c1098ee-d3b4-4b74-b1f8-74f462de5c0e/scratchpad/quelle_spieltag2.txt").read().strip()

cfg = load_config()
cal = Calibration.load("data/calibrations/KSG_Neuhof.json")
q = open_source(src, cfg); q.open()
erster = q.read()
lane = next(l for l in cal.lanes if l.display_number == 5)
proz = LaneProcessor(lane, cfg); proz.prepare(erster.image.shape)

aus = Path("debug/satz_bahn5_31"); aus.mkdir(parents=True, exist_ok=True)
VON, BIS = min(ziele), max(ziele)
print(f"Lese F{VON}-F{BIS} ({BIS-VON} Frames) fuer {len(ziele)} Wuerfe ...", flush=True)
q.seek(VON)
frame = q.read()
kacheln = []
while frame is not None and frame.index <= BIS:
    if frame.index in ziele:
        r = ziele[frame.index]
        lx, ly, lw, lh = proz.lane_box()
        tafel = frame.image[ly:ly+lh, lx:lx+lw].copy()
        kacheln.append((int(r["Wurfnummer"]), int(r["Kegel"]), frame.index, tafel))
        cv2.imwrite(str(aus / f"wurf{int(r['Wurfnummer']):02d}_F{frame.index}_{r['Kegel']}kegel.png"), tafel)
    frame = q.read()
q.close()
print(f"{len(kacheln)} Bilder gespeichert", flush=True)

# Kontaktbogen
BREIT, SPALTEN = 300, 6
h_bild = int(BREIT * kacheln[0][3].shape[0] / kacheln[0][3].shape[1])
h_text = 30
reihen = (len(kacheln) + SPALTEN - 1) // SPALTEN
bogen = np.full((reihen*(h_bild+h_text), SPALTEN*BREIT, 3), 25, np.uint8)
for i, (nr, kegel, idx, tafel) in enumerate(kacheln):
    r, c = divmod(i, SPALTEN)
    y0, x0 = r*(h_bild+h_text), c*BREIT
    bogen[y0:y0+h_bild, x0:x0+BREIT] = cv2.resize(tafel, (BREIT, h_bild))
    letzter = (i == len(kacheln)-1)
    farbe = (0, 160, 255) if letzter else (230, 230, 230)
    if letzter:
        cv2.rectangle(bogen, (x0+1, y0+1), (x0+BREIT-2, y0+h_bild-2), (0,160,255), 3)
    cv2.putText(bogen, f"Wurf {nr}  {kegel} Kegel  F{idx}", (x0+6, y0+h_bild+20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, farbe, 1, cv2.LINE_AA)
cv2.imwrite("debug/satz_bahn5_31/kontaktbogen.png", bogen)
print("Kontaktbogen:", bogen.shape[1], "x", bogen.shape[0])
