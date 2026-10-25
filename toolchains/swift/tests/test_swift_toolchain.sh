#!/bin/sh
# Prueba de humo del toolchain Swift (POSIX sh).
# Versiones, swiftc directo + ejecucion, swift build/run/test (SwiftPM) sin red y reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${SWIFT_EXAMPLE_DIR:-$here/../examples/hola}"
expected_version="${EXPECTED_SWIFT_VERSION:-6.4.1}"

for f in Package.swift Sources/HolaCore/HolaCore.swift Sources/Hola/main.swift Tests/HolaCoreTests/HolaCoreTests.swift; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas: Package.swift, Sources/, Tests/ las exige SwiftPM)" >&2; exit 2
    fi
done
for tool in swift swiftc swift-build swift-test swift-run ld; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done
for bad in python3 python curl wget git lldb; do
    if command -v "$bad" >/dev/null 2>&1; then echo "BLOCKED: '$bad' no debe estar en la imagen" >&2; exit 3; fi
done
[ "${GORDUS_SWIFT_OFFLINE:-}" = true ] || { echo "BLOCKED: GORDUS_SWIFT_OFFLINE debe ser true" >&2; exit 3; }

swiftc_out=$(swiftc --version 2>&1 | sed -n 1p)
spm_out=$(swift build --version 2>&1 | sed -n 1p)
echo "$swiftc_out"
echo "swiftpm: $spm_out"
echo "linker: $(ld --version | sed -n 1p)"
case "$swiftc_out" in *"Swift version $expected_version "*) : ;; *) echo "FAILED: swiftc no es $expected_version" >&2; exit 4 ;; esac
case "$spm_out" in *"$expected_version"*) : ;; *) echo "FAILED: SwiftPM no es $expected_version" >&2; exit 4 ;; esac

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-swift-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp -R "$src" "$work/hola"
chmod -R u+w "$work/hola"
cd "$work/hola"
scratch="$work/build"
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: [10, 8, 6, 4, 2]\nResult: 10/2 = 5, 1/0 -> division por cero')
flags="--disable-automatic-resolution --scratch-path $scratch"

# 1) swiftc directo (sin SwiftPM): un solo archivo compilado y ejecutado.
cat Sources/HolaCore/HolaCore.swift > "$work/directo.swift"
printf '\nfor l in lineas() { print(l) }\n' >> "$work/directo.swift"
swiftc -O -o "$work/hola-swiftc" "$work/directo.swift" || { echo "FAILED: swiftc directo" >&2; exit 4; }
[ "$("$work/hola-swiftc")" = "$want" ] || { echo "FAILED: salida inesperada de swiftc directo" >&2; exit 4; }
echo "swiftc directo OK ($(wc -c < "$work/hola-swiftc") bytes)"

# 2) swift build (release) + ejecutar el binario.
swift build $flags -c release --quiet || { echo "FAILED: swift build" >&2; exit 4; }
out=$("$scratch/release/Hola") || { echo "FAILED: ejecutar binario" >&2; exit 4; }
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada del binario" >&2; printf '%s\n' "$out" >&2; exit 4; }
echo "swift build -c release OK"

# 3) swift run.
run_out=$(swift run $flags --quiet Hola) || { echo "FAILED: swift run" >&2; exit 4; }
echo "$run_out"
[ "$run_out" = "$want" ] || { echo "FAILED: salida inesperada de swift run" >&2; exit 4; }

# 4) swift test (XCTest).
test_out=$(swift test $flags 2>&1) || { printf '%s\n' "$test_out" >&2; echo "FAILED: swift test" >&2; exit 4; }
printf '%s\n' "$test_out" | grep -E "Executed [0-9]+ tests?, with 0 failures" | tail -1
printf '%s\n' "$test_out" | grep -qE "Executed 3 tests, with 0 failures" || { echo "FAILED: se esperaban 3 tests sin fallos" >&2; exit 4; }
echo "swift test OK"
[ ! -e Package.resolved ] || { echo "FAILED: SwiftPM creo Package.resolved (no deberia haber dependencias)" >&2; exit 4; }

# Fail-closed: una dependencia externa nueva debe fallar (sin red, sin git, sin resolucion automatica).
cp -R "$src" "$work/dep" && chmod -R u+w "$work/dep"
sed -i 's|    name: "hola",|    name: "hola",\n    dependencies: [.package(url: "https://github.com/apple/swift-argument-parser", exact: "1.5.0")],|' "$work/dep/Package.swift"
grep -q 'swift-argument-parser' "$work/dep/Package.swift" || { echo "FAILED: no se pudo preparar la prueba de dependencia" >&2; exit 4; }
if (cd "$work/dep" && swift build --disable-automatic-resolution --scratch-path "$work/build-dep" >/dev/null 2>&1); then
    echo "FAILED: SwiftPM resolvio una dependencia externa estando offline" >&2; exit 4
fi
echo "dependencias externas bloqueadas: OK"

echo "PASS: toolchain Swift $expected_version (swiftc + swift build/run/test, offline) OK"
