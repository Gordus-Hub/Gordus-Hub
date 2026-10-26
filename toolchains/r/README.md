# Toolchain R — Gordus-Hub

Esta carpeta arma un **entorno de R aislado**: una imagen Debian 13 propia, con su registro
(`components.json`), sus pruebas, su flujo Kestra y su workflow de CI. No toca `ai/`, ni
`.devcontainer/`, ni `kestra/flows/`, ni los otros toolchains.

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **R** | Un lenguaje para estadística y análisis de datos. | `Rscript archivo.r` |
| **Paquete** | Una biblioteca de R (como una "gema" en Ruby). | Reutilizar código de otros. |
| **`install.packages()`** | El instalador de paquetes que viene dentro de R. | Instala desde el **repositorio local** de la imagen. |
| **renv** | Guarda las versiones **exactas** de los paquetes del proyecto. | `renv::restore()` con `renv.lock`. |
| **`renv.lock`** | La lista exacta de paquetes y versiones. | Que todos usen lo mismo. |
| **testthat** | La herramienta de pruebas de R. | Corre `tests/testthat/test_saludo.r`. |
| **`packages.lock`** | Los 25 paquetes CRAN con su versión y su hash **SHA-256**. | Si uno fue alterado, la construcción se corta. |

## Versiones exactas

| Herramienta | Versión | Origen |
|---|---|---|
| R | **4.6.1** (24/06/2026, la última estable) | https://cran.r-project.org/src/base/R-4/ |
| testthat | **3.3.2** | CRAN (código fuente, SHA-256 fijado) |
| renv | **1.3.1** | CRAN (código fuente, SHA-256 fijado) |
| Otros 23 paquetes | ver `packages.lock` | dependencias de testthat y renv |

## Seguridad

- **CVE-2024-27322**: un archivo `.rds` o un paquete malicioso podía ejecutar código. Afecta a
  R anterior a 4.4.0. Usamos **4.6.1**, que ya está corregida.
- El validador **bloquea** cualquier R anterior a 4.6.1 (y por lo tanto anterior a 4.4.0).
- Se revisó la base de avisos de seguridad del R Consortium: ninguno afecta a los paquetes fijados.
- **¿Cómo se verifica R?** CRAN **no publica firma GPG** del código de R ni de los paquetes.
  Por eso R se verifica con **SHA-256** (igual en dos espejos oficiales de CRAN) y **SHA-512**,
  y cada paquete con su **SHA-256** (comprobado contra el índice oficial de CRAN).

## Reglas de la imagen

- Base `debian:13-slim`, construcción en dos etapas; la imagen final **no** trae compilador, Python ni curl.
- Usuario **no root** `ruser`; el código en `/opt/gordus-r` es de **solo lectura**.
- **Sin red por defecto**: `install.packages()` y `renv` solo ven `file:///opt/gordus-r/repo`.
  Los paquetes nuevos van a `/var/lib/gordus-r/library`, nunca a `/opt`.
- Como no hay compilador en la imagen final, solo se pueden instalar paquetes de **R puro**.

## Cómo probarlo

```bash
docker build -f toolchains/r/Dockerfile -t gordus-r:local .
docker run --rm --network none gordus-r:local \
  sh /opt/gordus-r/tests/test_r_toolchain.sh
python3 toolchains/r/scripts/validate_r_toolchain.py   # exit 0 = PASS
```

Códigos de salida del validador: **0** PASS, **2** falta un archivo, **3** BLOCKED, **4** error.

## Archivos

| Archivo | Para qué |
|---|---|
| `Dockerfile` | Construye la imagen |
| `components.json` | Registro de versiones, hashes y avisos de seguridad |
| `packages.lock` | Los 25 paquetes CRAN fijados con SHA-256 |
| `rprofile.site` | Configura R para usar solo el repositorio local |
| `examples/hola/` | Ejemplo con `renv.lock` y 4 pruebas testthat |
| `tests/test_r_toolchain.sh` | Prueba de humo dentro del contenedor |
| `scripts/validate_r_toolchain.py` | Validador estático (solo biblioteca estándar) |
| `kestra/r_toolchain_smoke.yaml` | Puerta Kestra que exige las versiones fijadas |
