"""Pan Badek pisze w C++ - gotowe, sprawdzone programy, które działają bez internetu.

Każdy wzór to kompletny program (C++17), który kompiluje się bez ostrzeżeń
(`g++ -std=c++17 -Wall -Wextra`). Wzór wybierany jest po słowach kluczowych,
a niektóre dostają liczbę z pytania (np. "liczby pierwsze do 500").
Bardziej nietypowe zamówienia Badek oddaje Claude albo modelowi w telefonie.
"""

import re

from .text import normalizuj

KOMPILACJA = "g++ -std=c++17 -Wall -O2 program.cpp -o program"

# "c++", "cpp", "c plus plus", "cplusplus", "c ++"
_CPP = re.compile(r"(?<![a-z0-9])(c\s?\+\+|cpp|c\s*plus\s*plus|cplusplus)(?![a-z0-9])")
_PROSBA = re.compile(r"(napisz|napisac|pokaz|daj|zrob|stworz|utworz|przyklad|kod|program|"
                     r"jak\s+(?:sie\s+)?(?:w|napisac|zrobic|uzyc|uzywac|dziala|wyglada)|"
                     r"implementacj|zaimplementuj|funkcj|klas)")
_LICZBA = re.compile(r"\b(\d{1,7})\b")


def _wzor(tytul, slowa, kod, opis, liczba=None):
    return {"tytul": tytul, "slowa": slowa, "kod": kod.strip("\n") + "\n", "opis": opis, "liczba": liczba}


