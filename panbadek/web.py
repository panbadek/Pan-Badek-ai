"""Czat z Panem Badkiem w przeglądarce: python -m panbadek --web"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STRONA = """<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pan Badek</title>
<style>
  :root { --tlo: #f4f5f7; --karta: #fff; --tekst: #1d2330; --badek: #e8edf7; --ty: #2f6fed;
          --ramka: #d8dce3; }
  @media (prefers-color-scheme: dark) {
    :root { --tlo: #15181e; --karta: #1e222b; --tekst: #e6e9ef; --badek: #2a303c; --ty: #3d7bf2;
            --ramka: #343a46; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; font: 16px/1.5 system-ui, sans-serif; background: var(--tlo); color: var(--tekst);
         display: flex; justify-content: center; height: 100vh; }
  main { width: 100%; max-width: 720px; display: flex; flex-direction: column; padding: 16px; }
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
  } catch (err) { dodaj("Ups, nie mogę się połączyć z Panem Badkiem.", "badek"); }
});
</script>
</body>
</html>
"""


def stworz_serwer(badek, host="127.0.0.1", port=8000):
    blokada = threading.Lock()

    class Obsluga(BaseHTTPRequestHandler):
        def _wyslij(self, kod, tresc, typ):
            dane = tresc.encode("utf-8")
            self.send_response(kod)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(dane)))
            self.end_headers()
            self.wfile.write(dane)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._wyslij(200, STRONA, "text/html; charset=utf-8")
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


def uruchom(badek, host="127.0.0.1", port=8000):
    serwer = stworz_serwer(badek, host, port)
    print(f"Pan Badek czeka na http://{host}:{port} (Ctrl+C kończy)")
    try:
        serwer.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serwer.server_close()
