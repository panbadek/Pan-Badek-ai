"""Mostek między aplikacją w przeglądarce (web/) a mózgiem Pana Badka.

Strona uruchamia Pythona w przeglądarce (Pyodide) w Web Workerze i woła te funkcje.
Wyniki zwracamy jako JSON, żeby po stronie JavaScriptu nie trzeba było
konwertować obiektów Pythona.
"""

import json

from .brain import PanBadek
from .obrazy import Obraz

_badek = None


def start(katalog_pamieci):
    global _badek
    _badek = PanBadek(katalog_pamieci=katalog_pamieci)
    _badek.pliki_lokalne = False  # w przeglądarce nie ma dysku do przeglądania
    return json.dumps({"imie": _badek.imie})


def czat(tekst):
    odpowiedz = _badek.odpowiedz(tekst)
    return json.dumps({"odpowiedz": odpowiedz, "zrodlo": _badek.zrodlo, "imie": _badek.imie},
                      ensure_ascii=False)


def _bajty(dane):
    """Uint8Array z JavaScriptu przychodzi jako JsProxy - zamieniamy go na bytes."""
    if hasattr(dane, "to_py"):
        dane = dane.to_py()
    return bytes(dane or b"")


def zdjecie(szer, wys, oryg_szer, oryg_wys, piksele, naglowek):
    obraz = Obraz(int(szer), int(wys), _bajty(piksele), int(oryg_szer), int(oryg_wys))
    return json.dumps({"odpowiedz": _badek.analizuj_zdjecie(obraz, _bajty(naglowek))},
                      ensure_ascii=False)
