"""Testy rozumowania: logika z wyjaśnieniem, łączenie faktów z liczbami i wzorami, sprawdzanie wyników."""

import datetime
import os
import tempfile
import unittest

from panbadek import PanBadek
from panbadek.matematyka import rozwiaz as matematyka
from panbadek.rozumowanie import Rozumowanie, lemat
from panbadek.szkola import czas_po_ludzku, liczba, rozwiaz as szkola

DZIS = datetime.date(2026, 10, 2)


class TestLogika(unittest.TestCase):
    def setUp(self):
        self.r = Rozumowanie(dzis=DZIS)

    def odp(self, pytanie):
        return self.r.odpowiedz(pytanie)

    def test_lemat(self):
        for formy, podstawa in ((["ssak", "ssaki", "ssakiem", "ssakami"], "ssak"),
                                (["kwiaty", "kwiatami"], "kwiat"), (["kot", "kotem", "koty"], "kot")):
            for forma in formy:
                self.assertEqual(lemat(forma), podstawa, forma)

    def test_wnioskowanie_przez_kilka_krokow(self):
        odp, pewna = self.odp("Czy kot jest zwierzęciem?")
        self.assertTrue(pewna)
        self.assertEqual(odp, "Tak. Kot jest ssakiem, ssak jest kręgowcem, a kręgowiec jest zwierzęciem.")

    def test_nie_z_grup_rozlacznych(self):
        self.assertEqual(self.odp("Czy wieloryb jest rybą?")[0],
                         "Nie. Wieloryb jest ssakiem, a ssaki i ryby to rozłączne grupy.")
        self.assertTrue(self.odp("Czy kot jest psem?")[0].startswith("Nie."))

    def test_cechy_dziedziczone(self):
        self.assertEqual(self.odp("Czy pingwin składa jaja?")[0], "Tak. Pingwin jest ptakiem, a ptak składa jaja.")
        self.assertTrue(self.odp("Czy wieloryb oddycha skrzelami?")[0].startswith("Nie."))
        odp, pewna = self.odp("Czy pies lubi koty?")
        self.assertFalse(pewna)
        self.assertIn("Nie wiem na pewno", odp)

    def test_geografia(self):
        self.assertEqual(self.odp("Czy Kraków leży w Europie?")[0],
                         "Tak. Kraków leży w Polsce, a Polska leży w Europie.")
        self.assertTrue(self.odp("Czy Kraków leży w Azji?")[0].startswith("Nie."))
        self.assertEqual(self.odp("gdzie leży Gdańsk")[0], "Gdańsk leży w Polsce, w Europie.")

    def test_przeslanki_w_pytaniu(self):
        przypadki = {
            "Wszystkie koty są ssakami. Filemon jest kotem. Czy Filemon jest ssakiem?":
                "Tak. Filemon jest kotem, a kot jest ssakiem.",
            "Wszystkie róże są kwiatami. Wszystkie kwiaty są roślinami. Czy róże są roślinami?":
                "Tak. Wszystkie róże są kwiatami, a wszystkie kwiaty są roślinami.",
            "Żaden ptak nie jest ssakiem. Wróbel jest ptakiem. Czy wróbel jest ssakiem?":
                "Nie. Wróbel jest ptakiem, a żaden ptak nie jest ssakiem.",
            "Każdy ptak ma pióra. Kiwi jest ptakiem. Czy kiwi ma pióra?": "Tak. Kiwi jest ptakiem, a ptak ma pióra.",
        }
        for pytanie, odpowiedz in przypadki.items():
            self.assertEqual(self.odp(pytanie)[0], odpowiedz, pytanie)
        # Przesłanki z pytania nie zostają w pamięci na stałe.
        self.assertIsNone(self.r._znajdz("Filemon"))

    def test_uczciwe_nie_wiem(self):
        odp, pewna = self.odp("Czy Burek jest ssakiem?")
        self.assertFalse(pewna)
        self.assertIn("Nie wiem", odp)

    def test_nie_przejmuje_innych_pytan(self):
        for pytanie in ["czy jutro jest sobota?", "czy to jest dobre", "czy możesz mi pomóc", "jak się masz"]:
            self.assertIsNone(self.odp(pytanie), pytanie)

    def test_nauka_na_stale(self):
        with tempfile.TemporaryDirectory() as katalog:
            plik = os.path.join(katalog, "rozumowanie.json")
            Rozumowanie(plik).naucz("Burek jest psem")
            odp, pewna = Rozumowanie(plik).odpowiedz("Czy Burek jest ssakiem?")
            self.assertTrue(pewna)
            self.assertEqual(odp, "Tak. Burek jest psem, a pies jest ssakiem.")


