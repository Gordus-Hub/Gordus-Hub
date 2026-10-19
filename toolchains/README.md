# Toolchain Rust — Gordus-Hub

Esta carpeta arma un **entorno de Rust aislado**: una imagen Debian 13 propia, con su propio
registro, sus pruebas, su flujo Kestra y su workflow de CI. Es el primer lenguaje de la
prioridad P2 del entorno multi‑lenguaje (después de Python, Java, Mojo, Go y C++23).

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Rust** | Un lenguaje compilado, tan rápido como C++, pero que **evita errores de memoria** al compilar. | Programas rápidos y seguros (herramientas, servidores, sistemas). |
| **rustc** | El **compilador**. | Convierte tu `.rs` en un ejecutable. |
| **rust-std** | La **biblioteca estándar** (vectores, textos, archivos…). | Lo que usa todo programa Rust. |
| **Cargo** | El gestor de proyectos y paquetes. | `cargo build`, `cargo run`, `cargo test`. Lee `Cargo.toml`. |
| **`Cargo.toml`** | La "ficha" del proyecto: nombre, versión, dependencias. | Cargo exige ese nombre **con C mayúscula**. |
| **`Cargo.lock`** | La lista exacta de versiones usadas (y sus hashes). | Que todos compilen exactamente lo mismo. También va con **C mayúscula**. |
| **crates** | Así se llaman las bibliotecas de Rust (en crates.io). | El ejemplo **no usa ninguna**. |
| **rustfmt** (`cargo fmt`) | Da formato automático al código. | Estilo uniforme. |
| **clippy** (`cargo clippy`) | Revisor que avisa de errores comunes y código mejorable. | Calidad del código. |
| **Enlazador (linker)** | Une el código compilado con las bibliotecas del sistema. | Rust en Linux llama a `cc` para esto. |

## ¿Qué versión se usa exactamente?

- **Rust 1.99.1** (estable, distribución del **15/10/2026**): `rustc 1.99.1 (58cf8f9c3 2026-10-13)`,
  `cargo 1.99.1`, `rustfmt 1.10.0`, `clippy 0.1.99`.
- Se descargan los **5 componentes por separado** desde la carpeta fechada
  `https://static.rust-lang.org/dist/2026-10-15/` (no la carpeta "stable", que cambia):
  `rustc`, `rust-std`, `cargo`, `rustfmt`, `clippy`, para **amd64** y **arm64**.
- Cada archivo se verifica **dos veces**; si algo no coincide, la construcción **se corta** (falla cerrado):
  1. **SHA‑256** fijado en el `Dockerfile` (el mismo que publica el manifiesto oficial y el archivo `.sha256`).
  2. **Firma GPG** (`.asc`) con la clave oficial de Rust, fijada por su huella
     `108F 6620 5EAE B0AA A8DD 5E1C 85AB 96E6 FA1B E5FE`.
- **Sin rustup**: no hay auto‑actualizaciones ni descargas de otras versiones.
  `examples/hola/rust-toolchain.toml` fija `channel = "1.99.1"`; como no hay rustup que lo lea,
  la prueba comprueba que el `rustc` instalado coincida y falla si no. `Cargo.toml` además pide
  `rust-version = "1.99"` (Cargo se niega a compilar con un Rust más viejo).
- Instalado en **`/opt/rust`** (solo lectura), separado de todo lo demás.
- Licencia de Rust: **MIT o Apache‑2.0** (a elección).

## Configuración elegida (y por qué)

| Variable | Valor | Por qué |
|---|---|---|
| `CARGO_HOME` | `/var/lib/gordus-rust/cargo` | Registro y caché de Cargo: el único lugar escribible para Cargo. |
| `CARGO_TARGET_DIR` | `/var/lib/gordus-rust/target` | Donde quedan los binarios compilados. |
| `CARGO_NET_OFFLINE` | `true` | **Sin red por defecto**: Cargo no baja crates. Una dependencia nueva falla. Para un proyecto con dependencias: `docker run -e CARGO_NET_OFFLINE=false ...` |
| `CARGO_INCREMENTAL` | `0` | Compilaciones reproducibles y sin caché incremental grande. |
| `RUSTUP_HOME` | (no se usa) | No hay rustup. |

