"""Vergleicht die Erkennung gegen das handgefuehrte Wurfprotokoll.

Das ist die erste Messung in diesem Projekt gegen eine Quelle, die NICHT aus
dem Bild stammt. Alle bisherigen Kennzahlen ("Ziffer stimmt mit Lampen",
"Summenkette bestaetigt") vergleichen zwei Lesungen desselben Bildes -- wo die
sich einig sind, kann trotzdem beides falsch sein.

Verglichen wird je Bahn die chronologische Wurffolge. Dabei wird AUSGERICHTET
und nicht stur nach Index verglichen: Fehlt dem Werkzeug ein Wurf, verschoebe
sich sonst alles dahinter, und aus einem Fehler wuerden hundert. Die
Ausrichtung trennt sauber:

    passt      gleiche Kegelzahl an derselben Stelle
    falsch     Wurf erkannt, Kegelzahl daneben
    fehlt      im Protokoll, vom Werkzeug nicht gemeldet
    zuviel     vom Werkzeug gemeldet, im Protokoll nicht vorhanden

Aufruf -- entweder die `wuerfe.csv` eines Laufordners oder eine
`vollauswertung.json`:

    .venv/Scripts/python.exe tools/compare_protocol.py <laufordner>/wuerfe.csv \
        --wahrheit data/ground_truth/wurfprotokoll_spieltag_1.csv \
        --aus debug/protokollvergleich_spieltag1.csv

Ergebnis: je Zeile ein ausgerichtetes Wurfpaar.

ACHTUNG, wenn das Protokoll nur einen TEIL des Videos abdeckt: Die Ausrichtung
findet dann den passenden Abschnitt, aber alles davor und dahinter zaehlt als
"zuviel". Diese Zahl ist dann KEINE Fehlerquote -- sie sagt nur, wie viel
ausserhalb des Protokolls liegt. Aussagekraeftig sind "passt" und "falsch".
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

AUSWERTUNG = Path("debug/vollauswertung.json")
WAHRHEIT = Path("data/ground_truth/wurfprotokoll_langes_video.csv")
AUSGABE = Path("debug/protokollvergleich.csv")

# Bewertung der Ausrichtung. Eine Luecke muss teurer sein als ein Zahlendreher,
# sonst erklaert die Ausrichtung jede falsche Zahl lieber durch "fehlt + zuviel"
# und die Statistik sieht kuenstlich gut aus.
TREFFER = 2
DANEBEN = -1
LUECKE = -3


def ausrichten(werkzeug: list[int], wahrheit: list[int]) -> list[tuple]:
    """Needleman-Wunsch ueber zwei Wurffolgen.

    Liefert Paare (index_werkzeug, index_wahrheit), wobei None fuer eine Luecke
    steht. 120 x 120 Felder je Bahn -- der Aufwand faellt nicht ins Gewicht.
    """
    n, m = len(werkzeug), len(wahrheit)
    punkte = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        punkte[i][0] = punkte[i - 1][0] + LUECKE
    for j in range(1, m + 1):
        punkte[0][j] = punkte[0][j - 1] + LUECKE

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diagonal = punkte[i - 1][j - 1] + (
                TREFFER if werkzeug[i - 1] == wahrheit[j - 1] else DANEBEN)
            punkte[i][j] = max(diagonal,
                               punkte[i - 1][j] + LUECKE,
                               punkte[i][j - 1] + LUECKE)

    paare: list[tuple] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            diagonal = punkte[i - 1][j - 1] + (
                TREFFER if werkzeug[i - 1] == wahrheit[j - 1] else DANEBEN)
            if punkte[i][j] == diagonal:
                paare.append((i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and punkte[i][j] == punkte[i - 1][j] + LUECKE:
            paare.append((i - 1, None))
            i -= 1
            continue
        paare.append((None, j - 1))
        j -= 1
    paare.reverse()
    return paare


def wuerfe_aus_csv(pfad: Path) -> list[dict]:
    """Liest eine `wuerfe.csv` in dieselbe Form wie die JSON-Auswertung.

    Damit laesst sich jeder Laufordner vergleichen, ohne vorher eine
    Gesamtauswertung zu erzeugen -- die CSV entsteht ohnehin bei jedem Lauf.
    """
    wuerfe: list[dict] = []
    with pfad.open(encoding="utf-8-sig", newline="") as datei:
        for zeile in csv.DictReader(datei, delimiter=";"):
            ziffer = zeile.get("Ziffer", "")
            wuerfe.append({
                "lane": int(zeile["Bahn"]),
                "pins_count": int(zeile["Kegel"]),
                "pins": [int(x) for x in zeile["Kegelnummern"].split()
                         if x.isdigit()],
                "throw_number": int(zeile["Wurfnummer"]),
                "source_frame": int(zeile["Frame"]),
                "timestamp": float(zeile.get("Zeitstempel_s") or 0.0),
                "status": zeile["Status"],
                "displayed_pin_count": int(ziffer) if ziffer.isdigit() else None,
                "raeumen": zeile.get("Raeumen", ""),
            })
    return wuerfe


def wahrheit_lesen(pfad: Path) -> dict[int, list[dict]]:
    if not pfad.exists():
        raise SystemExit(f"Bodenwahrheit fehlt: {pfad}")
    je_bahn: dict[int, list[dict]] = {}
    with pfad.open(encoding="utf-8-sig", newline="") as datei:
        for zeile in csv.DictReader(datei, delimiter=";"):
            je_bahn.setdefault(int(zeile["Bahn"]), []).append({
                "satz": int(zeile["Satz"]),
                "spieler": zeile["Spieler"],
                "wurf": int(zeile["Wurf"]),
                "kegel": int(zeile["Kegel"]),
                "modus": zeile["Modus"],
            })
    return je_bahn


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("quelle", nargs="?", type=Path, default=AUSWERTUNG,
                   help="wuerfe.csv eines Laufs ODER vollauswertung.json")
    p.add_argument("--wahrheit", type=Path, default=WAHRHEIT)
    p.add_argument("--aus", type=Path, default=AUSGABE)
    a = p.parse_args()

    pfad = a.quelle
    if not pfad.exists():
        print(f"Keine Auswertung unter {pfad}")
        return 1

    if pfad.suffix.lower() == ".csv":
        alle_wuerfe = wuerfe_aus_csv(pfad)
        quelle_name = pfad.parent.name
    else:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        alle_wuerfe = daten["wuerfe"]
        quelle_name = daten.get("video", pfad.name)
    wahrheit = wahrheit_lesen(a.wahrheit)

    erkannt: dict[int, list[dict]] = {}
    for wurf in alle_wuerfe:
        erkannt.setdefault(wurf["lane"], []).append(wurf)
    for liste in erkannt.values():
        liste.sort(key=lambda w: w["source_frame"])

    print("=" * 78)
    print(f"VERGLEICH GEGEN DAS WURFPROTOKOLL   ({pfad.name})")
    print("=" * 78)
    print(f"Quelle    : {quelle_name}")
    print(f"Wahrheit  : {a.wahrheit.name}")
    print(f"Erkannt   : {len(alle_wuerfe)} Wuerfe")
    print(f"Protokoll : {sum(len(v) for v in wahrheit.values())} Wuerfe\n")

    zeilen: list[dict] = []
    gesamt = Counter()
    je_bahn_kennzahl = []

    for bahn in sorted(wahrheit):
        wuerfe = erkannt.get(bahn, [])
        soll = wahrheit[bahn]
        paare = ausrichten([w["pins_count"] for w in wuerfe],
                           [s["kegel"] for s in soll])

        zaehler = Counter()
        for i, j in paare:
            w = wuerfe[i] if i is not None else None
            s = soll[j] if j is not None else None
            if w is None:
                art = "fehlt"
            elif s is None:
                art = "zuviel"
            elif w["pins_count"] == s["kegel"]:
                art = "passt"
            else:
                art = "falsch"
            zaehler[art] += 1

            zeilen.append({
                "Bahn": bahn,
                "Art": art,
                "Satz": s["satz"] if s else "",
                "Spieler": s["spieler"] if s else "",
                "Wurf_Protokoll": s["wurf"] if s else "",
                "Kegel_Protokoll": s["kegel"] if s else "",
                "Modus": s["modus"] if s else "",
                "Kegel_Werkzeug": w["pins_count"] if w else "",
                "Ziffer_Werkzeug": (w.get("displayed_pin_count")
                                    if w and w.get("displayed_pin_count") is not None
                                    else ""),
                "Wurfnr_Werkzeug": w["throw_number"] if w else "",
                "Frame": w["source_frame"] if w else "",
                "Zeit": (f"{int(w['timestamp'] // 60)}:{int(w['timestamp'] % 60):02d}"
                         if w else ""),
                "Status": w["status"] if w else "",
                "Kegelnummern": " ".join(map(str, w["pins"])) if w else "",
                "Raeumen": ("ja" if w and (w.get("evidence") or {}).get(
                    "raw", {}).get("clearing") else ""),
            })

        gesamt.update(zaehler)
        vergleichbar = zaehler["passt"] + zaehler["falsch"]
        je_bahn_kennzahl.append((bahn, zaehler, vergleichbar, len(soll)))

    # -------------------------------------------------------------- Ausgabe
    print(f"{'Bahn':<6}{'passt':>8}{'falsch':>8}{'fehlt':>8}{'zuviel':>8}"
          f"{'erfasst':>10}{'richtig':>10}")
    for bahn, z, vergleichbar, anzahl_soll in je_bahn_kennzahl:
        print(f"{bahn:<6}{z['passt']:>8}{z['falsch']:>8}{z['fehlt']:>8}"
              f"{z['zuviel']:>8}"
              f"{100 * vergleichbar / anzahl_soll:>9.1f}%"
              f"{100 * z['passt'] / anzahl_soll:>9.1f}%")

    soll_gesamt = sum(len(v) for v in wahrheit.values())
    vergleichbar_gesamt = gesamt["passt"] + gesamt["falsch"]
    print("-" * 58)
    print(f"{'alle':<6}{gesamt['passt']:>8}{gesamt['falsch']:>8}"
          f"{gesamt['fehlt']:>8}{gesamt['zuviel']:>8}"
          f"{100 * vergleichbar_gesamt / soll_gesamt:>9.1f}%"
          f"{100 * gesamt['passt'] / soll_gesamt:>9.1f}%")

    # Kegelsummen -- die Zahl, die am Ende auf dem Spielberichtsbogen steht
    print(f"\nKegel je Satz -- Werkzeug/Protokoll\n")
    print(f"{'Bahn':<6}{'Satz 1':>12}{'Satz 2':>12}{'Satz 3':>12}{'Satz 4':>12}"
          f"{'gesamt':>13}")
    for bahn in sorted(wahrheit):
        soll_satz = {}
        ist_satz = {}
        for zeile in zeilen:
            if zeile["Bahn"] != bahn or not zeile["Satz"]:
                continue
            satz = zeile["Satz"]
            if zeile["Kegel_Protokoll"] != "":
                soll_satz[satz] = soll_satz.get(satz, 0) + zeile["Kegel_Protokoll"]
            if zeile["Kegel_Werkzeug"] != "":
                ist_satz[satz] = ist_satz.get(satz, 0) + zeile["Kegel_Werkzeug"]
        teile = []
        for satz in (1, 2, 3, 4):
            ist, sollwert = ist_satz.get(satz, 0), soll_satz.get(satz, 0)
            marke = "  ok" if ist == sollwert else f"{ist - sollwert:+4d}"
            teile.append(f"{ist:>3}/{sollwert:<3}{marke}")
        print(f"{bahn:<6}" + "".join(f"{t:>12}" for t in teile)
              + f"{sum(ist_satz.values()):>8}/{sum(soll_satz.values())}")

    kegel_ist = sum(z["Kegel_Werkzeug"] for z in zeilen if z["Kegel_Werkzeug"] != "")
    kegel_soll = sum(z["Kegel_Protokoll"] for z in zeilen if z["Kegel_Protokoll"] != "")
    print(f"\nKegel gesamt: Werkzeug {kegel_ist}, Protokoll {kegel_soll} "
          f"({kegel_ist - kegel_soll:+d}, {100 * kegel_ist / kegel_soll:.1f} %)")

    # Wo es falsch war: Sagte die ZIFFER die Wahrheit? Das trennt einen Fehler
    # der Lampen von einem Fehler des Messzeitpunkts.
    falsche = [z for z in zeilen if z["Art"] == "falsch"]
    ziffer_haette_geholfen = [z for z in falsche
                              if z["Ziffer_Werkzeug"] == z["Kegel_Protokoll"]]
    print(f"\nVon {len(falsche)} falschen Wuerfen haette die Ziffernanzeige "
          f"{len(ziffer_haette_geholfen)} richtig gehabt.")

    abweichungen = Counter(z["Kegel_Werkzeug"] - z["Kegel_Protokoll"]
                           for z in falsche)
    if abweichungen:
        print("Abweichung (Werkzeug minus Protokoll):")
        for wert, anzahl in sorted(abweichungen.items()):
            print(f"   {wert:+d} Kegel: {anzahl:>3}x")

    a.aus.parent.mkdir(parents=True, exist_ok=True)
    with a.aus.open("w", encoding="utf-8-sig", newline="") as datei:
        schreiber = csv.DictWriter(datei, fieldnames=list(zeilen[0]), delimiter=";")
        schreiber.writeheader()
        schreiber.writerows(zeilen)
    print(f"\nZeile fuer Zeile: {AUSGABE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
