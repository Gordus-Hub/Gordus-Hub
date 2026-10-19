#!/bin/sh
# Prueba de humo del toolchain Rust (POSIX sh).
# Versiones, rust-toolchain.toml, cargo build/run/test, cargo build --locked --offline,
# rustc directo, cargo fmt --check, cargo clippy -D warnings, enlazador y reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${RUST_EXAMPLE_DIR:-$here/../examples/hola}"
expected_version="${EXPECTED_RUST_VERSION:-1.99.1}"

for f in Cargo.toml Cargo.lock rust-toolchain.toml src/main.rs; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas: Cargo.toml lleva C mayuscula)" >&2; exit 2
    fi
done
for tool in rustc cargo rustfmt cargo-clippy cc; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done
for bad in rustup python3 python curl wget; do
    if command -v "$bad" >/dev/null 2>&1; then echo "BLOCKED: '$bad' no debe estar en la imagen" >&2; exit 3; fi
done
[ "${CARGO_NET_OFFLINE:-}" = true ] || { echo "BLOCKED: CARGO_NET_OFFLINE debe ser true" >&2; exit 3; }

rustc_out=$(rustc --version)
cargo_out=$(cargo --version)
echo "$rustc_out"
echo "$cargo_out"
echo "$(rustfmt --version)"
echo "$(cargo clippy --version)"
echo "linker: $(cc --version | sed -n 1p)"
case "$rustc_out" in "rustc $expected_version "*) : ;; *) echo "FAILED: rustc no es $expected_version" >&2; exit 4 ;; esac
case "$cargo_out" in "cargo $expected_version "*) : ;; *) echo "FAILED: cargo no es $expected_version" >&2; exit 4 ;; esac
channel=$(sed -n 's/^channel = "\(.*\)"$/\1/p' "$src/rust-toolchain.toml")
[ "$channel" = "$expected_version" ] || { echo "BLOCKED: rust-toolchain.toml pide '$channel', instalado $expected_version" >&2; exit 3; }
echo "rust-toolchain.toml channel = $channel (coincide)"

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-rust-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
mkdir -p "$work/hola/src"
cp "$src/Cargo.toml" "$src/Cargo.lock" "$src/rust-toolchain.toml" "$work/hola/"
cp "$src/src/main.rs" "$work/hola/src/"
chmod -R u+w "$work/hola"
cd "$work/hola"
export CARGO_TARGET_DIR="$work/target"
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: [10, 8, 6, 4, 2]\nResult: 10/2 = 5, 1/0 -> division por cero')
lock_before=$(cksum Cargo.lock)

cargo fmt --check || { echo "FAILED: cargo fmt --check (codigo sin formatear)" >&2; exit 4; }
echo "cargo fmt --check OK"
cargo clippy --locked --offline --quiet -- -D warnings || { echo "FAILED: cargo clippy" >&2; exit 4; }
echo "cargo clippy -D warnings OK"

cargo build --locked --offline --release --quiet || { echo "FAILED: cargo build --locked --offline" >&2; exit 4; }
out=$("$CARGO_TARGET_DIR/release/hola") || { echo "FAILED: ejecutar binario" >&2; exit 4; }
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada del binario" >&2; printf '%s\n' "$out" >&2; exit 4; }
echo "cargo build --locked --offline --release OK ($(wc -c < "$CARGO_TARGET_DIR/release/hola") bytes)"

run_out=$(cargo run --locked --offline --quiet) || { echo "FAILED: cargo run" >&2; exit 4; }
echo "$run_out"
[ "$run_out" = "$want" ] || { echo "FAILED: salida inesperada de cargo run" >&2; exit 4; }

cargo test --locked --offline --quiet || { echo "FAILED: cargo test" >&2; exit 4; }
echo "cargo test OK"
[ "$(cksum Cargo.lock)" = "$lock_before" ] || { echo "FAILED: cargo modifico Cargo.lock" >&2; exit 4; }

# rustc directo, sin cargo
rustc --edition 2024 -O src/main.rs -o "$work/hola-rustc" || { echo "FAILED: rustc directo" >&2; exit 4; }
[ "$("$work/hola-rustc")" = "$want" ] || { echo "FAILED: salida inesperada de rustc directo" >&2; exit 4; }
echo "rustc directo OK"
command -v readelf >/dev/null 2>&1 && readelf -p .comment "$work/hola-rustc" | grep -q 'GCC: (Debian 14' \
    || { echo "FAILED: el binario no lo enlazo el gcc 14 de Debian" >&2; exit 4; }
echo "enlazador OK: cc = gcc 14 (Debian)"

# Fail-closed 1: una dependencia nueva con --offline debe fallar (no hay red ni registro).
mkdir "$work/dep" && cp -r src Cargo.toml rust-toolchain.toml "$work/dep/"
sed -i 's/^\[dependencies\]$/[dependencies]\nserde = "1"/' "$work/dep/Cargo.toml"
grep -q '^serde = "1"' "$work/dep/Cargo.toml" || { echo "FAILED: no se pudo preparar la prueba de dependencia" >&2; exit 4; }
if (cd "$work/dep" && cargo build --offline >/dev/null 2>&1); then
    echo "FAILED: cargo descargo una dependencia estando offline" >&2; exit 4
fi
echo "offline bloquea dependencias nuevas: OK"
# Fail-closed 2: --locked con un Cargo.lock desactualizado debe fallar.
mkdir "$work/lock" && cp -r src Cargo.toml Cargo.lock rust-toolchain.toml "$work/lock/"
sed -i 's/^version = "0.1.0"/version = "0.2.0"/' "$work/lock/Cargo.toml"
if (cd "$work/lock" && cargo build --locked --offline >/dev/null 2>&1); then
    echo "FAILED: --locked acepto un Cargo.lock desactualizado" >&2; exit 4
fi
echo "--locked bloquea Cargo.lock desactualizado: OK"

echo "PASS: toolchain Rust $expected_version (fmt + clippy + build --locked --offline + run + test + rustc) OK"