**Enlazador:** se usa el **gcc 14 de Debian** (`gcc-14=14.2.0-19`, `binutils=2.44-3`,
`libc6-dev=2.41-12+deb13u4`), con `cc` apuntando a `gcc-14`. Es lo que Rust espera por defecto
en Linux y es mucho más chico que clang + lld. La prueba comprueba con `readelf` que el binario
lo enlazó ese gcc.

## ¿Por qué está separado?

- **Python** → `ai/` · **Java 25** → `toolchains/java/` · **Mojo** → `toolchains/mojo/` ·
  **Go** → `toolchains/go/` · **C++23** → `toolchains/cpp/` · **JDK 21 de Android** → `.devcontainer/`.
- **Rust** vive solo acá, en `toolchains/rust/`, con su workflow `.github/workflows/rust-toolchain.yml`,
  que **solo corre** cuando cambia algo en esta carpeta.
- El gcc de esta imagen es **otro** que el de la imagen C++: no se comparten.
- La imagen final **no tiene Python, ni curl, ni wget, ni gpg, ni rustup**, y corre con el usuario no‑root `rustuser`.

## Contenido de la carpeta

```
toolchains/rust/
├── Dockerfile                          imagen Debian 13 + Rust 1.99.1 (SHA‑256 + GPG)
├── README.md                           este archivo
├── components.json                     registro: versión, URLs, hashes, firma, licencias, variables
├── examples/hola/Cargo.toml            proyecto de ejemplo (sin dependencias)       ← C mayúscula
├── examples/hola/Cargo.lock            versiones exactas (solo el propio paquete)   ← C mayúscula
├── examples/hola/rust-toolchain.toml   fija Rust 1.99.1
├── examples/hola/src/main.rs           programa + 2 pruebas unitarias
├── tests/test_rust_toolchain.sh        prueba de humo
├── scripts/validate_rust_toolchain.py  validador fail-closed (solo biblioteca estándar)
└── kestra/rust_toolchain_smoke.yaml    compuerta Kestra (falla si faltan resultados)
```

Todo va en **minúsculas**, salvo cuatro excepciones permitidas a propósito:
`Dockerfile`, `README.md`, **`Cargo.toml`** y **`Cargo.lock`** (Cargo no los encuentra si se llaman
`cargo.toml`). Linux distingue mayúsculas.

## Cómo usarlo

```sh
# Construir la imagen (desde la raíz del repo)
docker build -f toolchains/rust/Dockerfile -t gordus-rust .

# Prueba de humo completa, sin red
docker run --rm --network none gordus-rust sh /opt/gordus-rust/tests/test_rust_toolchain.sh

# Tu propio proyecto (carpeta actual montada en /workspace)
docker run --rm -it -v "$PWD":/workspace gordus-rust cargo run

# Validador (en el repo, sin Docker)
python3 toolchains/rust/scripts/validate_rust_toolchain.py --repo-root .
```

Códigos de salida: `0` OK · `2` entrada inválida · `3` bloqueado · `4` falló.

## Límites

- Solo Linux (`x86_64` y `aarch64`, glibc). No trae targets para Windows, macOS, musl ni WebAssembly.
- Sin `rust-src` ni `rust-analyzer` (no hacen falta para compilar; ahorran espacio).
- Sin documentación local (`rust-docs`): está en https://doc.rust-lang.org.
- Proyectos con crates externos necesitan red (`-e CARGO_NET_OFFLINE=false`) o una carpeta `vendor/`.
- arm64 se probó emulado con QEMU; en CI solo se construye amd64.
- Estado: **candidato**, `certification: NOT_GRANTED`.
