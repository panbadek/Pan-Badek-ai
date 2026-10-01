// Pan Badek w przeglądarce - interfejs czatu i "dodatkowe mózgi":
//  * Pan Badek (Python w Pyodide, badek-worker.js) - polecenia, pamięć, internet, analiza zdjęć,
//  * MobileCLIP (Transformers.js) - rozpoznawanie obiektów na zdjęciach w telefonie,
//  * lokalny model językowy (WebLLM, llm-worker.js) - rozmowa na GPU telefonu,
//  * Claude (oficjalne SDK Anthropic) - najmocniejszy tryb, z kluczem API użytkownika.

const SDK_ANTHROPIC = "https://cdn.jsdelivr.net/npm/@anthropic-ai/sdk@0.131.0/+esm";
const WEBLLM = "https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.85/+esm";
const TRANSFORMERS = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.0";
const MODEL_CLAUDE = "claude-opus-5-5";
const MODELE_LOKALNE = [
  { baza: "Qwen3.5-0.8B", nazwa: "Qwen3.5 0.8B - lekki" },
  { baza: "Qwen3.5-2B", nazwa: "Qwen3.5 2B - zalecany" },
  { baza: "Qwen3.5-4B", nazwa: "Qwen3.5 4B - najmocniejszy" },
];
const ROZMIAR_ANALIZY = 256;
const ROZMIAR_DLA_CLAUDE = 1024;
const DLUGOSC_HISTORII = 16;

const $ = (id) => document.getElementById(id);
const czat = $("czat"), pole = $("t"), status = $("status");

// --- ustawienia (tylko w tym urządzeniu) ---------------------------------------

const DOMYSLNE = { mozg: "badek", kiedy: "zawsze", rozpoznawanie: true, model: "", klucz: "", uczSie: true };
let ust = { ...DOMYSLNE };
try { ust = { ...DOMYSLNE, ...JSON.parse(localStorage.getItem("panbadek") || "{}") }; } catch {}
function zapiszUstawienia() {
  try { localStorage.setItem("panbadek", JSON.stringify(ust)); } catch {}
}

// --- wiadomości w czacie ----------------------------------------------------------

function bezpieczny(tekst) {
  const d = document.createElement("div");
  d.textContent = tekst;
  return d.innerHTML
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/(https?:\/\/[^\s<]+[^\s<.,;:!?)\]])/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
}

function dodaj(tekst, kto, podpis) {
  const d = document.createElement("div");
  d.className = "msg " + kto;
  d.innerHTML = bezpieczny(tekst);
  if (podpis) ustawPodpis(d, podpis);
  czat.appendChild(d);
  czat.scrollTop = czat.scrollHeight;
  return d;
}

function ustawPodpis(dymek, podpis) {
  const p = document.createElement("span");
  p.className = "podpis" + (podpis.startsWith("🧠") ? " ai" : "");
  p.textContent = podpis;
  dymek.appendChild(p);
}

function aktualizuj(dymek, tekst) {
  dymek.innerHTML = bezpieczny(tekst);
  czat.scrollTop = czat.scrollHeight;
}

// --- Pan Badek (Python w Web Workerze) --------------------------------------------

const robotnik = new Worker("badek-worker.js");
const oczekujace = new Map();
let kolejneId = 0, badekGotowy = false, imie = null;
const startBadka = new Promise((ok, blad) => {
  robotnik.onmessage = ({ data }) => {
    if (data.typ === "postep") status.textContent = data.tekst;
    else if (data.typ === "gotowy") { imie = data.imie; badekGotowy = true; ok(); }
    else if (data.typ === "blad_startu") blad(new Error(data.tekst));
    else if (data.typ === "wynik") { oczekujace.get(data.id)?.(data); oczekujace.delete(data.id); }
  };
});
startBadka.then(() => { $("wyslij").disabled = false; odswiezStatus(); pole.focus(); })
  .catch((e) => { status.textContent = "błąd startu"; dodaj("Nie udało się uruchomić Pana Badka: " + e.message, "badek"); });

function zapytajBadka(wiadomosc, przenies) {
  const id = ++kolejneId;
  return new Promise((ok) => { oczekujace.set(id, ok); robotnik.postMessage({ ...wiadomosc, id }, przenies || []); });
}

