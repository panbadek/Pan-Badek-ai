"""Mózg Pana Badka: łączy sieć neuronową, umiejętności i pamięć."""

import json
import os
import random
import re

from . import skills
from .network import SiecNeuronowa
from .text import Slownik

KATALOG = os.path.dirname(os.path.abspath(__file__))
DOMYSLNE_INTENCJE = os.path.join(KATALOG, "data", "intencje.json")
DOMYSLNA_PAMIEC = os.path.join(os.path.expanduser("~"), ".panbadek")

PROG_PEWNOSCI = 0.45

_NAUCZ = re.compile(r"^\s*naucz\s+si[eę]\s*:?\s*(.+?)\s*=>\s*(.+?)\s*$", re.I | re.S)
_IMIE = re.compile(r"\b(?i:mam\s+na\s+imi[eę]|nazywam\s+si[eę]|jestem)\s+([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+)")
_JAK_MAM_NA_IMIE = re.compile(r"jak\s+(?:mam\s+na\s+imi[eę]|si[eę]\s+nazywam)", re.I)

NIE_WIEM = [
    "Hmm, tego jeszcze nie wiem. Naucz mnie: 'naucz się: {pytanie} => odpowiedź'.",
    "Nie jestem pewien, o co chodzi. Możesz to powiedzieć inaczej?",
]


class PanBadek:
    def __init__(self, plik_intencji=DOMYSLNE_INTENCJE, katalog_pamieci=DOMYSLNA_PAMIEC,
                 ziarno=None):
        self.katalog_pamieci = katalog_pamieci
        self.plik_nauki = os.path.join(katalog_pamieci, "nauczone.json") if katalog_pamieci else None
        self.plik_modelu = os.path.join(katalog_pamieci, "model.json") if katalog_pamieci else None
        self.los = random.Random(ziarno)
        self.ziarno = ziarno
        self.imie = None

        with open(plik_intencji, encoding="utf-8") as f:
            self.intencje = json.load(f)["intencje"]
        self.intencje += self._wczytaj_nauczone()

        if not self._wczytaj_model():
            self.trenuj()

    # --- pamięć -------------------------------------------------------------

    def _wczytaj_nauczone(self):
        if self.plik_nauki and os.path.exists(self.plik_nauki):
            with open(self.plik_nauki, encoding="utf-8") as f:
                dane = json.load(f)
            self.imie = dane.get("imie")
            return dane.get("intencje", [])
        return []

    def _zapisz_nauczone(self):
        if not self.plik_nauki:
            return
        os.makedirs(self.katalog_pamieci, exist_ok=True)
        nauczone = [i for i in self.intencje if i.get("nauczona")]
        with open(self.plik_nauki, "w", encoding="utf-8") as f:
            json.dump({"imie": self.imie, "intencje": nauczone}, f, ensure_ascii=False, indent=2)

    def _odcisk_danych(self):
        """Pozwala wykryć, że intencje się zmieniły i model trzeba wytrenować od nowa."""
        return json.dumps([[i["nazwa"], i["przyklady"]] for i in self.intencje], ensure_ascii=False)

    def _wczytaj_model(self):
        if not self.plik_modelu or not os.path.exists(self.plik_modelu):
            return False
        try:
            with open(self.plik_modelu, encoding="utf-8") as f:
                dane = json.load(f)
            if dane["odcisk"] != self._odcisk_danych():
                return False
            self.slownik = Slownik(dane["cechy"])
            self.siec = SiecNeuronowa.ze_slownika(dane["siec"])
            return True
        except (OSError, ValueError, KeyError):
            return False

    def _zapisz_model(self):
        if not self.plik_modelu:
            return
        os.makedirs(self.katalog_pamieci, exist_ok=True)
        with open(self.plik_modelu, "w", encoding="utf-8") as f:
            json.dump({"odcisk": self._odcisk_danych(), "cechy": self.slownik.lista(),
                       "siec": self.siec.do_slownika()}, f)

    # --- uczenie ------------------------------------------------------------

    def trenuj(self):
        przyklady = [(p, k) for k, i in enumerate(self.intencje) for p in i["przyklady"]]
        self.slownik = Slownik.zbuduj(p for p, _ in przyklady)
        self.siec = SiecNeuronowa(len(self.slownik), 32, len(self.intencje), ziarno=self.ziarno)
        dane = [(self.slownik.wektor(p), k) for p, k in przyklady]
        strata = self.siec.trenuj(dane, ziarno=self.ziarno)
        self._zapisz_model()
        return strata

    def naucz(self, pytanie, odpowiedz):
        """Dodaje nową wiedzę i trenuje sieć od nowa."""
        for intencja in self.intencje:
            if intencja.get("nauczona") and pytanie in intencja["przyklady"]:
                intencja["odpowiedzi"] = [odpowiedz]
                break
        else:
            self.intencje.append({"nazwa": f"nauczona_{len(self.intencje)}", "nauczona": True,
                                  "przyklady": [pytanie], "odpowiedzi": [odpowiedz]})
        self._zapisz_nauczone()
        self.trenuj()

    # --- myślenie -----------------------------------------------------------

    def klasyfikuj(self, tekst):
        """Zwraca (intencja, pewność) dla podanego tekstu."""
        wektor = self.slownik.wektor(tekst)
        if not wektor:
            return None, 0.0
        prawd = self.siec.przewiduj(wektor)
        najlepsza = max(range(len(prawd)), key=prawd.__getitem__)
        return self.intencje[najlepsza], prawd[najlepsza]

    def _wypelnij(self, szablon):
        return szablon.format(imie=self.imie or "przyjacielu",
                              imie_po_przecinku=f", {self.imie}" if self.imie else "")

    def odpowiedz(self, tekst):
        tekst = tekst.strip()
        if not tekst:
            return "Powiedz coś - słucham!"

        nauka = _NAUCZ.match(tekst)
        if nauka:
            pytanie, odpowiedz = nauka.groups()
            self.naucz(pytanie, odpowiedz)
            return f"Zapamiętałem! Na '{pytanie}' odpowiem: '{odpowiedz}'."

        if _JAK_MAM_NA_IMIE.search(tekst):
            if self.imie:
                return f"Masz na imię {self.imie}."
            return "Jeszcze mi nie powiedziałeś. Napisz: 'mam na imię ...'."

        imie = _IMIE.search(tekst)
        if imie:
            self.imie = imie.group(1)
            self._zapisz_nauczone()
            return f"Miło mi cię poznać, {self.imie}!"

        wynik = skills.kalkulator(tekst)
        if wynik:
            return wynik

        intencja, pewnosc = self.klasyfikuj(tekst)
        if intencja is None or pewnosc < PROG_PEWNOSCI:
            return self.los.choice(NIE_WIEM).format(pytanie=tekst)

        akcja = intencja.get("akcja")
        if akcja == "godzina":
            return skills.godzina()
        if akcja == "data":
            return skills.data()
        return self._wypelnij(self.los.choice(intencja["odpowiedzi"]))
