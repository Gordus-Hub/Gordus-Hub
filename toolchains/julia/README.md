# Toolchain Julia (Gordus-Hub)

Esta carpeta tiene todo lo necesario para programar en **Julia**, separado del resto del
proyecto. No toca Python (`ai/`), ni los otros lenguajes de `toolchains/`, ni `.devcontainer/`.

## Que trae

| Pieza | Version | Para que sirve |
|---|---|---|
| Julia | 1.13.2 | El lenguaje: compila y ejecuta los programas `.jl` |
| Pkg | 1.13.0 | El administrador de paquetes (viene con Julia) |
| Test | 1.11.0 | Para escribir pruebas (viene con Julia) |

- **Seguridad:** Julia 1.13.2 (15/10/2026) trae actualizadas sus bibliotecas internas
  (OpenSSL, LibCURL, LibGit2, nghttp2 y Zlib) y cierra varios avisos de seguridad.
  El validador bloquea cualquier version anterior a 1.13.2.
- **Descarga segura:** se baja de julialang.org y se revisa con firma GPG (clave guardada en
  `keys/`) y con SHA-256.
- **Sin internet por defecto:** Pkg no se conecta a nada (`JULIA_PKG_OFFLINE=true`).
- Funciona en PC comun (amd64) y en ARM (arm64), sobre Debian 13.

## Como se usa

```sh
docker build --file toolchains/julia/Dockerfile --tag gordus-julia .
docker run --rm --network none gordus-julia sh /opt/gordus-julia/tests/test_julia_toolchain.sh
docker run --rm -it -v "$PWD:/workspace" gordus-julia
```

Dentro del contenedor:

```sh
julia --project=. hola.jl                    # ejecuta un programa
julia --project=. -e 'using Pkg; Pkg.test()' # corre las pruebas
```

## Archivos

- `Dockerfile`: arma la imagen (Debian 13, usuario sin permisos de root).
- `components.json`: lista de versiones y huellas exactas.
- `keys/`: clave publica oficial para revisar la firma de Julia.
- `examples/hola/`: ejemplo con `Project.toml` y `Manifest.toml` (solo usa la biblioteca estandar).
- `tests/test_julia_toolchain.sh`: prueba que todo ande.
- `scripts/validate_julia_toolchain.py`: revisa las reglas (0 = PASS, 2 = datos malos, 3 = bloqueado, 4 = fallo).
- `kestra/julia_toolchain_smoke.yaml`: control en Kestra.

`Project.toml`, `Manifest.toml` y `src/Saludo.jl` llevan mayusculas porque Julia lo exige.

## Limites

- Solo paquetes de la biblioteca estandar. Para paquetes externos haria falta internet
  (`-e JULIA_PKG_OFFLINE=false`) y agregarlos al `Manifest.toml`.
- No incluye editor ni Jupyter.