# Słowa kluczowe są już znormalizowane (bez polskich znaków, małe litery);
# dopasowanie po początku słowa, więc "sortow" łapie "sortowanie" i "sortowania".
# Spacja na końcu ("gra ") wymaga całego słowa, żeby "gra" nie łapało "grafu".
WZORY = [
    _wzor("Hello world", ["hello", "witaj swiecie", "pierwszy program", "najprostszy", "podstaw"], r"""
#include <iostream>

int main() {
    std::cout << "Witaj, świecie!\n";
    return 0;
}
""", "Każdy program w C++ zaczyna się od funkcji `main`. `std::cout` wypisuje tekst na ekran, "
         "a `#include <iostream>` dołącza bibliotekę wejścia-wyjścia."),

    _wzor("Wczytywanie danych od użytkownika", ["wczyt", "pobier", "cin", "imie", "input", "wejsci", "podaj"], r"""
#include <iostream>
#include <string>

int main() {
    std::string imie;
    int wiek = 0;

    std::cout << "Jak masz na imię? ";
    std::getline(std::cin, imie);          // cała linia, także ze spacjami

    std::cout << "Ile masz lat? ";
    if (!(std::cin >> wiek)) {             // sprawdzamy, czy podano liczbę
        std::cerr << "To nie jest liczba.\n";
        return 1;
    }

    std::cout << "Cześć, " << imie << "! Za 10 lat będziesz mieć " << wiek + 10 << " lat.\n";
    return 0;
}
""", "`std::getline` wczytuje całą linię tekstu, a `std::cin >> zmienna` pojedynczą wartość. "
         "Warunek `if (!(std::cin >> wiek))` chroni przed wpisaniem liter zamiast liczby."),

    _wzor("Kalkulator", ["kalkulator", "dzialani", "dodawan", "odejmowan", "mnozen", "dzielen", "switch"], r"""
#include <iostream>

int main() {
    double a = 0, b = 0;
    char dzialanie = '+';

    std::cout << "Podaj działanie (np. 3 * 4): ";
    if (!(std::cin >> a >> dzialanie >> b)) {
        std::cerr << "Niepoprawne dane.\n";
        return 1;
    }

    switch (dzialanie) {
        case '+': std::cout << "Wynik: " << a + b << '\n'; break;
        case '-': std::cout << "Wynik: " << a - b << '\n'; break;
        case '*': std::cout << "Wynik: " << a * b << '\n'; break;
        case '/':
            if (b == 0) {
                std::cerr << "Nie można dzielić przez zero.\n";
                return 1;
            }
            std::cout << "Wynik: " << a / b << '\n';
            break;
        default:
            std::cerr << "Nieznane działanie: " << dzialanie << '\n';
            return 1;
    }
    return 0;
}
""", "`switch` wybiera działanie po znaku. Przed dzieleniem sprawdzamy, czy dzielnik nie jest zerem."),

    _wzor("Tabliczka mnożenia (pętle)", ["tabliczk", "petl", "for ", "while", "powtarz"], r"""
#include <iomanip>
#include <iostream>

int main() {
    const int n = {n};

    // Pętla zewnętrzna: wiersze, wewnętrzna: kolumny.
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            std::cout << std::setw(5) << i * j;
        }
        std::cout << '\n';
    }

    // To samo zadanie pętlą while: suma liczb od 1 do n.
    int i = 1, suma = 0;
    while (i <= n) {
        suma += i;
        ++i;
    }
    std::cout << "Suma liczb od 1 do " << n << " = " << suma << '\n';
    return 0;
}
""", "Pętla `for` jest wygodna, gdy znamy liczbę powtórzeń, a `while` - gdy powtarzamy, "
         "dopóki spełniony jest warunek. `std::setw` wyrównuje kolumny.", liczba=(10, 1, 30)),

    _wzor("Liczba parzysta czy nieparzysta (if/else)", ["parzyst", "nieparzyst", "if ", "else", "warun"], r"""
#include <iostream>

int main() {
    long long liczba = 0;
    std::cout << "Podaj liczbę całkowitą: ";
    std::cin >> liczba;

    if (liczba % 2 == 0) {
        std::cout << liczba << " jest parzysta.\n";
    } else {
        std::cout << liczba << " jest nieparzysta.\n";
    }

    if (liczba > 0) {
        std::cout << "Jest dodatnia.\n";
    } else if (liczba < 0) {
        std::cout << "Jest ujemna.\n";
    } else {
        std::cout << "To zero.\n";
    }
    return 0;
}
""", "Operator `%` daje resztę z dzielenia: liczba parzysta ma resztę 0 przy dzieleniu przez 2."),

    _wzor("Silnia (rekurencja i pętla)", ["silni", "rekurencj", "rekurenc"], r"""
#include <cstdint>
#include <iostream>

// Wersja rekurencyjna: n! = n * (n-1)!
std::uint64_t silniaRekurencyjnie(unsigned n) {
    if (n <= 1) return 1;                  // warunek zakończenia
    return n * silniaRekurencyjnie(n - 1);
}

// Wersja iteracyjna - bez ryzyka przepełnienia stosu.
std::uint64_t silniaPetla(unsigned n) {
    std::uint64_t wynik = 1;
    for (unsigned i = 2; i <= n; ++i) wynik *= i;
    return wynik;
}

int main() {
    const unsigned n = {n};                // uint64_t mieści silnię do 20!
    std::cout << n << "! = " << silniaRekurencyjnie(n) << '\n';
    std::cout << n << "! = " << silniaPetla(n) << " (pętla)\n";
    return 0;
}
""", "Rekurencja to funkcja wywołująca samą siebie; zawsze potrzebuje warunku zakończenia "
         "(`n <= 1`). Typ `std::uint64_t` mieści wyniki do 20!.", liczba=(10, 0, 20)),

    _wzor("Ciąg Fibonacciego", ["fibonacc", "fibonaci"], r"""
#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    const int n = {n};                     // ile wyrazów (do 93 mieści się w uint64_t)

    std::vector<std::uint64_t> fib(n + 1, 0);
    if (n >= 1) fib[1] = 1;
    for (int i = 2; i <= n; ++i) {
        fib[i] = fib[i - 1] + fib[i - 2];  // każdy wyraz to suma dwóch poprzednich
    }

    for (int i = 0; i <= n; ++i) {
        std::cout << "F(" << i << ") = " << fib[i] << '\n';
    }
    return 0;
}
""", "Liczymy iteracyjnie i zapamiętujemy wyniki w wektorze - to szybkie O(n), "
         "w przeciwieństwie do naiwnej rekurencji, która działa wykładniczo wolno.", liczba=(20, 1, 93)),

    _wzor("Liczby pierwsze (sito Eratostenesa)", ["pierwsz", "sito", "eratosten"], r"""
#include <iostream>
#include <vector>

int main() {
    const int n = {n};

    // pierwsza[i] == true, dopóki nie znajdziemy dzielnika i
    std::vector<bool> pierwsza(n + 1, true);
    pierwsza[0] = false;
    if (n >= 1) pierwsza[1] = false;

    for (long long i = 2; i * i <= n; ++i) {
        if (!pierwsza[i]) continue;
        for (long long j = i * i; j <= n; j += i) {
            pierwsza[j] = false;           // wielokrotności i nie są pierwsze
        }
    }

    int ile = 0;
    for (int i = 2; i <= n; ++i) {
        if (pierwsza[i]) {
            std::cout << i << ' ';
            ++ile;
        }
    }
    std::cout << "\nLiczb pierwszych do " << n << ": " << ile << '\n';
    return 0;
}
""", "Sito Eratostenesa skreśla wielokrotności kolejnych liczb pierwszych. Złożoność O(n log log n), "
         "więc bez problemu działa dla milionów liczb.", liczba=(100, 2, 10000000)),

    _wzor("Sortowanie", ["sort", "posortuj", "babelk", "rosnac", "malejac", "quicksort"], r"""
#include <algorithm>
#include <functional>
#include <iostream>
#include <vector>

// Sortowanie bąbelkowe - proste, dobre do nauki, ale wolne: O(n^2).
void sortowanieBabelkowe(std::vector<int>& t) {
    for (std::size_t i = 0; i + 1 < t.size(); ++i) {
        bool zamiana = false;
        for (std::size_t j = 0; j + 1 < t.size() - i; ++j) {
            if (t[j] > t[j + 1]) {
                std::swap(t[j], t[j + 1]);
                zamiana = true;
            }
        }
        if (!zamiana) break;               // już posortowane
    }
}

void wypisz(const std::vector<int>& t) {
    for (int x : t) std::cout << x << ' ';
    std::cout << '\n';
}

int main() {
    std::vector<int> liczby = {5, 3, 9, 1, 7, 2, 8};

    std::vector<int> a = liczby;
    sortowanieBabelkowe(a);
    std::cout << "Bąbelkowo: ";
    wypisz(a);

    // W prawdziwym kodzie używaj std::sort - O(n log n).
    std::vector<int> b = liczby;
    std::sort(b.begin(), b.end());
    std::cout << "std::sort: ";
    wypisz(b);

    std::sort(b.begin(), b.end(), std::greater<int>());
    std::cout << "Malejąco: ";
    wypisz(b);
    return 0;
}
""", "Sortowanie bąbelkowe zamienia sąsiednie elementy w złej kolejności. W praktyce używaj `std::sort` "
         "(O(n log n)); trzeci argument, np. `std::greater<int>()`, zmienia porządek."),

    _wzor("Wyszukiwanie binarne", ["binarn", "wyszukiw", "szukani", "znajdz element", "przeszukiw"], r"""
#include <algorithm>
#include <iostream>
#include <vector>

// Zwraca indeks szukanej wartości albo -1. Tablica musi być posortowana.
int szukajBinarnie(const std::vector<int>& t, int szukana) {
    int lewo = 0, prawo = static_cast<int>(t.size()) - 1;
    while (lewo <= prawo) {
        int srodek = lewo + (prawo - lewo) / 2;   // bez przepełnienia
        if (t[srodek] == szukana) return srodek;
        if (t[srodek] < szukana) lewo = srodek + 1;
        else prawo = srodek - 1;
    }
    return -1;
}

int main() {
    std::vector<int> t = {1, 3, 4, 7, 9, 12, 15, 20};
    int szukana = 12;

    int indeks = szukajBinarnie(t, szukana);
    if (indeks >= 0) std::cout << "Znaleziono " << szukana << " na pozycji " << indeks << '\n';
    else std::cout << "Nie ma " << szukana << '\n';

    // To samo z biblioteki standardowej:
    std::cout << "std::binary_search: " << std::boolalpha
              << std::binary_search(t.begin(), t.end(), szukana) << '\n';
    return 0;
}
""", "Wyszukiwanie binarne za każdym razem odrzuca połowę tablicy, więc działa w O(log n). "
         "Warunek: dane muszą być posortowane."),

    _wzor("NWD i NWW (algorytm Euklidesa)", ["nwd", "nww", "euklides", "najwiekszy wspolny", "najmniejsza wspolna"], r"""
#include <iostream>
#include <numeric>

long long nwd(long long a, long long b) {
    while (b != 0) {
        long long r = a % b;
        a = b;
        b = r;
    }
    return a;
}

long long nww(long long a, long long b) {
    return a / nwd(a, b) * b;              // najpierw dzielimy, żeby uniknąć przepełnienia
}

int main() {
    long long a = 48, b = 18;
    std::cout << "NWD(" << a << ", " << b << ") = " << nwd(a, b) << '\n';
    std::cout << "NWW(" << a << ", " << b << ") = " << nww(a, b) << '\n';

    // Od C++17 są gotowe funkcje w <numeric>:
    std::cout << "std::gcd = " << std::gcd(a, b) << ", std::lcm = " << std::lcm(a, b) << '\n';
    return 0;
}
""", "Algorytm Euklidesa zastępuje parę (a, b) parą (b, a mod b), aż reszta wyniesie 0. "
         "NWW = a / NWD · b."),

    _wzor("Tablica / wektor: suma, średnia, minimum, maksimum",
          ["tablic", "wektor", "vector", "sredni", "najwieksz", "najmniejsz", "maksim", "minim", "suma"], r"""
#include <algorithm>
#include <iostream>
#include <numeric>
#include <vector>

int main() {
    std::vector<double> liczby;
    double x = 0;

    std::cout << "Podaj liczby (zakończ literą, np. k): ";
    while (std::cin >> x) {
        liczby.push_back(x);               // wektor sam się powiększa
    }
    if (liczby.empty()) {
        std::cout << "Nie podano żadnej liczby.\n";
        return 0;
    }

    double suma = std::accumulate(liczby.begin(), liczby.end(), 0.0);
    auto [mn, mx] = std::minmax_element(liczby.begin(), liczby.end());

    std::cout << "Ilość: " << liczby.size() << '\n'
              << "Suma: " << suma << '\n'
              << "Średnia: " << suma / liczby.size() << '\n'
              << "Minimum: " << *mn << '\n'
              << "Maksimum: " << *mx << '\n';
    return 0;
}
""", "`std::vector` to tablica, która rośnie sama (`push_back`). `std::accumulate` sumuje, "
         "a `std::minmax_element` jednym przejściem znajduje minimum i maksimum."),

    _wzor("Napisy: odwracanie i palindrom", ["palindrom", "odwr", "napisy", "napisow", "lancuch", "string", "tekst", "liter"], r"""
#include <algorithm>
#include <cctype>
#include <iostream>
#include <string>

bool czyPalindrom(const std::string& s) {
    std::string litery;
    for (unsigned char c : s) {
        if (std::isalnum(c)) litery += static_cast<char>(std::tolower(c));  // bez spacji i wielkości liter
    }
    return std::equal(litery.begin(), litery.begin() + litery.size() / 2, litery.rbegin());
}

int main() {
    std::string tekst;
    std::cout << "Podaj tekst: ";
    std::getline(std::cin, tekst);

    std::string odwrocony(tekst.rbegin(), tekst.rend());
    std::cout << "Odwrócony: " << odwrocony << '\n';
    std::cout << "Długość: " << tekst.size() << " bajtów\n";
    std::cout << (czyPalindrom(tekst) ? "To palindrom!\n" : "To nie jest palindrom.\n");
    return 0;
}
""", "`std::string` przechowuje tekst; `rbegin()`/`rend()` przechodzą go od końca. Uwaga: polskie "
         "litery w UTF-8 zajmują po 2 bajty, więc `size()` liczy bajty, a odwracanie bajtów je psuje - "
         "do pełnej obsługi polskich znaków użyj `std::u32string` albo biblioteki ICU."),

    _wzor("Zliczanie słów (std::map)", ["map ", "mapa", "mapy", "slownik", "zlicz", "czestotliw", "ile razy", "slow", "slowa", "liczy slow", "policz slow"], r"""
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <unordered_map>

int main() {
    std::string tekst = "ala ma kota a kot ma ale ala lubi kota";

    std::map<std::string, int> licznik;    // klucze posortowane alfabetycznie
    std::istringstream strumien(tekst);
    std::string slowo;
    while (strumien >> slowo) {
        ++licznik[slowo];                  // brakujący klucz dostaje 0, potem +1
    }

    for (const auto& [klucz, ile] : licznik) {
        std::cout << klucz << ": " << ile << '\n';
    }

    // unordered_map - bez kolejności, ale szybsze wyszukiwanie (średnio O(1)).
    std::unordered_map<std::string, int> szybki(licznik.begin(), licznik.end());
    std::cout << "\"kota\" występuje " << szybki["kota"] << " razy\n";
    return 0;
}
""", "`std::map` trzyma pary klucz-wartość posortowane po kluczu (O(log n)), a `std::unordered_map` "
         "używa haszowania (średnio O(1)). `for (const auto& [klucz, ile] : ...)` to C++17."),

    _wzor("Klasa (konto bankowe)", ["klas", "obiekt", "konto", "bank", "enkapsulacj", "konstruktor", "oop"], r"""
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>

class KontoBankowe {
public:
    KontoBankowe(std::string wlasciciel, double saldo = 0.0)
        : wlasciciel_(std::move(wlasciciel)), saldo_(saldo) {}

    void wplac(double kwota) {
        if (kwota <= 0) throw std::invalid_argument("Kwota musi być dodatnia");
        saldo_ += kwota;
    }

    void wyplac(double kwota) {
        if (kwota > saldo_) throw std::runtime_error("Za mało środków");
        saldo_ -= kwota;
    }

    double saldo() const { return saldo_; }
    const std::string& wlasciciel() const { return wlasciciel_; }

private:                                   // dane ukryte - zmieniają je tylko metody
    std::string wlasciciel_;
    double saldo_;
};

int main() {
    KontoBankowe konto("Ania", 100.0);
    konto.wplac(50.0);

    try {
        konto.wyplac(500.0);
    } catch (const std::exception& e) {
        std::cout << "Błąd: " << e.what() << '\n';
    }

    std::cout << konto.wlasciciel() << " ma " << konto.saldo() << " zł\n";
    return 0;
}
""", "Klasa łączy dane (pola `private`) z operacjami (metody `public`). Konstruktor ustawia stan "
         "początkowy, a metody pilnują, żeby saldo nie było błędne (enkapsulacja)."),

    _wzor("Struktura (struct) i lista uczniów", ["struct", "struktur", "uczni", "student", "rekord"], r"""
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

struct Uczen {
    std::string imie;
    double srednia;
};

int main() {
    std::vector<Uczen> klasa = {
        {"Ola", 4.8},
        {"Kuba", 3.9},
        {"Zosia", 5.2},
    };

    // Sortujemy malejąco po średniej - lambda jako porównanie.
    std::sort(klasa.begin(), klasa.end(),
              [](const Uczen& a, const Uczen& b) { return a.srednia > b.srednia; });

    for (const auto& u : klasa) {
        std::cout << u.imie << ": " << u.srednia << '\n';
    }
    return 0;
}
""", "`struct` grupuje powiązane dane (domyślnie wszystko jest publiczne). Wektor struktur "
         "sortujemy `std::sort` z lambdą, która mówi, który element jest „mniejszy”."),

    _wzor("Pliki: zapis i odczyt", ["plik", "fstream", "zapis", "odczyt", "txt"], r"""
#include <fstream>
#include <iostream>
#include <string>

int main() {
    const std::string nazwa = "notatki.txt";

    {   // zapis - plik zamyka się sam na końcu bloku
        std::ofstream wyjscie(nazwa);
        if (!wyjscie) {
            std::cerr << "Nie mogę otworzyć pliku do zapisu.\n";
            return 1;
        }
        wyjscie << "Pierwsza linia\n" << "Druga linia\n";
    }

    {   // dopisywanie na końcu
        std::ofstream dopisz(nazwa, std::ios::app);
        dopisz << "Trzecia linia (dopisana)\n";
    }

    std::ifstream wejscie(nazwa);
    if (!wejscie) {
        std::cerr << "Nie mogę otworzyć pliku do odczytu.\n";
        return 1;
    }
    std::string linia;
    int numer = 1;
    while (std::getline(wejscie, linia)) {
        std::cout << numer++ << ": " << linia << '\n';
    }
    return 0;
}
""", "`std::ofstream` zapisuje, `std::ifstream` czyta, a `std::ios::app` dopisuje na końcu. "
         "Pliki zamykają się automatycznie, gdy obiekt wychodzi z zakresu (RAII)."),

    _wzor("Dziedziczenie i polimorfizm", ["dziedzicz", "polimorf", "wirtualn", "virtual", "override", "abstrakc"], r"""
#include <iostream>
#include <memory>
#include <vector>

class Figura {                             // klasa bazowa (abstrakcyjna)
public:
    virtual ~Figura() = default;           // wirtualny destruktor - zawsze w klasie bazowej
    virtual double pole() const = 0;       // metoda czysto wirtualna
    virtual const char* nazwa() const = 0;
};

class Prostokat : public Figura {
public:
    Prostokat(double a, double b) : a_(a), b_(b) {}
    double pole() const override { return a_ * b_; }
    const char* nazwa() const override { return "prostokąt"; }
private:
    double a_, b_;
};

class Kolo : public Figura {
public:
    explicit Kolo(double r) : r_(r) {}
    double pole() const override { return 3.14159265358979 * r_ * r_; }
    const char* nazwa() const override { return "koło"; }
private:
    double r_;
};

int main() {
    std::vector<std::unique_ptr<Figura>> figury;
    figury.push_back(std::make_unique<Prostokat>(3, 4));
    figury.push_back(std::make_unique<Kolo>(2));

    for (const auto& f : figury) {         // ta sama pętla, różne zachowanie
        std::cout << f->nazwa() << ": pole = " << f->pole() << '\n';
    }
    return 0;
}
""", "Klasy pochodne nadpisują (`override`) metody wirtualne klasy bazowej. Przez wskaźnik na `Figura` "
         "wywoła się właściwa wersja - to polimorfizm. `std::unique_ptr` sam zwalnia pamięć."),

    _wzor("Wskaźniki i referencje", ["wskaznik", "pointer", "referencj", "adres", "new ", "delete", "pamiec"], r"""
#include <iostream>
#include <memory>

void zwiekszPrzezWartosc(int x) { x += 1; }     // zmienia kopię
void zwiekszPrzezReferencje(int& x) { x += 1; } // zmienia oryginał
void zwiekszPrzezWskaznik(int* x) {
    if (x) *x += 1;                             // * - wartość pod adresem
}

int main() {
    int liczba = 10;
    int* wsk = &liczba;                         // & - adres zmiennej
    int& ref = liczba;                          // referencja = druga nazwa tej samej zmiennej

    std::cout << "adres: " << wsk << ", wartość: " << *wsk << '\n';
    ref = 20;
    std::cout << "po zmianie przez referencję: " << liczba << '\n';

    zwiekszPrzezWartosc(liczba);
    zwiekszPrzezReferencje(liczba);
    zwiekszPrzezWskaznik(&liczba);
    std::cout << "po funkcjach: " << liczba << '\n';  // 22

    // Pamięć dynamiczna: zamiast new/delete używaj inteligentnych wskaźników.
    auto tablica = std::make_unique<int[]>(5);
    for (int i = 0; i < 5; ++i) tablica[i] = i * i;
    std::cout << "tablica[4] = " << tablica[4] << '\n';
    return 0;                                   // unique_ptr zwolni pamięć sam
}
""", "Wskaźnik przechowuje adres (`&x`), a `*wsk` daje wartość pod nim; może być pusty (`nullptr`). "
         "Referencja to stała „druga nazwa” zmiennej i nie może być pusta. Zamiast gołych `new`/`delete` "
         "używaj `std::unique_ptr` i `std::make_unique`."),

    _wzor("Stos i kolejka", ["stos", "stack", "kolejk", "queue", "fifo", "lifo"], r"""
#include <iostream>
#include <queue>
#include <stack>

int main() {
    std::stack<int> stos;                  // LIFO: ostatni wchodzi, pierwszy wychodzi
    std::queue<int> kolejka;               // FIFO: pierwszy wchodzi, pierwszy wychodzi

    for (int i = 1; i <= 3; ++i) {
        stos.push(i);
        kolejka.push(i);
    }

    std::cout << "Stos: ";
    while (!stos.empty()) {
        std::cout << stos.top() << ' ';    // 3 2 1
        stos.pop();
    }

    std::cout << "\nKolejka: ";
    while (!kolejka.empty()) {
        std::cout << kolejka.front() << ' '; // 1 2 3
        kolejka.pop();
    }
    std::cout << '\n';
    return 0;
}
""", "Stos (`std::stack`) oddaje elementy w odwrotnej kolejności, kolejka (`std::queue`) w tej samej. "
         "Stos przydaje się np. do cofania operacji, kolejka do obsługi zadań po kolei."),

    _wzor("Lista jednokierunkowa", ["lista", "linked", "jednokierunk", "wezel", "wezl"], r"""
#include <iostream>
#include <memory>

struct Wezel {
    int wartosc;
    std::unique_ptr<Wezel> nastepny;
};

class Lista {
public:
    void dodajNaPoczatek(int x) {
        auto nowy = std::make_unique<Wezel>();
        nowy->wartosc = x;
        nowy->nastepny = std::move(glowa_);
        glowa_ = std::move(nowy);
    }

    bool usun(int x) {
        std::unique_ptr<Wezel>* biezacy = &glowa_;
        while (*biezacy) {
            if ((*biezacy)->wartosc == x) {
                *biezacy = std::move((*biezacy)->nastepny);
                return true;
            }
            biezacy = &(*biezacy)->nastepny;
        }
        return false;
    }

    void wypisz() const {
        for (const Wezel* w = glowa_.get(); w; w = w->nastepny.get()) {
            std::cout << w->wartosc << " -> ";
        }
        std::cout << "nullptr\n";
    }

private:
    std::unique_ptr<Wezel> glowa_;
};

int main() {
    Lista lista;
    for (int x : {4, 3, 2, 1}) lista.dodajNaPoczatek(x);
    lista.wypisz();                        // 1 -> 2 -> 3 -> 4 -> nullptr
    lista.usun(3);
    lista.wypisz();                        // 1 -> 2 -> 4 -> nullptr
    return 0;
}
""", "Każdy węzeł zna tylko następny. Dzięki `std::unique_ptr` pamięć zwalnia się sama. "
         "W praktyce zwykle wystarczy `std::vector` albo `std::list` z biblioteki standardowej."),

    _wzor("Gra: zgadnij liczbę", ["zgad", "gra ", "gre ", "gry ", "losow", "random"], r"""
#include <iostream>
#include <random>

int main() {
    std::random_device zrodlo;
    std::mt19937 generator(zrodlo());
    std::uniform_int_distribution<int> rozklad(1, {n});
    const int sekret = rozklad(generator);

    std::cout << "Zgadnij liczbę od 1 do {n}.\n";
    int proba = 0, liczbaProb = 0;
    while (true) {
        std::cout << "Twój typ: ";
        if (!(std::cin >> proba)) {
            std::cout << "Koniec gry.\n";
            return 0;
        }
        ++liczbaProb;
        if (proba < sekret) std::cout << "Za mało!\n";
        else if (proba > sekret) std::cout << "Za dużo!\n";
        else break;
    }
    std::cout << "Brawo! Zgadłeś w " << liczbaProb << " próbach.\n";
    return 0;
}
""", "Do losowania używaj `<random>` (`std::mt19937` i `std::uniform_int_distribution`) - "
         "stare `rand() % n` daje gorszy rozkład.", liczba=(100, 2, 1000000)),

    _wzor("Szablony funkcji i klas", ["szablon", "template", "generyczn"], r"""
#include <iostream>
#include <string>

// Jedna funkcja dla wielu typów - kompilator tworzy wersję dla każdego użytego typu.
template <typename T>
T wiekszy(const T& a, const T& b) {
    return a > b ? a : b;
}

template <typename T>
class Para {
public:
    Para(T pierwszy, T drugi) : pierwszy_(pierwszy), drugi_(drugi) {}
    T suma() const { return pierwszy_ + drugi_; }
private:
    T pierwszy_, drugi_;
};

int main() {
    std::cout << wiekszy(3, 7) << '\n';                                  // int
    std::cout << wiekszy(2.5, 1.5) << '\n';                              // double
    std::cout << wiekszy(std::string("kot"), std::string("pies")) << '\n';

    Para<int> p(2, 3);
    Para<std::string> s("Pan ", "Badek");
    std::cout << p.suma() << ", " << s.suma() << '\n';
    return 0;
}
""", "Szablony (`template <typename T>`) pozwalają napisać kod raz dla wielu typów. "
         "Na nich zbudowana jest cała biblioteka standardowa (`std::vector<T>`, `std::map<K, V>`)."),

    _wzor("Wyjątki (try/catch)", ["wyjat", "exception", "try", "catch", "throw", "bled"], r"""
#include <iostream>
#include <stdexcept>
#include <string>

double podziel(double a, double b) {
    if (b == 0) throw std::invalid_argument("dzielenie przez zero");
    return a / b;
}

int main() {
    try {
        std::cout << podziel(10, 2) << '\n';
        std::cout << podziel(1, 0) << '\n';      // rzuci wyjątek
        std::cout << "Tej linii nie zobaczysz.\n";
    } catch (const std::invalid_argument& e) {
        std::cerr << "Zły argument: " << e.what() << '\n';
    }

    try {
        int liczba = std::stoi("abc");           // też rzuca wyjątek
        std::cout << liczba << '\n';
    } catch (const std::exception& e) {          // łapie wszystkie standardowe wyjątki
        std::cerr << "Błąd konwersji: " << e.what() << '\n';
    }
    return 0;
}
""", "`throw` zgłasza błąd, a `catch` go obsługuje. Łap wyjątki przez stałą referencję "
         "(`const std::exception&`); bardziej szczegółowe typy umieszczaj przed ogólnymi."),

    _wzor("Inteligentne wskaźniki", ["inteligentn", "unique_ptr", "shared_ptr", "smart", "raii", "wyciek"], r"""
#include <iostream>
#include <memory>
#include <string>

struct Zasob {
    explicit Zasob(std::string n) : nazwa(std::move(n)) { std::cout << "Tworzę " << nazwa << '\n'; }
    ~Zasob() { std::cout << "Zwalniam " << nazwa << '\n'; }
    std::string nazwa;
};

int main() {
    {
        auto jeden = std::make_unique<Zasob>("unique");     // jedyny właściciel
        auto przeniesiony = std::move(jeden);               // własność można przenieść, nie skopiować
        std::cout << "jeden jest pusty: " << std::boolalpha << (jeden == nullptr) << '\n';
    }                                                        // tu "unique" jest zwalniany

    std::shared_ptr<Zasob> a = std::make_shared<Zasob>("shared");
    {
        std::shared_ptr<Zasob> b = a;                       // wspólna własność
        std::cout << "właścicieli: " << a.use_count() << '\n';  // 2
    }
    std::cout << "właścicieli: " << a.use_count() << '\n';      // 1
    return 0;                                                // tu "shared" jest zwalniany
}
""", "`std::unique_ptr` ma jednego właściciela i zwalnia obiekt automatycznie, `std::shared_ptr` "
         "liczy właścicieli. Dzięki nim (RAII) nie trzeba pisać `delete` i nie ma wycieków pamięci."),

    _wzor("Graf: przeszukiwanie wszerz (BFS)", ["graf", "bfs", "dfs", "wszerz", "najkrotsz", "sciezk"], r"""
#include <iostream>
#include <queue>
#include <vector>

int main() {
    const int n = 6;
    std::vector<std::vector<int>> sasiedzi(n);
    auto krawedz = [&](int a, int b) {
        sasiedzi[a].push_back(b);
        sasiedzi[b].push_back(a);
    };
    krawedz(0, 1); krawedz(0, 2); krawedz(1, 3); krawedz(2, 4); krawedz(4, 5);

    // BFS od wierzchołka 0: odległość = najmniejsza liczba krawędzi.
    std::vector<int> odleglosc(n, -1);
    std::queue<int> kolejka;
    odleglosc[0] = 0;
    kolejka.push(0);
    while (!kolejka.empty()) {
        int v = kolejka.front();
        kolejka.pop();
        for (int u : sasiedzi[v]) {
            if (odleglosc[u] == -1) {
                odleglosc[u] = odleglosc[v] + 1;
                kolejka.push(u);
            }
        }
    }

    for (int v = 0; v < n; ++v) {
        std::cout << "0 -> " << v << ": " << odleglosc[v] << " krawędzi\n";
    }
    return 0;
}
""", "Graf zapisany jest jako listy sąsiedztwa. BFS odwiedza wierzchołki warstwami (kolejka), więc "
         "znajduje najkrótsze ścieżki w grafie bez wag w czasie O(V + E). Dla wag użyj algorytmu Dijkstry."),

    _wzor("Macierze", ["macierz", "matrix", "mnozenie macierzy", "transpozycj"], r"""
#include <iostream>
#include <vector>

using Macierz = std::vector<std::vector<double>>;

Macierz pomnoz(const Macierz& A, const Macierz& B) {
    std::size_t n = A.size(), m = B[0].size(), k = B.size();
    Macierz C(n, std::vector<double>(m, 0.0));
    for (std::size_t i = 0; i < n; ++i)
        for (std::size_t p = 0; p < k; ++p)          // kolejność i-p-j jest przyjazna pamięci podręcznej
            for (std::size_t j = 0; j < m; ++j)
                C[i][j] += A[i][p] * B[p][j];
    return C;
}

void wypisz(const Macierz& M) {
    for (const auto& wiersz : M) {
        for (double x : wiersz) std::cout << x << '\t';
        std::cout << '\n';
    }
}

int main() {
    Macierz A = {{1, 2}, {3, 4}};
    Macierz B = {{5, 6}, {7, 8}};
    wypisz(pomnoz(A, B));                  // 19 22 / 43 50
    return 0;
}
""", "Macierz to wektor wektorów. Mnożenie wymaga, by liczba kolumn A równała się liczbie wierszy B. "
         "Do poważnych obliczeń użyj biblioteki Eigen."),

    _wzor("Funkcje i lambdy", ["lambd", "funkcj", "parametr", "przeciaz"], r"""
#include <algorithm>
#include <iostream>
#include <vector>

// Zwykła funkcja z parametrem domyślnym.
double pole(double a, double b = 1.0) {
    return a * b;
}

// Przeciążenie: ta sama nazwa, inne parametry.
int kwadrat(int x) { return x * x; }
double kwadrat(double x) { return x * x; }

int main() {
    std::cout << pole(3, 4) << ' ' << pole(5) << '\n';
    std::cout << kwadrat(3) << ' ' << kwadrat(1.5) << '\n';

    // Lambda: funkcja bez nazwy, może "przechwycić" zmienne z otoczenia.
    int prog = 5;
    std::vector<int> liczby = {1, 8, 3, 10, 6};
    auto ileWiekszych = std::count_if(liczby.begin(), liczby.end(),
                                      [prog](int x) { return x > prog; });
    std::cout << "Większych niż " << prog << ": " << ileWiekszych << '\n';

    auto dodaj = [](auto a, auto b) { return a + b; };  // lambda generyczna (C++14)
    std::cout << dodaj(2, 3) << ' ' << dodaj(1.5, 2.5) << '\n';
    return 0;
}
""", "Funkcje mogą mieć parametry domyślne i przeciążenia. Lambdy (`[przechwycenie](parametry) { ... }`) "
         "są wygodne jako krótkie funkcje przekazywane do algorytmów, np. `std::count_if`."),

    _wzor("Wątki (std::thread)", ["watk", "thread", "rownoleg", "mutex", "wspolbiez"], r"""
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

int main() {
    long long licznik = 0;
    std::mutex zamek;

    auto praca = [&](int ile) {
        for (int i = 0; i < ile; ++i) {
            std::lock_guard<std::mutex> blokada(zamek);  // tylko jeden wątek naraz
            ++licznik;
        }
    };

    std::vector<std::thread> watki;
    for (int i = 0; i < 4; ++i) watki.emplace_back(praca, 100000);
    for (auto& w : watki) w.join();                     // czekamy na wszystkie

    std::cout << "Licznik: " << licznik << '\n';        // zawsze 400000
    return 0;
}
""", "`std::thread` uruchamia funkcję równolegle, a `join()` czeka na jej koniec. Wspólne dane chroń "
         "`std::mutex` (lub `std::atomic`), inaczej wynik będzie losowy. Kompiluj z `-pthread`."),
]


