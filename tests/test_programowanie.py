"""Testy pisania programów w C++: wzory muszą się kompilować, a Badek wybierać właściwy."""

import os
import re
import shutil
import subprocess
import tempfile
import unittest

from panbadek import PanBadek
from panbadek.programowanie import WZORY, _kod, dopasuj, napisz, prosi_o_kod
from panbadek.text import slowa

KOMPILATOR = shutil.which("g++") or shutil.which("clang++")


class TestWzory(unittest.TestCase):
    @unittest.skipUnless(KOMPILATOR, "brak kompilatora C++")
    def test_kazdy_wzor_kompiluje_sie_bez_ostrzezen(self):
        with tempfile.TemporaryDirectory() as katalog:
            for i, wzor in enumerate(WZORY):
                with self.subTest(wzor["tytul"]):
                    zrodlo = os.path.join(katalog, f"w{i}.cpp")
                    with open(zrodlo, "w", encoding="utf-8") as f:
                        f.write(_kod(wzor, ""))
                    wynik = subprocess.run(
                        [KOMPILATOR, "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-pthread",
                         "-fsyntax-only", zrodlo], capture_output=True, text=True)
                    self.assertEqual(wynik.returncode, 0, wynik.stderr)

    @unittest.skipUnless(KOMPILATOR, "brak kompilatora C++")
    def test_liczba_z_pytania_trafia_do_programu(self):
        odp = napisz("liczby pierwsze do 50 w c++")
        self.assertIn("const int n = 50;", odp)
        kod = re.search(r"```cpp\n(.*?)```", odp, re.S).group(1)
        with tempfile.TemporaryDirectory() as katalog:
            zrodlo, program = os.path.join(katalog, "p.cpp"), os.path.join(katalog, "p")
            with open(zrodlo, "w", encoding="utf-8") as f:
                f.write(kod)
            subprocess.run([KOMPILATOR, "-std=c++17", zrodlo, "-o", program], check=True)
            wynik = subprocess.run([program], capture_output=True, text=True, check=True).stdout
        self.assertIn("2 3 5 7 11", wynik)
        self.assertIn("Liczb pierwszych do 50: 15", wynik)

    def test_liczba_jest_ograniczana(self):
        self.assertIn("const unsigned n = 20;", napisz("silnia 100 w c++"))  # 21! nie mieści się w uint64

    def test_wszystkie_wzory_maja_kod_i_opis(self):
        for wzor in WZORY:
            self.assertIn("int main()", wzor["kod"])
            self.assertTrue(wzor["opis"])
            self.assertEqual("{n}" in wzor["kod"], bool(wzor["liczba"]), wzor["tytul"])


class TestDopasowanie(unittest.TestCase):
    def test_wybiera_wzor(self):
        przypadki = {
            "napisz hello world w c++": "Hello world",
            "napisz program w C++ który sortuje liczby": "Sortowanie",
            "jak w c++ zrobić klasę": "Klasa",
            "pokaż przykład wskaźników w cpp": "Wskaźniki",
            "napisz w c++ grę w zgadywanie liczby": "Gra",
            "bfs w c++": "Graf",
            "napisz program w c++ który wczytuje tekst i liczy słowa": "Zliczanie słów",
            "c++ zapis do pliku": "Pliki",
            "napisz w c++ obsługę błędów": "Wyjątki",
            "jak użyć lambdy w c++": "Funkcje i lambdy",
            "tabliczka mnożenia do 12 w c++": "Tabliczka",
            "napisz w c plus plus palindrom": "Napisy",
        }
        for tekst, tytul in przypadki.items():
            self.assertTrue(dopasuj(tekst)["tytul"].startswith(tytul), tekst)

    def test_tylko_gdy_chodzi_o_cpp(self):
        self.assertIsNone(napisz("napisz sortowanie"))
        self.assertIsNone(napisz("gra w szachy"))
        self.assertIsNone(napisz("co to jest c++"))       # to pytanie o wiedzę, nie o kod
        self.assertTrue(prosi_o_kod("napisz w c++ program do biblioteki"))
        self.assertFalse(prosi_o_kod("lubię c++"))

    def test_c_plus_plus_jako_slowo(self):
        self.assertEqual(slowa("Co to jest C++? A C#?"), ["co", "to", "jest", "cpp", "a", "csharp"])


class TestBadekPiszeCpp(unittest.TestCase):
    def setUp(self):
        self.badek = PanBadek(katalog_pamieci=tempfile.mkdtemp(), ziarno=0, internet=False)

    def test_pisze_program(self):
        odp = self.badek.odpowiedz("Napisz w C++ sortowanie")
        self.assertEqual(self.badek.zrodlo, "programowanie")
        self.assertIn("```cpp", odp)
        self.assertIn("std::sort", odp)
        self.assertIn("g++ -std=c++17", odp)

    def test_kod_ma_pierwszenstwo_przed_matematyka(self):
        self.assertIn("```cpp", self.badek.odpowiedz("napisz w c++ fibonacci 30"))
        self.assertIn("832040", self.badek.odpowiedz("fibonacci 30"))
        self.assertEqual(self.badek.zrodlo, "matematyka")

    def test_pojecie_z_przykladem(self):
        odp = self.badek.odpowiedz("co to jest wskaźnik w c++")
        self.assertTrue(odp.startswith("Wskaźnik to zmienna"))
        self.assertIn("#### Przykład: Wskaźniki", odp)

    def test_wiedza_o_cpp(self):
        self.assertIn("Stroustrup", self.badek.odpowiedz("Co to jest C++?"))
        self.assertIn("rozszerzenie C", self.badek.odpowiedz("czym się różni c od c++"))
        self.assertIn("RAII", self.badek.odpowiedz("co to jest raii w c++"))

    def test_nietypowe_zamowienie_idzie_do_ai(self):
        tekst = "napisz w c++ program do zarządzania biblioteką"
        odp = self.badek.odpowiedz(tekst)
        self.assertEqual(self.badek.zrodlo, "nie_wiem")
        self.assertIn("Offline umiem", odp)
        self.assertTrue(self.badek.ocen_trudnosc(tekst))


if __name__ == "__main__":
    unittest.main()
