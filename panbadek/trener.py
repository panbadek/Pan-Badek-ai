"""Trener Pana Badka.

Uczy sieć, sprawdza całego Badka i dobiera ustawienia, które działają najlepiej:

  python3 -m panbadek.trener               # strojenie + egzamin (nic nie zapisuje)
  python3 -m panbadek.trener --zapisz      # ... i zapisuje najlepsze ustawienia
  python3 -m panbadek.trener --szybko      # mniej kandydatów i krótsza walidacja
  python3 -m panbadek.trener --egzamin     # tylko egzamin całego Badka
  python3 -m panbadek.trener --nauczyciel  # Claude dopisuje przykłady treningowe
                                           # i uczy Badka odpowiedzi na pytania z rozmów

Co robi:
1. **Walidacja krzyżowa**: dzieli przykłady na k części, trenuje na k-1, sprawdza na
   pozostałej. To uczciwa miara, bo sieć ocenia zdania, których nie widziała.
2. **Strojenie**: porównuje ustawienia (liczba neuronów, tempo uczenia, augmentacja
   literówkami) i wybiera najlepsze według walidacji krzyżowej. Zestawy testowe są tylko
   do raportu, więc nie „uczy się pod test”.
3. **Egzamin**: około 140 pytań do całego Badka (rozmowa, wiedza, matematyka, C++,
   uczciwość, pułapki) i wynik w każdej kategorii.
4. **Nauczyciel** (opcjonalnie, `pip install anthropic` i klucz API): Claude pisze nowe
   przykłady dla każdego tematu. Trener zostawia je tylko wtedy, gdy walidacja krzyżowa
   się nie pogorszy. Do tego Claude odpowiada na pytania z rozmów, na które Badek nie
   znał odpowiedzi, a Badek je zapamiętuje.
"""

import argparse
import contextlib
import json
import os
import random
import sys
import tempfile
import time
from datetime import date

from . import augmentacja, brain
from .text import normalizuj

DANE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EGZAMIN = os.path.join(DANE, "egzamin.json")
# Pytania napisane przed poprawkami i nieużywane do ich dobierania - uczciwa miara.
EGZAMIN_KONTROLNY = os.path.join(DANE, "egzamin_kontrolny.json")
ZESTAWY_TESTOWE = {"testowe": os.path.join(DANE, "test_intencje.json"),
                   "trudne": os.path.join(DANE, "test_trudne.json")}
NAZWY_KATEGORII = {"rozmowa": "rozmowa", "wiedza": "wiedza", "matematyka": "matematyka",
                   "programowanie": "C++", "szkola": "szkoła", "laczenie": "łączenie faktów",
                   "logika": "logika", "sprawdzanie": "sprawdzanie", "uczciwosc": "uczciwość", "pulapki": "pułapki"}

TOLERANCJA = 0.01
KANDYDACI = [
    {"neurony": 48, "epoki": 300, "tempo": 0.05, "warianty": 0},
    {"neurony": 64, "epoki": 300, "tempo": 0.05, "warianty": 0},
    {"neurony": 48, "epoki": 300, "tempo": 0.05, "warianty": 1},
    {"neurony": 48, "epoki": 300, "tempo": 0.05, "warianty": 2},
    {"neurony": 64, "epoki": 300, "tempo": 0.05, "warianty": 2},
    {"neurony": 64, "epoki": 300, "tempo": 0.03, "warianty": 2},
    {"neurony": 96, "epoki": 300, "tempo": 0.05, "warianty": 2},
    {"neurony": 64, "epoki": 300, "tempo": 0.05, "warianty": 3},
]
KANDYDACI_SZYBCY = [KANDYDACI[0], KANDYDACI[3], KANDYDACI[4]]


def wczytaj_json(plik):
    with open(plik, encoding="utf-8") as f:
        return json.load(f)


@contextlib.contextmanager
def ustawienia(nowe):
    """Na chwilę podmienia ustawienia sieci (trener porównuje różne)."""
    stare = dict(brain.USTAWIENIA)
    brain.USTAWIENIA.clear()
    brain.USTAWIENIA.update({**stare, **nowe})
    try:
        yield
    finally:
        brain.USTAWIENIA.clear()
        brain.USTAWIENIA.update(stare)


