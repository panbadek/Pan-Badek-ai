"""Zadania szkolne rozwiązywane jak w zeszycie: Dane, Szukane, Wzór, Rozwiązanie, Odpowiedź.

Działa offline. Obsługuje:
- fizykę z jednostkami: ruch, siła, gęstość, praca, moc, ciśnienie, prąd, energia,
  z zamianą jednostek (np. 30 min = 0,5 h),
- geometrię: pola, obwody, objętości, przekątne i twierdzenie Pitagorasa,
- procenty w zadaniach: obniżki, podwyżki i cenę sprzed zmiany,
- zadania z treścią: „Ania miała 12 cukierków, zjadła 3, dostała 5…”.

Gdy zadanie nie pasuje do żadnego wzoru, solver zwraca None. Badek nie zgaduje,
tylko oddaje zadanie mocniejszemu AI albo prosi o przepisanie treści.
"""

import math
import re

from .text import normalizuj

_LICZBA = r"(\d+(?:[.,]\d+)?)"


def liczba(x, miejsca=2):
    """Liczba po polsku: przecinek dziesiętny, bez zbędnych zer; "≈" gdy zaokrąglona."""
    zaokraglona = round(x, miejsca)
    tekst = f"{zaokraglona:.{miejsca}f}".rstrip("0").rstrip(".").replace(".", ",")
    if tekst in ("-0", ""):
        tekst = "0"
    return tekst if abs(zaokraglona - x) < 1e-9 else "≈ " + tekst


def _wartosc(tekst):
    return float(tekst.replace(",", "."))


def _przygotuj(tekst):
    t = re.sub(r"\bpół\s*tor(?:a|ej)\s+godzin\w*", "1,5 h", tekst, flags=re.I)
    t = re.sub(r"\bpół\s+godzin\w*", "0,5 h", t, flags=re.I)
    t = re.sub(r"\bkwadrans\w*", "15 min", t, flags=re.I)
    return t


# --- fizyka --------------------------------------------------------------------

# (wzorzec jednostki, wielkość, mnożnik do jednostki SI, zapis). Kolejność ma znaczenie:
# dłuższe jednostki przed krótszymi ("km/h" przed "km", "m/s²" przed "m/s" przed "m").
# Jednoliterowe jednostki, które są też polskimi słowami ("W", "A", "N"), tylko wielką literą.
_JEDNOSTKI = [
    (r"km\s*/\s*h|km\s*/\s*godz\w*|km\s+na\s+godzin\w*|kilometr\w*\s+na\s+godzin\w*", "v", 1 / 3.6, "km/h"),
    (r"m\s*/\s*s(?:²|2|\^2)|m\s*/\s*s\s*\^\s*2", "a", 1, "m/s²"),
    (r"m\s*/\s*s|metr\w*\s+na\s+sekund\w*", "v", 1, "m/s"),
    (r"g\s*/\s*cm(?:³|3|\^3)", "ρ", 1000, "g/cm³"),
    (r"kg\s*/\s*m(?:³|3|\^3)", "ρ", 1, "kg/m³"),
    (r"cm(?:²|2|\^2)|centymetr\w*\s+kwadrat\w*", "S", 1e-4, "cm²"),
    (r"m(?:²|2|\^2)|metr\w*\s+kwadrat\w*", "S", 1, "m²"),
    (r"cm(?:³|3|\^3)|centymetr\w*\s+sześcien\w*", "V", 1e-6, "cm³"),
    (r"dm(?:³|3|\^3)|l\b|litr\w*", "V", 1e-3, "dm³"),
    (r"m(?:³|3|\^3)|metr\w*\s+sześcien\w*", "V", 1, "m³"),
    (r"km|kilometr\w*", "s", 1000, "km"),
    (r"cm|centymetr\w*", "s", 0.01, "cm"),
    (r"mm|milimetr\w*", "s", 0.001, "mm"),
    (r"m|metr\w*", "s", 1, "m"),
    (r"h|godz\.?|godzin\w*", "t", 3600, "h"),
    (r"min\.?|minut\w*", "t", 60, "min"),
    (r"s|sek\.?|sekund\w*", "t", 1, "s"),
    (r"kg|kilogram\w*", "m", 1, "kg"),
    (r"g|gram\w*|dag", "m", 1e-3, "g"),
    (r"t|ton\w*", "m", 1000, "t"),
    (r"(?-i:kN)|kiloniuton\w*", "F", 1000, "kN"),
    (r"(?-i:N)|niuton\w*", "F", 1, "N"),
    (r"(?-i:kJ)|kilodżul\w*", "E", 1000, "kJ"),
    (r"(?-i:J)|dżul\w*", "E", 1, "J"),
    (r"(?-i:kW)|kilowat\w*", "P", 1000, "kW"),
    (r"(?-i:W)|wat\w*", "P", 1, "W"),
    (r"(?-i:hPa)|hektopaskal\w*", "p", 100, "hPa"),
    (r"(?-i:kPa)|kilopaskal\w*", "p", 1000, "kPa"),
    (r"(?-i:Pa)|paskal\w*", "p", 1, "Pa"),
    (r"(?-i:V)|wolt\w*", "U", 1, "V"),
    (r"(?-i:mA)|miliamper\w*", "I", 1e-3, "mA"),
    (r"(?-i:A)|amper\w*", "I", 1, "A"),
    (r"Ω|om\b|omów|omy", "R", 1, "Ω"),
]
_JEDNOSTKI = [(re.compile(r"\s*(?:" + w + r")(?![a-ząćęłńóśźż²³])", re.I), g, k, z) for w, g, k, z in _JEDNOSTKI]
MNOZNIK = {z: k for _, _, k, z in _JEDNOSTKI}

