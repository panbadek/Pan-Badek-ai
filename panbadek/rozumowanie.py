"""Rozumowanie: Pan Badek łączy fakty i wzory, zamiast tylko wyszukiwać gotowe odpowiedzi.

1. **Logika**: graf faktów „X jest Y”, „X leży w Y”, cechy grup i grupy rozłączne.
   Badek wnioskuje przez kilka kroków i mówi, z czego to wynika:
   „Czy pingwin składa jaja?” → „Tak. Pingwin jest ptakiem, a ptak składa jaja.”
   Przesłanki można podać w pytaniu („Wszystkie koty są ssakami. Filemon jest kotem.
   Czy Filemon jest ssakiem?”) albo nauczyć go na stałe („zapamiętaj, że Burek jest psem”).
   Gdy faktów brakuje, mówi „nie wiem”, zamiast zgadywać.
2. **Łączenie faktów z liczbami**: wiek z dat urodzin i śmierci, lata między wydarzeniami,
   porównania („o ile Everest jest wyższy od Rysów”) i fakty podstawione do wzorów fizyki
   („ile czasu leci światło ze Słońca do Ziemi” = odległość Słońca + prędkość światła + t = s / v).
"""

import datetime
import json
import os
import re

from . import szkola
from .biblioteki import NIEISTOTNE
from .text import normalizuj

PLIK_FAKTOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fakty.json")
_KONCOWKI = ("ami", "ach", "iem", "owi", "om", "em", "ow", "ie", "y", "i", "a", "e", "u", "o")


def lemat(slowo):
    """Przybliżona forma podstawowa: "ssakami", "ssakiem", "ssaki" -> "ssak"."""
    w = normalizuj(slowo).strip(".,!?;:\"'„”()")
    for koncowka in _KONCOWKI:
        if w.endswith(koncowka) and len(w) - len(koncowka) >= 3:
            return w[:-len(koncowka)]
    return w


def _zdania(tekst):
    return [z.strip() for z in re.split(r"(?<=[.!?])\s+|\n+", tekst.strip()) if z.strip()]


def _zdanie_w_srodku(zdanie):
    """ "Wszystkie kwiaty są roślinami" w środku zdania -> "wszystkie kwiaty są roślinami"."""
    pierwsze = normalizuj(zdanie.split()[0]) if zdanie.split() else ""
    if pierwsze in ("wszystkie", "wszyscy", "kazdy", "kazda", "kazde", "zaden", "zadna", "zadne"):
        return zdanie[:1].lower() + zdanie[1:]
    return zdanie


def _wielka(tekst):
    return tekst[:1].upper() + tekst[1:]


def _data(tekst):
    czesci = [int(c) for c in tekst.split("-")]
    return datetime.date(*czesci) if len(czesci) == 3 else czesci[0]


def _lata_miedzy(a, b):
    """Pełne lata od a do b (daty albo same lata)."""
    if isinstance(a, datetime.date) and isinstance(b, datetime.date):
        return b.year - a.year - ((b.month, b.day) < (a.month, a.day))
    rok = lambda d: d.year if isinstance(d, datetime.date) else d  # noqa: E731
    return rok(b) - rok(a)


def _lat(n):
    n = abs(n)
    if n == 1:
        return "1 rok"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} lata"
    return f"{n} lat"


def _rok(d):
    return str(d.year if isinstance(d, datetime.date) else d)