def pyta_o_cpp(tekst):
    """Czy wiadomość dotyczy C++ (wspomina język)?"""
    return bool(_CPP.search(normalizuj(tekst)))


def prosi_o_kod(tekst):
    """Czy ktoś prosi o kod w C++ ("napisz w c++ ...", "przykład klasy w cpp")?"""
    t = normalizuj(tekst)
    return bool(_CPP.search(t) and _PROSBA.search(t))


def _pasuje(slowo_kluczowe, tekst):
    return re.search(r"(?<![a-z0-9])" + re.escape(slowo_kluczowe), tekst) is not None


def dopasuj(tekst):
    """Najlepiej pasujący wzór (albo None) dla znormalizowanego tekstu."""
    t = " " + re.sub(r"[^a-z0-9_+]+", " ", _CPP.sub(" ", normalizuj(tekst))) + " "
    najlepszy, wynik = None, 0
    for wzor in WZORY:
        punkty = sum(len(s) for s in wzor["slowa"] if _pasuje(s, t))
        if punkty > wynik:
            najlepszy, wynik = wzor, punkty
    return najlepszy


def _kod(wzor, tekst):
    kod = wzor["kod"]
    if wzor["liczba"]:
        domyslna, najmniej, najwiecej = wzor["liczba"]
        liczby = [int(x) for x in _LICZBA.findall(tekst)]
        n = liczby[0] if liczby else domyslna
        kod = kod.replace("{n}", str(max(najmniej, min(najwiecej, n))))
    return kod