// --- historia rozmowy dla modeli AI -----------------------------------------------

const historia = [];
function zapamietaj(rola, tekst) {
  historia.push({ role: rola, content: tekst });
  while (historia.length > DLUGOSC_HISTORII) historia.shift();
}
function historiaDlaModelu() {
  const h = historia.slice();
  while (h.length && h[0].role !== "user") h.shift(); // rozmowa musi zaczynać się od użytkownika
  return h;
}
function instrukcja() {
  return "Jesteś Pan Badek - przyjazny, pomocny asystent AI w aplikacji na telefonie. " +
    "Odpowiadasz po polsku, zwięźle i konkretnie (zwykle 1-4 zdania), chyba że ktoś prosi o więcej. " +
    "Nie zmyślaj faktów; jeśli czegoś nie wiesz, powiedz to. " +
    (imie ? `Rozmówca ma na imię ${imie}. ` : "") +
    "Aplikacja ma też wbudowane polecenia, które możesz podpowiadać: 'pogoda w <mieście>', " +
    "'kurs <waluta>', 'co to jest <hasło>' (Wikipedia), kalkulator ('ile to 12*7'), " +
    "analiza zdjęć (przycisk 📷), 'naucz się: pytanie => odpowiedź'.";
}

// --- Claude (najmocniejszy mózg) --------------------------------------------------

let anthropic = null;
async function klientClaude() {
  if (!anthropic) anthropic = await import(SDK_ANTHROPIC);
  return new anthropic.default({ apiKey: ust.klucz, dangerouslyAllowBrowser: true });
}

function opisBleduClaude(e) {
  const A = anthropic?.default;
  if (A && e instanceof A.AuthenticationError) return "Nieprawidłowy klucz API - sprawdź go w ⚙️.";
  if (A && e instanceof A.PermissionDeniedError) return "Ten klucz API nie ma dostępu do modelu.";
  if (A && e instanceof A.RateLimitError) return "Za dużo zapytań naraz - spróbuj za chwilę.";
  if (A && e instanceof A.APIConnectionError) return "Brak połączenia z Claude - sprawdź internet.";
  return "Claude zgłosił błąd: " + (e?.message || e);
}

async function claudeStrumien(wiadomosci, naTekst) {
  const klient = await klientClaude();
  const strumien = klient.beta.messages.stream({
    model: MODEL_CLAUDE,
    max_tokens: 16000,
    // Gdy filtr bezpieczeństwa odmówi, API samo powtórzy zapytanie na zalecanym modelu zapasowym.
    betas: ["server-side-fallback-2026-07-01"],
    fallbacks: "default",
    output_config: { effort: "low" }, // rozmowa na telefonie: szybko i tanio
    system: instrukcja(),
    messages: wiadomosci,
  });
  let tekst = "";
  for await (const zdarzenie of strumien) {
    if (zdarzenie.type === "content_block_delta" && zdarzenie.delta.type === "text_delta") {
      tekst += zdarzenie.delta.text;
      naTekst(tekst);
    }
  }
  const koniec = await strumien.finalMessage();
  if (koniec.stop_reason === "refusal") {
    tekst = tekst || "Claude odmówił odpowiedzi na to pytanie.";
  }
  return tekst;
}

// --- lokalny model językowy (WebLLM) ----------------------------------------------

let webllm = null, silnik = null, modelSilnika = "", ladowanieSilnika = null;

async function wspieraWebGPU() {
  if (!navigator.gpu) return null;
  try { return await navigator.gpu.requestAdapter(); } catch { return null; }
}

async function dostepneModele() {
  webllm = webllm || await import(WEBLLM);
  const adapter = await wspieraWebGPU();
  const f16 = adapter?.features?.has("shader-f16");
  const lista = webllm.prebuiltAppConfig.model_list;
  return MODELE_LOKALNE.map((m) => {
    const id = [`${m.baza}-q4f16_1-MLC`, `${m.baza}-q4f32_1-MLC`].find((x, i) => (i === 1 || f16) && lista.some((l) => l.model_id === x));
    const rekord = lista.find((l) => l.model_id === id);
    return id && { id, nazwa: m.nazwa, mb: Math.round(rekord?.vram_required_MB || 0) };
  }).filter(Boolean);
}

