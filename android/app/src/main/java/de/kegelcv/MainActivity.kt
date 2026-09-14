package de.kegelcv

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import kotlin.concurrent.thread

/**
 * Erster Stand: beweist die Kette, baut noch keine Anwendung.
 *
 * Die Frage, die dieser Bildschirm beantwortet, ist die einzige, an der das
 * ganze Vorhaben haette scheitern koennen: Laeuft der Erkennungskern -- Python,
 * numpy, OpenCV, das Personenmodell -- auf einem Telefon, und was kosten die
 * Schritte, die spaeter in jedem Frame stecken?
 *
 * Kamera und Bedienung kommen danach. Wer zuerst die Oberflaeche baut, merkt
 * zu spaet, dass das Fundament nicht traegt.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var ausgabe: TextView

    /** Ablage der Modellkandidaten waehrend der Erprobung (siehe unten). */
    private val modellordner = File("/sdcard/Download/kegelmodelle")

    override fun onCreate(zustand: Bundle?) {
        super.onCreate(zustand)
        setContentView(R.layout.activity_main)
        ausgabe = findViewById(R.id.ausgabe)
        findViewById<Button>(R.id.knopf_selbsttest).setOnClickListener {
            starteSelbsttest()
        }

        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        // Ohne Knopfdruck loslaufen: Ein Test, den man erst antippen muss,
        // laeuft bei einer Fernpruefung ueber `adb` gar nicht -- MIUI
        // verweigert das Einspielen von Eingaben.
        starteSelbsttest()
    }

    /**
     * Das Personenmodell liegt als Asset im APK und muss als Datei vorliegen,
     * bevor OpenCV es lesen kann: `cv2.dnn.readNet` nimmt einen Pfad, keinen
     * Datenstrom.
     */
    private fun modellBereitstellen(): String {
        val ziel = File(filesDir, "yolox_tiny.onnx")
        if (ziel.exists() && ziel.length() > 0) return ziel.absolutePath
        return runCatching {
            assets.open("yolox_tiny.onnx").use { quelle ->
                ziel.outputStream().use { quelle.copyTo(it) }
            }
            ziel.absolutePath
        }.getOrElse {
            Log.w("KegelCV", "Modell nicht entpackt", it)
            ""
        }
    }

    private fun starteSelbsttest() {
        ausgabe.text = "laeuft ..."
        thread {
            val pfad = modellBereitstellen()
            val py = Python.getInstance()
            val text = runCatching {
                val kern = py.getModule("selbsttest")
                    .callAttr("selbsttest", pfad).toString()
                // Solange nicht feststeht, welches Modell das OpenCV DIESES
                // Geraets lesen kann, wird reihum geprueft. YOLOX-Tiny laedt
                // auf 5.0 und auf 4.5.5, scheitert aber auf dem Geraet an
                // 4.5.1 -- die Kandidaten liegen deshalb zum Durchprobieren
                // in `modellordner`. Faellt der Ordner weg, entfaellt der Teil.
                if (modellordner.isDirectory) {
                    val weitere = py.getModule("modelltest")
                        .callAttr("pruefe", modellordner.absolutePath).toString()
                    listOf(kern, "", weitere).joinToString(System.lineSeparator())
                } else {
                    kern
                }
            }.getOrElse {
                "Fehlgeschlagen: " + it::class.java.simpleName +
                    System.lineSeparator() + it.message
            }
            // Auch ins Protokoll: So laesst sich das Ergebnis ueber `adb
            // logcat` ablesen, ohne das Telefon in die Hand zu nehmen.
            Log.i("KegelCV", "SELBSTTEST" + System.lineSeparator() + text)
            runOnUiThread { ausgabe.text = text }
        }
    }
}
