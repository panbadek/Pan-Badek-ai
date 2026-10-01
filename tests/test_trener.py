"""Testy trenera: augmentacja, walidacja krzyżowa, egzamin, wybór ustawień i nauczyciel (bez sieci)."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from panbadek import PanBadek, brain, trener
from panbadek.augmentacja import literowka, warianty
from panbadek.matematyka import rozwiaz

MALE_INTENCJE = [
    {"nazwa": "powitanie", "przyklady": ["cześć", "hej", "dzień dobry", "witaj", "siema", "hejka"],
     "odpowiedzi": ["Cześć!"]},
    {"nazwa": "pozegnanie", "przyklady": ["pa", "do widzenia", "na razie", "do zobaczenia", "nara", "dobranoc"],
     "odpowiedzi": ["Pa!"]},
    {"nazwa": "inne", "przyklady": ["ile lat żyje słoń", "jak działa silnik", "kto napisał lalkę",
                                    "gdzie leży australia", "jak ugotować makaron", "co to jest kwas"],
     "odpowiedzi": [""]},
]


class FalszywyKlient:
    """Udaje SDK Anthropic: zapisuje zapytania i zwraca przygotowane odpowiedzi JSON."""

    def __init__(self, odpowiedzi):
        self.odpowiedzi, self.zapytania = list(odpowiedzi), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **zapytanie):
        self.zapytania.append(zapytanie)
        tresc = self.odpowiedzi.pop(0)
        if tresc is None:
            return SimpleNamespace(stop_reason="refusal", content=[])
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps(tresc, ensure_ascii=False))])


class TestAugmentacja(unittest.TestCase):
    def test_warianty_sa_powtarzalne_i_rozne(self):
        self.assertEqual(warianty("jestem zmęczony", 3, 0), warianty("jestem zmęczony", 3, 0))
        w = warianty("opowiedz mi żart", 3, 0)
        self.assertEqual(len(w), 3)
        self.assertNotIn("opowiedz mi żart", w)

    def test_literowka_zmienia_tylko_dlugie_slowa(self):
        import random
        self.assertEqual(literowka("pa", random.Random(0)), "pa")
        self.assertNotEqual(literowka("dziękuję", random.Random(0)), "dziękuję")


class TestWalidacja(unittest.TestCase):
    def test_podzial_obejmuje_kazdy_przyklad_raz(self):
        czesci = trener.podziel(MALE_INTENCJE, 3, 0)
        sprawdzane = [t["tekst"] for _, test in czesci for t in test]
        wszystkie = [p for i in MALE_INTENCJE for p in i["przyklady"]]
        self.assertCountEqual(sprawdzane, wszystkie)
        for trening, test in czesci:  # zdanie sprawdzane nie trafia do treningu
            uczone = {p for i in trening for p in i["przyklady"]}
            self.assertFalse(uczone & {t["tekst"] for t in test})

    def test_ustawienia_wracaja_po_tescie(self):
        przed = dict(brain.USTAWIENIA)
        with trener.ustawienia({"neurony": 7}):
            self.assertEqual(brain.USTAWIENIA["neurony"], 7)
        self.assertEqual(brain.USTAWIENIA, przed)

    def test_strojenie_wybiera_najprostsze_bliskie_najlepszemu(self):
        kandydaci = [{"neurony": 16, "epoki": 100, "tempo": 0.05, "warianty": 0},
                     {"neurony": 8, "epoki": 100, "tempo": 0.05, "warianty": 0}]
        wyniki = trener.strojenie(MALE_INTENCJE, kandydaci, k=2, ziarna=(0,), wypisz=lambda *_: None)
        self.assertEqual(len(wyniki), 2)
        najlepsza = max(w["walidacja"] for w in wyniki)
        self.assertGreaterEqual(wyniki[0]["walidacja"], najlepsza - trener.TOLERANCJA)
        if wyniki[1]["walidacja"] >= najlepsza - trener.TOLERANCJA:
            self.assertEqual(wyniki[0]["ustawienia"]["neurony"], 8)

    def test_literowki_w_zestawach_testowych(self):
        zestawy = trener.zestawy_testowe()
        self.assertIn("literówki", zestawy)
        self.assertGreater(len(zestawy["literówki"]), 100)


class TestEgzamin(unittest.TestCase):
    def test_egzamin_ocenia_kategorie(self):
        with tempfile.TemporaryDirectory() as katalog:
            plik = os.path.join(katalog, "egzamin.json")
            with open(plik, "w", encoding="utf-8") as f:
                json.dump({"pytania": [
                    {"pytanie": "cześć", "kategoria": "rozmowa", "intencja": "powitanie"},
                    {"pytanie": "rozwiąż 2x = 4", "kategoria": "matematyka", "zawiera": ["x = 2"]},
                    {"pytanie": "jak naprawić przerzutkę", "kategoria": "uczciwosc", "zrodlo": ["nie_wiem"]},
                    {"pytanie": "ile lat żyje kot", "kategoria": "pulapki", "nie_intencja": True},
                    {"pytanie": "ile to 2+2", "kategoria": "matematyka", "zawiera": ["5"]},
                ]}, f)
            wyniki = trener.egzamin(plik=plik)
        self.assertEqual(wyniki["rozmowa"][:2], (1, 1))
        self.assertEqual(wyniki["matematyka"][:2], (1, 2))  # 2+2 to nie 5
        self.assertEqual(wyniki["uczciwosc"][:2], (1, 1))
        self.assertEqual(wyniki["pulapki"][:2], (1, 1))

    def test_polecenie_egzaminu(self):
        wyjscie = io.StringIO()
        with redirect_stdout(wyjscie):
            trener.main(["--egzamin"])
        self.assertIn("RAZEM", wyjscie.getvalue())
        self.assertIn("Egzamin kontrolny", wyjscie.getvalue())


class TestNauczyciel(unittest.TestCase):
    def test_parafrazy_i_zapytanie(self):
        klient = FalszywyKlient([{"zdania": ["siemka badku", "x" * 200, "  "]}])
        zdania = trener.Nauczyciel(klient).parafrazy("powitanie", ["cześć"])
        self.assertEqual(zdania, ["siemka badku"])  # za długie i puste odpadają
        zapytanie = klient.zapytania[0]
        self.assertEqual(zapytanie["model"], "claude-opus-5-5")
        self.assertEqual(zapytanie["fallbacks"], "default")
        self.assertEqual(zapytanie["output_config"]["format"]["type"], "json_schema")

    def test_odmowa_i_niepewne_odpowiedzi_nie_sa_zapamietywane(self):
        n = trener.Nauczyciel(FalszywyKlient([None, {"odpowiedz": "Zależy od dnia.", "pewna": False},
                                              {"odpowiedz": "Papugi żyją 20-80 lat.", "pewna": True}]))
        self.assertIsNone(n.parafrazy("powitanie", ["cześć"]) or None)
        self.assertIsNone(n.odpowiedz("kiedy otwierają sklep"))
        self.assertEqual(n.odpowiedz("ile lat żyją papugi"), "Papugi żyją 20-80 lat.")

    def test_nie_dopisuje_zdan_testowych(self):
        testowe = trener.zestawy_testowe()["trudne"][0]["tekst"]  # "czesc"
        odpowiedzi = [{"zdania": [testowe, "elo elo elo", "cześć"]}] + [{"zdania": []}] * 2
        nowe, _, _ = trener.nauczyciel_przyklady(MALE_INTENCJE, trener.Nauczyciel(FalszywyKlient(odpowiedzi)),
                                                 k=2, wypisz=lambda *_: None)
        dodane = [p for p in nowe[0]["przyklady"] if p not in MALE_INTENCJE[0]["przyklady"]]
        self.assertNotIn(testowe, dodane)
        self.assertNotIn("cześć", dodane)  # już było

    def test_uczy_odpowiedzi_na_pytania_z_rozmow(self):
        badek = PanBadek(katalog_pamieci=tempfile.mkdtemp(), ziarno=0, internet=False)
        badek.odpowiedz("ile lat żyją papugi")
        badek.odpowiedz("ile lat żyją papugi")
        klient = FalszywyKlient([{"odpowiedz": "Papugi żyją od 20 do nawet 80 lat.", "pewna": True}])
        self.assertEqual(trener.nauczyciel_wiedza(badek, trener.Nauczyciel(klient), wypisz=lambda *_: None), 1)
        self.assertIn("80 lat", badek.odpowiedz("ile lat żyją papugi"))


class TestGotowyModel(unittest.TestCase):
    def test_po_aktualizacji_wczytuje_gotowy_model_zamiast_trenowac(self):
        with tempfile.TemporaryDirectory() as zrodlo, tempfile.TemporaryDirectory() as pamiec:
            PanBadek(katalog_pamieci=zrodlo, ziarno=0, internet=False)  # "budowanie strony"
            with open(os.path.join(pamiec, "model.json"), "w", encoding="utf-8") as f:
                json.dump({"odcisk": "stara wersja", "cechy": [], "siec": {}}, f)
            stary_trening = PanBadek.trenuj
            def trenuj(_):
                raise AssertionError("po aktualizacji Badek nie powinien trenować sieci od nowa")
            PanBadek.trenuj = trenuj
            try:
                badek = PanBadek(katalog_pamieci=pamiec, internet=False,
                                 gotowy_model=os.path.join(zrodlo, "model.json"))
            finally:
                PanBadek.trenuj = stary_trening
            self.assertEqual(badek.rozpoznaj_intencje("cześć"), "powitanie")
            with open(os.path.join(pamiec, "model.json"), encoding="utf-8") as f:
                self.assertNotEqual(json.load(f)["odcisk"], "stara wersja")  # zapisany w pamięci


class TestPoprawkiZEgzaminu(unittest.TestCase):
    def setUp(self):
        self.badek = PanBadek(katalog_pamieci=tempfile.mkdtemp(), ziarno=0, internet=False)

    def test_synonimy(self):
        self.assertIn("Rysy", self.badek.odpowiedz("Jak nazywa się najwyższa góra w Polsce?"))
        self.assertIn("Prus", self.badek.odpowiedz("Kto jest autorem Lalki?"))

    def test_nie_podmienia_pytania(self):
        for tekst in ["ile lat żyją papugi", "kto rządzi w Brazylii", "jak zrobić sushi"]:
            self.badek.odpowiedz(tekst)
            self.assertEqual(self.badek.zrodlo, "nie_wiem", tekst)
        self.assertIn("966", self.badek.odpowiedz("W którym roku był chrzest Polski?"))

    def test_dzien_tygodnia(self):
        self.assertIn("sobota", rozwiaz("jaki dzień tygodnia był 1 stycznia 2000"))
        self.assertIn("wtorek", rozwiaz("jaki dzień tygodnia będzie 24.12.2030"))
        self.assertIsNone(rozwiaz("jaki dzień tygodnia był 31 lutego 2000"))


if __name__ == "__main__":
    unittest.main()