NAZWY = {"s": "droga", "t": "czas", "v": "prędkość", "a": "przyspieszenie", "m": "masa", "F": "siła",
         "ρ": "gęstość", "V": "objętość", "W": "praca", "E": "energia", "P": "moc", "p": "ciśnienie",
         "S": "powierzchnia", "U": "napięcie", "I": "natężenie prądu", "R": "opór", "h": "wysokość"}
JEDNOSTKA_SI = {"s": "m", "h": "m", "t": "s", "v": "m/s", "a": "m/s²", "m": "kg", "F": "N", "ρ": "kg/m³",
                "V": "m³", "W": "J", "E": "J", "P": "W", "p": "Pa", "S": "m²", "U": "V", "I": "A", "R": "Ω"}
# Wielkości tego samego rodzaju (wysokość to droga, praca to energia).
_RODZAJ = {"h": "s", "W": "E"}
g = 10  # w szkole zwykle przyjmuje się g ≈ 10 m/s²

# Słowa w pytaniu, które mówią, czego szukamy.
_SZUKANE = [
    ("v", r"predkosc|predkoscia|jak szybko|szybkosc"),
    ("a", r"przyspieszen"),
    ("s", r"drog[aeiÄ™]|droge|jak daleko|odleglosc|ile kilometr|ile metr"),
    ("t", r"ile czasu|jak dlugo|w jakim czasie|po jakim czasie|ile godzin|ile minut|ile sekund|\bczas\b"),
    ("ρ", r"gestosc"),
    ("V", r"objetosc"),
    ("m", r"\bmas[aeęy]\b|\bmase\b|ile wazy"),
    ("F", r"\bsil[aeęy]\b|\bsile\b|\bsila\b|ciezar"),
    ("W", r"\bprac[aeęy]\b|\bprace\b"),
    ("E", r"energi"),
    ("P", r"\bmoc\b|\bmocy\b"),
    ("p", r"cisnieni"),
    ("U", r"napieci"),
    ("I", r"natezeni|jaki prad|jakie natez"),
    ("R", r"\bopor\b|opornosc|oporu"),
    ("h", r"wysokos"),
]

# Wzór: lewa = stała · Π prawa^wykładnik, oraz jego postaci rozwiązane względem każdej wielkości.
_WZORY = [
    ("ruch jednostajny", "s", 1, {"v": 1, "t": 1},
     {"s": "s = v · t", "v": "v = s / t", "t": "t = s / v"}),
    ("II zasada dynamiki Newtona", "F", 1, {"m": 1, "a": 1},
     {"F": "F = m · a", "m": "m = F / a", "a": "a = F / m"}),
    ("gęstość", "m", 1, {"ρ": 1, "V": 1},
     {"ρ": "ρ = m / V", "m": "m = ρ · V", "V": "V = m / ρ"}),
    ("praca", "W", 1, {"F": 1, "s": 1},
     {"W": "W = F · s", "F": "F = W / s", "s": "s = W / F"}),
    ("moc", "W", 1, {"P": 1, "t": 1},
     {"P": "P = W / t", "W": "W = P · t", "t": "t = W / P"}),
    ("ciśnienie", "F", 1, {"p": 1, "S": 1},
     {"p": "p = F / S", "F": "F = p · S", "S": "S = F / p"}),
    ("prawo Ohma", "U", 1, {"R": 1, "I": 1},
     {"U": "U = R · I", "R": "R = U / I", "I": "I = U / R"}),
    ("moc prądu", "P", 1, {"U": 1, "I": 1},
     {"P": "P = U · I", "U": "U = P / I", "I": "I = P / U"}),
    ("energia kinetyczna", "E", 0.5, {"m": 1, "v": 2},
     {"E": "Ek = m · v² / 2", "m": "m = 2 · Ek / v²", "v": "v = √(2 · Ek / m)"}),
    ("energia potencjalna", "E", g, {"m": 1, "h": 1},
     {"E": "Ep = m · g · h", "m": "m = Ep / (g · h)", "h": "h = Ep / (m · g)"}),
    ("ruch przyspieszony (od zera)", "v", 1, {"a": 1, "t": 1},
     {"a": "a = v / t", "v": "v = a · t", "t": "t = v / a"}),
    ("ciężar", "F", g, {"m": 1},
     {"F": "F = m · g", "m": "m = F / g"}),
]