@contextlib.contextmanager
def badek_na_danych(intencje, ziarno=0):
    """Świeży Pan Badek (bez internetu i bez twojej pamięci) wytrenowany na podanych intencjach."""
    with tempfile.TemporaryDirectory() as katalog:
        plik = os.path.join(katalog, "intencje.json")
        with open(plik, "w", encoding="utf-8") as f:
            json.dump({"intencje": intencje}, f, ensure_ascii=False)
        yield brain.PanBadek(plik_intencji=plik, katalog_pamieci=os.path.join(katalog, "pamiec"),
                             internet=False, ziarno=ziarno)


def dokladnosc(badek, testy):
    """Odsetek zdań, dla których sieć wybiera dobrą intencję ("inne" = sieć nie odpowiada)."""
    bledy = [(t["tekst"], t["oczekiwana"], badek.rozpoznaj_intencje(t["tekst"]) or "inne") for t in testy]
    bledy = [b for b in bledy if b[1] != b[2]]
    return 1 - len(bledy) / max(1, len(testy)), bledy


def podziel(intencje, k, ziarno):
    """k par (intencje do treningu, zdania do sprawdzenia), każda intencja w każdej części."""
    czesci = []
    los = random.Random(ziarno)
    pomieszane = {i["nazwa"]: los.sample(i["przyklady"], len(i["przyklady"])) for i in intencje}
    for n in range(k):
        trening, test = [], []
        for i in intencje:
            przyklady = pomieszane[i["nazwa"]]
            trening.append({**i, "przyklady": [p for j, p in enumerate(przyklady) if j % k != n]})
            test += [{"tekst": p, "oczekiwana": i["nazwa"]} for j, p in enumerate(przyklady) if j % k == n]
        czesci.append((trening, test))
    return czesci


def walidacja_krzyzowa(intencje, k=5, ziarna=(0,)):
    """Średnia dokładność na zdaniach odłożonych przy treningu."""
    wyniki = []
    for ziarno in ziarna:
        for trening, test in podziel(intencje, k, ziarno):
            with badek_na_danych(trening, ziarno) as badek:
                wyniki.append(dokladnosc(badek, test)[0])
    return sum(wyniki) / len(wyniki)


def zestawy_testowe():
    """Zestawy testowe i "literówki": te same zdania z jedną losową literówką (inne
    ziarno niż przy augmentacji, więc sieć ich nie widziała)."""
    zestawy = {nazwa: wczytaj_json(plik)["testy"] for nazwa, plik in ZESTAWY_TESTOWE.items()
               if os.path.exists(plik)}
    los = random.Random(999)
    literowki = []
    for t in [t for testy in zestawy.values() for t in testy]:
        slowa = t["tekst"].split()
        dlugie = [i for i, s in enumerate(slowa) if len(s) >= 4]
        if dlugie:
            i = los.choice(dlugie)
            slowa[i] = augmentacja.literowka(slowa[i], los)
            if " ".join(slowa) != t["tekst"]:
                literowki.append({"tekst": " ".join(slowa), "oczekiwana": t["oczekiwana"]})
    zestawy["literówki"] = literowki
    return zestawy


def ocen_ustawienia(intencje, kandydat, k, ziarna):
    """Walidacja krzyżowa i (do raportu) zestawy testowe, średnio po kilku losowaniach wag -
    pojedyncza sieć potrafi różnić się od innej o 2-3 punkty przez sam przypadek."""
    start = time.time()
    zestawy = zestawy_testowe()
    with ustawienia(kandydat):
        wynik = {"ustawienia": kandydat, "walidacja": walidacja_krzyzowa(intencje, k, ziarna)}
        for nazwa in zestawy:
            wynik[nazwa] = 0.0
        for ziarno in ziarna:
            with badek_na_danych(intencje, ziarno) as badek:
                for nazwa, testy in zestawy.items():
                    wynik[nazwa] += dokladnosc(badek, testy)[0] / len(ziarna)
    wynik["czas"] = time.time() - start
    return wynik


def opis(ustawienia_sieci):
    return (f"{ustawienia_sieci['neurony']} neuronów, tempo {ustawienia_sieci['tempo']}, "
            f"augmentacja ×{ustawienia_sieci['warianty']}")


