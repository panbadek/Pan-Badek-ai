"""Umiejętności, które nie wymagają uczenia: kalkulator i zegar."""

import ast
import datetime
import math
import operator
import re

_OPERATORY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_FUNKCJE = {"sqrt": math.sqrt, "pierwiastek": math.sqrt, "sin": math.sin,
            "cos": math.cos, "abs": abs, "round": round}
_STALE = {"pi": math.pi, "e": math.e}

_WYRAZENIE = re.compile(r"[\d\s.,+\-*/%^()a-z]*\d[\d\s.,+\-*/%^()a-z]*")
_SLOWNE = [("razy", "*"), ("podzielić przez", "/"), ("podzielone przez", "/"),
           ("przez", "/"), ("plus", "+"), ("minus", "-"), ("do potęgi", "**")]


def _oblicz(wezel):
    if isinstance(wezel, ast.Expression):
        return _oblicz(wezel.body)
    if isinstance(wezel, ast.Constant) and isinstance(wezel.value, (int, float)):
        return wezel.value
    if isinstance(wezel, ast.Name) and wezel.id in _STALE:
        return _STALE[wezel.id]
    if isinstance(wezel, ast.BinOp) and type(wezel.op) in _OPERATORY:
        lewy, prawy = _oblicz(wezel.left), _oblicz(wezel.right)
        if isinstance(wezel.op, ast.Pow) and abs(prawy) > 1000:
            raise ValueError("za duża potęga")
        return _OPERATORY[type(wezel.op)](lewy, prawy)
    if isinstance(wezel, ast.UnaryOp) and type(wezel.op) in _OPERATORY:
        return _OPERATORY[type(wezel.op)](_oblicz(wezel.operand))
    if (isinstance(wezel, ast.Call) and isinstance(wezel.func, ast.Name)
            and wezel.func.id in _FUNKCJE and not wezel.keywords):
        return _FUNKCJE[wezel.func.id](*[_oblicz(a) for a in wezel.args])
    raise ValueError("nieobsługiwane wyrażenie")


def oblicz(wyrazenie):
    """Bezpiecznie liczy wyrażenie matematyczne (bez eval)."""
    wyrazenie = wyrazenie.replace("^", "**").replace(",", ".")
    return _oblicz(ast.parse(wyrazenie.strip(), mode="eval"))


def formatuj_liczbe(wartosc):
    if isinstance(wartosc, float) and wartosc.is_integer() and abs(wartosc) < 1e15:
        return str(int(wartosc))
    if isinstance(wartosc, float):
        return f"{wartosc:.10g}"
    return str(wartosc)


def kalkulator(tekst):
    """Jeśli tekst zawiera działanie matematyczne, zwraca odpowiedź, w przeciwnym razie None."""
    maly = tekst.lower()
    for slowo, znak in _SLOWNE:
        maly = maly.replace(slowo, f" {znak} ")
    # Słowa, które nie są nazwą funkcji ani stałej, rozdzielają wyrażenia.
    maly = re.sub(r"[a-ząćęłńóśźż_]+",
                  lambda m: m.group() if m.group() in _FUNKCJE or m.group() in _STALE else "|",
                  maly)
    kandydaci = [k for czesc in maly.split("|") for k in _WYRAZENIE.findall(czesc)]
    for kandydat in sorted(kandydaci, key=len, reverse=True):
        kandydat = " ".join(kandydat.strip(" .,").split())
        if not re.search(r"[+\-*/%^(]", kandydat.lstrip("-")):
            continue
        try:
            wynik = oblicz(kandydat)
        except ZeroDivisionError:
            return "Nie dzielę przez zero - nawet ja mam swoje granice."
        except (ValueError, SyntaxError, TypeError, OverflowError):
            continue
        return f"{kandydat.strip()} = {formatuj_liczbe(wynik)}"
    return None


_DNI = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
_MIESIACE = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
             "sierpnia", "września", "października", "listopada", "grudnia"]


def godzina(teraz=None):
    teraz = teraz or datetime.datetime.now()
    return f"Jest godzina {teraz:%H:%M}."


def data(teraz=None):
    teraz = teraz or datetime.datetime.now()
    return (f"Dziś jest {_DNI[teraz.weekday()]}, {teraz.day} "
            f"{_MIESIACE[teraz.month - 1]} {teraz.year} r.")
