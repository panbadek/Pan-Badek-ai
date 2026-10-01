"""Biblioteki wiedzy: nazwane zbiory faktów, które Pan Badek tworzy i przeszukuje.

Każda biblioteka to plik JSON w katalogu pamięci. Wyszukiwanie działa jak mała
wyszukiwarka: zdania zamieniane są na cechy, ważone rzadkością (IDF), a wynikiem
jest podobieństwo kosinusowe pytania do każdego zapisanego faktu.
"""

import json
import math
import os
import re

from .text import cechy, normalizuj, slowa

# Słowa, które niczego nie wnoszą do wyszukiwania.
NIEISTOTNE = set("""
a aby ale albo bo by byc byl byla bylo byly co czy dla do gdzie i ich ile jak jaka jaki
jakie jest jestem jestes kim kto ktora ktore ktory ma mi mnie na nie o od po powiedz pod
przez sie ta tak te ten to tu twoj w we z za ze zna znasz opowiedz wiesz czym
moj moja moje mojego mojej moim twoja twoje twojego twojej twoim
ktorym ktorej ktorego ktorych ktorzy jako wynosi nazywa dlugo
""".split())

NAZWA = re.compile(r"^[\w ąćęłńóśźżĄĆĘŁŃÓŚŹŻ-]{1,60}$")


# Synonimy: różne słowa, to samo pytanie ("najwyższa góra" = "najwyższy szczyt").
# Słowa z listy zamieniane są przed wyszukiwaniem na pierwsze słowo grupy.
_GRUPY_SYNONIMOW = [
    "szczyt szczytu szczyty gora gory gore gorze gorach gorami",
    "napisal napisala napisali autor autorem autora autorka autorki",
    "predkosc predkosci szybko szybkosc szybkosci predko",
    "temperatura temperaturze temperatury stopniach stopni stopnie stopniu",
    "panstwo panstwa panstwem kraj kraju kraje krajem",
    "wynalazl wynalazla wymyslil wymyslila wynalazca wynalazcy",
]
SYNONIMY = {slowo: grupa.split()[0] for grupa in _GRUPY_SYNONIMOW for slowo in grupa.split()[1:]}


def _cechy_istotne(tekst):
    return cechy(" ".join(SYNONIMY.get(s, s) for s in slowa(tekst) if s not in NIEISTOTNE))


# Rdzeń słowa mówi o znaczeniu więcej niż trigram liter, więc waży więcej.
WAGA_SLOWA = 1.6


class IndeksTFIDF:
    """Mała wyszukiwarka: teksty zamienione na cechy ważone rzadkością (IDF),
    a trafność to podobieństwo kosinusowe zapytania do tekstu."""

    def __init__(self, teksty):
        cechy_tekstow = [_cechy_istotne(t) for t in teksty]
        df = {}
        for c in cechy_tekstow:
            for cecha in c:
                df[cecha] = df.get(cecha, 0) + 1
        n = len(cechy_tekstow)
        self.waga = {c: math.log((n + 1) / (d + 0.5)) * (WAGA_SLOWA if c.startswith("w:") else 1.0)
                     for c, d in df.items()}
        # Cecha, której nie ma w żadnym tekście, waży tyle co najrzadsza znana i liczy się
        # do normy zapytania - żeby "stolica Niemiec" nie była identyczna ze "stolicą Francji"
        # tylko dlatego, że słowa "Niemiec" indeks nie zna.
        self.waga_nieznanej = max((math.log((n + 1) / (d + 0.5)) for d in df.values()), default=1.0)
        self.teksty = [(c, math.sqrt(sum(self.waga[x] ** 2 for x in c)) or 1.0) for c in cechy_tekstow]

    def szukaj(self, zapytanie, ile=1):
        """Zwraca listę (wynik 0..1, numer tekstu) od najlepszego."""
        z = _cechy_istotne(zapytanie)
        norma_z = math.sqrt(sum(self._waga(x) ** 2 for x in z)) or 1.0
        wyniki = []
        for i, (c, norma) in enumerate(self.teksty):
            wspolne = z & c
            if wspolne:
                wyniki.append((sum(self.waga[x] ** 2 for x in wspolne) / (norma * norma_z), i))
        wyniki.sort(key=lambda w: -w[0])
        return wyniki[:ile]

    def _waga(self, cecha):
        if cecha in self.waga:
            return self.waga[cecha]
        return self.waga_nieznanej * (WAGA_SLOWA if cecha.startswith("w:") else 1.0)


