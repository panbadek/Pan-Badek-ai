# Historia zmian

## 0.11.0

### Zadania ze szkoły (`panbadek/szkola.py`)
- Zadania tekstowe rozwiązywane offline jak w zeszycie: **Dane, Szukane, Wzór, Rozwiązanie, Odpowiedź**.
- Fizyka z jednostkami i ich zamianą: ruch, siła, gęstość, praca, moc, ciśnienie, prawo Ohma,
  moc prądu, energia kinetyczna i potencjalna, ciężar.
- Geometria: pola, obwody, przekątne, objętości 14 figur i brył oraz twierdzenie Pitagorasa
  (wynik z π dokładnie i w przybliżeniu).
- Procenty w zadaniach (obniżki, podwyżki, cena sprzed zmiany) i zadania z treścią
  (dostał/zjadł, „za 4 zł”, „po 6”, „po równo między”, „o 3 starszy”, „3 razy więcej”).
- Gdy zadanie nie pasuje do wzoru, Badek nie zgaduje i oddaje je mocniejszemu AI.
- **Zadanie ze zdjęcia** (📝): zdjęcie zeszytu idzie do Claude, który przepisuje treść i rozwiązuje
  zadanie krok po kroku, jak korepetytor. Claude dostał też zasady rozwiązywania zadań szkolnych.

### Nauka z filmów i tekstów (`panbadek/youtube.py`)
- **„obejrzyj <link do YouTube>”:** Badek pobiera napisy filmu (polskie mają pierwszeństwo), dzieli je
  na zdania, robi streszczenie i listę najważniejszych słów, a notatki zapisuje w bibliotece
  „Film - <tytuł>”. Potem odpowiada na pytania o film, także offline.
- **„naucz się z tekstu: …”:** to samo z wklejonym tekstem (notatka z lekcji, transkrypcja).
- „o czym był film?”, „jakie filmy obejrzałeś”.
- W przeglądarce YouTube blokuje pobieranie napisów, więc Badek prosi o wklejenie transkrypcji.
  Na komputerze i w aplikacji na Androida ogląda filmy sam.

### Egzaminy
- Nowa kategoria „szkoła”: egzamin 97,9% (146 pytań), egzamin kontrolny 85,1% (47 pytań,
  w tym 8/8 nowych zadań szkolnych).

## 0.10.0

### Trener (`python3 -m panbadek --trener`)
- **Walidacja krzyżowa i strojenie:** trener porównuje ustawienia sieci (neurony, tempo, augmentacja),
  uśrednia po kilku losowaniach wag i wybiera najprostsze w granicach 1 punktu od najlepszego.
  `--zapisz` zapisuje je w `panbadek/data/ustawienia_sieci.json`, a Badek z nich korzysta.
- **Augmentacja** (`panbadek/augmentacja.py`): warianty przykładów z literówkami (zamiana, pominięcie,
  podwojenie litery, sąsiedni klawisz) i dopiskami. Zdania z literówkami: 78,3% → 82,4%.
- **Egzamin całego Badka** (138 pytań w 6 kategoriach) i **egzamin kontrolny** (39 pytań nieużywanych
  przy poprawkach), a także nowy trudny zestaw testowy sieci (176 zdań).
- **Nauczyciel (Claude):** `--nauczyciel` dopisuje nowe przykłady (zostają tylko, jeśli walidacja się
  nie pogorszy, i nigdy nie są zdaniami testowymi) oraz uczy Badka odpowiedzi na pytania z rozmów,
  na które nie znał odpowiedzi. Zapamiętuje tylko odpowiedzi, które Claude oznaczy jako pewne.
  Wymaga `pip install anthropic` i klucza API.

### Trening
- 170 nowych przykładów treningowych (523 zamiast 353), szczególnie dla klasy „inne”
  (np. „ile lat ma wieża Eiffla” to nie pytanie o wiek Badka).
- Sieć ma teraz 64 neurony i trenuje się na danych z augmentacją (ok. 4 s zamiast 2 s).

### Poprawki znalezione przez egzamin
- **Synonimy w wyszukiwaniu:** „najwyższa góra” = „najwyższy szczyt”, „autor” = „kto napisał”,
  „jak szybko” = „prędkość”, „kraj” = „państwo” i inne.
- **Mniej zmyślania:** gdy pytanie podmienia ważne słowo („ile lat żyją papugi” zamiast „ile lat żyje
  kot”), Badek przyznaje się do niewiedzy, zamiast odpowiadać o kotach. W aplikacji pytanie trafia
  wtedy do Claude.
- **Dzień tygodnia dowolnej daty:** „jaki dzień tygodnia był 1 stycznia 2000” → sobota.
- „napisz w c++ program, który sortuje tablicę” wybiera teraz wzór sortowania.

