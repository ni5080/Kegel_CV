plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "de.kegelcv"
    compileSdk = 36

    defaultConfig {
        applicationId = "de.kegelcv"
        // Chaquopy 17 verlangt mindestens 24.
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"

        ndk {
            // NUR arm64. Jede weitere Architektur zieht eine eigene Kopie von
            // Python, numpy und OpenCV ins APK -- das sind je rund 40 MB fuer
            // Geraete, die es seit Jahren nicht mehr gibt.
            abiFilters += listOf("arm64-v8a")
        }

    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

// Chaquopy wird in der Kotlin-Fassung ueber einen eigenen Block eingestellt,
// nicht ueber `android.defaultConfig`.
chaquopy {
    defaultConfig {
        // 3.10 ist nicht beliebig gewaehlt: OpenCV liegt in Chaquopys
        // Paketquelle nur fuer cp38 und cp310 vor -- und 3.10 ist zugleich die
        // Version, auf der das Projekt entwickelt wird.
        version = "3.10"

        pip {
            // OpenCV 4.5.1 ist das Neueste, was Chaquopy anbietet; das Projekt
            // selbst laeuft auf 5.0. Der Qt-freie Kern wurde am 2026-09-14
            // gegen 4.5 geprueft und lief ohne eine einzige echte Abweichung.
            // Siehe android/README.md -- dieser Test gehoert wiederholt, bevor
            // eine dieser Versionen steigt.
            install("opencv-python==4.5.1.48")
            install("numpy==1.26.2")
            install("pyyaml==6.0.3")
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
}
