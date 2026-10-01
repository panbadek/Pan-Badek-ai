"""Mózg Pana Badka: łączy sieć neuronową, internet, biblioteki wiedzy, wtyczki i pamięć."""

import json
import os
import random
import re
from zlib import error as zlib_error

from . import exif, internet, obrazy, skills, wtyczki
from .biblioteki import NIEISTOTNE, Biblioteki
from .network import SiecNeuronowa
from .text import Slownik, cechy, normalizuj

KATALOG = os.path.dirname(os.path.abspath(__file__))
DOMYSLNE_INTENCJE = os.path.join(KATALOG, "data", "intencje.json")
DOMYSLNA_PAMIEC = os.path.join(os.path.expanduser("~"), ".panbadek")

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

NIE_WIEM = [
    "Hmm, tego jeszcze nie wiem. Naucz mnie: 'naucz się: {pytanie} => odpowiedź' "
    "albo zapytaj 'co to jest ...', a sprawdzę w internecie.",
    "Nie jestem pewien, o co chodzi. Możesz to powiedzieć inaczej?",
]


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
        self.intencje += self._wczytaj_nauczone()
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
            return dane.get("intencje", [])
        return []

    def _zapisz_nauczone(self):
        if not self.plik_nauki:
            return
        os.makedirs(self.katalog_pamieci, exist_ok=True)
        nauczone = [i for i in self.intencje if i.get("nauczona")]
        with open(self.plik_nauki, "w", encoding="utf-8") as f:
            json.dump({"imie": self.imie, "miasto": self.miasto, "intencje": nauczone},
                      f, ensure_ascii=False, indent=2)

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

    def zapomnij(self, pytanie):
        """Usuwa nauczoną odpowiedź. Zwraca True, jeśli coś usunięto."""
        klucz = normalizuj(pytanie)
        przed = len(self.intencje)
        self.intencje = [i for i in self.intencje if not (
            i.get("nauczona") and any(normalizuj(p) == klucz for p in i["przyklady"]))]
        if len(self.intencje) == przed:
            return False
        self._zapisz_nauczone()
        self.trenuj()
        return True

    # --- myślenie -----------------------------------------------------------

    def klasyfikuj(self, tekst):
        """Zwraca (intencja, pewność) dla podanego tekstu."""
        wektor = self.slownik.wektor(tekst)
        if not wektor or not self._zna_tekst(tekst):
            return None, 0.0
        prawd = self.siec.przewiduj(wektor)
        najlepsza = max(range(len(prawd)), key=prawd.__getitem__)
        return self.intencje[najlepsza], prawd[najlepsza]

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
        self.zrodlo = "nie_wiem"
        tekst = tekst.strip()
        if not tekst:
            return "Powiedz coś - słucham!"
        zdjecie, self.ostatnie_zdjecie = self.ostatnie_zdjecie, None
        podpis = _TO_JEST.match(tekst)
        if zdjecie and podpis:
            self.zrodlo = "zdjecia"
            return self.naucz_zdjecie(zdjecie, podpis.group(1))
        for obsluga in (self._polecenia_zdjec, self._polecenia_pamieci, self._polecenia_bibliotek,
                        self._polecenia_wtyczek, self._wtyczki, self._internet,
                        self._kalkulator, self._siec_neuronowa):
            wynik = obsluga(tekst)
            if wynik:
                self.zrodlo = obsluga.__name__.lstrip("_")
                return wynik
        z_biblioteki = self._z_biblioteki(tekst)
        if z_biblioteki:
            self.zrodlo = "biblioteka"
            return z_biblioteki
        return self.los.choice(NIE_WIEM).format(pytanie=tekst)

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
            return f"Zapamiętałem! Na '{pytanie}' odpowiem: '{odpowiedz}'."

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
            return self._co_to_jest(wiki.group(1))

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

    def _co_to_jest(self, haslo):
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

    def _siec_neuronowa(self, tekst):
        intencja, pewnosc = self.klasyfikuj(tekst)
        if intencja is None or pewnosc < PROG_PEWNOSCI:
            return None
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
        return self._wypelnij(self.los.choice(intencja["odpowiedzi"]))

    def _z_biblioteki(self, tekst):
        wyniki = self.biblioteki.szukaj(tekst)
        if wyniki and wyniki[0][0] >= PROG_BIBLIOTEKI:
            _, nazwa, wpis = wyniki[0]
            return f"{wpis}\n(z mojej biblioteki „{nazwa}”)"
        return None

