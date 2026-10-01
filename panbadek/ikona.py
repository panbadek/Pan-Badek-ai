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


@functools.lru_cache(maxsize=8)
def png(rozmiar):
    """Zwraca bajty pliku PNG z ikoną o boku `rozmiar` pikseli (wygładzanie 2x2)."""
    probki = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
    wiersze = bytearray()
    for py in range(rozmiar):
        wiersze.append(0)  # filtr PNG: brak
        for px in range(rozmiar):
            kolory = [_kolor((px + ox) / rozmiar, (py + oy) / rozmiar) for ox, oy in probki]
            for kanal in range(3):
                wiersze.append(sum(k[kanal] for k in kolory) // 4)

    def blok(typ, dane):
        return (struct.pack(">I", len(dane)) + typ + dane
                + struct.pack(">I", zlib.crc32(typ + dane) & 0xFFFFFFFF))

    naglowek = struct.pack(">IIBBBBB", rozmiar, rozmiar, 8, 2, 0, 0, 0)  # 8 bitów, RGB
    return (b"\x89PNG\r\n\x1a\n" + blok(b"IHDR", naglowek)
            + blok(b"IDAT", zlib.compress(bytes(wiersze), 9)) + blok(b"IEND", b""))


def ico(rozmiar=256):
    """Plik .ico dla Windows - od Visty może po prostu zawierać obraz PNG."""
    dane = png(rozmiar)
    bok = 0 if rozmiar >= 256 else rozmiar  # 0 oznacza 256 pikseli
    return (struct.pack("<HHH", 0, 1, 1)
            + struct.pack("<BBBBHHII", bok, bok, 0, 0, 1, 32, len(dane), 6 + 16) + dane)


def zapisz(sciezka, rozmiar=256):
    with open(sciezka, "wb") as f:
        f.write(png(rozmiar))
    return sciezka
