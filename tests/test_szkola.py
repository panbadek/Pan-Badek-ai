"""Testy zadań szkolnych i nauki z filmów YouTube (YouTube jest tu udawany - bez sieci)."""

import json
import os
import sys
import tempfile
import unittest

from panbadek import PanBadek, internet, youtube
from panbadek.szkola import rozwiaz

DANE = os.path.join(os.path.dirname(__file__), "dane")


class TestFizyka(unittest.TestCase):
    def test_ruch_z_zamiana_jednostek(self):
        odp = rozwiaz("Pieszy idzie z prędkością 5 km/h. Jaką drogę pokona w 30 minut?")
        for fragment in ("**Dane:** v = 5 km/h, t = 30 min", "t = 30 min = 0,5 h", "**Wzór:** s = v · t",
                         "**2,5 km**", "**Odpowiedź:** Droga wynosi 2,5 km."):
            self.assertIn(fragment, odp)
        self.assertIn("**20 km/h**", rozwiaz("Rowerzysta przejechał 30 km w 1,5 godziny. Z jaką prędkością jechał?"))
        self.assertIn("**3 h**", rozwiaz("Pociąg jedzie z prędkością 90 km/h. Ile czasu zajmie mu przejechanie 270 km?"))

    def test_inne_wzory(self):
        przypadki = {
            "Ciało o masie 5 kg porusza się z przyspieszeniem 2 m/s². Jaka siła na nie działa?": "**10 N**",
            "Oblicz gęstość ciała o masie 200 g i objętości 50 cm³.": "**4 g/cm³**",
            "Jaką pracę wykona siła 20 N na drodze 5 m?": "**100 J**",
            "Silnik wykonał pracę 600 J w czasie 20 s. Jaka jest jego moc?": "**30 W**",
            "Oblicz natężenie prądu, jeśli napięcie wynosi 12 V, a opór 4 Ω.": "**3 A**",
            "Kamień o masie 0,5 kg leży na wysokości 10 m. Oblicz jego energię potencjalną.": "**50 J**",
        }
        for zadanie, wynik in przypadki.items():
            self.assertIn(wynik, rozwiaz(zadanie), zadanie)

    def test_energia_kinetyczna_z_km_h(self):
        odp = rozwiaz("Samochód o masie 1000 kg jedzie z prędkością 72 km/h. Oblicz jego energię kinetyczną.")
        self.assertIn("v = 72 km/h = 20 m/s", odp)
        self.assertIn("(20 m/s)²", odp)
        self.assertIn("**200 000 J**", odp)


class TestGeometria(unittest.TestCase):
    def test_figury(self):
        przypadki = {
            "Oblicz pole prostokąta o bokach 5 cm i 8 cm.": "**40 cm²**",
            "Oblicz obwód koła o promieniu 3 cm.": "6π cm ≈ 18,85 cm",
            "Oblicz pole koła o średnicy 10 cm.": "25π cm²",
            "Oblicz objętość walca o promieniu podstawy 2 cm i wysokości 10 cm.": "40π cm³",
            "Oblicz pole trapezu o podstawach 6 cm i 4 cm i wysokości 3 cm.": "**15 cm²**",
            "Oblicz objętość prostopadłościanu o wymiarach 2 dm, 3 dm i 4 dm.": "**24 dm³**",
            "Jaka jest przekątna kwadratu o boku 4 cm?": "4√2 cm",
            "Oblicz pole prostokąta o bokach 2 m i 50 cm.": "**10 000 cm²**",
        }
        for zadanie, wynik in przypadki.items():
            self.assertIn(wynik, rozwiaz(zadanie), zadanie)

    def test_pitagoras(self):
        self.assertIn("**5 cm**", rozwiaz("Przyprostokątne trójkąta prostokątnego mają 3 cm i 4 cm. Oblicz przeciwprostokątną."))
        self.assertIn("**12 cm**", rozwiaz("Przeciwprostokątna ma 13 cm, a jedna przyprostokątna 5 cm. Oblicz drugą przyprostokątną."))


class TestProcentyITresc(unittest.TestCase):
    def test_procenty(self):
        self.assertIn("**170 zł**", rozwiaz("Kurtka kosztowała 200 zł. Cenę obniżono o 15%. Ile kosztuje teraz?"))
        self.assertIn("**30 zł**", rozwiaz("Po podwyżce o 10% bilet kosztuje 33 zł. Ile kosztował przed podwyżką?"))
        self.assertIn("**7**", rozwiaz("W klasie jest 28 uczniów, 25% to dziewczynki. Ile jest dziewczynek?"))

    def test_zadania_z_trescia(self):
        przypadki = {
            "Ania miała 12 cukierków. Zjadła 3, a potem dostała 5 od babci. Ile cukierków ma teraz?": "12 − 3 + 5 = **14**",
            "Tomek kupił 4 paczki po 6 naklejek. Ile naklejek kupił?": "4 · 6 = **24**",
            "Mama upiekła 24 ciastka i podzieliła je po równo między 4 dzieci. Ile ciastek dostało każde dziecko?": "24 : 4 = **6**",
            "Ola ma 5 lat, a jej brat jest o 3 lata starszy. Ile lat ma brat?": "5 + 3 = **8**",
            "Jaś ma 6 kulek, a Staś ma 3 razy więcej. Ile kulek ma Staś?": "6 · 3 = **18**",
            "Marek miał 15 zł. Kupił lody za 4 zł i dostał od mamy 10 zł. Ile ma teraz złotych?": "15 − 4 + 10 = **21**",
        }
        for zadanie, wynik in przypadki.items():
            self.assertIn(wynik, rozwiaz(zadanie), zadanie)
        self.assertIn("**Odpowiedź:** 14 cukierków.", rozwiaz(next(iter(przypadki))))

    def test_nie_zgaduje(self):
        for tekst in ["ile to 2+2", "mam 3 koty i 2 psy", "jaka jest stolica polski", "rozwiąż 2x + 3 = 7",
                      "100 km na mile", "ile to 15% z 200", "Ola ma 5 lat. Ile lat ma jej kot?"]:
            self.assertIsNone(rozwiaz(tekst), tekst)

    def test_w_rozmowie(self):
        badek = PanBadek(katalog_pamieci=tempfile.mkdtemp(), ziarno=0, internet=False)
        self.assertIn("**Dane:**", badek.odpowiedz("Samochód jedzie z prędkością 60 km/h przez 3 godziny. Jaką drogę przejedzie?"))
        self.assertEqual(badek.zrodlo, "szkola")
        self.assertIn("x = 2", badek.odpowiedz("rozwiąż 2x + 3 = 7"))  # równania dalej robi solver matematyczny


