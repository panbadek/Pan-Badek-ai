"""Solver matematyczny Pana Badka - w czystym Pythonie, z rozwiązaniami krok po kroku.

Umie: równania (liniowe, kwadratowe, dowolne - numerycznie), układy równań liniowych,
pochodne symboliczne, całki (wielomianów symbolicznie, reszta numerycznie), procenty,
statystykę, teorię liczb (liczby pierwsze, rozkład, NWD, NWW, silnia), systemy liczbowe
i zamianę jednostek. Wyrażenia czyta bezpiecznie przez ast - nic nie jest wykonywane.
"""

import ast
import datetime
import math
import re
import statistics
from fractions import Fraction

# --- czytanie wyrażeń --------------------------------------------------------------

_FUNKCJE = {"sin": math.sin, "cos": math.cos, "tg": math.tan, "tan": math.tan, "exp": math.exp,
            "ln": math.log, "log": math.log10, "sqrt": math.sqrt, "pierwiastek": math.sqrt,
            "abs": abs}
_STALE = {"pi": math.pi, "e": math.e}


class BladMatematyczny(ValueError):
    pass


def przygotuj(wyrazenie):
    """Zapis "ludzki" -> zapis Pythona: 2x -> 2*x, x^2 -> x**2, 3(x+1) -> 3*(x+1), 2,5 -> 2.5."""
    w = wyrazenie.strip().lower()
    w = w.replace("−", "-").replace("·", "*").replace("×", "*").replace("÷", "/").replace("^", "**")
    w = w.replace("²", "**2").replace("³", "**3")
    w = re.sub(r"(\d),(\d)", r"\1.\2", w)
    w = re.sub(r"√\s*\(", "sqrt(", w)
    w = re.sub(r"√\s*([\d.]+|[a-z])", r"sqrt(\1)", w)
    nazwy = "|".join(sorted(list(_FUNKCJE) + list(_STALE), key=len, reverse=True))
    # Mnożenie domyślne: liczba lub ")" przed zmienną, funkcją albo "(".
    w = re.sub(rf"(\d|\))\s*(?=({nazwy})\b|[a-z(])", r"\1*", w)
    # Zmienna przed "(" lub inną zmienną (ale nie nazwa funkcji).
    w = re.sub(rf"\b([xyz])\s*(?=\()", r"\1*", w)
    w = re.sub(r"\b([xyz])([xyz])\b", r"\1*\2", w)
    return w


