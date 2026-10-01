package pl.panbadek.app;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import com.chaquo.python.PyException;
import com.chaquo.python.Python;

/**
 * Okno aplikacji: uruchamia Pana Badka (Python) w tle i pokazuje jego czat w WebView.
 */
public class MainActivity extends Activity {

    private static final String EKRAN_STARTOWY =
        "<!doctype html><html><head><meta name='viewport' content='width=device-width'>"
        + "<style>body{margin:0;height:100vh;display:flex;flex-direction:column;align-items:center;"
        + "justify-content:center;font:18px system-ui,sans-serif;background:#f4f5f7;color:#1d2330}"
        + "@media(prefers-color-scheme:dark){body{background:#15181e;color:#e6e9ef}}"
        + ".r{font-size:64px;animation:p 1.2s ease-in-out infinite}"
        + "@keyframes p{50%{transform:scale(1.15)}}</style></head>"
        + "<body><div class='r'>🤖</div><p>Pan Badek ładuje neurony…</p></body></html>";

    private static final int WYBOR_ZDJECIA = 1;

    private WebView web;
    private ValueCallback<Uri[]> czekaNaZdjecie;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        web = new WebView(this);
        WebSettings ustawienia = web.getSettings();
        ustawienia.setJavaScriptEnabled(true);
        ustawienia.setDomStorageEnabled(true);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri adres = request.getUrl();
                if ("127.0.0.1".equals(adres.getHost())) {
                    return false;
                }
                // Linki do internetu (np. Wikipedia) otwieramy w zwykłej przeglądarce.
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, adres));
                } catch (ActivityNotFoundException ignored) {
                }
                return true;
            }
        });
        // Przycisk 📷 w czacie otwiera systemowy wybór zdjęcia (galeria, pliki, aparat).
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                             FileChooserParams parametry) {
                if (czekaNaZdjecie != null) {
                    czekaNaZdjecie.onReceiveValue(null);
                }
                czekaNaZdjecie = callback;
                try {
                    startActivityForResult(parametry.createIntent(), WYBOR_ZDJECIA);
                } catch (ActivityNotFoundException e) {
                    czekaNaZdjecie = null;
                    return false;
                }
                return true;
            }
        });
        setContentView(web);
        web.loadDataWithBaseURL(null, EKRAN_STARTOWY, "text/html", "utf-8", null);

        final String katalog = getFilesDir().getAbsolutePath();
        new Thread(() -> {
            try {
                int port = Python.getInstance().getModule("panbadek.android")
                    .callAttr("uruchom", katalog).toInt();
                runOnUiThread(() -> web.loadUrl("http://127.0.0.1:" + port + "/"));
            } catch (PyException e) {
                String blad = android.text.TextUtils.htmlEncode(String.valueOf(e.getMessage()));
                runOnUiThread(() -> web.loadDataWithBaseURL(null,
                    "<h3>Pan Badek nie wystartował</h3><pre style='white-space:pre-wrap'>"
                        + blad + "</pre>", "text/html", "utf-8", null));
            }
        }, "pan-badek-start").start();
    }

    @Override
    protected void onActivityResult(int kod, int wynik, Intent dane) {
        if (kod == WYBOR_ZDJECIA && czekaNaZdjecie != null) {
            czekaNaZdjecie.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(wynik, dane));
            czekaNaZdjecie = null;
            return;
        }
        super.onActivityResult(kod, wynik, dane);
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
