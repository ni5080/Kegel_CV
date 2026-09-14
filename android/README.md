# Kegel_CV auf dem Telefon

> **Stand: Fundament, noch keine Anwendung.** Dieser Ordner enthält eine App,
> die genau eine Frage beantwortet — läuft der Erkennungskern auf echter
> Hardware, und was kosten die Rechenschritte? Kamera und Bedienung kommen
> danach. Wer zuerst die Oberfläche baut, merkt zu spät, dass das Fundament
> nicht trägt.

## Warum überhaupt eine App

Damit man nicht darauf angewiesen ist, dass die Halle einen Kamerastream
anbietet. Freizeitsport soll dieselbe Erfassung bekommen wie der Profisport.

## Die eine Bedingung: Stativ

Das gesamte Verfahren setzt eine **feste Kamera** voraus, und zwar nicht als
Empfehlung, sondern rechnerisch:

- Die Personenmaske ist ein Hintergrundmodell — bewegt sich die Kamera, ist
  *alles* Vordergrund.
- Das Kalibrierviereck sind feste Bildkoordinaten.
- Die Tafelwache vergleicht dieselben Bildpunkte gegen eine Referenz.

Bei BUG-026 haben **wenige Pixel Versatz** eine Bahn für 13 000 Frames
stillgelegt. Freihändig filmen ist kein „etwas ungenauer", sondern ein anderes
Verfahren. Die App sagt das dem Nutzer, statt es im Kleingedruckten zu
verstecken.

## Was mitwandert — und was nicht

Der gemessene Kern wird **nicht neu geschrieben**. Das ist keine Bequemlichkeit:
Jeder Schwellwert dieses Projekts ist an dieser Implementierung gemessen; eine
zweite Fassung in Kotlin wäre in einem Monat ein zweites Programm mit eigenen
Fehlern.

| kommt mit (Python, unverändert) | wird neu (Kotlin) |
|---|---|
| `detection/`, `analysis/`, `calibration/`, `models/`, `sinks/` | Kamera (CameraX) |
| `config/` samt aller Messwerte | Oberfläche, Tafelsuche-Dialog |
| das Personenmodell | Schreibweg zur Datenbank |

Nicht mit kommt `gui/` (PySide6) und `video/` — beides ersetzt die App.

## Die drei Machbarkeitsfragen (geprüft 2026-09-14)

| Frage | Antwort |
|---|---|
| Gibt es OpenCV für Chaquopy? | Ja — 4.5.1.48 für `cp310`/`arm64`, dazu numpy 1.26 |
| Läuft unser Kern auf OpenCV 4.5? | Ja — keine einzige echte Inkompatibilität |
| Liest OpenCV 4.5 das Personenmodell? | Ja — findet den Menschen am Beweisframe F42228 |

### Der Versionstest gehört wiederholt

Entwickelt wird auf **OpenCV 5.0**, die App läuft auf **4.5.1**. Diese Schere
schließt sich nicht von allein. Bevor eine der beiden Versionen steigt:

```bash
python -m venv /tmp/cv45
/tmp/cv45/Scripts/python.exe -m pip install "opencv-python==4.5.5.64" "numpy<2" pydantic PyYAML pytest
```

```bash
/tmp/cv45/Scripts/python.exe -m pytest tests/unit -q --ignore=tests/unit/test_analyse_sperrt_wiedergabe.py --ignore=tests/unit/test_analysis_worker.py --ignore=tests/unit/test_auto_kalibrieren.py --ignore=tests/unit/test_bahnen_finden_gui.py --ignore=tests/unit/test_livestream_analysestart.py --ignore=tests/unit/test_nachkalibrieren.py --ignore=tests/unit/test_stream_reader.py --ignore=tests/unit/test_ziffern_in_der_anzeige.py
```

Die ausgeschlossenen Dateien brauchen PySide6 — genau die Schicht, die auf dem
Telefon nicht existiert. 4.5.5 statt 4.5.1, weil 4.5.1 keine Räder für Python
3.10 auf Windows hat; die API ist zwischen beiden unverändert.

## Der offene Punkt: pydantic

**pydantic v2 läuft nicht auf Android.** Sein Kern (`pydantic-core`) ist in Rust
geschrieben, und Chaquopy liefert nur reine Python-Pakete plus eigene native
Übersetzungen. Betroffen sind genau zwei Dateien:

- `src/kegel_cv/config/schema.py` — 20 Klassen
- `src/kegel_cv/calibration/model.py` — 4 Klassen

Die benutzte Oberfläche ist überschaubar: `BaseModel`, `Field` mit
Wertebereichen (`ge`/`le`/`gt`/`lt`, `default_factory`), acht Validatoren,
je einmal `model_dump` und `model_validate`.

Solange das nicht gelöst ist, kann die App den Kern **noch nicht importieren** —
der Selbsttest prüft deshalb nur Python, numpy, OpenCV und das Modell.

## Bauen und aufspielen

Voraussetzungen: Android Studio (bringt JDK und SDK mit), ein Gerät mit
USB-Debugging.

```bash
cd android && ./gradlew :app:assembleDebug
```

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Das Personenmodell wird als Asset mitgeliefert und muss vor dem Bauen dort
liegen:

```bash
cp models/yolox_tiny.onnx android/app/src/main/assets/
```

### Xiaomi / HyperOS

`adb install` scheitert dort mit `INSTALL_FAILED_USER_RESTRICTED`. Abhilfe: in
den Entwickleroptionen **„USB-Debugging (Sicherheitseinstellungen)"**
einschalten — das verlangt ein angemeldetes Mi-Konto. Alternativ das APK
aufs Gerät legen und im Dateimanager antippen:

```bash
adb push app/build/outputs/apk/debug/app-debug.apk /sdcard/Download/KegelCV.apk
```

## Warum diese Versionen

| | | warum nicht anders |
|---|---|---|
| Chaquopy | 17.0 | einzige Fassung mit Python 3.10–3.14 **und** AGP bis 9.2 |
| Python | 3.10 | OpenCV liegt bei Chaquopy nur für `cp38` und `cp310` vor |
| OpenCV | 4.5.1.48 | das Neueste in Chaquopys Paketquelle |
| ABI | nur `arm64-v8a` | jede weitere Architektur legt Python, numpy und OpenCV ein zweites Mal ins APK |
| minSdk | 24 | Mindestanforderung von Chaquopy 17 |
