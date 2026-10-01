"""Mózg Pana Badka: łączy sieć neuronową, internet, biblioteki wiedzy, wtyczki i pamięć."""

import json
import os
import random
import re
import time
from zlib import error as zlib_error

from . import exif, internet, matematyka, obrazy, skills, wtyczki
from .biblioteki import NIEISTOTNE, Biblioteki
from .network import SiecNeuronowa
from .text import Slownik, cechy, normalizuj, rdzen
from .wiedza import BazaWiedzy, istotne_slowa

KATALOG = os.path.dirname(os.path.abspath(__file__))
DOMYSLNE_INTENCJE = os.path.join(KATALOG, "data", "intencje.json")
DOMYSLNA_PAMIEC = os.path.join(os.path.expanduser("~"), ".panbadek")
WBUDOWANA_WIEDZA = os.path.join(KATALOG, "data", "wiedza.json")
TESTY_INTENCJI = os.path.join(KATALOG, "data", "test_intencje.json")

NEURONY_UKRYTE = 48
# Baza wiedzy odpowiada, gdy pytanie jest wystarczająco podobne do zapamiętanego.
PROG_WIEDZY = 0.45
PROG_WIEDZY_PEWNY = 0.8
LIMIT_DZIENNIKA = 3000
NOTATKI = "Moje notatki"
# Wytrenowane sieci w tym procesie (te same dane -> ten sam model, bez ponownego treningu).
_GOTOWE_MODELE = {}

PROG_PEWNOSCI = 0.45
# Minimalne podobieństwo, żeby odpowiedzieć faktem z biblioteki.
PROG_BIBLIOTEKI = 0.30
# Na pytanie "co to jest X" biblioteka musi pasować wyraźnie, inaczej pytamy Wikipedię.
PROG_BIBLIOTEKI_PEWNY = 0.45
BIBLIOTEKA_INTERNETU = "Internet"
ZDANIA_NA_RAZ = 2
LIMIT_ZDAN_BIBLIOTEKI = 80

_I = re.I | re.S
_KONIEC = r"\s*[.!?]*\s*$"
_STWORZ = r"^\s*(?:stw[oó]rz|zr[oó]b|utw[oó]rz|za[lł][oó][zż])\s+(?:now[aą]\s+)?"
_NAZWA_WLASNA = r"([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+(?:[ -][A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+)?)"

_NAUCZ = re.compile(r"^\s*naucz\s+si[eę]\s*:?\s*(.+?)\s*=>\s*(.+?)\s*$", _I)
_ZAPOMNIJ = re.compile(r"^\s*zapomnij\s*:?\s*(.+?)" + _KONIEC, _I)
_IMIE = re.compile(r"\b(?i:mam\s+na\s+imi[eę]|nazywam\s+si[eę]|jestem)\s+([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+)")
_JAK_MAM_NA_IMIE = re.compile(r"jak\s+(?:mam\s+na\s+imi[eę]|si[eę]\s+nazywam)", re.I)
_MIESZKAM = re.compile(r"\b(?i:mieszkam\s+we?)\s+" + _NAZWA_WLASNA)

_BIBLIOTEKA_O = re.compile(_STWORZ + r"bibliotek[eęa]\s+o\s+(.+?)" + _KONIEC, _I)
_BIBLIOTEKA_NOWA = re.compile(_STWORZ + r"bibliotek[eęa]\s+(.+?)" + _KONIEC, _I)
_DODAJ = re.compile(r"^\s*dodaj\s+do\s+(?:biblioteki\s+)?(.+?)\s*:\s*(.+?)\s*$", _I)
_LISTA_BIBLIOTEK = re.compile(
    r"^\s*(?:(?:poka[zż]|lista|wymie[nń])\s+(?:moje\s+|swoje\s+)?bibliotek\w*"
    r"|jakie\s+masz\s+biblioteki)" + _KONIEC, _I)
_USUN_BIBLIOTEKE = re.compile(r"^\s*usu[nń]\s+bibliotek[eęa]\s+(.+?)" + _KONIEC, _I)
_WTYCZKA = re.compile(_STWORZ + r"wtyczk[eęa]\s+(.+?)" + _KONIEC, _I)
_PRZELADUJ = re.compile(r"^\s*prze[lł]aduj\s+wtyczki" + _KONIEC, _I)
_LISTA_WTYCZEK = re.compile(r"^\s*(?:poka[zż]|lista)\s+wtycz\w*" + _KONIEC, _I)

_POGODA = re.compile(r"\bpogod\w*", re.I)
_POGODA_MIASTO = re.compile(r"\b(?i:pogod\w*)\s+" + _NAZWA_WLASNA)
_MIEJSCE = re.compile(r"\b(?:w|we|dla)\s+([\wąćęłńóśźż-]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+)?)", re.I)
_NIE_MIEJSCA = {"tym", "ten", "ta", "nocy", "dzien", "weekend", "przyszlym", "przyszly",
                "poniedzialek", "wtorek", "srode", "czwartek", "piatek", "sobote", "niedziele"}
_KURS = re.compile(r"\bkurs\w*\s+(?:walut[ya]?\s+)?([a-ząćęłńóśźż]+)" + _KONIEC, _I)
_ILE_KOSZTUJE = re.compile(r"\bile\s+(?:kosztuje|jest\s+wart[ye]?|wynosi)\s+([a-ząćęłńóśźż]+)" + _KONIEC, _I)
_WIKI = re.compile(
    r"^\s*(?:co\s+to\s+(?:jest|s[aą]|by[lł][aoy]?)|kim\s+(?:jest|by[lł][aoy]?)"
    r"|czym\s+(?:jest|by[lł][aoy]?)|co\s+wiesz\s+o|opowiedz\s+(?:mi\s+)?o"
    r"|wikipedia|wyszukaj|szukaj|znajd[zź])\s*:?\s+(.+?)" + _KONIEC, _I)
_WIECEJ = re.compile(
    r"^\s*(?:(?:powiedz|opowiedz|napisz)\s+)?(?:mi\s+)?(?:co[sś]\s+)?(?:wi[eę]cej|dalej)"
    r"(?:\s+o\s+tym)?" + _KONIEC + r"|^\s*kontynuuj" + _KONIEC, _I)

_O_SOBIE = {"sobie", "tobie", "ciebie", "ty"}

# Samodzielna nauka i oceny.
_ZAPAMIETAJ_ZE = re.compile(r"^\s*zapami[eę]taj\s*,?\s*(?:że|ze)\s+(.+?)\s*[.!]*\s*$", _I)
_UCZ_SIE = re.compile(r"^\s*(?:ucz\s+si[eę]|trenuj(?:\s+si[eę])?|ulepsz\s+si[eę]|popraw\s+si[eę]"
                      r"|przetw[oó]rz\s+(?:wiedz[eę]|rozmowy))" + _KONIEC, _I)
_STATYSTYKI = re.compile(r"^\s*(?:statystyki|ile\s+wiesz|ile\s+umiesz|czego\s+si[eę]\s+nauczy[lł]e[sś]"
                         r"|co\s+ju[zż]\s+wiesz)" + _KONIEC, _I)
_CZEGO_NIE_WIESZ = re.compile(r"^\s*(?:czego\s+(?:jeszcze\s+)?nie\s+wiesz|czego\s+nie\s+umiesz"
                              r"|o\s+co\s+ci[eę]\s+pytaj[aą])" + _KONIEC, _I)
_OCENA_DOBRA = re.compile(r"^\s*(?:dobra\s+odpowied[zź]|dobrze\s+odpowiedzia[lł]e[sś]|zgadza\s+si[eę]"
                          r"|poprawnie|dok[lł]adnie\s+tak|👍)" + _KONIEC, _I)