def strojenie(intencje, kandydaci, k=5, ziarna=(0, 1), wypisz=print):
    """Porównuje ustawienia i zwraca listę wyników, najlepsze pierwsze."""
    wyniki = []
    for kandydat in kandydaci:
        wynik = ocen_ustawienia(intencje, kandydat, k, ziarna)
        wyniki.append(wynik)
        testy = "  ".join(f"{n}: {wynik[n]:6.1%}" for n in wynik if n not in ("ustawienia", "walidacja", "czas"))
        wypisz(f"  {opis(kandydat):42} walidacja: {wynik['walidacja']:6.1%}  {testy}  ({wynik['czas']:.0f} s)")
    # Różnice mniejsze niż TOLERANCJA to szum, więc spośród ustawień prawie tak dobrych jak
    # najlepsze wybieramy najprostsze (mniej neuronów i wariantów = szybszy trening).
    najlepsza = max(w["walidacja"] for w in wyniki)
    prostota = lambda w: (w["ustawienia"]["neurony"], w["ustawienia"]["warianty"], -w["walidacja"])  # noqa: E731
    bliskie = sorted((w for w in wyniki if w["walidacja"] >= najlepsza - TOLERANCJA), key=prostota)
    return bliskie + sorted((w for w in wyniki if w not in bliskie), key=lambda w: -w["walidacja"])


def _sprawdz(pytanie, odp, badek):
    if "intencja" in pytanie:
        return badek.zrodlo == "siec_neuronowa" and badek._intencja_odpowiedzi == pytanie["intencja"]
    if "zaczyna" in pytanie:  # "Tak"/"Nie" na początku, a nie gdzieś w środku ("także")
        return any(normalizuj(odp).lstrip("*# ").startswith(normalizuj(z)) for z in pytanie["zaczyna"])
    if "zawiera" in pytanie:
        trafione = [normalizuj(z) in normalizuj(odp) for z in pytanie["zawiera"]]
        return all(trafione) if pytanie.get("wszystkie") else any(trafione)
    if "zrodlo" in pytanie:
        return badek.zrodlo in pytanie["zrodlo"]
    if pytanie.get("nie_intencja"):
        return badek.zrodlo != "siec_neuronowa"
    return False


def egzamin(badek=None, plik=EGZAMIN):
    """Egzamin całego Badka: {kategoria: (zdane, wszystkie, [oblane pytania])}."""
    pytania = wczytaj_json(plik)["pytania"]
    with contextlib.ExitStack() as stos:
        if badek is None:
            badek = stos.enter_context(badek_na_danych(wczytaj_json(brain.DOMYSLNE_INTENCJE)["intencje"]))
        wyniki = {}
        for p in pytania:
            badek._temat = badek._poprzednia_odpowiedz = None  # każde pytanie to nowa rozmowa
            odp = badek.odpowiedz(p["pytanie"])
            zdane, wszystkie, oblane = wyniki.get(p["kategoria"], (0, 0, []))
            if _sprawdz(p, odp, badek):
                zdane += 1
            else:
                oblane.append((p["pytanie"], badek.zrodlo, odp.split("\n")[0][:80]))
            wyniki[p["kategoria"]] = (zdane, wszystkie + 1, oblane)
    return wyniki


def wypisz_egzamin(wyniki, wypisz=print, bledy=True):
    razem = sum(w[0] for w in wyniki.values()), sum(w[1] for w in wyniki.values())
    for kategoria, (zdane, wszystkie, oblane) in wyniki.items():
        pasek = "█" * round(20 * zdane / wszystkie)
        wypisz(f"  {NAZWY_KATEGORII.get(kategoria, kategoria):14} {pasek:20} {zdane}/{wszystkie}")
        if bledy:
            for pytanie, zrodlo, odp in oblane:
                wypisz(f"      ✗ „{pytanie}” [{zrodlo}] {odp}")
    wypisz(f"  {'RAZEM':14} {razem[0]}/{razem[1]} ({razem[0] / razem[1]:.1%})")
    return razem[0] / razem[1]


# Umiejętności, które moim zdaniem powinna mieć każda AI, i kategorie egzaminu, które je sprawdzają.
UMIEJETNOSCI = [
    ("Uczciwość: mówi „nie wiem” zamiast zmyślać", ["uczciwosc", "pulapki"]),
    ("Łączenie faktów i wzorów (rozumowanie wieloetapowe)", ["laczenie"]),
    ("Wnioskowanie logiczne z wyjaśnieniem", ["logika"]),
    ("Sprawdzanie własnych odpowiedzi", ["sprawdzanie"]),
    ("Rozwiązywanie zadań krok po kroku", ["matematyka", "szkola"]),
    ("Wiedza o świecie", ["wiedza"]),
    ("Rozmowa i rozumienie intencji", ["rozmowa"]),
    ("Pisanie kodu", ["programowanie"]),
]


