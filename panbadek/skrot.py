"""Skrót do Pana Badka na pulpicie i w menu programów (Windows, macOS, Linux).

Kliknięcie skrótu uruchamia czat w przeglądarce. Jeśli Pan Badek już działa,
skrót tylko otwiera jego okno.
"""

import os
import platform
import shlex
import stat
import subprocess
import sys

from . import ikona

NAZWA = "Pan Badek"
OPIS = "Twoja własna sztuczna inteligencja"


def katalog_projektu():
    """Katalog, z którego da się zaimportować pakiet panbadek."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pulpit():
    """Ścieżka do pulpitu, z uwzględnieniem polskiej nazwy 'Pulpit'."""
    try:
        wynik = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True,
                               timeout=5)
        if wynik.returncode == 0 and os.path.isdir(wynik.stdout.strip()):
            return wynik.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    dom = os.path.expanduser("~")
    for nazwa in ("Desktop", "Pulpit", os.path.join("OneDrive", "Desktop"),
                  os.path.join("OneDrive", "Pulpit")):
        if os.path.isdir(os.path.join(dom, nazwa)):
            return os.path.join(dom, nazwa)
    return None


def _python_bez_konsoli():
    """Na Windows pythonw.exe uruchamia program bez czarnego okna konsoli."""
    sciezka = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return sciezka if os.path.exists(sciezka) else sys.executable


def _zapisz(sciezka, tresc, wykonywalny=False):
    with open(sciezka, "w", encoding="utf-8", newline="\n" if wykonywalny else None) as f:
        f.write(tresc)
    if wykonywalny:
        os.chmod(sciezka, os.stat(sciezka).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return sciezka


def _windows(katalog_docelowy, katalog_pamieci):
    ikona_ico = os.path.join(katalog_pamieci, "ikona.ico")
    with open(ikona_ico, "wb") as f:
        f.write(ikona.ico(256))
    skrypt = os.path.join(katalog_pamieci, "uruchom_pana_badka.vbs")
    # VBScript uruchamia Pythona bez okna konsoli; skrót .url nie umie uruchomić programu,
    # więc tworzymy skrót .lnk przez wbudowany w Windows WScript.Shell.
    _zapisz(skrypt, (
        'Set sh = CreateObject("WScript.Shell")\r\n'
        f'sh.CurrentDirectory = "{katalog_projektu()}"\r\n'
        f'sh.Run """{_python_bez_konsoli()}"" -m panbadek --web --otworz", 0, False\r\n'))
    skrot = os.path.join(katalog_docelowy, f"{NAZWA}.lnk")
    polecenie = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:PB_SKROT);"
        "$s.TargetPath = 'wscript.exe'; $s.Arguments = '\"' + $env:PB_SKRYPT + '\"';"
        "$s.Description = $env:PB_OPIS; $s.IconLocation = $env:PB_IKONA; $s.Save()")
    srodowisko = dict(os.environ, PB_SKROT=skrot, PB_SKRYPT=skrypt, PB_OPIS=OPIS,
                      PB_IKONA=ikona_ico)
    subprocess.run(["powershell", "-NoProfile", "-Command", polecenie], check=True,
                   env=srodowisko, capture_output=True, timeout=30)
    return [skrot]


def _macos(katalog_docelowy, katalog_pamieci):
    skrot = os.path.join(katalog_docelowy, f"{NAZWA}.command")
    return [_zapisz(skrot, (
        "#!/bin/sh\n"
        f"cd {shlex.quote(katalog_projektu())}\n"
        f"exec {shlex.quote(sys.executable)} -m panbadek --web --otworz\n"), wykonywalny=True)]


def _linux(katalog_docelowy, katalog_pamieci):
    ikona_png = ikona.zapisz(os.path.join(katalog_pamieci, "ikona.png"), 256)
    exec_ = (f"sh -c 'cd {shlex.quote(katalog_projektu())} && "
             f"exec {shlex.quote(sys.executable)} -m panbadek --web --otworz'")
    wpis = ("[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={NAZWA}\n"
            f"Comment={OPIS}\n"
            f"Exec={exec_}\n"
            f"Icon={ikona_png}\n"
            "Terminal=false\n"
            "Categories=Utility;Education;\n")
    menu = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
    os.makedirs(menu, exist_ok=True)
    utworzone = [_zapisz(os.path.join(menu, "panbadek.desktop"), wpis, wykonywalny=True)]
    if katalog_docelowy:
        sciezka = _zapisz(os.path.join(katalog_docelowy, "panbadek.desktop"), wpis, wykonywalny=True)
        # GNOME wymaga oznaczenia skrótu na pulpicie jako zaufanego.
        try:
            subprocess.run(["gio", "set", sciezka, "metadata::trusted", "true"],
                           capture_output=True, check=False, timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
        utworzone.append(sciezka)
    return utworzone


def utworz_skrot(katalog_pamieci, katalog_docelowy=None, system=None):
    """Tworzy skrót i zwraca listę utworzonych plików."""
    system = system or platform.system()
    os.makedirs(katalog_pamieci, exist_ok=True)
    katalog_docelowy = katalog_docelowy or pulpit()
    if system == "Linux":
        return _linux(katalog_docelowy, katalog_pamieci)
    if not katalog_docelowy:
        raise RuntimeError("Nie znalazłem pulpitu. Podaj katalog: --skrot KATALOG")
    if system == "Windows":
        return _windows(katalog_docelowy, katalog_pamieci)
    if system == "Darwin":
        return _macos(katalog_docelowy, katalog_pamieci)
    raise RuntimeError(f"Nie umiem jeszcze tworzyć skrótów w systemie {system}.")