_OCENA_ZLA = re.compile(r"^\s*(?:[zź]le|[zź]le\s+odpowiedzia[lł]e[sś]|z[lł]a\s+odpowied[zź]|to\s+nieprawda"
                        r"|nieprawda|mylisz\s+si[eę]|to\s+b[lł][aą]d|bzdura|👎)" + _KONIEC, _I)
# Pytania zależne od kontekstu rozmowy albo prośby o twórczość nie nadają się do zapamiętania.
_KONTEKSTOWE = re.compile(r"\b(to|tego|tym|ten|ta|tamto|on|ona|ono|oni|jego|jej|ich|wcze[sś]niej|"
                          r"powy[zż]ej|wy[zż]ej|poprzedni\w*|m[oó]j|moja|moje|moich|moim|mojego|mojej)\b", re.I)
_TWORCZE = re.compile(r"^\s*(napisz|wymy[sś]l|u[lł][oó][zż]|stw[oó]rz|przet[lł]umacz|popraw|stre[sś][cć]"
                      r"|zredaguj|narysuj|opowiedz\s+(?:mi\s+)?(?:bajk|histori))", re.I)
# Zamiana pierwszej osoby na drugą w notatkach: "mój pies" -> "twój pies".
_NA_TY = {"mój": "twój", "moja": "twoja", "moje": "twoje", "mojego": "twojego", "mojej": "twojej",
          "moim": "twoim", "moich": "twoich", "mam": "masz", "jestem": "jesteś", "mnie": "ciebie",
          "mi": "ci", "lubię": "lubisz", "mieszkam": "mieszkasz", "pracuję": "pracujesz"}

_TO_JEST = re.compile(
    r"^\s*(?:to\s+(?:jest|s[aą])|zapami[eę]taj\s+(?:to\s+)?(?:zdj[eę]cie\s+)?jako"
    r"|na\s+zdj[eę]ciu\s+(?:jest|s[aą]))\s*:?\s+(.+?)" + _KONIEC, _I)
_ZDJECIE_Z_PLIKU = re.compile(
    r"^\s*(?:(?:prze)?analizuj|opisz|oce[nń]|sprawd[zź]|poka[zż])?\s*"
    r"(?:zdj[eę]cie|obraz(?:ek)?|fotk[eę]|plik)\s*:?\s+(.+?)\s*$", _I)
_PYTANIE_O_ZDJECIE = re.compile(r"(analiz|opisz|co\s+jest\s+na|rozpozn|oce[nń]|wy[sś]l)", re.I)
_SLOWO_ZDJECIE = re.compile(r"zdj[eę]|obraz|fotk|foto", re.I)
_ZNANE_ZDJECIA = re.compile(r"^\s*(?:jakie|co)\s+(?:zdj[eę]cia|obrazy|rzeczy)\s+"
                            r"(?:znasz|rozpoznajesz)" + _KONIEC, _I)
_ZAPOMNIJ_ZDJECIA = re.compile(r"^\s*zapomnij\s+(?:wszystkie\s+)?zdj[eę]cia" + _KONIEC, _I)
LIMIT_ZDJEC = 500

# Najczęstsze polskie końcówki miejscownika ("w Krakowie") -> mianownik ("Kraków").
_MIANOWNIK = [("owie", "ów"), ("awie", "awa"), ("dzi", "dź"), ("niu", "ń"), ("sku", "sk"),
              ("cku", "ck"), ("iu", ""), ("ach", "e"), ("ynie", "yn"), ("inie", "in"),
              ("ie", ""), ("em", "e"), ("u", ""), ("i", "ia")]

NIE_WIEM = ("Nie znam odpowiedzi na to pytanie i wolę nie zgadywać. Mogę za to:\n"
            "- poszukać w Wikipedii - napisz „co to jest …” albo „kim był …”\n"
            "- nauczyć się od ciebie - „naucz się: {pytanie} => odpowiedź”\n"
            "- oddać pytanie mocniejszemu AI (w aplikacji: ⚙️ → model w telefonie albo Claude)")
TRUDNY_PROBLEM = ("To złożony problem, który wymaga rozumowania krok po kroku - z takim sam sobie "
                  "rzetelnie nie poradzę i nie chcę udawać, że jest inaczej. Włącz mocniejszy mózg "
                  "(w aplikacji: ⚙️ → Claude albo model w telefonie), a przekażę mu to zadanie "
                  "w trybie głębokiego myślenia. Zadania matematyczne - równania, pochodne, całki, "
                  "procenty - mogę za to policzyć sam.")
NIE_ROZUMIEM = "Nie jestem pewien, o co pytasz. Możesz to ująć inaczej albo dodać trochę szczegółów?"

# Sygnały kryzysu - na nie Badek zawsze odpowiada z troską i numerami pomocy, nigdy przypadkowo.
_KRYZYS = re.compile(
    r"(chc[eę]\s+(?:si[eę]\s+)?(?:zabi[cć]|umrze[cć])|nie\s+chc[eę]\s+(?:ju[zż]\s+)?[zż]y[cć]"
    r"|samob[oó]j|odebra[cć]\s+sobie\s+[zż]ycie|sko[nń]czy[cć]\s+ze\s+sob[aą]|zrobi[cć]\s+sobie\s+krzywd"
    r"|skrzywdzi[cć]\s+(?:si[eę]|siebie)|tn[eę]\s+si[eę]|nie\s+ma\s+sensu\s+[zż]y[cć]"
    r"|my[sś]l[eę]\s+o\s+[sś]mierci|lepiej\s+(?:by\s+)?by[lł]o\s+(?:by\s+)?beze\s+mnie)", re.I)
WSPARCIE = ("Bardzo mi przykro, że tak się czujesz. To, co przeżywasz, jest ważne - i nie musisz radzić "
            "sobie z tym w pojedynkę. Porozmawiaj, proszę, z kimś, kto może pomóc od razu:\n"
            "- **116 123** - Kryzysowy Telefon Zaufania dla dorosłych\n"
            "- **800 70 2222** - Centrum Wsparcia, całą dobę i bezpłatnie\n"
            "- **116 111** - Telefon Zaufania dla Dzieci i Młodzieży\n"
            "- **112** - jeśli jesteś w bezpośrednim niebezpieczeństwie\n"
            "Jeśli chcesz, napisz mi, co się dzieje. Jestem tutaj i wysłucham.")

# Dopytania w stylu "a Niemiec?", "a w Gdańsku?" - odnoszą się do poprzedniego pytania.
_DOPYTANIE = re.compile(r"^\s*a\s+(?:co\s+z\s+|jak\s+z\s+)?(.{1,40}?)\s*\??\s*$", re.I)
_PRZYIMKI = {"w", "we", "dla", "na", "do", "z", "ze", "od", "o"}
# Złożone problemy - warto je oddać dużemu modelowi z "głębokim myśleniem".
_TRUDNE = re.compile(
    r"(udowodnij|dowód|dowod|uzasadnij|wyjaśnij\s+(?:dlaczego|jak|krok)|krok\s+po\s+kroku|porównaj"
    r"|przeanalizuj|zaplanuj|zaprojektuj|napisz\s+(?:program|kod|funkcj|skrypt|algorytm|esej)|algorytm"
    r"|zoptymalizuj|zdebuguj|b[lł][aą]d\s+w\s+kodzie|prawdopodobie[nń]stw|granic[aęy]\s+funkcji"
    r"|zadani[ea]|strategi|rozwa[zż]|za\s+i\s+przeciw|plusy\s+i\s+minusy|jak\s+najlepiej)", re.I)


