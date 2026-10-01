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


def rdzen(slowo):
    """Prosty rdzeń: odcinamy końcówkę (ostatnią literę) i przycinamy do 5 liter,
    więc "żyją"/"żyje" -> "zyj", "koty"/"kot" -> "kot", "polski"/"polska" -> "polsk"."""
    if len(slowo) <= 3:
        return slowo
    return slowo[:min(DLUGOSC_RDZENIA, max(3, len(slowo) - 1))]


def slowa(tekst):
    """Słowa tekstu: małe litery, bez polskich znaków i bez interpunkcji."""
    return _SLOWO.findall(normalizuj(tekst))


def tokenizuj(tekst):
    """Zwraca listę rdzeni słów z tekstu."""
    return [rdzen(slowo) for slowo in _SLOWO.findall(normalizuj(tekst))]


def cechy(tekst):
    """Zbiór cech zdania: rdzenie słów oraz trigramy znakowe.

    Trigramy pomagają rozpoznać słowa z literówkami albo w innej odmianie.
    """
    wynik = set()
    for slowo in _SLOWO.findall(normalizuj(tekst)):
        wynik.add("w:" + rdzen(slowo))
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

    def rozszerz(self, teksty):
        """Dopisuje nowe cechy na końcu (stare indeksy się nie zmieniają). Zwraca ich liczbę."""
        przed = len(self.indeksy)
        for tekst in teksty:
            for c in sorted(cechy(tekst)):
                if c not in self.indeksy:
                    self.indeksy[c] = len(self.indeksy)
        return len(self.indeksy) - przed

    def wektor(self, tekst):
        """Rzadki wektor: lista indeksów aktywnych cech (wartość 1)."""
        return sorted(self.indeksy[c] for c in cechy(tekst) if c in self.indeksy)
