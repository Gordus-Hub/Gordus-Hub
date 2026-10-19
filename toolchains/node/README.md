# Toolchain Node.js / TypeScript — Gordus-Hub

Esta carpeta arma un **entorno de JavaScript y TypeScript aislado**: una imagen Debian 13
propia, con su propio registro, sus pruebas, su flujo Kestra y su workflow de CI. Es parte de
la prioridad P2 del entorno multi‑lenguaje (después de Python, Java, Mojo, Go, C++23 y Rust).

**¿Por qué la carpeta se llama `node/` y no `js-ts/`?** Lo que se instala y se fija es el
*runtime* **Node.js** (con npm adentro); TypeScript es un paquete que corre sobre Node. Igual que
`go/` o `rust/`, la carpeta lleva el nombre de la herramienta, y además evita el guion y la
barra de "js/ts", que confunden en rutas y en nombres de imagen.

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **JavaScript (JS)** | El lenguaje de la web. Se ejecuta tal cual, sin compilar. | Scripts, servidores, herramientas. |
| **TypeScript (TS)** | JavaScript **con tipos**: escribís `n: number` y el compilador avisa si pasás un texto. | Detectar errores **antes** de ejecutar. |
| **Node.js** | El programa que **ejecuta JavaScript** fuera del navegador. | `node archivo.js`. Trae `node --test` para pruebas. |
| **LTS** | "Long Term Support": versión estable con parches de seguridad por ~30 meses. | Lo recomendado para proyectos serios. |
| **npm** | El gestor de paquetes que viene con Node. | Instala bibliotecas según `package.json`. |
| **`package.json`** | La ficha del proyecto: nombre, scripts, dependencias. | Dice qué hace falta. |
| **`package-lock.json`** | La lista **exacta** de versiones, con un hash **sha512** de cada paquete. | Todos instalan exactamente lo mismo; si un paquete fue alterado, falla. |
| **`npm ci`** | Instala **solo** lo que dice el lock (y falla si no coincide con `package.json`). | Instalaciones reproducibles. |
| **`tsc`** | El **compilador de TypeScript**: convierte `.ts` en `.js` y revisa los tipos. | `tsc --noEmit` solo revisa, sin generar archivos. |

## Versiones exactas

| Herramienta | Versión | Origen |
|---|---|---|
| Node.js | **24.22.0** (LTS "Krypton", 14/10/2026) | https://nodejs.org/dist/v24.22.0/ |
| npm | **11.19.1** | el que viene dentro de Node 24.22.0 |
| TypeScript | **7.0.2** | npm, fijado en `package.json` y `package-lock.json` |

TypeScript 7 es el **compilador nativo** (reescrito en Go): el paquete `typescript` trae un
binario por plataforma (`@typescript/typescript-linux-x64` y `-linux-arm64`), cada uno con su sha512 en el lock.

**¿Cómo se verifica Node?** Si algo no coincide, la construcción **se corta** (falla cerrado):

1. Se baja `SHASUMS256.txt` y su firma `SHASUMS256.txt.sig`, y se comprueba con **gpgv** usando la clave
   de release de Node, tomada del repo oficial `nodejs/release-keys` en un **commit fijo**
   (`481637f8…`) y aceptada solo si su huella es `C82F A3AE 1CBE DC6B E46B 9360 C43C EC45 C17A B93C`.
2. El **SHA‑256** fijado en el `Dockerfile` tiene que figurar en ese archivo firmado.
3. El tarball descargado tiene que dar ese mismo SHA‑256.

**¿Y TypeScript?** Una etapa intermedia hace `npm ci --ignore-scripts` (verifica cada sha512 del lock)
y deja los paquetes en la **caché de npm**. La imagen final trae esa caché, así que
`npm ci --offline` funciona **sin red**.

## Configuración elegida (y por qué)