function wlaczSilnik(id, naPostep) {
  if (silnik && modelSilnika === id) return Promise.resolve(silnik);
  ladowanieSilnika = (async () => {
    webllm = webllm || await import(WEBLLM);
    const watek = new Worker(new URL("llm-worker.js", import.meta.url), { type: "module" });
    const nowy = await webllm.CreateWebWorkerMLCEngine(watek, id, { initProgressCallback: naPostep });
    silnik = nowy; modelSilnika = id;
    return nowy;
  })();
  ladowanieSilnika.finally(() => { ladowanieSilnika = null; odswiezStatus(); });
  return ladowanieSilnika;
}

async function lokalnyStrumien(wiadomosci, naTekst) {
  const odpowiedz = await silnik.chat.completions.create({
    messages: [{ role: "system", content: instrukcja() }, ...wiadomosci],
    stream: true,
    temperature: 0.7,
    extra_body: { enable_thinking: false }, // Qwen bez "myślenia na głos" - szybciej na telefonie
  });
  let tekst = "";
  for await (const kawalek of odpowiedz) {
    tekst += kawalek.choices[0]?.delta?.content || "";
    naTekst(tekst.replace(/<think>[\s\S]*?(<\/think>|$)/g, "").trimStart());
  }
  return tekst.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
}

function nazwaModeluLokalnego() {
  return MODELE_LOKALNE.find((m) => modelSilnika.startsWith(m.baza))?.nazwa.split(" - ")[0] || modelSilnika;
}

// --- wybór mózgu ------------------------------------------------------------------

function aktywneAI() {
  if (ust.mozg === "claude" && ust.klucz) return "claude";
  if (ust.mozg === "lokalny" && silnik) return "lokalny";
  return null;
}

function odswiezStatus() {
  const czesci = [badekGotowy ? "Badek ✓" : "Badek…"];
  if (ust.mozg === "claude") czesci.push(ust.klucz ? "Claude ✓" : "Claude: brak klucza");
  if (ust.mozg === "lokalny") czesci.push(silnik ? `${nazwaModeluLokalnego()} ✓` : ladowanieSilnika ? "model AI: ładuję…" : "model AI: wyłączony");
  status.textContent = czesci.join(" · ");
}

async function odpowiedzAI(rodzaj, wiadomosci, zapasowa) {
  const podpis = rodzaj === "claude" ? "🧠 Claude" : `🧠 ${nazwaModeluLokalnego()} (w telefonie)`;
  const dymek = dodaj("", "badek pisze");
  try {
    const naTekst = (t) => aktualizuj(dymek, t);
    const tekst = rodzaj === "claude" ? await claudeStrumien(wiadomosci, naTekst) : await lokalnyStrumien(wiadomosci, naTekst);
    dymek.classList.remove("pisze");
    aktualizuj(dymek, tekst || zapasowa);
    ustawPodpis(dymek, podpis);
    return { tekst, dymek, nazwa: podpis.replace("🧠 ", "").replace(" (w telefonie)", "") };
  } catch (e) {
    dymek.classList.remove("pisze");
    aktualizuj(dymek, zapasowa || "");
    ustawPodpis(dymek, rodzaj === "claude" ? opisBleduClaude(e) : "Model w telefonie zgłosił błąd: " + e.message);
    return { tekst: null, dymek };
  }
}

// --- oceny 👍/👎: Badek uczy się na nich ---------------------------------------------

const OCENIANE = ["siec_neuronowa", "wiedza", "biblioteka", "internet", "ai"];

function dodajOceny(dymek, idOdpowiedzi) {
  const oceny = document.createElement("span");
  oceny.className = "oceny";
  for (const [znak, dobra, opis] of [["👍", true, "Dobra odpowiedź"], ["👎", false, "Zła odpowiedź"]]) {
    const przycisk = document.createElement("button");
    przycisk.type = "button"; przycisk.textContent = znak; przycisk.title = opis; przycisk.setAttribute("aria-label", opis);
    przycisk.addEventListener("click", async () => {
      oceny.remove();
      const wynik = await zapytajBadka({ typ: "ocena", id_odpowiedzi: idOdpowiedzi, dobra });
      ustawPodpis(dymek, (dobra ? "👍 " : "👎 ") + wynik.odpowiedz);
    });
    oceny.appendChild(przycisk);
  }
  dymek.appendChild(oceny);
}

