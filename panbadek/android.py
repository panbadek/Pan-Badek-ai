"""Start Pana Badka w aplikacji na Androida.

Aplikacja (android/) uruchamia Pythona przez Chaquopy, wywołuje uruchom()
i pokazuje czat z lokalnego serwera w WebView - ten sam co w przeglądarce.
"""

import os
import threading

from .brain import PanBadek
from .web import stworz_serwer

PORT = 8765
_serwer = None
_blokada = threading.Lock()


def uruchom(katalog_aplikacji):
    """Startuje mózg i serwer czatu (tylko raz na proces). Zwraca numer portu."""
    global _serwer
    with _blokada:
        if _serwer is None:
            badek = PanBadek(katalog_pamieci=os.path.join(katalog_aplikacji, "panbadek"))
            try:
                serwer = stworz_serwer(badek, "127.0.0.1", PORT)
            except OSError:
                serwer = stworz_serwer(badek, "127.0.0.1", 0)  # port zajęty - dowolny wolny
            threading.Thread(target=serwer.serve_forever, daemon=True).start()
            _serwer = serwer
        return _serwer.server_address[1]
