# Toolchain Ruby — Gordus-Hub

Esta carpeta arma un **entorno de Ruby aislado**: una imagen Debian 13 propia, con su registro
(`components.json`), sus pruebas, su flujo Kestra y su workflow de CI. No toca `ai/`, ni
`.devcontainer/`, ni `kestra/flows/`, ni los otros toolchains.

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Ruby** | Un lenguaje simple y legible. | `ruby archivo.rb` |
| **Gema (gem)** | Una biblioteca de Ruby. | Reutilizar código de otros. |
| **RubyGems** | El instalador de gemas (`gem`). | Viene dentro de Ruby. |
| **Bundler** | Instala **exactamente** las gemas del proyecto (`bundle`). | Viene dentro de Ruby. |
| **`Gemfile`** | La lista de gemas que necesita el proyecto. | Dice qué hace falta. |
| **`Gemfile.lock`** | Las versiones **exactas**, con un hash **sha256** de cada gema. | Si una gema fue alterada, falla. |
| **Minitest** | La herramienta de pruebas de Ruby. | Corre `test/saludo_test.rb`. |
| **Rake** | Tareas automáticas (como `make`). | `rake test` |

## Versiones exactas

| Herramienta | Versión | Origen |
|---|---|---|
| Ruby | **4.0.9** (23/10/2026, incluye parches de seguridad) | https://www.ruby-lang.org/en/news/2026/10/23/ruby-4-0-9-released/ |
| RubyGems / Bundler | **4.0.20** | dentro de Ruby 4.0.9 |
| Minitest | **6.0.0** | gema incluida en Ruby 4.0.9 |
| Rake | **13.3.1** | gema incluida en Ruby 4.0.9 |

**¿Cómo se verifica Ruby?** ruby-lang.org **no publica firma GPG** de sus tarballs. Por eso se
exigen **dos hashes** de dos fuentes oficiales: SHA-256 (anuncio) y SHA-512 (`index.txt` de
cache.ruby-lang.org). Si alguno no coincide, la construcción **se corta**.

## Reglas de la imagen

- Base `debian:13-slim`, construcción en dos etapas; la imagen final **no** trae compilador, Python ni curl.
- Usuario **no root** `rubyuser`; el código en `/opt/gordus-ruby` es de **solo lectura**.
- **Sin red por defecto**: `BUNDLE_FROZEN=true` y `bundle install --local` (solo gemas que ya están).
- Ojo: Bundler compara los checksums al **bajar** una gema; las que ya vienen con Ruby no se
  vuelven a comprobar. Por eso el validador revisa los checksums del lock contra `components.json`.

## Cómo probarlo

```bash
docker build --platform linux/amd64 -t gordus-ruby:local toolchains/ruby
docker run --rm --network none gordus-ruby:local \
  bash /opt/gordus-ruby/tests/test_ruby_toolchain.sh
python3 toolchains/ruby/scripts/validate_ruby_toolchain.py   # exit 0 = PASS
```

Códigos de salida del validador: **0** PASS, **2** falta un archivo, **3** BLOCKED, **4** error.

## Archivos

| Archivo | Para qué |
|---|---|
| `Dockerfile` | Construye la imagen |
| `components.json` | Registro de versiones y hashes |
| `examples/hola/` | Ejemplo con Bundler, Rake y 4 pruebas Minitest |
| `tests/test_ruby_toolchain.sh` | Prueba de humo dentro del contenedor |
| `scripts/validate_ruby_toolchain.py` | Validador estático (solo biblioteca estándar) |
| `kestra/ruby_toolchain_smoke.yaml` | Puerta Kestra que exige las versiones fijadas |
