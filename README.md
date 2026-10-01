# Pan Badek AI 🤖

Własna, mała sztuczna inteligencja napisana **od zera w czystym Pythonie**:
bez numpy, bez PyTorcha i bez płatnych API. Sercem jest samodzielnie
zaimplementowana sieć neuronowa z propagacją wsteczną. Do tego dochodzą dostęp do
internetu, własne biblioteki wiedzy i wtyczki.

## 📱 Na telefonie - najprościej

**Otwórz w telefonie: https://panbadek.github.io/Pan-Badek-ai/**

Potem w menu przeglądarki wybierz **„Dodaj do ekranu głównego”** (Android: Chrome ⋮,
iPhone: Safari → Udostępnij). Nic nie trzeba instalować ani mieć włączonego komputera:
cały Pan Badek (Python!) działa w przeglądarce telefonu dzięki
[Pyodide](https://pyodide.org), a po pierwszym otwarciu działa też bez internetu.

W ⚙️ wybierasz, jak mocny ma być mózg:

| Mózg | Co daje | Koszt |
|---|---|---|
| **Pan Badek** | polecenia, pamięć, Wikipedia, pogoda, kursy, kalkulator, analiza zdjęć | darmowy |
| **Rozpoznawanie obiektów** (MobileCLIP, 23 MB) | „🤖 AI rozpoznaje: kot 88%”: 180 kategorii, liczone w telefonie | darmowy |
| **Model AI w telefonie** (Qwen3.5 0,8B / 2B / 4B, WebLLM) | swobodna rozmowa po polsku na GPU telefonu, prywatnie i offline | darmowy, pobierany raz |
| **Claude** (Claude Opus 5.5) | najmocniejszy: rozmowa i dokładny opis zdjęć | własny klucz API, płatny za użycie |

Model AI w telefonie wymaga WebGPU: aktualny Chrome na Androidzie albo Safari na iOS 26+,
najlepiej 6 GB RAM lub więcej dla wersji 2B. Klucz API do Claude zostaje tylko w twoim telefonie.

> **Jednorazowo, żeby strona ruszyła:** w repozytorium na GitHubie wejdź w
> **Settings → Pages → Build and deployment → Source: GitHub Actions**. Od tej pory każda zmiana
> w kodzie sama aktualizuje stronę (workflow `.github/workflows/strona.yml`).
> Lokalnie stronę zbudujesz poleceniem `python3 narzedzia/zbuduj_strone.py _site`.

## Uruchomienie na komputerze

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
| Analiza zdjęć 📷 | przycisk 📷 w czacie, potem `to jest kot` |
| Kalkulator | `ile to 12*7+3`, `sqrt(16) + 2^3`, `5 razy 4` |
| Pamięć | `mam na imię Ania`, `jak mam na imię?` |
| Godzina i data | `która godzina`, `jaki dziś dzień` |

🌐 wymaga internetu. Wszystkie usługi są darmowe i nie potrzebują kluczy API.

### Samodzielna nauka 🧠

Pan Badek uczy się z każdej rozmowy:

- **Od mocniejszych AI:** gdy odpowiada Claude albo model w telefonie, Badek zapamiętuje pytanie
  i odpowiedź. Na podobne pytanie odpowie potem sam, bez internetu i za darmo
  („zapamiętałem od: Claude”).
- **Z twoich ocen:** 👍/👎 przy odpowiedziach (albo słowa „źle”, „dobra odpowiedź”). Złą odpowiedź
  zapomina, a ocenione zdania dopisuje do przykładów treningowych i od razu douczą sieć.
- **Z lekcji:** `naucz się: pytanie => odpowiedź`, `zapamiętaj, że mój pies ma na imię Burek`.
- **`ucz się`** porządkuje wiedzę, trenuje sieć od nowa, mierzy jej dokładność i mówi,
  o co najczęściej pytano, a on nie wiedział. Do tego `statystyki` i `czego nie wiesz`.
- **Ze wszystkich urządzeń:** w ⚙️ zapiszesz kopię pamięci i wczytasz ją na innym telefonie
  albo komputerze (`python3 -m panbadek --eksport pamiec.json` / `--import pamiec.json`).
  Wiedza się łączy, nic nie ginie.

Na start zna 143 odpowiedzi z wiedzy ogólnej (geografia, historia Polski, nauka, przyroda, kosmos).
Jakość sieci mierzy `python3 narzedzia/ocen_siec.py` na zdaniach, których nie widziała przy
treningu: obecnie ok. 97%.

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

### Analiza zdjęć 📷

W czacie (przeglądarka, telefon, aplikacja) naciśnij 📷 i wybierz zdjęcie. Pan Badek opisze:

- **kolory** dominujące z udziałami, np. „niebieski 61%, brązowy 27%” (algorytm k-średnich),
- **światło**: jasność, kontrast, nasycenie, barwy ciepłe lub chłodne,
- **ostrość**: ostre, lekko miękkie albo rozmyte (rozmyte tło portretu nie obniża oceny),
- **co widzi**: ostrożne domysły, np. niebo, zieleń, noc, zachód słońca, dokument lub zrzut ekranu,
- **metadane EXIF**: datę, telefon i miejsce z linkiem do mapy (o ile zdjęcie je zawiera).

Po analizie napisz **„to jest kot”**, a Badek zapamięta przykład i następnym razem powie
„Przypomina mi: kot”. Rozpoznaje po kolorach i ich układzie, a nie po kształtach, więc
najlepiej działa na podobnych ujęciach (ten sam pies, ten sam pokój, ten sam widok z okna).
Im więcej przykładów, tym lepiej. `jakie zdjęcia znasz` pokazuje, czego się nauczył.

W terminalu: `przeanalizuj zdjęcie ~/Obrazy/zdjecie.png`. PNG Badek czyta sam, a JPEG po
zainstalowaniu Pillow (`pip install pillow`). Zdjęcie nigdzie nie jest wysyłane: wszystko
liczy się na twoim urządzeniu.

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