class Wyr:
    """Węzeł drzewa wyrażenia (do liczenia i różniczkowania)."""

    def __init__(self, typ, *dzieci, wartosc=None):
        self.typ, self.dzieci, self.wartosc = typ, dzieci, wartosc

    # konstruktory z uproszczeniami
    @staticmethod
    def liczba(v):
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        return Wyr("num", wartosc=v)

    def jest(self, v):
        return self.typ == "num" and self.wartosc == v

    def __add__(self, b):
        if self.jest(0):
            return b
        if b.jest(0):
            return self
        if self.typ == b.typ == "num":
            return Wyr.liczba(self.wartosc + b.wartosc)
        return Wyr("+", self, b)

    def __sub__(self, b):
        if b.jest(0):
            return self
        if self.typ == b.typ == "num":
            return Wyr.liczba(self.wartosc - b.wartosc)
        if self.jest(0):
            return -b
        return Wyr("-", self, b)

    def __mul__(self, b):
        if self.jest(0) or b.jest(0):
            return Wyr.liczba(0)
        if b.typ == "/" and b.dzieci[0].jest(1):  # a · (1/b) = a/b
            return self / b.dzieci[1]
        if self.typ == "/" and self.dzieci[0].jest(1):
            return b / self.dzieci[1]
        if self.jest(1):
            return b
        if b.jest(1):
            return self
        if self.typ == b.typ == "num":
            return Wyr.liczba(self.wartosc * b.wartosc)
        if b.typ == "num":
            return Wyr("*", b, self)
        return Wyr("*", self, b)

    def __truediv__(self, b):
        if self.jest(0):
            return Wyr.liczba(0)
        if str(self) == str(b):
            return Wyr.liczba(1)
        if b.jest(1):
            return self
        return Wyr("/", self, b)

    def __pow__(self, b):
        if b.jest(0):
            return Wyr.liczba(1)
        if b.jest(1):
            return self
        return Wyr("**", self, b)

    def __neg__(self):
        if self.typ == "num":
            return Wyr.liczba(-self.wartosc)
        if self.typ == "neg":
            return self.dzieci[0]
        return Wyr("neg", self)

    # liczenie
    def licz(self, zmienne):
        t, d = self.typ, self.dzieci
        if t == "num":
            return self.wartosc
        if t == "var":
            if self.wartosc in _STALE and self.wartosc not in zmienne:
                return _STALE[self.wartosc]
            if self.wartosc not in zmienne:
                raise BladMatematyczny(f"nieznana zmienna {self.wartosc}")
            return zmienne[self.wartosc]
        if t == "neg":
            return -d[0].licz(zmienne)
        if t == "fun":
            return _FUNKCJE[self.wartosc](d[0].licz(zmienne))
        a, b = d[0].licz(zmienne), d[1].licz(zmienne)
        if t == "+":
            return a + b
        if t == "-":
            return a - b
        if t == "*":
            return a * b
        if t == "/":
            return a / b
        if t == "**":
            if abs(b) > 1000:
                raise BladMatematyczny("za duża potęga")
            return a ** b
        raise BladMatematyczny(t)

    # różniczkowanie
    def pochodna(self, x="x"):
        t, d = self.typ, self.dzieci
        if t == "num":
            return Wyr.liczba(0)
        if t == "var":
            return Wyr.liczba(1 if self.wartosc == x else 0)
        if t == "neg":
            return -d[0].pochodna(x)
        if t in "+-" and len(t) == 1:
            return d[0].pochodna(x) + d[1].pochodna(x) if t == "+" else d[0].pochodna(x) - d[1].pochodna(x)
        if t == "*":
            u, v = d
            return u.pochodna(x) * v + u * v.pochodna(x)
        if t == "/":
            u, v = d
            return (u.pochodna(x) * v - u * v.pochodna(x)) / (v ** Wyr.liczba(2))
        if t == "**":
            u, n = d
            if not n.zawiera(x):  # u^n
                return n * u ** (n - Wyr.liczba(1)) * u.pochodna(x)
            if not u.zawiera(x):  # a^v
                return self * _ln(u) * n.pochodna(x)
            # u^v = e^(v ln u)
            return self * (n.pochodna(x) * _ln(u) + n * u.pochodna(x) / u)
        if t == "fun":
            u = d[0]
            du = u.pochodna(x)
            f = self.wartosc
            if f == "sin":
                wew = Wyr("fun", u, wartosc="cos")
            elif f == "cos":
                wew = -Wyr("fun", u, wartosc="sin")
            elif f in ("tg", "tan"):
                wew = Wyr.liczba(1) / Wyr("fun", u, wartosc="cos") ** Wyr.liczba(2)
            elif f == "exp":
                wew = self
            elif f == "ln":
                wew = Wyr.liczba(1) / u
            elif f == "log":
                wew = Wyr.liczba(1) / (u * Wyr("fun", Wyr.liczba(10), wartosc="ln"))
            elif f == "sqrt":
                wew = Wyr.liczba(1) / (Wyr.liczba(2) * self)
            else:
                raise BladMatematyczny(f"nie umiem różniczkować {f}")
            return wew * du
        raise BladMatematyczny(t)

    def zawiera(self, x):
        if self.typ == "var":
            return self.wartosc == x
        return any(d.zawiera(x) for d in self.dzieci)

    def zmienne(self):
        """Niewiadome w wyrażeniu (bez stałych pi i e)."""
        if self.typ == "var":
            return set() if self.wartosc in _STALE else {self.wartosc}
        return set().union(*(d.zmienne() for d in self.dzieci)) if self.dzieci else set()

    # zapis
    _PRIORYTET = {"+": 1, "-": 1, "*": 2, "/": 2, "neg": 3, "**": 4}

    def __str__(self):
        t, d = self.typ, self.dzieci
        if t == "num":
            return formatuj(self.wartosc)
        if t == "var":
            return self.wartosc
        if t == "fun":
            return f"{self.wartosc}({d[0]})"
        if t == "neg":
            return "-" + self._w_nawiasie(d[0], 3)
        p = self._PRIORYTET[t]
        lewy = self._w_nawiasie(d[0], p + (1 if t == "**" else 0))
        prawy = self._w_nawiasie(d[1], p + (0 if t in ("+", "*") else 1) - (1 if t == "**" else 0))
        if t == "*" and d[0].typ == "num" and d[1].typ in ("var", "fun", "**"):
            return f"{lewy}{prawy}"
        znak = {"**": "^", "*": "·"}.get(t, t)
        return f"{lewy}{znak}{prawy}" if t in ("**", "*", "/") else f"{lewy} {znak} {prawy}"

    def _w_nawiasie(self, wezel, minimalny):
        tekst = str(wezel)
        p = self._PRIORYTET.get(wezel.typ, 5)
        if wezel.typ == "num" and wezel.wartosc < 0:
            p = 3
        return f"({tekst})" if p < minimalny else tekst


def _ln(u):
    """ln(u) z uproszczeniem ln(e) = 1."""
    if u.typ == "var" and u.wartosc == "e":
        return Wyr.liczba(1)
    return Wyr("fun", u, wartosc="ln")


def wczytaj(wyrazenie):
    """Tekst -> drzewo Wyr (tylko liczby, zmienne x/y/z, stałe, + - * / ^ i znane funkcje)."""
    try:
        drzewo = ast.parse(przygotuj(wyrazenie), mode="eval").body
    except SyntaxError as e:
        raise BladMatematyczny("nie rozumiem tego wyrażenia") from e

    def zamien(w):
        if isinstance(w, ast.Constant) and isinstance(w.value, (int, float)):
            return Wyr.liczba(w.value)
        if isinstance(w, ast.Name):
            if w.id in _STALE:
                return Wyr("var", wartosc=w.id)  # pi i e zostają symbolami (ładniejszy zapis pochodnych)
            if w.id in ("x", "y", "z", "t", "a", "b"):
                return Wyr("var", wartosc=w.id)
            raise BladMatematyczny(f"nieznana nazwa: {w.id}")
        if isinstance(w, ast.UnaryOp) and isinstance(w.op, (ast.USub, ast.UAdd)):
            return -zamien(w.operand) if isinstance(w.op, ast.USub) else zamien(w.operand)
        if isinstance(w, ast.BinOp):
            ops = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "**"}
            if type(w.op) in ops:
                return Wyr(ops[type(w.op)], zamien(w.left), zamien(w.right))
        if (isinstance(w, ast.Call) and isinstance(w.func, ast.Name) and w.func.id in _FUNKCJE
                and len(w.args) == 1 and not w.keywords):
            nazwa = {"pierwiastek": "sqrt", "tan": "tg"}.get(w.func.id, w.func.id)
            return Wyr("fun", zamien(w.args[0]), wartosc=nazwa)
        raise BladMatematyczny("nieobsługiwany element wyrażenia")

    return zamien(drzewo)


