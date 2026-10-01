"""Sieć neuronowa napisana od zera w czystym Pythonie (bez numpy).

Architektura: wejście (rzadki wektor cech) -> warstwa ukryta (ReLU) -> softmax.
Uczenie: propagacja wsteczna i stochastyczny spadek gradientu,
funkcja straty: entropia krzyżowa.
"""

import math
import random


def softmax(wartosci):
    maks = max(wartosci)
    potegi = [math.exp(v - maks) for v in wartosci]
    suma = sum(potegi)
    return [p / suma for p in potegi]


class SiecNeuronowa:
    def __init__(self, wejscia, ukryte, wyjscia, ziarno=None):
        los = random.Random(ziarno)
        # Inicjalizacja He dla ReLU i Xaviera dla warstwy wyjściowej.
        s1 = math.sqrt(2.0 / max(1, wejscia))
        s2 = math.sqrt(1.0 / max(1, ukryte))
        # w1[i] to wagi z wejścia i do wszystkich neuronów ukrytych -
        # przy rzadkim wejściu sumujemy tylko aktywne wiersze.
        self.w1 = [[los.gauss(0, s1) for _ in range(ukryte)] for _ in range(wejscia)]
        self.b1 = [0.0] * ukryte
        self.w2 = [[los.gauss(0, s2) for _ in range(wyjscia)] for _ in range(ukryte)]
        self.b2 = [0.0] * wyjscia

    @property
    def rozmiar_ukryty(self):
        return len(self.b1)

    def _naprzod(self, aktywne):
        ukryta = list(self.b1)
        for i in aktywne:
            wiersz = self.w1[i]
            for j in range(len(ukryta)):
                ukryta[j] += wiersz[j]
        ukryta = [max(0.0, h) for h in ukryta]

        logity = list(self.b2)
        for j, h in enumerate(ukryta):
            if h:
                wiersz = self.w2[j]
                for k in range(len(logity)):
                    logity[k] += h * wiersz[k]
        return ukryta, softmax(logity)

    def przewiduj(self, aktywne):
        """Zwraca rozkład prawdopodobieństwa klas dla rzadkiego wejścia."""
        return self._naprzod(aktywne)[1]

    def ucz_przyklad(self, aktywne, cel, tempo):
        """Jeden krok SGD. Zwraca stratę (entropię krzyżową)."""
        ukryta, wyjscie = self._naprzod(aktywne)
        strata = -math.log(max(wyjscie[cel], 1e-12))

        # Gradient softmax + entropia krzyżowa: p - one_hot(cel).
        d_wyj = list(wyjscie)
        d_wyj[cel] -= 1.0

        d_ukr = [0.0] * len(ukryta)
        for j, h in enumerate(ukryta):
            wiersz = self.w2[j]
            if h > 0:
                d_ukr[j] = sum(wiersz[k] * d_wyj[k] for k in range(len(d_wyj)))
            if h:
                for k in range(len(d_wyj)):
                    wiersz[k] -= tempo * h * d_wyj[k]
        for k in range(len(d_wyj)):
            self.b2[k] -= tempo * d_wyj[k]

        for i in aktywne:
            wiersz = self.w1[i]
            for j, d in enumerate(d_ukr):
                if d:
                    wiersz[j] -= tempo * d
        for j, d in enumerate(d_ukr):
            self.b1[j] -= tempo * d
        return strata

    def trenuj(self, dane, epoki=300, tempo=0.05, ziarno=None, cel_straty=0.01):
        """Trenuje na liście par (aktywne_cechy, klasa). Zwraca ostatnią średnią stratę."""
        los = random.Random(ziarno)
        dane = list(dane)
        srednia = float("inf")
        for _ in range(epoki):
            los.shuffle(dane)
            srednia = sum(self.ucz_przyklad(x, y, tempo) for x, y in dane) / max(1, len(dane))
            if srednia < cel_straty:
                break
        return srednia

    def dodaj_wejscia(self, ile, ziarno=None):
        """Nowe wejścia (nowe słowa) z małymi losowymi wagami - reszta wiedzy zostaje."""
        los = random.Random(ziarno)
        ukryte = len(self.b1)
        skala = math.sqrt(2.0 / max(1, len(self.w1) + ile))
        self.w1.extend([los.gauss(0, skala) for _ in range(ukryte)] for _ in range(ile))

    def do_slownika(self):
        return {"w1": self.w1, "b1": self.b1, "w2": self.w2, "b2": self.b2}

    @classmethod
    def ze_slownika(cls, dane):
        siec = cls.__new__(cls)
        siec.w1, siec.b1 = dane["w1"], dane["b1"]
        siec.w2, siec.b2 = dane["w2"], dane["b2"]
        return siec
