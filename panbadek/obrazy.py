"""Analiza zdjęć napisana od zera: kolory, jasność, ostrość, zgadywanie sceny i rozpoznawanie.

Obraz to zwykła tablica pikseli RGB. W przeglądarce i w aplikacji zdjęcie dekoduje
i pomniejsza sama przeglądarka (obsługuje JPEG, HEIC itd.), a w terminalu Pan Badek
sam czyta pliki PNG. Jeśli zainstalowana jest biblioteka Pillow, czyta też JPEG.
"""

import colorsys
import math
import random
import struct
import zlib

ROZMIAR_ANALIZY = 256  # dłuższy bok obrazu, na którym liczymy
PROBKA_KOLOROW = 4096  # tyle pikseli trafia do k-średnich


class Obraz:
    """Obraz RGB: szerokość, wysokość i bajty pikseli (po 3 na piksel, wierszami)."""

    def __init__(self, szer, wys, piksele, oryg_szer=None, oryg_wys=None):
        if szer <= 0 or wys <= 0 or len(piksele) != szer * wys * 3:
            raise ValueError("Niepoprawne wymiary obrazu.")
        self.szer, self.wys, self.piksele = szer, wys, bytes(piksele)
        self.oryg_szer = oryg_szer or szer
        self.oryg_wys = oryg_wys or wys

    def piksel(self, x, y):
        i = (y * self.szer + x) * 3
        return self.piksele[i], self.piksele[i + 1], self.piksele[i + 2]

    def pomniejsz(self, maks=ROZMIAR_ANALIZY):
        """Pomniejsza obraz (uśrednianie bloków) tak, żeby dłuższy bok miał co najwyżej `maks`."""
        skala = max(self.szer, self.wys) / maks
        if skala <= 1:
            return self
        nowa_s, nowa_w = max(1, round(self.szer / skala)), max(1, round(self.wys / skala))
        wynik = bytearray()
        for ny in range(nowa_w):
            y0, y1 = ny * self.wys // nowa_w, max(ny * self.wys // nowa_w + 1, (ny + 1) * self.wys // nowa_w)
            for nx in range(nowa_s):
                x0 = nx * self.szer // nowa_s
                x1 = max(x0 + 1, (nx + 1) * self.szer // nowa_s)
                suma, ile = [0, 0, 0], 0
                # Przy dużych zdjęciach bierzemy co któryś piksel bloku - wystarczy do statystyk.
                krok = max(1, (x1 - x0) // 4)
                for y in range(y0, y1, max(1, (y1 - y0) // 4)):
                    for x in range(x0, x1, krok):
                        i = (y * self.szer + x) * 3
                        suma[0] += self.piksele[i]
                        suma[1] += self.piksele[i + 1]
                        suma[2] += self.piksele[i + 2]
                        ile += 1
                wynik.extend(s // ile for s in suma)
        return Obraz(nowa_s, nowa_w, wynik, self.oryg_szer, self.oryg_wys)


# --- czytanie plików ----------------------------------------------------------

def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def wczytaj_png(dane):
    """Dekoder PNG (bez przeplotu) w czystym Pythonie. Zwraca Obraz."""
    if not dane.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("To nie jest plik PNG.")
    pos, idat, paleta, przezr = 8, bytearray(), None, None
    while pos < len(dane):
        dlugosc, typ = struct.unpack(">I4s", dane[pos:pos + 8])
        tresc = dane[pos + 8:pos + 8 + dlugosc]
        if typ == b"IHDR":
            szer, wys, glebia, typ_koloru, _, _, przeplot = struct.unpack(">IIBBBBB", tresc)
        elif typ == b"PLTE":
            paleta = tresc
        elif typ == b"IDAT":
            idat.extend(tresc)
        elif typ == b"IEND":
            break
        pos += 12 + dlugosc
    if przeplot:
        raise ValueError("Pliki PNG z przeplotem nie są obsługiwane - zapisz obraz bez przeplotu.")
    kanaly = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[typ_koloru]
    if glebia not in (8, 16) and not (typ_koloru == 3 and glebia == 8):
        raise ValueError(f"Nieobsługiwana głębia kolorów: {glebia} bitów.")
    bpp = kanaly * glebia // 8
    wiersz = szer * bpp
    surowe = zlib.decompress(bytes(idat))
    poprzedni = bytearray(wiersz)
    wynik = bytearray()
    for y in range(wys):
        filtr = surowe[y * (wiersz + 1)]
        biezacy = bytearray(surowe[y * (wiersz + 1) + 1:(y + 1) * (wiersz + 1)])
        if filtr == 1:
            for i in range(bpp, wiersz):
                biezacy[i] = (biezacy[i] + biezacy[i - bpp]) & 0xFF
        elif filtr == 2:
            for i in range(wiersz):
                biezacy[i] = (biezacy[i] + poprzedni[i]) & 0xFF
        elif filtr == 3:
            for i in range(wiersz):
                lewy = biezacy[i - bpp] if i >= bpp else 0
                biezacy[i] = (biezacy[i] + ((lewy + poprzedni[i]) >> 1)) & 0xFF
        elif filtr == 4:
            for i in range(wiersz):
                lewy = biezacy[i - bpp] if i >= bpp else 0
                gorny_lewy = poprzedni[i - bpp] if i >= bpp else 0
                biezacy[i] = (biezacy[i] + _paeth(lewy, poprzedni[i], gorny_lewy)) & 0xFF
        krok = glebia // 8  # przy 16 bitach bierzemy starszy bajt
        for x in range(szer):
            p = biezacy[x * bpp:(x + 1) * bpp:krok]
            if typ_koloru == 3:
                i = p[0] * 3
                p = paleta[i:i + 3]
            elif kanaly <= 2:
                p = (p[0], p[0], p[0])
            wynik.extend(p[:3])
        poprzedni = biezacy
    return Obraz(szer, wys, wynik)


def wczytaj_plik(sciezka):
    """Czyta PNG samodzielnie, inne formaty przez Pillow (jeśli jest zainstalowany)."""
    with open(sciezka, "rb") as f:
        dane = f.read()
    if dane.startswith(b"\x89PNG"):
        return wczytaj_png(dane).pomniejsz(), dane[:0]
    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise ValueError("Ten format umiem czytać tylko z pomocą Pillow (pip install pillow). "
                         "Zdjęcia JPEG możesz też wysłać w czacie w przeglądarce (przycisk 📷).")
    import io
    with Image.open(io.BytesIO(dane)) as zdjecie:
        oryg = zdjecie.size
        zdjecie = ImageOps.exif_transpose(zdjecie).convert("RGB")
        zdjecie.thumbnail((ROZMIAR_ANALIZY, ROZMIAR_ANALIZY))
        obraz = Obraz(zdjecie.width, zdjecie.height, zdjecie.tobytes(), *oryg)
    return obraz, dane[:256 * 1024]


# --- kolory -------------------------------------------------------------------

def nazwa_koloru(r, g, b):
    """Polska nazwa koloru na podstawie odcienia, nasycenia i jasności."""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h *= 360
    if v < 0.16:
        return "czarny"
    if s < 0.14 or (s < 0.22 and v < 0.35):
        if v > 0.88:
            return "biały"
        return "jasnoszary" if v > 0.62 else "szary" if v > 0.35 else "ciemnoszary"
    if 15 <= h < 55 and s < 0.4 and v > 0.7:
        return "beżowy"
    if h < 12 or h >= 345:
        if s < 0.5 and v > 0.7:
            return "różowy"
        return "bordowy" if v < 0.45 else "czerwony"
    if h < 42:
        return "brązowy" if v < 0.62 else "pomarańczowy"
    if h < 68:
        return "oliwkowy" if v < 0.5 else "żółty"
    if h < 160:
        return "ciemnozielony" if v < 0.38 else "zielony"
    if h < 195:
        return "turkusowy"
    if h < 255:
        if v < 0.42:
            return "granatowy"
        return "błękitny" if s < 0.5 and v > 0.7 else "niebieski"
    if h < 290:
        return "fioletowy"
    return "purpurowy" if v < 0.5 else "różowy"


def k_srednie(piksele, k=6, iteracje=10, ziarno=0):
    """Grupuje kolory metodą k-średnich (z inicjalizacją k-means++). Zwraca [(kolor, udział)]."""
    los = random.Random(ziarno)
    srodki = [los.choice(piksele)]
    while len(srodki) < k:
        odl = [min((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2 for c in srodki)
               for p in piksele]
        suma = sum(odl)
        if suma == 0:
            break
        cel, akumulacja = los.random() * suma, 0
        for p, d in zip(piksele, odl):
            akumulacja += d
            if akumulacja >= cel:
                srodki.append(p)
                break
    for _ in range(iteracje):
        grupy = [[] for _ in srodki]
        for p in piksele:
            najblizszy = min(range(len(srodki)), key=lambda i: (p[0] - srodki[i][0]) ** 2
                             + (p[1] - srodki[i][1]) ** 2 + (p[2] - srodki[i][2]) ** 2)
            grupy[najblizszy].append(p)
        nowe = [tuple(sum(c[i] for c in g) / len(g) for i in range(3)) if g else s
                for g, s in zip(grupy, srodki)]
        if nowe == srodki:
            break
        srodki = nowe
    return sorted(((s, len(g) / len(piksele)) for s, g in zip(srodki, grupy) if g),
                  key=lambda x: -x[1])


# --- analiza --------------------------------------------------------------------

def _hsv(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h * 360, s, v


def _skora(r, g, b):
    """Klasyczna reguła koloru skóry w przestrzeni YCbCr."""
    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
    return 80 <= cb <= 125 and 138 <= cr <= 170 and r > g > b and r > 90


def analizuj(obraz):
    """Liczy statystyki obrazu. Zwraca słownik z wynikami."""
    obraz = obraz.pomniejsz()
    s, w = obraz.szer, obraz.wys
    pix = [obraz.piksele[i:i + 3] for i in range(0, len(obraz.piksele), 3)]
    jasnosci = [(0.299 * r + 0.587 * g + 0.114 * b) / 255 for r, g, b in pix]
    n = len(pix)

    srednia = sum(jasnosci) / n
    kontrast = math.sqrt(sum((j - srednia) ** 2 for j in jasnosci) / n)
    hsv = [_hsv(*p) for p in pix]
    nasycenie = sum(x[1] for x in hsv) / n
    cieplo = sum(r - b for r, _, b in pix) / n / 255

    # Ostrość: wariancja laplasjanu - im więcej ostrych krawędzi, tym większa. Liczymy ją
    # w kafelkach 4x4 i bierzemy najostrzejszy, bo rozmyte tło (bokeh) to nie wada zdjęcia.
    kafelki = [[] for _ in range(16)]
    for y in range(1, w - 1):
        for x in range(1, s - 1):
            i = y * s + x
            kafelki[(y * 4 // w) * 4 + x * 4 // s].append(
                4 * jasnosci[i] - jasnosci[i - 1] - jasnosci[i + 1] - jasnosci[i - s] - jasnosci[i + s])
    lap = [v for k in kafelki for v in k]
    if lap:
        ostrosc = max(_wariancja(k) for k in kafelki if k) * 10000
        krawedzie = sum(abs(v) > 0.25 for v in lap) / len(lap)
    else:
        ostrosc, krawedzie = 0.0, 0.0

    # Kolory dominujące: k-średnie na próbce pikseli, potem łączymy grupy o tej samej nazwie.
    los = random.Random(0)
    probka = pix if n <= PROBKA_KOLOROW else los.sample(pix, PROBKA_KOLOROW)
    kolory = {}
    for srodek, udzial in k_srednie([tuple(p) for p in probka]):
        nazwa = nazwa_koloru(*srodek)
        kolory[nazwa] = kolory.get(nazwa, 0) + udzial

    # Udziały pikseli przydatne do zgadywania sceny.
    gora = s * w * 2 // 5
    niebo = sum(1 for i, (h, sat, v) in enumerate(hsv[:gora]) if 185 <= h <= 250 and sat > 0.15
                and v > 0.45) / max(1, gora)
    cieple_niebo = sum(1 for h, sat, v in hsv[:gora] if (h < 50 or h > 330) and sat > 0.35
                       and v > 0.5) / max(1, gora)
    zielen = sum(1 for h, sat, v in hsv if 70 <= h <= 165 and sat > 0.2 and v > 0.18) / n
    skora = sum(1 for p in pix if _skora(*p)) / n
    biel = sum(1 for _, sat, v in hsv if sat < 0.12 and v > 0.85) / n
    swiatla = sum(1 for j in jasnosci if j > 0.85) / n
    najczestszy = max(_histogram_ilosci(pix).values()) / n

    return {
        "szer": obraz.oryg_szer, "wys": obraz.oryg_wys, "jasnosc": srednia, "kontrast": kontrast,
        "nasycenie": nasycenie, "cieplo": cieplo, "ostrosc": ostrosc, "krawedzie": krawedzie,
        "kolory": sorted(kolory.items(), key=lambda x: -x[1]), "niebo": niebo,
        "cieple_niebo": cieple_niebo, "zielen": zielen, "skora": skora, "biel": biel,
        "swiatla": swiatla, "jednolity": najczestszy,
    }


def _wariancja(wartosci):
    srednia = sum(wartosci) / len(wartosci)
    return sum((v - srednia) ** 2 for v in wartosci) / len(wartosci)


def _histogram_ilosci(pix):
    """Ile pikseli ma (prawie) ten sam kolor - zrzuty ekranu i dokumenty mają duże jednolite tła."""
    licznik = {}
    for r, g, b in pix:
        klucz = (r >> 3, g >> 3, b >> 3)
        licznik[klucz] = licznik.get(klucz, 0) + 1
    return licznik


def zgadnij_scene(a):
    """Lista ostrożnych domysłów, co jest na zdjęciu."""
    domysly = []
    if a["jednolity"] > 0.35 and a["krawedzie"] > 0.02 and a["nasycenie"] < 0.25:
        domysly.append("wygląda na dokument, tekst albo zrzut ekranu")
    if a["jasnosc"] < 0.25 and a["swiatla"] > 0.005 and a["cieple_niebo"] < 0.35:
        domysly.append("zdjęcie nocne - ciemno, ale widać światła")
    if a["niebo"] > 0.3:
        domysly.append("niebieska góra kadru - pewnie niebo albo niebieskie tło")
    elif a["cieple_niebo"] > 0.35 and a["jasnosc"] > 0.15:
        domysly.append("ciepłe barwy u góry - może zachód albo wschód słońca")
    if a["zielen"] > 0.25:
        domysly.append("dużo zieleni - trawa, drzewa albo rośliny")
    if a["skora"] > 0.08 and a["cieple_niebo"] < 0.35:
        # Kolor skóry pokrywa się z futrem, piaskiem i drewnem, więc nie udajemy pewności.
        domysly.append("sporo ciepłych beżów i brązów - to mogą być ludzie, zwierzęta, "
                       "drewno albo piasek")
    if a["biel"] > 0.45 and not domysly:
        domysly.append("dużo bieli - może śnieg, kartka albo jasne tło")
    return domysly


def _stopien(wartosc, progi, nazwy):
    for prog, nazwa in zip(progi, nazwy):
        if wartosc < prog:
            return nazwa
    return nazwy[-1]


def opisz(a):
    """Opis analizy po polsku (bez metadanych i rozpoznawania)."""
    s, w = a["szer"], a["wys"]
    orientacja = "kwadratowe" if abs(s - w) <= 0.05 * max(s, w) else "poziome" if s > w else "pionowe"
    mpx = s * w / 1e6
    rozmiar = f"{s}×{w}" + (f" ({mpx:.1f} Mpx)".replace(".", ",") if mpx >= 0.1 else "")
    linie = [f"📷 Zdjęcie {rozmiar}, {orientacja}."]

    kolory = [f"{nazwa} {udzial:.0%}" for nazwa, udzial in a["kolory"] if udzial >= 0.04][:5]
    linie.append("🎨 Kolory: " + ", ".join(kolory) + ".")

    jasnosc = _stopien(a["jasnosc"], [0.15, 0.32, 0.68, 0.85],
                       ["bardzo ciemne", "ciemne", "dobrze naświetlone", "jasne", "prześwietlone"])
    kontrast = _stopien(a["kontrast"], [0.12, 0.25], ["niski", "średni", "wysoki"])
    if a["nasycenie"] < 0.08:
        barwy = "prawie czarno-białe"
    else:
        barwy = _stopien(a["nasycenie"], [0.2, 0.45], ["kolory stonowane", "kolory naturalne",
                                                      "kolory żywe"])
        barwy += ", " + ("barwy ciepłe" if a["cieplo"] > 0.08 else
                         "barwy chłodne" if a["cieplo"] < -0.08 else "barwy neutralne")
    linie.append(f"💡 {jasnosc.capitalize()}, kontrast {kontrast}, {barwy}.")

    ostrosc = _stopien(a["ostrosc"], [40, 80], ["rozmyte albo poruszone", "lekko miękkie", "ostre"])
    linie.append(f"🔍 Ostrość: {ostrosc}.")

    domysly = zgadnij_scene(a)
    if domysly:
        linie.append("👀 Co widzę: " + "; ".join(domysly) + ".")
    return "\n".join(linie)


# --- rozpoznawanie (uczenie na przykładach) -----------------------------------

def cechy(obraz):
    """Wektor cech do porównywania zdjęć: histogram kolorów i mała mapa układu kolorów."""
    obraz = obraz.pomniejsz(64)
    s, w = obraz.szer, obraz.wys
    # Wyrównujemy jasność, żeby to samo ujęcie, tylko jaśniejsze lub ciemniejsze, było podobne.
    srednia = sum(obraz.piksele) / len(obraz.piksele) or 1
    wzmocnienie = 110 / srednia
    obraz = Obraz(s, w, bytes(min(255, int(v * wzmocnienie)) for v in obraz.piksele))
    histogram = [0.0] * 64
    siatka = [[0.0, 0.0, 0.0, 0] for _ in range(16)]
    for y in range(w):
        for x in range(s):
            r, g, b = obraz.piksel(x, y)
            histogram[(r >> 6) * 16 + (g >> 6) * 4 + (b >> 6)] += 1
            komorka = siatka[(y * 4 // w) * 4 + x * 4 // s]
            komorka[0] += r
            komorka[1] += g
            komorka[2] += b
            komorka[3] += 1
    n = s * w
    # Pierwiastek z udziałów (odległość Hellingera) lepiej porównuje histogramy.
    wynik = [math.sqrt(h / n) for h in histogram]
    for r, g, b, ile in siatka:
        wynik.extend(c / max(1, ile) / 255 * 0.35 for c in (r, g, b))
    return [round(v, 4) for v in wynik]


def podobienstwo(a, b):
    """Podobieństwo dwóch wektorów cech w skali 0..1."""
    odleglosc = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    return max(0.0, 1.0 - odleglosc / 1.1)


def rozpoznaj(wektor, przyklady, prog=0.45):
    """Najbardziej podobny zapamiętany przykład: (etykieta, podobieństwo) albo None."""
    najlepszy = None
    for przyklad in przyklady:
        p = podobienstwo(wektor, przyklad["cechy"])
        if najlepszy is None or p > najlepszy[1]:
            najlepszy = (przyklad["etykieta"], p)
    if najlepszy and najlepszy[1] >= prog:
        return najlepszy
    return None