def _licz(wyr, x):
    return wyr.licz({"x": x, "pi": math.pi, "t": x})


def formatuj(v):
    if isinstance(v, Fraction):
        return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"
    if isinstance(v, complex):
        return f"{formatuj(v.real)} {'+' if v.imag >= 0 else '-'} {formatuj(abs(v.imag))}i"
    if isinstance(v, float):
        if v.is_integer() and abs(v) < 1e15:
            return str(int(v))
        return f"{v:.6g}".replace(".", ",")
    return str(v)


# --- wielomiany ------------------------------------------------------------------

def wielomian(wyr, x="x"):
    """Współczynniki wielomianu {potęga: Fraction} albo None, gdy to nie wielomian."""
    t, d = wyr.typ, wyr.dzieci
    if t == "num":
        return {0: Fraction(wyr.wartosc).limit_denominator(10 ** 9)}
    if t == "var":
        return {1: Fraction(1)} if wyr.wartosc == x else None
    if t == "neg":
        p = wielomian(d[0], x)
        return {k: -v for k, v in p.items()} if p is not None else None
    if t in ("+", "-", "*"):
        a, b = wielomian(d[0], x), wielomian(d[1], x)
        if a is None or b is None:
            return None
        wynik = {}
        if t == "*":
            for i, u in a.items():
                for j, v in b.items():
                    wynik[i + j] = wynik.get(i + j, 0) + u * v
        else:
            znak = 1 if t == "+" else -1
            for k in set(a) | set(b):
                wynik[k] = a.get(k, 0) + znak * b.get(k, 0)
        return {k: v for k, v in wynik.items() if v != 0} or {0: Fraction(0)}
    if t == "/":
        a, b = wielomian(d[0], x), wielomian(d[1], x)
        if a is None or b is None or set(b) != {0} or b[0] == 0:
            return None
        return {k: v / b[0] for k, v in a.items()}
    if t == "**":
        a, n = wielomian(d[0], x), d[1]
        if a is None or n.typ != "num" or not float(n.wartosc).is_integer() or not 0 <= n.wartosc <= 20:
            return None
        wynik = {0: Fraction(1)}
        for _ in range(int(n.wartosc)):
            wynik = wielomian(Wyr("*", _z_wielomianu(wynik, x), _z_wielomianu(a, x)), x)
        return wynik
    return None


def _z_wielomianu(p, x="x"):
    wyr = Wyr.liczba(0)
    for k in sorted(p):
        wyr = wyr + Wyr.liczba(float(p[k]) if p[k].denominator != 1 else int(p[k])) * (
            Wyr("var", wartosc=x) ** Wyr.liczba(k) if k else Wyr.liczba(1))
    return wyr


def zapis_wielomianu(p, x="x"):
    czesci = []
    for k in sorted(p, reverse=True):
        a = p[k]
        if a == 0:
            continue
        znak = "-" if a < 0 else "+"
        a = abs(a)
        wsp = "" if a == 1 and k else formatuj(a)
        if wsp and "/" in wsp and k:
            wsp = f"({wsp})"
        czlon = wsp + (x if k == 1 else f"{x}^{k}" if k else "")
        czesci.append((znak, czlon))
    if not czesci:
        return "0"
    pierwszy = ("-" if czesci[0][0] == "-" else "") + czesci[0][1]
    return pierwszy + "".join(f" {z} {c}" for z, c in czesci[1:])


# --- równania --------------------------------------------------------------------

def _pierwiastki_numeryczne(f, od=-1000, do=1000, krokow=20000):
    wyniki = []

    def wartosc(x):
        try:
            v = f(x)
            return v if isinstance(v, (int, float)) and math.isfinite(v) else None
        except (ValueError, ZeroDivisionError, OverflowError):
            return None

    krok = (do - od) / krokow
    poprzedni_x, poprzednia = od, wartosc(od)
    for i in range(1, krokow + 1):
        x = od + i * krok
        v = wartosc(x)
        if v is not None and poprzednia is not None:
            if v == 0:
                wyniki.append(x)
            elif poprzednia * v < 0:
                a, b, fa = poprzedni_x, x, poprzednia
                for _ in range(80):
                    m = (a + b) / 2
                    fm = wartosc(m)
                    if fm is None:
                        break
                    if fa * fm <= 0:
                        b = m
                    else:
                        a, fa = m, fm
                kandydat = (a + b) / 2
                if abs(wartosc(kandydat) or 1) < 1e-6:  # odrzucamy bieguny (np. 1/x)
                    wyniki.append(kandydat)
        poprzedni_x, poprzednia = x, v
    unikalne = []
    for r in wyniki:
        if all(abs(r - u) > 1e-6 for u in unikalne):
            unikalne.append(r)
    return [round(r, 10) for r in unikalne]


def _sprawdzenie(L, P, x, rozwiazania):
    """Podstawia rozwiązania do obu stron równania - jak sprawdzenie w zeszycie."""
    linie = []
    for v in rozwiazania[:3]:
        try:
            lewa, prawa = L.licz({x: float(v)}), P.licz({x: float(v)})
        except (ValueError, ZeroDivisionError, OverflowError):
            continue
        zgodne = abs(lewa - prawa) <= 1e-6 * max(1.0, abs(lewa), abs(prawa))
        f = lambda w: formatuj(round(w, 6))  # noqa: E731
        linie.append(f"dla {x} = {formatuj(v)}: lewa strona = {f(lewa)}, prawa strona = {f(prawa)} "
                     + ("✓" if zgodne else "✗"))
    return ["**Sprawdzenie:** " + "; ".join(linie)] if linie else []


