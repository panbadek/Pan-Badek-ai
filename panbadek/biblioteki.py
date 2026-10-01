"""Biblioteki wiedzy: nazwane zbiory faktów, które Pan Badek tworzy i przeszukuje.

Każda biblioteka to plik JSON w katalogu pamięci. Wyszukiwanie działa jak mała
wyszukiwarka: zdania zamieniane są na cechy, ważone rzadkością (IDF), a wynikiem
jest podobieństwo kosinusowe pytania do każdego zapisanego faktu.
"""

import json
import math
import os
import re

from .text import cechy, normalizuj

# Słowa, które niczego nie wnoszą do wyszukiwania.
NIEISTOTNE = set("""
a aby ale albo bo by byc byl byla bylo byly co czy dla do gdzie i ich ile jak jaka jaki
jakie jest jestem jestes kim kto ktora ktore ktory ma mi mnie na nie o od po powiedz pod
przez sie ta tak te ten to tu twoj w we z za ze zna znasz opowiedz wiesz czym
""".split())

NAZWA = re.compile(r"^[\w ąćęłńóśźżĄĆĘŁŃÓŚŹŻ-]{1,60}$")


def _cechy_istotne(tekst):
    slowa = [s for s in normalizuj(tekst).split() if s.strip(".,!?;:\"'()") not in NIEISTOTNE]
    return cechy(" ".join(slowa))


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
        dokumenty = [(n, w, _cechy_istotne(w)) for n, b in self.dane.items() for w in b["wpisy"]]
        df = {}
        for _, _, c in dokumenty:
            for cecha in c:
                df[cecha] = df.get(cecha, 0) + 1
        n = len(dokumenty)
        idf = {c: math.log((n + 1) / (d + 0.5)) for c, d in df.items()}
        indeks = []
        for nazwa, wpis, c in dokumenty:
            norma = math.sqrt(sum(idf[x] ** 2 for x in c)) or 1.0
            indeks.append((nazwa, wpis, c, norma))
        self._indeks = (indeks, idf)

    def szukaj(self, pytanie, ile=1):
        """Zwraca listę (wynik, nazwa_biblioteki, wpis) posortowaną od najlepszego."""
        if self._indeks is None:
            self._zbuduj_indeks()
        indeks, idf = self._indeks
        zapytanie = _cechy_istotne(pytanie)
        norma_z = math.sqrt(sum(idf.get(x, 0.0) ** 2 for x in zapytanie)) or 1.0
        wyniki = []
        for nazwa, wpis, c, norma in indeks:
            wspolne = zapytanie & c
            if wspolne:
                wynik = sum(idf[x] ** 2 for x in wspolne) / (norma * norma_z)
                wyniki.append((wynik, nazwa, wpis))
        wyniki.sort(key=lambda w: w[0], reverse=True)
        return wyniki[:ile]