# Układy jednostek, w których podajemy wynik - jak w zadaniu, a nie zawsze w SI.
_UKLAD_KMH = {"s": "km", "t": "h", "v": "km/h"}
_UKLAD_GCM = {"m": "g", "V": "cm³", "ρ": "g/cm³"}


def _wielkosci(tekst):
    """Liczby z jednostkami: [(symbol, wartość, jednostka, pozycja)]."""
    wynik = []
    for m in re.finditer(_LICZBA, tekst):
        if m.start() > 0 and tekst[m.start() - 1] in "^/":
            continue
        for wzor, symbol, _, zapis in _JEDNOSTKI:
            j = wzor.match(tekst, m.end())
            if j:
                przed = normalizuj(tekst[max(0, m.start() - 30):m.start()])
                if symbol == "s" and "wysokos" in przed:
                    symbol = "h"
                if symbol == "E" and re.search(r"prac", przed):
                    symbol = "W"
                wynik.append((symbol, _wartosc(m.group(1)), zapis, m.start()))
                break
    return wynik


def _pytanie(tekst):
    """Część z pytaniem: ostatnie zdanie albo fragment od "oblicz"/"ile"/"jak"."""
    zdania = [z for z in re.split(r"(?<=[.!?])\s+", tekst.strip()) if z]
    for z in reversed(zdania):
        if "?" in z or re.search(r"\b(oblicz|policz|wyznacz|podaj|ile|jak[aiąe]?)\b", z, re.I):
            return z
    return zdania[-1] if zdania else tekst


def _szukana(pytanie, dane):
    t = normalizuj(pytanie)
    znalezione = []
    for symbol, wzor in _SZUKANE:
        m = re.search(wzor, t)
        if m and symbol not in dane:
            znalezione.append((m.start(), symbol))
    return min(znalezione)[1] if znalezione else None


def _uklad(dane_jednostki, wzor_symbole):
    if set(wzor_symbole) <= {"s", "t", "v"} and set(dane_jednostki) & {"km/h", "km", "h", "min"}:
        return _UKLAD_KMH
    if set(wzor_symbole) <= {"m", "V", "ρ"} and set(dane_jednostki) & {"g", "cm³", "g/cm³"}:
        return _UKLAD_GCM
    return {}


def fizyka(tekst):
    tekst = _przygotuj(tekst)
    znalezione = _wielkosci(tekst)
    if not znalezione:
        return None
    dane = {}
    for symbol, wartosc, jednostka, _ in znalezione:
        if symbol in dane:  # dwie wartości tej samej wielkości - to nie nasz prosty wzór
            return None
        dane[symbol] = (wartosc, jednostka)
    szukana = _szukana(_pytanie(tekst), dane)
    if not szukana:
        return None
    if szukana == "F" and "ciezar" not in normalizuj(tekst) and set(dane) == {"m"}:
        return None
    kandydaci = []
    for nazwa, lewa, stala, prawa, postaci in _WZORY:
        symbole = {lewa, *prawa}
        if szukana not in postaci or not (symbole - {szukana}) <= set(dane):
            continue
        if nazwa == "ciężar" and "ciezar" not in normalizuj(tekst):
            continue
        kandydaci.append((len(symbole), nazwa, lewa, stala, prawa, postaci))
    if not kandydaci:
        return None
    _, nazwa, lewa, stala, prawa, postaci = max(kandydaci, key=lambda k: k[0])
    symbole = [lewa, *prawa]
    uklad = _uklad({j for _, j in dane.values()}, symbole)

    def w_ukladzie(symbol):
        return uklad.get(symbol, JEDNOSTKA_SI[symbol])

    # Dane i zamiana jednostek.
    linie_danych, zamiany, wartosci = [], [], {}
    for symbol in symbole:
        if symbol == szukana:
            continue
        wartosc, jednostka = dane[symbol]
        cel = w_ukladzie(symbol)
        linie_danych.append(f"{_symbol(symbol)} = {liczba(wartosc)} {jednostka}")
        przeliczona = wartosc * MNOZNIK[jednostka] / MNOZNIK[cel]
        if jednostka != cel:
            zamiany.append(f"{_symbol(symbol)} = {liczba(wartosc)} {jednostka} = {liczba(przeliczona, 4)} {cel}")
        wartosci[symbol] = przeliczona

    # Obliczenie w jednostkach SI (wzory są w SI), wynik w jednostce układu.
    si = {s: wartosci[s] * MNOZNIK[w_ukladzie(s)] for s in wartosci}
    if szukana == lewa:
        wynik_si = stala * math.prod(si[s] ** e for s, e in prawa.items())
    else:
        reszta = stala * math.prod(si[s] ** e for s, e in prawa.items() if s != szukana)
        if reszta == 0:
            return None
        wynik_si = (si[lewa] / reszta) ** (1 / prawa[szukana])
    jednostka_wyniku = w_ukladzie(szukana)
    wynik = wynik_si / MNOZNIK[jednostka_wyniku]

    postac = postaci[szukana]
    podstawienie = _podstaw(postac, wartosci, w_ukladzie)
    tekst_wyniku = f"{liczba(wynik)} {jednostka_wyniku}"
    if jednostka_wyniku == "h" and 0 < wynik < 10 and not float(wynik).is_integer():
        tekst_wyniku += f" = {liczba(wynik * 60)} min"
    linie = [f"#### Zadanie: {nazwa}",
             "**Dane:** " + ", ".join(linie_danych) + (", g ≈ 10 m/s²" if "g" in postac.split("=")[1] else ""),
             f"**Szukane:** {_symbol(szukana)} = ?"]
    if zamiany:
        linie.append("**Zamiana jednostek:** " + ", ".join(zamiany))
    linie += [f"**Wzór:** {postac}",
              f"**Rozwiązanie:** {podstawienie} = **{tekst_wyniku}**",
              f"**Odpowiedź:** {(nazwa if szukana == 'E' else NAZWY[szukana]).capitalize()} wynosi {tekst_wyniku}."]
    return "\n".join(linie)


