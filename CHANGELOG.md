# Historia zmian

## 0.7.0

### Samodzielna nauka
- **Baza wiedzy** (`panbadek/wiedza.py`): pary pytanie-odpowiedź wyszukiwane po podobieństwie
  (TF-IDF). Na start dostaje 143 pytania z wiedzy ogólnej (geografia, historia Polski, nauka,
  przyroda, kosmos, technika, kalendarz), dostępne także offline.
- **Nauka od dużych modeli:** każda odpowiedź Claude albo modelu w telefonie trafia do bazy
  wiedzy. Na podobne pytanie Badek odpowiada potem sam, offline i za darmo („zapamiętałem od: Claude”).
- **Oceny 👍/👎** (przyciski w aplikacji albo słowa „źle” / „dobra odpowiedź”): zła odpowiedź
  z bazy wiedzy jest usuwana, a ocena odpowiedzi sieci staje się nowym przykładem treningowym.
  Sieć douczana jest od razu, bez trenowania od zera, i zachowuje dotychczasową wiedzę.
- **„zapamiętaj, że …”** zapisuje notatki (biblioteka „Moje notatki”, z zamianą „mój” → „twój”).
- **„ucz się”** porządkuje wiedzę, trenuje sieć od zera, mierzy dokładność i pokazuje pytania,
  na które Badek najczęściej nie znał odpowiedzi. Do tego **„statystyki”** i **„czego nie wiesz”**.
- **Dziennik rozmów** (ostatnie 3000 wiadomości) służy do wyszukiwania luk w wiedzy.
- **Kopia pamięci**: eksport i import całej wyuczonej pamięci (aplikacja: ⚙️, terminal:
  `--eksport` / `--import`), żeby łączyć wiedzę z telefonu, komputera i innych przeglądarek.
- „naucz się: …” trafia teraz do bazy wiedzy, zamiast dokładać klasę do sieci i trenować ją od zera.
  Lekcje ze starszych wersji są przenoszone automatycznie.

### Trening i jakość
- Dane treningowe: 24 tematy i ponad 350 przykładów (wcześniej 12 tematów, ok. 100 przykładów).
  Doszła klasa „inne”, dzięki której sieć nie przejmuje pytań o wiedzę
  (np. „ile godzin śpią koty” to już nie pytanie o godzinę).
- Zestaw testowy 101 zdań, których sieć nie widzi przy treningu (`narzedzia/ocen_siec.py`):
  **ok. 97% trafień** (średnia z 5 losowań wag). Sieć ma 48 neuronów ukrytych.
- Lepsze rdzeniowanie słów („żyją” = „żyje”, „koty” = „kot”). Nieznane słowa obniżają trafność
  wyszukiwania, więc „stolica Niemiec” nie myli się już ze „stolicą Francji”.
- Twoje notatki i lekcje mają pierwszeństwo przed siecią, a „co to jest / kim był” najpierw
  sprawdza własną wiedzę, potem dopiero Wikipedię.
- Naprawiony błąd w aplikacji: odpowiedź mogła trafić nie do tego zapytania (kolizja pola `id`).

## 0.6.0

### Nowe
- **Pan Badek jako aplikacja w przeglądarce telefonu** (GitHub Pages, PWA): cały Python
  Pana Badka działa przez Pyodide w Web Workerze, bez serwera i bez instalacji. Pamięć jest
  trzymana w IndexedDB, a po pierwszym otwarciu aplikacja działa offline.
- **Rozpoznawanie obiektów na zdjęciach**: MobileCLIP (Transformers.js) w telefonie,
  180 kategorii z polskimi nazwami. Opisy kategorii są przeliczone z góry (`web/etykiety.json`),
  więc telefon pobiera tylko 23-megabajtowy model obrazu.
- **Model językowy w telefonie**: Qwen3.5 0,8B / 2B / 4B przez WebLLM (WebGPU).
- **Tryb Claude** (Claude Opus 5.5 przez oficjalne SDK, z kluczem API użytkownika):
  strumieniowane odpowiedzi, opis zdjęć, automatyczny model zapasowy przy odmowie.
