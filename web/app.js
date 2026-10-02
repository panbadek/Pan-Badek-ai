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

// Bezpieczny Markdown: najpierw cały tekst jest escapowany, potem dokładamy tylko
// znaczniki, które tworzymy sami (pogrubienie, kursywa, kod, listy, nagłówki, linki).
function escapuj(tekst) {
  const d = document.createElement("div");
  d.textContent = tekst;
  return d.innerHTML;
}

function wLinii(tekst) {
  return tekst
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s.,;:!?)]|$)/g, "$1<i>$2</i>")
    .replace(/(https?:\/\/[^\s<]+[^\s<.,;:!?)\]])/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
}

function markdown(tekst) {
  // split z dwiema grupami: [tekst, język, kod, tekst, język, kod, ...]
  const czesci = escapuj(tekst).split(/```([a-zA-Z0-9+#-]*)\n?([\s\S]*?)(?:```|$)/);
  let html = "";
  czesci.forEach((czesc, i) => {
    if (i % 3 === 1) return;
    if (i % 3 === 2) {
      const jezyk = { cpp: "C++", "c++": "C++", cc: "C++", py: "Python", js: "JavaScript" }[czesci[i - 1].toLowerCase()]
        || czesci[i - 1] || "kod";
      html += `<div class="kod"><div class="kod-pasek"><span>${jezyk}</span>`
        + `<button type="button" class="kopiuj-kod">📋 Kopiuj</button></div>`
        + `<pre><code>${czesc.replace(/\n$/, "")}</code></pre></div>`;
      return;
    }
    let lista = null;
    const zamknij = () => { if (lista) { html += `</${lista}>`; lista = null; } };
    for (const linia of czesc.split("\n")) {
      const punkt = linia.match(/^\s*(?:[-*•]|(\d+)[.)])\s+(.*)$/);
      const naglowek = linia.match(/^(#{1,4})\s+(.*)$/);
      if (punkt) {
        const typ = punkt[1] ? "ol" : "ul";
        if (lista !== typ) { zamknij(); html += `<${typ}>`; lista = typ; }
        html += `<li>${wLinii(punkt[2])}</li>`;
      } else if (naglowek) {
        zamknij();
        html += `<h4>${wLinii(naglowek[2])}</h4>`;
      } else {
        zamknij();
        html += linia.trim() ? `<p>${wLinii(linia)}</p>` : "";
      }
    }
    zamknij();
  });
  return html;
}

// Przycisk "Kopiuj" nad każdym blokiem kodu (jeden nasłuchiwacz dla całego czatu).
czat.addEventListener("click", async (e) => {
  const przycisk = e.target.closest(".kopiuj-kod");
  if (!przycisk) return;
  const kod = przycisk.closest(".kod").querySelector("code").textContent;
  try { await navigator.clipboard.writeText(kod); przycisk.textContent = "✓ Skopiowano"; }
  catch { przycisk.textContent = "✗ Nie udało się"; }
  setTimeout(() => { przycisk.textContent = "📋 Kopiuj"; }, 1500);
});

function przewin() {
  czat.scrollTop = czat.scrollHeight;
}

function dodaj(tekst, kto, podpis) {
  $("powitanie")?.remove();
  const d = document.createElement("div");
  d.className = "msg " + kto;
  if (kto.startsWith("ty")) {
    d.textContent = tekst;
  } else {
    d.innerHTML = '<div class="tresc"></div><div class="akcje"></div>';
    aktualizuj(d, tekst);
    dodajKopiowanie(d);
  }
  if (podpis) ustawPodpis(d, podpis);
  czat.appendChild(d);
  przewin();
  return d;
}

function ustawPodpis(dymek, podpis) {
  const p = document.createElement("span");
  p.className = "podpis" + (podpis.startsWith("🧠") ? " ai" : "");
  p.textContent = podpis;
  (dymek.querySelector(".akcje") || dymek).appendChild(p);
}

function aktualizuj(dymek, tekst) {
  dymek.dataset.tekst = tekst;
  const tresc = dymek.querySelector(".tresc") || dymek;
  tresc.innerHTML = tekst ? markdown(tekst) : '<span class="kropki"><i></i><i></i><i></i></span>';
  przewin();
}

