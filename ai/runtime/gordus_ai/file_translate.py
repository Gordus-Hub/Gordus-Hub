"""Traduce archivos de texto y ofimática a español mediante el adaptador gobernado de Argos.

Formatos: .txt/.text, .html/.htm, .docx, .pptx, .odt, .odp, .epub. La salida conserva el
formato y se escribe junto a la entrada como ``nombre_<destino>.ext`` (o en --output).
Los formatos ofimáticos y EPUB usan argos-translate-files (ai/requirements/files.txt);
texto y HTML se implementan acá para forzar UTF-8 y aceptar la extensión .text.

Todo texto pasa por ``ArgosTranslateAdapter.invoke`` con un ``WorkRequest``: solo se usan
pares directos aprobados o rutas de dos saltos aprobadas explícitamente en pairs.json.
No hay detección automática de idioma: --source es obligatorio.

Uso: python3 -m gordus_ai.file_translate entrada.docx --source fr [--target es] [--output salida.docx]
     [--evidence log.jsonl]   (evento encadenado por hash, PUAC2 §11/§28; nunca guarda texto)
Códigos de salida: 0 ok, 2 entrada inválida o extensión no soportada, 3 bloqueado por un gate.
"""

from __future__ import annotations

import argparse
import itertools
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .adapters import AdapterGateError
from .argos_adapter import ArgosTranslateAdapter
from .contracts import AdapterReadiness, WorkRequest
from .evidence import append_event, sha256_file, utc_now

EXIT_OK = 0
EXIT_BAD_INPUT = 2
EXIT_BLOCKED = 3

TEXT_EXTENSIONS = frozenset({".txt", ".text"})
HTML_EXTENSIONS = frozenset({".html", ".htm"})
LIBRARY_EXTENSIONS = frozenset({".docx", ".pptx", ".odt", ".odp", ".epub"})
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | HTML_EXTENSIONS | LIBRARY_EXTENSIONS


class TranslatorAdapter(Protocol):
    def preflight(self) -> AdapterReadiness: ...

    def invoke(self, request: WorkRequest, input_text: str) -> str: ...


@dataclass(frozen=True)
class _Language:
    code: str


class GovernedTranslation:
    """Objeto compatible con ``argostranslate.translate.ITranslation`` (translate, from_lang,
    to_lang) que manda cada fragmento al adaptador gobernado como un WorkRequest."""

    def __init__(self, adaptador: TranslatorAdapter, origen: str, destino: str, prefijo: str) -> None:
        self.adaptador = adaptador
        self.from_lang = _Language(origen)
        self.to_lang = _Language(destino)
        self._prefijo = prefijo
        self._contador = itertools.count(1)
        self.fragmentos = 0

    def translate(self, input_text: str) -> str:
        if not input_text.strip():
            return input_text
        pedido = WorkRequest.from_mapping({
            "request_id": f"{self._prefijo}-{next(self._contador)}"[:128],
            "task": "translate",
            "text": input_text,
            "parameters": {"source_language": self.from_lang.code, "target_language": self.to_lang.code},
        })
        self.fragmentos += 1
        return self.adaptador.invoke(pedido, pedido.text)


def ruta_salida(entrada: Path, destino: str) -> Path:
    return entrada.with_name(f"{entrada.stem}_{destino}{entrada.suffix}")


def _traducir_texto(traduccion: GovernedTranslation, entrada: Path, salida: Path) -> None:
    contenido = entrada.read_text(encoding="utf-8")
    bloques = contenido.split("\n\n")  # por párrafo, conservando las líneas en blanco
    salida.write_text("\n\n".join(traduccion.translate(bloque) for bloque in bloques), encoding="utf-8")


def _traducir_html(traduccion: GovernedTranslation, entrada: Path, salida: Path) -> None:
    import translatehtml

    contenido = entrada.read_text(encoding="utf-8")
    cabecera = ""
    if contenido.lstrip().lower().startswith("<!doctype"):
        fin = contenido.index(">") + 1
        cabecera, contenido = contenido[:fin], contenido[fin:]
    salida.write_text(cabecera + str(translatehtml.translate_html(traduccion, contenido)), encoding="utf-8")


def _traducir_con_libreria(traduccion: GovernedTranslation, entrada: Path, salida: Path) -> None:
    from argostranslatefiles import argostranslatefiles

    if not zipfile.is_zipfile(entrada):
        raise ValueError(f"no es un contenedor {entrada.suffix} válido: {entrada}")
    formato = next(
        (f for f in argostranslatefiles.get_supported_formats()
         if entrada.suffix.lower() in f.supported_file_extensions),
        None,
    )
    if formato is None:
        raise ValueError(f"argos-translate-files no soporta {entrada.suffix}")
    # La librería escribe <nombre>_<destino>.ext junto a la entrada: trabajamos en un temporal.
    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / f"entrada{entrada.suffix.lower()}"
        shutil.copyfile(entrada, copia)
        generado = Path(formato.translate(traduccion, str(copia)))
        shutil.move(str(generado), salida)


