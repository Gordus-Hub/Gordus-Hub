#!/usr/bin/env python3
"""Validador fail-closed del toolchain Go de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/,
toolchains/java/ ni toolchains/mojo/. Comprueba que toolchains/go/components.json y
toolchains/go/Dockerfile fijan exactamente la misma distribucion oficial de Go
(version, URL, archivo y SHA-256 por arquitectura), las variables de entorno
fail-closed (GOTOOLCHAIN=local, GOFLAGS=-mod=readonly, GOPROXY=off, ...), los nombres
exactos de archivos y las reglas de aislamiento.

Codigos de salida (convencion del repo):
  0  PASS        todo coincide
  2  BAD_INPUT   falta un archivo, JSON invalido o argumentos invalidos
  3  BLOCKED     una regla de politica o un pin no coincide (falla cerrado)
  4  FAILED      error inesperado o un tarball local no coincide con su SHA-256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_BAD_INPUT, EXIT_BLOCKED, EXIT_FAILED = 0, 2, 3, 4

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_ARCHES = {"amd64", "arm64"}
ARCH_SUFFIX = {"amd64": "AMD64", "arm64": "ARM64"}
GO_URL_BASE = "https://go.dev/dl"
INSTALL_PATH = "/opt/go"
STATE_ROOT = "/var/lib/gordus-go/"
REQUIRED_ENV = {
    "GOROOT": "/opt/go",
    "GOPATH": "/var/lib/gordus-go/gopath",
    "GOCACHE": "/var/lib/gordus-go/cache",
    "GOMODCACHE": "/var/lib/gordus-go/modcache",
    "GOENV": "/var/lib/gordus-go/env/go.env",
    "GOTOOLCHAIN": "local",
    "GOFLAGS": "-mod=readonly",
    "GOPROXY": "off",
    "GOSUMDB": "sum.golang.org",
    "CGO_ENABLED": "0",
}
REQUIRED_TOOLS = {"go build", "go run", "go mod", "go test", "go vet", "gofmt"}
# Nombres exactos (minusculas salvo Dockerfile/README.md): Linux distingue mayusculas.
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json",
    "examples/hola/go.mod", "examples/hola/main.go", "examples/hola/main_test.go",
    "tests/test_go_toolchain.sh", "scripts/validate_go_toolchain.py",
    "kestra/go_toolchain_smoke.yaml",
}
OPTIONAL_FILES = {"examples/hola/go.sum"}
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen Go no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen Go no debe copiar scripts/ai/",
    r"toolchains/(java|mojo)": "la imagen Go no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen Go no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen Go no debe referenciar kestra/flows/",
    r"apt-get install[^\n]*\b(python3?(\.\d+)?|golang(-[\w.]+)?)\b": "sin Python de sistema ni Go de apt",
    r"GOTOOLCHAIN=(auto|go\d|path)": "GOTOOLCHAIN debe ser local (sin descargas de toolchain)",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"GOINSECURE|GONOSUMCHECK|GONOSUMDB|GOSUMDB=off|GOFLAGS=[^\n]*-insecure": "no se desactiva la verificacion de checksums",
}


class Gate(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_dockerfile_args(text: str) -> dict[str, str]:
    args: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*ARG\s+([A-Z0-9_]+)=(\S+)\s*$", line)
        if m:
            if m.group(1) in args and args[m.group(1)] != m.group(2):
                raise Gate(EXIT_BLOCKED, f"ARG {m.group(1)} definido dos veces con valores distintos")
            args[m.group(1)] = m.group(2)
    return args


def final_stage(text: str) -> str:
    parts = re.split(r"^FROM\s", text, flags=re.M)
    return "FROM " + parts[-1] if len(parts) > 1 else text


def parse_env(stage: str) -> dict[str, str]:
    """ENV KEY=VALUE con continuaciones de linea (formato usado en el Dockerfile)."""
    env: dict[str, str] = {}
    joined = re.sub(r"\\\n", " ", stage)
    for line in joined.splitlines():
        if line.startswith("ENV "):
            for key, value in re.findall(r"([A-Z_][A-Z0-9_]*)=(\S+)", line[4:]):
                env[key] = value
    return env


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "go"
    manifest_path, dockerfile_path = base / "components.json", base / "Dockerfile"
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

    # --- nombres exactos y sin archivos sueltos
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES - OPTIONAL_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/go" + (f"; sobran: {sorted(extra)}" if extra else ""))
    for rel in present - {"Dockerfile", "README.md"}:
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "go", "toolchain == go")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("mutable_versions_allowed", False),
                      ("toolchain_auto_download_allowed", False), ("module_downloads_by_default", False),
                      ("system_python_allowed", False), ("telemetry", "off"), ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    need(manifest.get("dockerfile") == "toolchains/go/Dockerfile", "dockerfile apunta a toolchains/go/Dockerfile")
    comps = manifest.get("components")
    need(isinstance(comps, list) and len(comps) == 1 and comps[0].get("id") == "go", "exactamente un toolchain Go aprobado")
    go = comps[0]
    version = str(go.get("version", ""))
    need(re.fullmatch(r"1\.\d+\.\d+", version) is not None, f"version exacta de Go: {version}")
    need(go.get("go_version") == f"go{version}", "go_version coincide con version")
    need(go.get("install_path") == INSTALL_PATH and go.get("goroot") == INSTALL_PATH, f"install_path/goroot == {INSTALL_PATH}")
    need((go.get("license") or {}).get("value") == "BSD-3-Clause", "licencia BSD-3-Clause")
    tools = go.get("tools") or {}
    declared = {t for group in tools.values() if isinstance(group, list) for t in group}
    need(REQUIRED_TOOLS <= declared, "herramientas requeridas declaradas")
    smoke = go.get("smoke_test", "")
    need(bool(smoke) and (repo_root / smoke).is_file(), f"smoke_test existe: {smoke}")
    menv = go.get("environment") or {}
    for key, want in REQUIRED_ENV.items():
        need(menv.get(key) == want, f"components.json environment.{key} == {want}")

    # --- pines del Dockerfile
    args = parse_dockerfile_args(dockerfile)
    need(args.get("GO_VERSION") == version, "Dockerfile GO_VERSION == components.json version")
    need(args.get("GO_URL_BASE") == GO_URL_BASE, "Dockerfile GO_URL_BASE es https://go.dev/dl")
    artifacts = go.get("artifacts") or []
    need({a.get("arch") for a in artifacts} == REQUIRED_ARCHES, "artefactos amd64 + arm64")
    by_file: dict[str, str] = {}
    for art in artifacts:
        arch, suf, sha = art["arch"], ARCH_SUFFIX[art["arch"]], str(art.get("sha256", ""))
        want_file = f"go{version}.linux-{arch}.tar.gz"
        need(art.get("file") == want_file, f"{arch}: archivo oficial {want_file}")
        need(SHA256_RE.fullmatch(sha) is not None, f"{arch}: sha256 con formato valido")
        need(art.get("url") == f"{GO_URL_BASE}/{want_file}", f"{arch}: URL coincide")
        need(args.get(f"GO_FILE_{suf}") == want_file, f"{arch}: Dockerfile GO_FILE_{suf} coincide")
        need(args.get(f"GO_SHA256_{suf}") == sha, f"{arch}: Dockerfile GO_SHA256_{suf} coincide")
        by_file[want_file] = sha

    # --- imagen final: entorno, usuario, solo lectura, sin curl/python
    final = final_stage(dockerfile)
    instructions = "\n".join(l for l in dockerfile.splitlines() if not l.lstrip().startswith("#"))
    final_instr = "\n".join(l for l in final.splitlines() if not l.lstrip().startswith("#"))
    need(all(l.split()[1] == "debian:13-slim" or l.split()[1].startswith("debian:13-slim")
             for l in dockerfile.splitlines() if l.startswith("FROM ")), "todas las etapas usan debian:13-slim")
    need("sha256sum -c" in dockerfile, "Dockerfile verifica el SHA-256 (sha256sum -c)")
    fenv = parse_env(final)
    for key, want in REQUIRED_ENV.items():
        need(fenv.get(key) == want, f"ENV {key}={want} en la imagen final")
    need(fenv.get("PATH", "").startswith(f"{INSTALL_PATH}/bin:"), "PATH empieza con /opt/go/bin")
    for key in ("GOPATH", "GOCACHE", "GOMODCACHE"):
        need(fenv[key].startswith(STATE_ROOT), f"{key} bajo {STATE_ROOT}")
    need(re.search(r"\bcurl\b", final_instr) is None, "la imagen final no instala curl")
    need("COPY --from=go-fetch /opt/go /opt/go" in final, "la imagen final copia solo /opt/go de la etapa de descarga")
    need(re.search(r"^USER gouser\s*$", final, re.M) is not None, "imagen corre como usuario no-root 'gouser'")
    need("chmod -R a=rX /opt/gordus-go" in final, "codigo de solo lectura en /opt/gordus-go")
    need("chmod -R go-w /opt/go" in dockerfile, "GOROOT sin escritura para grupo/otros")
    need("telemetry/mode" in final and "printf 'off\\n'" in final, "telemetria de Go fijada en off")
    need('go env GOTOOLCHAIN)" = local' in final, "build verifica GOTOOLCHAIN=local")
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, instructions) is None, f"aislamiento: {reason}")

    # --- modulo de ejemplo sin dependencias externas
    gomod = (base / "examples/hola/go.mod").read_text(encoding="utf-8")
    need(re.search(r"^go 1\.\d+(\.\d+)?\s*$", gomod, re.M) is not None, "go.mod declara la version de Go")
    mod_go = re.search(r"^go (1\.\d+)", gomod, re.M).group(1)
    need(version == mod_go or version.startswith(mod_go + "."), f"go.mod (go {mod_go}) compatible con Go {version}")
    need(re.search(r"^(require|replace|toolchain)\b", gomod, re.M) is None, "go.mod sin dependencias externas ni directiva toolchain")

    verified = []
    for tb in tarballs:
        if not tb.is_file():
            raise Gate(EXIT_BAD_INPUT, f"no existe el tarball {tb}")
        if tb.name not in by_file:
            raise Gate(EXIT_BLOCKED, f"tarball no aprobado: {tb.name}")
        got = sha256_file(tb)
        if got != by_file[tb.name]:
            raise Gate(EXIT_FAILED, f"SHA-256 no coincide para {tb.name}: {got}")
        verified.append({"file": tb.name, "sha256": got})
        checks.append(f"tarball local verificado: {tb.name}")

    return {"checks": checks, "go_version": version, "tarballs_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[], help="tarball local de Go cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/go/scripts/validate_go_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (Go {report['go_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
