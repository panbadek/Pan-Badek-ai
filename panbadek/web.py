"""Czat z Panem Badkiem w przeglądarce: python -m panbadek --web"""

import base64
import binascii
import json
import socket
import threading
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, ikona
from .obrazy import Obraz

# Manifest i service worker pozwalają dodać czat do ekranu głównego telefonu
# albo zainstalować go jako aplikację w Chrome/Edge.
MANIFEST = json.dumps({
    "name": "Pan Badek",
    "short_name": "Pan Badek",
    "description": "Twoja własna sztuczna inteligencja",
    "lang": "pl",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#f4f5f7",
    "theme_color": "#2f6fed",
    "icons": [
        {"src": "/ikona-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/ikona-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/ikona-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}, ensure_ascii=False)

# Service worker trzyma w pamięci podręcznej samą stronę, żeby otwierała się szybko.
# Rozmowa zawsze idzie do serwera - bez działającego Pana Badka pokażemy komunikat.
SERVICE_WORKER = f"""
const WERSJA = "panbadek-{__version__}";
const PLIKI = ["/", "/manifest.webmanifest", "/ikona-192.png"];
self.addEventListener("install", e => e.waitUntil(
  caches.open(WERSJA).then(c => c.addAll(PLIKI)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(k => Promise.all(k.filter(n => n !== WERSJA).map(n => caches.delete(n))))
    .then(() => self.clients.claim())));
self.addEventListener("fetch", e => {{
  if (e.request.method !== "GET") return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
}});
"""

IKONY = {"/ikona-192.png": 192, "/ikona-512.png": 512, "/apple-touch-icon.png": 180,
         "/favicon.png": 64}

STRONA = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Pan Badek</title>
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#2f6fed">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Pan Badek">
<style>
  :root { --tlo: #f4f5f7; --karta: #fff; --tekst: #1d2330; --badek: #e8edf7; --ty: #2f6fed;
          --ramka: #d8dce3; }
  @media (prefers-color-scheme: dark) {
    :root { --tlo: #15181e; --karta: #1e222b; --tekst: #e6e9ef; --badek: #2a303c; --ty: #3d7bf2;
            --ramka: #343a46; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; font: 16px/1.5 system-ui, sans-serif; background: var(--tlo); color: var(--tekst);
         display: flex; justify-content: center; height: 100vh; height: 100dvh; }
  main { width: 100%; max-width: 720px; display: flex; flex-direction: column;
         padding: max(16px, env(safe-area-inset-top)) 16px max(16px, env(safe-area-inset-bottom)); }
  h1 { font-size: 20px; margin: 0 0 12px; }
  #czat { flex: 1; overflow-y: auto; background: var(--karta); border: 1px solid var(--ramka);
          border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
  .msg { max-width: 85%; padding: 8px 12px; border-radius: 12px; white-space: pre-wrap;
         overflow-wrap: anywhere; }
  .badek { background: var(--badek); align-self: flex-start; }
  .ty { background: var(--ty); color: #fff; align-self: flex-end; }
  form { display: flex; gap: 8px; margin-top: 12px; }
  input { flex: 1; padding: 10px 12px; font: inherit; border-radius: 10px; border: 1px solid var(--ramka);
          background: var(--karta); color: var(--tekst); }
  button { padding: 10px 16px; font: inherit; border: 0; border-radius: 10px; background: var(--ty);
           color: #fff; cursor: pointer; }
  #aparat { padding: 10px 12px; background: var(--badek); color: var(--tekst); }
  .msg img { display: block; max-width: 220px; max-height: 220px; border-radius: 8px; }
  .msg.ty:has(img) { padding: 4px; }
</style>
</head>
<body>
<main>
  <h1>🤖 Pan Badek</h1>
  <div id="czat"><div class="msg badek">Cześć! Jestem Pan Badek. Napisz „co potrafisz”, żeby zobaczyć, co umiem.</div></div>
  <form id="f">
    <button type="button" id="aparat" title="Wyślij zdjęcie do analizy" aria-label="Wyślij zdjęcie">📷</button>
    <input type="file" id="plik" accept="image/*" hidden>
    <input id="t" autocomplete="off" placeholder="Napisz wiadomość…" autofocus><button>Wyślij</button>
  </form>
</main>
<script>
const czat = document.getElementById("czat"), pole = document.getElementById("t");
function dodaj(tekst, kto) {
  const d = document.createElement("div");
  d.className = "msg " + kto; d.textContent = tekst;
  czat.appendChild(d); czat.scrollTop = czat.scrollHeight;
}
document.getElementById("f").addEventListener("submit", async (e) => {
  e.preventDefault();
  const tekst = pole.value.trim();
  if (!tekst) return;
  dodaj(tekst, "ty"); pole.value = "";
  try {
    const r = await fetch("/api/czat", {method: "POST", headers: {"Content-Type": "application/json"},
                                        body: JSON.stringify({tekst})});
    dodaj((await r.json()).odpowiedz, "badek");
  } catch (err) {
    dodaj("Ups, nie mogę się połączyć z Panem Badkiem. Czy program działa na komputerze?", "badek");
  }
});
// Zdjęcie dekoduje przeglądarka (JPEG, PNG, HEIC...), pomniejsza do 256 px i wysyła piksele.
// Do odczytu metadanych (data, aparat, miejsce) dokładamy początek oryginalnego pliku.
const ROZMIAR = 256;
document.getElementById("aparat").addEventListener("click", () => document.getElementById("plik").click());
document.getElementById("plik").addEventListener("change", async (e) => {
  const plik = e.target.files[0];
  e.target.value = "";
  if (!plik) return;
  const adres = URL.createObjectURL(plik);
  const d = document.createElement("div");
  d.className = "msg ty";
  const img = document.createElement("img");
  img.src = adres; img.alt = plik.name;
  d.appendChild(img); czat.appendChild(d); czat.scrollTop = czat.scrollHeight;
  try {
    await img.decode();
    const skala = Math.min(1, ROZMIAR / Math.max(img.naturalWidth, img.naturalHeight));
    const s = Math.max(1, Math.round(img.naturalWidth * skala)), w = Math.max(1, Math.round(img.naturalHeight * skala));
    const plotno = document.createElement("canvas");
    plotno.width = s; plotno.height = w;
    const ctx = plotno.getContext("2d");
    ctx.drawImage(img, 0, 0, s, w);
    const rgba = ctx.getImageData(0, 0, s, w).data, rgb = new Uint8Array(s * w * 3);
    for (let i = 0, j = 0; i < rgba.length; i += 4) {
      rgb[j++] = rgba[i]; rgb[j++] = rgba[i + 1]; rgb[j++] = rgba[i + 2];
    }
    const naglowek = new Uint8Array(await plik.slice(0, 256 * 1024).arrayBuffer());
    const r = await fetch("/api/zdjecie", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({szer: s, wys: w, oryg_szer: img.naturalWidth, oryg_wys: img.naturalHeight,
                            piksele: base64(rgb), naglowek: base64(naglowek)})});
    dodaj((await r.json()).odpowiedz, "badek");
  } catch (err) {
    dodaj("Nie udało się odczytać tego zdjęcia. Spróbuj JPEG albo PNG.", "badek");
  }
});
function base64(bajty) {
  let s = "";
  for (let i = 0; i < bajty.length; i += 0x8000) s += String.fromCharCode.apply(null, bajty.subarray(i, i + 0x8000));
  return btoa(s);
}
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
</script>
</body>
</html>
"""


def stworz_serwer(badek, host="127.0.0.1", port=8000):
    blokada = threading.Lock()

    class Obsluga(BaseHTTPRequestHandler):
        def _wyslij(self, kod, tresc, typ):
            dane = tresc if isinstance(tresc, bytes) else tresc.encode("utf-8")
            self.send_response(kod)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(dane)))
            self.end_headers()
            self.wfile.write(dane)

        def do_GET(self):
            sciezka = self.path.split("?")[0]
            if sciezka in ("/", "/index.html"):
                self._wyslij(200, STRONA, "text/html; charset=utf-8")
            elif sciezka == "/manifest.webmanifest":
                self._wyslij(200, MANIFEST, "application/manifest+json; charset=utf-8")
            elif sciezka == "/sw.js":
                self._wyslij(200, SERVICE_WORKER, "text/javascript; charset=utf-8")
            elif sciezka in IKONY:
                self._wyslij(200, ikona.png(IKONY[sciezka]), "image/png")
            else:
                self._wyslij(404, "Nie ma takiej strony", "text/plain; charset=utf-8")

        def _odpowiedz(self, kod, odpowiedz):
            self._wyslij(kod, json.dumps({"odpowiedz": odpowiedz}, ensure_ascii=False),
                         "application/json; charset=utf-8")

        def do_POST(self):
            limity = {"/api/czat": 10_000, "/api/zdjecie": 2_000_000}
            if self.path not in limity:
                return self._wyslij(404, "{}", "application/json")
            try:
                dlugosc = int(self.headers.get("Content-Length", 0))
                if dlugosc > limity[self.path]:
                    return self._odpowiedz(413, "Za duże zapytanie.")
                dane = json.loads(self.rfile.read(dlugosc) or b"{}")
                if self.path == "/api/czat":
                    tekst = str(dane.get("tekst", ""))
                else:
                    obraz = Obraz(int(dane["szer"]), int(dane["wys"]),
                                  base64.b64decode(dane["piksele"]),
                                  int(dane.get("oryg_szer") or 0), int(dane.get("oryg_wys") or 0))
                    if max(obraz.szer, obraz.wys) > 1024:
                        return self._odpowiedz(413, "Wyślij pomniejszone zdjęcie (do 1024 px).")
                    naglowek = base64.b64decode(dane.get("naglowek") or "")
            except (ValueError, AttributeError, KeyError, TypeError, binascii.Error):
                return self._odpowiedz(400, "Niepoprawne zapytanie.")
            with blokada:  # jeden mózg, więc myślimy po kolei
                if self.path == "/api/czat":
                    odpowiedz = badek.odpowiedz(tekst)
                else:
                    odpowiedz = badek.analizuj_zdjecie(obraz, naglowek)
            self._odpowiedz(200, odpowiedz)

        def log_message(self, *_):
            pass

    # Przez czat nie wolno czytać plików z dysku komputera po ścieżce.
    badek.pliki_lokalne = False
    return ThreadingHTTPServer((host, port), Obsluga)


def adres_w_sieci_lokalnej():
    """Adres IP komputera w sieci Wi-Fi/LAN (pod nim telefon znajdzie Pana Badka)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))  # nic nie jest wysyłane, to tylko wybór interfejsu
            return s.getsockname()[0]
        except OSError:
            return None


def juz_dziala(port):
    """Czy pod tym portem odpowiada już Pan Badek?"""
    try:
        bez_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with bez_proxy.open(f"http://127.0.0.1:{port}/manifest.webmanifest", timeout=2) as odp:
            return json.load(odp).get("name") == "Pan Badek"
    except (OSError, ValueError):
        return False


def uruchom(badek, host="127.0.0.1", port=8000, otworz=False):
    adres = f"http://127.0.0.1:{port}"
    try:
        serwer = stworz_serwer(badek, host, port)
    except OSError:
        if juz_dziala(port):
            print(f"Pan Badek już działa na {adres}")
            if otworz:
                webbrowser.open(adres)
            return
        raise SystemExit(f"Port {port} jest zajęty. Wybierz inny: --port 8080")

    print(f"Pan Badek czeka na {adres} (Ctrl+C kończy)")
    if host in ("0.0.0.0", "::"):
        ip = adres_w_sieci_lokalnej()
        if ip:
            print(f"Na telefonie w tej samej sieci Wi-Fi otwórz: http://{ip}:{port}")
            print("i wybierz w menu przeglądarki „Dodaj do ekranu głównego”.")
        print("Uwaga: każdy w tej sieci może teraz rozmawiać z Panem Badkiem.")
    if otworz:
        threading.Timer(0.5, webbrowser.open, [adres]).start()
    try:
        serwer.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serwer.server_close()