def napisz(tekst):
    """Odpowiedź z programem w C++ albo None, gdy nie ma pasującego wzoru.

    Wystarczy prośba o kod ("napisz w c++ ...") albo wzmianka o C++ razem ze znanym
    tematem ("dziedziczenie w c++", "bfs cpp")."""
    if not pyta_o_cpp(tekst):
        return None
    wzor = dopasuj(tekst)
    if not wzor:
        return None
    kompilacja = KOMPILACJA + (" -pthread" if "<thread>" in wzor["kod"] else "")
    return (f"#### {wzor['tytul']} w C++\n"
            f"{wzor['opis']}\n"
            f"```cpp\n{_kod(wzor, tekst)}```\n"
            f"**Kompilacja i uruchomienie:** `{kompilacja}`, potem `./program` "
            f"(Windows: `program.exe`). Na telefonie możesz użyć aplikacji typu Cxxdroid "
            f"albo strony godbolt.org / onlinegdb.com.")


def lista_wzorow():
    return ", ".join(w["tytul"].split(" (")[0].lower() for w in WZORY)


def brak_wzoru():
    return ("Bez dużego modelu AI piszę w C++ programy z gotowych, sprawdzonych wzorów, a tego jeszcze nie mam. "
            "Włącz Claude albo model w telefonie (⚙️) - wtedy napiszę dokładnie to, o co prosisz.\n\n"
            "Offline umiem: " + lista_wzorow() + ". Napisz np. „napisz w C++ sortowanie”.")
