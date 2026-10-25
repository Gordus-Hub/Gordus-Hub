#!/bin/sh
# Prueba de humo del toolchain Scala 3 (POSIX sh).
# Versiones, scalac -> clases + java, scala-cli (run/compile/package) sin red, pruebas y reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${SCALA_EXAMPLES_DIR:-$here/../examples}"
expected_scala="${EXPECTED_SCALA_VERSION:-3.10.0}"
expected_java="${EXPECTED_JAVA_MAJOR:-25}"

for f in hola.scala hola_test.scala; do
    [ -f "$src/$f" ] || { echo "BAD_INPUT: no existe $src/$f" >&2; exit 2; }
done
for tool in scala scalac scaladoc java javac jar; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done
for bad in python3 python curl wget git sbt mvn gradle cs coursier; do
    if command -v "$bad" >/dev/null 2>&1; then echo "BLOCKED: '$bad' no debe estar en la imagen" >&2; exit 3; fi
done
[ "${GORDUS_SCALA_OFFLINE:-}" = true ] || { echo "BLOCKED: GORDUS_SCALA_OFFLINE debe ser true" >&2; exit 3; }
[ "${JAVA_HOME:-}" = /opt/scala/jdk-25 ] || { echo "BLOCKED: JAVA_HOME debe ser /opt/scala/jdk-25" >&2; exit 3; }
lib="${SCALA_HOME:-/opt/scala/scala3}/lib"
[ -f "$lib/scala.jar" ] || { echo "BLOCKED: falta $lib/scala.jar" >&2; exit 3; }

java_line=$(java -version 2>&1 | sed -n 1p)
scalac_line=$(scalac -version 2>&1 | sed -n 1p)
cli_line=$(scala --version 2>&1 | grep -m1 'runner version' || true)
echo "$java_line"
echo "$scalac_line"
echo "$cli_line"
case "$java_line" in *"version \"$expected_java"*) : ;; *) echo "FAILED: java no es $expected_java" >&2; exit 4 ;; esac
case "$scalac_line" in *"Scala compiler version $expected_scala "*) : ;; *) echo "FAILED: scalac no es $expected_scala" >&2; exit 4 ;; esac
[ -n "$cli_line" ] || { echo "FAILED: scala (scala-cli) no responde" >&2; exit 4; }

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-scala-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp "$src/hola.scala" "$src/hola_test.scala" "$work/"
cd "$work"
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: [10, 8, 6, 4, 2]\nScala 3 en Java %s' "$expected_java")
cli="--power --offline --server=false"

# 1) scalac directo -> clases, ejecutadas con java + la biblioteca de Scala.
mkdir -p "$work/classes"
scalac -d "$work/classes" hola.scala || { echo "FAILED: scalac" >&2; exit 4; }
out=$(java -cp "$work/classes:$lib/scala.jar" hola) || { echo "FAILED: java" >&2; exit 4; }
echo "$out"
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada de scalac + java" >&2; exit 4; }
[ "$(java -cp "$work/classes:$lib/scala.jar" hola Mundo | sed -n 1p)" = "Hola, Mundo!" ] || { echo "FAILED: argumentos" >&2; exit 4; }
echo "scalac + java OK"

# 2) scala run (scala-cli) sin red, usando el repositorio local incluido en la distribucion.
run_out=$(scala run $cli hola.scala 2>/dev/null) || { echo "FAILED: scala run" >&2; exit 4; }
[ "$run_out" = "$want" ] || { echo "FAILED: salida inesperada de scala run" >&2; printf '%s\n' "$run_out" >&2; exit 4; }
echo "scala run (offline) OK"

# 3) Pruebas (sin bibliotecas externas).
test_out=$(scala run $cli hola.scala hola_test.scala --main-class holaTest 2>/dev/null) || { echo "FAILED: pruebas" >&2; exit 4; }
printf '%s\n' "$test_out"
printf '%s\n' "$test_out" | grep -qx 'Tests: 3 OK, 0 fallos' || { echo "FAILED: se esperaban 3 pruebas OK" >&2; exit 4; }

# 4) scala package -> jar ejecutable con java -jar.
scala --power package --offline --server=false hola.scala --main-class hola --assembly -o "$work/hola.jar" >/dev/null 2>&1 || { echo "FAILED: scala package" >&2; exit 4; }
[ "$(java -jar "$work/hola.jar")" = "$want" ] || { echo "FAILED: salida de java -jar" >&2; exit 4; }
echo "scala package + java -jar OK"

# 5) Fail-closed: codigo invalido y dependencias externas deben fallar sin red.
printf '@main def roto(): Unit = { val x: Int = "texto" }\n' > "$work/roto.scala"
if scalac -d "$work/classes" "$work/roto.scala" >/dev/null 2>&1; then echo "FAILED: scalac acepto codigo invalido" >&2; exit 4; fi
echo "codigo invalido rechazado: OK"
mkdir -p "$work/dep"
printf '//> using dep com.lihaoyi::os-lib:0.11.4\n@main def dep(): Unit = println(os.pwd)\n' > "$work/dep/dep.scala"
if (cd "$work/dep" && scala run $cli dep.scala >/dev/null 2>&1); then echo "FAILED: se resolvio una dependencia externa estando offline" >&2; exit 4; fi
echo "dependencias externas bloqueadas: OK"

echo "PASS: toolchain Scala $expected_scala (scalac + scala-cli run/package + pruebas, JDK $expected_java, offline) OK"
