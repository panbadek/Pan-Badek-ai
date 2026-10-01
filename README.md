# Pan Badek AI 🤖

Własna, mała sztuczna inteligencja napisana **od zera w czystym Pythonie** —
bez numpy, bez PyTorcha, bez zewnętrznych API. Cała „inteligencja” to
samodzielnie zaimplementowana sieć neuronowa z propagacją wsteczną.

## Uruchomienie

Wymagany jest tylko Python 3.8+.

```bash
python3 -m panbadek          # rozmowa w terminalu
python3 -m panbadek --debug  # pokazuje, co „myśli” sieć (intencja + pewność)
```

Przykładowa rozmowa:

```
Ty: Cześć!
Pan Badek: Hej! Miło cię widzieć.
Ty: Mam na imię Ania
Pan Badek: Miło mi cię poznać, Ania!
Ty: ile to 12 razy 7
Pan Badek: 12 * 7 = 84
Ty: naucz się: ulubiony kolor => Zielony jak trawa!
Pan Badek: Zapamiętałem! Na 'ulubiony kolor' odpowiem: 'Zielony jak trawa!'.
Ty: jaki jest twój ulubiony kolor?
Pan Badek: Zielony jak trawa!
```

## Co potrafi

- rozumie intencje (powitanie, żart, godzina, data, pytania o siebie…), także z literówkami i bez polskich znaków,
- liczy (`ile to 2^10`, `sqrt(16) + 3`, `5 razy 4`) — bezpiecznie, bez `eval`,
- podaje godzinę i datę po polsku,
- zapamiętuje twoje imię,
- **uczy się w trakcie rozmowy**: `naucz się: pytanie => odpowiedź` — sieć trenuje się od nowa,
  a wiedza jest zapisywana w `~/.panbadek/` i przetrwa restart.

## Jak to działa

1. **Tekst → wektor** (`panbadek/text.py`): zdanie jest normalizowane (małe litery, bez polskich
   znaków), a potem zamieniane na zbiór cech: rdzenie słów (pierwsze 5 liter — prosty sposób na
   polską odmianę) i trigramy znakowe (odporność na literówki).
2. **Sieć neuronowa** (`panbadek/network.py`): wejście → warstwa ukryta (32 neurony, ReLU) →
   softmax. Uczona spadkiem gradientu z entropią krzyżową; gradienty liczone ręcznie.
3. **Mózg** (`panbadek/brain.py`): najpierw sprawdza polecenia specjalne (nauka, imię, kalkulator),
   potem pyta sieć o intencję. Jeśli pewność jest poniżej 45%, przyznaje, że nie wie,
   zamiast zgadywać.

## Rozwijanie

Nowe tematy dodajesz w `panbadek/data/intencje.json` — wystarczy nazwa, kilka przykładowych zdań
i odpowiedzi. Model przetrenuje się automatycznie przy następnym uruchomieniu.

```json
{
  "nazwa": "pogoda",
  "przyklady": ["jaka jest pogoda", "czy pada deszcz", "będzie słońce"],
  "odpowiedzi": ["Nie mam okna, ale mam nadzieję, że świeci słońce!"]
}
```

## Testy

```bash
python3 -m unittest discover -s tests -v
```
