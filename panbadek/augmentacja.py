"""Augmentacja danych treningowych: z jednego zdania kilka wariantów, jakie ludzie
naprawdę piszą - z literówkami i z dopiskami ("słuchaj, ...", "... proszę").

Wielkość liter i polskie znaki Badek i tak normalizuje, więc takie warianty
nic by sieci nie dały. Literówki uczą ją rozpoznawać "dziekuej" i "zmeczny",
a dopiski - że "słuchaj, która godzina" to wciąż pytanie o godzinę.
"""

import random

# Klawisze obok siebie na klawiaturze QWERTY - typowe pomyłki przy pisaniu na telefonie.
_SASIEDZI = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh", "u": "yij", "i": "uok",
    "o": "ipl", "p": "ol", "a": "qsz", "s": "adwz", "d": "sfe", "f": "dgr", "g": "fht", "h": "gjy",
    "j": "hku", "k": "jli", "l": "kp", "z": "asx", "x": "zc", "c": "xv", "v": "cb", "b": "vn",
    "n": "bm", "m": "n",
}
PRZED = ["słuchaj, ", "a ", "no ", "badku, ", "ej, ", "powiedz mi, "]
PO = [" proszę", " badku", " :)", "?", "!", " no"]


def literowka(slowo, los):
    """Jedna literówka w środku słowa (pierwsza litera zwykle jest dobra)."""
    if len(slowo) < 4:
        return slowo
    i = los.randrange(1, len(slowo) - 1)
    rodzaj = los.randrange(4)
    if rodzaj == 0:                      # zamiana sąsiednich liter
        return slowo[:i] + slowo[i + 1] + slowo[i] + slowo[i + 2:]
    if rodzaj == 1:                      # pominięta litera
        return slowo[:i] + slowo[i + 1:]
    if rodzaj == 2:                      # podwojona litera
        return slowo[:i] + slowo[i] + slowo[i:]
    sasiad = _SASIEDZI.get(slowo[i].lower())  # sąsiedni klawisz
    return slowo[:i] + los.choice(sasiad) + slowo[i + 1:] if sasiad else slowo


def wariant(zdanie, los):
    slowa = zdanie.split()
    zmiana = los.random()
    if zmiana < 0.6:
        dlugie = [i for i, s in enumerate(slowa) if len(s) >= 4]
        if dlugie:
            i = los.choice(dlugie)
            slowa[i] = literowka(slowa[i], los)
    if zmiana > 0.4:
        if los.random() < 0.5:
            slowa = PRZED[los.randrange(len(PRZED))].split() + slowa
        else:
            slowa[-1] += PO[los.randrange(len(PO))]
    return " ".join(slowa)


def warianty(zdanie, ile, ziarno=0):
    """Do `ile` różnych wariantów zdania (bez oryginału). Zawsze te same dla tego samego ziarna."""
    los = random.Random(f"{ziarno}:{zdanie}")
    wynik = []
    for _ in range(ile * 4):
        w = wariant(zdanie, los)
        if w.lower() != zdanie.lower() and w not in wynik:
            wynik.append(w)
        if len(wynik) == ile:
            break
    return wynik
