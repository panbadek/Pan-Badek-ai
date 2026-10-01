// Service worker: Pan Badek otwiera się szybko i działa bez internetu.
// Pliki aplikacji: najpierw sieć (świeża wersja), w razie braku - kopia z pamięci.
// Pyodide z CDN: najpierw pamięć (pliki są wersjonowane i się nie zmieniają).
// Modele AI trzymają w pamięci same biblioteki (Transformers.js, WebLLM).

const WERSJA = "panbadek-__WERSJA__";
const CDN = "panbadek-cdn"; // pliki z CDN mają wersję w adresie, więc nie trzeba ich czyścić
const APLIKACJA = ["./", "index.html", "app.js", "badek-worker.js", "llm-worker.js", "panbadek.zip",
                   "model.json", "etykiety.json", "manifest.webmanifest", "ikona-192.png"];

self.addEventListener("install", (e) => e.waitUntil(
  caches.open(WERSJA).then((c) => c.addAll(APLIKACJA)).then(() => self.skipWaiting())));

self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((k) => Promise.all(k.filter((n) => n.startsWith("panbadek-") && n !== WERSJA && n !== CDN)
    .map((n) => caches.delete(n)))).then(() => self.clients.claim())));

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.origin === location.origin) {
    e.respondWith(fetch(e.request).then((odp) => {
      if (odp.ok) { const kopia = odp.clone(); caches.open(WERSJA).then((c) => c.put(e.request, kopia)); }
      return odp;
    }).catch(() => caches.match(e.request, { ignoreSearch: true })));
  } else if (url.hostname === "cdn.jsdelivr.net" && (url.pathname.startsWith("/pyodide/") || url.pathname.includes("@"))) {
    e.respondWith(caches.match(e.request).then((z) => z || fetch(e.request).then((odp) => {
      if (odp.ok) { const kopia = odp.clone(); caches.open(CDN).then((c) => c.put(e.request, kopia)); }
      return odp;
    })));
  }
});
