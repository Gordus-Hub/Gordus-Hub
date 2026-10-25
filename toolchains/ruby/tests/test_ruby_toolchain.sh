#!/bin/sh
# Prueba de humo del toolchain Ruby (POSIX sh).
# Versiones, ruby ejecuta el ejemplo, ruby -c rechaza un error de sintaxis, bundle install --local
# (sin red, con Gemfile.lock congelado), Minitest via rake, y las reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${RUBY_EXAMPLE_DIR:-$here/../examples/hola}"
expected_ruby="${EXPECTED_RUBY_VERSION:-4.0.9}"
expected_gem="${EXPECTED_RUBYGEMS_VERSION:-4.0.20}"
expected_bundler="${EXPECTED_BUNDLER_VERSION:-4.0.20}"
expected_minitest="${EXPECTED_MINITEST_VERSION:-6.0.0}"
expected_rake="${EXPECTED_RAKE_VERSION:-13.3.1}"

for f in Gemfile Gemfile.lock Rakefile hola.rb lib/saludo.rb test/saludo_test.rb; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
for tool in ruby gem bundle rake; do
    command -v "$tool" >/dev/null 2>&1 || { echo "BLOCKED: falta '$tool' en PATH" >&2; exit 3; }
done

ruby_v=$(ruby -e 'print RUBY_VERSION')
echo "ruby $ruby_v"
[ "$ruby_v" = "$expected_ruby" ] || { echo "FAILED: ruby no es $expected_ruby" >&2; exit 4; }
gem_v=$(gem --version)
echo "gem $gem_v"
[ "$gem_v" = "$expected_gem" ] || { echo "FAILED: RubyGems no es $expected_gem" >&2; exit 4; }
bundler_v=$(bundle --version | sed 's/^Bundler version //')
echo "bundler $bundler_v"
[ "$bundler_v" = "$expected_bundler" ] || { echo "FAILED: Bundler no es $expected_bundler" >&2; exit 4; }
echo "bundle config: frozen=${BUNDLE_FROZEN:-unset} GEM_HOME=${GEM_HOME:-unset}"
[ "${BUNDLE_FROZEN:-}" = true ] || { echo "BLOCKED: BUNDLE_FROZEN debe ser true" >&2; exit 3; }

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-ruby-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp -R "$src" "$work/hola"
chmod -R u+w "$work/hola"
cd "$work/hola"

# 1) ruby ejecuta el ejemplo
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: 10 8 6 4 2\nResultado: 10/2 = 5, 1/0 -> division por cero')
out=$(ruby hola.rb) || { echo "FAILED: ruby hola.rb" >&2; exit 4; }
echo "$out"
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada de hola.rb" >&2; exit 4; }
echo "ruby hola.rb OK"

# 2) ruby -c revisa la sintaxis (y rechaza un archivo roto)
ruby -wc lib/saludo.rb >/dev/null || { echo "FAILED: ruby -c lib/saludo.rb" >&2; exit 4; }
mkdir bad && printf 'def roto(\n  puts "sin cerrar"\n' > bad/roto.rb
if ruby -c bad/roto.rb >/dev/null 2>&1; then echo "FAILED: ruby -c acepto un error de sintaxis" >&2; exit 4; fi
echo "ruby -c rechaza error de sintaxis: OK"

# 3) bundle install --local: solo gemas ya instaladas, Gemfile.lock congelado
lock_before=$(cksum Gemfile.lock)
bundle install --local --quiet || { echo "FAILED: bundle install --local" >&2; exit 4; }
[ "$(cksum Gemfile.lock)" = "$lock_before" ] || { echo "FAILED: bundler modifico Gemfile.lock" >&2; exit 4; }
mt_v=$(bundle exec ruby -e 'require "minitest"; print Minitest::VERSION')
echo "minitest $mt_v"
[ "$mt_v" = "$expected_minitest" ] || { echo "FAILED: minitest no es $expected_minitest" >&2; exit 4; }
rake_v=$(bundle exec rake --version | sed 's/^rake, version //')
echo "rake $rake_v"
[ "$rake_v" = "$expected_rake" ] || { echo "FAILED: rake no es $expected_rake" >&2; exit 4; }
echo "bundle install --local OK"

# 4) Minitest via rake
bundle exec rake test || { echo "FAILED: rake test" >&2; exit 4; }
echo "minitest OK"

# 5) Fail-closed: una prueba que falla tiene que hacer fallar a Minitest
cp test/saludo_test.rb bad/falla_test.rb
sed -i 's/assert_equal 55,/assert_equal 56,/' bad/falla_test.rb
if (cd bad && bundle exec ruby falla_test.rb > out.txt 2>&1); then
    echo "FAILED: Minitest no detecto una prueba rota" >&2; exit 4
fi
grep -q "4 runs, 4 assertions, 1 failures" bad/out.txt || { echo "FAILED: Minitest fallo por otro motivo" >&2; cat bad/out.txt >&2; exit 4; }
echo "minitest detecta prueba rota: OK"

# 6) Fail-closed: sin red no se puede instalar una gema nueva
mkdir extra && printf 'source "https://rubygems.org"\ngem "left-pad", "1.0.0"\n' > extra/Gemfile
if (cd extra && BUNDLE_FROZEN=false bundle install --local >/dev/null 2>&1); then
    echo "FAILED: bundler instalo una gema nueva sin red" >&2; exit 4
fi
echo "offline bloquea gemas nuevas: OK"

# 7) Fail-closed: un Gemfile desincronizado del Gemfile.lock congelado debe fallar
mkdir lock && cp Gemfile Gemfile.lock lock/
sed -i 's/gem "rake", "13.3.1"/gem "rake", "13.3.0"/' lock/Gemfile
if (cd lock && bundle install --local >/dev/null 2>&1); then
    echo "FAILED: bundler acepto un lock desincronizado" >&2; exit 4
fi
echo "bundler bloquea lock desincronizado: OK"

echo "PASS: toolchain Ruby $expected_ruby + RubyGems $expected_gem + Bundler $expected_bundler + Minitest $expected_minitest (ruby + ruby -c + bundle --local + minitest) OK"
