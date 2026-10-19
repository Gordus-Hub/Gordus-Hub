# Toolchain C++23 — Gordus-Hub

Esta carpeta arma un **entorno de C++23 aislado**: una imagen Debian 13 propia, con su propio
registro, sus pruebas, su flujo Kestra y su workflow de CI. Es el último paso de la prioridad P1
del entorno multi‑lenguaje del repositorio (Python → Java → Mojo → Go → C++23).

## ¿Qué es C++23?

**C++** es un lenguaje compilado muy rápido, usado en motores de juegos, navegadores, bases de
datos y sistemas. Cada pocos años sale una versión nueva del estándar; **C++23** es la de 2023
(publicada como ISO/IEC 14882:2024). Un compilador en modo C++23 informa `__cplusplus == 202302`.

Novedades de C++23 que usa el ejemplo:

- `std::print` / `std::println` (`<print>`): imprimir con formato, más simple que `std::cout`.
- `std::expected` (`<expected>`): devolver "un valor **o** un error" sin excepciones.
- `std::ranges` y vistas (`std::views::iota`, `filter`, `zip`, `fold_left`…): trabajar con listas sin bucles manuales.
- `import std;`: importar toda la biblioteca estándar como **módulo** (ver límites abajo).

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Compilador** | Programa que traduce tu `.cpp` a código máquina. Acá hay **dos**: **g++ 14** (GCC) y **clang++ 19** (LLVM). | Tener dos compiladores detecta errores que uno solo deja pasar. |
| **Biblioteca estándar** | El código que trae `std::vector`, `std::print`, etc. **libstdc++ 14** (de GCC, por defecto) y **libc++ 19** (de LLVM, con `-stdlib=libc++`). | Cada una implementa partes distintas de C++23. |
| **Enlazador (linker)** | Une los pedazos compilados (`.o`) y las bibliotecas en un ejecutable. | Sin él no hay binario. |
| **CMake** | Describe el proyecto (`CMakeLists.txt`) y genera las instrucciones de compilación. | Mismo proyecto en Linux, Windows o macOS. |
| **Ninja** / **make** | Ejecutan esas instrucciones (compilan solo lo que cambió). | Ninja es más rápido; make es el clásico. |
| **pkg-config** | Dice qué opciones necesita una biblioteca instalada. | Usar bibliotecas del sistema. |
| **clang-format** | Da formato automático al código. | Estilo uniforme. |
| **clang-scan-deps** | Lee qué módulos importa cada archivo. | CMake lo necesita para `import std`. |

## Versiones exactas (paquetes oficiales de Debian 13 "trixie")

| Herramienta | Versión | Paquete Debian fijado |
|---|---|---|
| GCC / g++ | 14.2.0 | `g++-14=14.2.0-19` (+ `gcc-14`, `cpp-14`, `libstdc++-14-dev`) |
| Clang / clang++ | 19.1.7 | `clang-19=1:19.1.7-3+b1` |
| libc++ | 19.1.7 | `libc++-19-dev`, `libc++abi-19-dev` `=1:19.1.7-3+b1` |
| LLD (enlazador) | 19.1.7 | `lld-19=1:19.1.7-3+b1` |
| GNU ld (enlazador) | 2.44 | `binutils=2.44-3` |
| CMake | 3.31.6 | `cmake=3.31.6-2` |
| Ninja | 1.12.1 | `ninja-build=1.12.1-1` (amd64) / `1.12.1-1+b1` (arm64) |
| make | 4.4.1 | `make=4.4.1-2` |
| pkg-config | 1.8.1 (pkgconf) | `pkg-config=1.8.1-4` |
| cabeceras de glibc | 2.41 | `libc6-dev=2.41-12+deb13u4` |

**¿Cómo se verifica?** apt comprueba la **firma** de Debian sobre el índice del repositorio y el
**SHA‑256** de cada `.deb`. Además cada paquete principal se instala como `paquete=versión`
exacta: si Debian publica otra versión, la construcción **falla** (falla cerrado) y hay que
actualizar a la vez `Dockerfile` y `components.json`. Las dependencias secundarias las elige apt
dentro de Debian 13 (no se fijan una por una).

`clang-scan-deps` y `clang-format` vienen en paquetes que **dependen de Python**. Para que la
imagen final no tenga Python, se instalan en una etapa aparte y se copian **solo esos dos
binarios**, verificando su SHA‑256.

No se usó **apt.llvm.org**: el clang 19 de Debian está firmado y alcanza para C++23.

## Enlazador elegido (y por qué)

- **GNU ld 2.44** (de binutils) es el **predeterminado**: es el estándar de Debian y lo usan g++ y clang++ sin opciones extra.
- **LLD 19** está disponible con `-fuse-ld=lld`: más rápido y el compañero natural de clang + libc++. La prueba comprueba con `readelf` qué enlazador armó cada binario.
- **No** se instalaron `gold` (obsoleto en binutils) ni `mold` (no hace falta con ld + lld).

## ¿Qué funciona de C++23? (medido, no supuesto)