def _symbol(s):
    return {"E": "E"}.get(s, s)


def _podstaw(postac, wartosci, jednostka):
    """ "s = v · t" -> "s = 60 km/h · 3 h" (z wartościami i jednostkami)."""
    lewa, prawa = postac.split(" = ", 1)

    def zamien(m):
        symbol = {"Ek": "E", "Ep": "E"}.get(m.group(1), m.group(1))
        if symbol == "g":
            wartosc = "10 m/s²"
        elif symbol in wartosci:
            wartosc = f"{liczba(wartosci[symbol], 4)} {jednostka(symbol)}"
        else:
            return m.group(0)
        return f"({wartosc}){m.group(2)}" if m.group(2) else wartosc  # (3 m/s)², a nie 3 m/s²
    return f"{lewa} = " + re.sub(r"(Ek|Ep|ρ|[a-zA-Z])(²?)", zamien, prawa)


# --- geometria -------------------------------------------------------------------

_FIGURY = [
    ("trójkąt równoboczny", r"trojkat\w* rownoboczn"),
    ("trójkąt prostokątny", r"trojkat\w* prostokatn|przyprostokatn|przeciwprostokatn|pitagoras"),
    ("trójkąt", r"trojkat"), ("kwadrat", r"kwadrat"), ("prostokąt", r"\bprostokat(?!n)"), ("koło", r"\bkol[aou]\b|\bkolo\b|okreg"), ("trapez", r"trapez"),
    ("równoległobok", r"rownoleglobok"), ("romb", r"\bromb"), ("sześcian", r"szescian"),
    ("prostopadłościan", r"prostopadloscian"), ("walec", r"\bwal[ec]"), ("stożek", r"stoz[ek]"), ("kula", r"\bkul[aiey]\b"),
]
_ROLE = [("r", r"promie\w*(?:\s+podstaw\w*)?"), ("d", r"srednic"), ("h", r"wysokos"), ("e", r"przekatn"),
         ("c", r"przeciwprostokatn"), ("ab", r"przyprostokatn"), ("ab", r"podstaw"), ("ab", r"bok|krawedz|wymiar")]
_DLUGOSCI = {"mm": 0.1, "cm": 1, "dm": 10, "m": 100, "km": 100000}
_SZUKANE_GEO = [("pole", r"\bpol[ea]\b|powierzchni"), ("obwód", r"obwod"), ("objętość", r"objetosc"),
                ("przekątna", r"przekatn"), ("bok", r"przeciwprostokatn|przyprostokatn|\bbok")]


