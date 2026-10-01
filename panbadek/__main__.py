"""Czat z Panem Badkiem: python -m panbadek (terminal) albo --web (przeglądarka)."""

import argparse
import sys

from . import __version__
from .brain import PanBadek

KONIEC = {"koniec", "wyjdz", "wyjdź", "exit", "quit"}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--trener":
        # python3 -m panbadek --trener [--zapisz --szybko --egzamin --nauczyciel]
        from . import trener
        return trener.main(sys.argv[2:])
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
    parser.add_argument("--telefon", action="store_true",
                        help="z --web: udostępnij czat telefonom w tej samej sieci Wi-Fi")
    parser.add_argument("--otworz", action="store_true",
                        help="z --web: od razu otwórz czat w przeglądarce")
    parser.add_argument("--skrot", nargs="?", const="", metavar="KATALOG",
                        help="utwórz skrót do Pana Badka na pulpicie (albo we wskazanym katalogu)")
    parser.add_argument("--eksport", metavar="PLIK",
                        help="zapisz całą wyuczoną pamięć do pliku JSON (np. żeby przenieść ją na telefon)")
    parser.add_argument("--import", dest="import_", metavar="PLIK",
                        help="dołącz pamięć z pliku JSON (z telefonu albo innego komputera)")
    parser.add_argument("--trener", action="store_true",
                        help="trenuj i sprawdź Badka (szczegóły: python3 -m panbadek --trener --help)")
    parser.add_argument("--version", action="version", version=f"Pan Badek {__version__}")
    args = parser.parse_args()

    if args.skrot is not None:
        from .brain import DOMYSLNA_PAMIEC
        from .skrot import utworz_skrot
        try:
            pliki = utworz_skrot(DOMYSLNA_PAMIEC, args.skrot or None)
        except Exception as e:
            raise SystemExit(f"Nie udało się utworzyć skrótu: {e}")
        print("Utworzono skrót:\n" + "\n".join(f"  {p}" for p in pliki))
        return

    if args.eksport or args.import_:
        import json
        badek = PanBadek(internet=False)
        if args.import_:
            with open(args.import_, encoding="utf-8") as f:
                print(badek.importuj(json.load(f)))
        if args.eksport:
            with open(args.eksport, "w", encoding="utf-8") as f:
                json.dump(badek.eksport(), f, ensure_ascii=False)
            print(f"Zapisano pamięć do {args.eksport}")
        return

    if args.web:
        from .web import juz_dziala
        if juz_dziala(args.port):
            # Drugie kliknięcie skrótu: Badek już działa, więc tylko otwieramy okno.
            print(f"Pan Badek już działa na http://127.0.0.1:{args.port}")
            if args.otworz:
                import webbrowser
                webbrowser.open(f"http://127.0.0.1:{args.port}")
            return

    print("Pan Badek: Ładuję neurony...")
    opcje = {"internet": not args.offline}
    if args.bez_pamieci:
        opcje["katalog_pamieci"] = None
    badek = PanBadek(**opcje)
    for blad in badek.bledy_wtyczek:
        print(f"  [wtyczka nie załadowana: {blad}]")

    if args.web:
        from .web import uruchom
        uruchom(badek, host="0.0.0.0" if args.telefon else "127.0.0.1", port=args.port,
                otworz=args.otworz)
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