- Mózg zgłasza, która część odpowiedziała (`PanBadek.zrodlo`), żeby rozmowę mógł przejąć model AI.
- Internet działa też w przeglądarce (XMLHttpRequest w Pyodide, CORS dla Wikipedii).
- Gotowa, wytrenowana sieć jest dołączana do strony, więc telefon nie trenuje jej sam.

## 0.5.0

### Nowe
- **Analiza zdjęć** (przycisk 📷 w czacie, w aplikacji na Androida i w przeglądarce): dominujące
  kolory (k-średnie, polskie nazwy), jasność, kontrast, nasycenie, temperatura barw, ostrość
  (wariancja laplasjanu w najostrzejszym fragmencie) i ostrożne domysły (niebo, zieleń, noc,
  zachód słońca, dokument lub zrzut ekranu, ludzie, zwierzęta).
- **Metadane EXIF**: data zrobienia, telefon lub aparat, miejsce z linkiem do mapy.
- **Uczenie się zdjęć**: „to jest …” po zdjęciu zapamiętuje przykład, a podobne zdjęcia
  są potem rozpoznawane. Dodane też „jakie zdjęcia znasz”, „zapomnij zdjęcia”.
- W terminalu: `przeanalizuj zdjęcie ścieżka.png`, z własnym dekoderem PNG.
  JPEG i inne formaty są obsługiwane, gdy zainstalowany jest Pillow.

## 0.4.0

### Nowe
- **Aplikacja na Androida (APK)**: Python wbudowany przez Chaquopy, czat w WebView, działa
  bez komputera. Ma ikonę adaptacyjną robota, ekran ładowania, a linki otwiera w przeglądarce.
  Pamięć jest trzymana w telefonie.
- Automatyczne budowanie APK w GitHub Actions (`.github/workflows/apk.yml`).
- Ikona z przezroczystym tłem i skalowaniem (warstwa ikony adaptacyjnej).

## 0.3.0

### Nowe
- **Skrót na pulpicie**: `--skrot` tworzy ikonę na Windows (.lnk z ikoną, bez okna konsoli),
  macOS (.command) i Linux (.desktop na pulpicie i w menu programów). Rozpoznaje polski „Pulpit”.
- **Aplikacja na ekran główny telefonu (PWA)**: manifest, ikony, service worker i tryb
  pełnoekranowy. `--web --telefon` udostępnia czat w domowej sieci Wi-Fi i wypisuje adres dla telefonu.
- Ikona robota rysowana w kodzie (PNG i ICO bez bibliotek graficznych).
- `--otworz` od razu otwiera przeglądarkę. Ponowne uruchomienie, gdy Badek już działa, tylko otwiera okno.

## 0.2.0

### Nowe
- **Dostęp do internetu**: Wikipedia (`co to jest ...`, `więcej`), pogoda z Open-Meteo,
  kursy walut z NBP. Działa bez kluczy API, a tryb `--offline` go wyłącza.
- **Biblioteki wiedzy**: tworzenie z artykułów Wikipedii (`stwórz bibliotekę o ...`)
  albo ręcznie (`stwórz bibliotekę ...`, `dodaj do ...: ...`), wyszukiwanie TF-IDF,
  odpowiedzi offline. To, co Badek przeczyta w internecie, trafia do biblioteki „Internet”.
- **Wtyczki w Pythonie**: `stwórz wtyczkę ...` tworzy szablon, a `przeładuj wtyczki` ładuje zmiany.
- **Czat w przeglądarce**: `python3 -m panbadek --web`.
- Pamięć miasta (`mieszkam w ...`) dla szybkiej pogody.
- Polecenie `zapomnij: ...`.
- Instalacja przez `pip install .` i polecenie `panbadek`.

### Ulepszenia
- Sieć neuronowa nie zgaduje już na zdaniach, w których nie rozpoznaje żadnego słowa
  (np. „kurs programowania” nie jest już pożegnaniem).
- Gdy sieć się waha, a biblioteka zna wyraźnie pasujący fakt, Badek odpowiada faktem.
- Historia poleceń i strzałki w terminalu (readline).
- Neutralne zwroty („Jeszcze nie znam twojego imienia”).

## 0.1.0
- Pierwsza wersja: sieć neuronowa w czystym Pythonie, intencje po polsku, kalkulator,
  data i godzina, pamięć imienia, uczenie się nowych odpowiedzi.
