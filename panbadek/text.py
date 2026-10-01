"""Przetwarzanie tekstu: normalizacja, tokenizacja i zamiana zdań na wektory."""

import re
import unicodedata

_POLSKIE = str.maketrans("ąćęłńóśźż", "acelnoszz")
_SLOWO = re.compile(r"[a-z0-9]+")

# Długość "rdzenia" słowa. Polski mocno się odmienia ("kot", "kota", "kotem"),
# więc obcinamy końcówki zamiast budować pełny stemmer.
DLUGOSC_RDZENIA = 5


def normalizuj(tekst):
    """Małe litery, bez polskich znaków i akcentów."""
    tekst = tekst.lower().translate(_POLSKIE)
    tekst = unicodedata.normalize("NFKD", tekst)
    return "".join(z for z in tekst if not unicodedata.combining(z))


def tokenizuj(tekst):
    """Zwraca listę rdzeni słów z tekstu."""
    return [slowo[:DLUGOSC_RDZENIA] for slowo in _SLOWO.findall(normalizuj(tekst))]


def cechy(tekst):
    """Zbiór cech zdania: rdzenie słów oraz trigramy znakowe.

    Trigramy pomagają rozpoznać słowa z literówkami albo w innej odmianie.
    """
    wynik = set()
    for slowo in _SLOWO.findall(normalizuj(tekst)):
        wynik.add("w:" + slowo[:DLUGOSC_RDZENIA])
        obramowane = f"#{slowo}#"
        for i in range(len(obramowane) - 2):
            wynik.add("t:" + obramowane[i:i + 3])
    return wynik


class Slownik:
    """Mapuje cechy na indeksy wektora wejściowego sieci."""

    def __init__(self, cechy_lista=None):
        self.indeksy = {c: i for i, c in enumerate(cechy_lista or [])}

    @classmethod
    def zbuduj(cls, zdania):
        wszystkie = set()
        for zdanie in zdania:
            wszystkie |= cechy(zdanie)
        return cls(sorted(wszystkie))

    def __len__(self):
        return len(self.indeksy)

    def lista(self):
        return sorted(self.indeksy, key=self.indeksy.get)

    def wektor(self, tekst):
        """Rzadki wektor: lista indeksów aktywnych cech (wartość 1)."""
        return sorted(self.indeksy[c] for c in cechy(tekst) if c in self.indeksy)
