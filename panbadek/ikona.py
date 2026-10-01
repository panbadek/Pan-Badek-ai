"""Ikona Pana Badka rysowana w kodzie i zapisywana jako PNG (bez bibliotek graficznych)."""

import functools
import struct
import zlib

TLO = (47, 111, 237)
BIALY = (255, 255, 255)
GRANAT = (29, 35, 48)


def _w_prostokacie(x, y, x1, y1, x2, y2, r):
    """Czy punkt leży w prostokącie o zaokrąglonych rogach (r - promień)."""
    if not (x1 <= x <= x2 and y1 <= y <= y2):
        return False
    dx = max(x1 + r - x, 0, x - (x2 - r))
    dy = max(y1 + r - y, 0, y - (y2 - r))
    return dx * dx + dy * dy <= r * r


def _w_kole(x, y, sx, sy, r):
    return (x - sx) ** 2 + (y - sy) ** 2 <= r * r


def _kolor(x, y):
    """Kolor w punkcie (x, y) z zakresu 0..1. Rysunek mieści się w bezpiecznej strefie ikon."""
    if _w_kole(x, y, 0.40, 0.50, 0.055) or _w_kole(x, y, 0.60, 0.50, 0.055):
        return GRANAT  # oczy
    if _w_prostokacie(x, y, 0.40, 0.595, 0.60, 0.64, 0.02):
        return GRANAT  # uśmiech
    if (_w_prostokacie(x, y, 0.27, 0.33, 0.73, 0.72, 0.09)  # głowa
            or _w_prostokacie(x, y, 0.485, 0.22, 0.515, 0.34, 0.0)  # antena
            or _w_kole(x, y, 0.50, 0.21, 0.045)
            or _w_prostokacie(x, y, 0.22, 0.45, 0.28, 0.60, 0.02)  # uszy
            or _w_prostokacie(x, y, 0.72, 0.45, 0.78, 0.60, 0.02)):
        return BIALY
    return TLO


@functools.lru_cache(maxsize=16)
def png(rozmiar, przezroczyste_tlo=False, skala=1.0):
    """Zwraca bajty pliku PNG z ikoną o boku `rozmiar` pikseli (wygładzanie 2x2).

    Z przezroczystym tłem powstaje sam robot - np. warstwa ikony adaptacyjnej Androida.
    `skala` < 1 pomniejsza robota względem środka (np. żeby zmieścił się w okrągłej masce).
    """
    probki = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
    kanaly = 4 if przezroczyste_tlo else 3
    wiersze = bytearray()
    for py in range(rozmiar):
        wiersze.append(0)  # filtr PNG: brak
        for px in range(rozmiar):
            kolory = [_kolor(0.5 + ((px + ox) / rozmiar - 0.5) / skala,
                             0.5 + ((py + oy) / rozmiar - 0.5) / skala) for ox, oy in probki]
            if przezroczyste_tlo:
                kolory = [k for k in kolory if k is not TLO]
                if not kolory:
                    wiersze.extend(b"\0\0\0\0")
                    continue
                for kanal in range(3):
                    wiersze.append(sum(k[kanal] for k in kolory) // len(kolory))
                wiersze.append(255 * len(kolory) // len(probki))
            else:
                for kanal in range(3):
                    wiersze.append(sum(k[kanal] for k in kolory) // len(probki))

    def blok(typ, dane):
        return (struct.pack(">I", len(dane)) + typ + dane
                + struct.pack(">I", zlib.crc32(typ + dane) & 0xFFFFFFFF))

    typ_koloru = 6 if przezroczyste_tlo else 2  # RGBA albo RGB, po 8 bitów
    naglowek = struct.pack(">IIBBBBB", rozmiar, rozmiar, 8, typ_koloru, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + blok(b"IHDR", naglowek)
            + blok(b"IDAT", zlib.compress(bytes(wiersze), 9)) + blok(b"IEND", b""))


def ico(rozmiar=256):
    """Plik .ico dla Windows - od Visty może po prostu zawierać obraz PNG."""
    dane = png(rozmiar)
    bok = 0 if rozmiar >= 256 else rozmiar  # 0 oznacza 256 pikseli
    return (struct.pack("<HHH", 0, 1, 1)
            + struct.pack("<BBBBHHII", bok, bok, 0, 0, 1, 32, len(dane), 6 + 16) + dane)


def zapisz(sciezka, rozmiar=256, przezroczyste_tlo=False, skala=1.0):
    with open(sciezka, "wb") as f:
        f.write(png(rozmiar, przezroczyste_tlo, skala))
    return sciezka
