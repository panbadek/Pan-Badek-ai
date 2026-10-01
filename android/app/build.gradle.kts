plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

// Wersja aplikacji pochodzi z panbadek/__init__.py, żeby była jedna w całym projekcie.
val pakietPython = rootProject.projectDir.resolve("../panbadek")
val wersja = Regex("__version__ = \"([0-9.]+)\"")
    .find(pakietPython.resolve("__init__.py").readText())!!.groupValues[1]
val (glowna, poboczna, poprawka) = wersja.split(".").map { it.toInt() }

android {
    namespace = "pl.panbadek.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "pl.panbadek.app"
        minSdk = 24
        targetSdk = 35
        versionCode = glowna * 10000 + poboczna * 100 + poprawka
        versionName = wersja
        ndk {
            abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64")
        }
    }

    // Własny klucz podpisu można podać przez zmienne środowiskowe (np. w GitHub Actions).
    // Bez nich wydanie podpisywane jest kluczem debug - wystarczy do instalacji na telefonie.
    val plikKlucza = System.getenv("PANBADEK_KEYSTORE")
    signingConfigs {
        if (plikKlucza != null) {
            create("wydanie") {
                storeFile = file(plikKlucza)
                storePassword = System.getenv("PANBADEK_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("PANBADEK_KEY_ALIAS")
                keyPassword = System.getenv("PANBADEK_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("wydanie") ?: signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

// Kod Pana Badka kopiujemy z głównego katalogu repozytorium, żeby był jeden.
val kopiujPanaBadka by tasks.registering(Sync::class) {
    from(pakietPython) {
        exclude("**/__pycache__/**")
    }
    into(layout.buildDirectory.dir("kod-pana-badka/panbadek"))
}

chaquopy {
    defaultConfig {
        version = "3.11"
    }
    sourceSets {
        getByName("main") {
            srcDir(layout.buildDirectory.dir("kod-pana-badka"))
        }
    }
}

tasks.named("preBuild") {
    dependsOn(kopiujPanaBadka)
}
tasks.matching { it.name.startsWith("merge") && it.name.endsWith("PythonSources") }.configureEach {
    dependsOn(kopiujPanaBadka)
}
