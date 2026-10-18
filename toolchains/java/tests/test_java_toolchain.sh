#!/bin/sh
# Prueba de humo del toolchain Java 25 (POSIX sh).
# Compila examples/Hola.java con javac, lo ejecuta con java y verifica la salida.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${HOLA_SRC:-$here/../examples/Hola.java}"
expected_major="${EXPECTED_JAVA_MAJOR:-25}"

if [ ! -f "$src" ]; then
    echo "BAD_INPUT: no existe $src" >&2; exit 2
fi
for tool in java javac jar javadoc jshell jlink jdeps jpackage; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "BLOCKED: falta la herramienta '$tool' en PATH" >&2; exit 3
    fi
done

version_out=$(java -version 2>&1)
echo "$version_out"
first_line=$(printf '%s\n' "$version_out" | head -n 1)
case "$first_line" in
    *"version \"$expected_major"*) : ;;
    *) echo "FAILED: java -version no reporta $expected_major: $first_line" >&2; exit 4 ;;
esac
javac_out=$(javac -version 2>&1)
echo "$javac_out"
case "$javac_out" in
    "javac $expected_major"*) : ;;
    *) echo "FAILED: javac -version no reporta $expected_major: $javac_out" >&2; exit 4 ;;
esac

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-java-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp "$src" "$work/Hola.java"

javac -d "$work/classes" "$work/Hola.java" || { echo "FAILED: javac" >&2; exit 4; }
out=$(java -cp "$work/classes" Hola) || { echo "FAILED: java" >&2; exit 4; }
echo "$out"
want=$(printf 'Hola, Gordus-Hub!\nJava %s' "$expected_major")
if [ "$out" != "$want" ]; then
    echo "FAILED: salida inesperada" >&2; exit 4
fi

# jar: empaquetar y ejecutar desde el .jar
jar --create --file "$work/hola.jar" --main-class Hola -C "$work/classes" . || { echo "FAILED: jar" >&2; exit 4; }
jar_out=$(java -jar "$work/hola.jar" Mundo) || { echo "FAILED: java -jar" >&2; exit 4; }
[ "$jar_out" = "$(printf 'Hola, Mundo!\nJava %s' "$expected_major")" ] || { echo "FAILED: salida de jar" >&2; exit 4; }

# Ejecucion directa de un archivo fuente (JEP 330) sin compilar a mano
direct=$(java "$work/Hola.java") || { echo "FAILED: java Hola.java" >&2; exit 4; }
[ "$direct" = "$want" ] || { echo "FAILED: salida modo fuente" >&2; exit 4; }

echo "PASS: toolchain Java $expected_major (javac + java + jar) OK"
