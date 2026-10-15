"""Traduce un PDF (por defecto de inglés a español) usando el adaptador gobernado de Argos.

Uso: python3 -m gordus_ai.pdf_translate entrada.pdf salida.txt [--source en --target es]
Códigos de salida: 0 ok, 2 entrada inválida, 3 bloqueado por un gate.
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

EXIT_OK = 0
EXIT_BAD_INPUT = 2
EXIT_BLOCKED = 3


class TranslatorAdapter(Protocol):
    def preflight(self) -> AdapterReadiness: ...

    def invoke(self, request: WorkRequest, input_text: str) -> str: ...


def extraer_paginas(ruta_pdf: Path) -> list[str]:
    """Devuelve el texto de cada página; lanza ValueError si el PDF no se puede leer."""
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:
        raise ValueError("falta la dependencia pypdf (ai/requirements/pdf.txt)") from exc
    if not ruta_pdf.is_file():
        raise ValueError(f"no existe el archivo: {ruta_pdf}")
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


def traducir_pdf(
    ruta_pdf: str | Path,
    salida_txt: str | Path,
    origen: str = "en",
    destino: str = "es",
    adaptador: TranslatorAdapter | None = None,
) -> int:
    adaptador = adaptador if adaptador is not None else ArgosTranslateAdapter()
    ruta_pdf = Path(ruta_pdf)

    estado = adaptador.preflight()
    if not estado.ready:
        print(f"Bloqueado: {', '.join(estado.gate_codes)}", file=sys.stderr)
        return EXIT_BLOCKED

    try:
        paginas = extraer_paginas(ruta_pdf)
    except ValueError as exc:
        print(f"Entrada inválida: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    salida: list[str] = []
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
            except AdapterGateError as exc:
                print(f"Página {numero} bloqueada: {exc.gate_code}", file=sys.stderr)
                return EXIT_BLOCKED
        salida.append(f"--- Página {numero} ---\n" + "\n\n".join(traducidos))

    if not salida:
        print("Entrada inválida: el PDF no tiene texto extraíble (¿escaneado?)", file=sys.stderr)
        return EXIT_BAD_INPUT
    try:
        Path(salida_txt).write_text("\n\n".join(salida) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Entrada inválida: no se pudo escribir {salida_txt} ({exc})", file=sys.stderr)
        return EXIT_BAD_INPUT
    print(f"Listo: {salida_txt}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Traduce un PDF con el adaptador gobernado de Argos.")
    parser.add_argument("pdf", help="PDF de entrada")
    parser.add_argument("salida", help="archivo .txt de salida (UTF-8)")
    parser.add_argument("--source", default="en", help="idioma de origen (por defecto: en)")
    parser.add_argument("--target", default="es", help="idioma de destino (por defecto: es)")
    args = parser.parse_args(argv)
    return traducir_pdf(args.pdf, args.salida, args.source, args.target)


if __name__ == "__main__":
    raise SystemExit(main())