def _plik(nazwa):
    return normalizuj(nazwa).strip().replace(" ", "_") + ".json"


class Biblioteki:
    def __init__(self, katalog):
        self.katalog = katalog
        self.dane = {}
        if katalog and os.path.isdir(katalog):
            for plik in sorted(os.listdir(katalog)):
                if plik.endswith(".json"):
                    try:
                        with open(os.path.join(katalog, plik), encoding="utf-8") as f:
                            biblioteka = json.load(f)
                        self.dane[biblioteka["nazwa"]] = biblioteka
                    except (OSError, ValueError, KeyError):
                        continue
        self._indeks = None

    def _zapisz(self, nazwa):
        self._indeks = None
        if not self.katalog:
            return
        os.makedirs(self.katalog, exist_ok=True)
        with open(os.path.join(self.katalog, _plik(nazwa)), "w", encoding="utf-8") as f:
            json.dump(self.dane[nazwa], f, ensure_ascii=False, indent=2)

    def znajdz_nazwe(self, nazwa):
        """Dopasowuje nazwę bez względu na wielkość liter i polskie znaki."""
        klucz = normalizuj(nazwa).strip()
        for istniejaca in self.dane:
            if normalizuj(istniejaca) == klucz:
                return istniejaca
        return None

    def stworz(self, nazwa, opis="", zrodlo=""):
        nazwa = nazwa.strip()
        if not NAZWA.match(nazwa):
            raise ValueError("Nazwa biblioteki może mieć do 60 liter, cyfr, spacji i myślników.")
        istniejaca = self.znajdz_nazwe(nazwa)
        if istniejaca:
            return istniejaca
        self.dane[nazwa] = {"nazwa": nazwa, "opis": opis, "zrodlo": zrodlo, "wpisy": []}
        self._zapisz(nazwa)
        return nazwa

    def dodaj(self, nazwa, *wpisy):
        nazwa = self.znajdz_nazwe(nazwa) or self.stworz(nazwa)
        biblioteka = self.dane[nazwa]
        nowe = [w.strip() for w in wpisy if w.strip() and w.strip() not in biblioteka["wpisy"]]
        biblioteka["wpisy"].extend(nowe)
        self._zapisz(nazwa)
        return len(nowe)

    def ustaw(self, nazwa, **pola):
        """Dodatkowe informacje o bibliotece (np. streszczenie filmu)."""
        nazwa = self.znajdz_nazwe(nazwa)
        if nazwa:
            self.dane[nazwa].update(pola)
            self._zapisz(nazwa)

    def usun(self, nazwa):
        nazwa = self.znajdz_nazwe(nazwa)
        if not nazwa:
            return False
        del self.dane[nazwa]
        self._indeks = None
        if self.katalog:
            sciezka = os.path.join(self.katalog, _plik(nazwa))
            if os.path.exists(sciezka):
                os.remove(sciezka)
        return True

    def lista(self):
        return [(n, len(b["wpisy"]), b.get("opis", "")) for n, b in sorted(self.dane.items())]

    def _zbuduj_indeks(self):
        wpisy = [(n, w) for n, b in self.dane.items() for w in b["wpisy"]]
        self._indeks = (wpisy, IndeksTFIDF(w for _, w in wpisy))

    def szukaj(self, pytanie, ile=1):
        """Zwraca listę (wynik, nazwa_biblioteki, wpis) posortowaną od najlepszego."""
        if self._indeks is None:
            self._zbuduj_indeks()
        wpisy, indeks = self._indeks
        return [(wynik, *wpisy[i]) for wynik, i in indeks.szukaj(pytanie, ile)]
