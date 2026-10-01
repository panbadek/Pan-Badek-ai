# Historia zmian

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
