"""Mierzy, jak dobrze sieć neuronowa Pana Badka rozpoznaje intencje na zdaniach,
których nie widziała przy treningu: python3 narzedzia/ocen_siec.py"""

import json
import os
import sys
import tempfile
import time

KORZEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KORZEN)

from panbadek import PanBadek  # noqa: E402


def ocen(badek=None, pokaz_bledy=True):
    with open(os.path.join(KORZEN, "panbadek", "data", "test_intencje.json"), encoding="utf-8") as f:
        testy = json.load(f)["testy"]
    dobre, bledy = 0, []
    for t in testy:
        nazwa = badek.rozpoznaj_intencje(t["tekst"])
        # "inne" oznacza: sieć ma NIE odpowiadać (oddać pytanie wiedzy, internetowi lub AI).
        if (nazwa or "inne") == t["oczekiwana"]:
            dobre += 1
        else:
            bledy.append((t["tekst"], t["oczekiwana"], nazwa))
    if pokaz_bledy:
        for tekst, oczekiwana, wynik in bledy:
            print(f"  ✗ {tekst!r}: oczekiwano {oczekiwana}, jest {wynik}")
    return dobre / len(testy), bledy


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as katalog:
        start = time.time()
        badek = PanBadek(katalog_pamieci=katalog, internet=False, ziarno=0)
        print(f"Trening: {time.time() - start:.1f} s, przykładów: "
              f"{sum(len(p) for p in badek.przyklady_treningowe().values())}")
        dokladnosc, _ = ocen(badek)
        print(f"Dokładność na zdaniach testowych: {dokladnosc:.1%}")