// --- rozmowa ----------------------------------------------------------------------

async function wyslijTekst(tekst) {
  dodaj(tekst, "ty");
  const wynik = await zapytajBadka({ typ: "czat", tekst });
  imie = wynik.imie ?? imie;
  const rodzaj = aktywneAI();
  const pogawedka = ["siec_neuronowa", "biblioteka"].includes(wynik.zrodlo);
  zapamietaj("user", tekst);
  if (rodzaj && (wynik.zrodlo === "nie_wiem" || (ust.kiedy === "zawsze" && pogawedka))) {
    const ai = await odpowiedzAI(rodzaj, historiaDlaModelu(), wynik.odpowiedz);
    zapamietaj("assistant", ai.tekst || wynik.odpowiedz);
    if (ai.tekst && ust.uczSie) {
      // Badek zapamiętuje odpowiedź dużego modelu - na podobne pytanie odpowie potem sam.
      const nauka = await zapytajBadka({ typ: "naucz_od_ai", pytanie: tekst, odpowiedz: ai.tekst, zrodlo: ai.nazwa });
      if (nauka.zapamietane) ai.dymek.querySelector(".podpis").textContent += " · Badek zapamiętał";
      dodajOceny(ai.dymek, nauka.id_odpowiedzi);
    }
  } else {
    const dymek = dodaj(wynik.odpowiedz, "badek");
    if (OCENIANE.includes(wynik.zrodlo) && wynik.id_odpowiedzi) dodajOceny(dymek, wynik.id_odpowiedzi);
    zapamietaj("assistant", wynik.odpowiedz);
    if (wynik.zrodlo === "nie_wiem" && ust.mozg === "lokalny" && !silnik && ladowanieSilnika) {
      dodaj("Model AI jeszcze się ładuje - za chwilę odpowiem mądrzej.", "badek");
    }
  }
}

$("f").addEventListener("submit", (e) => {
  e.preventDefault();
  const tekst = pole.value.trim();
  if (!tekst || !badekGotowy) return;
  pole.value = "";
  wyslijTekst(tekst);
});

// --- zdjęcia ----------------------------------------------------------------------

let clip = null;
async function rozpoznawacz() {
  if (!clip) {
    clip = (async () => {
      const T = await import(TRANSFORMERS);
      const etykiety = await (await fetch("etykiety.json")).json();
      const procesor = await T.AutoProcessor.from_pretrained(etykiety.model);
      // fp16: wersja 8-bitowa (q8) tego modelu daje błędne wyniki.
      const model = await T.CLIPVisionModelWithProjection.from_pretrained(etykiety.model, { dtype: "fp16", device: "wasm" });
      const surowe = Uint8Array.from(atob(etykiety.wektory), (c) => c.charCodeAt(0));
      return { T, procesor, model, etykiety, wektory: new Int8Array(surowe.buffer) };
    })();
    clip.catch(() => { clip = null; });
  }
  return clip;
}

async function rozpoznajObiekty(adres) {
  const { T, procesor, model, etykiety, wektory } = await rozpoznawacz();
  const { image_embeds } = await model(await procesor(await T.RawImage.fromURL(adres)));
  const v = image_embeds.data, d = etykiety.wymiar;
  let norma = 0; for (const x of v) norma += x * x; norma = Math.sqrt(norma);
  const logity = etykiety.etykiety.map((_, i) => {
    let s = 0; for (let j = 0; j < d; j++) s += wektory[i * d + j] * v[j];
    return (100 * s) / 127 / norma;
  });
  const maks = Math.max(...logity), wyk = logity.map((l) => Math.exp(l - maks)), suma = wyk.reduce((a, b) => a + b, 0);
  return wyk.map((x, i) => [etykiety.etykiety[i], x / suma]).sort((a, b) => b[1] - a[1]).slice(0, 3);
}

