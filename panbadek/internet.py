"""Dostęp do internetu: Wikipedia, pogoda (Open-Meteo) i kursy walut (NBP).

Używa wyłącznie biblioteki standardowej (urllib) i darmowych API bez kluczy.
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from . import __version__

USER_AGENT = f"PanBadek/{__version__} (https://github.com/panbadek/Pan-Badek-ai)"
LIMIT_CZASU = 10


class BladInternetu(Exception):
    """Nie udało się pobrać danych z internetu."""

    def __init__(self, komunikat, chwilowy=False):
        super().__init__(komunikat)
        self.chwilowy = chwilowy  # zerwane połączenie lub timeout - warto spróbować ponownie


def pobierz_json(url, parametry=None, limit_czasu=LIMIT_CZASU, proby=2):
    """Pobiera JSON. Przy zerwanym połączeniu próbuje jeszcze raz. 404 daje None."""
    if parametry:
        url += "?" + urllib.parse.urlencode(parametry)
    for proba in range(proby):
        try:
            return _pobierz(url, limit_czasu)
        except BladInternetu as e:
            if not e.chwilowy or proba == proby - 1:
                raise


def _pobierz(url, limit_czasu):
    if sys.platform == "emscripten":
        return _pobierz_w_przegladarce(url, limit_czasu)
    zapytanie = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                    "Accept": "application/json"})
    try:
        with urllib.request.urlopen(zapytanie, timeout=limit_czasu) as odp:
            return json.loads(odp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise BladInternetu(f"serwer odpowiedział błędem {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise BladInternetu("brak połączenia z internetem", chwilowy=True) from e
    except ValueError as e:
        raise BladInternetu("serwer zwrócił niezrozumiałe dane") from e


def _pobierz_w_przegladarce(url, limit_czasu):
    """W przeglądarce (Pyodide, w Web Workerze) urllib nie działa - używamy XMLHttpRequest."""
    from js import XMLHttpRequest  # dostępne tylko w Pyodide

    zapytanie = XMLHttpRequest.new()
    try:
        zapytanie.open("GET", url, False)
        zapytanie.timeout = int(limit_czasu * 1000)
        zapytanie.send(None)
    except Exception as e:  # błąd sieci albo CORS przychodzi jako wyjątek JavaScriptu
        raise BladInternetu("brak połączenia z internetem", chwilowy=True) from e
    if zapytanie.status == 404:
        return None
    if zapytanie.status == 0:
        raise BladInternetu("brak połączenia z internetem", chwilowy=True)
    if zapytanie.status >= 400:
        raise BladInternetu(f"serwer odpowiedział błędem {zapytanie.status}")
    try:
        return json.loads(zapytanie.responseText)
    except ValueError as e:
        raise BladInternetu("serwer zwrócił niezrozumiałe dane") from e


def pobierz_tekst(url, dane=None, naglowki=None, limit_czasu=LIMIT_CZASU):
    """Pobiera stronę jako tekst; z `dane` wysyła je jako JSON (POST). 404 daje None."""
    naglowki = {"User-Agent": USER_AGENT, **(naglowki or {})}
    cialo = json.dumps(dane).encode("utf-8") if dane is not None else None
    if cialo is not None:
        naglowki["Content-Type"] = "application/json"
    if sys.platform == "emscripten":
        return _tekst_w_przegladarce(url, cialo, naglowki, limit_czasu)
    zapytanie = urllib.request.Request(url, data=cialo, headers=naglowki)
    try:
        with urllib.request.urlopen(zapytanie, timeout=limit_czasu) as odp:
            return odp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise BladInternetu(f"serwer odpowiedział błędem {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise BladInternetu("brak połączenia z internetem", chwilowy=True) from e


def _tekst_w_przegladarce(url, cialo, naglowki, limit_czasu):
    from js import XMLHttpRequest  # dostępne tylko w Pyodide

    zapytanie = XMLHttpRequest.new()
    try:
        zapytanie.open("POST" if cialo is not None else "GET", url, False)
        zapytanie.timeout = int(limit_czasu * 1000)
        if cialo is not None:
            zapytanie.setRequestHeader("Content-Type", "application/json")
        zapytanie.send(cialo.decode("utf-8") if cialo is not None else None)
    except Exception as e:  # CORS albo brak sieci
        raise BladInternetu("strona nie pozwala na dostęp z przeglądarki", chwilowy=False) from e
    if zapytanie.status == 404:
        return None
    if zapytanie.status == 0 or zapytanie.status >= 400:
        raise BladInternetu(f"serwer odpowiedział błędem {zapytanie.status}")
    return zapytanie.responseText


# --- tekst ------------------------------------------------------------------

_SKROTY = {"r", "w", "ok", "np", "tzw", "m.in", "in", "św", "ul", "im", "wg", "tj",
           "itd", "itp", "ur", "zm", "gen", "prof", "dr", "inż", "mgr", "ks", "pt", "tys", "mln",
           "mld", "st", "n.p.m", "p.n.e", "n.e", "pn", "płd", "wsch", "zach", "woj", "pow", "gm"}


def podziel_na_zdania(tekst):
    """Dzieli tekst na zdania, nie tnąc na popularnych skrótach (np. 'r.', 'm.in.')."""
    tekst = re.sub(r"\s+", " ", tekst).strip()
    zdania, poczatek = [], 0
    for m in re.finditer(r"[.!?]\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ0-9\"„(])", tekst):
        poprzednie = tekst[poczatek:m.start()].rsplit(" ", 1)[-1].lower()
        if poprzednie.rstrip(".") in _SKROTY or re.fullmatch(r"[a-ząćęłńóśźż]", poprzednie):
            continue
        zdania.append(tekst[poczatek:m.start() + 1].strip())
        poczatek = m.end()
    if tekst[poczatek:].strip():
        zdania.append(tekst[poczatek:].strip())
    return zdania


# --- Wikipedia --------------------------------------------------------------

WIKIPEDIA_API = "https://pl.wikipedia.org/w/api.php"


def wikipedia(haslo, caly_artykul=False):
    """Szuka hasła w polskiej Wikipedii. Zwraca (tytuł, tekst, adres) albo None."""
    parametry = {
        "action": "query", "format": "json", "formatversion": "2",
        "prop": "extracts|info", "inprop": "url", "explaintext": "1", "redirects": "1",
        "generator": "search", "gsrsearch": haslo, "gsrlimit": "1",
        "origin": "*",  # zgoda na zapytania z przeglądarki (CORS)
    }
    if not caly_artykul:
        parametry["exintro"] = "1"
    dane = pobierz_json(WIKIPEDIA_API, parametry)
    strony = (dane or {}).get("query", {}).get("pages", [])
    if not strony or not strony[0].get("extract"):
        return None
    strona = strony[0]
    tekst = strona["extract"]
    if caly_artykul:
        # Odcinamy sekcje typu "Przypisy", "Bibliografia" i nagłówki "== ... ==".
        tekst = re.split(r"\n==+\s*(Przypisy|Bibliografia|Linki zewnętrzne|Zobacz też)", tekst)[0]
        tekst = re.sub(r"\n==+[^=]+==+\n", "\n", tekst)
    return strona["title"], tekst.strip(), strona.get("fullurl", "")


# --- pogoda -----------------------------------------------------------------

_KODY_POGODY = {
    0: "bezchmurnie", 1: "przeważnie słonecznie", 2: "częściowe zachmurzenie", 3: "pochmurno",
    45: "mgła", 48: "szadź i mgła", 51: "lekka mżawka", 53: "mżawka", 55: "gęsta mżawka",
    56: "marznąca mżawka", 57: "marznąca mżawka", 61: "słaby deszcz", 63: "deszcz",
    65: "ulewa", 66: "marznący deszcz", 67: "marznący deszcz", 71: "słaby śnieg", 73: "śnieg",
    75: "intensywny śnieg", 77: "ziarnisty śnieg", 80: "przelotny deszcz",
    81: "przelotne opady", 82: "gwałtowne ulewy", 85: "przelotny śnieg", 86: "śnieżyca",
    95: "burza", 96: "burza z gradem", 99: "silna burza z gradem",
}


def pogoda(miasto):
    """Aktualna pogoda dla miasta (Open-Meteo)."""
    geo = pobierz_json("https://geocoding-api.open-meteo.com/v1/search",
                       {"name": miasto, "count": 1, "language": "pl"})
    if not geo or not geo.get("results"):
        return f"Nie znalazłem miejscowości „{miasto}”."
    miejsce = geo["results"][0]
    prognoza = pobierz_json("https://api.open-meteo.com/v1/forecast", {
        "latitude": miejsce["latitude"], "longitude": miejsce["longitude"],
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min", "forecast_days": 1,
        "timezone": "auto",
    })
    teraz = prognoza["current"]
    opis = _KODY_POGODY.get(teraz["weather_code"], "trudno powiedzieć")
    dzien = prognoza.get("daily", {})
    zakres = ""
    if dzien.get("temperature_2m_min") and dzien.get("temperature_2m_max"):
        zakres = (f" Dziś od {dzien['temperature_2m_min'][0]:.0f} "
                  f"do {dzien['temperature_2m_max'][0]:.0f}°C.")
    kraj = f", {miejsce['country']}" if miejsce.get("country") else ""
    return (f"Pogoda – {miejsce['name']}{kraj}: {opis}, {teraz['temperature_2m']:.0f}°C "
            f"(odczuwalna {teraz['apparent_temperature']:.0f}°C), "
            f"wiatr {teraz['wind_speed_10m']:.0f} km/h.{zakres}")


# --- kursy walut ------------------------------------------------------------

WALUTY = {
    "euro": "EUR", "eur": "EUR", "dolar": "USD", "dolara": "USD", "dolary": "USD",
    "dolarów": "USD", "usd": "USD", "funt": "GBP", "funta": "GBP", "funty": "GBP", "gbp": "GBP",
    "frank": "CHF", "franka": "CHF", "chf": "CHF", "jen": "JPY", "jena": "JPY", "jpy": "JPY",
    "korona": "CZK", "korony": "CZK", "czk": "CZK", "hrywna": "UAH", "hrywny": "UAH",
    "uah": "UAH", "juan": "CNY", "cny": "CNY", "nok": "NOK", "sek": "SEK", "dkk": "DKK",
}


def kurs(waluta):
    """Średni kurs waluty wg NBP (tabela A)."""
    kod = WALUTY.get(waluta.lower().strip(), waluta.upper().strip())
    if not re.fullmatch(r"[A-Z]{3}", kod):
        return f"Nie znam waluty „{waluta}”. Spróbuj kodu, np. EUR albo USD."
    dane = pobierz_json(f"https://api.nbp.pl/api/exchangerates/rates/a/{kod.lower()}/",
                        {"format": "json"})
    if not dane:
        return f"NBP nie podaje kursu dla {kod}."
    notowanie = dane["rates"][0]
    return (f"Średni kurs NBP z {notowanie['effectiveDate']}: "
            f"1 {kod} ({dane['currency']}) = {notowanie['mid']:.4f} zł.")
