package de.kegelcv

import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
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
 * numpy, OpenCV, das Personenmodell -- auf einem Telefon, und wie teuer sind
 * die Schritte, die spaeter in jedem Frame stecken?
 *
 * Kamera und Oberflaeche kommen erst danach. Wer zuerst die Oberflaeche baut,
 * merkt zu spaet, dass das Fundament nicht traegt.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var ausgabe: TextView

    override fun onCreate(zustand: Bundle?) {
        super.onCreate(zustand)

        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }

        val knopf = Button(this).apply {
            text = "Selbsttest starten"
            setOnClickListener { starteSelbsttest() }
        }
        ausgabe = TextView(this).apply {
            text = "Bereit."
            textSize = 13f
            setPadding(24, 24, 24, 24)
            typeface = android.graphics.Typeface.MONOSPACE
        }

        val spalte = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(24, 48, 24, 24)
            addView(knopf)
            addView(ausgabe)
        }
        setContentView(ScrollView(this).apply { addView(spalte) })

        modellBereitstellen()
    }

    /**
     * Das Personenmodell liegt als Asset im APK und muss als Datei vorliegen,
     * bevor OpenCV es lesen kann -- `cv2.dnn.readNet` nimmt einen Pfad, keinen
     * Datenstrom.
     */
    private fun modellBereitstellen() {
        val ziel = File(filesDir, "yolox_tiny.onnx")
        if (ziel.exists() && ziel.length() > 0) return
        thread {
            runCatching {
                assets.open("yolox_tiny.onnx").use { quelle ->
                    ziel.outputStream().use { quelle.copyTo(it) }
                }
            }.onFailure { Log.w("KegelCV", "Modell nicht entpackt", it) }
        }
    }

    private fun starteSelbsttest() {
        ausgabe.text = "laeuft ..."
        thread {
            val text = runCatching {
                Python.getInstance()
                    .getModule("selbsttest")
                    .callAttr("selbsttest")
                    .toString()
            }.getOrElse { "Fehlgeschlagen:\n${it.message}" }
            runOnUiThread { ausgabe.text = text }
        }
    }
}