def rozwiaz_rownanie(tekst):
    lewa, prawa = tekst.split("=", 1)
    L, P = wczytaj(lewa), wczytaj(prawa)
    zmienne = L.zmienne() | P.zmienne()
    if len(zmienne) != 1:
        raise BladMatematyczny("równanie powinno mieć jedną niewiadomą")
    x = zmienne.pop()
    roznica = Wyr("-", L, P)
    p = wielomian(roznica, x)
    kroki = [f"**Równanie:** {lewa.strip()} = {prawa.strip()}"]
    if p is not None:
        stopien = max(p)
        kroki.append(f"Przenoszę wszystko na lewą stronę: **{zapis_wielomianu(p, x)} = 0**")
        if stopien == 0:
            return "\n".join(kroki + ["To równanie jest " + ("**tożsamościowe** - spełnia je każde " + x
                                      if p.get(0, 0) == 0 else "**sprzeczne** - nie ma rozwiązań") + "."])
        if stopien == 1:
            a, b = p[1], p.get(0, Fraction(0))
            wynik = f"**{x} = {formatuj(-b / a)}**" + (
                f" (≈ {formatuj(float(-b / a))})" if (-b / a).denominator != 1 else "")
            if a == 1:
                kroki.append(f"To równanie liniowe, więc od razu: {wynik}")
            else:
                kroki.append(f"To równanie liniowe: {formatuj(a)}{x} = {formatuj(-b)}")
                kroki.append(f"Dzielę obie strony przez {formatuj(a)}: {wynik}")
            return "\n".join(kroki + _sprawdzenie(L, P, x, [-b / a]))
        if stopien == 2:
            a, b, c = p[2], p.get(1, Fraction(0)), p.get(0, Fraction(0))
            delta = b * b - 4 * a * c
            kroki.append(f"To równanie kwadratowe: a = {formatuj(a)}, b = {formatuj(b)}, c = {formatuj(c)}")
            czworka = formatuj(4 * a * c) if 4 * a * c >= 0 else f"({formatuj(4 * a * c)})"
            kroki.append(f"Δ = b² - 4ac = {formatuj(b * b)} - {czworka} = **{formatuj(delta)}**")
            if delta > 0:
                pd = math.sqrt(delta)
                x1, x2 = (-float(b) - pd) / (2 * float(a)), (-float(b) + pd) / (2 * float(a))
                dokladne = math.isqrt(delta.numerator) ** 2 == delta.numerator and \
                    math.isqrt(delta.denominator) ** 2 == delta.denominator
                if dokladne:
                    s = Fraction(math.isqrt(delta.numerator), math.isqrt(delta.denominator))
                    x1d, x2d = (-b - s) / (2 * a), (-b + s) / (2 * a)
                    kroki.append(f"√Δ = {formatuj(s)}")
                    kroki.append(f"{x}₁ = (-b - √Δ) / 2a = **{formatuj(x1d)}**, {x}₂ = (-b + √Δ) / 2a = **{formatuj(x2d)}**")
                    kroki += _sprawdzenie(L, P, x, [x1d, x2d])
                else:
                    kroki.append(f"√Δ ≈ {formatuj(pd)}")
                    kroki.append(f"{x}₁ = (-b - √Δ) / 2a ≈ **{formatuj(x1)}**, {x}₂ = (-b + √Δ) / 2a ≈ **{formatuj(x2)}**")
                    kroki += _sprawdzenie(L, P, x, [x1, x2])
            elif delta == 0:
                kroki.append(f"Δ = 0, więc jest jedno rozwiązanie: {x} = -b / 2a = **{formatuj(-b / (2 * a))}**")
                kroki += _sprawdzenie(L, P, x, [-b / (2 * a)])
            else:
                re_ = -float(b) / (2 * float(a))
                im = math.sqrt(-delta) / (2 * abs(float(a)))
                kroki.append("Δ < 0, więc **brak rozwiązań rzeczywistych**.")
                kroki.append(f"Rozwiązania zespolone: {x} = {formatuj(re_)} ± {formatuj(im)}i")
            return "\n".join(kroki)
    # Równanie wyższego stopnia albo nie-wielomianowe: szukamy miejsc zerowych numerycznie.
    funkcja = lambda v: roznica.licz({x: v})  # noqa: E731
    for zakres in (10, 100, 1000):
        pierwiastki = _pierwiastki_numeryczne(funkcja, -zakres, zakres, krokow=zakres * 200)
        if pierwiastki:
            break
    kroki.append(f"Szukam rozwiązań numerycznie (bisekcja) na przedziale od -{zakres} do {zakres}.")
    if not pierwiastki:
        kroki.append("Nie znalazłem rzeczywistych rozwiązań w tym przedziale.")
        return "\n".join(kroki)
    kroki.append("Rozwiązania: " + ", ".join(f"**{x} ≈ {formatuj(r)}**" for r in pierwiastki[:8])
                 + (" …" if len(pierwiastki) > 8 else ""))
    kroki += _sprawdzenie(L, P, x, pierwiastki[:2])
    if len(pierwiastki) > 8 or any(f in str(roznica) for f in ("sin", "cos", "tg")):
        kroki.append("Funkcje trygonometryczne są okresowe, więc rozwiązań jest nieskończenie wiele "
                     "- powyżej te najbliżej zera.")
    return "\n".join(kroki)


