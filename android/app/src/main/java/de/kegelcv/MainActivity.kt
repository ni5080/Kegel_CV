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
     *
     * Es ist die UMGEBAUTE Fassung (`tools/modell_fuer_android.py`): Das
     * Original scheitert am ONNX-Leser von OpenCV 4.5.1, weil seine
     * Focus-Schicht mit Schrittweite 2 abtastet. Der Umbau ersetzt sie durch
     * eine gleichwertige Faltung -- bewiesen, nicht gehofft: Die Ausgaben
     * beider Netze sind auf dem Entwicklungsrechner bitgleich.
     */
    private fun modellBereitstellen(): String = auspacken("yolox_tiny_android.onnx")

    /** Legt ein Asset als Datei ab und gibt seinen Pfad zurueck. */
    private fun auspacken(name: String): String {
        val ziel = File(filesDir, name)
        if (ziel.exists() && ziel.length() > 0) return ziel.absolutePath
        return runCatching {
            assets.open(name).use { quelle ->
                ziel.outputStream().use { quelle.copyTo(it) }
            }
            ziel.absolutePath
        }.getOrElse {
            Log.w("KegelCV", "Asset nicht entpackt: " + name, it)
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
                val konfig = auspacken("default.yaml")
                val kernmodule = py.getModule("selbsttest")
                    .callAttr("kern", konfig).toString()
                listOf(kern, "", "Erkennungskern:", kernmodule)
                    .joinToString(System.lineSeparator())
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
