const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [wejscie, wyjscie] = process.argv.slice(2);
  const kategorie = JSON.parse(fs.readFileSync(wejscie, 'utf8'));
  const b = await chromium.launch({ proxy: { server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost' }, args: ['--ignore-certificate-errors'] });
  const p = await b.newPage();
  p.on('console', m => console.log('[strona]', m.text()));
  await p.goto('about:blank');
  const wynik = await p.evaluate(async (kategorie) => {
    const T = await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.0');
    const id = 'Xenova/mobileclip_s0';
    const tok = await T.AutoTokenizer.from_pretrained(id);
    const model = await T.CLIPTextModelWithProjection.from_pretrained(id, { dtype: 'fp32', device: 'wasm' });
    // Kilka szablonów zdań na kategorię i uśrednienie - stara sztuczka z pracy o CLIP.
    const szablony = ['a photo of {}.', 'a picture of {}.', 'a close-up photo of {}.', 'a blurry photo of {}.'];
    const wektory = [];
    for (const [, en] of kategorie) {
      const zdania = szablony.map(s => s.replace('{}', en));
      const wej = tok(zdania, { padding: 'max_length', truncation: true });
      const { text_embeds } = await model(wej);
      const d = text_embeds.dims[1], dane = text_embeds.data, sr = new Float32Array(d);
      for (let i = 0; i < zdania.length; i++) {
        let n = 0; for (let j = 0; j < d; j++) n += dane[i * d + j] ** 2; n = Math.sqrt(n);
        for (let j = 0; j < d; j++) sr[j] += dane[i * d + j] / n;
      }
      let n = 0; for (let j = 0; j < d; j++) n += sr[j] ** 2; n = Math.sqrt(n);
      wektory.push(Array.from(sr, v => v / n));
    }
    return wektory;
  }, kategorie);
  // Zapisujemy jako int8 (×127) w base64 - plik jest kilkanaście razy mniejszy niż JSON z liczbami.
  const d = wynik[0].length, bufor = Buffer.alloc(wynik.length * d);
  wynik.forEach((w, i) => w.forEach((v, j) => bufor.writeInt8(Math.max(-127, Math.min(127, Math.round(v * 127))), i * d + j)));
  fs.writeFileSync(wyjscie, JSON.stringify({ model: 'Xenova/mobileclip_s0', wymiar: d,
    etykiety: kategorie.map(k => k[0]), wektory: bufor.toString('base64') }));
  console.log('zapisano', wynik.length, 'kategorii, wymiar', d);
  await b.close();
})();