def rozwiaz_uklad(rownania):
    """Układ równań liniowych - eliminacja Gaussa na ułamkach (wynik dokładny)."""
    wiersze, zmienne = [], set()
    for r in rownania:
        lewa, prawa = r.split("=", 1)
        roznica = Wyr("-", wczytaj(lewa), wczytaj(prawa))
        zmienne |= roznica.zmienne()
        wiersze.append(roznica)
    zmienne = sorted(zmienne)
    if not zmienne or len(zmienne) > 4:
        raise BladMatematyczny("układ powinien mieć od 1 do 4 niewiadomych")
    macierz = []
    for roznica in wiersze:
        # Współczynniki z wartości w punktach (równanie musi być liniowe - sprawdzamy to).
        zero = {v: 0 for v in zmienne}
        c = Fraction(roznica.licz(zero)).limit_denominator(10 ** 9)
        wsp = []
        for v in zmienne:
            punkt = dict(zero, **{v: 1})
            wsp.append(Fraction(roznica.licz(punkt)).limit_denominator(10 ** 9) - c)
        test = {v: 2 + i for i, v in enumerate(zmienne)}
        if abs(roznica.licz(test) - float(sum(w * test[v] for w, v in zip(wsp, zmienne)) + c)) > 1e-9:
            raise BladMatematyczny("to nie jest układ równań liniowych")
        macierz.append(wsp + [-c])
    n, m = len(zmienne), len(macierz)
    wiersz = 0
    for kolumna in range(n):
        os_ = next((i for i in range(wiersz, m) if macierz[i][kolumna] != 0), None)
        if os_ is None:
            continue
        macierz[wiersz], macierz[os_] = macierz[os_], macierz[wiersz]
        dz = macierz[wiersz][kolumna]
        macierz[wiersz] = [v / dz for v in macierz[wiersz]]
        for i in range(m):
            if i != wiersz and macierz[i][kolumna] != 0:
                k = macierz[i][kolumna]
                macierz[i] = [a - k * b for a, b in zip(macierz[i], macierz[wiersz])]
        wiersz += 1
    if any(all(v == 0 for v in r[:-1]) and r[-1] != 0 for r in macierz):
        return "Ten układ jest **sprzeczny** - nie ma rozwiązań."
    if wiersz < n:
        return "Ten układ ma **nieskończenie wiele rozwiązań** (równania są zależne)."
    wynik = {}
    for r in macierz[:n]:
        k = next(i for i in range(n) if r[i] == 1)
        wynik[zmienne[k]] = r[-1]
    linie = ["**Układ równań** (eliminacja Gaussa):"] + [f"- {r.strip()}" for r in rownania]
    linie.append("Rozwiązanie: " + ", ".join(f"**{v} = {formatuj(w)}**" for v, w in wynik.items()))
    return "\n".join(linie)


# --- analiza: pochodne i całki ---------------------------------------------------

def pochodna(wyrazenie):
    w = wczytaj(wyrazenie)
    x = "x" if "x" in w.zmienne() or not w.zmienne() else sorted(w.zmienne())[0]
    p = wielomian(w, x)
    if p is not None:
        pw = {k - 1: v * k for k, v in p.items() if k > 0} or {0: Fraction(0)}
        return (f"f({x}) = {zapis_wielomianu(p, x)}\n"
                f"Pochodna liczona wzorem (a·{x}ⁿ)' = n·a·{x}ⁿ⁻¹:\n**f'({x}) = {zapis_wielomianu(pw, x)}**")
    return f"f({x}) = {w}\n**f'({x}) = {w.pochodna(x)}**"


def calka(wyrazenie, od=None, do=None):
    w = wczytaj(wyrazenie)
    p = wielomian(w, "x")
    linie = []
    if p is not None:
        F = {k + 1: v / (k + 1) for k, v in p.items()}
        linie.append(f"Funkcja pierwotna: F(x) = {zapis_wielomianu(F)}" + (" + C" if od is None else ""))
        if od is not None:
            wartosc = sum(v * (Fraction(do).limit_denominator() ** k - Fraction(od).limit_denominator() ** k)
                          for k, v in F.items())
            linie.append(f"∫ od {formatuj(od)} do {formatuj(do)} = F({formatuj(do)}) - F({formatuj(od)}) = "
                         f"**{formatuj(wartosc)}**" + (f" (≈ {formatuj(float(wartosc))})" if wartosc.denominator != 1 else ""))
        return "\n".join(linie)
    if od is None:
        return ("Symbolicznie całkuję tylko wielomiany. Podaj granice, np. „całka z sin(x) od 0 do pi”, "
                "a policzę ją numerycznie.")
    n = 2000
    h = (do - od) / n
    suma = _licz(w, od) + _licz(w, do)
    for i in range(1, n):
        suma += (4 if i % 2 else 2) * _licz(w, od + i * h)
    return f"∫ od {formatuj(od)} do {formatuj(do)} z {w} dx ≈ **{formatuj(suma * h / 3)}** (metoda Simpsona)"


# --- teoria liczb ------------------------------------------------------------------

def czy_pierwsza(n):
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    return all(n % d for d in range(3, math.isqrt(n) + 1, 2))


def czynniki(n):
    wynik, d = [], 2
    while d * d <= n:
        while n % d == 0:
            wynik.append(d)
            n //= d
        d += 1
    if n > 1:
        wynik.append(n)
    return wynik


def _zapis_czynnikow(lista):
    potegi = {}
    for c in lista:
        potegi[c] = potegi.get(c, 0) + 1
    return " · ".join(f"{c}^{k}" if k > 1 else str(c) for c, k in sorted(potegi.items()))


