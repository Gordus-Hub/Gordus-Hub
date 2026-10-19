// Ejemplo C++23 de Gordus-Hub: std::print, std::expected y std::ranges.
#include <algorithm>
#include <expected>
#include <print>
#include <ranges>
#include <string>
#include <vector>

namespace {

std::expected<int, std::string> dividir(int a, int b) {
    if (b == 0) {
        return std::unexpected(std::string{"division por cero"});
    }
    return a / b;
}

}  // namespace

int main() {
    std::println("Hola, Gordus-Hub!");

    int suma = 0;
    for (int x : std::views::iota(1, 11)) {
        suma += x;
    }
    std::println("Suma 1..10 = {}", suma);

    std::vector<int> pares;
    std::ranges::copy(std::views::iota(1, 11) | std::views::filter([](int x) { return x % 2 == 0; }),
                      std::back_inserter(pares));
    std::ranges::reverse(pares);
    std::print("Pares al reves:");
    for (int p : pares) {
        std::print(" {}", p);
    }
    std::println("");

    auto ok = dividir(10, 2);
    auto error = dividir(1, 0);
    std::println("expected: 10/2 = {}, 1/0 -> {}", ok.value_or(-1), error ? "?" : error.error());
    std::println("C++ {}", __cplusplus);
    return 0;
}
