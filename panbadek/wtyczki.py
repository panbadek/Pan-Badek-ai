"""Wtyczki: własne umiejętności Pana Badka pisane w Pythonie.

Wtyczka to plik .py w katalogu ``wtyczki`` w pamięci Pana Badka, z funkcją
``obsluz(tekst, badek)``, która zwraca odpowiedź (str) albo None, gdy
wiadomość jej nie dotyczy. Wtyczki to zwykły kod Pythona uruchamiany na
twoim komputerze - wrzucaj tam tylko pliki, którym ufasz.
"""

import importlib.util
import os
import re

from .text import normalizuj

SZABLON = '''"""Wtyczka Pana Badka: {nazwa}

Edytuj funkcję obsluz(), zapisz plik i uruchom Pana Badka ponownie
(albo napisz mu "przeładuj wtyczki").
"""


def obsluz(tekst, badek):
    """Zwróć odpowiedź (str), jeśli wiadomość dotyczy tej wtyczki, w przeciwnym razie None.

    tekst  - wiadomość od użytkownika
    badek  - obiekt PanBadek (np. badek.imie, badek.biblioteki)
    """
    if "{nazwa}" in tekst.lower():
        return "Tu wtyczka {nazwa}! Zmień mnie w pliku " + __file__
    return None
'''


def _nazwa_pliku(nazwa):
    nazwa = re.sub(r"[^a-z0-9_]+", "_", normalizuj(nazwa).strip())
    return nazwa.strip("_") or "wtyczka"


def stworz(katalog, nazwa):
    """Tworzy szkielet wtyczki. Zwraca ścieżkę do pliku."""
    os.makedirs(katalog, exist_ok=True)
    modul = _nazwa_pliku(nazwa)
    sciezka = os.path.join(katalog, modul + ".py")
    if not os.path.exists(sciezka):
        with open(sciezka, "w", encoding="utf-8") as f:
            f.write(SZABLON.format(nazwa=modul))
    return sciezka


def wczytaj(katalog):
    """Ładuje wszystkie wtyczki z katalogu. Zwraca (lista_wtyczek, lista_bledow)."""
    wtyczki, bledy = [], []
    if not katalog or not os.path.isdir(katalog):
        return wtyczki, bledy
    for plik in sorted(os.listdir(katalog)):
        if not plik.endswith(".py") or plik.startswith("_"):
            continue
        nazwa = plik[:-3]
        try:
            spec = importlib.util.spec_from_file_location(f"panbadek_wtyczka_{nazwa}",
                                                          os.path.join(katalog, plik))
            modul = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modul)
            if callable(getattr(modul, "obsluz", None)):
                wtyczki.append((nazwa, modul.obsluz))
            else:
                bledy.append(f"{plik}: brak funkcji obsluz(tekst, badek)")
        except Exception as e:  # zepsuta wtyczka nie może wyłączyć całego Badka
            bledy.append(f"{plik}: {e}")
    return wtyczki, bledy
