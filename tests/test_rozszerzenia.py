"""Testy internetu, bibliotek, wtyczek i czatu w przeglądarce (bez prawdziwej sieci)."""

import json
import os
import tempfile
import threading
import unittest
import urllib.request
from unittest import mock

from panbadek import PanBadek, internet
from panbadek.biblioteki import Biblioteki
from panbadek.brain import kandydaci_miasta
from panbadek.web import stworz_serwer

ARTYKUL = ("Kraków – miasto na prawach powiatu w południowej Polsce, położone nad Wisłą. "
           "W latach 1038–1596 był stolicą Polski. Na Wawelu znajduje się zamek królewski. "
           "W 1978 r. Stare Miasto wpisano na listę UNESCO. Kraków jest siedzibą Uniwersytetu "
           "Jagiellońskiego, założonego w 1364 roku.")


def falszywa_wikipedia(haslo, caly_artykul=False):
    if "krak" in haslo.lower():
        return "Kraków", ARTYKUL, "https://pl.wikipedia.org/wiki/Krak%C3%B3w"
    return None


class TestZdania(unittest.TestCase):
    def test_nie_tnie_na_skrotach(self):
        zdania = internet.podziel_na_zdania(ARTYKUL)
        self.assertEqual(len(zdania), 5)
        self.assertTrue(zdania[3].startswith("W 1978 r. Stare Miasto"))

    def test_odmiana(self):
        from panbadek.brain import odmien
        self.assertEqual([odmien(n, "wpis", "wpisy", "wpisów") for n in (1, 3, 5, 12, 22)],
                         ["wpis", "wpisy", "wpisów", "wpisów", "wpisy"])

    def test_kandydaci_miasta(self):
        self.assertEqual(kandydaci_miasta("Krakowie")[0], "Kraków")
        self.assertEqual(kandydaci_miasta("Warszawie")[0], "Warszawa")
        self.assertEqual(kandydaci_miasta("Gdańsku")[0], "Gdańsk")
        self.assertIn("Zakopane", kandydaci_miasta("Zakopane"))


class TestInternet(unittest.TestCase):
    def test_kurs_nbp(self):
        odp = {"currency": "euro", "code": "EUR",
               "rates": [{"effectiveDate": "2026-10-01", "mid": 4.377}]}
        with mock.patch.object(internet, "pobierz_json", return_value=odp) as pobierz:
            self.assertIn("1 EUR (euro) = 4.3770 zł", internet.kurs("euro"))
        self.assertIn("/eur/", pobierz.call_args[0][0])

    def test_ponawia_po_zerwanym_polaczeniu(self):
        bledy = [internet.BladInternetu("timeout", chwilowy=True), {"ok": 1}]
        with mock.patch.object(internet, "_pobierz", side_effect=bledy) as pobierz:
            self.assertEqual(internet.pobierz_json("https://example.invalid"), {"ok": 1})
        self.assertEqual(pobierz.call_count, 2)

    def test_nieznana_waluta(self):
        self.assertIn("Nie znam", internet.kurs("ziemniaki"))

    def test_pogoda(self):
        odpowiedzi = [
            {"results": [{"name": "Kraków", "country": "Polska", "latitude": 50, "longitude": 20}]},
            {"current": {"temperature_2m": 18.2, "apparent_temperature": 16, "weather_code": 3,
                         "wind_speed_10m": 7},
             "daily": {"temperature_2m_min": [9], "temperature_2m_max": [20]}},
        ]
        with mock.patch.object(internet, "pobierz_json", side_effect=odpowiedzi):
            wynik = internet.pogoda("Kraków")
        self.assertIn("Kraków, Polska: pochmurno, 18°C", wynik)

    def test_wikipedia_parsuje_odpowiedz(self):
        odp = {"query": {"pages": [{"title": "Kraków", "extract": ARTYKUL,
                                    "fullurl": "https://pl.wikipedia.org/wiki/Krak%C3%B3w"}]}}
        with mock.patch.object(internet, "pobierz_json", return_value=odp) as pobierz:
            tytul, tekst, _ = internet.wikipedia("Kraków")
        self.assertEqual(tytul, "Kraków")
        self.assertEqual(pobierz.call_args[0][1]["exintro"], "1")


class TestBiblioteki(unittest.TestCase):
    def setUp(self):
        self.katalog = tempfile.TemporaryDirectory()
        self.addCleanup(self.katalog.cleanup)

    def test_tworzy_szuka_i_pamieta(self):
        b = Biblioteki(self.katalog.name)
        b.stworz("Zwierzęta")
        b.dodaj("zwierzeta", "Słoń jest największym zwierzęciem lądowym.",
                "Gepard to najszybszy ssak na lądzie.")
        wynik, nazwa, wpis = b.szukaj("który ssak jest najszybszy?")[0]
        self.assertIn("Gepard", wpis)
        self.assertEqual(nazwa, "Zwierzęta")

        nowa = Biblioteki(self.katalog.name)
        self.assertEqual(nowa.lista(), [("Zwierzęta", 2, "")])
        self.assertTrue(nowa.usun("ZWIERZĘTA"))
        self.assertEqual(Biblioteki(self.katalog.name).lista(), [])

    def test_odrzuca_dziwne_nazwy(self):
        with self.assertRaises(ValueError):
            Biblioteki(self.katalog.name).stworz("../../etc")