class TestYouTube(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(DANE, "youtube_odtwarzacz.json"), encoding="utf-8") as f:
            self.odtwarzacz = f.read()
        with open(os.path.join(DANE, "youtube_napisy.xml"), encoding="utf-8") as f:
            self.napisy = f.read()
        self.zapytania = []
        self.oryginal = internet.pobierz_tekst

        def falszywe(url, dane=None, naglowki=None, limit_czasu=10):
            self.zapytania.append((url, dane))
            return self.odtwarzacz if "youtubei" in url else self.napisy
        internet.pobierz_tekst = falszywe
        self.badek = PanBadek(katalog_pamieci=tempfile.mkdtemp(), ziarno=0, internet=True)

    def tearDown(self):
        internet.pobierz_tekst = self.oryginal

    def test_id_filmu(self):
        for link in ["https://www.youtube.com/watch?v=abcdefghijk", "https://youtu.be/abcdefghijk?t=10",
                     "youtube.com/shorts/abcdefghijk", "https://m.youtube.com/watch?feature=share&v=abcdefghijk"]:
            self.assertEqual(youtube.id_filmu(link), "abcdefghijk", link)
        self.assertIsNone(youtube.id_filmu("https://example.com/watch?v=abcdefghijk"))

    def test_oglada_film_i_odpowiada_z_notatek(self):
        odp = self.badek.odpowiedz("obejrzyj https://www.youtube.com/watch?v=abcdefghijk")
        self.assertIn("Obejrzałem „Fotosynteza - lekcja biologii”", odp)
        self.assertIn("automatycznych napisów (pl)", odp)  # polskie napisy mają pierwszeństwo przed angielskimi
        self.assertIn("**W skrócie:**", odp)
        self.assertIn("chlorofil", odp)
        self.assertEqual(self.zapytania[0][1]["videoId"], "abcdefghijk")
        self.assertNotIn("fmt=", self.zapytania[1][0])
        self.badek.internet = False
        self.assertIn("lugola", self.badek.odpowiedz("czym wykryć skrobię").lower())
        self.assertIn("W skrócie", self.badek.odpowiedz("o czym był film?"))
        self.assertIn("Film - Fotosynteza", self.badek.odpowiedz("jakie filmy obejrzałeś"))

    def test_film_bez_napisow(self):
        self.odtwarzacz = json.dumps({"videoDetails": {"title": "Bez napisów"}})
        self.napisy = ""
        self.assertIn("nie ma napisów", self.badek.odpowiedz("https://youtu.be/abcdefghijk"))

    def test_przegladarka_prosi_o_wklejenie_transkrypcji(self):
        def blad(*_, **__):
            raise internet.BladInternetu("strona nie pozwala na dostęp z przeglądarki")
        internet.pobierz_tekst = blad
        stara, sys.platform = sys.platform, "emscripten"
        try:
            odp = self.badek.odpowiedz("obejrzyj https://youtu.be/abcdefghijk")
        finally:
            sys.platform = stara
        self.assertIn("Pokaż transkrypcję", odp)
        self.assertIn("naucz się z tekstu", odp)

    def test_parsery_formatow(self):
        json3 = json.dumps({"events": [{"tStartMs": 0, "segs": [{"utf8": "Cześć "}, {"utf8": "wszystkim"}]},
                                       {"tStartMs": 1500, "segs": [{"utf8": "[Muzyka]"}]}]})
        self.assertEqual(youtube.parsuj_napisy(json3), [(0.0, "Cześć wszystkim")])
        srv3 = '<timedtext><body><p t="2000" d="900"><s>Ala</s><s> ma kota</s></p></body></timedtext>'
        self.assertEqual(youtube.parsuj_napisy(srv3), [(2.0, "Ala ma kota")])
        self.assertEqual(youtube.parsuj_napisy('<transcript><text start="1.5">It&amp;#39;s ok</text></transcript>'),
                         [(1.5, "It's ok")])

    def test_nauka_z_wklejonego_tekstu(self):
        tekst = ("Mikołaj Kopernik urodził się w 1473 roku w Toruniu. Studiował w Krakowie, a potem we Włoszech. "
                 "Stworzył teorię heliocentryczną. Według niej to Ziemia krąży wokół Słońca, a nie odwrotnie. "
                 "Swoje dzieło O obrotach sfer niebieskich wydał w 1543 roku.")
        odp = self.badek.odpowiedz("naucz się z tekstu: " + tekst)
        self.assertIn("Przeczytałem tekst (5 zdań)", odp)
        self.badek.internet = False
        self.assertIn("1543", self.badek.odpowiedz("kiedy wydał dzieło o obrotach sfer niebieskich"))
        self.assertIn("za krótki", self.badek.odpowiedz("naucz się z tekstu: Ala ma kota."))


if __name__ == "__main__":
    unittest.main()
