#!/usr/bin/env python3
"""Validador fail-closed del toolchain Java 25 de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/ ni de scripts/ai/.
Comprueba que toolchains/java/components.json y toolchains/java/Dockerfile fijan
exactamente el mismo JDK (version, URL, archivo y SHA-256 por arquitectura) y que
se respetan las reglas de aislamiento.

Codigos de salida (convencion del repo):
  0  PASS               todo coincide
  2  BAD_INPUT          falta un archivo, JSON invalido o argumentos invalidos
  3  BLOCKED            una regla de politica o un pin no coincide (falla cerrado)
  4  FAILED             error inesperado o un tarball local no coincide con su SHA-256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

EXIT_OK, EXIT_BAD_INPUT, EXIT_BLOCKED, EXIT_FAILED = 0, 2, 3, 4

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_TOOLS = {"javac", "java", "jar", "javadoc", "jshell", "jlink", "jdeps", "jpackage"}
REQUIRED_ARCHES = {"amd64", "arm64"}
ARCH_SUFFIX = {"amd64": "AMD64", "arm64": "ARM64"}
URL_PREFIX = "https://github.com/adoptium/temurin25-binaries/releases/download/"
EXPECTED_LICENSE = "GPL-2.0-only WITH Classpath-exception-2.0"
INSTALL_PATH = "/opt/java/jdk-25"
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen Java no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen Java no debe copiar scripts/ai/",
    r"\.devcontainer": "la imagen Java no debe referenciar .devcontainer/",
    r"openjdk-\d+-jdk|default-jdk": "el JDK no debe venir de apt (debe ser el tarball fijado)",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"\bpython3?\b": "la imagen Java no debe instalar Python",
}


class Gate(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def parse_dockerfile_args(text: str) -> dict[str, str]:
    args: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*ARG\s+([A-Z0-9_]+)=(\S+)\s*$", line)
        if m:
            if m.group(1) in args and args[m.group(1)] != m.group(2):
                raise Gate(EXIT_BLOCKED, f"ARG {m.group(1)} definido dos veces con valores distintos")
            args[m.group(1)] = m.group(2)
    return args


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "java"
    manifest_path = base / "components.json"
    dockerfile_path = base / "Dockerfile"
    for p in (manifest_path, dockerfile_path):
        if not p.is_file():
            raise Gate(EXIT_BAD_INPUT, f"falta el archivo {p}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"components.json invalido: {exc}") from exc
    dockerfile = dockerfile_path.read_text(encoding="utf-8")

    def need(cond: bool, reason: str) -> None:
        if not cond:
            raise Gate(EXIT_BLOCKED, reason)
        checks.append(reason)

    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "java", "toolchain == java")
    policy = manifest.get("policy") or {}
    need(policy.get("fail_closed") is True, "policy.fail_closed == true")
    need(policy.get("checksum_required") is True, "policy.checksum_required == true")
    need(policy.get("mutable_versions_allowed") is False, "policy.mutable_versions_allowed == false")
    need(policy.get("certification") == "NOT_GRANTED", "policy.certification == NOT_GRANTED (sin autocertificacion)")
    need(manifest.get("dockerfile") == "toolchains/java/Dockerfile", "dockerfile apunta a toolchains/java/Dockerfile")

    comps = manifest.get("components")
    need(isinstance(comps, list) and len(comps) == 1, "exactamente un JDK aprobado")
    jdk = comps[0]
    need(jdk.get("kind") == "jdk" and jdk.get("installation_enabled") is True, "componente JDK habilitado")
    need(jdk.get("feature_version") == 25, "feature_version == 25")
    version = str(jdk.get("version", ""))
    need(re.fullmatch(r"25(\.\d+)*\+\d+", version) is not None, f"version fija de JDK 25: {version}")
    need(jdk.get("release_tag") == f"jdk-{version}", "release_tag coincide con version")
    need(jdk.get("install_path") == INSTALL_PATH and jdk.get("java_home") == INSTALL_PATH, f"install_path/java_home == {INSTALL_PATH}")
    need((jdk.get("license") or {}).get("value") == EXPECTED_LICENSE, f"licencia declarada: {EXPECTED_LICENSE}")
    tools = jdk.get("tools") or {}
    declared = {t for group in tools.values() if isinstance(group, list) for t in group}
    missing = REQUIRED_TOOLS - declared
    need(not missing, f"herramientas requeridas declaradas ({', '.join(sorted(REQUIRED_TOOLS))})" + (f" faltan: {sorted(missing)}" if missing else ""))
    smoke = jdk.get("smoke_test", "")
    need(bool(smoke) and (repo_root / smoke).is_file(), f"smoke_test existe: {smoke}")

    args = parse_dockerfile_args(dockerfile)
    need(args.get("JDK_VERSION") == version, "Dockerfile JDK_VERSION == components.json version")
    need(args.get("JDK_RELEASE_TAG") == quote(f"jdk-{version}", safe="-."), "Dockerfile JDK_RELEASE_TAG coincide (URL-encoded)")
    need(args.get("JDK_URL_BASE", "") + "/" == URL_PREFIX, "Dockerfile JDK_URL_BASE es el release oficial de Adoptium")

    artifacts = jdk.get("artifacts") or []
    arches = {a.get("arch") for a in artifacts}
    need(arches == REQUIRED_ARCHES, f"artefactos para {sorted(REQUIRED_ARCHES)}")
    by_arch = {}
    for art in artifacts:
        arch = art["arch"]
        suf = ARCH_SUFFIX[arch]
        sha = str(art.get("sha256", ""))
        need(SHA256_RE.fullmatch(sha) is not None, f"{arch}: sha256 con formato valido")
        url = str(art.get("url", ""))
        need(url == f"{URL_PREFIX}{args.get('JDK_RELEASE_TAG')}/{art.get('file')}", f"{arch}: URL coincide con release/archivo")
        need(args.get(f"JDK_FILE_{suf}") == art.get("file"), f"{arch}: Dockerfile JDK_FILE_{suf} coincide")
        need(args.get(f"JDK_SHA256_{suf}") == sha, f"{arch}: Dockerfile JDK_SHA256_{suf} coincide")
        by_arch[art.get("file")] = sha

    need("sha256sum -c" in dockerfile, "Dockerfile verifica el SHA-256 (sha256sum -c)")
    need(re.search(r"^FROM debian:13-slim\b", dockerfile, re.M) is not None, "base debian:13-slim")
    need(f"JAVA_HOME={INSTALL_PATH}" in dockerfile, f"ENV JAVA_HOME={INSTALL_PATH}")
    need(f"PATH={INSTALL_PATH}/bin" in dockerfile, "PATH incluye el bin del JDK")
    need(re.search(r"^USER java\s*$", dockerfile, re.M) is not None, "imagen corre como usuario no-root 'java'")
    need("chmod -R a=rX /opt/gordus-java" in dockerfile, "codigo de solo lectura en /opt/gordus-java")
    instructions = "\n".join(l for l in dockerfile.splitlines() if not l.lstrip().startswith("#"))
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, instructions) is None, f"aislamiento: {reason}")

    verified = []
    for tb in tarballs:
        if not tb.is_file():
            raise Gate(EXIT_BAD_INPUT, f"no existe el tarball {tb}")
        if tb.name not in by_arch:
            raise Gate(EXIT_BLOCKED, f"tarball no aprobado: {tb.name}")
        got = sha256_file(tb)
        if got != by_arch[tb.name]:
            raise Gate(EXIT_FAILED, f"SHA-256 no coincide para {tb.name}: {got}")
        verified.append({"file": tb.name, "sha256": got})
        checks.append(f"tarball local verificado: {tb.name}")

    return {"checks": checks, "jdk_version": version, "tarballs_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[], help="tarball local cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/java/scripts/validate_java_toolchain.py",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "certification": "NOT_GRANTED",
    }
    try:
        detail = validate(Path(ns.repo_root).resolve(), [Path(p) for p in ns.verify_tarball])
        report.update(result="PASS", exit_code=EXIT_OK, **detail)
    except Gate as gate:
        label = {EXIT_BAD_INPUT: "BAD_INPUT", EXIT_BLOCKED: "BLOCKED", EXIT_FAILED: "FAILED"}[gate.code]
        report.update(result=label, exit_code=gate.code, reason=gate.reason)
    except Exception as exc:  # fail closed ante cualquier error inesperado
        report.update(result="FAILED", exit_code=EXIT_FAILED, reason=f"{type(exc).__name__}: {exc}")

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if ns.report:
        try:
            Path(ns.report).write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"no se pudo escribir el informe: {exc}", file=sys.stderr)
            return EXIT_FAILED
    if report["result"] == "PASS":
        print(f"PASS: {len(report['checks'])} comprobaciones OK (JDK {report['jdk_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
