# Toolchain Kotlin (Kotlin 2.4.21 + JDK 25 propio) — Gordus-Hub

Esta carpeta arma un **entorno de Kotlin aislado**: una imagen Debian 13 propia, con su propio
JDK, su propio registro, sus propias pruebas y su propio workflow de CI. Es parte de la
prioridad P3 del entorno multi‑lenguaje del repositorio.

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Kotlin** | Un lenguaje moderno que corre sobre la JVM (como Java, pero más corto). | Escribir programas, servidores y apps Android. |
| **`kotlinc`** | El **compilador** de Kotlin. | Convierte `hola.kt` (texto) en clases o en un `.jar`. |
| **`kotlin`** | El **lanzador**. | Ejecuta un programa Kotlin ya compilado. |
| **JDK 25** | El "motor" de Java (JVM) que Kotlin necesita para correr. | Ejecuta los `.jar` con `java -jar`. |
| **`kotlin.test`** | Biblioteca de pruebas que viene con el compilador. | Verificar que las funciones devuelvan lo esperado. |

## ¿Qué versiones se usan exactamente?

- **Kotlin 2.4.21** (JetBrains), última versión estable publicada el 08/10/2026.
  - Archivo oficial: `kotlin-compiler-2.4.21.zip` de `https://github.com/JetBrains/kotlin/releases`.
  - SHA‑256: `7cc140e76daf416a0424a5557f99afd7ca89ebd463ea1101261e3e01c33e75cd`
- **JDK Eclipse Temurin 25.0.5+8** (LTS, 22/10/2026), **propio de esta imagen** en `/opt/kotlin/jdk-25`.
  - amd64: `68982529869257d0ee6b824ec5aa270ff8b118bb438670da0b97ebdab178d7fb`
  - arm64: `bb5b2ded252f21c6090cf780b0a408ad0d83bbb557e702955643557f13231880`
  - Además del SHA‑256 se verifica la **firma GPG** de Adoptium. La clave pública está guardada en
    `keys/adoptium-release-key.asc` y su huella fijada es
    `3B04 D753 C905 0D9A 5D34 3F39 843C 48A5 65F8 F04B`. Así no hace falta bajar la clave de internet.
- Si un hash o la firma no coinciden, la construcción **se corta** (falla cerrado).

## ¿Por qué está separado?

- **Python** vive en `ai/`. El **JDK 21 de Android** vive en `.devcontainer/`.
- **Java 25** vive en `toolchains/java/` y **Scala** en `toolchains/scala/`.
- **Kotlin** vive solo acá, con **su propio JDK** (no usa el de `toolchains/java/`) y su workflow
  `.github/workflows/kotlin-toolchain.yml`, que **solo corre** cuando cambia algo en esta carpeta.

Así, actualizar Kotlin nunca puede romper Java, Scala, Python ni Android, y al revés.

## Contenido de la carpeta

```
toolchains/kotlin/
├── Dockerfile                          imagen Debian 13 con JDK 25 + kotlinc (SHA‑256 + GPG)
├── components.json                     registro de lo aprobado (versiones, URLs, hashes, licencias)
├── README.md                           este archivo
├── keys/adoptium-release-key.asc       clave pública de Adoptium (para verificar el JDK)
├── examples/hola.kt                    programa de ejemplo
├── examples/hola_test.kt               3 pruebas del ejemplo con kotlin.test
├── tests/test_kotlin_toolchain.sh      prueba completa (compilar, ejecutar, probar, fallar cerrado)
├── scripts/validate_kotlin_toolchain.py  validador fail‑closed (solo biblioteca estándar)
└── kestra/kotlin_toolchain_smoke.yaml  flujo Kestra que bloquea si la prueba no da PASS
```

## Cómo usarlo

Todos los comandos se corren desde la **raíz del repositorio**.

1. Validar que el registro y el Dockerfile coinciden:
   ```sh
   python3 toolchains/kotlin/scripts/validate_kotlin_toolchain.py --repo-root .
   ```
   Códigos de salida: `0` OK · `2` entrada inválida · `3` bloqueado · `4` fallo.

2. Construir la imagen:
   ```sh
   docker build --pull -f toolchains/kotlin/Dockerfile -t gordus-kotlin .
   ```

3. Correr la prueba dentro de la imagen, **sin internet**:
   ```sh
   docker run --rm --network none gordus-kotlin sh /opt/gordus-kotlin/tests/test_kotlin_toolchain.sh
   ```
   Debe terminar con `PASS: toolchain Kotlin 2.4.21 ...`.

4. Compilar y ejecutar tu propio código (tu carpeta se monta en `/workspace`):
   ```sh
   docker run --rm --network none -v "$PWD:/workspace" gordus-kotlin \
     sh -c 'kotlinc hola.kt -include-runtime -d /tmp/hola.jar && java -jar /tmp/hola.jar'
   ```

## Qué NO trae (a propósito)

- **Gradle / Maven**: necesitan bajar plugins y dependencias de internet en cada proyecto, y esta
  imagen trabaja **sin red**. Si más adelante hace falta, se agrega como pieza aparte y fijada.
- Python, curl, gpg y unzip **no** están en la imagen final.

## Reglas (igual que el resto del repo)

- **Falla cerrado:** si algo no coincide (versión, URL, hash, firma, usuario, aislamiento), se bloquea.
- **Sin autocertificación:** el estado es `KOTLIN_TOOLCHAIN_CANDIDATE_NOT_RUNTIME_CERTIFIED`.
- **Usuario no‑root `kotlin`**, código de solo lectura en `/opt/gordus-kotlin` y toolchain en `/opt/kotlin`.
- Para cambiar de versión: actualizar **a la vez** `Dockerfile` y `components.json`
  (versión, archivo, URL y SHA‑256) y correr el validador.
