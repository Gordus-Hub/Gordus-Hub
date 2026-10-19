#!/bin/sh
# Prueba de humo del toolchain Mojo (POSIX sh).
# Verifica la version, "mojo run", "mojo build" + ejecutar el binario, y la
# interoperabilidad con el Python que vive DENTRO del entorno Mojo.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
examples="${MOJO_EXAMPLES:-$here/../examples}"
expected_version="${EXPECTED_MOJO_VERSION:-1.1.0}"
mojo_env="${MOJO_ENV:-}"

for f in hola.mojo interop_python.mojo; do
    if [ ! -f "$examples/$f" ]; then
        echo "BAD_INPUT: no existe $examples/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
for tool in mojo pixi; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "BLOCKED: falta la herramienta '$tool' en PATH" >&2; exit 3
    fi
done
if [ -z "$mojo_env" ] || [ ! -d "$mojo_env" ]; then
    echo "BLOCKED: MOJO_ENV no apunta al entorno Mojo" >&2; exit 3
fi

version_out=$(mojo --version 2>&1)
echo "$version_out"
case "$version_out" in
    "Mojo $expected_version "*) : ;;
    *) echo "FAILED: mojo --version no reporta $expected_version" >&2; exit 4 ;;
esac
pixi --version

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-mojo-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp "$examples/hola.mojo" "$examples/interop_python.mojo" "$work/"
cd "$work"

want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55')

run_out=$(mojo run hola.mojo 2>/dev/null) || { echo "FAILED: mojo run" >&2; exit 4; }
echo "$run_out"
[ "$run_out" = "$want" ] || { echo "FAILED: salida inesperada de mojo run" >&2; exit 4; }

mojo build hola.mojo -o hola 2>/dev/null || { echo "FAILED: mojo build" >&2; exit 4; }
[ -x ./hola ] || { echo "FAILED: mojo build no genero el binario" >&2; exit 4; }
bin_out=$(./hola) || { echo "FAILED: ejecutar ./hola" >&2; exit 4; }
[ "$bin_out" = "$want" ] || { echo "FAILED: salida inesperada del binario" >&2; exit 4; }
echo "binario OK: ./hola ($(wc -c < hola) bytes)"

interop=$(mojo run interop_python.mojo 2>/dev/null) || { echo "FAILED: interop Python" >&2; exit 4; }
echo "$interop"
case "$interop" in
    *"python_prefix: $mojo_env"*"sqrt(16) = 4.0"*) : ;;
    *) echo "FAILED: Mojo no uso el Python del entorno Mojo ($mojo_env)" >&2; exit 4 ;;
esac

echo "PASS: toolchain Mojo $expected_version (mojo run + mojo build + interop Python) OK"
