"""Testy wersji przeglądarkowej: mostek dla Pyodide, źródło odpowiedzi i budowanie strony."""

import json
import os
import sys
import tempfile
import unittest
import zipfile

from panbadek import PanBadek, przegladarka

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "narzedzia"))
import zbuduj_strone  # noqa: E402


class TestZrodloOdpowiedzi(unittest.TestCase):
    def setUp(self):
        self.badek = PanBadek(katalog_pamieci=None, ziarno=0, internet=False)

    def zrodlo(self, tekst):
        self.badek.odpowiedz(tekst)
        return self.badek.zrodlo

    def test_rozpoznaje_kto_odpowiedzial(self):
        self.assertEqual(self.zrodlo("cześć"), "siec_neuronowa")
        self.assertEqual(self.zrodlo("ile to 2+2"), "kalkulator")
        self.assertEqual(self.zrodlo("Mam na imię Ola"), "polecenia_pamieci")
        self.assertEqual(self.zrodlo("asdf qwerty zxcv"), "nie_wiem")
        self.assertEqual(self.zrodlo("jak długo śpią koty?"), "wiedza")
        self.badek.biblioteki.dodaj("zwierzaki", "Chomik Puszek uwielbia marchewkę.")
        self.assertEqual(self.zrodlo("co uwielbia chomik Puszek?"), "biblioteka")


class TestMostPrzegladarki(unittest.TestCase):
    def test_czat_i_zdjecie_przez_json(self):
        with tempfile.TemporaryDirectory() as katalog:
            self.assertEqual(json.loads(przegladarka.start(katalog)), {"imie": None})
            wynik = json.loads(przegladarka.czat("Mam na imię Ola"))
            self.assertEqual(wynik["imie"], "Ola")
            self.assertEqual(wynik["zrodlo"], "polecenia_pamieci")
            piksele = bytes([70, 140, 230] * 32 * 16 + [50, 160, 60] * 32 * 16)
            wynik = json.loads(przegladarka.zdjecie(32, 32, 4000, 4000, piksele, b""))
            self.assertIn("4000×4000", wynik["odpowiedz"])
            # W przeglądarce nie wolno przeglądać plików po ścieżce.
            self.assertFalse(przegladarka._badek.pliki_lokalne)


class TestBudowanieStrony(unittest.TestCase):
    def test_zbuduj(self):
        with tempfile.TemporaryDirectory() as tmp:
            cel = zbuduj_strone.zbuduj(os.path.join(tmp, "site"))
            pliki = set(os.listdir(cel))
            for wymagany in ["index.html", "app.js", "badek-worker.js", "llm-worker.js", "sw.js",
                             "etykiety.json", "panbadek.zip", "model.json", "manifest.webmanifest",
                             "ikona-192.png", "ikona-512.png", "apple-touch-icon.png"]:
                self.assertIn(wymagany, pliki)
            with zipfile.ZipFile(os.path.join(cel, "panbadek.zip")) as z:
                nazwy = z.namelist()
            self.assertIn("panbadek/przegladarka.py", nazwy)
            self.assertIn("panbadek/data/intencje.json", nazwy)
            self.assertNotIn("panbadek/web.py", nazwy)
            with open(os.path.join(cel, "sw.js"), encoding="utf-8") as f:
                self.assertNotIn("__WERSJA__", f.read())
            with open(os.path.join(cel, "manifest.webmanifest"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["start_url"], "./")

            # Gotowy model musi pasować do intencji - inaczej telefon i tak trenowałby od nowa.
            pamiec = os.path.join(tmp, "pamiec")
            os.makedirs(pamiec)
            with open(os.path.join(cel, "model.json"), "rb") as zrodlo, \
                    open(os.path.join(pamiec, "model.json"), "wb") as kopia:
                kopia.write(zrodlo.read())
            badek = PanBadek(katalog_pamieci=pamiec, internet=False)
            self.assertTrue(badek._wczytaj_model())

    def test_etykiety_rozpoznawania(self):
        with open(os.path.join(zbuduj_strone.KORZEN, "web", "etykiety.json"), encoding="utf-8") as f:
            etykiety = json.load(f)
        with open(os.path.join(zbuduj_strone.KORZEN, "narzedzia", "kategorie.json"), encoding="utf-8") as f:
            kategorie = json.load(f)
        self.assertEqual(etykiety["etykiety"], [pl for pl, _ in kategorie])
        import base64
        self.assertEqual(len(base64.b64decode(etykiety["wektory"])), len(kategorie) * etykiety["wymiar"])


if __name__ == "__main__":
    unittest.main()