class Rozumowanie:
    def __init__(self, plik_pamieci=None, dzis=None):
        with open(PLIK_FAKTOW, encoding="utf-8") as f:
            self.dane = json.load(f)
        self.dzis = dzis
        self.plik_pamieci = plik_pamieci
        self.wyswietl = {}      # węzeł -> nazwa do pokazania
        self.indeks = {}        # lemat słowa -> węzeł
        self.jest = {}          # węzeł -> [(rodzic, uzasadnienie)]
        self.nie_jest = {}      # węzeł -> [(nie-rodzic, uzasadnienie)]
        self.rozlaczne = []     # (a, b, uzasadnienie)
        self.cechy = {}         # węzeł -> [(cecha, uzasadnienie)]
        self.lezy_w = {}        # miejsce -> (miejsce, uzasadnienie)
        self.lisc = set()       # gatunki (wzajemnie rozłączne)
        self._wczytaj_wbudowane()
        self.nauczone = []
        if plik_pamieci and os.path.exists(plik_pamieci):
            try:
                with open(plik_pamieci, encoding="utf-8") as f:
                    for zdanie in json.load(f).get("zdania", []):
                        if self._dodaj_zdanie(zdanie):
                            self.nauczone.append(zdanie)
            except (OSError, ValueError):
                pass

    # --- wiedza --------------------------------------------------------------

    def _wezel(self, nazwa, formy=()):
        klucz = normalizuj(nazwa)
        self.wyswietl.setdefault(klucz, nazwa)
        for forma in (nazwa, *formy):
            self.indeks.setdefault(lemat(forma), klucz)
            self.indeks.setdefault(normalizuj(forma), klucz)
        return klucz

    def _wczytaj_wbudowane(self):
        kategorie = self.dane["kategorie"]
        rodzice = {k["rodzic"] for k in kategorie.values()}
        for nazwa, k in kategorie.items():
            self._wezel(nazwa, k["formy"])
        self.mnoga = {normalizuj(n): k["mnoga"] for n, k in kategorie.items()}
        for nazwa, k in kategorie.items():
            wezel = normalizuj(nazwa)
            self.kategorie_narz = getattr(self, "kategorie_narz", {})
            self.kategorie_narz[wezel] = k["narzednik"]
            if k["rodzic"]:
                self.jest.setdefault(wezel, []).append(
                    (normalizuj(k["rodzic"]), f"{nazwa} jest {kategorie[k['rodzic']]['narzednik']}"))
            if nazwa not in rodzice:
                self.lisc.add(wezel)
        for nazwa, lista in self.dane["cechy"].items():
            for cecha in lista:
                self.cechy.setdefault(normalizuj(nazwa), []).append((cecha, f"{nazwa} {cecha}"))
        for grupa in self.dane["rozlaczne"]:
            for i, a in enumerate(grupa):
                for b in grupa[i + 1:]:
                    self.rozlaczne.append((normalizuj(a), normalizuj(b), None))
        self.miejscownik = {}
        for nazwa, m in self.dane["miejsca"].items():
            wezel = self._wezel(nazwa, m["formy"])
            self.miejscownik[wezel] = m["miejscownik"]
        for nazwa, m in self.dane["miejsca"].items():
            if m["w"]:
                gdzie = normalizuj(m["w"])
                self.lezy_w[normalizuj(nazwa)] = (gdzie, f"{nazwa} leży w {self.dane['miejsca'][m['w']]['miejscownik']}")

    def _znajdz(self, fraza):
        """Węzeł dla frazy ("pingwinem", "Wielkiej Brytanii", "Filemon") albo None."""
        fraza = fraza.strip(" ?.!,")
        for kandydat in (normalizuj(fraza), lemat(fraza), *(lemat(s) for s in reversed(fraza.split()))):
            if kandydat in self.indeks:
                return self.indeks[kandydat]
        return None

    def _dodaj_zdanie(self, zdanie, tymczasowo=False):
        """Fakt w zdaniu ("Każdy ptak ma pióra", "Burek jest psem"). Zwraca True, gdy zrozumiany."""
        t = normalizuj(zdanie).strip(" .!")
        wszystkie = r"(?:wszystkie|wszyscy|kazdy|kazda|kazde)"
        m = re.match(r"^(?:zaden|zadna|zadne)\s+(\w+)\s+nie\s+(?:jest|sa)\s+(\w+)$", t)
        if m:
            a, b = (self._wezel_z_tekstu(x, zdanie) for x in m.groups())
            self.rozlaczne.append((a, b, zdanie.strip(" .")))
            return True
        m = re.match(rf"^{wszystkie}\s+(\w+)\s+(?:sa|jest|to)\s+(\w+)$", t) or \
            re.match(r"^(\w+)\s+(?:jest|sa|to)\s+(\w+)$", t)
        if m:
            a, b = (self._wezel_z_tekstu(x, zdanie) for x in m.groups())
            if a != b:
                self.jest.setdefault(a, []).append((b, zdanie.strip(" .")))
                return True
        m = re.match(r"^(\w+)\s+nie\s+(?:jest|sa)\s+(\w+)$", t)
        if m:
            a, b = (self._wezel_z_tekstu(x, zdanie) for x in m.groups())
            self.nie_jest.setdefault(a, []).append((b, zdanie.strip(" .")))
            return True
        m = re.match(rf"^{wszystkie}\s+(\w+)\s+(\w+\s.+)$", t)
        if m:
            a = self._wezel_z_tekstu(m.group(1), zdanie)
            oryginal = zdanie.strip(" .").split(None, 2)[2]
            self.cechy.setdefault(a, []).append((oryginal, zdanie.strip(" .")))
            return True
        return False

    def _wezel_z_tekstu(self, slowo, zdanie):
        istniejacy = self._znajdz(slowo)
        if istniejacy:
            return istniejacy
        # Nowe słowo z przesłanki: zapamiętujemy je z oryginalną pisownią.
        oryginal = next((s for s in re.findall(r"[\w-]+", zdanie) if normalizuj(s) == slowo), slowo)
        klucz = lemat(oryginal)
        self.wyswietl.setdefault(klucz, oryginal)
        self.indeks.setdefault(klucz, klucz)
        self.indeks.setdefault(normalizuj(oryginal), klucz)
        return klucz

    def naucz(self, zdanie):
        """„zapamiętaj, że Burek jest psem” - fakt na stałe. Zwraca True, gdy zrozumiany."""
        if not self._dodaj_zdanie(zdanie):
            return False
        self.nauczone.append(zdanie)
        if self.plik_pamieci:
            os.makedirs(os.path.dirname(self.plik_pamieci), exist_ok=True)
            with open(self.plik_pamieci, "w", encoding="utf-8") as f:
                json.dump({"zdania": self.nauczone}, f, ensure_ascii=False, indent=1)
        return True

    # --- wnioskowanie --------------------------------------------------------

    def _przodkowie(self, wezel):
        """{przodek: [uzasadnienia po kolei]} - przeszukiwanie wszerz po „X jest Y”."""
        sciezki, kolejka = {wezel: []}, [wezel]
        while kolejka:
            biezacy = kolejka.pop(0)
            for rodzic, dlaczego in self.jest.get(biezacy, []):
                if rodzic not in sciezki:
                    sciezki[rodzic] = sciezki[biezacy] + [dlaczego]
                    kolejka.append(rodzic)
        return sciezki

    def _rozlaczne(self, a, b):
        # Najpierw przesłanki podane wprost ("Żaden ptak nie jest ssakiem"), potem wbudowane.
        for x, y, dlaczego in sorted(self.rozlaczne, key=lambda r: r[2] is None):
            if {x, y} == {a, b}:
                return _zdanie_w_srodku(dlaczego) if dlaczego else \
                    f"{self.mnoga.get(a, self.wyswietl[a])} i {self.mnoga.get(b, self.wyswietl[b])} to rozłączne grupy"
        if a in self.lisc and b in self.lisc and a != b:
            return f"{self.wyswietl[a]} i {self.wyswietl[b]} to różne gatunki"
        return None

    @staticmethod
    def _dlaczego(kroki):
        kroki = [kroki[0]] + [_zdanie_w_srodku(k) for k in kroki[1:]]
        if len(kroki) <= 2:
            return ", a ".join(kroki)
        return ", ".join(kroki[:-1]) + ", a " + kroki[-1]

    def czy_jest(self, x, y):
        """(odpowiedź, pewna)."""
        sciezki = self._przodkowie(x)
        nx, ny = self.wyswietl.get(x, x), self.wyswietl.get(y, y)
        if y in sciezki:
            return f"Tak. {_wielka(self._dlaczego(sciezki[y]))}.", True
        for przodek, kroki in sciezki.items():
            for nie, dlaczego in self.nie_jest.get(przodek, []):
                if nie == y or y in self._przodkowie(nie):
                    return f"Nie. {_wielka(self._dlaczego(kroki + [dlaczego]))}.", True
        przodkowie_y = self._przodkowie(y)
        for przodek, kroki in sciezki.items():
            for przodek_y in przodkowie_y:
                dlaczego = self._rozlaczne(przodek, przodek_y)
                if dlaczego:
                    return f"Nie. {_wielka(self._dlaczego(kroki + [dlaczego]))}.", True
        znane = [self.wyswietl.get(p, p) for p in sciezki if p != x]
        if znane:
            return (f"Nie wiem na pewno. Wiem tylko, że {nx} to: {', '.join(znane)} - z tego nie wynika, "
                    f"czy {nx} jest {self._narzednik(y, ny)}."), False
        return f"Nie wiem, czy {nx} jest {self._narzednik(y, ny)} - nie znam faktów, które by to łączyły.", False

    def _narzednik(self, wezel, domyslnie):
        return getattr(self, "kategorie_narz", {}).get(wezel, domyslnie)

    def czy_ma_ceche(self, x, orzeczenie):
        sciezki = self._przodkowie(x)
        nx = self.wyswietl.get(x, x)
        pytanie = {lemat(s) for s in re.findall(r"\w+", orzeczenie) if normalizuj(s) not in NIEISTOTNE}
        for przodek, kroki in sciezki.items():
            for cecha, dlaczego in self.cechy.get(przodek, []):
                tresc = {lemat(s) for s in re.findall(r"\w+", cecha) if normalizuj(s) not in NIEISTOTNE}
                if tresc and tresc <= pytanie:
                    return f"Tak. {_wielka(self._dlaczego(kroki + [dlaczego]))}.", True
        # Wykluczające się cechy: oddycha płucami / skrzelami, żyje w wodzie / na lądzie.
        czasownik = lemat(orzeczenie.split()[0]) if orzeczenie.split() else ""
        if czasownik in ("oddych",):
            for przodek, kroki in sciezki.items():
                for cecha, dlaczego in self.cechy.get(przodek, []):
                    if lemat(cecha.split()[0]) == czasownik:
                        return f"Nie. {_wielka(self._dlaczego(kroki + [dlaczego]))}.", True
        znane = [(p, c) for p in sciezki for c, _ in self.cechy.get(p, [])]
        if not znane:
            return f"Nie wiem - nie znam cech, które by o tym mówiły.", False
        grupa = next(p for p, _ in znane)
        cechy = ", ".join(c for p, c in znane if p == grupa)
        return (f"Nie wiem na pewno. Wiem, że {nx} to {self.wyswietl[grupa]}, a o grupie „{self.wyswietl[grupa]}” "
                f"wiem tylko tyle: {cechy}. O tym, o co pytasz, nie mam faktów."), False

    def _gdzie(self, miejsce):
        lancuch = []
        while miejsce in self.lezy_w:
            miejsce, dlaczego = self.lezy_w[miejsce]
            lancuch.append((miejsce, dlaczego))
        return lancuch

    def czy_lezy(self, x, y):
        lancuch = self._gdzie(x)
        miejsca = [m for m, _ in lancuch]
        if y in miejsca:
            kroki = [d for _, d in lancuch[:miejsca.index(y) + 1]]
            return f"Tak. {_wielka(self._dlaczego(kroki))}.", True
        poziom_y = len(self._gdzie(y))
        for i, (m, _) in enumerate(lancuch):
            if len(self._gdzie(m)) == poziom_y:
                kroki = [d for _, d in lancuch[:i + 1]]
                return (f"Nie. {_wielka(self._dlaczego(kroki))} - nie w {self.miejscownik.get(y, self.wyswietl[y])}."), True
        return f"Nie wiem, czy {self.wyswietl[x]} leży w {self.miejscownik.get(y, self.wyswietl[y])}.", False

    # --- odpowiedzi na pytania ----------------------------------------------

    def odpowiedz(self, tekst):
        """(odpowiedź, pewna) albo None, gdy to nie pytanie do rozumowania."""
        zdania = _zdania(tekst)
        if not zdania:
            return None
        pytanie = zdania[-1]
        przeslanki = zdania[:-1]
        if przeslanki:
            # Przesłanki z pytania: działamy na kopii, żeby nie zapamiętać ich na stałe.
            kopia = Rozumowanie.__new__(Rozumowanie)
            kopia.__dict__ = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else
                                  set(v) if isinstance(v, set) else v) for k, v in self.__dict__.items()}
            kopia.jest = {k: list(v) for k, v in self.jest.items()}
            kopia.nie_jest = {k: list(v) for k, v in self.nie_jest.items()}
            kopia.cechy = {k: list(v) for k, v in self.cechy.items()}
            zrozumiane = [kopia._dodaj_zdanie(p) for p in przeslanki]
            if any(zrozumiane):
                return kopia._pytanie(pytanie, z_przeslankami=True)
            # Wstęp bez faktów ("Hej. Czy pingwin jest ptakiem?") - odpowiadamy na samo pytanie.
        return self._pytanie(pytanie) or self.liczby(tekst)

    def _pytanie(self, pytanie, z_przeslankami=False):
        t = normalizuj(pytanie).strip(" ?.!")
        oryg = pytanie.strip(" ?.!")
        m = re.match(r"^czy\s+(.+?)\s+lez\w*\s+w[e]?\s+(.+)$", t)
        if m:
            x, y = self._znajdz(m.group(1)), self._znajdz(m.group(2))
            if x and y and x in self.lezy_w:
                return self.czy_lezy(x, y)
            return None
        m = re.match(r"^gdzie\s+lez\w*\s+(.+)$", t)
        if m:
            x = self._znajdz(m.group(1))
            if x and x in self.lezy_w:
                lancuch = self._gdzie(x)
                return (f"{self.wyswietl[x]} leży w {self.miejscownik.get(lancuch[0][0], lancuch[0][0])}"
                        + "".join(f", w {self.miejscownik.get(m_, m_)}" for m_, _ in lancuch[1:]) + "."), True
            return None
        m = re.match(r"^czy\s+(.+?)\s+(?:jest|to|sa)\s+(.+)$", t)
        if m:
            x, y = self._znajdz(m.group(1)), self._znajdz(m.group(2))
            if y is None or (x is None and not self._czy_kategoria(y)):
                return None
            if x is None:
                nazwa = oryg.split()[1] if len(oryg.split()) > 1 else m.group(1)
                return (f"Nie wiem, kim albo czym jest „{nazwa}”. Możesz mnie nauczyć: "
                        f"„zapamiętaj, że {nazwa} jest psem”."), False
            return self.czy_jest(x, y)
        m = re.match(r"^czy\s+(\w+)\s+(.+)$", t)
        if m:
            x = self._znajdz(m.group(1))
            if x and (z_przeslankami or self._przodkowie(x).keys() & self.cechy.keys()):
                return self.czy_ma_ceche(x, m.group(2))
        m = re.match(r"^(?:co\s+wiesz\s+o|opowiedz\s+(?:mi\s+)?o)\s+(.+)$", t)
        if m:
            x = self._znajdz(m.group(1))
            if x and x in self.jest:
                return self.opis(x), True
        return None

    def _czy_kategoria(self, wezel):
        return wezel in self.cechy or any(wezel == r for v in self.jest.values() for r, _ in v)

    def opis(self, x):
        sciezki = self._przodkowie(x)
        grupy = [self.wyswietl.get(p, p) for p in sorted(sciezki, key=lambda p: len(sciezki[p])) if p != x]
        linie = [f"**{_wielka(self.wyswietl[x])}** to: {' → '.join(grupy)}."]
        for p in sorted(sciezki, key=lambda p: len(sciezki[p])):
            if self.cechy.get(p):
                linie.append(f"- jako {self.wyswietl.get(p, p)}: {', '.join(c for c, _ in self.cechy[p])}")
        return "\n".join(linie)

    # --- fakty z liczbami ------------------------------------------------------

    def _dzis(self):
        return self.dzis or datetime.date.today()

    def _wzmianki(self, t, lista, klucz="wzorzec"):
        wynik = []
        for element in lista:
            m = re.search(element[klucz], t)
            if m:
                wynik.append((m.start(), element))
        return [e for _, e in sorted(wynik, key=lambda x: x[0])]

    def liczby(self, tekst):
        t = normalizuj(tekst)
        for metoda in (self._wiek, self._lata, self._porownanie, self._fizyka):
            wynik = metoda(t, tekst)
            if wynik:
                return wynik, True
        return None

    def _wiek(self, t, tekst):
        osoby = self._wzmianki(t, self.dane["osoby"])
        if len(osoby) != 1:
            return None
        o = osoby[0]
        k = o["nazwa"].split()[0].endswith("a")  # Maria, Anna - polskie imiona żeńskie
        urodzil, zmarl, zyl, mial = (("urodziła", "zmarła", "żyła", "Miała") if k else
                                     ("urodził", "zmarł", "żył", "Miał"))
        ur, zm = _data(o["urodzony"]), _data(o["zmarly"])
        if re.search(r"ile lat (zyl|zyla|przezyl)|w jakim wieku (zmarl|umarl)|ile lat mial\w* .*(zmarl|umarl|smierc)", t):
            wiek = _lata_miedzy(ur, zm)
            uwaga = ""
            if wiek != zm.year - ur.year:
                uwaga = (f" (lata {ur.year}-{zm.year} dają {zm.year - ur.year}, ale urodziny "
                         f"{ur.day}.{ur.month:02d} były później w roku niż śmierć {zm.day}.{zm.month:02d})")
            return (f"🔗 **Łączę fakty:** {o['nazwa']} {urodzil} się {ur.day}.{ur.month:02d}.{ur.year}, "
                    f"a {zmarl} {zm.day}.{zm.month:02d}.{zm.year}.\n**Odpowiedź:** {o['nazwa']} {zyl} "
                    f"**{_lat(wiek)}**{uwaga}.")
        m = re.search(r"ile lat mial\w*\s.*\b(gdy|kiedy|w chwili|podczas)\b", t)
        if m:
            wydarzenia = self._wzmianki(t[m.end():], self.dane["wydarzenia"])
            if wydarzenia:
                w = wydarzenia[0]
                kiedy = _data(w["data"])
                if not (ur <= kiedy if isinstance(kiedy, datetime.date) else ur.year <= kiedy):
                    return f"{o['nazwa']} {urodzil} się dopiero {ur.year} roku - po wydarzeniu: {w['nazwa']} ({_rok(kiedy)})."
                wiek = _lata_miedzy(ur, kiedy)
                return (f"🔗 **Łączę fakty:**\n1. {o['nazwa']} {urodzil} się {ur.day}.{ur.month:02d}.{ur.year}.\n"
                        f"2. {_wielka(w['nazwa'])}: {self._data_tekst(w['data'])}.\n"
                        f"**Odpowiedź:** {mial} wtedy **{_lat(wiek)}**.")
        if re.search(r"ile lat temu (urodzil|przyszl)", t):
            return (f"🔗 {o['nazwa']} {urodzil} się {ur.day}.{ur.month:02d}.{ur.year}, a dziś jest "
                    f"{self._dzis().day}.{self._dzis().month:02d}.{self._dzis().year}.\n"
                    f"**Odpowiedź:** {_lat(_lata_miedzy(ur, self._dzis()))} temu.")
        if re.search(r"ile lat temu (zmarl|umarl)", t):
            return (f"🔗 {o['nazwa']} {zmarl} {zm.day}.{zm.month:02d}.{zm.year}.\n"
                    f"**Odpowiedź:** {_lat(_lata_miedzy(zm, self._dzis()))} temu.")
        return None

    @staticmethod
    def _data_tekst(data):
        d = _data(data)
        return f"{d.day}.{d.month:02d}.{d.year}" if isinstance(d, datetime.date) else f"{d} rok"

    def _lata(self, t, tekst):
        if not re.search(r"ile (lat|czasu|wiekow)|jak dawno|ile minelo", t):
            return None
        wydarzenia = self._wzmianki(t, self.dane["wydarzenia"])
        if len(wydarzenia) == 2:
            a, b = wydarzenia
            da, db = _data(a["data"]), _data(b["data"])
            if (da.year if isinstance(da, datetime.date) else da) > (db.year if isinstance(db, datetime.date) else db):
                a, b, da, db = b, a, db, da
            lata = _lata_miedzy(da, db)
            return (f"🔗 **Łączę fakty:**\n1. {_wielka(a['nazwa'])}: {self._data_tekst(a['data'])}.\n"
                    f"2. {_wielka(b['nazwa'])}: {self._data_tekst(b['data'])}.\n"
                    f"3. Różnica: {_rok(db)} − {_rok(da)}"
                    + (f" (pełnych lat: {lata})" if lata != int(_rok(db)) - int(_rok(da)) else "")
                    + f".\n**Odpowiedź:** Minęło **{_lat(lata)}**.")
        if len(wydarzenia) == 1 and re.search(r"\btemu\b|minelo od|uplynelo od|jak dawno", t):
            w = wydarzenia[0]
            lata = _lata_miedzy(_data(w["data"]), self._dzis())
            return (f"🔗 **Łączę fakty:** {w['nazwa']} - {self._data_tekst(w['data'])}, a dziś jest "
                    f"{self._dzis().day}.{self._dzis().month:02d}.{self._dzis().year}.\n"
                    f"**Odpowiedź:** To było **{_lat(lata)} temu**.")
        return None

    def _porownanie(self, t, tekst):
        tryb = "razy" if re.search(r"ile razy", t) else "o ile" if re.search(r"\bo ile\b|roznic", t) else None
        if not tryb:
            return None
        byty = self._wzmianki(t, self.dane["liczby"])
        if len(byty) != 2 or byty[0]["symbol"] != byty[1]["symbol"]:
            return None
        a, b = byty
        mnoznik = szkola.MNOZNIK
        wa, wb = a["wartosc"] * mnoznik[a["jednostka"]], b["wartosc"] * mnoznik[b["jednostka"]]
        jedn = a["jednostka"] if a["jednostka"] == b["jednostka"] else szkola.JEDNOSTKA_SI[a["symbol"]]
        va, vb = wa / mnoznik[jedn], wb / mnoznik[jedn]
        L = szkola.liczba
        fakty = (f"🔗 **Łączę fakty:**\n1. {_wielka(a['opis'])}: {L(va)} {jedn}.\n"
                 f"2. {_wielka(b['opis'])}: {L(vb)} {jedn}.\n")
        if tryb == "razy":
            if vb == 0:
                return None
            return fakty + f"3. Iloraz: {L(va)} : {L(vb)} = **{L(va / vb)}**.\n**Odpowiedź:** {L(va / vb)} raza."
        return fakty + f"3. Różnica: {L(max(va, vb))} − {L(min(va, vb))} = **{L(abs(va - vb))} {jedn}**.\n" \
                       f"**Odpowiedź:** Różnica wynosi {L(abs(va - vb))} {jedn}."

    def _fizyka(self, t, tekst):
        byty = self._wzmianki(t, self.dane["liczby"])
        if not byty:
            return None
        fakty = [(b["symbol"], b["wartosc"], b["jednostka"], f"{b['opis']} - z mojej bazy faktów") for b in byty]
        wynik = szkola.fizyka(tekst, fakty=fakty)
        if not wynik:
            return None
        return "🔗 **Łączę fakty ze wzorem.**\n" + wynik