def wypisz_umiejetnosci(*wyniki_egzaminow, wypisz=print):
    """Wyniki egzaminów zebrane według umiejętności AI."""
    for nazwa, kategorie in UMIEJETNOSCI:
        zdane = sum(w[k][0] for w in wyniki_egzaminow for k in kategorie if k in w)
        wszystkie = sum(w[k][1] for w in wyniki_egzaminow for k in kategorie if k in w)
        if wszystkie:
            ocena = "✅" if zdane / wszystkie >= 0.95 else "🟡" if zdane / wszystkie >= 0.8 else "🔴"
            wypisz(f"  {ocena} {nazwa}: {zdane}/{wszystkie} ({zdane / wszystkie:.0%})")


def zapisz_ustawienia(wynik, plik=brain.USTAWIENIA_SIECI):
    dane = {**wynik["ustawienia"], "_opis": "Ustawienia dobrane przez trenera (python3 -m panbadek.trener --zapisz).",
            "_wyniki": {k: round(v, 4) for k, v in wynik.items() if k not in ("ustawienia", "czas")},
            "_data": date.today().isoformat()}
    with open(plik, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=1)
        f.write("\n")


# --- nauczyciel (Claude) -------------------------------------------------------

MODEL = "claude-opus-5-5"
_SCHEMAT_ZDAN = {
    "type": "object",
    "properties": {"zdania": {"type": "array", "items": {"type": "string"}}},
    "required": ["zdania"],
    "additionalProperties": False,
}
_SCHEMAT_ODPOWIEDZI = {
    "type": "object",
    "properties": {"odpowiedz": {"type": "string"}, "pewna": {"type": "boolean"}},
    "required": ["odpowiedz", "pewna"],
    "additionalProperties": False,
}


class Nauczyciel:
    """Claude jako nauczyciel: pisze nowe przykłady treningowe i odpowiedzi do zapamiętania."""

    def __init__(self, klient=None):
        if klient is None:
            try:
                import anthropic
            except ImportError as e:
                raise RuntimeError("Nauczyciel potrzebuje SDK: pip install anthropic") from e
            klient = anthropic.Anthropic()  # klucz z ANTHROPIC_API_KEY albo z `ant auth login`
        self.klient = klient

    def _zapytaj(self, polecenie, schemat, wysilek="medium"):
        odp = self.klient.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # przy odmowie API samo spróbuje innego modelu
            output_config={"effort": wysilek, "format": {"type": "json_schema", "schema": schemat}},
            messages=[{"role": "user", "content": polecenie}],
        )
        if odp.stop_reason == "refusal":
            return None
        tekst = next((b.text for b in odp.content if b.type == "text"), "")
        try:
            return json.loads(tekst)
        except ValueError:
            return None

    def parafrazy(self, intencja, przyklady, ile=12):
        """Nowe, różnorodne zdania o tym samym znaczeniu, co przykłady intencji."""
        if intencja == "inne":
            polecenie = (
                "Uczę małą sieć neuronową rozpoznawać pogawędkę po polsku. Klasa „inne” to pytania o wiedzę, "
                "porady i zadania, na które ma NIE odpowiadać pogawędką (zajmie się nimi baza wiedzy albo duży model). "
                f"Przykłady: {json.dumps(przyklady[:25], ensure_ascii=False)}\n"
                f"Napisz {ile} nowych, różnorodnych pytań tego rodzaju. Szczególnie takich, które zawierają słowa "
                "z pogawędki (np. „ile lat ma…”, „która godzina jest w Tokio”, „jak się czuje…”, „dziękuję – co to za "
                "piosenka”), a mimo to są pytaniami o wiedzę. Krótkie, naturalne, jak pisane na telefonie.")
        else:
            polecenie = (
                f"Uczę małą sieć neuronową rozpoznawać intencję „{intencja}” w rozmowie po polsku. "
                f"Obecne przykłady: {json.dumps(przyklady, ensure_ascii=False)}\n"
                f"Napisz {ile} NOWYCH zdań o tej samej intencji, innych niż przykłady: różne słowa i długości, "
                "mowa potoczna i slang, czasem bez polskich znaków albo z drobną literówką, jak pisane na telefonie. "
                "Każde zdanie musi jednoznacznie wyrażać tę intencję i nic więcej.")
        wynik = self._zapytaj(polecenie, _SCHEMAT_ZDAN)
        return [z.strip() for z in (wynik or {}).get("zdania", []) if 0 < len(z.strip()) <= 80]

    def odpowiedz(self, pytanie):
        """Krótka, sprawdzona odpowiedź do zapamiętania albo None, gdy nie ma pewnej."""
        wynik = self._zapytaj(
            "Odpowiedz po polsku, rzeczowo, w 1-3 zdaniach, na pytanie zadane asystentowi w telefonie. "
            "Odpowiedź zostanie zapamiętana na stałe, więc ustaw „pewna” na false, jeśli odpowiedź zależy od "
            "bieżących wydarzeń, miejsca, osoby pytającej albo nie masz pewności.\n\n"
            f"Pytanie: {pytanie}", _SCHEMAT_ODPOWIEDZI, wysilek="low")
        if not wynik or not wynik.get("pewna") or not wynik.get("odpowiedz", "").strip():
            return None
        return wynik["odpowiedz"].strip()


