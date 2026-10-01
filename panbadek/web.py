"""Czat z Panem Badkiem w przeglądarce: python -m panbadek --web"""

import json
import socket
import threading
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, ikona

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
</style>
</head>
<body>
<main>
  <h1>🤖 Pan Badek</h1>
  <div id="czat"><div class="msg badek">Cześć! Jestem Pan Badek. Napisz „co potrafisz”, żeby zobaczyć, co umiem.</div></div>
  <form id="f"><input id="t" autocomplete="off" placeholder="Napisz wiadomość…" autofocus><button>Wyślij</button></form>
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

        def do_POST(self):
            if self.path != "/api/czat":
                return self._wyslij(404, "{}", "application/json")
            try:
                dlugosc = min(int(self.headers.get("Content-Length", 0)), 10_000)
                tekst = str(json.loads(self.rfile.read(dlugosc) or b"{}").get("tekst", ""))
            except (ValueError, AttributeError):
                return self._wyslij(400, json.dumps({"odpowiedz": "Niepoprawne zapytanie."}),
                                    "application/json; charset=utf-8")
            with blokada:  # jeden mózg, więc myślimy po kolei
                odpowiedz = badek.odpowiedz(tekst)
            self._wyslij(200, json.dumps({"odpowiedz": odpowiedz}, ensure_ascii=False),
                         "application/json; charset=utf-8")

        def log_message(self, *_):
            pass

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
