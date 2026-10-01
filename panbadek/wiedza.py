"""Baza wiedzy: pary pytanie -> odpowiedź, które Pan Badek zbiera z rozmów i sam porządkuje.

Skąd bierze się wiedza (pole "zrodlo"):
  "wbudowana" - startowa wiedza ogólna z panbadek/data/wiedza.json,
  "ty"        - nauczona poleceniem "naucz się: pytanie => odpowiedź",
  "Claude", "Qwen3.5 2B", ... - odpowiedzi dużych modeli AI, które Badek zapamiętał,
                żeby następnym razem odpowiedzieć sam (bez internetu i za darmo).

Każdy wpis ma ocenę: 👍 ją podnosi, 👎 obniża, a odpowiedzi z oceną poniżej zera
są usuwane. Wyszukiwanie porównuje pytanie z zapamiętanymi pytaniami (TF-IDF).
"""

import json
import os
import time

from .biblioteki import NIEISTOTNE, IndeksTFIDF, _cechy_istotne
from .text import normalizuj, slowa

# Powyżej tego podobieństwa uznajemy, że to "to samo pytanie" (scalamy zamiast dublować).
PROG_DUPLIKATU = 0.85
LIMIT_WPISOW = 5000
MAKS_ODPOWIEDZ = 1500
# Mnożnik podobieństwa, gdy pytanie ma słowo obce całej bazie: odpowiedź zostaje
# tylko przy bardzo dobrym dopasowaniu reszty pytania.
KARA_OBCEGO_SLOWA = 0.55


def istotne_slowa(tekst):
    return [s for s in slowa(tekst) if s not in NIEISTOTNE and len(s) > 1]


