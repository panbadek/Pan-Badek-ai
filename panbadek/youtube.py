"""Pan Badek „ogląda” filmy na YouTube: czyta ich napisy i robi z nich notatki.

Badek nie widzi obrazu ani nie słyszy dźwięku, ale prawie każdy film na YouTube ma
napisy (dodane przez autora albo automatyczne). Badek pobiera je, dzieli na zdania,
zapisuje w bibliotece wiedzy i robi streszczenie. Potem odpowiada na pytania o film.

Pobieranie napisów działa w aplikacji na Androida i na komputerze. W przeglądarce
YouTube na to nie pozwala (CORS), więc tam można wkleić transkrypcję:
„naucz się z tekstu: …”.
"""

import html
import json
import re

from . import internet
from .biblioteki import NIEISTOTNE
from .text import normalizuj, rdzen
from .wiedza import istotne_slowa

ID_FILMU = re.compile(r"(?:youtube\.com/(?:watch\?(?:[^\s#]*&)?v=|shorts/|embed/|live/)|youtu\.be/)([\w-]{11})")
_KLIENT = {"clientName": "ANDROID", "clientVersion": "20.10.38", "androidSdkVersion": 34, "hl": "pl"}
_UA_ANDROID = "com.google.android.youtube/20.10.38 (Linux; U; Android 14) gzip"
_SZUM = re.compile(r"\[(?:muzyka|music|śmiech|laughter|oklaski|applause|brawa|__|muzyka w tle)\]", re.I)
MAKS_FRAGMENTOW = 400


class BrakNapisow(Exception):
    """Film nie ma napisów (Badek nie ma z czego się uczyć)."""


def id_filmu(tekst):
    m = ID_FILMU.search(tekst)
    return m.group(1) if m else None


# --- pobieranie ---------------------------------------------------------------

def _odtwarzacz_api(id_):
    """Dane filmu z API odtwarzacza (tak jak aplikacja YouTube na Androida)."""
    tresc = internet.pobierz_tekst(
        "https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
        dane={"context": {"client": _KLIENT}, "videoId": id_},
        naglowki={"User-Agent": _UA_ANDROID, "X-Youtube-Client-Name": "3",
                  "X-Youtube-Client-Version": _KLIENT["clientVersion"]})
    return json.loads(tresc) if tresc else None


