# Pan Badek AI 🤖

Własna, mała sztuczna inteligencja napisana **od zera w czystym Pythonie**:
bez numpy, bez PyTorcha i bez płatnych API. Sercem jest samodzielnie
zaimplementowana sieć neuronowa z propagacją wsteczną. Do tego dochodzą dostęp do
internetu, własne biblioteki wiedzy i wtyczki.

## Uruchomienie

Wymagany jest tylko Python 3.8+.

```bash
python3 -m panbadek            # rozmowa w terminalu
python3 -m panbadek --web      # rozmowa w przeglądarce: http://127.0.0.1:8000
python3 -m panbadek --skrot    # ikona Pana Badka na pulpicie
python3 -m panbadek --offline  # bez internetu
python3 -m panbadek --debug    # pokazuje, co „myśli” sieć (intencja + pewność)
```

## Aplikacja na Androida (APK) 📱

Pan Badek działa też jako zwykła aplikacja na telefonie, bez komputera i bez Termuksa.
W środku jest ten sam Python i ten sam mózg (dzięki [Chaquopy](https://chaquo.com/chaquopy/)),
a czat wyświetla się w oknie aplikacji.

**Instalacja:**
1. Pobierz plik `app-release.apk` na telefon (z GitHub Actions: zakładka *Actions* →
   *Buduj APK* → najnowsze uruchomienie → *Artifacts*).
2. Otwórz go. Android zapyta o zgodę na instalację z nieznanego źródła; zezwól na nią
   dla przeglądarki albo menedżera plików.
3. Na ekranie głównym pojawi się ikona **Pan Badek**.

Pierwsze uruchomienie trwa kilka sekund, bo sieć neuronowa trenuje się na telefonie. Kolejne są
szybsze. Pamięć Badka (imię, biblioteki, nauczone odpowiedzi) zostaje w telefonie.

**Budowanie samemu** (wymaga JDK 17+ i Android SDK, np. z Android Studio):

```bash
cd android
./gradlew assembleRelease
# gotowy plik: android/app/build/outputs/apk/release/app-release.apk
```

Bez dodatkowej konfiguracji APK jest podpisywane kluczem debug. Wystarczy to do instalacji
na własnym telefonie, ale aktualizacje trzeba budować na tym samym komputerze, bo inaczej
Android każe najpierw odinstalować starą wersję. Własny klucz ustawisz zmiennymi
`PANBADEK_KEYSTORE`, `PANBADEK_KEYSTORE_PASSWORD`, `PANBADEK_KEY_ALIAS`, `PANBADEK_KEY_PASSWORD`.
Ikony aplikacji generuje `python3 android/generuj_ikony.py`.

## Skrót na ekranie głównym 📱 / pulpicie 🖥️

**Komputer (Windows, macOS, Linux):**

```bash
python3 -m panbadek --skrot
```

Na pulpicie pojawi się ikona **Pan Badek**. Kliknięcie uruchamia Badka i otwiera czat w przeglądarce.
Jeśli Badek już działa, skrót tylko otwiera okno. Możesz też wskazać inny katalog:
`--skrot ŚCIEŻKA`.

**Telefon (Android i iPhone):** Pan Badek działa na komputerze, a telefon łączy się z nim przez Wi-Fi.

1. Na komputerze uruchom: `python3 -m panbadek --web --telefon`
2. Program wypisze adres, np. `http://192.168.1.20:8000`. Otwórz go na telefonie
   (telefon musi być w tej samej sieci Wi-Fi).
3. **Android (Chrome):** menu ⋮ → „Dodaj do ekranu głównego”.
   **iPhone (Safari):** przycisk Udostępnij → „Do ekranu początkowego”.

Na ekranie głównym pojawi się ikona robota. Czat otwiera się jak osobna aplikacja, na pełnym
ekranie. Uwaga: z `--telefon` każdy w twojej sieci Wi-Fi może rozmawiać z Badkiem, więc używaj
tego w domu, nie w publicznej sieci.

Możesz też zainstalować Pana Badka jako polecenie `panbadek`:

```bash
pip install .
panbadek --web
```

## Co potrafi

| Umiejętność | Przykład |
|---|---|
| Rozmowa (sieć neuronowa) | `cześć`, `kim jesteś`, `opowiedz żart` |
| Wikipedia 🌐 | `co to jest fotosynteza`, potem `więcej` |
| Pogoda 🌐 (Open-Meteo) | `pogoda w Krakowie`, `mieszkam w Gdańsku` → `jaka pogoda?` |
| Kursy walut 🌐 (NBP) | `kurs euro`, `ile kosztuje dolar` |
| Biblioteki wiedzy 📚 | `stwórz bibliotekę o Koperniku`, `stwórz bibliotekę przepisy` |
| Wtyczki w Pythonie 🔌 | `stwórz wtyczkę kostka`, `przeładuj wtyczki` |
| Nauka | `naucz się: pytanie => odpowiedź`, `zapomnij: pytanie` |
| Kalkulator | `ile to 12*7+3`, `sqrt(16) + 2^3`, `5 razy 4` |
| Pamięć | `mam na imię Ania`, `jak mam na imię?` |
| Godzina i data | `która godzina`, `jaki dziś dzień` |

🌐 wymaga internetu. Wszystkie usługi są darmowe i nie potrzebują kluczy API.

### Biblioteki wiedzy 📚

Biblioteka to nazwany zbiór faktów, który Pan Badek przeszukuje jak mała wyszukiwarka
(cechy słów ważone rzadkością, czyli TF-IDF, i podobieństwo kosinusowe).

- `stwórz bibliotekę o Koperniku`: Pan Badek czyta cały artykuł z Wikipedii, dzieli go
  na zdania i zapisuje jako bibliotekę. **Potem odpowiada na pytania o ten temat także bez internetu.**
- `stwórz bibliotekę przepisy`, a potem `dodaj do przepisy: Na naleśniki potrzeba mąki, mleka i jajek.`
  tworzy twoją własną bazę wiedzy.
- `pokaż biblioteki`, `usuń bibliotekę przepisy`.
- Wszystko, czego Pan Badek dowie się z Wikipedii przez `co to jest ...`, trafia do biblioteki
  „Internet”, więc pamięta to na później.

### Wtyczki 🔌

`stwórz wtyczkę kostka` tworzy plik `~/.panbadek/wtyczki/kostka.py` z gotowym szablonem.
Wystarczy uzupełnić funkcję:

```python
import random

def obsluz(tekst, badek):
    if "rzuć kostką" in tekst.lower():
        return f"Wypadło {random.randint(1, 6)}!"
    return None  # ta wiadomość nie dotyczy tej wtyczki
```

i napisać `przeładuj wtyczki`. Wtyczka ma dostęp do całego Pana Badka (`badek.imie`,
`badek.biblioteki`, `badek.odpowiedz(...)`). Zepsuta wtyczka nie wywróci programu, tylko
zgłosi błąd. **Uwaga:** wtyczki to zwykły kod Pythona, więc wrzucaj tam tylko pliki, którym ufasz.

## Jak to działa

1. **Tekst → wektor** (`text.py`): normalizacja (małe litery, bez polskich znaków) i cechy:
   rdzenie słów (odporność na odmianę) oraz trigramy znakowe (odporność na literówki).
2. **Sieć neuronowa** (`network.py`): wejście → 32 neurony ReLU → softmax; uczenie spadkiem
   gradientu z entropią krzyżową. Gradienty są liczone ręcznie.
3. **Mózg** (`brain.py`) przepuszcza wiadomość przez kolejne etapy: polecenia pamięci →
   biblioteki → wtyczki → internet → kalkulator → sieć neuronowa → przeszukanie bibliotek.
   Sieć odpowiada tylko wtedy, gdy jest pewna (≥ 45%) i rozpoznaje słowa ze zdania,
   dzięki czemu nie „strzela” na zupełnie obcych pytaniach.
4. **Internet** (`internet.py`): Wikipedia, Open-Meteo i NBP przez `urllib`, z limitem czasu
   i ponowieniem przy zerwanym połączeniu.

Cała pamięć (wytrenowany model, nauczone odpowiedzi, biblioteki, wtyczki) leży w `~/.panbadek/`.

## Rozwijanie

Nowe tematy rozmów dodajesz w `panbadek/data/intencje.json`. Model przetrenuje się sam
przy następnym uruchomieniu.

```json
{
  "nazwa": "hobby",
  "przyklady": ["jakie masz hobby", "co lubisz robić", "czym się interesujesz"],
  "odpowiedzi": ["Uwielbiam czytać Wikipedię i liczyć gradienty!"]
}
```

## Testy

```bash
python3 -m unittest discover -s tests -v
```

Testy nie łączą się z internetem: odpowiedzi serwerów są symulowane.
