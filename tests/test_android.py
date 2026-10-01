"""Test startu Pana Badka tak, jak robi to aplikacja na Androida."""

import json
import tempfile
import unittest
import urllib.request

from panbadek import android


class TestAndroid(unittest.TestCase):
    def test_uruchom_startuje_serwer_tylko_raz(self):
        with tempfile.TemporaryDirectory() as katalog:
            port = android.uruchom(katalog)
            try:
                self.assertEqual(android.uruchom(katalog), port)
                bez_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                zapytanie = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/czat", data=json.dumps({"tekst": "2+2"}).encode())
                with bez_proxy.open(zapytanie) as odp:
                    self.assertEqual(json.load(odp)["odpowiedz"], "2+2 = 4")
            finally:
                android._serwer.shutdown()
                android._serwer.server_close()
                android._serwer = None


if __name__ == "__main__":
    unittest.main()
