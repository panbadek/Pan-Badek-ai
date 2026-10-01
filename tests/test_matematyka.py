"""Testy solvera matematycznego i zachowań "w stylu Claude" (dopytania, kryzys, szczerość)."""

import tempfile
import unittest

from panbadek import PanBadek
from panbadek.matematyka import pochodna, rozwiaz


class TestRownania(unittest.TestCase):
    def test_liniowe(self):
        self.assertIn("**x = 2**", rozwiaz("rozwiąż 2x + 3 = 7"))
        self.assertIn("x = 1/3", rozwiaz("3x = 1"))

    def test_kwadratowe(self):
        wynik = rozwiaz("x^2 - 5x + 6 = 0")
        self.assertIn("Δ", wynik)
        self.assertIn("**2**", wynik)
        self.assertIn("**3**", wynik)
        self.assertIn("brak rozwiązań rzeczywistych", rozwiaz("x^2 + 1 = 0"))
        self.assertIn("0 - (-8)", rozwiaz("x^2 - 2 = 0"))

    def test_numeryczne_i_okresowe(self):
        self.assertIn("x ≈ 3", rozwiaz("2^x = 8"))
        wynik = rozwiaz("sin(x) = 0.5")
        self.assertIn("2,61799", wynik)
        self.assertIn("okresowe", wynik)

    def test_sprzeczne_i_tozsamosciowe(self):
        self.assertIn("sprzeczne", rozwiaz("x + 1 = x + 2"))
        self.assertIn("tożsamościowe", rozwiaz("2x + 2 = 2(x + 1)"))

    def test_uklady(self):
        self.assertIn("**x = 3**, **y = 2**", rozwiaz("rozwiąż układ: x + y = 5, x - y = 1"))
        self.assertIn("z = 3", rozwiaz("x+y+z=6; x-y=0; 2z=6"))
        self.assertIn("sprzeczny", rozwiaz("x + y = 1, x + y = 2"))


class TestAnaliza(unittest.TestCase):
    def test_pochodne(self):
        self.assertIn("3x^2 + 2", pochodna("x^3 + 2x"))
        self.assertIn("ln(x) + 1", pochodna("x*ln(x)"))
        self.assertIn("2e^(2x)", pochodna("e^(2x)"))
        self.assertIn("cos(x^2)", pochodna("sin(x^2)"))

    def test_calki(self):
        self.assertIn("**9**", rozwiaz("całka z x^2 od 0 do 3"))
        self.assertIn("**2**", rozwiaz("całka z sin(x) od 0 do pi"))
        self.assertIn("x^3 + x^2 + C", rozwiaz("całka z 3x^2+2x"))


class TestRozne(unittest.TestCase):
    def test_procenty(self):
        self.assertIn("**30**", rozwiaz("ile to 15% z 200"))
        self.assertIn("**25%** (wzrost)", rozwiaz("o ile procent wzrosła cena z 80 do 100"))
        self.assertIn("**25%**", rozwiaz("jakim procentem 200 jest 50"))

    def test_statystyka(self):
        self.assertIn("**6,25**", rozwiaz("średnia z 3, 5, 7, 10"))
        self.assertIn("mediana: **4,5**", rozwiaz("statystyki 2 4 4 4 5 5 7 9"))

    def test_teoria_liczb(self):
        self.assertIn("jest liczbą pierwszą", rozwiaz("czy 97 jest liczbą pierwszą"))
        self.assertIn("91 = 7 · 13", rozwiaz("czy 91 jest pierwsza"))
        self.assertIn("2^3 · 3^2 · 5", rozwiaz("rozłóż 360 na czynniki"))
        self.assertIn("**NWD(48, 18) = 6**", rozwiaz("nwd 48 i 18"))
        self.assertIn("**12**", rozwiaz("nww 4 i 6"))
        self.assertIn("3628800", rozwiaz("silnia 10"))
        self.assertIn("832040", rozwiaz("fibonacci 30"))

    def test_systemy_i_jednostki(self):
        self.assertIn("11111111", rozwiaz("zamień 255 na binarny"))
        self.assertIn("MMXXVI", rozwiaz("zamień 2026 na rzymskie"))
        self.assertIn("62,1371", rozwiaz("100 km na mile"))
        self.assertIn("86 °F", rozwiaz("30 C na F"))

    def test_nie_przejmuje_zwyklych_zdan(self):
        for tekst in ["cześć", "ile to 2+2", "jak się masz?", "kot = zwierzę", "mam 3 koty"]:
            self.assertIsNone(rozwiaz(tekst), tekst)


class TestStylClaude(unittest.TestCase):
    def setUp(self):
        self.badek = PanBadek(katalog_pamieci=tempfile.mkdtemp(), ziarno=0, internet=False)

    def test_matematyka_w_rozmowie(self):
        self.assertIn("x = 2", self.badek.odpowiedz("rozwiąż 2x + 3 = 7"))
        self.assertEqual(self.badek.zrodlo, "matematyka")

    def test_dopytania(self):
        self.badek.odpowiedz("Jaka jest stolica Francji?")
        self.assertIn("Berlin", self.badek.odpowiedz("a Niemiec?"))
        self.assertIn("Londyn", self.badek.odpowiedz("a Wielkiej Brytanii?"))

    def test_mowi_jak_zrozumial_przy_niepewnym_dopasowaniu(self):
        odp = self.badek.odpowiedz("najwyższa góra w polsce")
        self.assertIn("Jeśli dobrze rozumiem", odp)
        self.assertIn("Rysy", odp)
        self.assertNotIn("Jeśli dobrze rozumiem", self.badek.odpowiedz("Jaka jest stolica Polski?"))

    def test_kryzys(self):
        for tekst in ["chcę się zabić", "nie chcę już żyć", "czasem myślę o śmierci"]:
            odp = self.badek.odpowiedz(tekst)
            self.assertEqual(self.badek.zrodlo, "kryzys")
            self.assertIn("116 123", odp)
            self.assertIn("112", odp)

    def test_szczere_nie_wiem(self):
        self.assertIn("wolę nie zgadywać", self.badek.odpowiedz("jak naprawić przerzutkę w rowerze"))
        self.assertIn("Nie jestem pewien, o co pytasz", self.badek.odpowiedz("qwerty"))
        trudne = "Udowodnij, że istnieje nieskończenie wiele liczb pierwszych"
        self.assertTrue(self.badek.ocen_trudnosc(trudne))
        self.assertIn("głębokiego myślenia", self.badek.odpowiedz(trudne))
        self.assertFalse(self.badek.ocen_trudnosc("cześć"))


if __name__ == "__main__":
    unittest.main()
