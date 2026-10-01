"""Czat z Panem Badkiem: python -m panbadek (terminal) albo --web (przeglądarka)."""

import argparse

from . import __version__
from .brain import PanBadek

KONIEC = {"koniec", "wyjdz", "wyjdź", "exit", "quit"}


def main():
    parser = argparse.ArgumentParser(prog="panbadek", description="Porozmawiaj z Panem Badkiem.")
    parser.add_argument("--debug", action="store_true",
                        help="pokazuj rozpoznaną intencję i pewność sieci")
    parser.add_argument("--bez-pamieci", action="store_true",
                        help="nie zapisuj niczego na dysku")
    parser.add_argument("--offline", action="store_true",
                        help="nie korzystaj z internetu")
    parser.add_argument("--web", action="store_true",
                        help="uruchom czat w przeglądarce zamiast w terminalu")
    parser.add_argument("--port", type=int, default=8000, help="port dla --web (domyślnie 8000)")
    parser.add_argument("--version", action="version", version=f"Pan Badek {__version__}")
    args = parser.parse_args()

    print("Pan Badek: Ładuję neurony...")
    opcje = {"internet": not args.offline}
    if args.bez_pamieci:
        opcje["katalog_pamieci"] = None
    badek = PanBadek(**opcje)
    for blad in badek.bledy_wtyczek:
        print(f"  [wtyczka nie załadowana: {blad}]")

    if args.web:
        from .web import uruchom
        uruchom(badek, port=args.port)
        return

    try:
        import readline  # noqa: F401 - strzałki i historia w terminalu
    except ImportError:
        pass

    print("Pan Badek: Cześć! Napisz coś (albo 'koniec', żeby wyjść).")
    while True:
        try:
            tekst = input("Ty: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if tekst.strip().lower() in KONIEC:
            break
        if args.debug:
            intencja, pewnosc = badek.klasyfikuj(tekst)
            if intencja:
                print(f"  [intencja: {intencja['nazwa']}, pewność: {pewnosc:.0%}]")
        print("Pan Badek:", badek.odpowiedz(tekst))

    print("Pan Badek: Do zobaczenia!")


if __name__ == "__main__":
    main()
