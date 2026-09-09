---
name: kegel-video-pipeline
description: >
  Videoquellen, Frame-Handling und Performance in Kegel_CV. Laden bei Arbeit an
  VideoSource, FileVideoSource, StreamVideoSource, Seeking, FPS, Timestamps,
  Frame-Nummern, Dropframes, Decoding, Ressourcenfreigabe oder wenn die Analyse
  Frames konsumiert. Enthält die gemessenen Eigenschaften des Quellmaterials.
---

# Video-Pipeline

## 1. Quellmaterial (gemessen)

| Eigenschaft | Wert |
|---|---|
| Auflösung | 1920 × 1080 |
| FPS | 25.00 (konstant, alle Clips) |
| Codec | h264 |
| Sessions | `2024-09-03` (9 Clips, 13–30 s) · `2026-08-22` (2 Clips, einer ~2,3 GB) |

Bei 25 fps ⇒ **40 ms pro Frame**. Das ist das Echtzeit-Budget.

## 2. Die Abstraktion

```python
class VideoSource(ABC):
    @abstractmethod
    def open(self) -> None: ...
    @abstractmethod
    def read(self) -> Frame | None: ...   # None = Ende
    @abstractmethod
    def close(self) -> None: ...
    @property
    @abstractmethod
    def info(self) -> VideoInfo: ...      # width, height, fps, frame_count, source_id
```

`FileVideoSource` heute, `StreamVideoSource` später. **Die Analyse darf niemals
wissen, woher die Frames kommen.** Konkret verboten in `analysis/` und `detection/`:
`cv2.VideoCapture`, Dateipfade, `frame_count` als Abbruchbedingung.

### Warum `Frame` ein eigenes Objekt ist

```python
@dataclass(frozen=True)
class Frame:
    index: int          # 0-basierte Frame-Nummer der Quelle
    timestamp: float    # Sekunden seit Start
    image: np.ndarray   # BGR, nicht kopiert
```

Ein nacktes `np.ndarray` verliert die Zeitinformation — und die brauchen wir für
jede Debug-Ausgabe und jedes Ergebnis. Bei Streams gibt es kein `frame_count` und
kein zuverlässiges Seeking; nur `index` und `timestamp` sind universell.

## 3. Sequenziell lesen — Seeking ist teuer

```python
# Analyse: sequenziell
while (frame := source.read()) is not None:
    process(frame)
```

Nicht in der Analyse verwenden: `cap.set(cv2.CAP_PROP_POS_FRAMES, n)`.

h264 ist ein Inter-Frame-Codec: ein Seek springt zum nächsten Keyframe und dekodiert
vorwärts. Das ist langsam **und** ungenau (OpenCV landet je nach Build ein paar
Frames daneben). Seeking ist ausschließlich in der GUI-Navigation erlaubt
(Slider, Frame-Step) — dort ist es interaktiv gewollt.

Deshalb existiert `FrameBuffer`: Für Frame-Sampling rund um ein Ereignis werden die
letzten *N* Frames **im Speicher vorgehalten**, statt zurückzuspringen.

```
        +-- Ringpuffer der letzten N Frames --+
   ...  | f-4  f-3  f-2  f-1  f_aktuell       |  -> bei Trigger sofort verfügbar
        +-------------------------------------+
```

Speicherbedarf: 1920×1080×3 B ≈ 6 MB/Frame. Bei N=50 ⇒ ~300 MB.
⇒ Puffergröße gehört in die Config und muss bewusst klein gehalten werden.
Für lange Videos ggf. nur die **Overlay-Region** puffern (~1 MB/Frame).

## 4. Timestamps

`timestamp = index / fps` — **nicht** `cap.get(CAP_PROP_POS_MSEC)`.
Grund: `POS_MSEC` ist bei manchen h264-Dateien unzuverlässig und nach einem Seek
teils inkonsistent. Die Frame-Nummer ist die belastbare Größe, FPS ist konstant
gemessen. Bei variabler Framerate (Stream) muss das später neu bewertet werden —
dann die quelleneigenen PTS verwenden.

## 5. Dropframes und Robustheit

`read()` kann einzelne Frames nicht liefern, ohne dass das Video zu Ende ist.
Behandlung:

- Fehlgeschlagenes `read()` **zählt trotzdem den Index hoch** (sonst driftet die Zeit).
- Mehr als `max_consecutive_read_failures` hintereinander ⇒ Quelle als beendet werten.
- Der Vorfall wird geloggt (`WARNING`), bricht die Analyse aber nicht ab.

## 6. Ressourcen

`VideoSource` implementiert `__enter__` und `__exit__`. Ein nicht geschlossenes
`VideoCapture` hält den Datei-Handle — unter Windows blockiert das anschließend das
Verschieben oder Löschen der Datei. In der GUI: beim Laden eines neuen Videos immer
erst die alte Quelle schließen.

## 7. Performance messen

`PerformanceMonitor` läuft von Anfang an mit und liefert:

```
Video FPS: 25.0 | Processing FPS: 21.4 | Ø 46 ms/Frame
  Lane 1: 2.1 ms   Lane 2: 1.9 ms   Lane 3: 2.0 ms   Lane 4: 2.2 ms
```

Nicht optimieren ohne Messwert. Die häufigsten realen Kosten in dieser Pipeline:
Decoding (unvermeidbar) vor Farbraumkonvertierung ganzer Frames (vermeidbar!) vor
ROI-Analyse.
