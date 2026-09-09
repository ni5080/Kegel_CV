---
name: kegel-gui
description: >
  PySide6-Oberfläche in Kegel_CV. Laden bei Arbeit an Fenstern, Widgets, Video-Anzeige,
  Kalibrierungs-GUI, Mausinteraktion, ROI-Overlays, Ergebnistabellen, Debug-Ansicht,
  Threading zwischen Analyse und GUI, Signals/Slots oder wenn die Oberfläche hängt,
  flackert oder abstürzt.
---

# GUI (PySide6)

## 1. Fensteraufbau

```
+---------------------------------------------------------------+
| Menü / Toolbar: Video laden | Kalibrieren | Analyse starten    |
+---------------------------------------------------------------+
|                                                               |
|                  VIDEO-ANZEIGE + ROI-Overlays                 |
|                                                               |
+---------------------------------------------------------------+
| [<<] [>] [>>]  Frame 3702 / 12450   t = 148.08 s   [=====---]  |
+---------------------------------------------------------------+
| Bahn 1      | Bahn 2      | Bahn 3      | Bahn 4               |
| Tabelle     | Tabelle     | Tabelle     | Tabelle              |
+---------------------------------------------------------------+
| Debug / Events / erkannte Frames                              |
+---------------------------------------------------------------+
```

## 2. Threading — die wichtigste Regel

> **Qt-Widgets dürfen ausschließlich im GUI-Thread berührt werden.**

Ein Zugriff aus einem Worker-Thread führt nicht zuverlässig zum Absturz — er führt
zu sporadischen, schwer reproduzierbaren Fehlern. Das ist die tückischste
Fehlerklasse in diesem Projekt.

```python
# Falsch -- Worker schreibt direkt ins Widget
class AnalysisWorker(QThread):
    def run(self):
        self.window.table.setItem(...)     # sporadischer Absturz

# Richtig -- Worker sendet Signal, GUI-Thread reagiert
class AnalysisWorker(QThread):
    throw_detected = Signal(object)        # ThrowResult
    def run(self):
        self.throw_detected.emit(result)   # thread-sicher
```

Verbindung im GUI-Thread:
```python
worker.throw_detected.connect(self._on_throw, Qt.QueuedConnection)
```

Signale übertragen **unveränderliche Objekte** (`frozen dataclass`). Ein geteiltes
`np.ndarray` zwischen Threads ist eine Race Condition mit Ansage — Frames werden
für die Anzeige kopiert.

## 3. Video-Anzeige

- Konvertierung BGR nach RGB genau einmal, direkt vor der Anzeige.
- `QImage` braucht den **`bytesPerLine`-Parameter**, sonst zerreißt das Bild bei
  Breiten, die nicht durch 4 teilbar sind:
  ```python
  h, w, ch = rgb.shape
  img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
  ```
- `QImage` kopiert die Daten **nicht**. Das zugrundeliegende Array muss am Leben
  bleiben, solange das Bild angezeigt wird — sonst gibt es Grafikmüll oder Absturz.
  Deshalb: `.copy()` beim Erzeugen des QImage.
- Skalierung mit `Qt.KeepAspectRatio` und `Qt.SmoothTransformation`.

## 4. Koordinaten-Umrechnung bei Mausklicks

Der Nutzer klickt auf ein **skaliertes** Bild, die Kalibrierung braucht
**Originalpixel**. Fehlt diese Umrechnung, liegen alle Eckpunkte falsch — und das
fällt erst viel später auf.

```python
def widget_to_frame(self, pos: QPoint) -> tuple[float, float]:
    # Skalierung UND Zentrier-Offset berücksichtigen
    x = (pos.x() - self._offset_x) / self._scale
    y = (pos.y() - self._offset_y) / self._scale
    return x, y
```

Der Offset entsteht, weil das Bild bei `KeepAspectRatio` mittig im Widget sitzt.
Ihn zu vergessen ist ein klassischer Fehler mit subtiler Wirkung: Klicks stimmen
in der Bildmitte fast, an den Rändern gar nicht.

## 5. Kalibrierungs-Ablauf

```
Video laden -> Frame wählen -> Bahn wählen -> 4 Klicks
   -> Homographie -> entzerrte Vorschau -> ROIs setzen/ziehen -> speichern
```

- Gesetzte Punkte sofort einzeichnen (nummeriert 1–4), damit die Reihenfolge sichtbar ist.
- Letzten Punkt zurücknehmen können (Undo).
- ROIs per Maus verschieb- und skalierbar (Auftrag §13).
- Beim Verlassen ohne Speichern: nachfragen.

## 6. Live-Aktualisierung ohne Ruckeln

Bei 25 fps würde ein Neuaufbau der Tabelle pro Frame die Oberfläche lahmlegen.

- Tabellen nur bei **neuem Wurf** aktualisieren, nicht pro Frame.
- Video-Anzeige über einen `QTimer` entkoppeln (Anzeige-FPS in der Config,
  unabhängig von der Analyse-Geschwindigkeit).
- Zeilen anhängen statt Tabelle neu aufbauen.
- Debug-Log als Ringpuffer mit Obergrenze — sonst wächst der Speicher unbegrenzt.

## 7. Fehler gehören in die Oberfläche

Ein Fehler, der nur in der Konsole steht, existiert für den Nutzer nicht.
Statusleiste plus Debug-Panel zeigen: Videoname, Kalibrierungsname, Analysezustand,
Verarbeitungs-FPS, letzte Warnung.

## 8. Testbarkeit

Logik **niemals** in Widget-Klassen. Ein `QTableWidget` ist eine Darstellung,
kein Modell. Die Zuordnung Wurf zu Tabellenzeile gehört in eine testbare Klasse
ohne Qt-Import — sonst braucht jeder Test eine `QApplication`.

```
gui/result_table.py       -> nur Darstellung
analysis/lane_tracker.py  -> die Logik, ohne Qt, voll testbar
```