| Variable | Valor | Por qué |
|---|---|---|
| `NPM_CONFIG_CACHE` | `/var/lib/gordus-node/npm-cache` | Caché de npm: escribible, fuera del código. |
| `NPM_CONFIG_PREFIX` | `/var/lib/gordus-node/npm-global` | Si alguien instala algo "global", va acá y no a `/opt/node`. |
| `NPM_CONFIG_OFFLINE` | `true` | **Sin red por defecto**: un paquete nuevo falla. Para usar red: `-e NPM_CONFIG_OFFLINE=false`. |
| `NPM_CONFIG_IGNORE_SCRIPTS` | `true` | npm **no ejecuta** scripts de instalación de paquetes (vía común de ataques). |
| `NPM_CONFIG_UPDATE_NOTIFIER` / `NO_UPDATE_NOTIFIER` | `false` / `1` | Sin aviso de "hay un npm nuevo" (no consulta internet). |
| `NPM_CONFIG_FUND` | `false` | Sin mensajes de donaciones. |
| `NPM_CONFIG_AUDIT` | `false` | `npm audit` contacta al registro; se desactiva en modo offline. |

Node.js y npm **no tienen telemetría**; lo único que "llamaba a casa" era el update-notifier, y está apagado.

## ¿Por qué está separado?

- **Python** → `ai/` · **Java 25** → `toolchains/java/` · **Mojo** → `toolchains/mojo/` · **Go** → `toolchains/go/` ·
  **C++23** → `toolchains/cpp/` · **Rust** → `toolchains/rust/` · **JDK 21 de Android** → `.devcontainer/`.
- **Node/TS** vive solo acá, con su workflow `.github/workflows/node-toolchain.yml`, que **solo corre**
  cuando cambia algo en esta carpeta.
- La imagen final **no tiene Python, ni curl, ni wget, ni gpg**, y corre con el usuario no‑root `nodeuser`.
  `/opt/node` y `/opt/gordus-node` son de solo lectura.

## Contenido de la carpeta (todo en minúsculas salvo `Dockerfile` y `README.md`)

```
toolchains/node/
├── Dockerfile                          imagen Debian 13 + Node 24.22.0 (SHA‑256 + GPG) + caché de npm
├── README.md                           este archivo
├── components.json                     registro: versiones, URLs, hashes, firma, licencias, config npm
├── examples/hola/package.json          proyecto de ejemplo (typescript 7.0.2 exacto)
├── examples/hola/package-lock.json     versiones exactas + sha512   ← subir con "Upload files"
├── examples/hola/tsconfig.json         opciones del compilador (modo estricto)
├── examples/hola/src/hola.ts           programa TypeScript
├── examples/hola/src/saludo.js         programa JavaScript (sin compilar)
├── examples/hola/test/hola.test.js     4 pruebas con node:test
├── tests/test_node_toolchain.sh        prueba de humo
├── scripts/validate_node_toolchain.py  validador fail-closed (solo biblioteca estándar)
└── kestra/node_toolchain_smoke.yaml    compuerta Kestra (falla si faltan resultados)
```

No se suben `node_modules/` ni `dist/` (se generan): el validador los rechaza.

## Cómo usarlo

```sh
# Construir la imagen (desde la raíz del repo)
docker build -f toolchains/node/Dockerfile -t gordus-node .

# Prueba de humo completa, sin red
docker run --rm --network none gordus-node sh /opt/gordus-node/tests/test_node_toolchain.sh

# Ejecutar JavaScript
docker run --rm -v "$PWD":/workspace gordus-node node mi_script.js

# Validador (en el repo, sin Docker)
python3 toolchains/node/scripts/validate_node_toolchain.py --repo-root .
```

Códigos de salida: `0` OK · `2` entrada inválida · `3` bloqueado · `4` falló.

## Licencias

- **Node.js**: MIT. **npm**: Artistic‑2.0. **TypeScript**: Apache‑2.0.

## Límites

- La caché offline trae **solo** TypeScript (y su binario para la arquitectura de la imagen).
  Otros paquetes necesitan red (`-e NPM_CONFIG_OFFLINE=false`) y su propio `package-lock.json`.
- No hay `@types/node`: el ejemplo declara lo mínimo de `process` a mano.
- Corepack (pnpm/yarn) viene con Node pero **no** está activado.
- Node 24 está en LTS hasta abril de 2028; Node 26 pasa a LTS a fines de octubre de 2026 y se puede adoptar cuando lo sea.
- arm64 se probó emulado con QEMU; en CI solo se construye amd64.
- Estado: **candidato**, `certification: NOT_GRANTED`.
