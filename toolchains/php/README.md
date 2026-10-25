# Toolchain PHP — Gordus-Hub

Esta carpeta arma un **entorno de PHP aislado**: una imagen Debian 13 propia, con su registro
(`components.json`), sus pruebas, su flujo Kestra y su workflow de CI. No toca `ai/`, ni
`.devcontainer/`, ni `kestra/flows/`, ni los otros toolchains.

## ⚠️ Seguridad primero (octubre 2026)

El **21/10/2026** PHP publicó parches para **dos fallos críticos** (CVSS 4.0 = **9.2**) que
permiten **ejecutar código a distancia sin contraseña**:

| CVE | Aviso | Qué pasa |
|---|---|---|
| CVE-2026-109618 | GHSA-w8hw-w9fx-j79w | RCE por corrupción de memoria al quedarse sin memoria |
| CVE-2026-109619 | GHSA-6wmf-4rv5-p3rp | RCE por estado global "viejo" entre peticiones |

Versiones **corregidas**: **8.5.12**, 8.4.27, 8.3.36 y 8.2.35. Cualquier versión menor es vulnerable.
Este toolchain usa **PHP 8.5.12** y el validador devuelve **BLOCKED** si alguien baja la versión.

Además, el 23/10/2026 PHP avisó de **CVE-2026-115560** (subida de archivos con
`session.upload_progress`), que se arreglará en la próxima versión. Mientras tanto la imagen
lo **desactiva** en `php-gordus.ini` (`session.upload_progress.enabled=0`).

Fuentes oficiales: https://www.php.net/ (noticias), https://www.php.net/ChangeLog-8.php,
https://github.com/php/php-src/security/advisories

## ¿Qué es cada cosa? (explicado fácil)

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **PHP** | Un lenguaje muy usado para páginas web y scripts. | `php archivo.php` |
| **CLI** | La versión de PHP para la terminal (sin servidor web). | Es la única que se instala acá (sin FPM ni CGI). |
| **Composer** | El gestor de paquetes de PHP. | Instala bibliotecas según `composer.json`. |
| **`composer.lock`** | La lista **exacta** de versiones. | Todos instalan lo mismo. |
| **PHPUnit** | La herramienta de pruebas de PHP. | `phpunit` corre las pruebas de `tests/`. |
| **PHAR** | Un programa PHP empaquetado en un solo archivo. | Composer y PHPUnit vienen así, **firmados**. |
| **GPG** | Firmas digitales: prueban **quién** publicó el archivo. | Si alguien lo altera, la firma falla. |

## Versiones exactas

| Herramienta | Versión | Cómo se verifica |
|---|---|---|
| PHP | **8.5.12** (21/10/2026) | firma GPG de Daniel Scherzer (release manager 8.5, `D95C 03BC 702B E951 5344 AE33 74E4 4BC9 0677 01A5`) + SHA-256 |
| Composer | **2.10.3** | firma GPG de Packagist (`161D FBE3 4288 9F01 DDAC 4E61 CBB3 D576 F2A0 946F`) + SHA-256. Es la primera versión con los parches de CVE-2026-59944 y CVE-2026-84361 |
| PHPUnit | **13.4.3** | firma GPG de Sebastian Bergmann (`D840 6D0D 8294 7747 2937 7831 4AA3 9408 6372 C20A`) + SHA-256 |

Las tres claves públicas están **guardadas en el repo**, en `keys/`. Así el CI no depende de un
servidor de claves que puede caerse. El Dockerfile y el validador comprueban que cada clave tenga
**exactamente** la huella fijada.

Si una firma o un hash no coincide, la construcción **se corta** (falla cerrado).

## Reglas de la imagen

- Base `debian:13-slim`, construcción en varias etapas; la imagen final **no** trae compilador, Python, curl ni gpg.
- Usuario **no root** `phpuser`; el código en `/opt/gordus-php` es de **solo lectura**.
- **Sin red por defecto**: `COMPOSER_DISABLE_NETWORK=1`. Composer no puede bajar nada.
- `php.ini-production` + `php-gordus.ini` (sin `expose_php`, sin mostrar errores, sin `allow_url_include`).

## Cómo probarlo

```bash
docker build --platform linux/amd64 -t gordus-php:local toolchains/php
docker run --rm --network none gordus-php:local \
  bash /opt/gordus-php/tests/test_php_toolchain.sh
python3 toolchains/php/scripts/validate_php_toolchain.py   # exit 0 = PASS
```

Códigos de salida del validador: **0** PASS, **2** falta un archivo, **3** BLOCKED (regla o versión insegura), **4** error.

## Archivos

| Archivo | Para qué |
|---|---|
| `Dockerfile` | Construye la imagen |
| `php-gordus.ini` | Ajustes de seguridad de PHP |
| `keys/*.asc` | Claves GPG públicas de PHP, Composer y PHPUnit |
| `components.json` | Registro de versiones, hashes, firmas y CVEs |
| `examples/hola/` | Ejemplo con Composer y 4 pruebas PHPUnit |
| `tests/test_php_toolchain.sh` | Prueba de humo dentro del contenedor |
| `scripts/validate_php_toolchain.py` | Validador estático (solo biblioteca estándar) |
| `kestra/php_toolchain_smoke.yaml` | Puerta Kestra que exige las versiones fijadas |