def _strona_filmu(id_):
    """Zapasowo: dane odtwarzacza zapisane w kodzie strony filmu."""
    tresc = internet.pobierz_tekst(
        f"https://www.youtube.com/watch?v={id_}&hl=pl",
        naglowki={"Accept-Language": "pl,en;q=0.8", "Cookie": "CONSENT=YES+1; SOCS=CAI",
                  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"})
    if not tresc:
        return None
    m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;\s*(?:var\s|</script>)", tresc, re.S)
    return json.loads(m.group(1)) if m else None


def wybierz_sciezke(odtwarzacz):
    """Najlepsze napisy: polskie od autora, polskie automatyczne, angielskie, a potem dowolne."""
    sciezki = (((odtwarzacz or {}).get("captions") or {}).get("playerCaptionsTracklistRenderer") or {}).get(
        "captionTracks") or []
    if not sciezki:
        return None

    def ocena(s):
        jezyk = s.get("languageCode", "")
        return ({"pl": 0, "en": 2}.get(jezyk.split("-")[0], 4) + (1 if s.get("kind") == "asr" else 0))
    return min(sciezki, key=ocena)


def parsuj_napisy(tresc):
    """Napisy w formacie YouTube (XML srv1/srv3 albo JSON json3) -> [(sekunda, tekst)]."""
    tresc = (tresc or "").strip()
    fragmenty = []
    if tresc.startswith("{"):
        for zdarzenie in json.loads(tresc).get("events", []):
            tekst = "".join(s.get("utf8", "") for s in zdarzenie.get("segs") or [])
            fragmenty.append((zdarzenie.get("tStartMs", 0) / 1000, tekst))
    else:
        wzorce = [(r'<text start="([\d.]+)"[^>]*>(.*?)</text>', 1),
                  (r'<p t="(\d+)"[^>]*>(.*?)</p>', 1000)]
        for wzor, dzielnik in wzorce:
            for m in re.finditer(wzor, tresc, re.S):
                tekst = re.sub(r"<[^>]+>", "", m.group(2))
                fragmenty.append((float(m.group(1)) / dzielnik, tekst))
            if fragmenty:
                break
    wynik = []
    for czas, tekst in fragmenty:
        tekst = html.unescape(html.unescape(tekst)).replace("\n", " ")
        tekst = _SZUM.sub(" ", tekst)
        tekst = re.sub(r"\s+", " ", tekst).strip()
        if tekst:
            wynik.append((czas, tekst))
    return wynik


def pobierz_napisy(id_):
    """(tytuł, autor, [(sekunda, tekst)], język, czy_automatyczne). Rzuca BrakNapisow."""
    odtwarzacz, ostatni_blad = None, None
    for zrodlo in (_odtwarzacz_api, _strona_filmu):
        try:
            odtwarzacz = zrodlo(id_)
        except (internet.BladInternetu, ValueError) as e:
            ostatni_blad = e
            continue
        if wybierz_sciezke(odtwarzacz):
            break
    sciezka = wybierz_sciezke(odtwarzacz)
    if not sciezka:
        if odtwarzacz is None and isinstance(ostatni_blad, internet.BladInternetu):
            raise ostatni_blad
        raise BrakNapisow(id_)
    adres = re.sub(r"&fmt=[^&]*", "", sciezka["baseUrl"])
    fragmenty = parsuj_napisy(internet.pobierz_tekst(adres))
    if not fragmenty:
        raise BrakNapisow(id_)
    szczegoly = (odtwarzacz or {}).get("videoDetails") or {}
    return (szczegoly.get("title") or f"Film {id_}", szczegoly.get("author") or "", fragmenty,
            sciezka.get("languageCode", "?"), sciezka.get("kind") == "asr")


# --- notatki -------------------------------------------------------------------

def na_zdania(fragmenty):
    """Fragmenty napisów -> zdania. Automatyczne napisy nie mają kropek, więc tniemy je
    na kawałki po 12-22 słowa, najchętniej w miejscu dłuższej pauzy."""
    tekst = " ".join(t for _, t in fragmenty)
    slow = len(tekst.split())
    if slow and len(re.findall(r"[.!?](?:\s|$)", tekst)) >= slow / 40:
        return [z for z in internet.podziel_na_zdania(tekst) if len(z.split()) >= 3][:MAKS_FRAGMENTOW]
    zdania, biezace = [], []
    for i, (czas, tekst) in enumerate(fragmenty):
        nastepny = fragmenty[i + 1][0] if i + 1 < len(fragmenty) else None
        biezace.append(tekst)
        dlugosc = len(" ".join(biezace).split())
        pauza = nastepny is not None and nastepny - czas > 3
        if dlugosc >= 22 or (dlugosc >= 12 and pauza) or (dlugosc >= 8 and i % 2 == 1) or nastepny is None:
            zdanie = " ".join(biezace)
            zdania.append(zdanie[0].upper() + zdanie[1:] + ".")
            biezace = []
    return zdania[:MAKS_FRAGMENTOW]


def _czestosci(zdania):
    """Częstość rdzeni ważnych słów i ich najczęstsze formy (z polskimi znakami)."""
    licznik, formy = {}, {}
    for zdanie in zdania:
        for slowo in re.findall(r"[^\W\d_]+", zdanie.lower()):
            znormalizowane = normalizuj(slowo)
            if len(znormalizowane) <= 3 or znormalizowane in NIEISTOTNE:
                continue
            r = rdzen(znormalizowane)
            licznik[r] = licznik.get(r, 0) + 1
            formy.setdefault(r, {}).setdefault(slowo, 0)
            formy[r][slowo] += 1
    return licznik, formy


def streszczenie(zdania, ile=5):
    """Najważniejsze zdania (te, w których najczęściej padają główne słowa filmu), w kolejności."""
    licznik, _ = _czestosci(zdania)
    if not licznik:
        return zdania[:ile]

    def ocena(zdanie):
        rdzenie = {rdzen(s) for s in istotne_slowa(zdanie) if len(s) > 3}
        if len(zdanie.split()) < 6 or not rdzenie:
            return 0
        return sum(licznik.get(r, 0) for r in rdzenie) / len(rdzenie) ** 0.5

    najlepsze = sorted(range(len(zdania)), key=lambda i: -ocena(zdania[i]))[:ile]
    return [zdania[i] for i in sorted(najlepsze)]


def slowa_kluczowe(zdania, ile=8):
    licznik, formy = _czestosci(zdania)
    najczestsze = sorted(licznik, key=lambda r: -licznik[r])[:ile]
    return [max(formy[r], key=formy[r].get) for r in najczestsze if licznik[r] >= 2]