def _wymiary(tekst):
    """Liczby z rolami (r, d, h, e, a/b/c) i wspólna jednostka długości."""
    wymiary, jednostki, poprzedni = [], [], 0
    for m in re.finditer(_LICZBA + r"\s*(mm|cm|dm|km|m)?(?![a-ząćęłńóśźż²³])", tekst):
        przed = normalizuj(tekst[poprzedni:m.start()])
        # Rola od słowa najbliższego liczbie ("przekątna kwadratu o boku 4" -> bok),
        # a przy remisie od ważniejszego ("promieniu podstawy 2" -> promień).
        trafienia = [(m2.end(), -i, r) for i, (r, w) in enumerate(_ROLE) for m2 in re.finditer(w, przed)]
        rola = max(trafienia)[2] if trafienia else None
        wymiary.append([rola, _wartosc(m.group(1)), m.group(2)])
        if m.group(2):
            jednostki.append(m.group(2))
        poprzedni = m.end()
    if not wymiary:
        return None, None
    # Wspólna jednostka: najmniejsza z podanych (zamieniamy na nią resztę).
    jednostka = min(jednostki, key=lambda j: _DLUGOSCI[j]) if jednostki else ""
    for w in wymiary:
        if w[2] and jednostka and w[2] != jednostka:
            w[1] = w[1] * _DLUGOSCI[w[2]] / _DLUGOSCI[jednostka]
    # Rola "kolejny bok" dla liczb bez opisu albo opisanych jako bok/podstawa.
    boki = iter("abc")
    for w in wymiary:
        if w[0] in (None, "ab"):
            w[0] = next(boki, None)
    return {w[0]: w[1] for w in wymiary if w[0]}, jednostka


