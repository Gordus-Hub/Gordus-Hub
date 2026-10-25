#!/bin/sh
# Prueba de humo del toolchain PHP (POSIX sh).
# Versiones, parche de seguridad (>= 8.5.12), mitigaciones de php.ini, php ejecuta el ejemplo,
# php -l rechaza un error de sintaxis, composer validate + install sin red, PHPUnit, y las
# reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${PHP_EXAMPLE_DIR:-$here/../examples/hola}"
expected_php="${EXPECTED_PHP_VERSION:-8.5.12}"
expected_composer="${EXPECTED_COMPOSER_VERSION:-2.10.3}"
expected_phpunit="${EXPECTED_PHPUNIT_VERSION:-13.4.3}"
# Minimo con el parche de CVE-2026-109618 y CVE-2026-109619 (php.net, 21/10/2026).
min_php_id=80512

for f in composer.json composer.lock phpunit.xml hola.php src/saludo.php tests/SaludoTest.php; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
for tool in php composer phpunit; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done

php_v=$(php -r 'echo PHP_VERSION;')
echo "php $php_v"
php -r "exit(PHP_VERSION_ID >= $min_php_id ? 0 : 3);" \
    || { echo "BLOCKED: PHP $php_v no tiene el parche de seguridad (minimo 8.5.12)" >&2; exit 3; }
[ "$php_v" = "$expected_php" ] || { echo "FAILED: php no es $expected_php" >&2; exit 4; }
echo "parche de seguridad (>= 8.5.12): OK"
sapi=$(php -r 'echo PHP_SAPI;')
[ "$sapi" = cli ] || { echo "BLOCKED: SAPI inesperado: $sapi" >&2; exit 3; }
for b in php-cgi php-fpm phpdbg; do
    if command -v "$b" >/dev/null 2>&1; then echo "BLOCKED: no debe existir $b" >&2; exit 3; fi
done
upl=$(php -r 'echo ini_get("session.upload_progress.enabled");')
fbt=$(php -r 'echo ini_get("fatal_error_backtraces");')
expo=$(php -r 'echo ini_get("expose_php");')
echo "php.ini: session.upload_progress.enabled=$upl fatal_error_backtraces=$fbt expose_php=$expo"
[ "$upl" = 0 ] && [ "$fbt" = 0 ] && [ -z "$expo" ] || { echo "BLOCKED: faltan mitigaciones de php.ini" >&2; exit 3; }
for ext in dom json libxml mbstring openssl phar tokenizer xml xmlwriter; do
    php -r "exit(extension_loaded('$ext') ? 0 : 1);" || { echo "BLOCKED: falta la extension $ext" >&2; exit 3; }
done
composer_v=$(composer --version 2>/dev/null | awk '/^Composer version/ {print $3; exit}')
echo "composer $composer_v"
[ "$composer_v" = "$expected_composer" ] || { echo "FAILED: Composer no es $expected_composer" >&2; exit 4; }
phpunit_v=$(phpunit --version | awk '/^PHPUnit/ {print $2; exit}')
echo "phpunit $phpunit_v"
[ "$phpunit_v" = "$expected_phpunit" ] || { echo "FAILED: PHPUnit no es $expected_phpunit" >&2; exit 4; }
echo "composer config: COMPOSER_DISABLE_NETWORK=${COMPOSER_DISABLE_NETWORK:-unset} COMPOSER_NO_AUDIT=${COMPOSER_NO_AUDIT:-unset}"
[ "${COMPOSER_DISABLE_NETWORK:-}" = 1 ] || { echo "BLOCKED: COMPOSER_DISABLE_NETWORK debe ser 1" >&2; exit 3; }

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-php-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp -R "$src" "$work/hola"
chmod -R u+w "$work/hola"
cd "$work/hola"
rm -rf vendor .phpunit.cache

# 1) php -l revisa la sintaxis (y rechaza un archivo roto)
for f in hola.php src/saludo.php tests/SaludoTest.php; do
    php -l "$f" >/dev/null || { echo "FAILED: php -l $f" >&2; exit 4; }
done
mkdir bad && printf '<?php\nfunction roto( {\n' > bad/roto.php
if php -l bad/roto.php >/dev/null 2>&1; then echo "FAILED: php -l acepto un error de sintaxis" >&2; exit 4; fi
echo "php -l rechaza error de sintaxis: OK"

# 2) composer validate + install sin red (solo arma el autoload)
lock_before=$(cksum composer.lock)
composer validate --strict --no-interaction >/dev/null || { echo "FAILED: composer validate --strict" >&2; exit 4; }
composer install --no-interaction --no-progress --quiet || { echo "FAILED: composer install" >&2; exit 4; }
[ "$(cksum composer.lock)" = "$lock_before" ] || { echo "FAILED: composer modifico composer.lock" >&2; exit 4; }
[ -f vendor/autoload.php ] || { echo "FAILED: composer no genero vendor/autoload.php" >&2; exit 4; }
echo "composer validate + install OK"

# 3) php ejecuta el ejemplo
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: 10 8 6 4 2\nResultado: 10/2 = 5, 1/0 -> division por cero')
out=$(php hola.php) || { echo "FAILED: php hola.php" >&2; exit 4; }
echo "$out"
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada de hola.php" >&2; exit 4; }
echo "php hola.php OK"

# 4) PHPUnit
phpunit --do-not-record-test-run-history > bad/ok.txt 2>&1 || { cat bad/ok.txt >&2; echo "FAILED: phpunit" >&2; exit 4; }
cat bad/ok.txt
grep -qx "OK (4 tests, 4 assertions)" bad/ok.txt || { echo "FAILED: phpunit con avisos o sin las 4 pruebas" >&2; exit 4; }
echo "phpunit OK"

# 5) Fail-closed: una prueba que falla tiene que hacer fallar a PHPUnit
sed -i 's/assertSame(55,/assertSame(56,/' tests/SaludoTest.php
if phpunit --do-not-record-test-run-history > bad/out.txt 2>&1; then echo "FAILED: PHPUnit no detecto una prueba rota" >&2; exit 4; fi
grep -q "Tests: 4, Assertions: 4, Failures: 1" bad/out.txt || { echo "FAILED: PHPUnit fallo por otro motivo" >&2; cat bad/out.txt >&2; exit 4; }
sed -i 's/assertSame(56,/assertSame(55,/' tests/SaludoTest.php
echo "phpunit detecta prueba rota: OK"

# 6) Fail-closed: sin red no se puede agregar un paquete nuevo
mkdir extra && printf '{"name":"x/y","require":{"psr/log":"3.0.2"}}\n' > extra/composer.json
if (cd extra && composer install --no-interaction >/dev/null 2>&1); then
    echo "FAILED: composer instalo un paquete nuevo sin red" >&2; exit 4
fi
echo "offline bloquea paquetes nuevos: OK"

# 7) Fail-closed: un composer.json desincronizado del composer.lock debe fallar
mkdir lock && cp composer.json composer.lock lock/
sed -i 's/"php": ">=8.5.12"/"php": ">=8.5.11"/' lock/composer.json
if (cd lock && composer validate --strict --no-interaction >/dev/null 2>&1); then
    echo "FAILED: composer acepto un lock desincronizado" >&2; exit 4
fi
echo "composer bloquea lock desincronizado: OK"

echo "PASS: toolchain PHP $expected_php (parche CVE-2026-109618/109619) + Composer $expected_composer + PHPUnit $expected_phpunit (php -l + composer + php + phpunit) OK"
