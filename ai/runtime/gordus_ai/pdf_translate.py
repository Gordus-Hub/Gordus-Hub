"""Traduce un PDF (por defecto de inglés a español) usando el adaptador gobernado de Argos.

Uso: python3 -m gordus_ai.pdf_translate entrada.pdf salida.txt [--source en --target es] [--evidence log.jsonl]
Códigos de salida: 0 ok, 2 entrada inválida, 3 bloqueado por un gate (incluye falta de pypdf).
Con --evidence se agrega un evento encadenado por hash (PUAC2 §11/§28) con hashes de entrada
y salida, nunca el texto.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Protocol

from .adapters import AdapterGateError
from .argos_adapter import ArgosTranslateAdapter
from .contracts import AdapterReadiness, WorkRequest
from .evidence import append_event, sha256_file, utc_now

EXIT_OK = 0
EXIT_BAD_INPUT = 2
EXIT_BLOCKED = 3


class DependenciaFaltante(Exception):
    """Falta una dependencia de runtime: se trata como bloqueo (fail closed), no como entrada inválida."""


class TranslatorAdapter(Protocol):
    def preflight(self) -> AdapterReadiness: ...

    def invoke(self, request: WorkRequest, input_text: str) -> str: ...


def extraer_paginas(ruta_pdf: Path) -> list[str]:
    """Devuelve el texto de cada página; lanza ValueError si el PDF no se puede leer."""
    if not ruta_pdf.is_file():
        raise ValueError(f"no existe el archivo: {ruta_pdf}")
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise DependenciaFaltante("PDF_DEPENDENCY_MISSING") from exc
    try:
        lector = PdfReader(str(ruta_pdf))
        return [(pagina.extract_text() or "") for pagina in lector.pages]
    except (PdfReadError, OSError, ValueError) as exc:
        raise ValueError(f"PDF ilegible: {ruta_pdf} ({exc})") from exc


def dividir_parrafos(texto: str) -> list[str]:
    """Separa en párrafos por líneas en blanco y une los saltos de línea internos."""
    bloques = re.split(r"\n\s*\n", texto.strip())
    parrafos = [" ".join(linea.strip() for linea in bloque.splitlines() if linea.strip()) for bloque in bloques]
    return [parrafo for parrafo in parrafos if parrafo]


RESULTADOS = {EXIT_OK: "SUCCEEDED", EXIT_BAD_INPUT: "REJECTED", EXIT_BLOCKED: "BLOCKED"}
TOOL_ID = "gordus_ai.pdf_translate"
TOOL_VERSION = "1.1.0"


def traducir_pdf(
    ruta_pdf: str | Path,
    salida_txt: str | Path,
    origen: str = "en",
    destino: str = "es",
    adaptador: TranslatorAdapter | None = None,
    evidencia: str | Path | None = None,
) -> int:
    """Traduce y, si se indica ``evidencia``, agrega un evento encadenado (solo hashes) al log."""
    inicio = utc_now()
    codigo, motivo, extra = _traducir_pdf(Path(ruta_pdf), Path(salida_txt), origen, destino, adaptador)
    if evidencia is not None:
        append_event(
            evidencia, "TRANSLATION_RUN", "translate_pdf", RESULTADOS.get(codigo, "FAILED"), TOOL_ID, TOOL_VERSION,
            inicio, exit_code=codigo, reason_code=motivo, source_language=origen, target_language=destino,
            input_sha256=sha256_file(ruta_pdf) if Path(ruta_pdf).is_file() else None,
            output_sha256=sha256_file(salida_txt) if codigo == EXIT_OK else None, **extra,
        )
    return codigo


def _traducir_pdf(
    ruta_pdf: Path, salida_txt: Path, origen: str, destino: str, adaptador: TranslatorAdapter | None,
) -> tuple[int, str, dict]:
    adaptador = adaptador if adaptador is not None else ArgosTranslateAdapter()

    estado = adaptador.preflight()
    if not estado.ready:
        print(f"Bloqueado: {', '.join(estado.gate_codes)}", file=sys.stderr)
        return EXIT_BLOCKED, ",".join(estado.gate_codes), {}

    try:
        paginas = extraer_paginas(ruta_pdf)
    except DependenciaFaltante as exc:
        print(f"Bloqueado: {exc} (instalar ai/requirements/pdf.txt)", file=sys.stderr)
        return EXIT_BLOCKED, str(exc), {}
    except ValueError as exc:
        print(f"Entrada inválida: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT, "INPUT_PDF_MISSING_OR_UNREADABLE", {}

    salida: list[str] = []
    fragmentos = 0
    for numero, texto in enumerate(paginas, start=1):
        parrafos = dividir_parrafos(texto)
        if not parrafos:
            continue  # página vacía o escaneada sin capa de texto
        traducidos: list[str] = []
        for indice, parrafo in enumerate(parrafos, start=1):
            pedido = WorkRequest.from_mapping({
                "request_id": f"pdf-p{numero}-{indice}",
                "task": "translate",
                "text": parrafo,
                "parameters": {"source_language": origen, "target_language": destino},
            })
            try:
                traducidos.append(adaptador.invoke(pedido, pedido.text))
                fragmentos += 1
            except AdapterGateError as exc:
                print(f"Página {numero} bloqueada: {exc.gate_code}", file=sys.stderr)
                return EXIT_BLOCKED, exc.gate_code, {"page": numero}
        salida.append(f"--- Página {numero} ---\n" + "\n\n".join(traducidos))

    if not salida:
        print("Entrada inválida: el PDF no tiene texto extraíble (¿escaneado?)", file=sys.stderr)
        return EXIT_BAD_INPUT, "NO_EXTRACTABLE_TEXT", {"pages": len(paginas)}
    try:
        salida_txt.write_text("\n\n".join(salida) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Entrada inválida: no se pudo escribir {salida_txt} ({exc})", file=sys.stderr)
        return EXIT_BAD_INPUT, "OUTPUT_NOT_WRITABLE", {}
    print(f"Listo: {salida_txt}")
    return EXIT_OK, "OK", {"pages": len(paginas), "pages_translated": len(salida), "fragments": fragmentos}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Traduce un PDF con el adaptador gobernado de Argos.")
    parser.add_argument("pdf", help="PDF de entrada")
    parser.add_argument("salida", help="archivo .txt de salida (UTF-8)")
    parser.add_argument("--source", default="en", help="idioma de origen (por defecto: en)")
    parser.add_argument("--target", default="es", help="idioma de destino (por defecto: es)")
    parser.add_argument("--evidence", help="log JSONL de auditoría encadenado (append-only, solo hashes)")
    args = parser.parse_args(argv)
    return traducir_pdf(args.pdf, args.salida, args.source, args.target, evidencia=args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())
