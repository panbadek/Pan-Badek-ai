"""Generuje ikony aplikacji z panbadek/ikona.py: python3 android/generuj_ikony.py"""

import os
import sys

KATALOG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(KATALOG))

from panbadek import ikona  # noqa: E402

# Gęstość ekranu -> (rozmiar zwykłej ikony, rozmiar warstwy ikony adaptacyjnej)
GESTOSCI = {"mdpi": (48, 108), "hdpi": (72, 162), "xhdpi": (96, 216),
            "xxhdpi": (144, 324), "xxxhdpi": (192, 432)}

for gestosc, (zwykla, warstwa) in GESTOSCI.items():
    katalog = os.path.join(KATALOG, "app", "src", "main", "res", f"mipmap-{gestosc}")
    os.makedirs(katalog, exist_ok=True)
    ikona.zapisz(os.path.join(katalog, "ic_launcher.png"), zwykla)
    # Warstwa ma 108dp, ale launcher pokazuje tylko środek przycięty do koła o średnicy
    # ok. 66dp - pomniejszamy robota, żeby antena i uszy się zmieściły.
    ikona.zapisz(os.path.join(katalog, "ic_launcher_foreground.png"), warstwa,
                 przezroczyste_tlo=True, skala=0.72)
    print("ikony:", katalog)
