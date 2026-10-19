#!/bin/sh
# Prueba de humo del toolchain C++23 (POSIX sh).
# Versiones, g++ y clang++ con -std=c++23 (compilar + ejecutar), clang++ con libc++,
# CMake + Ninja, make, enlazadores (GNU ld y LLD), "import std" con clang + libc++
# y las reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${CPP_EXAMPLE_DIR:-$here/../examples/hola}"
want_gcc="${EXPECTED_GCC_VERSION:-14.2.0}"
want_clang="${EXPECTED_CLANG_VERSION:-19.1.7}"
want_cmake="${EXPECTED_CMAKE_VERSION:-3.31.6}"

for f in CMakeLists.txt main.cpp; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
for tool in g++ gcc clang++ clang ld ld.lld cmake ninja make pkg-config clang-scan-deps clang-format; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done
for bad in python3 python curl wget; do
    if command -v "$bad" >/dev/null 2>&1; then echo "BLOCKED: '$bad' no debe estar en la imagen" >&2; exit 3; fi
done

# 1) Versiones
gcc_v=$(g++ -dumpfullversion)
clang_v=$(clang++ -dumpversion)
cmake_v=$(cmake --version | sed -n '1s/^cmake version //p')
echo "g++ $gcc_v"
echo "clang++ $clang_v"
echo "cmake $cmake_v"
echo "ninja $(ninja --version)"
echo "$(make --version | sed -n 1p)"
echo "$(ld --version | sed -n 1p)"
echo "$(ld.lld --version)"
[ "$gcc_v" = "$want_gcc" ] || { echo "FAILED: g++ no es $want_gcc" >&2; exit 4; }
[ "$clang_v" = "$want_clang" ] || { echo "FAILED: clang++ no es $want_clang" >&2; exit 4; }
[ "$cmake_v" = "$want_cmake" ] || { echo "FAILED: cmake no es $want_cmake" >&2; exit 4; }

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-cpp-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp "$src/CMakeLists.txt" "$src/main.cpp" "$work/"
cd "$work"
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: 10 8 6 4 2\nexpected: 10/2 = 5, 1/0 -> division por cero\nC++ 202302')

check_run() {  # $1 = nombre, $2 = binario
    out=$("./$2") || { echo "FAILED: ejecutar $2" >&2; exit 4; }
    [ "$out" = "$want" ] || { echo "FAILED: salida inesperada de $1" >&2; printf '%s\n' "$out" >&2; exit 4; }
    echo "$1 OK"
}

# 2) Compilar + ejecutar con cada compilador / biblioteca estandar / enlazador
flags="-std=c++23 -Wall -Wextra -Wpedantic -Werror -O2"
# shellcheck disable=SC2086
g++ $flags main.cpp -o hola-gcc || { echo "FAILED: g++ -std=c++23" >&2; exit 4; }
check_run "g++ -std=c++23 (libstdc++, GNU ld)" hola-gcc
# shellcheck disable=SC2086
clang++ $flags main.cpp -o hola-clang || { echo "FAILED: clang++ -std=c++23" >&2; exit 4; }
check_run "clang++ -std=c++23 (libstdc++, GNU ld)" hola-clang
# shellcheck disable=SC2086
clang++ $flags -stdlib=libc++ -fuse-ld=lld main.cpp -o hola-libcxx || { echo "FAILED: clang++ libc++ + lld" >&2; exit 4; }
check_run "clang++ -std=c++23 -stdlib=libc++ (LLD)" hola-libcxx
# shellcheck disable=SC2086
g++ $flags -fuse-ld=lld main.cpp -o hola-gcc-lld || { echo "FAILED: g++ -fuse-ld=lld" >&2; exit 4; }
check_run "g++ -std=c++23 (LLD)" hola-gcc-lld

# 3) Enlazador realmente usado: cada binario lleva la marca del linker en .comment
command -v readelf >/dev/null 2>&1 || { echo "BLOCKED: falta readelf" >&2; exit 3; }
readelf -p .comment hola-libcxx | grep -q 'Linker: Debian LLD 19' || { echo "FAILED: hola-libcxx no lo enlazo LLD" >&2; exit 4; }
if readelf -p .comment hola-gcc | grep -q 'Linker:'; then echo "FAILED: hola-gcc deberia usar GNU ld" >&2; exit 4; fi
readelf -d hola-libcxx | grep -q 'libc++.so' || { echo "FAILED: hola-libcxx no usa libc++" >&2; exit 4; }
readelf -d hola-gcc | grep -q 'libstdc++.so' || { echo "FAILED: hola-gcc no usa libstdc++" >&2; exit 4; }
echo "enlazadores OK: GNU ld (por defecto) y LLD 19"

# 4) CMake + Ninja (generador por defecto) y CMake + make
cmake -S . -B build-ninja -G Ninja -DCMAKE_BUILD_TYPE=Release >/dev/null || { echo "FAILED: cmake (Ninja)" >&2; exit 4; }
cmake --build build-ninja >/dev/null || { echo "FAILED: ninja build" >&2; exit 4; }
cp build-ninja/hola hola-cmake-ninja && check_run "cmake + ninja (g++)" hola-cmake-ninja
CXX=clang++ cmake -S . -B build-make -G "Unix Makefiles" >/dev/null || { echo "FAILED: cmake (make)" >&2; exit 4; }
cmake --build build-make >/dev/null || { echo "FAILED: make build" >&2; exit 4; }
cp build-make/hola hola-cmake-make && check_run "cmake + make (clang++)" hola-cmake-make

# 5) import std (C++23 modulos): clang 19 + libc++ 19 + CMake 3.31 (experimental en CMake)
mkdir modstd && cd modstd
cat > CMakeLists.txt <<'CM'
cmake_minimum_required(VERSION 3.31)
set(CMAKE_EXPERIMENTAL_CXX_IMPORT_STD "0e5b6991-d74f-4b3d-a41c-cf096e0b2508")
project(gordus_import_std LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_MODULE_STD 1)
add_executable(modstd main.cpp)
CM
cat > main.cpp <<'CPP'
import std;
int main() {
    std::println("import std: suma 1..10 = {}", std::ranges::fold_left(std::views::iota(1, 11), 0, std::plus{}));
}
CPP
CXX=clang++ CXXFLAGS=-stdlib=libc++ LDFLAGS="-stdlib=libc++ -fuse-ld=lld" \
    cmake -S . -B build -G Ninja >/dev/null 2>&1 || { echo "FAILED: cmake import std" >&2; exit 4; }
cmake --build build >/dev/null || { echo "FAILED: build import std" >&2; exit 4; }
mod_out=$(./build/modstd)
[ "$mod_out" = "import std: suma 1..10 = 55" ] || { echo "FAILED: import std" >&2; exit 4; }
echo "$mod_out"
echo "import std OK (clang++ 19 + libc++ 19 + CMake + Ninja)"
cd ..

# 6) Fail-closed: un programa que no es C++23 valido debe fallar al compilar
printf 'int main() { return undefined_symbol; }\n' > roto.cpp
if g++ -std=c++23 roto.cpp -o roto >/dev/null 2>&1; then echo "FAILED: compilo codigo roto" >&2; exit 4; fi
echo "codigo roto rechazado: OK"

echo "PASS: toolchain C++23 (g++ $gcc_v + clang++ $clang_v, libstdc++ + libc++, GNU ld + LLD, cmake + ninja + make, import std) OK"
