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
python3 -m panbadek --offline  # bez internetu
python3 -m panbadek --debug    # pokazuje, co „myśli” sieć (intencja + pewność)
```

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
