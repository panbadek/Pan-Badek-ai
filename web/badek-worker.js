// Pan Badek w przeglądarce: Python (Pyodide) uruchomiony w Web Workerze, żeby strona się nie zacinała.
// Pamięć Badka (imię, nauczone odpowiedzi, biblioteki, zdjęcia) trzymamy w IndexedDB przez IDBFS.

importScripts("https://cdn.jsdelivr.net/pyodide/v0.28.3/full/pyodide.js");

const PAMIEC = "/home/pyodide/.panbadek";
let py, most;

function zapiszPamiec() {
  return new Promise((ok) => py.FS.syncfs(false, () => ok()));
}

async function start() {
  postMessage({ typ: "postep", tekst: "Ładuję Pythona…" });
  py = await loadPyodide();

  postMessage({ typ: "postep", tekst: "Ładuję mózg Pana Badka…" });
  const kod = await (await fetch("panbadek.zip")).arrayBuffer();
  py.unpackArchive(kod, "zip", { extractDir: "/home/pyodide/app" });

  py.FS.mkdirTree(PAMIEC);
  py.FS.mount(py.FS.filesystems.IDBFS, {}, PAMIEC);
  await new Promise((ok, blad) => py.FS.syncfs(true, (e) => (e ? blad(e) : ok())));

  // Sieć neuronowa wytrenowana przy budowaniu strony - telefon nie musi trenować jej sam,
  // także po aktualizacji, gdy model zapisany w pamięci jest już nieaktualny.
  const GOTOWY = "/home/pyodide/gotowy_model.json";
  const model = await fetch("model.json").catch(() => null);
  if (model?.ok) py.FS.writeFile(GOTOWY, new Uint8Array(await model.arrayBuffer()));

  py.runPython('import sys; sys.path.insert(0, "/home/pyodide/app")');
  most = py.pyimport("panbadek.przegladarka");
  const stan = JSON.parse(most.start(PAMIEC, model?.ok ? GOTOWY : null));
  await zapiszPamiec();
  postMessage({ typ: "gotowy", ...stan });
}

const gotowy = start().catch((e) => postMessage({ typ: "blad_startu", tekst: String(e) }));

onmessage = async ({ data }) => {
  await gotowy;
  let wynik;
  try {
    if (data.typ === "czat") {
      wynik = JSON.parse(most.czat(data.tekst));
    } else if (data.typ === "zdjecie") {
      wynik = JSON.parse(most.zdjecie(data.szer, data.wys, data.oryg_szer, data.oryg_wys,
                                      data.piksele, data.naglowek));
    } else if (data.typ === "naucz_od_ai") {
      wynik = JSON.parse(most.naucz_od_ai(data.pytanie, data.odpowiedz, data.zrodlo));
    } else if (data.typ === "ocena") {
      wynik = JSON.parse(most.ocena(data.id_odpowiedzi, data.dobra));
    } else if (data.typ === "eksport") {
      wynik = { dane: most.eksport() };
    } else if (data.typ === "import") {
      wynik = JSON.parse(most.import_(data.dane));
    }
    await zapiszPamiec();
  } catch (e) {
    wynik = { odpowiedz: "Ups, coś mi się pomieszało w głowie: " + e.message.split("\n").slice(-2).join(" "),
              zrodlo: "blad" };
  }
  // Pola "typ" i "id" na końcu - wynik z Pythona nie może ich nadpisać.
  postMessage({ ...wynik, typ: "wynik", id: data.id });
};
