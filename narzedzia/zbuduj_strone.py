"""Buduje Pana Badka jako stronę (do GitHub Pages): python3 narzedzia/zbuduj_strone.py _site

Strona działa w całości w przeglądarce telefonu: Python Pana Badka uruchamia Pyodide,
a pliki tutaj to tylko statyczne zasoby - nie potrzeba żadnego serwera.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile

KORZEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KORZEN)

from panbadek import PanBadek, __version__, ikona  # noqa: E402

PLIKI_WEB = ["index.html", "app.js", "badek-worker.js", "llm-worker.js", "sw.js", "etykiety.json"]
# Moduły, które w przeglądarce nie mają sensu (serwer, skróty na pulpicie, Android).
POMIJANE = {"web.py", "skrot.py", "android.py", "__main__.py"}



def _zaokraglij(wartosc):
    if isinstance(wartosc, list):
        return [_zaokraglij(w) for w in wartosc]
    return round(wartosc, 4)

def zbuduj(cel):
    if os.path.exists(cel):
        shutil.rmtree(cel)
    os.makedirs(cel)
    for nazwa in PLIKI_WEB:
        shutil.copy(os.path.join(KORZEN, "web", nazwa), os.path.join(cel, nazwa))

    with zipfile.ZipFile(os.path.join(cel, "panbadek.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        pakiet = os.path.join(KORZEN, "panbadek")
        for katalog, _, pliki in os.walk(pakiet):
            if "__pycache__" in katalog:
                continue
            for plik in sorted(pliki):
                if plik in POMIJANE or plik.endswith(".pyc"):
                    continue
                pelna = os.path.join(katalog, plik)
                z.write(pelna, os.path.relpath(pelna, KORZEN))

    # Wytrenowana sieć: telefon nie musi jej trenować przy pierwszym uruchomieniu.
    with tempfile.TemporaryDirectory() as tmp:
        PanBadek(katalog_pamieci=tmp, internet=False, ziarno=0)
        with open(os.path.join(tmp, "model.json"), encoding="utf-8") as f:
            model = json.load(f)
    # 4 miejsca po przecinku wystarczą (żadna decyzja sieci się nie zmienia),
    # a plik do pobrania jest 3 razy mniejszy.
    model["siec"] = {k: _zaokraglij(v) for k, v in model["siec"].items()}
    with open(os.path.join(cel, "model.json"), "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, separators=(",", ":"))

    for nazwa, rozmiar in {"ikona-192.png": 192, "ikona-512.png": 512,
                           "apple-touch-icon.png": 180, "favicon.png": 64}.items():
        ikona.zapisz(os.path.join(cel, nazwa), rozmiar)

    with open(os.path.join(cel, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        json.dump({
            "name": "Pan Badek", "short_name": "Pan Badek", "lang": "pl",
            "description": "Twoja sztuczna inteligencja, która działa w telefonie",
            "start_url": "./", "scope": "./", "display": "standalone",
            "background_color": "#f4f5f7", "theme_color": "#2f6fed",
            "icons": [
                {"src": "ikona-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": "ikona-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                {"src": "ikona-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
            ],
        }, f, ensure_ascii=False)

    # Wersja w service workerze zmienia się razem z treścią plików, więc telefon pobierze aktualizację.
    skrot = hashlib.sha256()
    for nazwa in sorted(os.listdir(cel)):
        with open(os.path.join(cel, nazwa), "rb") as f:
            skrot.update(f.read())
    sciezka_sw = os.path.join(cel, "sw.js")
    with open(sciezka_sw, encoding="utf-8") as f:
        sw = f.read().replace("__WERSJA__", f"{__version__}-{skrot.hexdigest()[:10]}")
    with open(sciezka_sw, "w", encoding="utf-8") as f:
        f.write(sw)
    open(os.path.join(cel, ".nojekyll"), "w").close()
    return cel


if __name__ == "__main__":
    cel = zbuduj(sys.argv[1] if len(sys.argv) > 1 else os.path.join(KORZEN, "_site"))
    print("Strona zbudowana w", cel)