def _znane_zdania(intencje):
    znane = {normalizuj(p).strip(" ?!.") for i in intencje for p in i["przyklady"]}
    for testy in zestawy_testowe().values():  # nigdy nie trenujemy na zdaniach testowych
        znane |= {normalizuj(t["tekst"]).strip(" ?!.") for t in testy}
    return znane


def nauczyciel_przyklady(intencje, nauczyciel, ile=12, k=5, ziarna=(0,), wypisz=print):
    """Claude dopisuje przykłady. Zostają tylko, jeśli walidacja się nie pogorszy."""
    przed = walidacja_krzyzowa(intencje, k, ziarna)
    znane = _znane_zdania(intencje)
    nowe_intencje, dodane = [], 0
    for i in intencje:
        nowe = []
        for zdanie in nauczyciel.parafrazy(i["nazwa"], i["przyklady"], ile):
            klucz = normalizuj(zdanie).strip(" ?!.")
            if klucz and klucz not in znane:
                znane.add(klucz)
                nowe.append(zdanie)
        dodane += len(nowe)
        nowe_intencje.append({**i, "przyklady": i["przyklady"] + nowe})
        wypisz(f"  {i['nazwa']:14} +{len(nowe)}")
    # Porównujemy na tych samych zdaniach sprawdzających: nowe przykłady tylko dokładamy do treningu.
    po = _walidacja_z_dodatkami(intencje, nowe_intencje, k, ziarna)
    wypisz(f"  walidacja: {przed:.1%} → {po:.1%} ({dodane} nowych zdań)")
    return (nowe_intencje if po >= przed else intencje), przed, po


def _walidacja_z_dodatkami(stare, nowe, k, ziarna):
    """Walidacja na starych zdaniach; nowe przykłady trafiają tylko do treningu."""
    dodatki = {i["nazwa"]: i["przyklady"][len(s["przyklady"]):] for i, s in zip(nowe, stare)}
    wyniki = []
    for ziarno in ziarna:
        for trening, test in podziel(stare, k, ziarno):
            trening = [{**i, "przyklady": i["przyklady"] + dodatki[i["nazwa"]]} for i in trening]
            with badek_na_danych(trening, ziarno) as badek:
                wyniki.append(dokladnosc(badek, test)[0])
    return sum(wyniki) / len(wyniki)


def nauczyciel_wiedza(badek, nauczyciel, ile=20, wypisz=print):
    """Claude odpowiada na pytania z rozmów, na które Badek nie znał odpowiedzi."""
    nauczone = 0
    for pytanie, razy in badek.czego_nie_wiem(ile):
        odp = nauczyciel.odpowiedz(pytanie)
        if odp and badek.naucz_od_ai(pytanie, odp, "Claude (trener)") is not None:
            nauczone += 1
            wypisz(f"  ✓ „{pytanie}” ({razy}×) → {odp[:70]}")
        else:
            wypisz(f"  – „{pytanie}”: bez pewnej odpowiedzi, pomijam")
    return nauczone


# --- uruchomienie --------------------------------------------------------------