def geometria(tekst):
    t = normalizuj(tekst)
    figura = next((f for f, w in _FIGURY if re.search(w, t)), None)
    if not figura:
        return None
    pytanie = normalizuj(_pytanie(tekst))
    szukane = next((s for s, w in _SZUKANE_GEO if re.search(w, pytanie)), None)
    w, j = _wymiary(tekst)
    if not w or not szukane:
        return None
    if "d" in w and "r" not in w:
        w["r"] = w["d"] / 2
    j2, j3 = (f" {j}²", f" {j}³") if j else ("", "")
    jd = f" {j}" if j else ""
    L = lambda x: liczba(x)  # noqa: E731

    def pi(x, jedn):  # wynik z π: dokładnie i w przybliżeniu
        return f"{L(x)}π{jedn} ≈ {L(x * math.pi).lstrip('≈ ')}{jedn}"

    a, b, c, h, r, e = (w.get(k) for k in "abchre")
    rozw = None
    if figura == "kwadrat" and a:
        rozw = {"pole": ("P = a²", f"P = {L(a)}² = **{L(a * a)}{j2}**"),
                "obwód": ("Obw = 4 · a", f"Obw = 4 · {L(a)} = **{L(4 * a)}{jd}**"),
                "przekątna": ("d = a√2", f"d = {L(a)}√2 = **{L(a)}√2{jd} ≈ {L(a * math.sqrt(2)).lstrip('≈ ')}{jd}**")}.get(szukane)
    elif figura == "prostokąt" and a and b:
        rozw = {"pole": ("P = a · b", f"P = {L(a)} · {L(b)} = **{L(a * b)}{j2}**"),
                "obwód": ("Obw = 2 · (a + b)", f"Obw = 2 · ({L(a)} + {L(b)}) = **{L(2 * (a + b))}{jd}**"),
                "przekątna": ("d = √(a² + b²)", f"d = √({L(a)}² + {L(b)}²) = **{L(math.hypot(a, b))}{jd}**")}.get(szukane)
    elif figura == "trójkąt równoboczny" and a:
        rozw = {"pole": ("P = a²√3 / 4", f"P = {L(a)}²√3 / 4 = **{L(a * a / 4)}√3{j2} ≈ {L(a * a * math.sqrt(3) / 4).lstrip('≈ ')}{j2}**"),
                "obwód": ("Obw = 3 · a", f"Obw = 3 · {L(a)} = **{L(3 * a)}{jd}**")}.get(szukane)
    elif figura == "trójkąt prostokątny" and szukane in ("bok", "przekątna", "obwód", "pole"):
        if c and a and not b:  # przeciwprostokątna i jedna przyprostokątna
            if c <= a:
                return None
            b = math.sqrt(c * c - a * a)
            rozw = ("a² + b² = c², więc b = √(c² - a²)", f"b = √({L(c)}² - {L(a)}²) = √{L(c * c - a * a)} = **{L(b)}{jd}**")
        elif a and b and not c:
            c = math.hypot(a, b)
            if szukane == "pole":
                rozw = ("P = a · b / 2", f"P = {L(a)} · {L(b)} / 2 = **{L(a * b / 2)}{j2}**")
            elif szukane == "obwód":
                rozw = ("c = √(a² + b²), Obw = a + b + c",
                        f"c = √({L(a)}² + {L(b)}²) = {L(c)}, Obw = {L(a)} + {L(b)} + {L(c).lstrip('≈ ')} = **{L(a + b + c)}{jd}**")
            else:
                rozw = ("a² + b² = c² (twierdzenie Pitagorasa)",
                        f"c = √({L(a)}² + {L(b)}²) = √{L(a * a + b * b)} = **{L(c)}{jd}**")
    elif figura == "trójkąt":
        if szukane == "pole" and a and h:
            rozw = ("P = a · h / 2", f"P = {L(a)} · {L(h)} / 2 = **{L(a * h / 2)}{j2}**")
        elif szukane == "obwód" and a and b and c:
            rozw = ("Obw = a + b + c", f"Obw = {L(a)} + {L(b)} + {L(c)} = **{L(a + b + c)}{jd}**")
    elif figura == "koło" and r:
        rozw = {"pole": ("P = πr²", f"P = π · {L(r)}² = **{pi(r * r, j2)}**"),
                "obwód": ("Obw = 2πr", f"Obw = 2π · {L(r)} = **{pi(2 * r, jd)}**")}.get(szukane)
    elif figura == "trapez" and szukane == "pole" and a and b and h:
        rozw = ("P = (a + b) · h / 2", f"P = ({L(a)} + {L(b)}) · {L(h)} / 2 = **{L((a + b) * h / 2)}{j2}**")
    elif figura == "równoległobok" and szukane == "pole" and a and h:
        rozw = ("P = a · h", f"P = {L(a)} · {L(h)} = **{L(a * h)}{j2}**")
    elif figura == "romb" and szukane == "pole":
        przekatne = [v for k, v in w.items() if k in ("e", "a", "b")]
        if len(przekatne) >= 2:
            e, f = przekatne[:2]
            rozw = ("P = e · f / 2", f"P = {L(e)} · {L(f)} / 2 = **{L(e * f / 2)}{j2}**")
    elif figura == "sześcian" and a:
        rozw = {"objętość": ("V = a³", f"V = {L(a)}³ = **{L(a ** 3)}{j3}**"),
                "pole": ("Pc = 6 · a²", f"Pc = 6 · {L(a)}² = **{L(6 * a * a)}{j2}**")}.get(szukane)
    elif figura == "prostopadłościan" and a and b and (c or h):
        c = c or h
        rozw = {"objętość": ("V = a · b · c", f"V = {L(a)} · {L(b)} · {L(c)} = **{L(a * b * c)}{j3}**"),
                "pole": ("Pc = 2 · (ab + bc + ac)",
                         f"Pc = 2 · ({L(a)}·{L(b)} + {L(b)}·{L(c)} + {L(a)}·{L(c)}) = **{L(2 * (a * b + b * c + a * c))}{j2}**")
                }.get(szukane)
    elif figura == "walec" and r and h:
        rozw = {"objętość": ("V = πr² · h", f"V = π · {L(r)}² · {L(h)} = **{pi(r * r * h, j3)}**"),
                "pole": ("Pc = 2πr² + 2πrh", f"Pc = 2π · {L(r)}² + 2π · {L(r)} · {L(h)} = **{pi(2 * r * r + 2 * r * h, j2)}**")
                }.get(szukane)
    elif figura == "stożek" and r and h and szukane == "objętość":
        rozw = ("V = πr² · h / 3", f"V = π · {L(r)}² · {L(h)} / 3 = **{pi(r * r * h / 3, j3)}**")
    elif figura == "kula" and r:
        rozw = {"objętość": ("V = 4/3 · πr³", f"V = 4/3 · π · {L(r)}³ = **{pi(4 / 3 * r ** 3, j3)}**"),
                "pole": ("P = 4πr²", f"P = 4π · {L(r)}² = **{pi(4 * r * r, j2)}**")}.get(szukane)
    if not rozw:
        return None
    wzor, obliczenie = rozw
    dane = ", ".join(f"{k} = {L(v)}{jd}" for k, v in w.items())
    wynik = obliczenie.split("**")[1]
    co = {"bok": "Szukany bok", "przekątna": "Przekątna"}.get(szukane, szukane.capitalize())
    return "\n".join([f"#### Zadanie: {figura}", f"**Dane:** {dane}", f"**Szukane:** {szukane}",
                      f"**Wzór:** {wzor}", f"**Rozwiązanie:** {obliczenie}",
                      f"**Odpowiedź:** {co} wynosi {wynik}."])


# --- procenty w zadaniach ----------------------------------------------------------

_W_DOL = r"obniz|przecen|zmniejsz|spad|tanie|rabat|znizk|mniej"
_W_GORE = r"podwyz|podnies|wzros|zwieksz|drozej|droze|wiecej|podroz"


