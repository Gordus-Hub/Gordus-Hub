# Traducción en gordus_ai (guía simple)

Esta carpeta guarda **qué idiomas se pueden traducir** y las pruebas de cómo se aprobaron.
El código que traduce está en `ai/runtime/gordus_ai/`.

## ¿Qué hace?

Traduce documentos **sin internet**, usando la biblioteca **Argos Translate** (`argostranslate==1.11.0`).
Cada dirección de idioma (por ejemplo inglés → español) necesita un "modelo" propio, un archivo `.argosmodel`.
Solo se traduce si ese par de idiomas está **aprobado** en `pairs.json` y su modelo está **instalado**.
Si falta algo, el programa **se frena** (no adivina): eso se llama *fail closed*.

## Archivos de esta carpeta

| Archivo | Para qué sirve |
|---|---|
| `pairs.json` | Lista oficial de pares e idiomas aprobados (la que lee el código). |
| `language-matrix.json` y `LANGUAGE_MATRIX_ASSESSMENT.md` | Estudio de qué idiomas conviene aprobar. |
| `evidence/` | Registros (JSON) de cada vez que se actualizó `pairs.json`. |

## Cómo se definen los idiomas aceptados (`pairs.json`)

- **`approved_language_pairs`**: pares directos aprobados. Hoy son: `de→en`, `en→es`, `fr→en`, `it→en`, `pt→es`.
  Cada uno tiene versión, dirección de descarga, tamaño y su código de verificación `artifact_sha256`.
  Sin ese código de 64 caracteres, el par **no** cuenta como aprobado.
- **`approved_two_hop_routes`**: rutas de "dos saltos" pasando por inglés, aprobadas **una por una**.
  Hoy son: `de→en→es`, `fr→en→es`, `it→en→es`. Ambos saltos tienen que ser pares directos aprobados
  y la ruta tiene que tener `"explicit_two_hop_approved": true`. La calidad es menor que con un modelo directo.
- `candidate_pairs_pending_hash` y otras listas `candidate_*`: son **candidatos**, el código **nunca** los usa.
- Las licencias de los modelos siguen pendientes de revisión (`PENDING_REVIEW`): no redistribuyas los modelos.

### Regla: no se pasa por inglés sin permiso

En `policy`, `"automatic_pivot_translation": false`. Eso significa que el programa **nunca** inventa una ruta
por inglés por su cuenta. Si pedís `fr→es`, funciona solo porque la ruta `fr→en→es` está escrita y aprobada.
Si pedís un par sin aprobar, da el error `LANGUAGE_PAIR_NOT_APPROVED`.

## Los modelos no se bajan solos

En `pairs.json`, `"model_package_downloads_enabled": false`. Los traductores **no descargan nada** al usarse.
Los modelos se instalan a mano, con el script `scripts/ai/sync_argos_pairs.py`:

```bash
# 1) Ver el plan, sin cambiar nada (modo por defecto):
python3 scripts/ai/sync_argos_pairs.py
# 2) Descargar, verificar el hash e instalar los modelos de idiomas elegidos (ej. italiano):
python3 scripts/ai/sync_argos_pairs.py --languages it --download --install
```

- `--install` necesita `--download`, y vuelve a comprobar el hash antes de instalar.
- Si el modelo ya estaba aprobado y el hash no coincide, se frena (`ARTIFACT_SHA256_MISMATCH`).
- Agregar `--write` actualiza `pairs.json` y guarda un registro en `evidence/`. Hacelo solo si querés aprobar idiomas nuevos.
- Necesita `argostranslate` instalado para el paso `--install`.

## Preparar el entorno

- **Python 3.13** (lo exige `scripts/ai/preflight.sh`, igual que Debian 13).
- **Contenedor Debian 13**: `ai/runtime/Dockerfile` (base `debian:13-slim`) trae Python 3.13 y `venv`,
  usuario `ai` sin permisos de administrador, el código en `/opt/gordus-ai` de solo lectura,
  y la carpeta de modelos `/var/lib/gordus-ai/argos-packages` (variable `ARGOS_PACKAGES_DIR`).
  La imagen **no** instala las bibliotecas: se instalan en un entorno virtual (ver abajo).
  Esa carpeta de datos hay que montarla en almacenamiento persistente si querés conservar los modelos.
- **Versiones fijas**: el registro es `ai/components.json` y las versiones exactas están en `ai/requirements/`:
  - `argos-translate.txt` → Argos Translate (obligatorio para traducir).
  - `files.txt` → formatos de oficina, EPUB y HTML.
  - `pdf.txt` → `pypdf` para PDF.

```bash
# Desde la raíz del repo (o /opt/gordus-ai dentro del contenedor):
docker build -f ai/runtime/Dockerfile -t gordus-ai .      # solo si usás el contenedor
python3.13 -m venv ~/venv-gordus
~/venv-gordus/bin/pip install -r ai/requirements/argos-translate.txt -r ai/requirements/files.txt -r ai/requirements/pdf.txt
```

## Cómo traducir un documento

Los comandos se corren desde `ai/runtime` (o con `PYTHONPATH=ai/runtime`).

**Texto y documentos** (`.txt`, `.text`, `.docx`, `.pptx`, `.odt`, `.odp`, `.epub`, `.html`, `.htm`):

```bash
python3 -m gordus_ai.file_translate carta.docx --source fr
# Resultado: carta_es.docx al lado del original, con el mismo formato.
```

- `--source` es **obligatorio** (no detecta el idioma solo). `--target` por defecto es `es`.
- `--output` elige otra ruta de salida.

**PDF** (con `pypdf`):

```bash
python3 -m gordus_ai.pdf_translate informe.pdf informe_es.txt
# Por defecto: --source en --target es
```

- Saca el texto de cada página y lo traduce párrafo por párrafo.
- La salida es un `.txt` en UTF-8 con un bloque `--- Página N ---` por página. **No** conserva el diseño ni las imágenes.
- Un PDF escaneado (sin texto) da error `NO_EXTRACTABLE_TEXT`.

**En los dos casos**, `--evidence registro.jsonl` agrega un registro de auditoría encadenado
(solo códigos de verificación, nunca el texto), según PUAC2 §11/§28.

### Códigos de salida

| Código | Significa |
|---|---|
| `0` | Todo OK. |
| `2` | Entrada inválida (archivo que no existe, extensión no soportada, PDF sin texto). |
| `3` | Bloqueado: par no aprobado, modelo no instalado o falta una biblioteca. |

## Pruebas

```bash
python3 -m unittest discover -s ai/runtime/tests
```

Las pruebas usan un traductor de mentira, así que no necesitan modelos ni internet.