_RZYMSKIE = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
             (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def rzymska(n):
    wynik = ""
    for wartosc, znak in _RZYMSKIE:
        while n >= wartosc:
            wynik += znak
            n -= wartosc
    return wynik


# --- jednostki ---------------------------------------------------------------------

_JEDNOSTKI = {  # nazwa -> (wielkość, mnożnik do jednostki podstawowej)
    "mm": ("dł", 0.001), "cm": ("dł", 0.01), "m": ("dł", 1), "km": ("dł", 1000),
    "cal": ("dł", 0.0254), "cali": ("dł", 0.0254), "stopa": ("dł", 0.3048), "stóp": ("dł", 0.3048),
    "stopy": ("dł", 0.3048), "jard": ("dł", 0.9144), "mila": ("dł", 1609.344), "mile": ("dł", 1609.344),
    "mil": ("dł", 1609.344), "mili": ("dł", 1609.344),
    "mg": ("masa", 0.001), "g": ("masa", 1), "dag": ("masa", 10), "kg": ("masa", 1000), "t": ("masa", 1e6),
    "funt": ("masa", 453.59237), "funty": ("masa", 453.59237), "funtów": ("masa", 453.59237),
    "uncja": ("masa", 28.349523125), "uncje": ("masa", 28.349523125), "uncji": ("masa", 28.349523125),
    "ml": ("obj", 0.001), "l": ("obj", 1), "litr": ("obj", 1), "litry": ("obj", 1), "litrów": ("obj", 1),
    "galon": ("obj", 3.785411784), "galony": ("obj", 3.785411784), "galonów": ("obj", 3.785411784),
    "s": ("czas", 1), "sek": ("czas", 1), "min": ("czas", 60), "h": ("czas", 3600), "godz": ("czas", 3600),
    "dni": ("czas", 86400), "dzień": ("czas", 86400), "doba": ("czas", 86400),
    "km/h": ("pręd", 1 / 3.6), "m/s": ("pręd", 1), "mph": ("pręd", 0.44704), "węzłów": ("pręd", 0.514444),
    "b": ("dane", 1), "kb": ("dane", 1024), "mb": ("dane", 1024 ** 2), "gb": ("dane", 1024 ** 3),
    "tb": ("dane", 1024 ** 4),
}
_TEMPERATURY = {"c": "C", "°c": "C", "celsjusza": "C", "f": "F", "°f": "F", "fahrenheita": "F",
                "k": "K", "kelwinów": "K", "kelwina": "K"}


def _na_kelwiny(v, j):
    return {"C": v + 273.15, "F": (v - 32) * 5 / 9 + 273.15, "K": v}[j]


def _z_kelwinow(v, j):
    return {"C": v - 273.15, "F": (v - 273.15) * 9 / 5 + 32, "K": v}[j]


def zamien_jednostki(liczba, z, na):
    z, na = z.lower().strip(" .°"), na.lower().strip(" .°")
    if z in ("stopni", "st") or na in ("stopni", "st"):
        return None
    tz, tna = _TEMPERATURY.get(z) or _TEMPERATURY.get("°" + z), _TEMPERATURY.get(na) or _TEMPERATURY.get("°" + na)
    if tz and tna:
        wynik = _z_kelwinow(_na_kelwiny(liczba, tz), tna)
        return f"{formatuj(liczba)} °{tz} = **{formatuj(round(wynik, 4))} °{tna}**" if tna != "K" else \
            f"{formatuj(liczba)} °{tz} = **{formatuj(round(wynik, 4))} K**"
    if z in _JEDNOSTKI and na in _JEDNOSTKI and _JEDNOSTKI[z][0] == _JEDNOSTKI[na][0]:
        wynik = liczba * _JEDNOSTKI[z][1] / _JEDNOSTKI[na][1]
        return f"{formatuj(liczba)} {z} = **{formatuj(round(wynik, 6))} {na}**"
    return None


# --- rozpoznawanie poleceń ----------------------------------------------------------

_LICZBA = r"-?\d+(?:[.,]\d+)?"
_I = re.I


def _liczba(t):
    return float(t.replace(",", "."))


def _liczby(tekst):
    return [_liczba(x) for x in re.findall(_LICZBA, tekst)]


_WZORY = []


def _wzor(regex):
    def dekorator(funkcja):
        _WZORY.append((re.compile(regex, _I), funkcja))
        return funkcja
    return dekorator


_MIESIACE = ["stycz", "lut", "mar", "kwie", "maj", "czerw", "lip", "sierp", "wrze", "pazdz", "listop", "grud"]
_DNI_TYGODNIA = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]


@_wzor(r"dzie[nń]\w*\s+tygodnia\D*?(\d{1,2})(?:\s*\.\s*|\s+)([a-ząćęłńóśźż]+|\d{1,2})(?:(?:\s*\.\s*|\s+)(\d{1,4}))?")
def _dzien_tygodnia(m):
    """ "jaki dzień tygodnia był 1 stycznia 2000" -> sobota."""
    dzien, miesiac, rok = int(m.group(1)), m.group(2).lower(), m.group(3)
    if miesiac.isdigit():
        miesiac = int(miesiac)
    else:
        miesiac = next((i + 1 for i, nazwa in enumerate(_MIESIACE)
                        if miesiac.translate(str.maketrans("ąćęłńóśźż", "acelnoszz")).startswith(nazwa)), None)
    teraz = datetime.date.today()
    try:
        data = datetime.date(int(rok) if rok else teraz.year, miesiac or 0, dzien)
    except ValueError:
        return None
    dzien_tygodnia = _DNI_TYGODNIA[data.weekday()]
    zenski = dzien_tygodnia in ("środa", "sobota", "niedziela")
    czas = ("była" if zenski else "był") if data < teraz else "jest" if data == teraz else "będzie"
    return f"{data.day}.{data.month:02d}.{data.year} {czas} **{dzien_tygodnia}**."