def odmien(liczba, jeden, kilka, wiele):
    """Polska odmiana po liczebniku: 1 wpis, 3 wpisy, 5 wpisów, 22 wpisy, 12 wpisów."""
    if liczba == 1:
        return jeden
    if liczba % 10 in (2, 3, 4) and liczba % 100 not in (12, 13, 14):
        return kilka
    return wiele


def kandydaci_miasta(miasto):
    """Zamienia 'Krakowie' na listę prawdopodobnych mianowników do wyszukania."""
    miasto = miasto.strip(" .,!?")
    kandydaci = []
    for koncowka, zamiana in _MIANOWNIK:
        if miasto.lower().endswith(koncowka) and len(miasto) > len(koncowka) + 2:
            kandydaci.append(miasto[:-len(koncowka)] + zamiana)
    kandydaci.append(miasto)
    return list(dict.fromkeys(kandydaci))


class PanBadek:
    def __init__(self, plik_intencji=DOMYSLNE_INTENCJE, katalog_pamieci=DOMYSLNA_PAMIEC,
                 ziarno=None, internet=True):
        self.katalog_pamieci = katalog_pamieci
        sciezka = (lambda nazwa: os.path.join(katalog_pamieci, nazwa)) if katalog_pamieci else (lambda _: None)
        self.plik_nauki = sciezka("nauczone.json")
        self.plik_modelu = sciezka("model.json")
        self.katalog_wtyczek = sciezka("wtyczki")
        self.los = random.Random(ziarno)
        self.ziarno = ziarno
        self.internet = internet
        self.imie = None
        self.miasto = None
        # Ostatni temat z internetu - do obsługi "powiedz więcej".
        self.kontekst = None
        self.zrodlo = None
        # Cechy ostatnio analizowanego zdjęcia - czekają na podpis "to jest ...".
        self.ostatnie_zdjecie = None
        # Czy wolno czytać zdjęcia z dysku po ścieżce (w czacie przez sieć - nie).
        self.pliki_lokalne = True
        self.plik_zdjec = sciezka("zdjecia.json")
        self.zdjecia = []
        if self.plik_zdjec and os.path.exists(self.plik_zdjec):
            try:
                with open(self.plik_zdjec, encoding="utf-8") as f:
                    self.zdjecia = json.load(f)
            except (OSError, ValueError):
                self.zdjecia = []

        with open(plik_intencji, encoding="utf-8") as f:
            self.intencje = json.load(f)["intencje"]
        # Przykłady dopisane z ocen 👍/👎 - sieć douczana jest na nich bez trenowania od zera.
        self.dodatkowe_przyklady = {}
        self.wiedza = BazaWiedzy(sciezka("wiedza.json"), WBUDOWANA_WIEDZA)
        self._przenies_stare_lekcje(self._wczytaj_nauczone())
        self.plik_dziennika = sciezka("dziennik.jsonl")
        self.dziennik = self._wczytaj_dziennik()
        # Ostatnie odpowiedzi (do ocen 👍/👎): numer -> co odpowiedziało i na co.
        self.odpowiedzi = {}
        self.id_odpowiedzi = None
        self._kolejna_odpowiedz = 0
        self._zrodlo_szczegol = None
        self.biblioteki = Biblioteki(sciezka("biblioteki"))
        self.wtyczki, self.bledy_wtyczek = wtyczki.wczytaj(self.katalog_wtyczek)

        if not self._wczytaj_model():
            self.trenuj()

    # --- pamięć -------------------------------------------------------------

    def _wczytaj_nauczone(self):
        if self.plik_nauki and os.path.exists(self.plik_nauki):
            with open(self.plik_nauki, encoding="utf-8") as f:
                dane = json.load(f)
            self.imie = dane.get("imie")
            self.miasto = dane.get("miasto")
            self.dodatkowe_przyklady = dane.get("dodatkowe_przyklady", {})
            return dane.get("intencje", [])
        return []

    def _przenies_stare_lekcje(self, stare):
        """Lekcje z wersji <0.7 były osobnymi klasami sieci - teraz trafiają do bazy wiedzy."""
        for lekcja in stare:
            if lekcja.get("przyklady") and lekcja.get("odpowiedzi"):
                self.wiedza.dodaj(lekcja["przyklady"][0], lekcja["odpowiedzi"][0], "ty")
        if stare:
            self._zapisz_nauczone()

    def _wczytaj_dziennik(self):
        if not self.plik_dziennika or not os.path.exists(self.plik_dziennika):
            return []
        wpisy = []
        with open(self.plik_dziennika, encoding="utf-8") as f:
            for linia in f:
                try:
                    wpisy.append(json.loads(linia))
                except ValueError:
                    continue
        return wpisy[-LIMIT_DZIENNIKA:]

    def _zapisz_w_dzienniku(self, tekst, zrodlo):
        wpis = {"czas": int(time.time()), "tekst": tekst[:500], "zrodlo": zrodlo}
        self.dziennik.append(wpis)
        if not self.plik_dziennika:
            return
        os.makedirs(self.katalog_pamieci, exist_ok=True)
        if len(self.dziennik) > LIMIT_DZIENNIKA * 1.5:
            self.dziennik = self.dziennik[-LIMIT_DZIENNIKA:]
            with open(self.plik_dziennika, "w", encoding="utf-8") as f:
                f.writelines(json.dumps(w, ensure_ascii=False) + "\n" for w in self.dziennik)
        else:
            with open(self.plik_dziennika, "a", encoding="utf-8") as f:
                f.write(json.dumps(wpis, ensure_ascii=False) + "\n")

    def _zapisz_nauczone(self):
        if not self.plik_nauki:
            return
        os.makedirs(self.katalog_pamieci, exist_ok=True)
        with open(self.plik_nauki, "w", encoding="utf-8") as f:
            json.dump({"imie": self.imie, "miasto": self.miasto,
                       "dodatkowe_przyklady": self.dodatkowe_przyklady},
                      f, ensure_ascii=False, indent=2)

    def _odcisk_danych(self):
        """Pozwala wykryć, że dane treningowe się zmieniły i model trzeba wytrenować od nowa."""
        return json.dumps(sorted(self.przyklady_treningowe().items()), ensure_ascii=False)

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

    def przyklady_treningowe(self):
        """Nazwa intencji -> zdania treningowe (wbudowane i dopisane z ocen)."""
        return {i["nazwa"]: i["przyklady"] + self.dodatkowe_przyklady.get(i["nazwa"], [])
                for i in self.intencje}

    def _dane_treningowe(self):
        przyklady = self.przyklady_treningowe()
        return [(p, k) for k, i in enumerate(self.intencje) for p in przyklady[i["nazwa"]]]

    def trenuj(self):
        """Trenuje sieć od zera na wszystkich przykładach. Zwraca końcową stratę."""
        klucz = (self._odcisk_danych(), self.ziarno)
        if klucz in _GOTOWE_MODELE:
            cechy_slownika, siec, strata = _GOTOWE_MODELE[klucz]
            self.slownik = Slownik(cechy_slownika)
            self.siec = SiecNeuronowa.ze_slownika(json.loads(siec))
            self._zapisz_model()
            return strata
        przyklady = self._dane_treningowe()
        self.slownik = Slownik.zbuduj(p for p, _ in przyklady)
        self.siec = SiecNeuronowa(len(self.slownik), NEURONY_UKRYTE, len(self.intencje), ziarno=self.ziarno)
        dane = [(self.slownik.wektor(p), k) for p, k in przyklady]
        strata = self.siec.trenuj(dane, ziarno=self.ziarno)
        if self.ziarno is not None:
            _GOTOWE_MODELE[klucz] = (self.slownik.lista(), json.dumps(self.siec.do_slownika()), strata)
        self._zapisz_model()
        return strata

    def dotrenuj(self, nowe=(), epoki=30):
        """Douczanie po nowych przykładach: sieć zachowuje wiedzę, dostaje nowe słowa
        i kilka epok treningu - zamiast trenowania od zera. Świeże przykłady liczą się
        kilka razy mocniej, żeby jedna ocena wystarczyła do poprawy."""
        przyklady = self._dane_treningowe()
        nowe_cechy = self.slownik.rozszerz(p for p, _ in przyklady)
        if nowe_cechy:
            self.siec.dodaj_wejscia(nowe_cechy, ziarno=self.ziarno)
        nazwy = [i["nazwa"] for i in self.intencje]
        dane = [(self.slownik.wektor(p), k) for p, k in przyklady]
        dane += [(self.slownik.wektor(t), nazwy.index(n)) for t, n in nowe if n in nazwy] * 4
        strata = self.siec.trenuj(dane, epoki=epoki, tempo=0.03, ziarno=self.ziarno)
        self._zapisz_model()
        return strata

    def dodaj_przyklad(self, tekst, intencja):
        """Dopisuje zdanie do przykładów intencji i douczą sieć."""
        lista = self.dodatkowe_przyklady.setdefault(intencja, [])
        if tekst in lista:
            return
        for inne in self.dodatkowe_przyklady.values():
            if tekst in inne:
                inne.remove(tekst)
        lista.append(tekst)
        self._zapisz_nauczone()
        self.dotrenuj(nowe=[(tekst, intencja)])

    def naucz(self, pytanie, odpowiedz):
        """Lekcja od użytkownika: trafia do bazy wiedzy (bez trenowania sieci)."""
        return self.wiedza.dodaj(pytanie, odpowiedz, "ty")

    def zapomnij(self, pytanie):
        """Usuwa zapamiętaną odpowiedź na pytanie. Zwraca True, jeśli coś usunięto."""
        wpis, podobienstwo = self.wiedza.szukaj(pytanie)
        if wpis and podobienstwo >= PROG_WIEDZY_PEWNY:
            return self.wiedza.usun(wpis["id"])
        return False

    def naucz_od_ai(self, pytanie, odpowiedz, zrodlo):
        """Zapamiętuje odpowiedź dużego modelu AI, żeby następnym razem odpowiedzieć samemu.
        Zwraca numer wpisu w bazie wiedzy albo None, gdy pytanie nie nadaje się do zapamiętania."""
        pytanie, odpowiedz = pytanie.strip(), (odpowiedz or "").strip()
        slowa = istotne_slowa(pytanie)
        if (len(slowa) < 2 or len(pytanie) > 300 or len(odpowiedz) < 2 or _TWORCZE.match(pytanie)
                or _KONTEKSTOWE.search(pytanie)):
            return None
        return self.wiedza.dodaj(pytanie, odpowiedz, zrodlo)["id"]

    def ocen(self, id_odpowiedzi, dobra):
        """Ocena 👍/👎 odpowiedzi - Badek uczy się na niej. Zwraca komunikat."""
        info = self.odpowiedzi.get(id_odpowiedzi)
        if not info:
            return "Nie pamiętam już tej odpowiedzi, ale dziękuję za ocenę!"
        if info.get("wiedza"):
            wynik = self.wiedza.ocen(info["wiedza"], dobra)
            if wynik == "usunieto":
                return "Usunąłem tę odpowiedź z pamięci. Następnym razem poszukam lepszej."
            return "Dzięki! Zapamiętam, że to dobra odpowiedź." if dobra else \
                "Dzięki, obniżyłem jej ocenę - jeszcze jedna zła ocena i ją usunę."
        if info.get("intencja"):
            if dobra:
                self.dodaj_przyklad(info["tekst"], info["intencja"])
                return "Dzięki! Dopisałem to zdanie do swoich przykładów treningowych."
            self.dodaj_przyklad(info["tekst"], "inne")
            return (f"Rozumiem - na „{info['tekst']}” nie powinienem tak odpowiadać. "
                    "Douczyłem sieć, a następnym razem poszukam odpowiedzi gdzie indziej.")
        return "Dzięki za ocenę!" if dobra else \
            "Przykro mi. Naucz mnie poprawnej odpowiedzi: „naucz się: pytanie => odpowiedź”."

    # --- samodoskonalenie ----------------------------------------------------

    def ocen_siec(self):
        """Dokładność sieci na zdaniach, których nie widziała przy treningu (0..1)."""
        if not os.path.exists(TESTY_INTENCJI):
            return None
        with open(TESTY_INTENCJI, encoding="utf-8") as f:
            testy = json.load(f)["testy"]
        dobre = sum((self.rozpoznaj_intencje(t["tekst"]) or "inne") == t["oczekiwana"] for t in testy)
        return dobre / len(testy)

    def czego_nie_wiem(self, ile=5):
        """Najczęstsze pytania z rozmów, na które wciąż nie ma odpowiedzi."""
        licznik, przyklad = {}, {}
        for wpis in self.dziennik:
            if wpis.get("zrodlo") != "nie_wiem":
                continue
            klucz = " ".join(sorted(istotne_slowa(wpis["tekst"])))
            if not klucz:
                continue
            licznik[klucz] = licznik.get(klucz, 0) + 1
            przyklad[klucz] = wpis["tekst"]
        wyniki = []
        for klucz in sorted(licznik, key=lambda k: -licznik[k]):
            if self.wiedza.szukaj(przyklad[klucz])[1] < PROG_WIEDZY:  # wciąż nie wiem
                wyniki.append((przyklad[klucz], licznik[klucz]))
            if len(wyniki) == ile:
                break
        return wyniki

    def statystyki(self):
        zrodla = self.wiedza.statystyki()
        nazwy = {"wbudowana": "wbudowanych", "ty": "od ciebie"}
        wiedza = ", ".join(f"{n} {nazwy.get(z, 'od ' + z)}" for z, n in sorted(zrodla.items()))
        przyklady = sum(len(p) for p in self.przyklady_treningowe().values())
        dopisane = sum(len(p) for p in self.dodatkowe_przyklady.values())
        biblioteki = sum(ile for _, ile, _ in self.biblioteki.lista())
        rozmowy = len(self.dziennik)
        linie = [
            "📊 Co już wiem:",
            f"• baza wiedzy: {len(self.wiedza.wpisy)} {odmien(len(self.wiedza.wpisy), 'odpowiedź', 'odpowiedzi', 'odpowiedzi')} ({wiedza})",
            f"• sieć neuronowa: {len(self.intencje)} {odmien(len(self.intencje), 'temat', 'tematy', 'tematów')}, "
            f"{przyklady} {odmien(przyklady, 'przykład', 'przykłady', 'przykładów')}"
            + (f" (w tym {dopisane} z twoich ocen)" if dopisane else ""),
            f"• biblioteki: {len(self.biblioteki.lista())} ({biblioteki} {odmien(biblioteki, 'fakt', 'fakty', 'faktów')})",
            f"• zdjęcia: {len(self.zdjecia)} zapamiętanych",
            f"• przeczytane wiadomości: {rozmowy}",
        ]
        return "\n".join(linie)

    def ucz_sie(self):
        """"Sen" Badka: porządkuje wiedzę, trenuje sieć od zera i mówi, czego jeszcze nie wie."""
        scalone = self.wiedza.porzadkuj()
        start = time.time()
        self.trenuj()
        dokladnosc = self.ocen_siec()
        linie = ["🧠 Skończyłem naukę!",
                 f"• przetrenowałem sieć w {time.time() - start:.1f} s".replace(".", ",", 1)
                 + (f" - rozpoznaje {dokladnosc:.0%} zdań testowych" if dokladnosc is not None else ""),
                 f"• uporządkowałem wiedzę ({scalone} {odmien(scalone, 'duplikat scalony', 'duplikaty scalone', 'duplikatów scalonych')})"]
        nie_wiem = self.czego_nie_wiem()
        if nie_wiem:
            linie.append("• najczęstsze pytania, na które jeszcze nie znam odpowiedzi:")
            linie += [f"   - „{t}” ({n}×)" for t, n in nie_wiem]
            linie.append("  Naucz mnie: „naucz się: pytanie => odpowiedź” albo włącz mocniejsze AI w ⚙️.")
        return "\n".join(linie)

    # --- wymiana pamięci między urządzeniami ------------------------------------

    def eksport(self):
        """Cała wyuczona pamięć jako słownik (do zapisania w pliku JSON)."""
        return {
            "panbadek_pamiec": 1, "imie": self.imie, "miasto": self.miasto,
            "wiedza": self.wiedza.eksport(), "dodatkowe_przyklady": self.dodatkowe_przyklady,
            "biblioteki": {n: self.biblioteki.dane[n] for n in self.biblioteki.dane},
            "zdjecia": self.zdjecia,
        }

    def importuj(self, dane):
        """Dołącza pamięć z innego urządzenia (nic nie kasuje). Zwraca podsumowanie."""
        if not isinstance(dane, dict) or "panbadek_pamiec" not in dane:
            raise ValueError("To nie jest plik pamięci Pana Badka.")
        self.imie = self.imie or dane.get("imie")
        self.miasto = self.miasto or dane.get("miasto")
        nowa_wiedza = self.wiedza.import_(dane.get("wiedza", []))
        nowe_przyklady = 0
        for intencja, przyklady in dane.get("dodatkowe_przyklady", {}).items():
            lista = self.dodatkowe_przyklady.setdefault(intencja, [])
            for p in przyklady:
                if p not in lista:
                    lista.append(p)
                    nowe_przyklady += 1
        nowe_fakty = 0
        for nazwa, biblioteka in dane.get("biblioteki", {}).items():
            try:
                nowe_fakty += self.biblioteki.dodaj(nazwa, *biblioteka.get("wpisy", []))
            except ValueError:
                continue
        znane = {json.dumps(z, sort_keys=True) for z in self.zdjecia}
        nowe_zdjecia = [z for z in dane.get("zdjecia", []) if json.dumps(z, sort_keys=True) not in znane]
        self.zdjecia += nowe_zdjecia
        self._zapisz_zdjecia()
        self._zapisz_nauczone()
        if nowe_przyklady:
            self.dotrenuj()
        n = len(nowe_zdjecia)
        return ("Wczytałem pamięć: "
                f"{nowa_wiedza} {odmien(nowa_wiedza, 'nową odpowiedź', 'nowe odpowiedzi', 'nowych odpowiedzi')}, "
                f"{nowe_fakty} {odmien(nowe_fakty, 'fakt', 'fakty', 'faktów')} w bibliotekach, "
                f"{nowe_przyklady} {odmien(nowe_przyklady, 'przykład', 'przykłady', 'przykładów')} treningowych, "
                f"{n} {odmien(n, 'zdjęcie', 'zdjęcia', 'zdjęć')}.")

    # --- myślenie -----------------------------------------------------------

    def klasyfikuj(self, tekst):
        """Zwraca (intencja, pewność) dla podanego tekstu."""
        wektor = self.slownik.wektor(tekst)
        if not wektor or not self._zna_tekst(tekst):
            return None, 0.0
        prawd = self.siec.przewiduj(wektor)
        najlepsza = max(range(len(prawd)), key=prawd.__getitem__)
        return self.intencje[najlepsza], prawd[najlepsza]

    def rozpoznaj_intencje(self, tekst):
        """Nazwa intencji, którą sieć rozpoznaje z pewnością, albo None ("to nie do mnie")."""
        intencja, pewnosc = self.klasyfikuj_ostroznie(tekst)
        if intencja is None or pewnosc < PROG_PEWNOSCI or intencja["nazwa"] == "inne":
            return None
        return intencja["nazwa"]

    def klasyfikuj_ostroznie(self, tekst):
        """Jak klasyfikuj(), ale gdy ponad połowa istotnych słów jest sieci obca, nie zgaduje
        ("jak szybko lata jaskółka" to nie pogawędka, choć zaczyna się od "jak")."""
        if self._nieznane_slowa(tekst) > 0.5:
            return None, 0.0
        return self.klasyfikuj(tekst)

    def _zna_tekst(self, tekst):
        """Chroni przed pewnymi siebie strzałami sieci na zupełnie obcych zdaniach.

        Sieć zawsze wybierze jakąś intencję, nawet dla "kurs programowania".
        Wymagamy więc, by przynajmniej jedno istotne słowo (nie "na", "co", "jest")
        było znane albo by większość trigramów pochodziła ze słownika (literówki).
        """
        wszystkie = cechy(tekst)
        if any(c in self.slownik.indeksy for c in wszystkie
               if c.startswith("w:") and c[2:] not in NIEISTOTNE):
            return True
        trigramy = [c for c in wszystkie if c.startswith("t:")]
        znane = sum(c in self.slownik.indeksy for c in trigramy)
        return bool(trigramy) and znane / len(trigramy) >= 0.8

    def _wypelnij(self, szablon):
        return szablon.format(imie=self.imie or "przyjacielu",
                              imie_po_przecinku=f", {self.imie}" if self.imie else "")

    def odpowiedz(self, tekst):
        # Która część mózgu odpowiedziała - np. aplikacja w przeglądarce oddaje rozmowę
        # dużemu modelowi językowemu, gdy było to "nie_wiem" albo zwykła pogawędka.
        tekst = tekst.strip()
        if not tekst:
            self.zrodlo = "nie_wiem"
            return "Powiedz coś - słucham!"
        poprzednia, self._poprzednia_odpowiedz = getattr(self, "_poprzednia_odpowiedz", None), None
        self._wpis_wiedzy = self._intencja_odpowiedzi = None
        wynik = self._mysl(tekst, poprzednia)
        self.zarejestruj_odpowiedz(tekst, self.zrodlo, self._wpis_wiedzy, self._intencja_odpowiedzi)
        self._zapisz_w_dzienniku(tekst, self.zrodlo)
        return wynik

    def zarejestruj_odpowiedz(self, tekst, zrodlo, wiedza=None, intencja=None):
        """Zapamiętuje, kto odpowiedział na wiadomość - żeby dało się tę odpowiedź ocenić."""
        self._kolejna_odpowiedz += 1
        self.id_odpowiedzi = self._kolejna_odpowiedz
        self.odpowiedzi[self.id_odpowiedzi] = {"tekst": tekst, "zrodlo": zrodlo,
                                               "wiedza": wiedza, "intencja": intencja}
        for stary in [k for k in self.odpowiedzi if k < self.id_odpowiedzi - 50]:
            del self.odpowiedzi[stary]
        self._poprzednia_odpowiedz = self.id_odpowiedzi
        return self.id_odpowiedzi

    def ocen_trudnosc(self, tekst):
        """Czy to złożony problem, który warto oddać dużemu modelowi z głębokim myśleniem?"""
        return (len(tekst.split()) >= 25 or "```" in tekst or tekst.count("\n") >= 3
                or bool(_TRUDNE.search(tekst)))

    def _mysl(self, tekst, poprzednia, glebokosc=0):
        self.zrodlo = "nie_wiem"
        if _KRYZYS.search(tekst):
            self.zrodlo = "kryzys"
            return WSPARCIE
        zdjecie, self.ostatnie_zdjecie = self.ostatnie_zdjecie, None
        podpis = _TO_JEST.match(tekst)
        if zdjecie and podpis:
            self.zrodlo = "zdjecia"
            return self.naucz_zdjecie(zdjecie, podpis.group(1))
        # Ocena poprzedniej odpowiedzi słowami ("źle", "dobra odpowiedź").
        for wzor, dobra in ((_OCENA_DOBRA, True), (_OCENA_ZLA, False)):
            if poprzednia and wzor.match(tekst):
                self.zrodlo = "ocena"
                return self.ocen(poprzednia, dobra)
        for obsluga in (self._polecenia_uczenia, self._polecenia_zdjec, self._polecenia_pamieci,
                        self._polecenia_bibliotek, self._polecenia_wtyczek, self._wtyczki,
                        self._internet, self._matematyka, self._kalkulator, self._wiedza_lub_siec):
            self._zrodlo_szczegol = None
            wynik = obsluga(tekst)
            if wynik:
                self.zrodlo = self._zrodlo_szczegol or obsluga.__name__.lstrip("_")
                if self.zrodlo not in ("siec_neuronowa", "ocena") and not obsluga.__name__.startswith("_polecenia"):
                    self._temat = tekst  # do dopytań "a ...?"
                return wynik
        z_biblioteki = self._z_biblioteki(tekst)
        if z_biblioteki:
            self.zrodlo = "biblioteka"
            return z_biblioteki
        dopytanie = self._dopytanie(tekst, poprzednia, glebokosc)
        if dopytanie:
            return dopytanie
        self.zrodlo = "nie_wiem"
        if len(istotne_slowa(tekst)) <= 1 and len(tekst.split()) <= 2:
            return NIE_ROZUMIEM
        if self.ocen_trudnosc(tekst):
            return TRUDNY_PROBLEM
        return NIE_WIEM.format(pytanie=tekst)

    def _dopytanie(self, tekst, poprzednia, glebokosc):
        """ "Jaka jest stolica Francji?" -> "A Niemiec?" = "Jaka jest stolica Niemiec?"."""
        temat = getattr(self, "_temat", None)
        m = _DOPYTANIE.match(tekst)
        if not m or not temat or glebokosc:
            return None
        nowe = m.group(1).strip(" ?")
        slowa_tematu = temat.rstrip(" ?!.").split()
        istotne = set(istotne_slowa(temat))
        indeks = next((i for i in range(len(slowa_tematu) - 1, -1, -1)
                       if istotne_slowa(slowa_tematu[i]) and istotne_slowa(slowa_tematu[i])[0] in istotne), None)
        if indeks is None:
            return None
        poczatek = indeks
        # "pogoda w Krakowie" + "a w Gdańsku" -> zamieniamy też przyimek.
        if nowe.split()[0].lower() in _PRZYIMKI and indeks > 0 and slowa_tematu[indeks - 1].lower() in _PRZYIMKI:
            poczatek = indeks - 1
        kandydat = " ".join(slowa_tematu[:poczatek] + [nowe]) + "?"
        zapamietany_temat = temat
        wynik = self._mysl(kandydat, poprzednia, glebokosc=1)
        if self.zrodlo in ("nie_wiem", "siec_neuronowa"):
            self._temat = zapamietany_temat
            return None
        self._temat = kandydat
        return wynik

    def _matematyka(self, tekst):
        return matematyka.rozwiaz(tekst)

    def _polecenia_uczenia(self, tekst):
        notatka = _ZAPAMIETAJ_ZE.match(tekst)
        if notatka:
            fakt = " ".join(_NA_TY.get(s.lower(), s) for s in notatka.group(1).split())
            fakt = fakt[0].upper() + fakt[1:]
            self.biblioteki.dodaj(NOTATKI, fakt)
            return f"Zapamiętałem: {fakt}"
        if _UCZ_SIE.match(tekst):
            return self.ucz_sie()
        if _STATYSTYKI.match(tekst):
            return self.statystyki()
        if _CZEGO_NIE_WIESZ.match(tekst):
            nie_wiem = self.czego_nie_wiem()
            if not nie_wiem:
                return "Na wszystkie dotychczasowe pytania znalazłem już odpowiedź! 🎉"
            return "Najczęściej nie wiedziałem, co odpowiedzieć na:\n" + "\n".join(
                f"• „{t}” ({n}×)" for t, n in nie_wiem) + "\nNaucz mnie: „naucz się: pytanie => odpowiedź”."
        return None

    # --- zdjęcia --------------------------------------------------------------

    def analizuj_zdjecie(self, obraz, naglowek=b""):
        """Opisuje zdjęcie: kolory, światło, ostrość, domysły, metadane i rozpoznanie."""
        opis = obrazy.opisz(obrazy.analizuj(obraz))
        metadane = exif.opisz(exif.czytaj(naglowek))
        if metadane:
            opis += "\n" + metadane
        wektor = obrazy.cechy(obraz)
        rozpoznanie = obrazy.rozpoznaj(wektor, self.zdjecia)
        if rozpoznanie:
            etykieta, pewnosc = rozpoznanie
            opis += f"\n🧠 Przypomina mi: {etykieta} (podobieństwo {pewnosc:.0%})."
        self.ostatnie_zdjecie = wektor
        opis += ("\nNapisz „to jest …”, a zapamiętam, co jest na zdjęciu, i rozpoznam podobne."
                 if not rozpoznanie else
                 "\nJeśli się mylę, napisz „to jest …”, a zapamiętam poprawnie.")
        return opis

    def naucz_zdjecie(self, wektor, etykieta):
        etykieta = etykieta.strip(" .,!?\"'„”")[:60]
        self.zdjecia.append({"etykieta": etykieta, "cechy": wektor})
        self.zdjecia = self.zdjecia[-LIMIT_ZDJEC:]
        self._zapisz_zdjecia()
        ile = sum(1 for z in self.zdjecia if z["etykieta"] == etykieta)
        return (f"Zapamiętałem: to jest {etykieta}. Mam już "
                f"{ile} {odmien(ile, 'przykład', 'przykłady', 'przykładów')} „{etykieta}”. "
                "Im więcej podobnych zdjęć mi pokażesz, tym lepiej będę rozpoznawać.")

    def _zapisz_zdjecia(self):
        if not self.plik_zdjec:
            return
        os.makedirs(self.katalog_pamieci, exist_ok=True)
        with open(self.plik_zdjec, "w", encoding="utf-8") as f:
            json.dump(self.zdjecia, f)

    def _polecenia_zdjec(self, tekst):
        if _ZNANE_ZDJECIA.match(tekst):
            if not self.zdjecia:
                return "Nie znam jeszcze żadnych zdjęć. Wyślij zdjęcie i napisz „to jest …”."
            licznik = {}
            for z in self.zdjecia:
                licznik[z["etykieta"]] = licznik.get(z["etykieta"], 0) + 1
            return "Rozpoznaję: " + ", ".join(f"{e} ({n})" for e, n in sorted(licznik.items())) + "."
        if _ZAPOMNIJ_ZDJECIA.match(tekst):
            self.zdjecia = []
            self._zapisz_zdjecia()
            return "Zapomniałem wszystkie zdjęcia."

        z_pliku = _ZDJECIE_Z_PLIKU.match(tekst)
        if z_pliku and self.pliki_lokalne:
            sciezka = os.path.expanduser(z_pliku.group(1).strip("\"'"))
            if os.path.isfile(sciezka):
                try:
                    obraz, naglowek = obrazy.wczytaj_plik(sciezka)
                except (ValueError, OSError, zlib_error) as e:
                    return f"Nie umiem otworzyć tego obrazu: {e}"
                return self.analizuj_zdjecie(obraz, naglowek)

        if _SLOWO_ZDJECIE.search(tekst) and _PYTANIE_O_ZDJECIE.search(tekst):
            if self.pliki_lokalne:
                return ("Podaj ścieżkę do pliku, np. „przeanalizuj zdjęcie ~/Obrazy/kot.png”, "
                        "albo uruchom mnie z --web i wyślij zdjęcie przyciskiem 📷.")
            return "Wyślij zdjęcie przyciskiem 📷 obok pola wiadomości, a je przeanalizuję."
        return None

    # --- obsługa poszczególnych rodzajów wiadomości -------------------------

    def _polecenia_pamieci(self, tekst):
        nauka = _NAUCZ.match(tekst)
        if nauka:
            pytanie, odpowiedz = nauka.groups()
            self.naucz(pytanie, odpowiedz)
            return f"Zapamiętałem! Na „{pytanie}” (i podobne pytania) odpowiem: „{odpowiedz}”."

        zapomnij = _ZAPOMNIJ.match(tekst)
        if zapomnij:
            if self.zapomnij(zapomnij.group(1)):
                return f"Zapomniałem odpowiedź na '{zapomnij.group(1)}'."
            return f"Nie mam nauczonej odpowiedzi na '{zapomnij.group(1)}'."

        if _JAK_MAM_NA_IMIE.search(tekst):
            if self.imie:
                return f"Masz na imię {self.imie}."
            return "Jeszcze nie znam twojego imienia. Napisz: 'mam na imię ...'."

        imie = _IMIE.search(tekst)
        if imie:
            self.imie = imie.group(1)
            self._zapisz_nauczone()
            return f"Miło mi cię poznać, {self.imie}!"

        miasto = _MIESZKAM.search(tekst)
        if miasto:
            self.miasto = miasto.group(1)
            self._zapisz_nauczone()
            return f"Zapamiętałem, że mieszkasz w {self.miasto}. Teraz wystarczy zapytać o pogodę."
        return None

    def _polecenia_bibliotek(self, tekst):
        if _LISTA_BIBLIOTEK.match(tekst):
            lista = self.biblioteki.lista()
            if not lista:
                return ("Nie mam jeszcze żadnych bibliotek. Stwórz jedną: "
                        "'stwórz bibliotekę o Krakowie' albo 'stwórz bibliotekę przepisy'.")
            return "Moje biblioteki:\n" + "\n".join(
                f"• {nazwa} ({ile} {odmien(ile, 'wpis', 'wpisy', 'wpisów')}){' – ' + opis if opis else ''}" for nazwa, ile, opis in lista)

        usun = _USUN_BIBLIOTEKE.match(tekst)
        if usun:
            if self.biblioteki.usun(usun.group(1)):
                return f"Usunąłem bibliotekę „{usun.group(1)}”."
            return f"Nie mam biblioteki „{usun.group(1)}”."

        dodaj = _DODAJ.match(tekst)
        if dodaj:
            nazwa, wpis = dodaj.groups()
            try:
                self.biblioteki.dodaj(nazwa, wpis)
            except ValueError as e:
                return str(e)
            return f"Dodałem do biblioteki „{self.biblioteki.znajdz_nazwe(nazwa)}”: {wpis}"

        z_internetu = _BIBLIOTEKA_O.match(tekst)
        if z_internetu:
            return self.stworz_biblioteke_z_internetu(z_internetu.group(1))

        nowa = _BIBLIOTEKA_NOWA.match(tekst)
        if nowa:
            try:
                nazwa = self.biblioteki.stworz(nowa.group(1))
            except ValueError as e:
                return str(e)
            return (f"Biblioteka „{nazwa}” gotowa. Dodawaj wiedzę: "
                    f"'dodaj do {nazwa}: jakiś fakt'.")
        return None

    def stworz_biblioteke_z_internetu(self, temat):
        if not self.internet:
            return "Jestem w trybie offline, więc nie mogę niczego pobrać."
        try:
            wynik = internet.wikipedia(temat, caly_artykul=True)
        except internet.BladInternetu as e:
            return f"Nie udało się połączyć z Wikipedią ({e})."
        if not wynik:
            return f"Nie znalazłem w Wikipedii nic o „{temat}”."
        tytul, tekst, adres = wynik
        zdania = internet.podziel_na_zdania(tekst)[:LIMIT_ZDAN_BIBLIOTEKI]
        try:
            nazwa = self.biblioteki.stworz(tytul, opis=f"z Wikipedii: {tytul}", zrodlo=adres)
        except ValueError:
            nazwa = self.biblioteki.stworz(temat[:60], opis=f"z Wikipedii: {tytul}", zrodlo=adres)
        dodane = self.biblioteki.dodaj(nazwa, *zdania)
        return (f"Przeczytałem artykuł „{tytul}” i stworzyłem bibliotekę „{nazwa}” "
                f"({dodane} {odmien(dodane, 'nowy fakt', 'nowe fakty', 'nowych faktów')}). Pytaj śmiało - działa też bez internetu!")

    def _polecenia_wtyczek(self, tekst):
        nowa = _WTYCZKA.match(tekst)
        if nowa:
            if not self.katalog_wtyczek:
                return "Bez katalogu pamięci nie mam gdzie zapisać wtyczki."
            sciezka = wtyczki.stworz(self.katalog_wtyczek, nowa.group(1))
            self.przeladuj_wtyczki()
            return (f"Stworzyłem wtyczkę: {sciezka}\n"
                    "Otwórz plik, napisz w funkcji obsluz() co ma robić "
                    "i napisz do mnie 'przeładuj wtyczki'.")
        if _PRZELADUJ.match(tekst):
            self.przeladuj_wtyczki()
            odp = f"Załadowane wtyczki: {', '.join(n for n, _ in self.wtyczki) or 'brak'}."
            if self.bledy_wtyczek:
                odp += "\nBłędy:\n" + "\n".join(self.bledy_wtyczek)
            return odp
        if _LISTA_WTYCZEK.match(tekst):
            return f"Moje wtyczki: {', '.join(n for n, _ in self.wtyczki) or 'brak'}."
        return None

    def przeladuj_wtyczki(self):
        self.wtyczki, self.bledy_wtyczek = wtyczki.wczytaj(self.katalog_wtyczek)

    def _wtyczki(self, tekst):
        for nazwa, obsluz in self.wtyczki:
            try:
                wynik = obsluz(tekst, self)
            except Exception as e:  # zepsuta wtyczka nie może wyłączyć całego Badka
                return f"Wtyczka „{nazwa}” zgłosiła błąd: {e}"
            if wynik:
                return str(wynik)
        return None

    def _internet(self, tekst):
        if _WIECEJ.match(tekst):
            return self._wiecej()

        wiki = _WIKI.match(tekst)
        if wiki and normalizuj(wiki.group(1)) not in _O_SOBIE:
            return self._co_to_jest(wiki.group(1), tekst)

        if _POGODA.search(tekst):
            miejsca = [m for m in _MIEJSCE.findall(tekst) + _POGODA_MIASTO.findall(tekst)
                       if normalizuj(m) not in _NIE_MIEJSCA]
            miasto = miejsca[0] if miejsca else self.miasto
            if not miasto:
                return "Dla jakiego miasta? Napisz np. 'pogoda w Krakowie' albo 'mieszkam w Krakowie'."
            return self._z_internetu(self._pogoda, miasto)

        kurs = _KURS.search(tekst) or _ILE_KOSZTUJE.search(tekst)
        if kurs and (kurs.group(1).lower() in internet.WALUTY or len(kurs.group(1)) == 3):
            return self._z_internetu(internet.kurs, kurs.group(1))
        return None

    def _z_internetu(self, funkcja, *argumenty):
        if not self.internet:
            return "Jestem w trybie offline - uruchom mnie bez --offline, żeby sprawdzić to w sieci."
        try:
            return funkcja(*argumenty)
        except internet.BladInternetu as e:
            return f"Nie udało się sprawdzić tego w internecie ({e})."

    def _pogoda(self, miasto):
        for kandydat in kandydaci_miasta(miasto):
            wynik = internet.pogoda(kandydat)
            if not wynik.startswith("Nie znalazłem"):
                return wynik
        return f"Nie znalazłem miejscowości „{miasto}”."

    def _co_to_jest(self, haslo, pytanie=None):
        # Najpierw własna wiedza (działa offline i nie zużywa internetu).
        wpis, podobienstwo = self.wiedza.szukaj(pytanie or haslo)
        if wpis and podobienstwo >= PROG_WIEDZY:
            return self._odpowiedz_z_wiedzy(wpis, podobienstwo)
        z_biblioteki = self.biblioteki.szukaj(haslo)
        if z_biblioteki and z_biblioteki[0][0] >= PROG_BIBLIOTEKI_PEWNY:
            _, nazwa, wpis = z_biblioteki[0]
            return f"{wpis}\n(z mojej biblioteki „{nazwa}”)"
        if not self.internet:
            return self._z_biblioteki(haslo) or f"Nie wiem, co to „{haslo}”, a jestem offline."
        try:
            wynik = internet.wikipedia(haslo)
        except internet.BladInternetu as e:
            return (self._z_biblioteki(haslo)
                    or f"Nie udało się połączyć z Wikipedią ({e}).")
        if not wynik:
            return f"Nie znalazłem w Wikipedii nic o „{haslo}”."
        tytul, tekst, adres = wynik
        zdania = internet.podziel_na_zdania(tekst)
        # Zapamiętujemy przeczytane wstępy, żeby później odpowiadać bez internetu.
        self.biblioteki.dodaj(BIBLIOTEKA_INTERNETU, *zdania[:3])
        self.kontekst = {"tytul": tytul, "adres": adres, "pokazane": ZDANIA_NA_RAZ,
                         "zdania": zdania, "caly": False}
        odp = " ".join(zdania[:ZDANIA_NA_RAZ])
        dalej = " Napisz 'więcej', żeby usłyszeć więcej." if len(zdania) > ZDANIA_NA_RAZ else ""
        return f"{odp}\n(Wikipedia: {tytul}){dalej}"

    def _wiecej(self):
        k = self.kontekst
        if not k:
            return "Więcej o czym? Zapytaj najpierw np. 'co to jest fotosynteza'."
        if k["pokazane"] >= len(k["zdania"]) and not k["caly"] and self.internet:
            try:
                wynik = internet.wikipedia(k["tytul"], caly_artykul=True)
            except internet.BladInternetu as e:
                return f"Nie udało się pobrać dalszej części ({e})."
            k["caly"] = True
            if wynik:
                k["zdania"] = internet.podziel_na_zdania(wynik[1])
        nowe = k["zdania"][k["pokazane"]:k["pokazane"] + ZDANIA_NA_RAZ]
        if not nowe:
            return f"To już wszystko, co wiem o „{k['tytul']}”. Cały artykuł: {k['adres']}"
        k["pokazane"] += len(nowe)
        return " ".join(nowe)

    def _kalkulator(self, tekst):
        return skills.kalkulator(tekst)

    def _odpowiedz_z_wiedzy(self, wpis, podobienstwo):
        """Odpowiedź z bazy wiedzy - przy niepewnym dopasowaniu mówi, jak zrozumiał pytanie."""
        self.wiedza.uzyto(wpis)
        self._wpis_wiedzy = wpis["id"]
        self._zrodlo_szczegol = "wiedza"
        odpowiedz = wpis["odpowiedz"]
        if podobienstwo < 0.7:
            odpowiedz = f"Jeśli dobrze rozumiem, pytasz: „{wpis['pytanie'].rstrip('?')}?”\n\n{odpowiedz}"
        if wpis["zrodlo"] not in ("wbudowana", "ty"):
            odpowiedz += f"\n(zapamiętałem od: {wpis['zrodlo']})"
        return odpowiedz

    def _zna_wszystkie_slowa(self, tekst):
        """Czy sieć widziała przy treningu każde istotne słowo pytania?"""
        return self._nieznane_slowa(tekst) == 0

    def _nieznane_slowa(self, tekst):
        """Jaka część istotnych słów pytania jest sieci obca (0..1)."""
        slowa = istotne_slowa(tekst)
        if not slowa:
            return 0
        return sum("w:" + rdzen(s) not in self.slownik.indeksy for s in slowa) / len(slowa)

    def _wiedza_lub_siec(self, tekst):
        """Baza wiedzy i sieć neuronowa razem: wygrywa ta, która jest pewniejsza.
        Sieć nie przejmuje pytań z nieznanymi jej słowami, jeśli wiedzę o nich mają
        baza wiedzy albo biblioteki (np. "jak ma na imię mój pies" to nie pytanie o Badka)."""
        wpis, podobienstwo = self.wiedza.szukaj(tekst)
        intencja, pewnosc = self.klasyfikuj_ostroznie(tekst)
        nazwa = intencja["nazwa"] if intencja and pewnosc >= PROG_PEWNOSCI else None
        zna_slowa = self._zna_wszystkie_slowa(tekst)
        z_biblioteki = self.biblioteki.szukaj(tekst)
        if z_biblioteki and z_biblioteki[0][0] >= max(PROG_BIBLIOTEKI_PEWNY, podobienstwo) and (
                not zna_slowa or nazwa in (None, "inne")):
            return None  # twoje notatki i biblioteki pasują lepiej - odpowie biblioteka
        # Gdy sieć rozpoznała temat rozmowy i zna wszystkie słowa, wiedza musi pasować
        # bardzo dokładnie - inaczej "mam zły dzień" trafiałoby w "Kiedy jest Dzień Matki?".
        # Twoje własne lekcje ("naucz się: ...") wygrywają zawsze, gdy pasują.
        siec_pewna = nazwa not in (None, "inne") and zna_slowa
        prog = PROG_WIEDZY if not siec_pewna or (wpis and wpis["zrodlo"] == "ty") else PROG_WIEDZY_PEWNY
        if wpis and podobienstwo >= prog:
            return self._odpowiedz_z_wiedzy(wpis, podobienstwo)
        if nazwa in (None, "inne"):
            return None
        self._zrodlo_szczegol = "siec_neuronowa"
        self._intencja_odpowiedzi = nazwa
        return self._odpowiedz_intencji(tekst, intencja, pewnosc)

    def _odpowiedz_intencji(self, tekst, intencja, pewnosc):
        if pewnosc < 0.9:
            # Sieć się waha, a biblioteka zna wyraźnie pasujący fakt - wybieramy fakt.
            wyniki = self.biblioteki.szukaj(tekst)
            if wyniki and wyniki[0][0] >= PROG_BIBLIOTEKI_PEWNY:
                return self._z_biblioteki(tekst)
        akcja = intencja.get("akcja")
        if akcja == "godzina":
            return skills.godzina()
        if akcja == "data":
            return skills.data()
        if akcja == "ciekawostka":
            wpisy = [w for w in self.wiedza.wpisy if w["zrodlo"] != "ty"] or self.wiedza.wpisy
            if wpisy:
                return "💡 Ciekawostka: " + self.los.choice(wpisy)["odpowiedz"]
        return self._wypelnij(self.los.choice(intencja["odpowiedzi"]))

    def _z_biblioteki(self, tekst):
        wyniki = self.biblioteki.szukaj(tekst)
        if wyniki and wyniki[0][0] >= PROG_BIBLIOTEKI:
            _, nazwa, wpis = wyniki[0]
            return f"{wpis}\n(z mojej biblioteki „{nazwa}”)"
        return None

