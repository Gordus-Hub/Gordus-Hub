#!/bin/sh
# Prueba de humo del toolchain Node.js / TypeScript (POSIX sh).
# Versiones, node con JS, npm ci --offline (sin scripts), tsc compila + node ejecuta,
# tsc --noEmit rechaza un error de tipos, node --test y las reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${NODE_EXAMPLE_DIR:-$here/../examples/hola}"
expected_node="${EXPECTED_NODE_VERSION:-24.22.0}"
expected_npm="${EXPECTED_NPM_VERSION:-11.19.1}"
expected_tsc="${EXPECTED_TSC_VERSION:-7.0.2}"

for f in package.json package-lock.json tsconfig.json src/hola.ts src/saludo.js test/hola.test.js; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
for tool in node npm npx; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done
for bad in python3 python curl wget; do
    if command -v "$bad" >/dev/null 2>&1; then echo "BLOCKED: '$bad' no debe estar en la imagen" >&2; exit 3; fi
done
[ "$(npm config get offline)" = true ] || { echo "BLOCKED: npm debe estar offline por defecto" >&2; exit 3; }
[ "$(npm config get ignore-scripts)" = true ] || { echo "BLOCKED: npm debe ignorar scripts de instalacion" >&2; exit 3; }
[ "$(npm config get update-notifier)" = false ] || { echo "BLOCKED: update-notifier debe estar apagado" >&2; exit 3; }

node_v=$(node --version)
npm_v=$(npm --version)
echo "node $node_v"
echo "npm $npm_v"
[ "$node_v" = "v$expected_node" ] || { echo "FAILED: node no es $expected_node" >&2; exit 4; }
[ "$npm_v" = "$expected_npm" ] || { echo "FAILED: npm no es $expected_npm" >&2; exit 4; }
echo "npm config: offline=$(npm config get offline) ignore-scripts=$(npm config get ignore-scripts) fund=$(npm config get fund) audit=$(npm config get audit) update-notifier=$(npm config get update-notifier)"

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-node-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp -R "$src" "$work/hola"
chmod -R u+w "$work/hola"
cd "$work/hola"
rm -rf node_modules dist

# 1) JavaScript puro
js_out=$(node src/saludo.js) || { echo "FAILED: node src/saludo.js" >&2; exit 4; }
echo "$js_out"
[ "$js_out" = "JS: Hola, Gordus-Hub! (Node v$expected_node)" ] || { echo "FAILED: salida inesperada de JS" >&2; exit 4; }

# 2) npm ci --offline: solo desde la cache, verificando los sha512 del package-lock.json
lock_before=$(cksum package-lock.json)
npm ci --offline --ignore-scripts --no-audit --no-fund --loglevel=error || { echo "FAILED: npm ci --offline" >&2; exit 4; }
[ "$(cksum package-lock.json)" = "$lock_before" ] || { echo "FAILED: npm modifico package-lock.json" >&2; exit 4; }
tsc_v=$(./node_modules/.bin/tsc --version)
echo "tsc: $tsc_v"
[ "$tsc_v" = "Version $expected_tsc" ] || { echo "FAILED: tsc no es $expected_tsc" >&2; exit 4; }
echo "npm ci --offline OK"

# 3) tsc compila y node ejecuta el resultado
./node_modules/.bin/tsc -p tsconfig.json || { echo "FAILED: tsc" >&2; exit 4; }
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: 10 8 6 4 2\nResultado: 10/2 = 5, 1/0 -> division por cero')
ts_out=$(node dist/hola.js) || { echo "FAILED: node dist/hola.js" >&2; exit 4; }
echo "$ts_out"
[ "$ts_out" = "$want" ] || { echo "FAILED: salida inesperada de TypeScript compilado" >&2; exit 4; }
echo "tsc + node OK"

# 4) tsc --noEmit debe rechazar un error de tipos
mkdir bad && cp tsconfig.json bad/ && mkdir bad/src
printf 'const n: number = "no soy un numero";\nexport { n };\n' > bad/src/roto.ts
if ./node_modules/.bin/tsc -p bad/tsconfig.json --noEmit > bad/out.txt 2>&1; then
    echo "FAILED: tsc --noEmit acepto un error de tipos" >&2; exit 4
fi
grep -q "TS2322" bad/out.txt || { echo "FAILED: tsc no reporto TS2322" >&2; cat bad/out.txt >&2; exit 4; }
echo "tsc --noEmit rechaza error de tipos (TS2322): OK"

# 5) node --test (runner integrado)
node --test test/hola.test.js || { echo "FAILED: node --test" >&2; exit 4; }
echo "node --test OK"

# 6) Fail-closed: un paquete que no esta en la cache no se puede instalar offline
mkdir extra && printf '{"name":"x","version":"1.0.0","private":true,"dependencies":{"left-pad":"1.3.0"}}\n' > extra/package.json
if (cd extra && npm install --ignore-scripts --no-audit --no-fund >/dev/null 2>&1); then
    echo "FAILED: npm instalo un paquete nuevo estando offline" >&2; exit 4
fi
echo "offline bloquea paquetes nuevos: OK"
# 7) Fail-closed: npm ci con un lock que no coincide con package.json debe fallar
mkdir lock && cp package.json package-lock.json lock/
sed -i 's/"typescript": "7.0.2"/"typescript": "7.0.1"/' lock/package.json
if (cd lock && npm ci --offline --ignore-scripts >/dev/null 2>&1); then
    echo "FAILED: npm ci acepto un lock desincronizado" >&2; exit 4
fi
echo "npm ci bloquea lock desincronizado: OK"

echo "PASS: toolchain Node $expected_node + npm $expected_npm + TypeScript $expected_tsc (js + npm ci --offline + tsc + noEmit + node --test) OK"
