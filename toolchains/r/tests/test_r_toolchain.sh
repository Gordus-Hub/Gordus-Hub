#!/bin/sh
# Prueba de humo del toolchain R (POSIX sh).
# Versiones, Rscript ejecuta el ejemplo, parse() rechaza un error de sintaxis, install.packages()
# desde el repositorio local (sin red), renv::restore() offline, testthat, y reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${R_EXAMPLE_DIR:-$here/../examples/hola}"
expected_r="${EXPECTED_R_VERSION:-4.6.1}"
expected_testthat="${EXPECTED_TESTTHAT_VERSION:-3.3.2}"
expected_renv="${EXPECTED_RENV_VERSION:-1.3.1}"
repo_url="file:///opt/gordus-r/repo"

for f in hola.r saludo.r renv.lock tests/testthat/test_saludo.r; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
for tool in R Rscript; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done

r_v=$(Rscript -e 'cat(as.character(getRversion()))')
echo "R $r_v"
[ "$r_v" = "$expected_r" ] || { echo "FAILED: R no es $expected_r" >&2; exit 4; }
tt_v=$(Rscript -e 'cat(format(packageVersion("testthat")))')
echo "testthat $tt_v"
[ "$tt_v" = "$expected_testthat" ] || { echo "FAILED: testthat no es $expected_testthat" >&2; exit 4; }
renv_v=$(Rscript -e 'cat(format(packageVersion("renv")))')
echo "renv $renv_v"
[ "$renv_v" = "$expected_renv" ] || { echo "FAILED: renv no es $expected_renv" >&2; exit 4; }
repos=$(Rscript -e 'cat(getOption("repos"))')
echo "repos $repos"
[ "$repos" = "$repo_url" ] || { echo "BLOCKED: el repositorio por defecto debe ser $repo_url" >&2; exit 3; }

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-r-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp -R "$src" "$work/hola"
chmod -R u+w "$work/hola"
cd "$work/hola"

# 1) Rscript ejecuta el ejemplo
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: 10 8 6 4 2\nResultado: 10/2 = 5, 1/0 -> division por cero')
out=$(Rscript hola.r) || { echo "FAILED: Rscript hola.r" >&2; exit 4; }
echo "$out"
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada de hola.r" >&2; exit 4; }
echo "Rscript hola.r OK"

# 2) parse() revisa la sintaxis (y rechaza un archivo roto)
Rscript -e 'invisible(parse("saludo.r"))' || { echo "FAILED: parse saludo.r" >&2; exit 4; }
mkdir bad && printf 'roto <- function( {\n  print("sin cerrar"\n' > bad/roto.r
if Rscript -e 'invisible(parse("bad/roto.r"))' >/dev/null 2>&1; then echo "FAILED: parse acepto un error de sintaxis" >&2; exit 4; fi
echo "parse rechaza error de sintaxis: OK"

# 3) install.packages() offline desde el repositorio local, a una biblioteca temporal
mkdir lib
Rscript -e 'install.packages("praise", lib = "lib", quiet = TRUE); library(praise, lib.loc = "lib"); stopifnot(packageVersion("praise", lib.loc = "lib") == "1.0.0")' >/dev/null 2>&1 \
    || { echo "FAILED: install.packages offline" >&2; exit 4; }
echo "install.packages offline OK"

# 4) renv::restore() offline del renv.lock en una biblioteca temporal
lock_before=$(cksum renv.lock)
Rscript -e 'renv::restore(lockfile = "renv.lock", library = "renvlib", prompt = FALSE); stopifnot(packageVersion("praise", lib.loc = "renvlib") == "1.0.0")' >renv.txt 2>&1 \
    || { echo "FAILED: renv::restore offline" >&2; cat renv.txt >&2; exit 4; }
[ "$(cksum renv.lock)" = "$lock_before" ] || { echo "FAILED: renv modifico renv.lock" >&2; exit 4; }
echo "renv restore offline OK"

# 5) testthat
Rscript -e 'r <- as.data.frame(testthat::test_dir("tests/testthat", reporter = "summary", stop_on_failure = TRUE)); cat("testthat:", sum(r$nb), "expectativas,", sum(r$failed), "fallas\n")' \
    || { echo "FAILED: testthat" >&2; exit 4; }
echo "testthat OK"

# 6) Fail-closed: una prueba que falla tiene que hacer fallar a testthat
mkdir -p bad/t && sed 's/expect_equal(suma_hasta(10), 55)/expect_equal(suma_hasta(10), 56)/; s|file.path("..", "..", "saludo.r")|file.path("..", "..", "..", "saludo.r")|' \
    tests/testthat/test_saludo.r > bad/t/test_falla.r
if Rscript -e 'testthat::test_dir("bad/t", reporter = "silent", stop_on_failure = TRUE)' >/dev/null 2>&1; then
    echo "FAILED: testthat no detecto una prueba rota" >&2; exit 4
fi
echo "testthat detecta prueba rota: OK"

# 7) Fail-closed: un paquete que no esta en el repositorio local no se puede instalar (sin red)
if Rscript -e 'suppressWarnings(install.packages("leftpad", lib = "lib", quiet = TRUE)); library(leftpad, lib.loc = "lib")' >/dev/null 2>&1; then
    echo "FAILED: se instalo un paquete fuera del repositorio local" >&2; exit 4
fi
echo "offline bloquea paquetes nuevos: OK"

# 8) Fail-closed: no se puede escribir en la biblioteca del sistema
if Rscript -e 'install.packages("praise", lib = .Library.site[1], quiet = TRUE); stopifnot(file.access(.Library.site[1], 2) == 0)' >/dev/null 2>&1; then
    echo "FAILED: la biblioteca del sistema es escribible" >&2; exit 4
fi
echo "biblioteca del sistema de solo lectura: OK"

echo "PASS: toolchain R $expected_r + testthat $expected_testthat + renv $expected_renv (Rscript + parse + install.packages offline + renv + testthat) OK"