function opisRozpoznania(top) {
  const widoczne = top.filter(([, p], i) => i === 0 || p >= 0.1).map(([n, p]) => `${n} ${Math.round(p * 100)}%`);
  return (top[0][1] >= 0.3 ? "🤖 AI rozpoznaje: " : "🤖 AI nie jest pewne - może: ") + widoczne.join(", ");
}

function pomniejsz(img, maks) {
  const skala = Math.min(1, maks / Math.max(img.naturalWidth, img.naturalHeight));
  const plotno = document.createElement("canvas");
  plotno.width = Math.max(1, Math.round(img.naturalWidth * skala));
  plotno.height = Math.max(1, Math.round(img.naturalHeight * skala));
  plotno.getContext("2d").drawImage(img, 0, 0, plotno.width, plotno.height);
  return plotno;
}

async function wyslijZdjecie(plik) {
  const adres = URL.createObjectURL(plik);
  const dymek = document.createElement("div");
  dymek.className = "msg ty foto";
  const img = document.createElement("img");
  img.src = adres; img.alt = "Wysłane zdjęcie";
  dymek.appendChild(img); czat.appendChild(dymek); czat.scrollTop = czat.scrollHeight;
  try {
    await img.decode();
  } catch {
    dodaj("Nie udało się odczytać tego zdjęcia. Spróbuj JPEG albo PNG.", "badek");
    return;
  }

  const plotno = pomniejsz(img, ROZMIAR_ANALIZY);
  const rgba = plotno.getContext("2d").getImageData(0, 0, plotno.width, plotno.height).data;
  const rgb = new Uint8Array((rgba.length / 4) * 3);
  for (let i = 0, j = 0; i < rgba.length; i += 4) { rgb[j++] = rgba[i]; rgb[j++] = rgba[i + 1]; rgb[j++] = rgba[i + 2]; }
  const naglowek = new Uint8Array(await plik.slice(0, 256 * 1024).arrayBuffer());

  const analiza = zapytajBadka({ typ: "zdjecie", szer: plotno.width, wys: plotno.height,
    oryg_szer: img.naturalWidth, oryg_wys: img.naturalHeight, piksele: rgb, naglowek }, [rgb.buffer, naglowek.buffer]);
  const obiekty = ust.rozpoznawanie ? rozpoznajObiekty(adres).catch(() => null) : Promise.resolve(null);
  const [wynik, top] = await Promise.all([analiza, obiekty]);

  let tekst = wynik.odpowiedz;
  if (top) tekst = opisRozpoznania(top) + "\n" + tekst;
  else if (ust.rozpoznawanie) tekst = "🤖 Rozpoznawanie obiektów niedostępne (brak internetu przy pierwszym użyciu?).\n" + tekst;
  dodaj(tekst, "badek");
  zapamietaj("user", "(Wysłałem zdjęcie.)");
  zapamietaj("assistant", tekst);

  if (aktywneAI() === "claude") {
    const jpeg = pomniejsz(img, ROZMIAR_DLA_CLAUDE).toDataURL("image/jpeg", 0.85).split(",")[1];
    const { tekst: opis } = await odpowiedzAI("claude", [{ role: "user", content: [
      { type: "image", source: { type: "base64", media_type: "image/jpeg", data: jpeg } },
      { type: "text", text: "Opisz po polsku, co jest na tym zdjęciu (2-4 zdania). Jeśli jest na nim tekst, przepisz najważniejszy fragment." },
    ] }], "");
    if (opis) zapamietaj("assistant", "Opis zdjęcia: " + opis);
  }
}

$("aparat").addEventListener("click", () => $("plik").click());
$("plik").addEventListener("change", (e) => {
  const plik = e.target.files[0];
  e.target.value = "";
  if (plik && badekGotowy) wyslijZdjecie(plik);
});

// --- panel ustawień ---------------------------------------------------------------

const panel = $("panel"), formularz = $("formularz");

