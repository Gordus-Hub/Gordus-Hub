# Toolchain Swift (aislado)

Esta carpeta arma un entorno para programar en **Swift** dentro de su propia imagen Docker
(Debian 13). No se mezcla con Python (`ai/`) ni con los otros lenguajes de `toolchains/`.

## Qué trae

| Pieza | Versión | Para qué sirve |
|---|---|---|
| Swift (toolchain oficial de swift.org para Debian 13) | 6.4.1 (`swift-6.4.1-RELEASE`, 12/10/2026) | Lenguaje y compilador |
| `swiftc` | 6.4.1 | Compila archivos `.swift` directamente |
| `swift build` / `swift run` / `swift test` | Swift Package Manager 6.4.1 | Construir, ejecutar y probar paquetes |
| Enlazador | GNU ld 2.44 (Debian) + `ld.lld` del toolchain | Une el programa final |

El toolchain queda instalado en `/opt/swift` (programas en `/opt/swift/usr/bin`), **solo lectura**.
Las cachés que necesita Swift van en `/var/lib/gordus-swift/` (sí se puede escribir ahí).

## Seguridad (falla cerrado)

- El archivo se baja de `download.swift.org` y se verifican **dos cosas**: el SHA-256 fijado y la
  firma GPG oficial ("Swift 6.x Release Signing Key", huella `52BB7E3DE28A71BE22EC05FFEF80A866B47A981F`).
  Si cualquiera no coincide, la construcción se frena.
- Sin `swiftly` (no se actualiza solo).
- Sin internet por defecto: el ejemplo no tiene dependencias, la imagen no trae `git` ni `curl`,
  y las pruebas usan `--disable-automatic-resolution`. Si un paquete pide una dependencia externa, falla.
- Corre con un usuario común (`swiftuser`), no como administrador.
- **Sin LLDB ni REPL**: el depurador LLDB de Swift necesita Python (`libpython3`), y esta imagen
  no lleva Python para no mezclarse con `ai/`. Por eso se quitan `lldb` y `repl_swift`.
  Compilar, ejecutar y testear funciona igual.

## Cómo se usa

```sh
docker build -f toolchains/swift/Dockerfile -t gordus-swift .
docker run --rm --network none gordus-swift sh /opt/gordus-swift/tests/test_swift_toolchain.sh
```

Para trabajar con tu propio código:

```sh
docker run --rm -it -v "$PWD:/workspace" gordus-swift
swift build && swift run && swift test
```

## Archivos

- `Dockerfile`: la imagen (Debian 13 + Swift 6.4.1).
- `components.json`: el registro con la versión aprobada, URLs, hashes y la huella de la clave.
- `examples/hola/`: paquete de ejemplo. Los nombres `Package.swift`, `Sources/`, `Tests/`,
  `HolaCore`, `Hola` y `HolaCoreTests` **llevan mayúsculas a propósito**: SwiftPM los exige así.
- `tests/test_swift_toolchain.sh`: prueba versiones, `swiftc`, `swift build`, `swift run` y `swift test`.
- `scripts/validate_swift_toolchain.py`: validador (solo Python estándar) que revisa que todo coincida.
- `kestra/swift_toolchain_smoke.yaml`: flujo propio de Kestra (no va en `kestra/flows/`).

## Licencia

Swift se distribuye con **Apache-2.0 con Runtime Library Exception**: es libre, se puede usar
comercialmente, y los programas compilados no quedan obligados a esa licencia. El repo no
redistribuye Swift: solo lo descarga al armar la imagen.

Códigos de salida del validador y la prueba: `0` ok, `2` entrada inválida, `3` bloqueado, `4` fallo.