class BazaWiedzy:
    def __init__(self, plik=None, wbudowana=None):
        self.plik = plik
        self.wpisy = []
        if wbudowana and os.path.exists(wbudowana):
            with open(wbudowana, encoding="utf-8") as f:
                for i, w in enumerate(json.load(f)["wiedza"]):
                    self.wpisy.append({"id": f"w{i}", "pytanie": w["pytanie"], "odpowiedz": w["odpowiedz"],
                                       "zrodlo": "wbudowana", "ocena": 0, "uzycia": 0})
        self._kolejne = 1
        self._usuniete = set()  # wbudowane wpisy, które oceniłeś źle albo nadpisałeś
        if plik and os.path.exists(plik):
            try:
                with open(plik, encoding="utf-8") as f:
                    dane = json.load(f)
                self._kolejne = dane.get("kolejne", 1)
                self._usuniete = set(dane.get("usuniete_wbudowane", []))
                oceny = dane.get("oceny_wbudowanych", {})
                self.wpisy = [w for w in self.wpisy if w["id"] not in self._usuniete]
                for w in self.wpisy:
                    w["ocena"] = oceny.get(w["id"], 0)
                self.wpisy += dane.get("wpisy", [])
            except (OSError, ValueError):
                pass
        self._indeks = None

    # --- zapis ---------------------------------------------------------------

    def zapisz(self):
        self._indeks = None
        if not self.plik:
            return
        os.makedirs(os.path.dirname(self.plik), exist_ok=True)
        wbudowane = [w for w in self.wpisy if w["zrodlo"] == "wbudowana"]
        stan = {
            "kolejne": self._kolejne,
            "wpisy": [w for w in self.wpisy if w["zrodlo"] != "wbudowana"],
            "oceny_wbudowanych": {w["id"]: w["ocena"] for w in wbudowane if w["ocena"]},
            "usuniete_wbudowane": sorted(self._usuniete),
        }
        with open(self.plik, "w", encoding="utf-8") as f:
            json.dump(stan, f, ensure_ascii=False)

    # --- wyszukiwanie --------------------------------------------------------

    def _zbuduj_indeks(self):
        self._indeks = IndeksTFIDF(w["pytanie"] for w in self.wpisy)

    def szukaj(self, pytanie):
        """Najlepiej pasujący wpis: (wpis, podobieństwo) albo (None, 0)."""
        if not self.wpisy or not istotne_slowa(pytanie):
            return None, 0.0
        if self._indeks is None:
            self._zbuduj_indeks()
        wyniki = self._indeks.szukaj(pytanie, ile=3)
        if not wyniki:
            return None, 0.0
        wyniki = [(wynik * (KARA_OBCEGO_SLOWA if self._obce_slowo(pytanie, i) else 1.0), i) for wynik, i in wyniki]
        # Przy podobnej trafności wygrywa lepiej oceniona odpowiedź.
        najlepszy = max(wyniki, key=lambda w: w[0] + 0.02 * self.wpisy[w[1]]["ocena"])
        return self.wpisy[najlepszy[1]], najlepszy[0]

    def _obce_slowo(self, pytanie, numer):
        """Czy pytanie podmienia ważne słowo? Dopasowanemu pytaniu brakuje jego własnego słowa,
        a w pytaniu jest słowo, którego baza w ogóle nie zna i które nie jest literówką
        ("ile lat żyją papugi" to nie "ile lat żyje kot", ale "w którym roku był chrzest
        Polski" to wciąż "kiedy był chrzest Polski")."""
        cechy_wpisu = self._indeks.teksty[numer][0]
        cechy_pytania = _cechy_istotne(pytanie)
        if all(c in cechy_pytania for c in cechy_wpisu if c.startswith("w:")):
            return False
        for slowo in istotne_slowa(pytanie):
            if len(slowo) < 4:
                continue
            cechy_slowa = _cechy_istotne(slowo)
            if any(c in self._indeks.waga for c in cechy_slowa if c.startswith("w:")):
                continue
            trigramy = [c for c in cechy_slowa if c.startswith("t:")]
            if trigramy and sum(t in cechy_wpisu for t in trigramy) / len(trigramy) < 0.5:
                return True
        return False

    def wpis(self, id_wpisu):
        return next((w for w in self.wpisy if w["id"] == id_wpisu), None)

    # --- uczenie ---------------------------------------------------------------

    def dodaj(self, pytanie, odpowiedz, zrodlo):
        """Dodaje (albo aktualizuje) parę pytanie-odpowiedź. Zwraca wpis."""
        pytanie, odpowiedz = pytanie.strip(), odpowiedz.strip()[:MAKS_ODPOWIEDZ]
        istniejacy, podobienstwo = self.szukaj(pytanie)
        if istniejacy and (podobienstwo >= PROG_DUPLIKATU or
                           normalizuj(istniejacy["pytanie"]) == normalizuj(pytanie)):
            # Twoja lekcja zawsze nadpisuje; odpowiedź AI nie nadpisuje twojej ani dobrze ocenionej.
            if zrodlo == "ty" or (istniejacy["zrodlo"] != "ty" and istniejacy["ocena"] <= 0):
                if istniejacy["zrodlo"] == "wbudowana":
                    self._oznacz_usuniety(istniejacy)
                    self.wpisy.remove(istniejacy)
                else:
                    istniejacy.update(odpowiedz=odpowiedz, zrodlo=zrodlo, ocena=0)
                    self.zapisz()
                    return istniejacy
            else:
                return istniejacy
        wpis = {"id": f"u{self._kolejne}", "pytanie": pytanie, "odpowiedz": odpowiedz,
                "zrodlo": zrodlo, "ocena": 1 if zrodlo == "ty" else 0, "uzycia": 0,
                "dodano": int(time.time())}
        self._kolejne += 1
        self.wpisy.append(wpis)
        if len(self.wpisy) > LIMIT_WPISOW:
            # Wypychamy najsłabsze odpowiedzi AI, nigdy twoich lekcji.
            kandydaci = sorted((w for w in self.wpisy if w["zrodlo"] not in ("ty", "wbudowana")),
                               key=lambda w: (w["ocena"], w["uzycia"]))
            if kandydaci:
                self.wpisy.remove(kandydaci[0])
        self.zapisz()
        return wpis

    def _oznacz_usuniety(self, wpis):
        if wpis["zrodlo"] == "wbudowana":
            self._usuniete.add(wpis["id"])

    def ocen(self, id_wpisu, dobra):
        """👍 albo 👎 dla wpisu. Zwraca "usunieto", "ocenione" albo None."""
        wpis = self.wpis(id_wpisu)
        if not wpis:
            return None
        wpis["ocena"] += 1 if dobra else -1
        # Twoje lekcje znoszą jedną złą ocenę, reszta wylatuje od razu.
        if (wpis["ocena"] < 0 and wpis["zrodlo"] != "ty") or wpis["ocena"] < -1:
            self._oznacz_usuniety(wpis)
            self.wpisy.remove(wpis)
            self.zapisz()
            return "usunieto"
        self.zapisz()
        return "ocenione"

    def usun(self, id_wpisu):
        wpis = self.wpis(id_wpisu)
        if wpis:
            self._oznacz_usuniety(wpis)
            self.wpisy.remove(wpis)
            self.zapisz()
        return wpis is not None

    def uzyto(self, wpis):
        wpis["uzycia"] = wpis.get("uzycia", 0) + 1

    def porzadkuj(self):
        """Scala zdublowane pytania (zostaje lepiej oceniony wpis). Zwraca liczbę scalonych."""
        kolejnosc = sorted(range(len(self.wpisy)),
                           key=lambda i: (-self.wpisy[i]["ocena"], self.wpisy[i]["zrodlo"] != "ty"))
        indeks = IndeksTFIDF(w["pytanie"] for w in self.wpisy)
        zostaja, scalone = set(), 0
        for i in kolejnosc:
            wpis = self.wpisy[i]
            duplikat = next((j for wynik, j in indeks.szukaj(wpis["pytanie"], ile=3)
                             if j != i and j in zostaja and wynik >= 0.95), None)
            if duplikat is not None:
                lepszy = self.wpisy[duplikat]
                lepszy["uzycia"] = lepszy.get("uzycia", 0) + wpis.get("uzycia", 0)
                self._oznacz_usuniety(wpis)
                scalone += 1
            else:
                zostaja.add(i)
        self.wpisy = [w for i, w in enumerate(self.wpisy) if i in zostaja]
        if scalone:
            self.zapisz()
        return scalone

    def statystyki(self):
        licznik = {}
        for w in self.wpisy:
            licznik[w["zrodlo"]] = licznik.get(w["zrodlo"], 0) + 1
        return licznik

    # --- wymiana między urządzeniami --------------------------------------------

    def eksport(self):
        return [{k: w[k] for k in ("pytanie", "odpowiedz", "zrodlo", "ocena")}
                for w in self.wpisy if w["zrodlo"] != "wbudowana"]

    def import_(self, wpisy):
        """Dołącza wiedzę z innego urządzenia. Zwraca liczbę nowych wpisów."""
        przed = len(self.wpisy)
        for w in wpisy:
            if w.get("pytanie") and w.get("odpowiedz"):
                nowy = self.dodaj(w["pytanie"], w["odpowiedz"], w.get("zrodlo", "ty"))
                nowy["ocena"] = max(nowy["ocena"], int(w.get("ocena", 0)))
        self.zapisz()
        return len(self.wpisy) - przed
