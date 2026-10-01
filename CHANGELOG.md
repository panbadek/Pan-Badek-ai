# Historia zmian

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
