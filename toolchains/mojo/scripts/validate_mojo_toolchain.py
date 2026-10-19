#!/usr/bin/env python3
"""Validador fail-closed del toolchain Mojo de Gordus-Hub.

Solo usa la biblioteca estandar de Python (3.11+ por tomllib): no importa nada de
ai/, scripts/ai/ ni toolchains/java/. Comprueba que toolchains/mojo/components.json,
toolchains/mojo/Dockerfile, env/pixi.toml y env/pixi.lock fijan exactamente lo mismo
(pixi por version + SHA-256; Mojo por version exacta + lock con SHA-256 por paquete)
y que se respetan las reglas de aislamiento.

Codigos de salida (convencion del repo):
  0  PASS        todo coincide
  2  BAD_INPUT   falta un archivo, JSON/TOML invalido o argumentos invalidos
  3  BLOCKED     una regla de politica o un pin no coincide (falla cerrado)
  4  FAILED      error inesperado o un tarball local no coincide con su SHA-256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_BAD_INPUT, EXIT_BLOCKED, EXIT_FAILED = 0, 2, 3, 4

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_ARCHES = {"amd64", "arm64"}
ARCH_SUFFIX = {"amd64": "AMD64", "arm64": "ARM64"}
REQUIRED_PLATFORMS = {"linux-64", "linux-aarch64"}
PIXI_URL_BASE = "https://github.com/prefix-dev/pixi/releases/download"
MODULAR_CHANNEL = "https://conda.modular.com/max/"
ALLOWED_LOCK_PREFIXES = ("https://conda.modular.com/max/", "https://conda.anaconda.org/conda-forge/")
MOJO_ENV = "/opt/mojo/env/.pixi/envs/default"
REQUIRED_MOJO_TOOLS = {"mojo build", "mojo run", "mojo"}
REQUIRED_FILES = (  # nombres exactos (minusculas): Linux distingue mayusculas
    "toolchains/mojo/env/pixi.toml",
    "toolchains/mojo/env/pixi.lock",
    "toolchains/mojo/examples/hola.mojo",
    "toolchains/mojo/examples/interop_python.mojo",
    "toolchains/mojo/tests/test_mojo_toolchain.sh",
    "toolchains/mojo/kestra/mojo_toolchain_smoke.yaml",
)
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen Mojo no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen Mojo no debe copiar scripts/ai/",
    r"toolchains/java": "la imagen Mojo no debe tocar toolchains/java/",
    r"\.devcontainer": "la imagen Mojo no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen Mojo no debe referenciar kestra/flows/",
    r"apt-get install[^\n]*\bpython3?(\.\d+)?\b": "no se instala Python del sistema (solo el del entorno Mojo)",
    r"\bpip3?\s+install\b|\buv\s+(pip|add)\b": "Mojo se instala solo via pixi.lock (sin pip/uv)",
    r"pixi\.sh/install\.sh|\|\s*(ba)?sh\b": "prohibido 'curl | sh' (pixi se fija por SHA-256)",
    r"--frozen\b": "usar 'pixi install --locked' (--frozen no verifica el lock)",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
}


class Gate(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def parse_lock_packages(text: str) -> tuple[int | None, list[dict[str, str]]]:
    """Lector minimo de pixi.lock (YAML) sin dependencias: version y paquetes con sha256."""
    m = re.search(r"^version:\s*(\d+)\s*$", text, re.M)
    version = int(m.group(1)) if m else None
    idx = text.find("\npackages:\n")
    if idx < 0:
        raise Gate(EXIT_BAD_INPUT, "pixi.lock sin seccion 'packages:'")
    packages: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text[idx + len("\npackages:\n"):].splitlines():
        if line.startswith("- "):
            kind, _, url = line[2:].partition(": ")
            current = {"kind": kind.strip(), "url": url.strip()}
            packages.append(current)
        elif current is not None:
            s = re.match(r"^  (sha256|license):\s*(.+?)\s*$", line)
            if s:
                current[s.group(1)] = s.group(2)
    return version, packages


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "mojo"
    paths = {
        "manifest": base / "components.json",
        "dockerfile": base / "Dockerfile",
        "pixi_toml": base / "env" / "pixi.toml",
        "pixi_lock": base / "env" / "pixi.lock",
    }
    for p in paths.values():
        if not p.is_file():
            raise Gate(EXIT_BAD_INPUT, f"falta el archivo {p}")
    try:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"components.json invalido: {exc}") from exc
    toml_bytes = paths["pixi_toml"].read_bytes()
    lock_bytes = paths["pixi_lock"].read_bytes()
    try:
        pixi_toml = tomllib.loads(toml_bytes.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"pixi.toml invalido: {exc}") from exc
    dockerfile = paths["dockerfile"].read_text(encoding="utf-8")

    def need(cond: bool, reason: str) -> None:
        if not cond:
            raise Gate(EXIT_BLOCKED, reason)
        checks.append(reason)

    # --- nombres exactos de archivos (leccion hola.java / Hola.java)
    for rel in REQUIRED_FILES:
        p = repo_root / rel
        need(p.is_file() and p.name in {c.name for c in p.parent.iterdir()}, f"archivo con nombre exacto: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "mojo", "toolchain == mojo")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("lockfile_required", True),
                      ("mutable_versions_allowed", False), ("system_python_allowed", False),
                      ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    need(manifest.get("dockerfile") == "toolchains/mojo/Dockerfile", "dockerfile apunta a toolchains/mojo/Dockerfile")
    comps = {c.get("id"): c for c in manifest.get("components") or []}
    need(set(comps) == {"pixi", "mojo-sdk"}, "componentes aprobados: pixi + mojo-sdk")
    pixi, mojo = comps["pixi"], comps["mojo-sdk"]

    # --- pixi: version + SHA-256 por arquitectura
    args = parse_dockerfile_args(dockerfile)
    pv = str(pixi.get("version", ""))
    need(re.fullmatch(r"\d+\.\d+\.\d+", pv) is not None, f"pixi con version exacta: {pv}")
    need(args.get("PIXI_VERSION") == pv, "Dockerfile PIXI_VERSION == components.json")
    need(args.get("PIXI_URL_BASE") == PIXI_URL_BASE, "Dockerfile PIXI_URL_BASE es el release oficial de prefix-dev/pixi")
    need((pixi.get("license") or {}).get("value") == "BSD-3-Clause", "pixi licencia BSD-3-Clause")
    p_arts = pixi.get("artifacts") or []
    need({a.get("arch") for a in p_arts} == REQUIRED_ARCHES, "pixi: artefactos amd64 + arm64")
    pixi_by_file: dict[str, str] = {}
    for art in p_arts:
        arch, suf, sha = art["arch"], ARCH_SUFFIX[art["arch"]], str(art.get("sha256", ""))
        need(SHA256_RE.fullmatch(sha) is not None, f"pixi {arch}: sha256 con formato valido")
        need(art.get("url") == f"{PIXI_URL_BASE}/v{pv}/{art.get('file')}", f"pixi {arch}: URL coincide con version/archivo")
        need(args.get(f"PIXI_FILE_{suf}") == art.get("file"), f"pixi {arch}: Dockerfile PIXI_FILE_{suf} coincide")
        need(args.get(f"PIXI_SHA256_{suf}") == sha, f"pixi {arch}: Dockerfile PIXI_SHA256_{suf} coincide")
        pixi_by_file[art["file"]] = sha

    # --- Mojo: version exacta en pixi.toml + hashes del manifiesto y del lock
    mv = str(mojo.get("version", ""))
    need(re.fullmatch(r"\d+\.\d+\.\d+", mv) is not None, f"Mojo con version exacta: {mv}")
    deps = pixi_toml.get("dependencies") or {}
    need(deps.get("mojo") == f"=={mv}", f"pixi.toml fija mojo == {mv}")
    ws = pixi_toml.get("workspace") or pixi_toml.get("project") or {}
    need(set(ws.get("platforms") or []) == REQUIRED_PLATFORMS and set(mojo.get("platforms") or []) == REQUIRED_PLATFORMS,
         "plataformas linux-64 + linux-aarch64 en pixi.toml y components.json")
    need((ws.get("channels") or [None])[0] == MODULAR_CHANNEL, "primer canal = canal oficial de Modular")
    need(list(ws.get("channels") or []) == list(mojo.get("conda_channels") or []), "canales coinciden con components.json")
    need(mojo.get("manifest_sha256") == sha256_bytes(toml_bytes), "SHA-256 de pixi.toml coincide con components.json")
    need(mojo.get("lockfile_sha256") == sha256_bytes(lock_bytes), "SHA-256 de pixi.lock coincide con components.json")
    need(mojo.get("install_path") == MOJO_ENV, f"install_path == {MOJO_ENV}")
    lic = mojo.get("license") or {}
    need(lic.get("value") == "LicenseRef-Modular-MAX-Community-License", "licencia Mojo SDK declarada (Modular MAX Community License)")
    tools = mojo.get("tools") or {}
    declared = {t for group in tools.values() if isinstance(group, list) for t in group}
    need(REQUIRED_MOJO_TOOLS <= declared, "herramientas Mojo declaradas (mojo, mojo run, mojo build)")
    smoke = mojo.get("smoke_test", "")
    need(bool(smoke) and (repo_root / smoke).is_file(), f"smoke_test existe: {smoke}")

    try:
        lock_version, packages = parse_lock_packages(lock_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise Gate(EXIT_BAD_INPUT, f"pixi.lock invalido: {exc}") from exc
    need(lock_version in (6, 7), f"formato de pixi.lock soportado (version {lock_version})")
    need(len(packages) > 0 and all(p["kind"] == "conda" for p in packages), "pixi.lock solo contiene paquetes conda")
    need(all(SHA256_RE.fullmatch(p.get("sha256", "")) for p in packages), f"los {len(packages)} paquetes del lock tienen SHA-256")
    need(all(p["url"].startswith(ALLOWED_LOCK_PREFIXES) for p in packages), "todos los paquetes vienen de canales aprobados (Modular, conda-forge)")
    need(mojo.get("lock_package_count") == len(packages), f"lock_package_count == {len(packages)}")
    lock_by_url = {p["url"]: p.get("sha256") for p in packages}
    for sub in ("linux-64", "linux-aarch64"):
        for name in (f"mojo-{mv}-", f"mojo-compiler-{mv}-"):
            need(any(u.startswith(f"{MODULAR_CHANNEL}{sub}/{name}") for u in lock_by_url), f"lock contiene {name}* para {sub}")
    m_arts = mojo.get("modular_artifacts") or []
    need(len(m_arts) > 0, "components.json lista los artefactos de Modular")
    for art in m_arts:
        need(lock_by_url.get(art.get("url")) == art.get("sha256"), f"artefacto Modular coincide con el lock: {art.get('subdir')}/{art.get('package')}")
    modular_in_lock = {u for u in lock_by_url if u.startswith(MODULAR_CHANNEL)}
    need(modular_in_lock == {a.get("url") for a in m_arts}, "todos los paquetes de Modular del lock estan registrados")

    # --- Dockerfile: instalacion, usuario y aislamiento
    need(re.search(r"^FROM debian:13-slim\b", dockerfile, re.M) is not None, "base debian:13-slim")
    need(all(line.split()[1].startswith("debian:13-slim") for line in dockerfile.splitlines() if line.startswith("FROM ")), "todas las etapas usan debian:13-slim")
    need("sha256sum -c" in dockerfile, "Dockerfile verifica el SHA-256 de pixi (sha256sum -c)")
    need(re.search(r"\bpixi install --locked\b", dockerfile) is not None, "Mojo se instala con 'pixi install --locked'")
    need("COPY toolchains/mojo/env/pixi.toml toolchains/mojo/env/pixi.lock /opt/mojo/env/" in dockerfile, "Dockerfile copia pixi.toml + pixi.lock comprometidos")
    need(f"MOJO_ENV={MOJO_ENV}" in dockerfile and f"PATH={MOJO_ENV}/bin" in dockerfile, "ENV MOJO_ENV y PATH apuntan al entorno Mojo")
    need("firstActivation" in dockerfile, "evento de telemetria de primera activacion suprimido")
    need(re.search(r"^USER mojo\s*$", dockerfile, re.M) is not None, "imagen corre como usuario no-root 'mojo'")
    need("chmod -R a=rX /opt/gordus-mojo" in dockerfile, "codigo de solo lectura en /opt/gordus-mojo")
    need("chmod -R go-w /opt/mojo" in dockerfile, "SDK sin escritura para grupo/otros")
    instructions = "\n".join(l for l in dockerfile.splitlines() if not l.lstrip().startswith("#"))
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, instructions) is None, f"aislamiento: {reason}")

    verified = []
    for tb in tarballs:
        if not tb.is_file():
            raise Gate(EXIT_BAD_INPUT, f"no existe el tarball {tb}")
        if tb.name not in pixi_by_file:
            raise Gate(EXIT_BLOCKED, f"tarball no aprobado: {tb.name}")
        got = sha256_file(tb)
        if got != pixi_by_file[tb.name]:
            raise Gate(EXIT_FAILED, f"SHA-256 no coincide para {tb.name}: {got}")
        verified.append({"file": tb.name, "sha256": got})
        checks.append(f"tarball local verificado: {tb.name}")

    return {"checks": checks, "mojo_version": mv, "pixi_version": pv,
            "lock_packages": len(packages), "tarballs_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[], help="tarball de pixi local cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/mojo/scripts/validate_mojo_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (Mojo {report['mojo_version']}, pixi {report['pixi_version']}, {report['lock_packages']} paquetes en el lock)")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