function dodajKopiowanie(dymek) {
  const przycisk = document.createElement("button");
  przycisk.type = "button"; przycisk.className = "akcja"; przycisk.textContent = "📋";
  przycisk.title = "Kopiuj odpowiedź"; przycisk.setAttribute("aria-label", "Kopiuj odpowiedź");
  przycisk.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(dymek.dataset.tekst || ""); przycisk.textContent = "✓"; }
    catch { przycisk.textContent = "✗"; }
    setTimeout(() => { przycisk.textContent = "📋"; }, 1500);
  });
  dymek.querySelector(".akcje").appendChild(przycisk);
}

// Rozwijany "tok rozumowania" przy trudnych problemach.
function pokazMysli(dymek, mysli) {
  let d = dymek.querySelector("details.mysli");
  if (!d) {
    d = document.createElement("details");
    d.className = "mysli";
    d.innerHTML = "<summary>💭 Tok rozumowania</summary><div></div>";
    dymek.insertBefore(d, dymek.firstChild);
  }
  d.querySelector("div").innerHTML = markdown(mysli);
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
  return [
    "Jesteś Pan Badek - pomocny, szczery i życzliwy asystent AI w aplikacji na telefonie.",
    imie ? `Rozmówca ma na imię ${imie}.` : "",
    "Zasady:",
    "- Odpowiadaj po polsku. Najpierw konkretna odpowiedź, potem krótkie wyjaśnienie, jeśli pomaga.",
    "- Zwykle 1-5 zdań; dłużej tylko przy złożonych problemach albo gdy ktoś prosi o szczegóły.",
    "- Przy trudnych problemach (matematyka, logika, kod, planowanie) rozumuj krok po kroku i pokaż kluczowe kroki.",
    "- Gdy pytanie jest niejasne, zadaj jedno krótkie pytanie doprecyzowujące zamiast zgadywać.",
    "- Nie zmyślaj. Jeśli czegoś nie wiesz albo nie masz pewności, powiedz to wprost.",
    "- Formatuj Markdownem (pogrubienia, listy, bloki kodu), gdy to zwiększa czytelność.",
    "- Bądź ciepły, ale bez przesadnych zachwytów i bez schlebiania.",
    "- W sprawach zdrowia, prawa i pieniędzy podawaj rzetelne informacje i zachęcaj do konsultacji ze specjalistą.",
    "- Jeśli ktoś jest w kryzysie, okaż troskę i podaj numery 116 123, 800 70 2222 albo 112.",
    "- Gdy odpowiedź wymaga połączenia kilku faktów albo wzorów, wypisz krótko, z których korzystasz, i pokaż, jak je łączysz.",
    "- Po obliczeniach sprawdź wynik (podstaw go z powrotem albo oszacuj rząd wielkości) i pokaż to sprawdzenie.",
    "- Zadania szkolne rozwiązuj jak w zeszycie: **Dane**, **Szukane**, **Wzór**, **Rozwiązanie** krok po kroku",
    "  (z jednostkami), **Odpowiedź** pełnym zdaniem. Tłumacz jak cierpliwy korepetytor. Gdy uczeń prosi",
    "  o podpowiedź albo sprawdzenie, nie podawaj od razu całego rozwiązania - naprowadź go.",
    "- Programowanie (szczególnie C++): pisz kompletny, kompilujący się kod w nowoczesnym C++17/20 w bloku ```cpp,",
    "  z potrzebnymi #include, std:: zamiast 'using namespace std', kontenerami STL, RAII i inteligentnymi",
    "  wskaźnikami zamiast new/delete, sprawdzaniem danych wejściowych i krótkimi komentarzami po polsku.",
    "  Po kodzie: jak skompilować (g++ -std=c++17 -Wall plik.cpp -o program) i 1-3 zdania o kluczowych decyzjach.",
    "  Przy szukaniu błędów najpierw wskaż przyczynę, potem poprawiony fragment.",
    "Aplikacja ma też własne polecenia, które możesz podpowiadać: 'pogoda w <mieście>', 'kurs <waluta>',",
    "'co to jest <hasło>', 'rozwiąż <równanie>', 'pochodna <funkcja>', 'napisz w C++ <temat>', analiza zdjęć (📷),",
    "zadanie ze zdjęcia (📝), 'obejrzyj <link do YouTube>', 'naucz się z tekstu: <tekst>',",
    "'naucz się: pytanie => odpowiedź'.",
  ].filter(Boolean).join("\n");
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

async function claudeStrumien(wiadomosci, naTekst, glebokie, naMysli) {
  const klient = await klientClaude();
  const strumien = klient.beta.messages.stream({
    model: MODEL_CLAUDE,
    max_tokens: glebokie ? 32000 : 16000,
    // Gdy filtr bezpieczeństwa odmówi, API samo powtórzy zapytanie na zalecanym modelu zapasowym.
    betas: ["server-side-fallback-2026-07-01"],
    fallbacks: "default",
    // Zwykła rozmowa: szybko i tanio. Trudny problem: dłuższe myślenie z widocznym streszczeniem.
    output_config: { effort: glebokie ? "high" : "low" },
    ...(glebokie ? { thinking: { type: "adaptive", display: "summarized" } } : {}),
    system: instrukcja(),
    messages: wiadomosci,
  });
  let tekst = "", mysli = "";
  for await (const zdarzenie of strumien) {
    if (zdarzenie.type !== "content_block_delta") continue;
    if (zdarzenie.delta.type === "text_delta") {
      tekst += zdarzenie.delta.text;
      naTekst(tekst);
    } else if (zdarzenie.delta.type === "thinking_delta" && naMysli) {
      mysli += zdarzenie.delta.thinking;
      naMysli(mysli);
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

async function lokalnyStrumien(wiadomosci, naTekst, glebokie, naMysli) {
  const odpowiedz = await silnik.chat.completions.create({
    messages: [{ role: "system", content: instrukcja() }, ...wiadomosci],
    stream: true,
    temperature: glebokie ? 0.6 : 0.7,
    // Qwen "myśli na głos" tylko przy trudnych problemach - zwykła rozmowa ma być szybka.
    extra_body: { enable_thinking: !!glebokie },
  });
  let tekst = "";
  for await (const kawalek of odpowiedz) {
    tekst += kawalek.choices[0]?.delta?.content || "";
    const mysli = tekst.match(/<think>([\s\S]*?)(<\/think>|$)/);
    if (mysli && naMysli) naMysli(mysli[1].trim());
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

async function odpowiedzAI(rodzaj, wiadomosci, zapasowa, glebokie = false, dymek = null) {
  const nazwa = rodzaj === "claude" ? "Claude" : nazwaModeluLokalnego();
  const podpis = `🧠 ${nazwa}${rodzaj === "claude" ? "" : " (w telefonie)"}${glebokie ? " · głębokie myślenie" : ""}`;
  dymek = dymek || dodaj("", "badek pisze");
  dymek.classList.add("pisze");
  aktualizuj(dymek, "");
  if (glebokie) pokazMysli(dymek, "*Myślę nad tym krok po kroku…*");
  try {
    const naTekst = (t) => aktualizuj(dymek, t);
    const naMysli = (m) => pokazMysli(dymek, m);
    const tekst = rodzaj === "claude"
      ? await claudeStrumien(wiadomosci, naTekst, glebokie, naMysli)
      : await lokalnyStrumien(wiadomosci, naTekst, glebokie, naMysli);
    dymek.classList.remove("pisze");
    aktualizuj(dymek, tekst || zapasowa);
    if (glebokie && dymek.querySelector(".mysli div").textContent.startsWith("Myślę nad tym")) {
      dymek.querySelector(".mysli").remove(); // model nie pokazał streszczenia myśli
    }
    ustawPodpis(dymek, podpis);
    dodajPonow(dymek, rodzaj, wiadomosci, zapasowa, glebokie);
    return { tekst, dymek, nazwa };
  } catch (e) {
    dymek.classList.remove("pisze");
    aktualizuj(dymek, zapasowa || "");
    ustawPodpis(dymek, rodzaj === "claude" ? opisBleduClaude(e) : "Model w telefonie zgłosił błąd: " + e.message);
    return { tekst: null, dymek };
  }
}

// 🔄 - ta sama rozmowa, nowa odpowiedź (jak "spróbuj ponownie").
function dodajPonow(dymek, rodzaj, wiadomosci, zapasowa, glebokie) {
  const przycisk = document.createElement("button");
  przycisk.type = "button"; przycisk.className = "akcja"; przycisk.textContent = "🔄";
  przycisk.title = "Odpowiedz jeszcze raz"; przycisk.setAttribute("aria-label", "Odpowiedz jeszcze raz");
  przycisk.addEventListener("click", async () => {
    dymek.querySelector(".akcje").innerHTML = "";
    dymek.querySelector(".mysli")?.remove();
    dodajKopiowanie(dymek);
    const ai = await odpowiedzAI(rodzaj, wiadomosci, zapasowa, glebokie, dymek);
    if (ai.tekst && historia.length && historia[historia.length - 1].role === "assistant") {
      historia[historia.length - 1].content = ai.tekst;
    }
  });
  dymek.querySelector(".akcje").appendChild(przycisk);
}

// --- oceny 👍/👎: Badek uczy się na nich ---------------------------------------------

const OCENIANE = ["siec_neuronowa", "wiedza", "biblioteka", "internet", "ai"];

function dodajOceny(dymek, idOdpowiedzi) {
  const oceny = document.createElement("span");
  oceny.className = "oceny";
  for (const [znak, dobra, opis] of [["👍", true, "Dobra odpowiedź"], ["👎", false, "Zła odpowiedź"]]) {
    const przycisk = document.createElement("button");
    przycisk.type = "button"; przycisk.className = "akcja";
    przycisk.textContent = znak; przycisk.title = opis; przycisk.setAttribute("aria-label", opis);
    przycisk.addEventListener("click", async () => {
      oceny.remove();
      const wynik = await zapytajBadka({ typ: "ocena", id_odpowiedzi: idOdpowiedzi, dobra });
      ustawPodpis(dymek, (dobra ? "👍 " : "👎 ") + wynik.odpowiedz);
    });
    oceny.appendChild(przycisk);
  }
  dymek.querySelector(".akcje").appendChild(oceny);
}

// --- rozmowa ----------------------------------------------------------------------

async function wyslijTekst(tekst) {
  dodaj(tekst, "ty");
  const dymek = dodaj("", "badek pisze");
  const wynik = await zapytajBadka({ typ: "czat", tekst });
  imie = wynik.imie ?? imie;
  const rodzaj = aktywneAI();
  const pogawedka = ["siec_neuronowa", "biblioteka"].includes(wynik.zrodlo);
  // Kod z gotowego wzoru Badka: Claude napisze go dokładnie pod prośbę (wzór zostaje zapasową odpowiedzią).
  // Mały model w telefonie pisze gorszy kod niż sprawdzone wzory, więc wtedy zostaje wzór.
  const kodAI = wynik.zrodlo === "programowanie" && rodzaj === "claude" && ust.kiedy === "zawsze";
  // Złożony problem, którego Badek sam nie rozwiązał (np. dowód, kod, plan) -> głębokie myślenie AI.
  const glebokie = !!wynik.trudne
    && (["nie_wiem", "siec_neuronowa", "biblioteka", "internet"].includes(wynik.zrodlo) || kodAI);
  zapamietaj("user", tekst);
  if (rodzaj && (wynik.zrodlo === "nie_wiem" || (ust.kiedy === "zawsze" && pogawedka) || kodAI || glebokie)) {
    const ai = await odpowiedzAI(rodzaj, historiaDlaModelu(), wynik.odpowiedz, glebokie, dymek);
    zapamietaj("assistant", ai.tekst || wynik.odpowiedz);
    if (ai.tekst && ust.uczSie) {
      // Badek zapamiętuje odpowiedź dużego modelu - na podobne pytanie odpowie potem sam.
      const nauka = await zapytajBadka({ typ: "naucz_od_ai", pytanie: tekst, odpowiedz: ai.tekst, zrodlo: ai.nazwa });
      if (nauka.zapamietane) ai.dymek.querySelector(".podpis").textContent += " · Badek zapamiętał";
      dodajOceny(ai.dymek, nauka.id_odpowiedzi);
    }
  } else {
    dymek.classList.remove("pisze");
    aktualizuj(dymek, wynik.odpowiedz);
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
  pole.placeholder = PODPOWIEDZ_POLA;
  dopasujPole();
  wyslijTekst(tekst);
});

// Pole tekstowe rośnie razem z wiadomością; Enter wysyła, Shift+Enter robi nową linię.
function dopasujPole() {
  pole.style.height = "auto";
  pole.style.height = Math.min(pole.scrollHeight, 160) + "px";
}
pole.addEventListener("input", dopasujPole);
pole.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    $("f").requestSubmit();
  }
});

// Podpowiedzi na start.
for (const przycisk of document.querySelectorAll("#powitanie [data-pytanie]")) {
  przycisk.addEventListener("click", () => {
    if (!badekGotowy) return;
    if (przycisk.dataset.pytanie === "📷") { $("plik").click(); return; }
    if (przycisk.dataset.pytanie === "📝") { trybZadania = true; $("plik").click(); return; }
    if (przycisk.dataset.pytanie === "📺") {
      pole.value = "obejrzyj "; pole.focus(); dopasujPole();
      pole.placeholder = "Wklej link do filmu z YouTube…";
      return;
    }
    wyslijTekst(przycisk.dataset.pytanie);
  });
}

// Nowa rozmowa: czyści ekran i kontekst dla AI (pamięć Badka zostaje).
$("nowa").addEventListener("click", () => {
  historia.length = 0;
  czat.innerHTML = "";
  dodaj("Zaczynamy od nowa. W czym mogę pomóc?", "badek");
  pole.focus();
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
  $("powitanie")?.remove();
  dymek.appendChild(img); czat.appendChild(dymek); przewin();
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

// Zadanie ze zdjęcia: po podpowiedzi „📝” albo gdy w polu tekstowym jest prośba
// („rozwiąż zadanie 3”) - wtedy zdjęcie zeszytu trafia do Claude zamiast do analizy kolorów.
let trybZadania = false;
const PODPOWIEDZ_POLA = pole.placeholder;
const PROSBA_O_ZADANIE = /zadani|rozwi|oblicz|policz|sprawd|pom[oó][zż]|wyt[lł]umacz|wyja[sś]nij|jak zrobi/i;

$("aparat").addEventListener("click", () => $("plik").click());
$("plik").addEventListener("change", (e) => {
  const plik = e.target.files[0];
  e.target.value = "";
  if (!plik || !badekGotowy) { trybZadania = false; return; }
  const polecenie = pole.value.trim();
  if (trybZadania || PROSBA_O_ZADANIE.test(polecenie)) {
    pole.value = ""; dopasujPole();
    zadanieZeZdjecia(plik, polecenie);
  } else {
    wyslijZdjecie(plik);
  }
  trybZadania = false;
});

async function zadanieZeZdjecia(plik, polecenie) {
  const adres = URL.createObjectURL(plik);
  const dymek = document.createElement("div");
  dymek.className = "msg ty foto";
  const img = document.createElement("img");
  img.src = adres; img.alt = "Zdjęcie zadania";
  $("powitanie")?.remove();
  dymek.appendChild(img);
  if (polecenie) { const p = document.createElement("div"); p.textContent = polecenie; dymek.appendChild(p); }
  czat.appendChild(dymek); przewin();
  try {
    await img.decode();
  } catch {
    dodaj("Nie udało się odczytać tego zdjęcia. Spróbuj JPEG albo PNG.", "badek");
    return;
  }
  if (aktywneAI() !== "claude") {
    dodaj("Do zadań ze zdjęcia potrzebuję Claude (⚙️ → mózg: Claude), bo sam nie umiem czytać pisma " +
      "ze zdjęć. Możesz też **przepisać treść zadania** - zadania z fizyki, geometrii, procentów " +
      "i zadania z treścią rozwiążę sam, krok po kroku.", "badek");
    return;
  }
  const jpeg = pomniejsz(img, ROZMIAR_DLA_CLAUDE).toDataURL("image/jpeg", 0.9).split(",")[1];
  const prosba = (polecenie ? `Uczeń prosi: „${polecenie}”.\n` : "") +
    "To zdjęcie zadania szkolnego (zeszyt, podręcznik albo karta pracy). Najpierw przepisz treść zadania, " +
    "a potem rozwiąż je jak w zeszycie: **Dane**, **Szukane**, **Wzór** (jeśli jest), **Rozwiązanie** krok po kroku, " +
    "**Odpowiedź** pełnym zdaniem. Jeśli na zdjęciu jest kilka zadań, a uczeń nie wskazał które, rozwiąż pierwsze " +
    "i zapytaj o resztę. Jeśli czegoś nie da się odczytać, powiedz to wprost zamiast zgadywać.";
  const wiadomosc = { role: "user", content: [
    { type: "image", source: { type: "base64", media_type: "image/jpeg", data: jpeg } },
    { type: "text", text: prosba },
  ] };
  const ai = await odpowiedzAI("claude", [...historiaDlaModelu(), wiadomosc], "", true);
  zapamietaj("user", "(Wysłałem zdjęcie zadania" + (polecenie ? `: ${polecenie}` : "") + ".)");
  if (ai.tekst) zapamietaj("assistant", ai.tekst);
}

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
