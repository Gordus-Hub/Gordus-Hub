# Toolchain Go — Gordus-Hub

Esta carpeta arma un **entorno de Go aislado**: una imagen Debian 13 propia, con su propio
registro, sus pruebas, su flujo Kestra y su workflow de CI. Es parte de la prioridad P1 del
entorno multi‑lenguaje del repositorio (Python → Java → Mojo → Go).

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Go** | Un lenguaje de programación de Google, simple y rápido, muy usado en servidores y herramientas. | Programas que compilan a un único binario sin dependencias. |
| **Distribución de Go** | El paquete oficial de https://go.dev/dl (un `.tar.gz`). | Trae el comando `go`, el compilador, la biblioteca estándar y las herramientas. |
| **`go build`** | El **compilador**. | Convierte tu código `.go` en un **binario ejecutable** (`./hola`). |
| **Runtime** | La parte de Go que va **dentro** de cada binario (memoria, goroutines). | Por eso el binario corre solo, sin instalar nada más. |
| **`go run`** | Compila y ejecuta en un paso. | Probar rápido sin dejar binario. |
| **Módulos (`go mod`)** | El sistema de dependencias de Go: `go.mod` dice el nombre del módulo y la versión de Go; `go.sum` guarda los hashes de las dependencias. | Saber exactamente qué código se usa. |
| `go test`, `go vet`, `gofmt` | Herramientas de desarrollo. | Pruebas automáticas, detectar errores comunes, dar formato al código. |

## ¿Qué versión se usa exactamente?

- **Go 1.27.2** (estable, publicada el 02/10/2026), de https://go.dev/dl.
- Cada tarball se verifica con el **SHA‑256** que publica `https://go.dev/dl/?mode=json`:
  - amd64: `ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5`
  - arm64: `94f3e30b8e374bc285e7dadc11e0865726b9bc6e85b841ccceaabc0214c6b7c8`
  Si no coincide, la construcción **se corta** (falla cerrado).
- Instalado en **`/opt/go`** (`GOROOT`), separado de todo lo demás, igual que `/opt/java` y `/opt/mojo`.
- Licencia: **BSD‑3‑Clause** (archivo `/opt/go/LICENSE`).

## Configuración elegida (y por qué)

| Variable | Valor | Por qué |
|---|---|---|
| `GOROOT` | `/opt/go` | Donde vive Go (solo lectura). |
| `GOPATH` / `GOCACHE` / `GOMODCACHE` | `/var/lib/gordus-go/...` | Lo único donde Go puede escribir (caché de compilación y de módulos). |
| `GOTOOLCHAIN` | `local` | Go **nunca** descarga otra versión. Si un `go.mod` pide Go 1.99, falla. |
| `GOFLAGS` | `-mod=readonly` | `go build` / `go test` no modifican `go.mod` ni `go.sum` a escondidas. |
| `GOPROXY` | `off` | Sin descargas de módulos por defecto (el ejemplo no tiene dependencias, funciona sin red). Para un proyecto con dependencias: `docker run -e GOPROXY=https://proxy.golang.org,direct ...` |
| `GOSUMDB` | `sum.golang.org` | Se **mantiene** la verificación de checksums oficial (no se desactiva). |
| `CGO_ENABLED` | `0` | Binarios estáticos; la imagen no trae compilador C. |
| Telemetría | `off` | Go por defecto está en modo `local` (no sube nada). Se fija en `off` con un archivo de solo lectura; `go telemetry on` no puede activarla. (`GOTELEMETRY` no se puede fijar con una variable de entorno.) |
| `GOENV` | archivo vacío de solo lectura | `go env -w` no puede cambiar la configuración. |

## ¿Por qué está separado?

- **Python de gordus_ai** → `ai/` · **Java 25** → `toolchains/java/` · **Mojo** → `toolchains/mojo/` ·
  **JDK 21 de Android** → `.devcontainer/`.
- **Go** vive solo acá, en `toolchains/go/`, con su workflow `.github/workflows/go-toolchain.yml`,
  que **solo corre** cuando cambia algo en esta carpeta.
- La imagen final **no tiene Python, ni curl, ni gcc**, y corre con el usuario no‑root `gouser`.

## Contenido de la carpeta (todo en minúsculas salvo `Dockerfile` y `README.md`)

```
toolchains/go/
├── Dockerfile                        imagen Debian 13 + Go 1.27.2 (SHA‑256 verificado)
├── README.md                         este archivo
├── components.json                   registro: versión, URLs, hashes, licencia, variables, herramientas
├── examples/hola/go.mod              módulo de ejemplo (sin dependencias externas, sin go.sum)
├── examples/hola/main.go             programa de ejemplo
├── examples/hola/main_test.go        prueba unitaria del ejemplo
├── tests/test_go_toolchain.sh        prueba: version, run, build, vet, test, mod verify, cross
├── scripts/validate_go_toolchain.py  validador fail‑closed (solo biblioteca estándar)
└── kestra/go_toolchain_smoke.yaml    flujo Kestra que bloquea si la prueba no prueba Go 1.27.2
```

> **Ojo con mayúsculas/minúsculas:** Linux distingue `main.go` de `Main.go`. El validador
> exige los nombres **exactos** y que no haya archivos de más en `toolchains/go/`.

## Cómo usarlo

Todos los comandos se corren desde la **raíz del repositorio**.

1. Validar:
   ```sh
   python3 toolchains/go/scripts/validate_go_toolchain.py --repo-root .
   ```
   Códigos de salida: `0` OK · `2` entrada inválida · `3` bloqueado · `4` fallo.
2. Construir la imagen:
   ```sh
   docker build --pull -f toolchains/go/Dockerfile -t gordus-go .
   ```
3. Correr la prueba (sin red):
   ```sh
   docker run --rm --network none gordus-go sh /opt/gordus-go/tests/test_go_toolchain.sh
   ```
   Debe terminar con `PASS: toolchain Go 1.27.2 (run + build + vet + test + mod verify + cross) OK`.
4. Tu propio proyecto (montado en `/workspace`):
   ```sh
   docker run --rm -v "$PWD:/workspace" gordus-go go run .
   docker run --rm -v "$PWD:/workspace" gordus-go sh -c 'go build -o app . && ./app'
   ```
5. Compilar para Windows desde Linux (compilación cruzada):
   ```sh
   docker run --rm -v "$PWD:/workspace" -e GOOS=windows -e GOARCH=amd64 gordus-go go build -o app.exe .
   ```

## Actualizar la versión de Go

1. Mirar la última estable en `https://go.dev/dl/?mode=json` (archivo, `sha256`).
2. Cambiar en el `Dockerfile`: `GO_VERSION`, `GO_FILE_*`, `GO_SHA256_*`.
3. Cambiar lo mismo en `components.json` (`version`, `go_version`, `artifacts`, `release_date`).
4. Si cambia la versión menor (1.28…), actualizar `go 1.27` en `examples/hola/go.mod`.
5. Correr el validador: tiene que dar `PASS`.

## Reglas (igual que el resto del repo)

- **Falla cerrado:** si algo no coincide (versión, hash, variables, nombres, aislamiento), se bloquea.
- **Sin autocertificación:** estado `GO_TOOLCHAIN_CANDIDATE_NOT_RUNTIME_CERTIFIED`.