class TestPanBadekRozszerzony(unittest.TestCase):
    def setUp(self):
        self.katalog = tempfile.TemporaryDirectory()
        self.addCleanup(self.katalog.cleanup)
        self.badek = PanBadek(katalog_pamieci=self.katalog.name, ziarno=0)
        lata = mock.patch.object(internet, "wikipedia", side_effect=falszywa_wikipedia)
        lata.start()
        self.addCleanup(lata.stop)

    def test_co_to_jest_i_wiecej(self):
        odp = self.badek.odpowiedz("Co to jest Kraków?")
        self.assertIn("Wisłą", odp)
        self.assertIn("(Wikipedia: Kraków)", odp)
        self.assertIn("Wawelu", self.badek.odpowiedz("powiedz więcej"))
        self.assertIn("Jagiellońskiego", self.badek.odpowiedz("więcej"))
        self.assertIn("wszystko", self.badek.odpowiedz("więcej"))

    def test_nie_szuka_w_internecie_o_sobie(self):
        with mock.patch.object(internet, "wikipedia") as wiki:
            self.badek.odpowiedz("opowiedz o sobie")
        wiki.assert_not_called()

    def test_biblioteka_z_internetu_dziala_offline(self):
        odp = self.badek.odpowiedz("stwórz bibliotekę o Krakowie")
        self.assertIn("„Kraków”", odp)
        offline = PanBadek(katalog_pamieci=self.katalog.name, ziarno=0, internet=False)
        self.assertIn("1364", offline.odpowiedz("kiedy założono uniwersytet jagielloński?"))
        self.assertIn("Kraków (5 wpisów)", offline.odpowiedz("pokaż biblioteki"))

    def test_wlasna_biblioteka(self):
        self.assertIn("gotowa", self.badek.odpowiedz("stwórz bibliotekę przepisy"))
        self.badek.odpowiedz("dodaj do przepisy: Na naleśniki potrzeba mąki, mleka i jajek.")
        self.assertIn("mąki", self.badek.odpowiedz("czego potrzeba na naleśniki?"))

    def test_offline_nie_lacza_sie(self):
        badek = PanBadek(katalog_pamieci=None, ziarno=0, internet=False)
        with mock.patch.object(internet, "pobierz_json") as pobierz:
            self.assertIn("offline", badek.odpowiedz("pogoda w Krakowie"))
            self.assertIn("offline", badek.odpowiedz("kurs euro"))
        pobierz.assert_not_called()

    def test_brak_internetu_nie_wywraca(self):
        with mock.patch.object(internet, "pobierz_json",
                               side_effect=internet.BladInternetu("brak połączenia z internetem")):
            self.assertIn("brak połączenia", self.badek.odpowiedz("kurs euro"))

    def test_pogoda_dla_zapamietanego_miasta(self):
        self.badek.odpowiedz("Mieszkam w Krakowie")
        with mock.patch.object(internet, "pogoda", return_value="Pogoda – Kraków") as pogoda:
            self.assertEqual(self.badek.odpowiedz("jaka jest dziś pogoda?"), "Pogoda – Kraków")
        pogoda.assert_called_with("Kraków")

    def test_ile_kosztuje_chleb_to_nie_waluta(self):
        with mock.patch.object(internet, "kurs") as kurs:
            self.badek.odpowiedz("ile kosztuje chleb")
        kurs.assert_not_called()

    def test_siec_nie_strzela_na_obcych_zdaniach(self):
        intencja, _ = self.badek.klasyfikuj("kurs programowania")
        self.assertIsNone(intencja)

    def test_zapomnij(self):
        self.badek.odpowiedz("naucz się: ulubiony kolor => Zielony!")
        self.assertIn("Zapomniałem", self.badek.odpowiedz("zapomnij: ulubiony kolor"))
        self.assertNotEqual(self.badek.odpowiedz("ulubiony kolor"), "Zielony!")

    def test_wtyczki(self):
        odp = self.badek.odpowiedz("stwórz wtyczkę rzut kostką")
        sciezka = os.path.join(self.katalog.name, "wtyczki", "rzut_kostka.py")
        self.assertIn(sciezka, odp)
        self.assertIn("Tu wtyczka", self.badek.odpowiedz("uruchom rzut_kostka"))

        with open(os.path.join(self.katalog.name, "wtyczki", "echo.py"), "w") as f:
            f.write("def obsluz(tekst, badek):\n"
                    "    return 'ECHO ' + tekst[5:] if tekst.startswith('echo ') else None\n")
        with open(os.path.join(self.katalog.name, "wtyczki", "zepsuta.py"), "w") as f:
            f.write("to nie jest python(")
        odp = self.badek.odpowiedz("przeładuj wtyczki")
        self.assertIn("echo", odp)
        self.assertIn("zepsuta.py", odp)
        self.assertEqual(self.badek.odpowiedz("echo halo"), "ECHO halo")


class TestWeb(unittest.TestCase):
    def test_api_czatu(self):
        badek = PanBadek(katalog_pamieci=None, ziarno=0, internet=False)
        serwer = stworz_serwer(badek, port=0)
        watek = threading.Thread(target=serwer.serve_forever, daemon=True)
        watek.start()
        self.addCleanup(serwer.server_close)
        self.addCleanup(serwer.shutdown)
        adres = f"http://127.0.0.1:{serwer.server_address[1]}"

        with urllib.request.urlopen(adres + "/") as odp:
            self.assertIn("Pan Badek", odp.read().decode("utf-8"))
        zapytanie = urllib.request.Request(adres + "/api/czat",
                                           data=json.dumps({"tekst": "ile to 6*7"}).encode(),
                                           headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(zapytanie) as odp:
            self.assertEqual(json.load(odp)["odpowiedz"], "6*7 = 42")


if __name__ == "__main__":
    unittest.main()
