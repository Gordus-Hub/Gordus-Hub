# Toolchain Scala (Scala 3.10.0 + JDK 25 propio) — Gordus-Hub

Esta carpeta arma un **entorno de Scala 3 aislado**: una imagen Debian 13 propia, con su propio
JDK, su propio registro, sus propias pruebas y su propio workflow de CI. Es parte de la
prioridad P3 del entorno multi‑lenguaje del repositorio.

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Scala 3** | Un lenguaje que corre sobre la JVM y mezcla estilo de objetos y funcional. | Programas, datos, servidores. |
| **`scalac`** | El **compilador** de Scala. | Convierte `hola.scala` (texto) en clases de Java. |
| **`scala`** | La herramienta **scala-cli** (viene dentro de Scala 3). | Ejecutar (`scala run`), compilar y empaquetar (`scala package`) sin configurar nada. |
| **`scaladoc`** | Generador de documentación. | Crea páginas HTML a partir de los comentarios. |
| **JDK 25** | El "motor" de Java (JVM) que Scala necesita para correr. | Ejecuta los `.jar` con `java -jar`. |

## ¿Qué versiones se usan exactamente?

- **Scala 3.10.0**, última versión estable publicada el 12/10/2026 (trae scala-cli 1.17.1 adentro).
  - Archivos oficiales de `https://github.com/scala/scala3/releases`, uno por arquitectura:
  - amd64 `scala3-3.10.0-x86_64-pc-linux.tar.gz`: `5dc94c2d4c653e29277f8b482b2c7bb90d2737838930c41422c7b253dfec1b3a`
  - arm64 `scala3-3.10.0-aarch64-pc-linux.tar.gz`: `a14242e269847cd46a80d45e2ba3f0ea3bdecda9b2b5ac78effad07adc499aea`
- **JDK Eclipse Temurin 25.0.5+8** (LTS, 22/10/2026), **propio de esta imagen** en `/opt/scala/jdk-25`.
  - amd64: `68982529869257d0ee6b824ec5aa270ff8b118bb438670da0b97ebdab178d7fb`
  - arm64: `bb5b2ded252f21c6090cf780b0a408ad0d83bbb557e702955643557f13231880`
  - Además del SHA‑256 se verifica la **firma GPG** de Adoptium con la clave guardada en
    `keys/adoptium-release-key.asc` (huella `3B04 D753 C905 0D9A 5D34 3F39 843C 48A5 65F8 F04B`).
- Si un hash o la firma no coinciden, la construcción **se corta** (falla cerrado).

## ¿Por qué está separado?

- **Python** vive en `ai/`. El **JDK 21 de Android** vive en `.devcontainer/`.
- **Java 25** vive en `toolchains/java/` y **Kotlin** en `toolchains/kotlin/`.
- **Scala** vive solo acá, con **su propio JDK** y su workflow `.github/workflows/scala-toolchain.yml`,
  que **solo corre** cuando cambia algo en esta carpeta.

## Contenido de la carpeta

```
toolchains/scala/
├── Dockerfile                          imagen Debian 13 con JDK 25 + Scala 3 (SHA‑256 + GPG)
├── components.json                     registro de lo aprobado (versiones, URLs, hashes, licencias)
├── README.md                           este archivo
├── keys/adoptium-release-key.asc       clave pública de Adoptium (para verificar el JDK)
├── examples/hola.scala                 programa de ejemplo
├── examples/hola_test.scala            3 pruebas del ejemplo (sin bibliotecas externas)
├── tests/test_scala_toolchain.sh       prueba completa (compilar, ejecutar, empaquetar, fallar cerrado)
├── scripts/validate_scala_toolchain.py validador fail‑closed (solo biblioteca estándar)
└── kestra/scala_toolchain_smoke.yaml   flujo Kestra que bloquea si la prueba no da PASS
```

## Cómo usarlo

Todos los comandos se corren desde la **raíz del repositorio**.

1. Validar que el registro y el Dockerfile coinciden:
   ```sh
   python3 toolchains/scala/scripts/validate_scala_toolchain.py --repo-root .
   ```
   Códigos de salida: `0` OK · `2` entrada inválida · `3` bloqueado · `4` fallo.

2. Construir la imagen:
   ```sh
   docker build --pull -f toolchains/scala/Dockerfile -t gordus-scala .
   ```

3. Correr la prueba dentro de la imagen, **sin internet**:
   ```sh
   docker run --rm --network none gordus-scala sh /opt/gordus-scala/tests/test_scala_toolchain.sh
   ```
   Debe terminar con `PASS: toolchain Scala 3.10.0 ...`.

4. Ejecutar tu propio código (tu carpeta se monta en `/workspace`):
   ```sh
   docker run --rm --network none -v "$PWD:/workspace" gordus-scala \
     scala run --power --offline --server=false hola.scala
   ```

## Qué NO trae (a propósito)

- **sbt / coursier / bibliotecas de internet**: la imagen trabaja **sin red**. scala-cli usa solo el
  repositorio local que viene dentro de la distribución de Scala. Si un archivo pide una
  dependencia externa (`//> using dep ...`), **falla** — y la prueba comprueba que falle.
- Python, curl y gpg **no** están en la imagen final.

## Reglas (igual que el resto del repo)

- **Falla cerrado:** si algo no coincide (versión, URL, hash, firma, usuario, aislamiento), se bloquea.
- **Sin autocertificación:** el estado es `SCALA_TOOLCHAIN_CANDIDATE_NOT_RUNTIME_CERTIFIED`.
- **Usuario no‑root `scala`**, código de solo lectura en `/opt/gordus-scala` y toolchain en `/opt/scala`.
- Para cambiar de versión: actualizar **a la vez** `Dockerfile` y `components.json` y correr el validador.
