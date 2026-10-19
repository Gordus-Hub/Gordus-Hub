#!/bin/sh
# Prueba de humo del toolchain Go (POSIX sh).
# go version, go run, go build + ejecutar, go vet, go test, go mod verify,
# compilacion cruzada (linux/arm64 o linux/amd64 y windows/amd64) y las reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${GO_EXAMPLE_DIR:-$here/../examples/hola}"
expected_version="${EXPECTED_GO_VERSION:-1.27.2}"

for f in go.mod main.go main_test.go; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
for tool in go gofmt; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done
[ "$(go env GOTOOLCHAIN)" = local ] || { echo "BLOCKED: GOTOOLCHAIN debe ser local" >&2; exit 3; }
case "$(go env GOFLAGS)" in *-mod=readonly*) : ;; *) echo "BLOCKED: GOFLAGS sin -mod=readonly" >&2; exit 3 ;; esac

version_out=$(go version)
echo "$version_out"
case "$version_out" in
    "go version go$expected_version "*) : ;;
    *) echo "FAILED: go version no reporta $expected_version" >&2; exit 4 ;;
esac
echo "GOROOT=$(go env GOROOT) GOPATH=$(go env GOPATH) GOTOOLCHAIN=$(go env GOTOOLCHAIN) GOPROXY=$(go env GOPROXY) GOTELEMETRY=$(go env GOTELEMETRY)"

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-go-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp "$src/go.mod" "$src/main.go" "$src/main_test.go" "$work/"
cd "$work"
arch=$(go env GOARCH)
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nGo %s linux/%s' "$expected_version" "$arch")

[ -z "$(gofmt -l .)" ] || { echo "FAILED: gofmt encontro archivos sin formatear" >&2; exit 4; }

run_out=$(go run .) || { echo "FAILED: go run" >&2; exit 4; }
echo "$run_out"
[ "$run_out" = "$want" ] || { echo "FAILED: salida inesperada de go run" >&2; exit 4; }

go build -trimpath -o hola . || { echo "FAILED: go build" >&2; exit 4; }
bin_out=$(./hola) || { echo "FAILED: ejecutar ./hola" >&2; exit 4; }
[ "$bin_out" = "$want" ] || { echo "FAILED: salida inesperada del binario" >&2; exit 4; }
echo "binario OK: ./hola ($(wc -c < hola) bytes)"

go vet ./... || { echo "FAILED: go vet" >&2; exit 4; }
echo "go vet OK"
go test -count=1 ./... || { echo "FAILED: go test" >&2; exit 4; }
mod_out=$(go mod verify) || { echo "FAILED: go mod verify" >&2; exit 4; }
echo "go mod verify: $mod_out"

# Compilacion cruzada: otra arquitectura Linux y Windows. Se verifica la cabecera del binario.
if [ "$arch" = amd64 ]; then other=arm64; else other=amd64; fi
GOOS=linux GOARCH="$other" go build -trimpath -o "hola-linux-$other" . || { echo "FAILED: cross linux/$other" >&2; exit 4; }
[ "$(od -An -c -N4 "hola-linux-$other" | tr -d ' ')" = '177ELF' ] || { echo "FAILED: linux/$other no es ELF" >&2; exit 4; }
GOOS=windows GOARCH=amd64 go build -trimpath -o hola.exe . || { echo "FAILED: cross windows/amd64" >&2; exit 4; }
[ "$(od -An -c -N2 hola.exe | tr -d ' ')" = 'MZ' ] || { echo "FAILED: hola.exe no es PE" >&2; exit 4; }
echo "cross-compile OK: linux/$other + windows/amd64"

# Fail-closed: un go.mod que pide un Go mas nuevo debe fallar (sin descargar nada).
mkdir future && printf 'module future\n\ngo 1.99\n' > future/go.mod && cp main.go future/
if (cd future && go build -o /dev/null . >/dev/null 2>&1); then
    echo "FAILED: GOTOOLCHAIN=local no bloqueo un go.mod con 'go 1.99'" >&2; exit 4
fi
echo "GOTOOLCHAIN=local bloquea toolchains ajenos: OK"

echo "PASS: toolchain Go $expected_version (run + build + vet + test + mod verify + cross) OK"
