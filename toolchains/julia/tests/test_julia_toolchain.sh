#!/bin/sh
# Prueba de humo del toolchain Julia (POSIX sh).
# Version y piso de seguridad (>= 1.13.2), Pkg sin red (instantiate + status con Manifest),
# julia ejecuta el ejemplo, Pkg.test con la biblioteca Test, y las reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${JULIA_EXAMPLE_DIR:-$here/../examples/hola}"
expected_julia="${EXPECTED_JULIA_VERSION:-1.13.2}"
# Minimo con las actualizaciones de seguridad de OpenSSL/LibCURL/LibGit2/nghttp2/Zlib (15/10/2026).
min_julia=1.13.2

for f in Project.toml Manifest.toml hola.jl src/Saludo.jl test/runtests.jl; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
command -v julia >/dev/null 2>&1 || { echo "BLOCKED: falta 'julia' en PATH" >&2; exit 3; }
J="julia --startup-file=no --history-file=no --color=no"

julia_v=$($J -e 'print(VERSION)')
echo "julia $julia_v"
$J -e "exit(VERSION >= v\"$min_julia\" ? 0 : 3)" \
    || { echo "BLOCKED: Julia $julia_v no tiene las actualizaciones de seguridad (minimo $min_julia)" >&2; exit 3; }
[ "$julia_v" = "$expected_julia" ] || { echo "FAILED: julia no es $expected_julia" >&2; exit 4; }
echo "parche de seguridad (>= $min_julia): OK"
echo "pkg config: JULIA_PKG_OFFLINE=${JULIA_PKG_OFFLINE:-unset} JULIA_PKG_SERVER='${JULIA_PKG_SERVER-unset}'"
[ "${JULIA_PKG_OFFLINE:-}" = true ] || { echo "BLOCKED: JULIA_PKG_OFFLINE debe ser true" >&2; exit 3; }
[ -z "${JULIA_PKG_SERVER-x}" ] || { echo "BLOCKED: JULIA_PKG_SERVER debe estar vacio" >&2; exit 3; }
pkg_v=$($J -e 'using Pkg; print(pkgversion(Pkg))')
echo "pkg $pkg_v"

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-julia-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp -R "$src" "$work/hola"
chmod -R u+w "$work/hola"
cd "$work/hola"
mkdir bad

# 1) Pkg: instantiate sin red y el Manifest no cambia
man_before=$(cksum Manifest.toml)
$J --project=. -e 'using Pkg; Pkg.instantiate(); Pkg.status()' > bad/pkg.txt 2>&1 \
    || { cat bad/pkg.txt >&2; echo "FAILED: Pkg.instantiate" >&2; exit 4; }
[ "$(cksum Manifest.toml)" = "$man_before" ] || { echo "FAILED: Pkg modifico Manifest.toml" >&2; exit 4; }
echo "pkg instantiate (offline) OK"

# 2) julia ejecuta el ejemplo
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: 10 8 6 4 2\nResultado: 10/2 = 5, 1/0 -> division por cero')
out=$($J --project=. hola.jl) || { echo "FAILED: julia hola.jl" >&2; exit 4; }
echo "$out"
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada de hola.jl" >&2; exit 4; }
echo "julia hola.jl OK"

# 3) Un error de sintaxis tiene que fallar
printf 'function roto(\n' > bad/roto.jl
if $J bad/roto.jl >/dev/null 2>&1; then echo "FAILED: julia acepto un error de sintaxis" >&2; exit 4; fi
echo "julia rechaza error de sintaxis: OK"

# 4) Pkg.test con la biblioteca estandar Test
$J --project=. -e 'using Pkg; Pkg.test()' > bad/ok.txt 2>&1 || { cat bad/ok.txt >&2; echo "FAILED: Pkg.test" >&2; exit 4; }
grep -Eq '^Saludo +\| +4 +4 ' bad/ok.txt || { cat bad/ok.txt >&2; echo "FAILED: no pasaron las 4 pruebas" >&2; exit 4; }
echo "Test Summary: Saludo 4/4"
echo "pkg test OK"

# 5) Fail-closed: una prueba rota tiene que hacer fallar a Pkg.test
sed -i 's/suma_hasta(10) == 55/suma_hasta(10) == 56/' test/runtests.jl
if $J --project=. -e 'using Pkg; Pkg.test()' > bad/out.txt 2>&1; then echo "FAILED: Pkg.test no detecto una prueba rota" >&2; exit 4; fi
grep -Eq '^Saludo +\| +3 +1 +4 ' bad/out.txt || { echo "FAILED: Pkg.test fallo por otro motivo" >&2; cat bad/out.txt >&2; exit 4; }
sed -i 's/suma_hasta(10) == 56/suma_hasta(10) == 55/' test/runtests.jl
echo "pkg test detecta prueba rota: OK"

# 6) Fail-closed: sin red no se puede agregar un paquete nuevo del registro
mkdir extra
if (cd extra && $J --project=. -e 'using Pkg; Pkg.add("JSON")' >/dev/null 2>&1); then
    echo "FAILED: Pkg instalo un paquete nuevo sin red" >&2; exit 4
fi
echo "offline bloquea paquetes nuevos: OK"

# 7) Fail-closed: un Project.toml desincronizado del Manifest.toml debe fallar
mkdir lock && cp -R Project.toml Manifest.toml src lock/
sed -i 's/^Printf = "de0858da-6303-5e67-8744-51eddeeeb8d7"$/&\nDates = "ade2ca70-3891-5945-98fb-dc099432e06a"/' lock/Project.toml
if (cd lock && $J --project=. -e 'using Pkg; Pkg.instantiate()' >/dev/null 2>&1); then
    echo "FAILED: Pkg acepto un Manifest desincronizado" >&2; exit 4
fi
echo "pkg detecta manifest desincronizado: OK"

echo "PASS: toolchain Julia $expected_julia (Pkg $pkg_v offline + Test) OK"