def main(argv=None, wypisz=print):
    parser = argparse.ArgumentParser(prog="python3 -m panbadek.trener", description="Trener Pana Badka")
    parser.add_argument("--zapisz", action="store_true", help="zapisz najlepsze ustawienia (i przykłady od nauczyciela)")
    parser.add_argument("--szybko", action="store_true", help="mniej kandydatów i krótsza walidacja")
    parser.add_argument("--egzamin", action="store_true", help="tylko egzamin całego Badka")
    parser.add_argument("--nauczyciel", action="store_true", help="Claude dopisuje przykłady i uczy Badka (pip install anthropic)")
    parser.add_argument("--pamiec", default=brain.DOMYSLNA_PAMIEC, help="katalog pamięci Badka uczonego przez nauczyciela")
    args = parser.parse_args(argv)

    if args.egzamin:
        wypisz("📝 Egzamin Pana Badka (offline, bez twojej pamięci):")
        glowny = egzamin()
        wypisz_egzamin(glowny, wypisz)
        wypisz("\n📝 Egzamin kontrolny:")
        kontrolny = egzamin(plik=EGZAMIN_KONTROLNY)
        wypisz_egzamin(kontrolny, wypisz)
        wypisz("\n🎯 Umiejętności AI (oba egzaminy razem):")
        wypisz_umiejetnosci(glowny, kontrolny, wypisz=wypisz)
        return 0

    intencje = wczytaj_json(brain.DOMYSLNE_INTENCJE)["intencje"]
    k, ziarna = (3, (0,)) if args.szybko else (5, (0, 1))
    przykladow = sum(len(i["przyklady"]) for i in intencje)
    wypisz(f"🏋️ Trener Pana Badka: {len(intencje)} tematów, {przykladow} przykładów, walidacja {k}-krotna")

    if args.nauczyciel:
        nauczyciel = Nauczyciel()
        wypisz("\n👩‍🏫 Nauczyciel (Claude) pisze nowe przykłady:")
        nowe, przed, po = nauczyciel_przyklady(intencje, nauczyciel, k=k, ziarna=ziarna[:1], wypisz=wypisz)
        if nowe is intencje:
            wypisz("  Nowe przykłady nie pomogły - zostawiam stare.")
        else:
            intencje = nowe
            if args.zapisz:
                with open(brain.DOMYSLNE_INTENCJE, "w", encoding="utf-8") as f:
                    json.dump({"intencje": intencje}, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                wypisz(f"  Zapisałem przykłady w {brain.DOMYSLNE_INTENCJE}")

    wypisz("\n🔧 Strojenie sieci:")
    wyniki = strojenie(intencje, KANDYDACI_SZYBCY if args.szybko else KANDYDACI, k, ziarna, wypisz)
    najlepszy, obecny = wyniki[0], next((w for w in wyniki if w["ustawienia"] == {
        k_: brain.USTAWIENIA[k_] for k_ in brain.DOMYSLNE_USTAWIENIA}), None)
    wypisz(f"\n🏆 Wybrane: {opis(najlepszy['ustawienia'])} (walidacja {najlepszy['walidacja']:.1%}; "
           f"najprostsze w granicach {TOLERANCJA:.0%} od najlepszego)")
    if obecny and obecny is not najlepszy:
        wypisz(f"   Obecne:   {opis(obecny['ustawienia'])} (walidacja {obecny['walidacja']:.1%})")

    wypisz("\n📝 Egzamin z najlepszymi ustawieniami:")
    with ustawienia(najlepszy["ustawienia"]):
        with badek_na_danych(intencje) as badek:
            najlepszy["egzamin"] = wypisz_egzamin(egzamin(badek), wypisz)
        wypisz("\n📝 Egzamin kontrolny (pytania nieużywane przy poprawkach):")
        with badek_na_danych(intencje) as badek:
            najlepszy["egzamin_kontrolny"] = wypisz_egzamin(egzamin(badek, EGZAMIN_KONTROLNY), wypisz)

    if args.zapisz:
        zapisz_ustawienia(najlepszy)
        wypisz(f"\n💾 Zapisałem ustawienia w {brain.USTAWIENIA_SIECI}")
    else:
        wypisz("\nUruchom z --zapisz, żeby Badek używał tych ustawień.")

    if args.nauczyciel:
        wypisz("\n👩‍🏫 Nauczyciel odpowiada na pytania z twoich rozmów, na które Badek nie znał odpowiedzi:")
        with ustawienia(najlepszy["ustawienia"]):
            badek = brain.PanBadek(katalog_pamieci=args.pamiec, internet=False)
            nauczone = nauczyciel_wiedza(badek, nauczyciel, wypisz=wypisz)
        wypisz(f"  Badek zapamiętał {nauczone} nowych odpowiedzi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