| Función | g++ 14 + libstdc++ | clang++ 19 + libstdc++ | clang++ 19 + libc++ |
|---|---|---|---|
| `std::print` | sí | sí | sí |
| `std::expected` | sí | sí | sí |
| ranges (`zip`, `fold_left`) | sí | sí | sí (libc++ aún no marca la macro `__cpp_lib_ranges_zip`) |
| `std::generator` | sí | sí | **no** |
| `std::mdspan` | **no** | **no** | sí |
| `std::flat_map` | **no** | **no** | **no** |
| `std::stacktrace` | sí (enlazar con `-lstdc++exp`) | sí (`-lstdc++exp`) | **no** |
| "deducing this" (`this` explícito) | sí | sí (clang 19 no define la macro) | sí |
| `import std;` | **no** (llega en GCC 15) | **no** | **sí**, con CMake + Ninja |

Cada fila se comprobó **compilando y ejecutando** un programa pequeño en la imagen (no solo
mirando las macros `__cpp_lib_*`, que a veces no coinciden con lo que funciona).

`import std` con CMake 3.31 es **experimental**: se activa con
`CMAKE_EXPERIMENTAL_CXX_IMPORT_STD` (ver `tests/test_cpp_toolchain.sh`), con clang++ y libc++.

## ¿Por qué está separado?

- **Python de gordus_ai** → `ai/` · **Java 25** → `toolchains/java/` · **Mojo** → `toolchains/mojo/` ·
  **Go** → `toolchains/go/` · **JDK 21 de Android** → `.devcontainer/`.
- **C++** vive solo acá, en `toolchains/cpp/`, con su workflow `.github/workflows/cpp-toolchain.yml`,
  que **solo corre** cuando cambia algo en esta carpeta.
- El gcc que usa Mojo vive dentro de la imagen de Mojo; este es otro, en otra imagen. No se mezclan.
- La imagen final **no tiene Python, ni curl, ni wget**, corre con el usuario no‑root `cppuser`
  y el código de `/opt/gordus-cpp` es de solo lectura.

## Contenido de la carpeta

```
toolchains/cpp/
├── Dockerfile                          imagen Debian 13 + g++ 14 + clang 19 (paquetes fijados)
├── README.md                           este archivo
├── components.json                     registro: versiones, licencias, funciones C++23
├── examples/hola/CMakeLists.txt        proyecto CMake de ejemplo (C++23)
├── examples/hola/main.cpp              programa de ejemplo (print, expected, ranges)
├── tests/test_cpp_toolchain.sh         prueba de humo (compiladores, linkers, CMake, import std)
├── scripts/validate_cpp_toolchain.py   validador fail-closed (solo biblioteca estándar)
└── kestra/cpp_toolchain_smoke.yaml     compuerta Kestra (falla si faltan resultados)
```

Los nombres van en minúsculas salvo `Dockerfile`, `README.md` y `CMakeLists.txt` (así lo exige CMake).
Linux distingue mayúsculas: `main.CPP` **no** es `main.cpp`.

## Cómo usarlo

```sh
# Construir la imagen (desde la raíz del repo)
docker build -f toolchains/cpp/Dockerfile -t gordus-cpp .

# Prueba de humo completa, sin red
docker run --rm --network none gordus-cpp sh /opt/gordus-cpp/tests/test_cpp_toolchain.sh

# Compilar tu propio proyecto (carpeta actual montada en /workspace)
docker run --rm -it -v "$PWD":/workspace gordus-cpp \
  sh -c 'cmake -S . -B build && cmake --build build'

# Validador (en el repo, sin Docker)
python3 toolchains/cpp/scripts/validate_cpp_toolchain.py --repo-root .
```

Códigos de salida del validador y de la prueba: `0` OK · `2` entrada inválida · `3` bloqueado · `4` falló.

## Licencias

- **GCC / libstdc++**: GPL‑3.0 **con la GCC Runtime Library Exception** (tus programas compilados no quedan bajo GPL).
- **LLVM / clang / libc++ / LLD**: Apache‑2.0 **con LLVM exception**.
- binutils y make: GPL‑3.0; CMake: BSD‑3‑Clause; Ninja: Apache‑2.0; pkgconf: ISC; glibc: LGPL‑2.1.

## Límites (honestos)

- **No hay depurador**: `gdb` y `clang-tidy` dependen de Python y quedaron afuera.
- **No hay gestor de paquetes** (Conan, vcpkg): las bibliotecas externas hay que agregarlas aparte.
- `import std` solo con clang++ + libc++ y es experimental en CMake 3.31.
- Los pines `paquete=versión` dependen de que Debian siga publicando esa versión; cuando sale una
  actualización (por ejemplo de seguridad) la construcción falla y hay que subir las versiones.
  Para reproducir exactamente lo mismo en el futuro se puede usar `snapshot.debian.org` (no activado).
- arm64 se probó emulado con QEMU; en CI solo se construye amd64.
- Estado: **candidato**, `certification: NOT_GRANTED`.