RESULTADOS = {EXIT_OK: "SUCCEEDED", EXIT_BAD_INPUT: "REJECTED", EXIT_BLOCKED: "BLOCKED"}
TOOL_ID = "gordus_ai.file_translate"
TOOL_VERSION = "1.1.0"


def traducir_archivo(
    ruta: str | Path,
    origen: str,
    destino: str = "es",
    salida: str | Path | None = None,
    adaptador: TranslatorAdapter | None = None,
    evidencia: str | Path | None = None,
) -> int:
    """Traduce y, si se indica ``evidencia``, agrega un evento encadenado (solo hashes) al log."""
    inicio = utc_now()
    entrada = Path(ruta)
    codigo, motivo, extra = _traducir_archivo(entrada, origen, destino, salida, adaptador)
    if evidencia is not None:
        destino_final = extra.pop("output_path", None)
        append_event(
            evidencia, "TRANSLATION_RUN", "translate_file", RESULTADOS.get(codigo, "FAILED"), TOOL_ID, TOOL_VERSION,
            inicio, exit_code=codigo, reason_code=motivo, source_language=origen, target_language=destino,
            input_format=entrada.suffix.lower(), input_sha256=sha256_file(entrada) if entrada.is_file() else None,
            output_sha256=sha256_file(destino_final) if codigo == EXIT_OK and destino_final else None, **extra,
        )
    return codigo


def _traducir_archivo(
    entrada: Path, origen: str, destino: str, salida: str | Path | None, adaptador: TranslatorAdapter | None,
) -> tuple[int, str, dict]:
    extension = entrada.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        print(f"Entrada inválida: extensión no soportada '{entrada.suffix}' "
              f"(soportadas: {', '.join(sorted(SUPPORTED_EXTENSIONS))})", file=sys.stderr)
        return EXIT_BAD_INPUT, "UNSUPPORTED_EXTENSION", {}
    if not origen or not destino or origen == destino:
        print("Entrada inválida: --source y --target deben ser códigos distintos", file=sys.stderr)
        return EXIT_BAD_INPUT, "INVALID_LANGUAGE_ARGUMENTS", {}

    adaptador = adaptador if adaptador is not None else ArgosTranslateAdapter()
    por_par = getattr(adaptador, "pair_readiness", None)
    estado = por_par(origen, destino) if callable(por_par) else adaptador.preflight()
    if not estado.ready:
        print(f"Bloqueado: {', '.join(estado.gate_codes)}", file=sys.stderr)
        return EXIT_BLOCKED, ",".join(estado.gate_codes), {}

    if not entrada.is_file():
        print(f"Entrada inválida: no existe el archivo: {entrada}", file=sys.stderr)
        return EXIT_BAD_INPUT, "INPUT_FILE_MISSING", {}
    destino_final = Path(salida) if salida is not None else ruta_salida(entrada, destino)
    if destino_final.suffix.lower() != extension:
        print("Entrada inválida: la salida debe tener la misma extensión que la entrada", file=sys.stderr)
        return EXIT_BAD_INPUT, "OUTPUT_EXTENSION_MISMATCH", {}

    traduccion = GovernedTranslation(adaptador, origen, destino, f"file-{entrada.stem}")
    try:
        if extension in TEXT_EXTENSIONS:
            _traducir_texto(traduccion, entrada, destino_final)
        elif extension in HTML_EXTENSIONS:
            _traducir_html(traduccion, entrada, destino_final)
        else:
            _traducir_con_libreria(traduccion, entrada, destino_final)
    except AdapterGateError as exc:
        destino_final.unlink(missing_ok=True)
        print(f"Bloqueado durante la traducción: {exc.gate_code}", file=sys.stderr)
        return EXIT_BLOCKED, exc.gate_code, {}
    except ImportError as exc:
        print(f"Bloqueado: falta dependencia ({exc.name}); ver ai/requirements/files.txt", file=sys.stderr)
        return EXIT_BLOCKED, "FILE_FORMAT_DEPENDENCY_MISSING", {}
    except (OSError, UnicodeDecodeError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        destino_final.unlink(missing_ok=True)
        print(f"Entrada inválida: no se pudo procesar {entrada} ({exc})", file=sys.stderr)
        return EXIT_BAD_INPUT, "INPUT_FILE_UNREADABLE_OR_CORRUPT", {}
    print(f"Listo: {destino_final} ({traduccion.fragmentos} fragmentos)")
    return EXIT_OK, "OK", {"fragments": traduccion.fragmentos, "output_path": destino_final}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Traduce archivos con el adaptador gobernado de Argos.")
    parser.add_argument("archivo", help="archivo de entrada (" + ", ".join(sorted(SUPPORTED_EXTENSIONS)) + ")")
    parser.add_argument("--source", required=True, help="idioma de origen (código Argos, p. ej. fr, de, pt)")
    parser.add_argument("--target", default="es", help="idioma de destino (por defecto: es)")
    parser.add_argument("--output", help="ruta de salida (por defecto: <nombre>_<destino>.<ext>)")
    parser.add_argument("--evidence", help="log JSONL de auditoría encadenado (append-only, solo hashes)")
    args = parser.parse_args(argv)
    return traducir_archivo(args.archivo, args.source, args.target, args.output, evidencia=args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())