def procenty(tekst):
    t = normalizuj(tekst)
    if len(t.split()) < 6:  # "ile to 15% z 200" to działanie dla kalkulatora, nie zadanie z treścią
        return None
    proc = re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:%|procent)", t)
    kwoty = re.findall(r"(\d+(?:[.,]\d+)?)\s*(zl|zlot\w*|euro|\$|dolar\w*|kg|osob|uczni\w*)?(?!\s*%|\d|\s*procent)", t)
    kwoty = [(k, j) for k, j in kwoty if k not in proc]
    if len(proc) != 1 or len(kwoty) != 1:
        return None
    p, (kwota, jedn) = _wartosc(proc[0]), kwoty[0]
    k = _wartosc(kwota)
    # Jednostkę dopisujemy tylko przy pieniądzach (reszta traciłaby polskie znaki z normalizacji).
    jedn = {"zl": " zł", "eu": " euro", "$": " $", "do": " dolarów"}.get((jedn or "")[:2], "")
    w_dol, w_gore = re.search(_W_DOL, t), re.search(_W_GORE, t)
    if not w_dol and not w_gore:
        # "W klasie jest 28 uczniów, 25% to dziewczynki. Ile jest dziewczynek?"
        czesc = k * p / 100
        return "\n".join([
            "#### Zadanie z procentami",
            f"**Dane:** całość = {liczba(k)}{jedn}, część = {liczba(p)}%",
            f"**Rozwiązanie:** {liczba(p)}% z {liczba(k)} = {liczba(k)} · {liczba(p)} / 100 = **{liczba(czesc)}{jedn}**",
            f"**Odpowiedź:** To {liczba(czesc)}{jedn}."])
    if w_dol and w_gore:
        return None
    znak = -1 if w_dol else 1
    zmiana = "obniżce" if w_dol else "podwyżce"
    czynnik = 1 + znak * p / 100
    wstecz = re.search(r"przed\s+(?:obnizk|podwyzk|przecen|zmian)|wczesniej|pierwotn|na poczatku|poprzednio", normalizuj(_pytanie(tekst)))
    if wstecz:
        przed = k / czynnik
        return "\n".join([
            "#### Zadanie z procentami",
            f"**Dane:** cena po {zmiana} = {liczba(k)}{jedn}, zmiana o {liczba(p)}%",
            "**Szukane:** cena przed zmianą = x",
            f"**Rozwiązanie:** po {zmiana} zostaje {liczba(100 + znak * p)}% ceny, więc "
            f"{liczba(czynnik, 4)} · x = {liczba(k)}{jedn}, x = {liczba(k)} : {liczba(czynnik, 4)} = **{liczba(przed)}{jedn}**",
            f"**Odpowiedź:** Przed zmianą było {liczba(przed)}{jedn}."])
    po = k * czynnik
    ile = k * p / 100
    return "\n".join([
        "#### Zadanie z procentami",
        f"**Dane:** na początku {liczba(k)}{jedn}, {'obniżka' if w_dol else 'podwyżka'} o {liczba(p)}%",
        "**Szukane:** wartość po zmianie",
        f"**Rozwiązanie:** {liczba(p)}% z {liczba(k)} = {liczba(k)} · {liczba(p / 100, 4)} = {liczba(ile)}{jedn}; "
        f"{liczba(k)} {'−' if w_dol else '+'} {liczba(ile)} = **{liczba(po)}{jedn}**",
        f"**Odpowiedź:** Po {zmiana} jest {liczba(po)}{jedn}."])


# --- zadania z treścią ----------------------------------------------------------------

_PLUS = (r"dosta|kupi|znalaz|doda|przyby|dolozy|dolozyl|zebra|przynios|dokupi|wygra|zarobi|dosypa|dola|"
         r"przyjecha|przyszl|przyszed|wsiad|przylecia|urodzil|dorzuci|uzbiera|otrzyma|dopisa")
_MINUS = (r"zjad|zjedl|odda|zgubi|sprzeda|wyda|ubyl|straci|zabra|odjecha|wyjecha|wysiad|zuzy|przegra|"
          r"uciekl|odlecia|wypil|wyszl|wyszed|poszl|pekl|zepsul|rozda|podarowa|pozyczy|wyrzuci|skresli|usuna")
_LICZEBNIKI = {"jeden": 1, "jedna": 1, "jedno": 1, "dwa": 2, "dwie": 2, "trzy": 3, "cztery": 4, "piec": 5,
               "szesc": 6, "siedem": 7, "osiem": 8, "dziewiec": 9, "dziesiec": 10}