@_wzor(rf"^\s*(?:ile\s+to\s+|oblicz\s+|policz\s+)?({_LICZBA})\s*(?:%|procent\w*)\s+(?:z|od)\s+({_LICZBA})\s*\??\s*$")
def _procent_z(m):
    p, z = _liczba(m.group(1)), _liczba(m.group(2))
    return f"{formatuj(p)}% z {formatuj(z)} = {formatuj(z)} · {formatuj(p)} / 100 = **{formatuj(round(z * p / 100, 10))}**"


@_wzor(rf"o\s+ile\s+procent\w*.*?\bz\s+({_LICZBA})\s+(?:do|na)\s+({_LICZBA})")
def _zmiana_procentowa(m):
    a, b = _liczba(m.group(1)), _liczba(m.group(2))
    if a == 0:
        return "Nie da się policzyć zmiany procentowej od zera."
    zmiana = (b - a) / a * 100
    kierunek = "wzrost" if zmiana >= 0 else "spadek"
    return (f"Zmiana: ({formatuj(b)} - {formatuj(a)}) / {formatuj(a)} · 100% = "
            f"**{formatuj(round(zmiana, 4))}%** ({kierunek})")


@_wzor(rf"(?:jakim\s+procentem|ile\s+procent)\s+(?:liczby\s+)?({_LICZBA})\s+(?:jest|stanowi)\s+({_LICZBA})"
       rf"|ile\s+procent\s+({_LICZBA})\s+(?:stanowi|to)\s+({_LICZBA})")
def _jaki_procent(m):
    if m.group(1):  # "jakim procentem 200 jest 50" -> 50 to x% z 200
        calosc, czesc = _liczba(m.group(1)), _liczba(m.group(2))
    else:  # "ile procent 200 stanowi 50"
        calosc, czesc = _liczba(m.group(3)), _liczba(m.group(4))
    return f"{formatuj(czesc)} / {formatuj(calosc)} · 100% = **{formatuj(round(czesc / calosc * 100, 4))}%**"


@_wzor(r"^\s*(?:oblicz\s+|podaj\s+|policz\s+)?(średni\w*|srednia|mediana?|median\w*|odchyleni\w*|wariancj\w*|"
       r"sum\w*|statystyk\w*|dominant\w*|moda)\s*(?:z|dla|liczb|ciągu|danych)?\s*:?\s*([-\d.,;\s]+)\??$")
def _statystyka(m):
    dane = _liczby(m.group(2).replace(";", " "))
    if len(dane) < 1:
        return None
    co = m.group(1).lower()
    wyniki = {
        "średnia": statistics.fmean(dane), "mediana": statistics.median(dane),
        "suma": sum(dane), "min": min(dane), "max": max(dane),
    }
    if len(dane) > 1:
        wyniki["odchylenie standardowe"] = statistics.stdev(dane)
        wyniki["wariancja"] = statistics.variance(dane)
    try:
        wyniki["dominanta"] = statistics.mode(dane)
    except statistics.StatisticsError:
        pass
    klucz = ("średnia" if co.startswith(("śr", "sr")) else "mediana" if co.startswith("med")
             else "odchylenie standardowe" if co.startswith("odch") else "wariancja" if co.startswith("war")
             else "suma" if co.startswith("sum") else "dominanta" if co.startswith(("dom", "mod")) else None)
    dane_txt = ", ".join(formatuj(v) for v in dane)
    if klucz and klucz in wyniki:
        return f"{klucz.capitalize()} z [{dane_txt}] = **{formatuj(round(wyniki[klucz], 6))}**"
    return f"Statystyki dla [{dane_txt}]:\n" + "\n".join(
        f"- {k}: **{formatuj(round(v, 6))}**" for k, v in wyniki.items())


@_wzor(r"czy\s+(\d+)\s+(?:jest\s+)?(?:liczb\w+\s+)?pierwsz")
def _pierwsza(m):
    n = int(m.group(1))
    if czy_pierwsza(n):
        return f"Tak, **{n} jest liczbą pierwszą** - dzieli się tylko przez 1 i przez siebie."
    if n < 2:
        return f"Nie, {n} nie jest liczbą pierwszą (liczby pierwsze są większe od 1)."
    return f"Nie, {n} nie jest liczbą pierwszą: **{n} = {_zapis_czynnikow(czynniki(n))}**"


@_wzor(r"(?:rozłóż|rozloz|rozkład\w*|czynniki\s+pierwsze)\s+(?:liczb\w+\s+)?(\d+)|(\d+)\s+na\s+czynniki")
def _rozklad(m):
    n = int(m.group(1) or m.group(2))
    if n < 2 or n > 10 ** 13:
        return None
    return f"**{n} = {_zapis_czynnikow(czynniki(n))}**"


@_wzor(r"(nwd|największ\w+\s+wspóln\w+\s+dzielnik\w*|nww|najmniejsz\w+\s+wspóln\w+\s+wielokrotn\w*)"
       r"\s*(?:z|dla|liczb)?\s*\(?\s*(\d+)\s*(?:,|i|oraz)\s*(\d+)")
def _nwd(m):
    a, b = int(m.group(2)), int(m.group(3))
    if m.group(1).lower().startswith(("nwd", "najwi")):
        kroki, x, y = [], a, b
        while y:
            kroki.append(f"{x} = {x // y}·{y} + {x % y}")
            x, y = y, x % y
        return "Algorytm Euklidesa:\n" + "\n".join(f"- {k}" for k in kroki[:12]) + f"\n**NWD({a}, {b}) = {x}**"
    return f"NWW({a}, {b}) = a·b / NWD = {a * b} / {math.gcd(a, b)} = **{a * b // math.gcd(a, b)}**"


@_wzor(r"(?:silni\w*\s+(?:z\s+)?(\d+)|(\d+)\s*!)")
def _silnia(m):
    n = int(m.group(1) or m.group(2))
    if n > 500:
        return "To liczba zbyt wielka, żeby ją wypisać."
    return f"**{n}! = {math.factorial(n)}**"


