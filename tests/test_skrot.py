"""Testy ikony, aplikacji na ekran główny (PWA) i skrótów na pulpit."""

import json
import os
import struct
import tempfile
import threading
import unittest
import urllib.request
from unittest import mock

from panbadek import PanBadek, ikona, skrot
from panbadek.web import juz_dziala, stworz_serwer


class TestIkona(unittest.TestCase):
    def test_png(self):
        dane = ikona.png(64)
        self.assertTrue(dane.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack(">II", dane[16:24]), (64, 64))

    def test_ico_zawiera_png(self):
        dane = ikona.ico(256)
        self.assertEqual(struct.unpack("<HHH", dane[:6]), (0, 1, 1))
        self.assertEqual(dane[22:30], b"\x89PNG\r\n\x1a\n")


class TestAplikacjaNaTelefon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        badek = PanBadek(katalog_pamieci=None, ziarno=0, internet=False)
        cls.serwer = stworz_serwer(badek, port=0)
        threading.Thread(target=cls.serwer.serve_forever, daemon=True).start()
        cls.port = cls.serwer.server_address[1]
        cls.bez_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.serwer.shutdown()
        cls.serwer.server_close()

    def pobierz(self, sciezka):
        with self.bez_proxy.open(f"http://127.0.0.1:{self.port}{sciezka}") as odp:
            return odp.headers["Content-Type"], odp.read()

    def test_strona_wskazuje_manifest_i_ikony(self):
        _, html = self.pobierz("/")
        self.assertIn(b'rel="manifest"', html)
        self.assertIn(b'rel="apple-touch-icon"', html)
        self.assertIn(b"serviceWorker", html)

    def test_manifest(self):
        typ, dane = self.pobierz("/manifest.webmanifest")
        self.assertIn("manifest+json", typ)
        manifest = json.loads(dane)
        self.assertEqual(manifest["display"], "standalone")
        rozmiary = {i["sizes"] for i in manifest["icons"]}
        self.assertTrue({"192x192", "512x512"} <= rozmiary)
        for sciezka in {i["src"] for i in manifest["icons"]}:
            typ, png = self.pobierz(sciezka)
            self.assertEqual(typ, "image/png")
            self.assertTrue(png.startswith(b"\x89PNG"))

    def test_service_worker_i_ikona_apple(self):
        typ, _ = self.pobierz("/sw.js")
        self.assertIn("javascript", typ)
        _, png = self.pobierz("/apple-touch-icon.png")
        self.assertEqual(struct.unpack(">II", png[16:24]), (180, 180))

    def test_wykrywa_dzialajacego_badka(self):
        self.assertTrue(juz_dziala(self.port))


class TestSkrotNaPulpit(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dom = tmp.name
        self.pulpit = os.path.join(self.dom, "Pulpit")
        os.makedirs(self.pulpit)
        self.pamiec = os.path.join(self.dom, ".panbadek")
        lata = mock.patch.dict(os.environ, {"HOME": self.dom, "USERPROFILE": self.dom})
        lata.start()
        self.addCleanup(lata.stop)

    def test_znajduje_polski_pulpit(self):
        with mock.patch.object(skrot.subprocess, "run", side_effect=OSError):
            self.assertEqual(skrot.pulpit(), self.pulpit)

    def test_linux(self):
        pliki = skrot.utworz_skrot(self.pamiec, self.pulpit, system="Linux")
        self.assertEqual(len(pliki), 2)
        with open(pliki[0], encoding="utf-8") as f:
            wpis = f.read()
        self.assertIn("Name=Pan Badek", wpis)
        self.assertIn("-m panbadek --web --otworz", wpis)
        self.assertTrue(os.path.exists(os.path.join(self.pamiec, "ikona.png")))
        self.assertTrue(os.access(pliki[1], os.X_OK))

    def test_macos(self):
        (plik,) = skrot.utworz_skrot(self.pamiec, self.pulpit, system="Darwin")
        self.assertTrue(plik.endswith("Pan Badek.command"))
        self.assertTrue(os.access(plik, os.X_OK))

    def test_windows(self):
        with mock.patch.object(skrot.subprocess, "run") as run:
            (plik,) = skrot.utworz_skrot(self.pamiec, self.pulpit, system="Windows")
        self.assertTrue(plik.endswith("Pan Badek.lnk"))
        srodowisko = run.call_args.kwargs["env"]
        self.assertEqual(srodowisko["PB_SKROT"], plik)
        self.assertTrue(srodowisko["PB_IKONA"].endswith("ikona.ico"))
        with open(srodowisko["PB_SKRYPT"], encoding="utf-8") as f:
            self.assertIn("-m panbadek --web --otworz", f.read())


if __name__ == "__main__":
    unittest.main()
