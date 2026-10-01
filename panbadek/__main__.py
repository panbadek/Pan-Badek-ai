"""Czat z Panem Badkiem w terminalu: python -m panbadek"""

import argparse

from .brain import PanBadek

KONIEC = {"koniec", "wyjdz", "wyjdź", "exit", "quit"}


def main():
    parser = argparse.ArgumentParser(description="Porozmawiaj z Panem Badkiem.")
    parser.add_argument("--debug", action="store_true",
                        help="pokazuj rozpoznaną intencję i pewność sieci")
    parser.add_argument("--bez-pamieci", action="store_true",
                        help="nie zapisuj niczego na dysku")
    args = parser.parse_args()

    print("Pan Badek: Ładuję neurony...")
    badek = PanBadek(katalog_pamieci=None) if args.bez_pamieci else PanBadek()
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