@_wzor(r"(\d+)\s*(?:\.|-)?\s*(?:wyraz|element|liczb\w*)\s+(?:ciągu\s+)?fibonacci\w*|fibonacci\w*\s+(?:dla\s+|n\s*=\s*)?(\d+)")
def _fibonacci(m):
    n = int(m.group(1) or m.group(2))
    if n > 1000:
        return None
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return f"**F({n}) = {a}** (ciąg Fibonacciego: F(0)=0, F(1)=1, F(n)=F(n-1)+F(n-2))"


@_wzor(r"(?:zamień|zamien|przelicz|zapisz|ile\s+to)\s+(\d+)\s+(?:na|w|jako)\s+(?:system\s+)?"
       r"(binarn\w*|dwójkow\w*|dwojkow\w*|szesnastkow\w*|hex\w*|ósemkow\w*|osemkow\w*|rzymsk\w*)")
def _systemy(m):
    n, na = int(m.group(1)), m.group(2).lower()
    if na.startswith(("bin", "dwó", "dwo")):
        return f"{n} (dziesiętnie) = **{bin(n)[2:]}** (dwójkowo)"
    if na.startswith(("szes", "hex")):
        return f"{n} (dziesiętnie) = **{hex(n)[2:].upper()}** (szesnastkowo)"
    if na.startswith(("ósem", "osem")):
        return f"{n} (dziesiętnie) = **{oct(n)[2:]}** (ósemkowo)"
    if 0 < n < 4000:
        return f"{n} = **{rzymska(n)}** (cyframi rzymskimi)"
    return "Cyframi rzymskimi zapiszę liczby od 1 do 3999."


@_wzor(rf"^\s*(?:ile\s+to\s+|zamień\s+|zamien\s+|przelicz\s+)?({_LICZBA})\s*(°?\s?[a-ząćęłńóśźż/]+)"
       rf"\s+(?:na|w|to|=|ile)\s+(?:ile\s+)?(°?\s?[a-ząćęłńóśźż/]+)\s*\??\s*$")
def _jednostki(m):
    return zamien_jednostki(_liczba(m.group(1)), m.group(2).replace(" ", ""), m.group(3).replace(" ", ""))


@_wzor(r"(?:pochodn\w*|zróżniczkuj|zrozniczkuj|d/dx)\s*(?:z\s+|funkcji\s+|od\s+)?(?:f\s*\(\s*x\s*\)\s*=\s*|y\s*=\s*)?(.+?)\s*\??$")
def _pochodna(m):
    return pochodna(m.group(1))


@_wzor(rf"(?:całk\w*|calk\w*|∫)\s*(?:oznaczon\w*\s+)?(?:z\s+|funkcji\s+)?(.+?)"
       rf"(?:\s+(?:od|w\s+granicach\s+od)\s+({_LICZBA}|pi|-pi)\s+do\s+({_LICZBA}|pi|-pi|2pi))?\s*(?:dx)?\s*\??$")
def _calka(m):
    wyr = re.sub(r"\s*dx\s*$", "", m.group(1))
    if m.group(2) is None:
        return calka(wyr)
    granica = {"pi": math.pi, "-pi": -math.pi, "2pi": 2 * math.pi}
    od = granica.get(m.group(2)) if m.group(2) in granica else _liczba(m.group(2))
    do = granica.get(m.group(3)) if m.group(3) in granica else _liczba(m.group(3))
    return calka(wyr, od, do)


_UKLAD = re.compile(r"^\s*(?:rozwiąż|rozwiaz|oblicz)?\s*(?:układ(?:\s+równań)?|uklad(?:\s+rownan)?)\s*:?\s*(.+)$", _I)
_ROWNANIE = re.compile(r"^\s*(?:rozwiąż|rozwiaz|oblicz|wyznacz\s+x\s+z|znajdź\s+x)?\s*(?:równanie|rownanie)?\s*:?\s*"
                       r"([^=]*[a-z][^=]*=[^=]+?|[^=]+=[^=]*[a-z][^=]*?)\s*\??$", _I)


def rozwiaz(tekst):
    """Próbuje rozwiązać zadanie matematyczne. Zwraca odpowiedź albo None, gdy to nie zadanie."""
    tekst = tekst.strip()
    try:
        uklad = _UKLAD.match(tekst)
        if uklad or tekst.count("=") >= 2:
            czesci = re.split(r"\s*(?:[,;]|\s+i\s+|\s+oraz\s+)\s*", uklad.group(1) if uklad else tekst)
            czesci = [re.sub(r"^\s*(?:rozwiąż|rozwiaz)\s*", "", c, flags=_I) for c in czesci if "=" in c]
            if len(czesci) >= 2:
                return rozwiaz_uklad(czesci)
        for wzor, funkcja in _WZORY:
            m = wzor.search(tekst)
            if m:
                wynik = funkcja(m)
                if wynik:
                    return wynik
        rownanie = _ROWNANIE.match(tekst)
        if rownanie and re.search(r"\b[xyzt]\b|\d[xyzt]\b", rownanie.group(1), _I):
            return rozwiaz_rownanie(rownanie.group(1))
    except (BladMatematyczny, ZeroDivisionError, OverflowError, ValueError, RecursionError) as e:
        if isinstance(e, BladMatematyczny) and re.match(r"^\s*(rozwiąż|rozwiaz|pochodn|całk|calk)", tekst, _I):
            return f"Próbowałem to policzyć, ale {e}. Spróbuj zapisać to inaczej, np. „rozwiąż 2x + 3 = 7”."
        return None
    return None
