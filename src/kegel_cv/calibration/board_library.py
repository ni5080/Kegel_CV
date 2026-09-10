"""Bibliothek bekannter Tafeltypen -- damit eine Halle sich selbst erklaert.

DIE IDEE (vom Nutzer, 2026-09-09)

    "cool waere, wenn er standardmaessig wenn ein Stream startet schaut, ob er
     eins der bekannten Kegelboards aus seinem Repertoire kennt. Langfristig
     sollen alle typischen Boards selbststaendig erkannt werden."

Ein Tafeltyp besteht aus zwei Dingen:

* einem **Musterbild** -- die geradegerechnete Tafel, wie sie einmal
  aufgenommen wurde
* den **ROIs in normierten Tafelkoordinaten** -- wo Lampen und Ziffern auf
  dieser Bauart sitzen

Beides zusammen genuegt: Wird das Muster in einem neuen Bild wiedergefunden,
folgen alle Felder aus den vier gefundenen Ecken. Genau darauf beruht die
automatische Kalibrierung.

WAS EIN TYP NICHT IST: eine Halle. Dieselbe FUNK-Anlage steht in vielen
Vereinen. Der Typ beschreibt die BAUART, nicht den Ort -- deshalb traegt er
auch keine Adresse und keinen Vereinsnamen.

WIE SICHER IST SICHER GENUG

Die Zahl der tragenden Merkmale (RANSAC-Inlier) trennt sauber. GEMESSEN am
2026-09-09 ueber vier Tafeln in zwei verschiedenen Quellen: gelungene Treffer
hatten 15 bis 197 Merkmale, ein Fehltreffer 7 -- und der lag 1429 Pixel
daneben. Deshalb gilt ein Typ erst ab `min_inlier` als erkannt, und ein
erkannter Typ wird dem Nutzer VORGESCHLAGEN, nicht aufgezwungen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .board_finder import BoardFinder, Treffer, entzerre, quad_groesse
from .model import Calibration

log = logging.getLogger(__name__)

# Neben jedem Tafeltyp liegt sein Musterbild unter demselben Namen.
MUSTER_ENDUNG = ".png"


@dataclass
class Tafeltyp:
    """Eine bekannte Bauart: Musterbild plus die ROIs darauf."""

    name: str
    muster: np.ndarray
    kalibrierung: Calibration

    @property
    def bahn(self):
        """Die eine Bahn, die den Typ beschreibt."""
        return self.kalibrierung.lanes[0]


@dataclass
class Erkennung:
    """Ein erkannter Typ samt der gefundenen Tafeln."""

    typ: Tafeltyp
    treffer: list[Treffer]

    @property
    def merkmale(self) -> int:
        return sum(t.inlier for t in self.treffer)


def lade_bibliothek(ordner: str | Path) -> list[Tafeltyp]:
    """Liest alle Tafeltypen aus einem Ordner.

    Ein Typ, dessen Musterbild fehlt, wird uebersprungen statt zu werfen: Eine
    unvollstaendige Bibliothek darf den Programmstart nicht verhindern.
    """
    ordner = Path(ordner)
    if not ordner.is_dir():
        return []

    typen: list[Tafeltyp] = []
    for pfad in sorted(ordner.glob("*.json")):
        bild_pfad = pfad.with_suffix(MUSTER_ENDUNG)
        if not bild_pfad.is_file():
            log.warning("Tafeltyp %s hat kein Musterbild (%s erwartet)",
                        pfad.stem, bild_pfad.name)
            continue
        muster = cv2.imread(str(bild_pfad))
        if muster is None:
            log.warning("Musterbild %s liess sich nicht lesen", bild_pfad.name)
            continue
        try:
            kal = Calibration.load(pfad)
        except Exception as exc:  # noqa: BLE001
            # Eine kaputte Datei darf die uebrigen Typen nicht mitnehmen.
            log.warning("Tafeltyp %s unbrauchbar: %s", pfad.stem, exc)
            continue
        if not kal.lanes:
            log.warning("Tafeltyp %s enthaelt keine Bahn", pfad.stem)
            continue
        typen.append(Tafeltyp(name=pfad.stem, muster=muster, kalibrierung=kal))
    log.info("Tafelbibliothek: %d Typen aus %s", len(typen), ordner)
    return typen


def erkenne(bild: np.ndarray, typen: list[Tafeltyp], *,
            min_inlier: int = 18, max_tafeln: int = 8) -> Erkennung | None:
    """Sucht den Typ, der am besten zu diesem Bild passt.

    Gewertet wird nach der Zahl der TAFELN zuerst und der Summe der tragenden
    Merkmale danach: Ein Typ, der vier Tafeln findet, ist mehr wert als einer,
    der eine einzige besonders sicher trifft.

    Rueckgabe None, wenn keiner passt -- das ist der Normalfall in einer
    unbekannten Halle und kein Fehler.
    """
    if bild is None or bild.size == 0 or not typen:
        return None

    finder = BoardFinder(min_inlier=min_inlier)
    bestes: Erkennung | None = None
    for typ in typen:
        treffer = finder.finde_alle(bild, [typ.muster], max_tafeln=max_tafeln)
        if not treffer:
            continue
        treffer = _verfeinere(bild, treffer, finder, max_tafeln)
        kandidat = Erkennung(typ=typ, treffer=treffer)
        log.debug("Tafeltyp %s: %d Tafeln, %d tragende Merkmale",
                  typ.name, len(treffer), kandidat.merkmale)
        if bestes is None or (len(kandidat.treffer), kandidat.merkmale) > \
                (len(bestes.treffer), bestes.merkmale):
            bestes = kandidat

    if bestes is not None:
        log.info("Tafeltyp erkannt: %s -- %d Tafeln, %d tragende Merkmale",
                 bestes.typ.name, len(bestes.treffer), bestes.merkmale)
    return bestes


def _mitte(quad) -> tuple[float, float]:
    q = np.asarray(quad, dtype=float)
    return float(q[:, 0].mean()), float(q[:, 1].mean())


def erkenne_ueber_frames(bilder: list[np.ndarray], typen: list[Tafeltyp], *,
                         min_inlier: int = 14, anker_inlier: int = 8,
                         min_frames: int = 2, max_tafeln: int = 8,
                         runden: int = 3) -> Erkennung | None:
    """Sucht ueber MEHRERE Standbilder statt ueber eines.

    WARUM EIN BILD NICHT GENUEGT -- gemessen 2026-09-10 am Verbandsligaspiel,
    16 Stichproben ueber 3:08 h, Typ FUNK_klassisch gegen vier gleiche Tafeln:

        4 Tafeln gefunden   1 Frame
        3 Tafeln            6 Frames
        1 Tafel             4 Frames
        gar nichts          5 Frames

    Der Grund steht auf der Tafel selbst: Leuchtende Kegellampen und wechselnde
    Ziffern veraendern genau die Merkmale, an denen der Abgleich haengt. Auf
    einem Bild mit vielen brennenden Lampen wurde KEINE Tafel gefunden, obwohl
    alle vier klar zu sehen waren.

    Was sich dagegen NICHT aendert, ist die Lage: Ein Overlay steht fest, und
    eine Tafel an der Wand steht auch fest. Deshalb wird ueber mehrere Bilder
    gesucht und nach Lage gebuendelt. Was in mindestens `min_frames` Bildern an
    derselben Stelle auftaucht, ist eine Tafel; ein Zufallstreffer wiederholt
    sich dort nicht.

    ZWEI SCHRANKEN, mit Absicht verschieden hoch:

    * `min_inlier` fuer den ANKER -- die erste Tafel, die mit der Vorlage aus
      der Bibliothek gefunden wird. Sie muss sitzen, denn aus ihr wird die
      Vorlage fuer alles Weitere geschnitten.
    * `anker_inlier` fuer die uebrigen. Sie duerfen niedriger liegen, weil die
      Wiederholung ueber mehrere Bilder die Sicherheit ersetzt, die sonst die
      hohe Schranke geben muesste. GEMESSEN: Die vierte Tafel kam mit 11
      tragenden Merkmalen -- unter der Schranke 14, aber an der richtigen
      Stelle und in drei Bildern.
    """
    bilder = [b for b in bilder if b is not None and b.size]
    if not bilder or not typen:
        return None

    bestes: Erkennung | None = None
    for typ in typen:
        treffer = _kette(bilder, typ.muster, min_inlier=min_inlier,
                         anker_inlier=anker_inlier, min_frames=min_frames,
                         max_tafeln=max_tafeln, runden=runden)
        if not treffer:
            continue
        kandidat = Erkennung(typ=typ, treffer=treffer)
        log.info("Tafeltyp %s ueber %d Bilder: %d Tafeln, %d tragende "
                 "Merkmale", typ.name, len(bilder), len(treffer),
                 kandidat.merkmale)
        if bestes is None or (len(kandidat.treffer), kandidat.merkmale) > \
                (len(bestes.treffer), bestes.merkmale):
            bestes = kandidat
    return bestes


class LaufendeSuche:
    """Eine Suche, die Bild fuer Bild waechst -- fuer den Livestream.

    WOFUER -- Einwand des Nutzers am 2026-09-10:

        "Das ganze soll ja spaeter im Livestream laufen, da kann er ja nicht
         einfach hin und herspringen ... eigentlich waere es besser, wenn er
         in den ersten 5-10 Sekunden das glattzieht ... und wenn es nach 20
         Sekunden immer noch nicht alle Boards gefunden hat"

    Ein Stream hat keine Vergangenheit: Es laesst sich nicht zu Frame 84750
    springen, um ein besseres Bild zu holen. Es gibt nur das naechste Bild.
    Also arbeitet die Suche andersherum -- sie nimmt entgegen, was kommt, und
    wird mit jedem Bild besser.

    ABBRUCH NACH ERFOLG, NICHT NACH ZEIT: Sind so viele Tafeln gefunden wie
    erwartet, ist die Suche fertig. GEMESSEN an der Aufzeichnung: Das tritt
    meist nach zwei bis vier Bildern ein -- keine zwanzig Sekunden Wartezeit,
    wenn es gut laeuft.
    """

    def __init__(self, typen: list[Tafeltyp], *, ziel_anzahl: int = 4,
                 min_inlier: int = 14, anker_inlier: int = 8,
                 min_frames: int = 2, max_tafeln: int = 8) -> None:
        self.typen = list(typen)
        self.ziel_anzahl = max(1, ziel_anzahl)
        self.min_frames = min_frames
        self.max_tafeln = max_tafeln
        self.bilder_gesehen = 0
        self._grob = BoardFinder(min_inlier=min_inlier)
        self._fein = BoardFinder(min_inlier=anker_inlier)
        # Je Bauart: Vorlagen, gebuendelte Funde, schon verwendete Buendel.
        self._stand: dict[str, dict] = {
            typ.name: {"typ": typ, "vorlagen": [], "gruppen": [],
                       "benutzt": set()} for typ in self.typen}

    def fuettere(self, bild: np.ndarray) -> None:
        """Nimmt ein weiteres Standbild entgegen."""
        if bild is None or bild.size == 0:
            return
        self.bilder_gesehen += 1
        for stand in self._stand.values():
            if not stand["vorlagen"]:
                # Noch kein Anker: mit dem Muster aus der Bibliothek suchen.
                gefunden = self._grob.finde_alle(bild, [stand["typ"].muster],
                                                 max_tafeln=self.max_tafeln)
                if not gefunden:
                    continue
                bester = max(gefunden, key=lambda t: t.inlier)
                stand["vorlagen"] = [_ausschnitt(bild, bester.quad)]
                # Der Anker zaehlt selbst als Fund -- sonst muesste er sich
                # in einem spaeteren Bild noch einmal beweisen.
                _einsortieren(stand["gruppen"], (bester, bild))
                # KEIN `continue`: Mit der frischen Vorlage wird DASSELBE
                # Bild sofort noch einmal durchsucht. Im Livestream kostet
                # jedes verschenkte Bild eine knappe Sekunde.

            for t in self._fein.finde_alle(bild, stand["vorlagen"],
                                           max_tafeln=self.max_tafeln):
                _einsortieren(stand["gruppen"], (t, bild))
            self._neue_vorlagen(stand)

    def _neue_vorlagen(self, stand: dict) -> None:
        """Jede neu bestaetigte Tafel wird selbst zur Vorlage (Ankerkette)."""
        for i, g in enumerate(stand["gruppen"]):
            if i in stand["benutzt"] or len(g) < self.min_frames:
                continue
            stand["benutzt"].add(i)
            t, bild = max(g, key=lambda x: x[0].inlier)
            ausschnitt = _ausschnitt(bild, t.quad)
            if ausschnitt is not None and ausschnitt.size:
                stand["vorlagen"].append(ausschnitt)

    def _treffer(self, stand: dict) -> list[Treffer]:
        treffer = [max(g, key=lambda x: x[0].inlier)[0]
                   for g in stand["gruppen"] if len(g) >= self.min_frames]
        treffer.sort(key=lambda t: _mitte(t.quad)[0])
        return treffer

    @property
    def gefunden(self) -> int:
        """Zahl der Tafeln der derzeit besten Bauart."""
        return max((len(self._treffer(s)) for s in self._stand.values()),
                   default=0)

    @property
    def fertig(self) -> bool:
        return self.gefunden >= self.ziel_anzahl

    def ergebnis(self) -> Erkennung | None:
        """Die beste Bauart mit ihren Tafeln -- oder None."""
        bestes: Erkennung | None = None
        for stand in self._stand.values():
            treffer = self._treffer(stand)
            if not treffer:
                continue
            kandidat = Erkennung(typ=stand["typ"], treffer=treffer)
            if bestes is None or (len(kandidat.treffer), kandidat.merkmale) > \
                    (len(bestes.treffer), bestes.merkmale):
                bestes = kandidat
        if bestes is not None:
            log.info("Laufende Suche: %s, %d Tafeln aus %d Bildern, %d "
                     "tragende Merkmale", bestes.typ.name, len(bestes.treffer),
                     self.bilder_gesehen, bestes.merkmale)
        return bestes


def _kette(bilder: list[np.ndarray], muster: np.ndarray, *, min_inlier: int,
           anker_inlier: int, min_frames: int, max_tafeln: int,
           runden: int) -> list[Treffer]:
    """Jede gefundene Tafel wird selbst zur Vorlage fuer die naechste Runde.

    WARUM DIE KETTE -- gemessen 2026-09-10 an sechs Stellen des Spiels:

        eine Vorlage      3, 3, 3, 3, 0, 4 Tafeln, schwaechster Treffer 13
        Ankerkette        4, 4, 4, 4, 0, 3 Tafeln, schwaechster Treffer 10,
                          tragende Merkmale je Tafel 46 bis 191

    Der Grund liegt am Blickwinkel: Das Overlay ist ein Ausschnitt einer
    echten Kameraaufnahme, die vier Tafeln stehen darin unterschiedlich
    schraeg. Eine Vorlage von der mittleren Tafel passt schlecht zur
    aeussersten rechten -- die wurde fast immer uebersehen. Ihr NACHBAR passt
    dagegen gut. So waechst die Suche von Tafel zu Tafel weiter, statt von
    einer einzigen Stelle aus alles erreichen zu muessen.
    """
    grob = BoardFinder(min_inlier=min_inlier)
    anker: tuple[Treffer, np.ndarray] | None = None
    for bild in bilder:
        for t in grob.finde_alle(bild, [muster], max_tafeln=max_tafeln):
            if anker is None or t.inlier > anker[0].inlier:
                anker = (t, bild)
    if anker is None:
        return []

    fein = BoardFinder(min_inlier=anker_inlier)
    vorlagen = [_ausschnitt(anker[1], anker[0].quad)]
    gruppen: list[list[tuple[Treffer, np.ndarray]]] = []
    benutzt: set[int] = set()
    for _ in range(max(1, runden)):
        vorlagen = [v for v in vorlagen if v is not None and v.size]
        if not vorlagen:
            break
        for bild in bilder:
            for t in fein.finde_alle(bild, vorlagen, max_tafeln=max_tafeln):
                _einsortieren(gruppen, (t, bild))

        # Nur die BESTAETIGTEN Tafeln geben eine neue Vorlage her -- aus einem
        # einzelnen Zufallstreffer eine Vorlage zu schneiden hiesse, den
        # Irrtum zu vervielfaeltigen.
        vorlagen = []
        for i, g in enumerate(gruppen):
            if i in benutzt or len(g) < min_frames:
                continue
            benutzt.add(i)
            t, bild = max(g, key=lambda x: x[0].inlier)
            vorlagen.append(_ausschnitt(bild, t.quad))
        if not vorlagen:
            break

    treffer = [max(g, key=lambda x: x[0].inlier)[0] for g in gruppen
               if len(g) >= min_frames]
    treffer.sort(key=lambda t: _mitte(t.quad)[0])   # von links nach rechts
    return treffer


def _ausschnitt(bild: np.ndarray, quad) -> np.ndarray:
    """Schneidet eine Tafel geradegerechnet aus einem Bild."""
    return entzerre(bild, quad, quad_groesse(quad))


def _einsortieren(gruppen: list[list[tuple[Treffer, np.ndarray]]],
                  neu: tuple[Treffer, np.ndarray],
                  toleranz: float = 0.5) -> None:
    """Legt einen Treffer zu denen an derselben Stelle -- oder eroeffnet neu.

    `toleranz` ist ein Anteil der Tafelgroesse: Zwei Funde gelten als dieselbe
    Tafel, wenn ihre Mitten naeher beieinander liegen als eine halbe
    Tafelbreite. Das ist grosszuegig genug fuer den Schaetzfehler eines
    schwachen Treffers und eng genug, um Nachbartafeln zu trennen -- die
    stehen rund eine ganze Tafelbreite auseinander (gemessen: Mitten bei
    554, 863, 1096, 1392 Pixel bei 159 Pixel Breite).
    """
    mx, my = _mitte(neu[0].quad)
    breite, hoehe = quad_groesse(neu[0].quad)
    for g in gruppen:
        gx, gy = _mitte(g[0][0].quad)
        if abs(mx - gx) < breite * toleranz and abs(my - gy) < hoehe * toleranz:
            g.append(neu)
            return
    gruppen.append([neu])


def _verfeinere(bild: np.ndarray, treffer: list[Treffer],
                finder: BoardFinder, max_tafeln: int) -> list[Treffer]:
    """Zweiter Durchgang mit einer Vorlage aus dem ZIELBILD selbst.

    Das Muster der Bibliothek stammt aus einer anderen Aufnahme -- anderes
    Licht, andere Kamera, anderer Massstab. Sobald der erste Durchgang eine
    Tafel gefunden hat, laesst sich aus dem Zielbild eine Vorlage schneiden,
    die zu allen uebrigen Tafeln desselben Bildes viel besser passt.

    GEMESSEN 2026-09-09, Muster von der Hallenkamera gegen ein Overlay-Video
    einer anderen Kamera: 92 -> 176 tragende Merkmale, und die am
    schlechtesten sitzende Tafel rueckte um 16 Pixel an die richtige Stelle.

    Uebernommen wird nur, was mindestens so viele Tafeln findet UND mehr
    tragende Merkmale hat -- sonst bleibt es beim ersten Durchgang.
    """
    bester = max(treffer, key=lambda t: t.inlier)
    eigene = entzerre(bild, bester.quad, quad_groesse(bester.quad))
    zweite = finder.finde_alle(bild, [eigene], max_tafeln=max_tafeln)
    if (len(zweite) >= len(treffer)
            and sum(t.inlier for t in zweite) > sum(t.inlier for t in treffer)):
        log.debug("Verfeinerung: %d -> %d Tafeln, %d -> %d Merkmale",
                  len(treffer), len(zweite),
                  sum(t.inlier for t in treffer),
                  sum(t.inlier for t in zweite))
        return zweite
    return treffer


def uebernimm(erkennung: Erkennung, nummern: list[int]) -> Calibration:
    """Baut aus einer Erkennung eine vollstaendige Kalibrierung.

    Die ROIs des Typs werden unveraendert uebernommen -- sie liegen in
    normierten Tafelkoordinaten und gelten deshalb fuer jede Tafel dieser
    Bauart, egal wie gross oder schraeg sie im Bild steht.
    """
    if len(nummern) != len(erkennung.treffer):
        raise ValueError(
            f"{len(nummern)} Bahnnummern fuer {len(erkennung.treffer)} Tafeln")

    kal = erkennung.typ.kalibrierung.model_copy(deep=True)
    muster = erkennung.typ.bahn
    bahnen = []
    for i, (t, nummer) in enumerate(zip(erkennung.treffer, nummern), start=1):
        bahn = muster.model_copy(deep=True)
        bahn.lane_id = i                    # Position von links
        bahn.real_lane_number = int(nummer)
        bahn.quad = t.quad
        bahnen.append(bahn)
    kal.lanes = bahnen
    return kal


def speichere_typ(ordner: str | Path, name: str, bild: np.ndarray,
                  kalibrierung: Calibration, lane_id: int | None = None) -> Path:
    """Legt einen neuen Tafeltyp an -- aus einem Bild und einer Kalibrierung.

    Das Musterbild wird in BEOBACHTETER Groesse abgelegt, nicht in einer
    Normgroesse. GEMESSEN: Eine auf 440x530 entzerrte Vorlage gegen eine im
    Bild 192 Pixel grosse Tafel -- Massstabssprung 2,3fach -- fand nur eine
    von vier Tafeln, die uebrigen lagen 160 bis 600 Pixel daneben.
    """
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    bahn = (next(l for l in kalibrierung.lanes if l.lane_id == lane_id)
            if lane_id is not None else kalibrierung.lanes[0])

    muster = entzerre(bild, bahn.quad, quad_groesse(bahn.quad))
    cv2.imwrite(str(ordner / f"{name}{MUSTER_ENDUNG}"), muster)

    nur_eine = kalibrierung.model_copy(deep=True)
    nur_eine.lanes = [bahn.model_copy(deep=True)]
    nur_eine.name = name
    ziel = ordner / f"{name}.json"
    nur_eine.save(ziel)
    log.info("Tafeltyp %s angelegt: Muster %dx%d px", name,
             muster.shape[1], muster.shape[0])
    return ziel
