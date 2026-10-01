"""Testy analizy zdjęć: dekoder PNG, EXIF, kolory, sceny, ostrość i rozpoznawanie."""

import base64
import json
import os
import struct
import tempfile
import threading
import unittest
import urllib.request
import zlib

from panbadek import PanBadek, exif, ikona, obrazy
from panbadek.obrazy import Obraz
from panbadek.web import stworz_serwer


def obraz_z_funkcji(szer, wys, kolor):
    """Obraz, w którym kolor piksela (x, y) wylicza funkcja."""
    return Obraz(szer, wys, bytes(c for y in range(wys) for x in range(szer) for c in kolor(x, y)))


def scena(gora, dol, szer=120, wys=80):
    return obraz_z_funkcji(szer, wys, lambda x, y: gora if y < wys // 2 else dol)


def png_z_filtrami(szer, wys, kolor, kanaly=3, typ_koloru=2, paleta=None):
    """Koduje PNG, używając po kolei wszystkich pięciu filtrów wierszy."""
    bpp = kanaly
    surowe, poprzedni = bytearray(), bytearray(szer * bpp)
    for y in range(wys):
        wiersz = bytearray(v for x in range(szer) for v in kolor(x, y))
        filtr = y % 5
        zakodowany = bytearray()
        for i, v in enumerate(wiersz):
            lewy = wiersz[i - bpp] if i >= bpp else 0
            gora = poprzedni[i]
            gl = poprzedni[i - bpp] if i >= bpp else 0
            przewidywanie = [0, lewy, gora, (lewy + gora) >> 1, obrazy._paeth(lewy, gora, gl)][filtr]
            zakodowany.append((v - przewidywanie) & 0xFF)
        surowe += bytes([filtr]) + zakodowany
        poprzedni = wiersz

    def blok(typ, dane):
        return struct.pack(">I", len(dane)) + typ + dane + struct.pack(">I", zlib.crc32(typ + dane))

    wynik = b"\x89PNG\r\n\x1a\n" + blok(b"IHDR", struct.pack(">IIBBBBB", szer, wys, 8, typ_koloru, 0, 0, 0))
    if paleta:
        wynik += blok(b"PLTE", paleta)
    return wynik + blok(b"IDAT", zlib.compress(bytes(surowe))) + blok(b"IEND", b"")


def jpeg_z_exif(model="Pixel 8", marka="Google", data="2024:07:14 18:03:22",
                gps=((50, 3, 41.0), "N", (19, 56, 24.0), "E")):
    """Minimalny 'JPEG' z segmentem EXIF (do czytania metadanych obraz nie jest potrzebny)."""
    wpisy_ifd0, dane_dodatkowe = [], bytearray()
    poczatek_danych = 8 + 2 + 5 * 12 + 4  # nagłówek TIFF + IFD0 z 5 wpisami

    def tekst(znacznik, wartosc):
        b = wartosc.encode() + b"\0"
        wpisy_ifd0.append((znacznik, 2, len(b), poczatek_danych + len(dane_dodatkowe)))
        dane_dodatkowe.extend(b)

    tekst(0x010F, marka)
    tekst(0x0110, model)
    exif_ifd = poczatek_danych + len(dane_dodatkowe)
    b_data = data.encode() + b"\0"
    adres_daty = exif_ifd + 2 + 12 + 4
    dane_dodatkowe.extend(struct.pack("<HHHII", 1, 0x9003, 2, len(b_data), adres_daty) + b"\0" * 4 + b_data)
    wpisy_ifd0.append((0x8769, 4, 1, exif_ifd))
    gps_ifd = poczatek_danych + len(dane_dodatkowe)
    wartosci = gps_ifd + 2 + 4 * 12 + 4

    def wymierne(trojka):
        return b"".join(struct.pack("<II", int(v * 100), 100) for v in trojka)

    gps_wpisy = struct.pack("<H", 4)
    gps_wpisy += struct.pack("<HHI4s", 1, 2, 2, gps[1].encode() + b"\0\0\0")
    gps_wpisy += struct.pack("<HHII", 2, 5, 3, wartosci)
    gps_wpisy += struct.pack("<HHI4s", 3, 2, 2, gps[3].encode() + b"\0\0\0")
    gps_wpisy += struct.pack("<HHII", 4, 5, 3, wartosci + 24)
    dane_dodatkowe.extend(gps_wpisy + b"\0" * 4 + wymierne(gps[0]) + wymierne(gps[2]))
    wpisy_ifd0.append((0x8825, 4, 1, gps_ifd))
    wpisy_ifd0.append((0x0112, 3, 1, 1))

    tiff = b"II*\0" + struct.pack("<I", 8) + struct.pack("<H", len(wpisy_ifd0))
    for znacznik, typ, liczba, wartosc in wpisy_ifd0:
        tiff += struct.pack("<HHII", znacznik, typ, liczba, wartosc)
    tiff += b"\0" * 4 + bytes(dane_dodatkowe)
    app1 = b"Exif\0\0" + tiff
    return b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xda"


class TestPNG(unittest.TestCase):
    def test_wszystkie_filtry_rgb(self):
        kolor = lambda x, y: ((x * 37) % 256, (y * 53) % 256, (x * y) % 256)  # noqa: E731
        obraz = obrazy.wczytaj_png(png_z_filtrami(13, 11, kolor))
        self.assertEqual((obraz.szer, obraz.wys), (13, 11))
        for x, y in [(0, 0), (12, 10), (5, 7), (3, 4)]:
            self.assertEqual(obraz.piksel(x, y), kolor(x, y))

    def test_rgba_i_paleta(self):
        obraz = obrazy.wczytaj_png(ikona.png(20, przezroczyste_tlo=True))
        self.assertEqual(obraz.szer, 20)
        paleta = bytes([255, 0, 0, 0, 0, 255])
        obraz = obrazy.wczytaj_png(png_z_filtrami(4, 4, lambda x, y: (x % 2,), kanaly=1,
                                                  typ_koloru=3, paleta=paleta))
        self.assertEqual(obraz.piksel(0, 0), (255, 0, 0))
        self.assertEqual(obraz.piksel(1, 3), (0, 0, 255))

    def test_odrzuca_nie_png(self):
        with self.assertRaises(ValueError):
            obrazy.wczytaj_png(b"GIF89a")


class TestEXIF(unittest.TestCase):
    def test_czyta_metadane(self):
        dane = exif.czytaj(jpeg_z_exif())
        self.assertEqual(dane["aparat"], "Google Pixel 8")
        self.assertEqual(dane["data"], "2024-07-14 18:03")
        self.assertAlmostEqual(dane["szerokosc_geo"], 50.06139, places=4)
        self.assertAlmostEqual(dane["dlugosc_geo"], 19.94, places=4)
        self.assertIn("openstreetmap.org", exif.opisz(dane))

    def test_poludnie_i_zachod(self):
        dane = exif.czytaj(jpeg_z_exif(gps=((33, 52, 0.0), "S", (151, 12, 0.0), "W")))
        self.assertLess(dane["szerokosc_geo"], 0)
        self.assertLess(dane["dlugosc_geo"], 0)

    def test_bez_exif(self):
        self.assertEqual(exif.czytaj(b"\xff\xd8\xff\xda"), {})
        self.assertEqual(exif.czytaj(b"nie jpeg"), {})
        self.assertEqual(exif.czytaj(b""), {})


class TestAnaliza(unittest.TestCase):
    def test_nazwy_kolorow(self):
        oczekiwane = {(220, 30, 30): "czerwony", (30, 80, 220): "niebieski", (250, 250, 250): "biały",
                      (5, 5, 5): "czarny", (40, 170, 60): "zielony", (120, 70, 30): "brązowy",
                      (240, 220, 40): "żółty", (128, 128, 128): "szary"}
        for rgb, nazwa in oczekiwane.items():
            self.assertEqual(obrazy.nazwa_koloru(*rgb), nazwa, rgb)

    def test_niebo_i_trawa(self):
        a = obrazy.analizuj(scena((70, 140, 230), (50, 160, 60)))
        domysly = " ".join(obrazy.zgadnij_scene(a))
        self.assertIn("niebo", domysly)
        self.assertIn("zieleni", domysly)
        nazwy = [n for n, _ in a["kolory"]]
        self.assertEqual(set(nazwy[:2]), {"niebieski", "zielony"})

    def test_noc(self):
        swiatla = lambda x, y: (255, 240, 200) if x % 10 < 2 and y % 10 < 2 else (10, 10, 25)  # noqa
        a = obrazy.analizuj(obraz_z_funkcji(100, 100, swiatla))
        self.assertIn("nocne", " ".join(obrazy.zgadnij_scene(a)))

    def test_ostrosc(self):
        szachownica = obraz_z_funkcji(64, 64, lambda x, y: (255,) * 3 if (x // 4 + y // 4) % 2 else (0,) * 3)
        gradient = obraz_z_funkcji(64, 64, lambda x, y: (x * 4,) * 3)
        self.assertIn("ostre", obrazy.opisz(obrazy.analizuj(szachownica)))
        self.assertIn("rozmyte", obrazy.opisz(obrazy.analizuj(gradient)))

    def test_opis(self):
        opis = obrazy.opisz(obrazy.analizuj(scena((70, 140, 230), (50, 160, 60), 300, 200)))
        self.assertIn("300×200", opis)
        self.assertIn("poziome", opis)

    def test_pomniejszanie(self):
        duzy = scena((255, 0, 0), (0, 0, 255), 1000, 600).pomniejsz(100)
        self.assertEqual((duzy.szer, duzy.wys), (100, 60))
        self.assertEqual((duzy.oryg_szer, duzy.oryg_wys), (1000, 600))
        self.assertEqual(duzy.piksel(50, 5), (255, 0, 0))

    def test_rozpoznawanie(self):
        niebo = obrazy.cechy(scena((70, 140, 230), (50, 160, 60)))
        podobne = obrazy.cechy(scena((80, 150, 235), (45, 150, 55), 90, 60))
        inne = obrazy.cechy(scena((200, 40, 40), (250, 230, 60)))
        przyklady = [{"etykieta": "łąka", "cechy": niebo}]
        self.assertEqual(obrazy.rozpoznaj(podobne, przyklady)[0], "łąka")
        self.assertIsNone(obrazy.rozpoznaj(inne, przyklady))


class TestPanBadekZdjecia(unittest.TestCase):
    def setUp(self):
        self.katalog = tempfile.TemporaryDirectory()
        self.addCleanup(self.katalog.cleanup)
        self.badek = PanBadek(katalog_pamieci=self.katalog.name, ziarno=0, internet=False)

    def test_uczy_sie_rozpoznawac(self):
        odp = self.badek.analizuj_zdjecie(scena((70, 140, 230), (50, 160, 60)))
        self.assertIn("to jest …", odp)
        self.assertIn("Zapamiętałem: to jest łąka", self.badek.odpowiedz("to jest łąka"))
        # Po innej wiadomości "to jest ..." nie dotyczy już zdjęcia.
        self.badek.odpowiedz("cześć")
        self.assertNotIn("Zapamiętałem", self.badek.odpowiedz("to jest kot"))

        nowy = PanBadek(katalog_pamieci=self.katalog.name, ziarno=0, internet=False)
        odp = nowy.analizuj_zdjecie(scena((80, 150, 235), (45, 150, 55)))
        self.assertIn("Przypomina mi: łąka", odp)
        self.assertNotIn("Przypomina", nowy.analizuj_zdjecie(scena((200, 40, 40), (250, 230, 60))))
        self.assertIn("łąka (1)", nowy.odpowiedz("jakie zdjęcia znasz?"))

    def test_metadane(self):
        odp = self.badek.analizuj_zdjecie(scena((70, 140, 230), (50, 160, 60)), jpeg_z_exif())
        self.assertIn("Google Pixel 8", odp)
        self.assertIn("2024-07-14", odp)

    def test_zdjecie_z_pliku(self):
        sciezka = os.path.join(self.katalog.name, "test.png")
        with open(sciezka, "wb") as f:
            f.write(png_z_filtrami(40, 30, lambda x, y: (70, 140, 230) if y < 15 else (50, 160, 60)))
        self.assertIn("40×30", self.badek.odpowiedz(f"przeanalizuj zdjęcie {sciezka}"))
        self.badek.pliki_lokalne = False
        self.assertNotIn("40×30", self.badek.odpowiedz(f"przeanalizuj zdjęcie {sciezka}"))

    def test_podpowiedz_bez_zdjecia(self):
        self.badek.pliki_lokalne = False
        self.assertIn("📷", self.badek.odpowiedz("czy możesz przeanalizować zdjęcie?"))


class TestWebZdjecia(unittest.TestCase):
    def test_api_zdjecie(self):
        badek = PanBadek(katalog_pamieci=None, ziarno=0, internet=False)
        serwer = stworz_serwer(badek, port=0)
        threading.Thread(target=serwer.serve_forever, daemon=True).start()
        self.addCleanup(serwer.server_close)
        self.addCleanup(serwer.shutdown)
        obraz = scena((70, 140, 230), (50, 160, 60), 64, 48)
        cialo = json.dumps({"szer": 64, "wys": 48, "oryg_szer": 4032, "oryg_wys": 3024,
                            "piksele": base64.b64encode(obraz.piksele).decode(),
                            "naglowek": base64.b64encode(jpeg_z_exif()).decode()}).encode()
        bez_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        adres = f"http://127.0.0.1:{serwer.server_address[1]}/api/zdjecie"
        with bez_proxy.open(urllib.request.Request(adres, data=cialo)) as odp:
            tekst = json.load(odp)["odpowiedz"]
        self.assertIn("4032×3024", tekst)
        self.assertIn("Pixel 8", tekst)
        zle = json.dumps({"szer": 10, "wys": 10, "piksele": "AAAA"}).encode()
        with self.assertRaises(urllib.error.HTTPError) as blad:
            bez_proxy.open(urllib.request.Request(adres, data=zle))
        self.assertEqual(blad.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
