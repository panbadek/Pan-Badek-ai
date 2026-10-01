"""Testy samodzielnej nauki: baza wiedzy, nauka od AI, oceny, douczanie, notatki i wymiana pamięci."""

import json
import os
import tempfile
import unittest

from panbadek import PanBadek


class TestSamonauka(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.katalog = tmp.name
        self.badek = PanBadek(katalog_pamieci=self.katalog, ziarno=0, internet=False)

    def nowy(self):
        return PanBadek(katalog_pamieci=self.katalog, ziarno=0, internet=False)

    def test_siec_rozumie_zdania_testowe(self):
        self.assertGreaterEqual(self.badek.ocen_siec(), 0.9)

    def test_interpunkcja_nie_przeszkadza(self):
        for tekst in ["Cześć!", "cześć", "Cześć, Badku!!!", "Dzięki!", "Jak się masz?"]:
            self.assertIsNotNone(self.badek.rozpoznaj_intencje(tekst), tekst)
        self.assertIn("Paryż", self.badek.odpowiedz("Jaka jest stolica Francji?!"))

    def test_wbudowana_wiedza(self):
        self.assertIn("Warszawa", self.badek.odpowiedz("jaka jest stolica polski?"))
        self.assertEqual(self.badek.zrodlo, "wiedza")
        self.assertIn("Ciekawostka", self.badek.odpowiedz("powiedz ciekawostkę"))

    def test_lekcja_trafia_do_wiedzy_i_odpowiada_na_podobne_pytania(self):
        self.badek.odpowiedz("naucz się: jak ma na imię nasz kot => Nasz kot to Filemon!")
        self.assertEqual(self.nowy().odpowiedz("jak ma na imię kot?"), "Nasz kot to Filemon!")
        self.assertIn("Zapomniałem", self.badek.odpowiedz("zapomnij: jak ma na imię nasz kot"))

    def test_przenosi_lekcje_ze_starej_wersji(self):
        with open(os.path.join(self.katalog, "nauczone.json"), "w", encoding="utf-8") as f:
            json.dump({"imie": "Ola", "intencje": [{"nazwa": "nauczona_12", "nauczona": True,
                       "przyklady": ["ulubiony kolor"], "odpowiedzi": ["Zielony!"]}]}, f)
        badek = self.nowy()
        self.assertEqual(badek.imie, "Ola")
        self.assertEqual(badek.odpowiedz("jaki jest twój ulubiony kolor?"), "Zielony!")
        with open(os.path.join(self.katalog, "nauczone.json"), encoding="utf-8") as f:
            self.assertNotIn("intencje", json.load(f))

    def test_uczy_sie_od_duzego_modelu(self):
        id_wpisu = self.badek.naucz_od_ai("Jak szybko leci jaskółka?", "Jaskółka leci ok. 50 km/h.", "Claude")
        self.assertIsNotNone(id_wpisu)
        odp = self.nowy().odpowiedz("jak szybko lata jaskółka")
        self.assertIn("50 km/h", odp)
        self.assertIn("zapamiętałem od: Claude", odp)

    def test_nie_zapamietuje_pytan_zaleznych_od_rozmowy(self):
        self.assertIsNone(self.badek.naucz_od_ai("a ile to kosztuje?", "100 zł", "Claude"))
        self.assertIsNone(self.badek.naucz_od_ai("napisz wiersz o morzu", "Fale...", "Claude"))
        self.assertIsNone(self.badek.naucz_od_ai("hej", "Cześć!", "Claude"))

    def test_zla_ocena_usuwa_odpowiedz_ai(self):
        self.badek.naucz_od_ai("Ile nóg ma stonoga?", "Dokładnie 100.", "Qwen3.5 2B")
        self.badek.odpowiedz("ile nóg ma stonoga")
        self.assertEqual(self.badek.zrodlo, "wiedza")
        self.assertIn("Usunąłem", self.badek.ocen(self.badek.id_odpowiedzi, dobra=False))
        self.assertNotEqual(self.badek.odpowiedz("ile nóg ma stonoga"), "Dokładnie 100.")

    def test_ocena_slowami(self):
        self.badek.naucz_od_ai("Jaki kolor ma niebo na Marsie?", "Zielony.", "Claude")
        self.badek.odpowiedz("jaki kolor ma niebo na marsie?")
        self.assertIn("Usunąłem", self.badek.odpowiedz("źle"))
        self.assertEqual(self.badek.zrodlo, "ocena")

    def test_dobra_ocena_doucza_siec(self):
        self.badek.odpowiedz("elo elo witaj")
        self.assertEqual(self.badek.zrodlo, "siec_neuronowa")
        self.badek.ocen(self.badek.id_odpowiedzi, dobra=True)
        self.assertIn("elo elo witaj", self.nowy().dodatkowe_przyklady["powitanie"])

    def test_zla_ocena_oducza_siec(self):
        tekst = "mam dzisiaj zły dzień"
        intencja = self.badek.rozpoznaj_intencje(tekst)
        self.assertIsNotNone(intencja)
        self.badek.odpowiedz(tekst)
        self.badek.ocen(self.badek.id_odpowiedzi, dobra=False)
        self.assertIn(tekst, self.badek.dodatkowe_przyklady["inne"])
        self.assertIsNone(self.badek.rozpoznaj_intencje(tekst))
        self.assertIsNone(self.nowy().rozpoznaj_intencje(tekst))

    def test_notatki(self):
        self.assertIn("Twój pies ma na imię Burek", self.badek.odpowiedz("Zapamiętaj, że mój pies ma na imię Burek"))
        self.assertIn("Burek", self.nowy().odpowiedz("jak ma na imię mój pies?"))

    def test_dziennik_statystyki_i_czego_nie_wiem(self):
        for _ in range(3):
            self.badek.odpowiedz("kto wygrał turniej w kółko i krzyżyk")
        nowy = self.nowy()
        self.assertEqual(len(nowy.dziennik), 3)
        self.assertIn("kółko i krzyżyk", nowy.odpowiedz("czego nie wiesz?"))
        self.assertIn("baza wiedzy", nowy.odpowiedz("statystyki"))
        raport = nowy.odpowiedz("ucz się")
        self.assertIn("Skończyłem naukę", raport)
        self.assertIn("zdań testowych", raport)

    def test_eksport_i_import_pamieci(self):
        self.badek.odpowiedz("Mam na imię Ola")
        self.badek.odpowiedz("naucz się: hasło do wifi w domu => Jest na routerze.")
        self.badek.naucz_od_ai("Jak długo żyje żółw?", "Nawet ponad 100 lat.", "Claude")
        self.badek.odpowiedz("Zapamiętaj, że lubię pizzę")
        pamiec = json.loads(json.dumps(self.badek.eksport()))

        with tempfile.TemporaryDirectory() as inny:
            telefon = PanBadek(katalog_pamieci=inny, ziarno=0, internet=False)
            podsumowanie = telefon.importuj(pamiec)
            self.assertIn("2 nowe odpowiedzi", podsumowanie)
            self.assertEqual(telefon.imie, "Ola")
            self.assertIn("100 lat", telefon.odpowiedz("ile lat żyje żółw"))
            self.assertIn("pizzę", telefon.odpowiedz("co lubię jeść? pizzę?"))
            # Drugi import niczego nie dubluje.
            self.assertIn("0 nowych odpowiedzi", telefon.importuj(pamiec))
        with self.assertRaises(ValueError):
            self.badek.importuj({"cos": 1})


if __name__ == "__main__":
    unittest.main()
