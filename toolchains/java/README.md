# Toolchain Java (JDK 25) — Gordus-Hub

Esta carpeta arma un **entorno de Java 25 aislado**: una imagen Debian 13 propia, con su
propio registro, sus propias pruebas y su propio workflow de CI. Es la prioridad P1 del
entorno multi‑lenguaje del repositorio, después de Python.

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **JDK** (Java Development Kit) | El "kit completo" para programar en Java. | Trae el compilador, la máquina virtual y las herramientas. |
| **`javac`** | El **compilador**. | Convierte tu código `Hola.java` (texto) en `Hola.class` (bytecode). |
| **`java`** | El **runtime** (la JVM, máquina virtual de Java). | Ejecuta los `.class` o `.jar`. |
| **`jar`** | Empaquetador. | Junta muchos `.class` en un solo archivo `.jar`. |
| **`javadoc`** | Generador de documentación. | Crea páginas HTML a partir de los comentarios del código. |
| **`jshell`** | Consola interactiva. | Probar líneas de Java sin crear archivos. |
| **`jlink`** | Armador de runtimes. | Crea una JVM recortada solo con los módulos que tu app usa. |
| **`jdeps`** | Analizador de dependencias. | Muestra qué módulos/paquetes usa un `.jar`. |
| **`jpackage`** | Empaquetador de instaladores. | Genera paquetes nativos (`.deb`, etc.) de una app Java. |
| `javap`, `jdb`, `jcmd`, `jfr`, `keytool`… | Herramientas de diagnóstico y seguridad. | Desensamblar, depurar, perfilar, manejar certificados. |

## ¿Qué JDK se usa exactamente?

- **Eclipse Temurin 25.0.4.1+1** (Adoptium), versión LTS publicada el 18/08/2026.
- Se descarga del release oficial: `https://github.com/adoptium/temurin25-binaries/releases`.
- Cada tarball se verifica con su **SHA‑256** dentro del `Dockerfile` (`sha256sum -c`).
  Si el hash no coincide, la construcción **se corta** (falla cerrado).
  - amd64: `dbb698396d478e7fa2b1e50f4103324b2a99b90569ee27c33f2261f9215cf41e`
  - arm64: `69df11a02cfa3ef7d7ca645e03edce6778ec090e100f6ae2b42097865730ac52`
- Licencia: **GPLv2 con Classpath Exception** (`GPL-2.0-only WITH Classpath-exception-2.0`).
- Queda instalado en **`/opt/java/jdk-25`**, con `JAVA_HOME=/opt/java/jdk-25` y su `bin/` en el `PATH`.

## ¿Por qué está separado?

- **Python** vive en `ai/` y su imagen es `ai/runtime/Dockerfile`.
- El **JDK 21 de Android** vive en `.devcontainer/` (`/usr/lib/jvm/java-21-openjdk-amd64`).
- **Java 25** vive solo acá, en `toolchains/java/`, con su propia imagen y su workflow
  `.github/workflows/java-toolchain.yml`, que **solo corre** cuando cambia algo en esta carpeta.

Así, actualizar Java nunca puede romper Python ni Android, y al revés. La imagen de Java
no copia `ai/`, no instala Python y no usa el JDK de `apt`; el validador lo comprueba.

## Contenido de la carpeta

```
toolchains/java/
├── Dockerfile                      imagen Debian 13 con JDK 25 (SHA‑256 verificado)
├── components.json                 registro del JDK aprobado (versión, URL, hash, licencia, herramientas)
├── README.md                       este archivo
├── examples/Hola.java              programa de ejemplo
├── tests/test_java_toolchain.sh    prueba: javac + java + jar, y que la versión sea 25
├── scripts/validate_java_toolchain.py  validador fail‑closed (solo biblioteca estándar)
└── kestra/java_toolchain_smoke.yaml    flujo Kestra que bloquea si la prueba no prueba JDK 25
```

## Cómo usarlo

Todos los comandos se corren desde la **raíz del repositorio**.

1. Validar que el registro y el Dockerfile coinciden:
   ```sh
   python3 toolchains/java/scripts/validate_java_toolchain.py --repo-root .
   ```
   Códigos de salida: `0` OK · `2` entrada inválida · `3` bloqueado · `4` fallo.

2. Construir la imagen:
   ```sh
   docker build --pull -f toolchains/java/Dockerfile -t gordus-java25 .
   ```

3. Correr la prueba dentro de la imagen:
   ```sh
   docker run --rm gordus-java25 sh /opt/gordus-java/tests/test_java_toolchain.sh
   ```
   Debe terminar con `PASS: toolchain Java 25 (javac + java + jar) OK`.

4. Compilar y ejecutar tu propio código (montando tu carpeta en `/workspace`):
   ```sh
   docker run --rm -v "$PWD:/workspace" gordus-java25 sh -c 'javac Hola.java && java Hola'
   ```

5. Consola interactiva:
   ```sh
   docker run --rm -it gordus-java25 jshell
   ```

## Reglas (igual que el resto del repo)

- **Falla cerrado:** si algo no coincide (versión, URL, hash, usuario, aislamiento), se bloquea.
- **Sin autocertificación:** el estado es `JAVA_TOOLCHAIN_CANDIDATE_NOT_RUNTIME_CERTIFIED`.
- **Usuario no‑root `java`** y código de solo lectura en `/opt/gordus-java`.
- Para cambiar de versión: actualizar **a la vez** `Dockerfile` y `components.json`
  (versión, archivo, URL y SHA‑256 de cada arquitectura) y correr el validador.
