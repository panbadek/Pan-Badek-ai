"""Czytanie metadanych EXIF ze zdjęć JPEG (data, aparat, miejsce) w czystym Pythonie."""

import struct

# Rozmiary typów danych EXIF w bajtach.
_ROZMIARY = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}


def _segment_exif(dane):
    """Wyszukuje w JPEG segment APP1 z EXIF-em. Zwraca bajty TIFF albo None."""
    if not dane.startswith(b"\xff\xd8"):
        return None
    pos = 2
    while pos + 4 <= len(dane):
        if dane[pos] != 0xFF:
            return None
        znacznik = dane[pos + 1]
        if znacznik in (0xD9, 0xDA):  # koniec obrazu albo początek danych - EXIF-u już nie będzie
            return None
        dlugosc = struct.unpack(">H", dane[pos + 2:pos + 4])[0]
        tresc = dane[pos + 4:pos + 2 + dlugosc]
        if znacznik == 0xE1 and tresc.startswith(b"Exif\0\0"):
            return tresc[6:]
        pos += 2 + dlugosc
    return None


def _czytaj_ifd(tiff, przesuniecie, kolejnosc):
    """Czyta katalog znaczników. Zwraca {znacznik: wartość}."""
    wynik = {}
    if przesuniecie + 2 > len(tiff):
        return wynik
    ile = struct.unpack(kolejnosc + "H", tiff[przesuniecie:przesuniecie + 2])[0]
    for n in range(ile):
        wpis = przesuniecie + 2 + n * 12
        if wpis + 12 > len(tiff):
            break
        znacznik, typ, liczba = struct.unpack(kolejnosc + "HHI", tiff[wpis:wpis + 8])
        rozmiar = _ROZMIARY.get(typ, 1) * liczba
        if rozmiar <= 4:
            surowe = tiff[wpis + 8:wpis + 8 + rozmiar]
        else:
            adres = struct.unpack(kolejnosc + "I", tiff[wpis + 8:wpis + 12])[0]
            surowe = tiff[adres:adres + rozmiar]
        if len(surowe) < rozmiar:
            continue
        if typ == 2:
            wartosc = surowe.split(b"\0", 1)[0].decode("utf-8", "replace").strip()
        elif typ == 3:
            wartosc = struct.unpack(kolejnosc + "H" * liczba, surowe)
        elif typ in (4, 9):
            wartosc = struct.unpack(kolejnosc + ("I" if typ == 4 else "i") * liczba, surowe)
        elif typ in (5, 10):
            liczby = struct.unpack(kolejnosc + ("I" if typ == 5 else "i") * 2 * liczba, surowe)
            wartosc = tuple(liczby[i] / liczby[i + 1] if liczby[i + 1] else 0.0
                            for i in range(0, len(liczby), 2))
        else:
            wartosc = surowe
        wynik[znacznik] = wartosc
    return wynik


def _stopnie(wartosci, kierunek):
    if not wartosci or len(wartosci) < 3:
        return None
    stopnie = wartosci[0] + wartosci[1] / 60 + wartosci[2] / 3600
    return -stopnie if kierunek in ("S", "W") else stopnie


def czytaj(dane):
    """Zwraca słownik z kluczami: data, aparat, szerokosc_geo, dlugosc_geo (te, które są)."""
    tiff = _segment_exif(dane or b"")
    if not tiff or len(tiff) < 8:
        return {}
    kolejnosc = {b"II": "<", b"MM": ">"}.get(tiff[:2])
    if not kolejnosc:
        return {}
    try:
        ifd0 = _czytaj_ifd(tiff, struct.unpack(kolejnosc + "I", tiff[4:8])[0], kolejnosc)
        wynik = {}
        marka, model = ifd0.get(0x010F, ""), ifd0.get(0x0110, "")
        if isinstance(model, str) and model:
            wynik["aparat"] = model if isinstance(marka, str) and model.startswith(marka) \
                else f"{marka} {model}".strip()
        if 0x8769 in ifd0:
            exif = _czytaj_ifd(tiff, ifd0[0x8769][0], kolejnosc)
            data = exif.get(0x9003) or ifd0.get(0x0132)
            if isinstance(data, str) and len(data) >= 16:
                dzien, godzina = data[:10].replace(":", "-"), data[11:16]
                wynik["data"] = f"{dzien} {godzina}"
        if 0x8825 in ifd0:
            gps = _czytaj_ifd(tiff, ifd0[0x8825][0], kolejnosc)
            szer = _stopnie(gps.get(2), gps.get(1))
            dl = _stopnie(gps.get(4), gps.get(3))
            if szer is not None and dl is not None and (szer or dl):
                wynik["szerokosc_geo"], wynik["dlugosc_geo"] = round(szer, 5), round(dl, 5)
        return wynik
    except (struct.error, IndexError, TypeError):
        return {}


def opisz(metadane):
    """Linijka opisu metadanych po polsku albo pusty napis."""
    czesci = []
    if "data" in metadane:
        czesci.append(f"zrobione {metadane['data']}")
    if "aparat" in metadane:
        czesci.append(f"aparat: {metadane['aparat']}")
    if "szerokosc_geo" in metadane:
        szer, dl = metadane["szerokosc_geo"], metadane["dlugosc_geo"]
        czesci.append(f"miejsce: {szer}, {dl} "
                      f"(https://www.openstreetmap.org/?mlat={szer}&mlon={dl}#map=15/{szer}/{dl})")
    return ("🗓️ " + "; ".join(czesci) + ".") if czesci else ""