class TestLaczenieFaktow(unittest.TestCase):
    def setUp(self):
        self.r = Rozumowanie(dzis=DZIS)

    def odp(self, pytanie):
        return self.r.odpowiedz(pytanie)[0]

    def test_wiek_z_dokladnych_dat(self):
        self.assertIn("**70 lat**", self.odp("Ile lat żył Mikołaj Kopernik?"))
        skłodowska = self.odp("Ile lat żyła Maria Skłodowska-Curie?")
        self.assertIn("żyła **66 lat**", skłodowska)  # 1934 - 1867 = 67, ale urodziny były w listopadzie
        self.assertIn("dają 67", skłodowska)
        self.assertIn("**50 lat**", self.odp("Ile lat miał Piłsudski, gdy Polska odzyskała niepodległość?"))

    def test_lata_miedzy_wydarzeniami(self):
        self.assertIn("**508 lat**", self.odp("Ile lat minęło od bitwy pod Grunwaldem do odzyskania niepodległości?"))
        self.assertIn("**444 lata**", self.odp("Ile lat minęło między chrztem Polski a bitwą pod Grunwaldem?"))
        self.assertIn("**616 lat temu**", self.odp("Ile lat temu była bitwa pod Grunwaldem?"))

    def test_porownania(self):
        self.assertIn("**6350 m**", self.odp("O ile metrów Everest jest wyższy od Rysów?"))
        self.assertIn("3,54", self.odp("Ile razy Everest jest wyższy od Rysów?"))

    def test_fakty_we_wzorze(self):
        swiatlo = self.odp("Ile czasu leci światło ze Słońca do Ziemi?")
        self.assertIn("z mojej bazy faktów", swiatlo)
        self.assertIn("8 min 19 s", swiatlo)
        self.assertIn("✓", swiatlo)
        self.assertIn("3844 h (≈ 160 dni 4 h)", self.odp("Jak długo jechałby samochód z prędkością 100 km/h na Księżyc?"))
        self.assertIn("2,92 s", self.odp("Ile czasu potrzebuje dźwięk, żeby pokonać 1 km?"))


class TestLaczenieWzorowISprawdzanie(unittest.TestCase):
    def test_lancuch_wzorow(self):
        odp = szkola("Ciało ma gęstość 2 g/cm³ i objętość 500 cm³. Oblicz jego ciężar.")
        self.assertIn("łączę wzory (gęstość → ciężar)", odp)
        self.assertIn("**Krok 1 (gęstość):** m = 2000 kg/m³ · 0,0005 m³ = **1 kg**", odp)
        self.assertIn("**Odpowiedź:** Ciężar wynosi 10 N.", odp)
        self.assertIn("**3000 N**", szkola("Samochód o masie 1000 kg rozpędza się od 0 do 15 m/s w 5 s. "
                                           "Jaka siła na niego działa?"))

    def test_zasada_zachowania_energii(self):
        odp = szkola("Ciało o masie 2 kg uderzyło w ziemię z prędkością 20 m/s. Z jakiej wysokości spadło?")
        self.assertIn("Ek = Ep", odp)
        self.assertIn("**20 m**", odp)

    def test_sprawdzenie_w_fizyce(self):
        odp = szkola("Pieszy idzie z prędkością 5 km/h. Jaką drogę pokona w 30 minut?")
        self.assertIn("**Sprawdzenie:** v = 2,5 km / 0,5 h = 5 km/h ✓", odp)

    def test_sprawdzenie_rownan(self):
        self.assertIn("dla x = 5: lewa strona = 20, prawa strona = 20 ✓", matematyka("rozwiąż 3x + 5 = 20"))
        kwadratowe = matematyka("rozwiąż x^2 - 5x + 6 = 0")
        self.assertIn("dla x = 2", kwadratowe)
        self.assertIn("dla x = 3", kwadratowe)
        self.assertEqual(kwadratowe.count("✓"), 2)

    def test_formatowanie(self):
        self.assertEqual(liczba(149600000), "149 600 000")
        self.assertEqual(liczba(-12345.5), "-12 345,5")
        self.assertEqual(czas_po_ludzku(499), "8 min 19 s")


class TestWRozmowie(unittest.TestCase):
    def test_badek_laczy_fakty_i_uczy_sie(self):
        badek = PanBadek(katalog_pamieci=tempfile.mkdtemp(), ziarno=0, internet=False)
        self.assertTrue(badek.odpowiedz("Czy pingwin jest ptakiem?").startswith("Tak."))
        self.assertEqual(badek.zrodlo, "rozumowanie")
        badek.odpowiedz("Czy Burek jest ssakiem?")
        self.assertEqual(badek.zrodlo, "nie_wiem")  # w aplikacji przejmie to mocniejsze AI
        self.assertIn("Połączę to", badek.odpowiedz("zapamiętaj, że Burek jest psem"))
        self.assertEqual(badek.odpowiedz("Czy Burek jest ssakiem?"), "Tak. Burek jest psem, a pies jest ssakiem.")
        self.assertIn("8 min 19 s", badek.odpowiedz("Ile czasu leci światło ze Słońca do Ziemi?"))


if __name__ == "__main__":
    unittest.main()