async function wypelnijModele() {
  const wybor = $("model-lokalny");
  if (!(await wspieraWebGPU())) { $("brak-webgpu").hidden = false; $("pobierz-model").disabled = true; }
  if (wybor.options.length) return;
  try {
    const modele = await dostepneModele();
    for (const m of modele) wybor.add(new Option(`${m.nazwa} · ${(m.mb / 1024).toFixed(1).replace(".", ",")} GB`, m.id));
    wybor.value = ust.model || modele.find((m) => m.id.includes("2B"))?.id || modele[0]?.id;
    for (const m of modele) {
      if (await webllm.hasModelInCache(m.id)) wybor.querySelector(`option[value="${m.id}"]`).text += " ✓ pobrany";
    }
  } catch (e) {
    $("stan-modelu").textContent = "Nie udało się wczytać listy modeli: " + e.message;
  }
}

function pokazSekcje() {
  $("ustawienia-lokalne").hidden = formularz.mozg.value !== "lokalny";
  $("ustawienia-claude").hidden = formularz.mozg.value !== "claude";
}
for (const r of formularz.mozg) r.addEventListener("change", pokazSekcje);

function pokazPanel() {
  formularz.mozg.value = ust.mozg;
  pokazSekcje();
  formularz.kiedy.value = ust.kiedy;
  $("rozpoznawanie").checked = ust.rozpoznawanie;
  $("ucz-sie").checked = ust.uczSie;
  $("klucz").value = ust.klucz;
  panel.showModal();
  wypelnijModele();
}

async function uruchomModelLokalny(id) {
  const postep = $("postep-modelu"), stan = $("stan-modelu");
  postep.hidden = false;
  stan.textContent = "Pobieram model… (raz, potem jest w pamięci telefonu)";
  odswiezStatus();
  try {
    await wlaczSilnik(id, (r) => { postep.value = r.progress || 0; stan.textContent = r.text?.slice(0, 120) || ""; });
    stan.textContent = "Model działa ✓";
    dodaj(`Włączyłem model AI w telefonie (${nazwaModeluLokalnego()}). Teraz rozmawiam mądrzej!`, "badek");
  } catch (e) {
    stan.textContent = "Nie udało się uruchomić modelu: " + e.message;
  } finally {
    postep.hidden = true;
    odswiezStatus();
  }
}

$("ustawienia").addEventListener("click", pokazPanel);
$("pobierz-model").addEventListener("click", () => {
  ust.model = $("model-lokalny").value;
  ust.mozg = formularz.mozg.value = "lokalny";
  zapiszUstawienia();
  uruchomModelLokalny(ust.model);
});
panel.addEventListener("close", () => {
  ust.mozg = formularz.mozg.value || "badek";
  ust.kiedy = formularz.kiedy.value || "zawsze";
  ust.rozpoznawanie = $("rozpoznawanie").checked;
  ust.uczSie = $("ucz-sie").checked;
  ust.klucz = $("klucz").value.trim();
  if ($("model-lokalny").value) ust.model = $("model-lokalny").value;
  zapiszUstawienia();
  if (ust.mozg === "lokalny" && ust.model && !silnik && !ladowanieSilnika) uruchomModelLokalny(ust.model);
  if (ust.mozg === "claude" && !ust.klucz) dodaj("Aby używać Claude, wklej klucz API w ⚙️.", "badek");
  odswiezStatus();
});

// Po ponownym otwarciu aplikacji włączamy wcześniej wybrany model (jest już pobrany, więc to chwila).
if (ust.mozg === "lokalny" && ust.model) {
  wspieraWebGPU().then((gpu) => gpu && wlaczSilnik(ust.model, () => {}).then(odswiezStatus, () => odswiezStatus()));
}

// --- kopia pamięci: przenoszenie wiedzy między telefonem, komputerem i innymi czatami -------

$("eksport").addEventListener("click", async () => {
  const { dane } = await zapytajBadka({ typ: "eksport" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([dane], { type: "application/json" }));
  link.download = `pan-badek-pamiec-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 10000);
});
$("import").addEventListener("click", () => $("plik-pamieci").click());
$("plik-pamieci").addEventListener("change", async (e) => {
  const plik = e.target.files[0];
  e.target.value = "";
  if (!plik) return;
  const wynik = await zapytajBadka({ typ: "import", dane: await plik.text() });
  panel.close();
  dodaj(wynik.odpowiedz, "badek");
});

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
odswiezStatus();
