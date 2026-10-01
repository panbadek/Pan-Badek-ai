import datetime
import os
import tempfile
import unittest

from panbadek import PanBadek
from panbadek.network import SiecNeuronowa
from panbadek.skills import data, godzina, kalkulator
from panbadek.text import Slownik, normalizuj, tokenizuj


class TestTekst(unittest.TestCase):
    def test_normalizacja_usuwa_polskie_znaki(self):
        self.assertEqual(normalizuj("Zażółć GĘŚLĄ jaźń"), "zazolc gesla jazn")

    def test_tokenizacja_obcina_koncowki(self):
        self.assertEqual(tokenizuj("Opowiedz żart!"), ["opowi", "zart"])

    def test_wektor_pomija_nieznane_cechy(self):
        slownik = Slownik.zbuduj(["cześć"])
        self.assertTrue(slownik.wektor("cześć"))
        self.assertEqual(slownik.wektor("xyz"), [])


class TestSiec(unittest.TestCase):
    def test_uczy_sie_xor(self):
        # Wejście 0 = bias, 1 i 2 = bity; XOR nie jest liniowo separowalny.
        dane = [([0], 0), ([0, 1], 1), ([0, 2], 1), ([0, 1, 2], 0)]
        siec = SiecNeuronowa(3, 8, 2, ziarno=0)
        siec.trenuj(dane, epoki=2000, tempo=0.1, ziarno=0)
        for wejscie, cel in dane:
            prawd = siec.przewiduj(wejscie)
            self.assertEqual(prawd.index(max(prawd)), cel)

    def test_serializacja(self):
        siec = SiecNeuronowa(4, 3, 2, ziarno=1)
        kopia = SiecNeuronowa.ze_slownika(siec.do_slownika())
        self.assertEqual(siec.przewiduj([0, 2]), kopia.przewiduj([0, 2]))


class TestUmiejetnosci(unittest.TestCase):
    def test_kalkulator(self):
        self.assertEqual(kalkulator("Ile to 12*7+3?"), "12*7+3 = 87")
        self.assertEqual(kalkulator("ile to 5 razy 4"), "5 * 4 = 20")
        self.assertEqual(kalkulator("sqrt(16) + 2^3"), "sqrt(16) + 2^3 = 12")
        self.assertIn("zero", kalkulator("2/0"))

    def test_kalkulator_ignoruje_zwykly_tekst(self):
        self.assertIsNone(kalkulator("mam 3 koty"))
        self.assertIsNone(kalkulator("cześć"))

    def test_kalkulator_nie_wykonuje_kodu(self):
        self.assertIsNone(kalkulator("__import__('os').system('ls')"))
        self.assertIsNone(kalkulator("2**99999"))

    def test_data_i_godzina(self):
        chwila = datetime.datetime(2026, 10, 1, 9, 5)
        self.assertEqual(godzina(chwila), "Jest godzina 09:05.")
        self.assertEqual(data(chwila), "Dziś jest czwartek, 1 października 2026 r.")


class TestPanBadek(unittest.TestCase):
    def setUp(self):
        self.katalog = tempfile.TemporaryDirectory()
        self.addCleanup(self.katalog.cleanup)
        self.badek = PanBadek(katalog_pamieci=self.katalog.name, ziarno=0)

    def nazwa(self, tekst):
        intencja, _ = self.badek.klasyfikuj(tekst)
        return intencja["nazwa"]

    def test_rozpoznaje_intencje_spoza_przykladow(self):
        self.assertEqual(self.nazwa("Cześć!"), "powitanie")
        self.assertEqual(self.nazwa("kim ty jestes?"), "kim_jestes")
        self.assertEqual(self.nazwa("opowiedz mi jakis zart"), "zart")
        self.assertEqual(self.nazwa("dzieki wielkie"), "podziekowanie")
        self.assertEqual(self.nazwa("która godzinka?"), "godzina")

    def test_nie_zgaduje_przy_bełkocie(self):
        self.assertIn("nie", self.badek.odpowiedz("asdfgh qwerty").lower())

    def test_liczy(self):
        self.assertEqual(self.badek.odpowiedz("ile to 2+2"), "2+2 = 4")

    def test_zapamietuje_imie(self):
        self.badek.odpowiedz("Mam na imię Ania")
        self.assertEqual(self.badek.odpowiedz("jak mam na imię?"), "Masz na imię Ania.")
        nowy = PanBadek(katalog_pamieci=self.katalog.name, ziarno=0)
        self.assertEqual(nowy.imie, "Ania")

    def test_uczy_sie_i_pamieta_po_restarcie(self):
        self.badek.odpowiedz("naucz się: ulubiony kolor => Zielony!")
        self.assertEqual(self.badek.odpowiedz("jaki jest twój ulubiony kolor?"), "Zielony!")
        self.assertTrue(os.path.exists(os.path.join(self.katalog.name, "model.json")))
        nowy = PanBadek(katalog_pamieci=self.katalog.name, ziarno=0)
        self.assertEqual(nowy.odpowiedz("ulubiony kolor"), "Zielony!")


if __name__ == "__main__":
    unittest.main()
