#!/bin/sh
# Prueba de humo del toolchain Kotlin (POSIX sh).
# Versiones, kotlinc -> .jar, java -jar, kotlin runner, pruebas con kotlin.test y reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${KOTLIN_EXAMPLES_DIR:-$here/../examples}"
expected_kotlin="${EXPECTED_KOTLIN_VERSION:-2.4.21}"
expected_java="${EXPECTED_JAVA_MAJOR:-25}"

for f in hola.kt hola_test.kt; do
    [ -f "$src/$f" ] || { echo "BAD_INPUT: no existe $src/$f" >&2; exit 2; }
done
for tool in kotlinc kotlin java javac jar; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done
for bad in python3 python curl wget git gradle mvn; do
    if command -v "$bad" >/dev/null 2>&1; then echo "BLOCKED: '$bad' no debe estar en la imagen" >&2; exit 3; fi
done
[ "${GORDUS_KOTLIN_OFFLINE:-}" = true ] || { echo "BLOCKED: GORDUS_KOTLIN_OFFLINE debe ser true" >&2; exit 3; }
[ "${JAVA_HOME:-}" = /opt/kotlin/jdk-25 ] || { echo "BLOCKED: JAVA_HOME debe ser /opt/kotlin/jdk-25" >&2; exit 3; }
lib="${KOTLIN_HOME:-/opt/kotlin/kotlinc}/lib"
for jar in kotlin-stdlib.jar kotlin-test.jar; do
    [ -f "$lib/$jar" ] || { echo "BLOCKED: falta $lib/$jar" >&2; exit 3; }
done

java_line=$(java -version 2>&1 | sed -n 1p)
kotlinc_line=$(kotlinc -version 2>&1 | grep -m1 'kotlinc-jvm' || true)
echo "$java_line"
echo "$kotlinc_line"
case "$java_line" in *"version \"$expected_java"*) : ;; *) echo "FAILED: java no es $expected_java" >&2; exit 4 ;; esac
case "$kotlinc_line" in *"kotlinc-jvm $expected_kotlin "*) : ;; *) echo "FAILED: kotlinc no es $expected_kotlin" >&2; exit 4 ;; esac

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-kotlin-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp "$src/hola.kt" "$src/hola_test.kt" "$work/"
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: [10, 8, 6, 4, 2]\nKotlin %s en Java %s' "$expected_kotlin" "$expected_java")

# 1) kotlinc -> jar ejecutable con el runtime de Kotlin incluido.
kotlinc "$work/hola.kt" -include-runtime -d "$work/hola.jar" 2>"$work/kotlinc.log" || { cat "$work/kotlinc.log" >&2; echo "FAILED: kotlinc" >&2; exit 4; }
out=$(java -jar "$work/hola.jar") || { echo "FAILED: java -jar" >&2; exit 4; }
echo "$out"
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada de java -jar" >&2; exit 4; }
echo "kotlinc + java -jar OK"

# 2) Argumentos y el lanzador 'kotlin'.
[ "$(java -jar "$work/hola.jar" Mundo | sed -n 1p)" = "Hola, Mundo!" ] || { echo "FAILED: argumentos" >&2; exit 4; }
run_out=$(kotlin -cp "$work/hola.jar" HolaKt) || { echo "FAILED: kotlin runner" >&2; exit 4; }
[ "$run_out" = "$want" ] || { echo "FAILED: salida inesperada de kotlin" >&2; exit 4; }
echo "kotlin runner OK"

# 3) Pruebas con kotlin.test (sin descargas).
kotlinc "$work/hola.kt" "$work/hola_test.kt" -cp "$lib/kotlin-test.jar" -d "$work/test-classes" 2>"$work/kotlinc-test.log" || { cat "$work/kotlinc-test.log" >&2; echo "FAILED: kotlinc tests" >&2; exit 4; }
test_out=$(java -cp "$work/test-classes:$lib/kotlin-stdlib.jar:$lib/kotlin-test.jar" Hola_testKt) || { echo "FAILED: pruebas" >&2; exit 4; }
printf '%s\n' "$test_out"
printf '%s\n' "$test_out" | grep -qx 'Tests: 3 OK, 0 fallos' || { echo "FAILED: se esperaban 3 pruebas OK" >&2; exit 4; }

# 4) Fail-closed: un error de compilacion debe cortar con codigo distinto de 0.
printf 'fun main() { val x: Int = "texto" }\n' > "$work/roto.kt"
if kotlinc "$work/roto.kt" -d "$work/roto" >/dev/null 2>&1; then echo "FAILED: kotlinc acepto codigo invalido" >&2; exit 4; fi
echo "codigo invalido rechazado: OK"

echo "PASS: toolchain Kotlin $expected_kotlin (kotlinc + java -jar + kotlin.test, JDK $expected_java, offline) OK"