Wyniki: egzamin 91,3% → 97,8%, egzamin kontrolny 79,5% → 82,1%, zestaw testowy 97,0% → 98,5%,
zdania z literówkami 78,3% → 82,4%. Trudny zestaw bez zmian (93,2%).

## 0.9.0

### Programowanie w C++
- **Badek pisze w C++** (`panbadek/programowanie.py`), także offline: 29 wzorów kompletnych programów
  (od „hello world” przez sortowanie, klasy, dziedziczenie, wskaźniki, STL, pliki i wyjątki po BFS,
  macierze i wątki). Każdy kompiluje się bez ostrzeżeń w C++17, co sprawdza test z `g++`.
- Liczba z pytania trafia do programu: „liczby pierwsze do 500 w c++”, „tabliczka mnożenia do 12”.
- Odpowiedź: krótkie wyjaśnienie, kod w bloku ```cpp i komenda kompilacji. Pytanie o pojęcie
  („co to jest wskaźnik w c++”) daje najpierw definicję, potem przykład.
- 18 nowych wpisów w bazie wiedzy o C++ (różnice C/C++, kompilacja, STL, referencje, RAII, UB, const…).
- „c++” i „c#” są teraz rozpoznawane jako słowa (wcześniej znikały razem z interpunkcją).
- Z Claude kod pisany jest pod konkretną prośbę w trybie głębokiego myślenia, z zasadami nowoczesnego
  C++ w instrukcji (STL, RAII, inteligentne wskaźniki, kompletne `#include`). Nietypowe zamówienia
  bez AI dostają uczciwą odpowiedź z listą tego, co Badek umie offline.

### Interfejs
- Bloki kodu mają nagłówek z nazwą języka i przycisk **📋 Kopiuj** (kopiuje sam kod).
- Nowa podpowiedź na ekranie startowym: „💻 Napisz kod w C++”.

## 0.8.0

### Charakter w stylu Claude
- Nowe odpowiedzi: pomocne, szczere i ciepłe, bez przesady. Przy niepewnym dopasowaniu Badek
  mówi, jak zrozumiał pytanie („Jeśli dobrze rozumiem, pytasz: …”).
- „Nie wiem” podaje konkretne możliwości (Wikipedia, lekcja, mocniejsze AI) zamiast zgadywać.
  Na niejasne wiadomości prosi o doprecyzowanie.
- **Dopytania:** „Jaka jest stolica Francji?” → „A Niemiec?” → „A Wielkiej Brytanii?”.
- **Troska w kryzysie:** przy sygnałach myśli samobójczych albo samookaleczenia Badek zawsze odpowiada
  z empatią i numerami pomocy (116 123, 800 70 2222, 116 111, 112). Tej odpowiedzi nie oddaje AI.
- Instrukcja dla modeli AI opisuje te same zasady: odpowiedź najpierw, rozumowanie krok po kroku,
  pytanie doprecyzowujące, przyznawanie się do niewiedzy, Markdown.

### Zaawansowane problemy
- **Solver matematyczny** (`panbadek/matematyka.py`), działający offline i pokazujący kroki:
  - równania liniowe i kwadratowe (z deltą, dokładnie na ułamkach), dowolne równania numerycznie
    (z uwagą o okresowości), układy do 4 równań liniowych (eliminacja Gaussa);
  - pochodne symboliczne (reguły iloczynu, ilorazu, łańcuchowa, sin/cos/tg/exp/ln/sqrt);
  - całki: wielomianów symbolicznie, pozostałe numerycznie (Simpson);
  - procenty, statystyka, liczby pierwsze, rozkład na czynniki, NWD (algorytm Euklidesa z krokami),
    NWW, silnia, Fibonacci, systemy liczbowe (także rzymski), jednostki i temperatury.
- **Głębokie myślenie:** trudne problemy (dowody, kod, analiza, planowanie, długie zadania) idą do
  Claude z wysokim wysiłkiem i streszczeniem toku rozumowania, a do modelu w telefonie z włączonym
  myśleniem. Zwykła rozmowa zostaje szybka i tania.

### Interfejs
- Odpowiedzi bez dymków, z awatarem i formatowaniem (pogrubienia, listy, nagłówki, bloki kodu).
- Akcje pod odpowiedzią: 📋 kopiuj, 🔄 odpowiedz jeszcze raz (AI), 👍/👎.
- Animowany wskaźnik „myśli…” i rozwijany „💭 Tok rozumowania”.
- Ekran powitalny z podpowiedziami, rosnące pole tekstowe (Enter wysyła, Shift+Enter dodaje nową linię),
  przycisk ✏️ „Nowa rozmowa” i informacja, że AI może się mylić.

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
