[README.md](https://github.com/user-attachments/files/33644896/README.md)
# Toolchain Mojo — Gordus-Hub

Esta carpeta arma un **entorno de Mojo aislado**: una imagen Debian 13 propia, con su
propio registro, sus propias pruebas, su propio flujo Kestra y su propio workflow de CI.
Es parte de la prioridad P1 del entorno multi‑lenguaje del repositorio (Python → Java → Mojo).

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Mojo** | Un lenguaje de programación de Modular con sintaxis parecida a Python, pero compilado y muy rápido. | Escribir programas de alto rendimiento (cálculo, IA) con estilo "pythonesco". |
| **SDK de Mojo** | El paquete completo que instala Modular: compilador, biblioteca estándar, depurador, servidor de lenguaje. | Todo lo necesario para programar en Mojo. |
| **`mojo`** | La herramienta de línea de comandos. | Punto de entrada para todo lo de abajo. |
| **`mojo run`** | Compila y ejecuta en un paso. | Probar un archivo `.mojo` rápido, sin generar binario. |
| **`mojo build`** | El **compilador**. | Genera un **binario ejecutable** (`./hola`) que corre solo. |
| `mojo repl`, `mojo format`, `mojo doc`, `mojo package`, `mojo debug` | Herramientas de desarrollo. | Consola interactiva, formatear código, documentación, empaquetar, depurar. |
| `mojo-lsp-server`, `mojo-lldb` | Soporte para editores y depurador. | Autocompletado en VS Code, depuración paso a paso. |
| **pixi** | El **gestor de paquetes y entornos** que recomienda Modular. | Descarga Mojo y sus dependencias **exactamente** como dice el archivo de bloqueo. |
| **Entorno (environment)** | Una carpeta autocontenida con Mojo + su propio Python + bibliotecas. | Que nada se mezcle con el sistema ni con otros proyectos. |
| **`pixi.toml`** | La "lista de compras": qué versión de Mojo queremos (`==1.1.0`). | Declarar dependencias. |
| **`pixi.lock`** | El "ticket": cada paquete exacto con su **SHA‑256** (79 paquetes). | Que siempre se instale lo mismo, byte por byte. |

## ¿Qué versión se usa exactamente?

- **Mojo 1.1.0** (build `8189361e`), canal oficial de Modular `https://conda.modular.com/max/`
  (método oficial: https://mojolang.org/docs/manual/install).
- **pixi 0.82.0**, binario oficial de https://github.com/prefix-dev/pixi/releases, verificado por SHA‑256:
  - amd64: `d305406a7630aab6484419833f9204b2fe9ea40632da8bb536496f123ca86e7f`
  - arm64: `b18dadba196c0c77781533184ec3e7757422c0ae9bed0047ff7ca1c688c0f62b`
- La imagen instala con **`pixi install --locked`**: si `pixi.lock` no coincide con `pixi.toml`,
  o si un paquete descargado no coincide con su SHA‑256, **la construcción se corta** (falla cerrado).
- Entorno instalado en **`/opt/mojo/env/.pixi/envs/default`** (variable `MOJO_ENV`), con su `bin/` en el `PATH`.

## Licencia (importante)

- El **SDK de Mojo** (paquetes `mojo` y `mojo-compiler`) se distribuye bajo la
  **Modular MAX Community License** (última modificación 18/08/2026,
  https://www.modular.com/legal/community). Permite usarlo gratis, también comercialmente,
  con condiciones: conservar avisos, atribución si se redistribuye, y la cláusula 2.1
  dice que el uso **puede recolectar telemetría**.
- El **código fuente del lenguaje Mojo y su biblioteca estándar** (github.com/modular/modular)
  es **Apache 2.0 con excepción LLVM**.
- Este repo **no redistribuye** el SDK: solo lo referencia y lo descarga al construir la imagen.
- **pixi** es BSD‑3‑Clause. El Python del entorno (conda‑forge) es PSF.

## ¿Por qué está separado?

- **Python de gordus_ai** vive en `ai/` (imagen `ai/runtime/Dockerfile`).
- **Java 25** vive en `toolchains/java/`.
- **El JDK 21 de Android** vive en `.devcontainer/`.
- **Mojo** vive solo acá, en `toolchains/mojo/`, con su workflow `.github/workflows/mojo-toolchain.yml`,
  que **solo corre** cuando cambia algo en esta carpeta.

Mojo trae **su propio Python** (3.13, dentro del entorno pixi) para la interoperabilidad.
Ese Python **no toca** el del sistema (la imagen no tiene Python de sistema) ni el de `gordus_ai`.

## ¿Funciona en Windows?

**Mojo no corre nativamente en Windows.** En Windows usá esta **imagen Docker**
(Docker Desktop) o **WSL** con Ubuntu 22.04 o superior. En Linux necesita glibc 2.34+ y,
en PCs x86‑64, un procesador **x86‑64‑v3** (Haswell, ~2013, o más nuevo).

## Contenido de la carpeta (todos los nombres en minúsculas salvo `Dockerfile` y `README.md`)

```
toolchains/mojo/
├── Dockerfile                          imagen Debian 13 + pixi (SHA‑256) + Mojo (pixi install --locked)
├── components.json                     registro: versiones, URLs, hashes, licencia, herramientas
├── README.md                           este archivo
├── env/pixi.toml                       manifiesto del entorno Mojo (mojo ==1.1.0)
├── env/pixi.lock                       lock con los 79 paquetes y sus SHA‑256
├── examples/hola.mojo                  programa de ejemplo
├── examples/interop_python.mojo        Mojo llamando al Python del entorno Mojo
├── tests/test_mojo_toolchain.sh        prueba: versión, mojo run, mojo build + binario, interop
├── scripts/validate_mojo_toolchain.py  validador fail‑closed (solo biblioteca estándar)
└── kestra/mojo_toolchain_smoke.yaml    flujo Kestra que bloquea si la prueba no prueba Mojo 1.1.0
```

> **Ojo con mayúsculas/minúsculas:** Linux distingue `hola.mojo` de `Hola.mojo`.
> Al subir por la web de GitHub, los nombres tienen que quedar **exactamente** así.
> El validador lo comprueba.

## Cómo usarlo

Todos los comandos se corren desde la **raíz del repositorio**.

1. Validar registro, Dockerfile, `pixi.toml` y `pixi.lock`:
   ```sh
   python3 toolchains/mojo/scripts/validate_mojo_toolchain.py --repo-root .
   ```
   Códigos de salida: `0` OK · `2` entrada inválida · `3` bloqueado · `4` fallo.

2. Construir la imagen:
   ```sh
   docker build --pull -f toolchains/mojo/Dockerfile -t gordus-mojo .
   ```

3. Correr la prueba dentro de la imagen (funciona incluso sin red):
   ```sh
   docker run --rm --network none gordus-mojo sh /opt/gordus-mojo/tests/test_mojo_toolchain.sh
   ```
   Debe terminar con `PASS: toolchain Mojo 1.1.0 (mojo run + mojo build + interop Python) OK`.

4. Ejecutar y compilar tu propio código (montando tu carpeta en `/workspace`):
   ```sh
   docker run --rm -v "$PWD:/workspace" gordus-mojo mojo run hola.mojo
   docker run --rm -v "$PWD:/workspace" gordus-mojo sh -c 'mojo build hola.mojo -o hola && ./hola'
   ```

5. Consola interactiva:
   ```sh
   docker run --rm -it gordus-mojo mojo repl
   ```

## Actualizar la versión de Mojo

1. Cambiar `mojo = "==X.Y.Z"` en `env/pixi.toml`.
2. Regenerar el lock con pixi 0.82.0: `cd toolchains/mojo/env && pixi lock`.
3. Actualizar en `components.json`: `version`, `manifest_sha256`, `lockfile_sha256`,
   `lock_package_count` y `modular_artifacts` (URLs y SHA‑256 que figuran en el lock).
4. Correr el validador: tiene que dar `PASS`.

## Reglas (igual que el resto del repo)

- **Falla cerrado:** si algo no coincide (versión, hash, lock, usuario, aislamiento), se bloquea.
- **Sin autocertificación:** estado `MOJO_TOOLCHAIN_CANDIDATE_NOT_RUNTIME_CERTIFIED`.
- **Usuario no‑root `mojo`**; SDK y código de solo lectura. Mojo escribe su caché solo en
  `/var/lib/gordus-mojo/max` (`MODULAR_HOME`).
- La imagen final **no tiene `curl`** y el evento de telemetría de "primera activación"
  del script de Modular queda desactivado; la prueba corre con `--network none`.