def z_trescia(tekst):
    """ "Ania miała 12 cukierków. Zjadła 3, a potem dostała 5. Ile ma teraz?" """
    t = normalizuj(tekst)
    t = re.sub(r"\b(" + "|".join(_LICZEBNIKI) + r")\b", lambda m: str(_LICZEBNIKI[m.group(1)]), t)
    if "?" not in t and not re.search(r"\b(oblicz|ile)\b", t):
        return None
    if not re.search(r"\bile\b", normalizuj(_pytanie(tekst))):
        return None
    liczby = list(re.finditer(r"\d+(?:[.,]\d+)?", t))
    if not 2 <= len(liczby) <= 6 or re.search(r"%|procent|km|cm|\bm\b|kg|\bh\b|godzin|minut", t):
        return None
    kroki, wynik, poprzedni = [], None, 0
    for i, m in enumerate(liczby):
        x = _wartosc(m.group(0))
        przed = t[poprzedni:m.start()]
        po = t[m.end():m.end() + 30]
        poprzedni = m.end()
        # "brat jest o 3 lata starszy" / "2 razy więcej"
        porownanie = re.match(r"\s*(?:\w+\s+)?(?:\w+\s+)?(starsz|wyzsz|wiecej|dluzsz|drozsz|ciezsz|szybsz|"
                              r"mlodsz|nizsz|mniej|krotsz|tansz|lzejsz|wolniej)", po)
        if kroki and porownanie:
            plus = porownanie.group(1) in ("starsz", "wyzsz", "wiecej", "dluzsz", "drozsz", "ciezsz", "szybsz")
            if re.match(r"\s*razy", po):
                if not plus:
                    kroki.append((":", x, liczba(x)))
                else:
                    kroki.append(("·", x, liczba(x)))
                continue
            if re.search(r"\bo\s*$", przed):
                kroki.append(("+" if plus else "-", x, liczba(x)))
                continue
        # "4 paczki po 6 cukierków" -> 4 · 6
        if kroki and re.match(r"\s*\w*\s*po\s*$", t[liczby[i - 1].end():m.start()]) and kroki[-1][0] in ("start", "+", "-"):
            znak, poprz = kroki.pop()[0], liczby[i - 1].group(0)
            wartosc = _wartosc(poprz) * x
            kroki.append((znak, wartosc, f"{liczba(_wartosc(poprz))} · {liczba(x)}"))
            continue
        if re.search(r"(po\s+rowno|rowno)\s+(miedzy|na|pomiedzy)\s*$|podziel\w*.*(na|miedzy)\s*$", przed):
            kroki.append((":", x, liczba(x)))
            continue
        if re.search(r"\bza\s*$", przed):  # "kupił lody za 4 zł" - to wydatek
            kroki.append(("-", x, liczba(x)))
        elif re.search(_MINUS, przed):
            kroki.append(("-", x, liczba(x)))
        elif re.search(_PLUS, przed):
            kroki.append(("+", x, liczba(x)))
        elif i == 0:
            kroki.append(("start", x, liczba(x)))
        else:
            return None  # liczba bez czasownika - nie zgadujemy, co z nią zrobić
        del po
    if not kroki or kroki[0][0] not in ("start", "+"):
        return None
    zapis, wynik = kroki[0][2], kroki[0][1]
    for znak, wartosc, opis in kroki[1:]:
        if znak == "+":
            wynik += wartosc
        elif znak == "-":
            wynik -= wartosc
        elif znak == "·":
            wynik *= wartosc
            zapis = f"({zapis})" if any(z in zapis for z in "+−") else zapis
        elif znak == ":":
            if wartosc == 0:
                return None
            wynik /= wartosc
            zapis = f"({zapis})" if any(z in zapis for z in "+−") else zapis
        zapis += {"+": " + ", "-": " − ", ":": " : ", "·": " · "}[znak] + opis
    if wynik < 0:
        return None
    pytanie = normalizuj(_pytanie(tekst))
    rzecz = re.search(r"\bile\s+(\w+)", pytanie)
    rzecz = rzecz.group(1) if rzecz and rzecz.group(1) not in ("ma", "jest", "bylo", "zostalo", "teraz", "razem", "maja", "dostal", "dostala", "kazdy", "kazde", "kazda") else ""
    oryg = re.search(r"\bile\s+(\S+)", _pytanie(tekst), re.I)
    rzecz = oryg.group(1).strip("?.,!") if rzecz and oryg else ""
    # Dopełniacz z pytania ("ile cukierków") pasuje tylko do 0, 5-21, 25-31... ("24 naklejki").
    n = wynik
    if not (float(n).is_integer() and n != 1 and (n % 10 not in (2, 3, 4) or 12 <= n % 100 <= 14)):
        rzecz = ""
    return "\n".join(["#### Zadanie z treścią",
                      f"**Rozwiązanie:** {zapis} = **{liczba(wynik)}**",
                      f"**Odpowiedź:** {liczba(wynik)}{' ' + rzecz if rzecz else ''}."])


def rozwiaz(tekst):
    """Rozwiązanie zadania szkolnego albo None, gdy nie pasuje do żadnego wzoru."""
    if len(tekst) > 1500 or not re.search(r"\d", tekst):
        return None
    for solver in (geometria, fizyka, procenty, z_trescia):
        try:
            wynik = solver(tekst)
        except (ValueError, ZeroDivisionError, OverflowError):
            wynik = None
        if wynik:
            return wynik
    return None
