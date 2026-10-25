#!/usr/bin/env python3
"""Validador fail-closed del toolchain .NET 10 SDK (C#) de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/dotnet/components.json y toolchains/dotnet/Dockerfile
fijan exactamente el mismo SDK oficial de .NET (archivo, URL y SHA-512 por arquitectura),
las dependencias nativas con version exacta de Debian, la configuracion fail-closed
(telemetria apagada, NuGet sin fuentes remotas, lock files en modo bloqueado), los nombres
exactos de archivo (con lista blanca de mayusculas) y el aislamiento.

Codigos de salida (convencion del repo):
  0  PASS        todo coincide
  2  BAD_INPUT   falta un archivo, JSON/XML invalido o argumentos invalidos
  3  BLOCKED     una regla de politica o un pin no coincide (falla cerrado)
  4  FAILED      error inesperado o un tarball local no coincide con su SHA-512
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_BAD_INPUT, EXIT_BLOCKED, EXIT_FAILED = 0, 2, 3, 4

SHA512_RE = re.compile(r"^[0-9a-f]{128}$")
DOTNET_RID = {"amd64": "x64", "arm64": "arm64"}
ARCH_SUFFIX = {"amd64": "AMD64", "arm64": "ARM64"}
URL_BASE = "https://builds.dotnet.microsoft.com/dotnet/Sdk"
RELEASES_JSON = "https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json"
INSTALL_PATH = "/usr/share/dotnet"
STATE_ROOT = "/var/lib/gordus-dotnet/"
REQUIRED_ENV = {
    "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
    "DOTNET_NOLOGO": "1",
    "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
    "DOTNET_GENERATE_ASPNET_CERTIFICATE": "false",
    "DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE": "1",
    "DOTNET_ADD_GLOBAL_TOOLS_TO_PATH": "0",
    "DOTNET_CLI_HOME": "/var/lib/gordus-dotnet/cli-home",
    "NUGET_PACKAGES": "/var/lib/gordus-dotnet/nuget/packages",
    "NUGET_HTTP_CACHE_PATH": "/var/lib/gordus-dotnet/nuget/http-cache",
}
REQUIRED_NATIVE = ("ca-certificates", "libicu76", "libssl3t64", "tzdata")
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json",
    "examples/hola/Directory.Build.props", "examples/hola/nuget.config",
    "examples/hola/Hola/Hola.csproj", "examples/hola/Hola/Program.cs",
    "examples/hola/Hola/packages.lock.json",
    "examples/hola/Hola.Tests/Hola.Tests.csproj", "examples/hola/Hola.Tests/Program.cs",
    "examples/hola/Hola.Tests/packages.lock.json",
    "tests/test_dotnet_toolchain.sh", "scripts/validate_dotnet_toolchain.py",
    "kestra/dotnet_toolchain_smoke.yaml",
}
# Lista blanca de mayusculas (Linux distingue mayusculas): solo estos nombres pueden
# llevar mayusculas; todo lo demas debe ir en minusculas.
CASE_ALLOWED_NAMES = {"Dockerfile", "README.md", "Program.cs", "Directory.Build.props", "Hola", "Hola.Tests"}
CASE_ALLOWED_RE = re.compile(r"^[A-Z][A-Za-z.]*\.csproj$")
WORKFLOW = ".github/workflows/dotnet-toolchain.yml"
OTHER_TOOLCHAINS = r"toolchains/(java|mojo|go|cpp|rust|node|swift)\b"
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen .NET no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen .NET no debe copiar scripts/ai/",
    OTHER_TOOLCHAINS: "la imagen .NET no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen .NET no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen .NET no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r"dotnet-install\.sh|dot\.net/v1": "sin dotnet-install.sh (version mutable)",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(dotnet[\w.-]*|python3?)\b": "sin .NET de apt ni Python de sistema",
    r"packages\.microsoft\.com": "sin repositorio apt de Microsoft",
    r"nuget\.org|api\.nuget": "sin fuentes NuGet remotas",
    r"DOTNET_CLI_TELEMETRY_OPTOUT=0|--allow-unauthenticated|--insecure|-k\s": "no se reactiva telemetria ni se desactiva TLS",
    r"dotnet tool install|dotnet workload install": "sin herramientas globales ni workloads",
}


class Gate(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def sha512_file(path: Path) -> str:
    h = hashlib.sha512()
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


def split_stages(text: str) -> list[str]:
    return [p for p in re.split(r"^(?=FROM\s)", text, flags=re.M) if p.startswith("FROM ")]


def strip_comments(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


def parse_env(stage: str) -> dict[str, str]:
    env: dict[str, str] = {}
    joined = re.sub(r"\\\n", " ", stage)
    for line in joined.splitlines():
        if line.startswith("ENV "):
            for key, value in re.findall(r"([A-Z_][A-Z0-9_]*)=(\S+)", line[4:]):
                env[key] = value
    return env


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"JSON invalido en {path.name}: {exc}") from exc


def load_xml(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"XML invalido en {path.name}: {exc}") from exc


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "dotnet"
    manifest_path, dockerfile_path = base / "components.json", base / "Dockerfile"
    for p in (manifest_path, dockerfile_path):
        if not p.is_file():
            raise Gate(EXIT_BAD_INPUT, f"falta el archivo {p}")
    manifest = load_json(manifest_path)
    dockerfile = dockerfile_path.read_text(encoding="utf-8")

    def need(cond: bool, reason: str) -> None:
        if not cond:
            raise Gate(EXIT_BLOCKED, reason)
        checks.append(reason)

    # --- nombres exactos y sin archivos sueltos (bin/obj no se suben)
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    present = {p for p in present if "__pycache__" not in p}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/dotnet" + (f"; sobran: {sorted(extra)[:10]}" if extra else ""))
    for rel in sorted(present):
        ok = all(part == part.lower() or part in CASE_ALLOWED_NAMES or CASE_ALLOWED_RE.fullmatch(part)
                 for part in rel.split("/"))
        need(ok, f"mayusculas permitidas (Program.cs, *.csproj, Dockerfile, README.md): {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "dotnet", "toolchain == dotnet")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("checksum_algorithm", "sha512"),
                      ("mutable_versions_allowed", False), ("lock_files_required", True),
                      ("restore_locked_mode", True), ("external_packages_allowed", False),
                      ("package_downloads_by_default", False), ("system_python_allowed", False),
                      ("network_tools_allowed", False), ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    iso = policy.get("isolated_from") or []
    for d in ("ai/", "scripts/ai/", "toolchains/node/", "toolchains/swift/", ".devcontainer/", "kestra/flows/"):
        need(d in iso, f"policy.isolated_from incluye {d}")
    need(manifest.get("dockerfile") == "toolchains/dotnet/Dockerfile", "dockerfile apunta a toolchains/dotnet/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == ["dotnet-sdk"], "componente exacto: dotnet-sdk")
    sdk = comps[0]
    need((sdk.get("license") or {}).get("value") == "MIT", "licencia dotnet-sdk: MIT")
    version = str(sdk.get("version", ""))
    runtime = str(sdk.get("runtime_version", ""))
    need(re.fullmatch(r"10\.0\.\d{3}", version) is not None, f"version exacta del SDK .NET 10: {version}")
    need(re.fullmatch(r"10\.0\.\d+", runtime) is not None, f"version exacta del runtime .NET 10: {runtime}")
    need(sdk.get("release_type") == "lts" and sdk.get("channel") == "10.0", ".NET 10 es LTS (canal 10.0)")
    need(sdk.get("checksum_source") == RELEASES_JSON, "checksum_source es releases.json oficial")
    need(sdk.get("install_path") == INSTALL_PATH, f"install_path == {INSTALL_PATH}")
    menv = sdk.get("environment") or {}
    for key, want in REQUIRED_ENV.items():
        need(menv.get(key) == want, f"components.json environment.{key} == {want}")
    native = manifest.get("native_dependencies") or {}
    need(set(native) == set(REQUIRED_NATIVE), "dependencias nativas exactas: " + ", ".join(REQUIRED_NATIVE))
    smoke = manifest.get("smoke_test", "")
    need(bool(smoke) and (repo_root / smoke).is_file(), f"smoke_test existe: {smoke}")

    # --- pines del Dockerfile
    args = parse_dockerfile_args(dockerfile)
    need(args.get("DOTNET_SDK_VERSION") == version, "Dockerfile DOTNET_SDK_VERSION == components.json version")
    need(args.get("DOTNET_RUNTIME_VERSION") == runtime, "Dockerfile DOTNET_RUNTIME_VERSION == components.json")
    need(args.get("DOTNET_URL_BASE") == URL_BASE, f"Dockerfile DOTNET_URL_BASE es {URL_BASE}")
    artifacts = sdk.get("artifacts") or []
    need({a.get("arch") for a in artifacts} == set(DOTNET_RID) and len(artifacts) == 2, "artefactos amd64 + arm64")
    by_file: dict[str, str] = {}
    for art in artifacts:
        arch, sha = art["arch"], str(art.get("sha512", ""))
        want_file = f"dotnet-sdk-{version}-linux-{DOTNET_RID[arch]}.tar.gz"
        need(art.get("file") == want_file, f"{arch}: archivo oficial {want_file}")
        need(art.get("url") == f"{URL_BASE}/{version}/{want_file}", f"{arch}: URL coincide")
        need(SHA512_RE.fullmatch(sha) is not None, f"{arch}: sha512 con formato valido")
        need(args.get(f"DOTNET_SHA512_{ARCH_SUFFIX[arch]}") == sha, f"{arch}: Dockerfile DOTNET_SHA512_{ARCH_SUFFIX[arch]} coincide")
        by_file[want_file] = sha

    # --- etapas
    stages = split_stages(dockerfile)
    need(len(stages) == 2 and all(s.split()[1] == "debian:13-slim" for s in stages), "dos etapas, ambas debian:13-slim")
    fetch, final = stages
    need(fetch.split()[2:4] == ["AS", "dotnet-fetch"], "etapa dotnet-fetch")
    fetch_i, final_i = strip_comments(fetch), strip_comments(final)
    need("sha512sum -c" in fetch_i, "verifica el SHA-512 del tarball (sha512sum -c)")
    need("--proto '=https'" in fetch_i, "descarga solo por https")
    need("chmod -R go-w /usr/share/dotnet" in fetch_i, "/usr/share/dotnet sin escritura para grupo/otros")
    need('test -d "/usr/share/dotnet/sdk/$DOTNET_SDK_VERSION"' in fetch_i, "comprueba la carpeta del SDK fijado")
    final_flat = re.sub(r"\\\n", " ", final_i)
    final_apt = " ".join(re.findall(r"apt-get install([^;&|]*)", final_flat))
    need(bool(final_apt) and re.search(r"\b(curl|wget|gpgv?|python3?)\b", final_apt) is None,
         "la imagen final no instala curl/wget/gpg/python")
    for pkg in REQUIRED_NATIVE:
        need(f"{pkg}={native.get(pkg)}" in final_apt, f"dependencia nativa fijada: {pkg}={native.get(pkg)}")
    tokens = [t for t in final_apt.split() if not t.startswith("-")]
    need(all("=" in t for t in tokens), "todo paquete apt de la imagen final lleva version exacta (pkg=version)")
    need("command -v python3" in final_i and "command -v curl" in final_i, "build falla si aparece Python o curl")
    copies = re.findall(r"^COPY --from=(\S+) (.+)$", final_i, re.M)
    need(copies == [("dotnet-fetch", "/usr/share/dotnet /usr/share/dotnet")], "la imagen final copia solo /usr/share/dotnet")
    fenv = parse_env(final)
    for key, want in REQUIRED_ENV.items():
        need(fenv.get(key) == want, f"ENV {key}={want} en la imagen final")
    need(fenv.get("DOTNET_ROOT") == INSTALL_PATH, "DOTNET_ROOT == /usr/share/dotnet")
    for key in ("DOTNET_CLI_HOME", "NUGET_PACKAGES", "NUGET_HTTP_CACHE_PATH"):
        need(fenv[key].startswith(STATE_ROOT), f"{key} bajo {STATE_ROOT}")
    need("<clear />" in final_i and "NuGet.Config" in final_i, "NuGet.Config del usuario sin fuentes remotas (<clear />)")
    need(re.search(r"^USER dotnetuser\s*$", final, re.M) is not None, "imagen corre como usuario no-root 'dotnetuser'")
    need("chmod -R a=rX /opt/gordus-dotnet" in final, "codigo de solo lectura en /opt/gordus-dotnet")
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, strip_comments(dockerfile)) is None, f"aislamiento: {reason}")

    # --- proyecto de ejemplo: sin paquetes externos, lock files en modo bloqueado
    hola = base / "examples/hola"
    props = load_xml(hola / "Directory.Build.props")
    pg = {el.tag: (el.text or "").strip() for grp in props.iter("PropertyGroup") for el in grp}
    for key, want in (("TargetFramework", "net10.0"), ("RestorePackagesWithLockFile", "true"),
                      ("RestoreLockedMode", "true"), ("TreatWarningsAsErrors", "true"), ("Nullable", "enable")):
        need(pg.get(key) == want, f"Directory.Build.props {key} == {want}")
    ncfg = load_xml(hola / "nuget.config")
    sources = ncfg.find("packageSources")
    need(sources is not None and [c.tag for c in sources] == ["clear"], "nuget.config: solo <clear />, ninguna fuente")
    for proj in ("Hola/Hola.csproj", "Hola.Tests/Hola.Tests.csproj"):
        root = load_xml(hola / proj)
        need(root.get("Sdk") == "Microsoft.NET.Sdk", f"{proj}: Sdk=Microsoft.NET.Sdk")
        need(not list(root.iter("PackageReference")), f"{proj}: sin PackageReference (sin paquetes externos)")
        need(not list(root.iter("RestoreSources")) and not list(root.iter("RestoreLockedMode")),
             f"{proj}: no redefine fuentes ni modo bloqueado")
    refs = [el.get("Include") for el in load_xml(hola / "Hola.Tests/Hola.Tests.csproj").iter("ProjectReference")]
    need(refs == ["../Hola/Hola.csproj"], "Hola.Tests referencia solo ../Hola/Hola.csproj")
    for proj, want in (("Hola", {}), ("Hola.Tests", {"hola": {"type": "Project"}})):
        lock = load_json(hola / proj / "packages.lock.json")
        need(lock.get("version") == 1, f"{proj}/packages.lock.json version 1")
        need(lock.get("dependencies") == {"net10.0": want}, f"{proj}/packages.lock.json sin paquetes externos")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/dotnet/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(OTHER_TOOLCHAINS + r"|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
    need("contents: read" in wf, "workflow con permisos de solo lectura")
    need(RELEASES_JSON in wf, "workflow compara los SHA-512 con releases.json oficial")

    verified = []
    for tb in tarballs:
        if not tb.is_file():
            raise Gate(EXIT_BAD_INPUT, f"no existe el tarball {tb}")
        if tb.name not in by_file:
            raise Gate(EXIT_BLOCKED, f"tarball no aprobado: {tb.name}")
        got = sha512_file(tb)
        if got != by_file[tb.name]:
            raise Gate(EXIT_FAILED, f"SHA-512 no coincide para {tb.name}: {got}")
        verified.append({"file": tb.name, "sha512": got})
        checks.append(f"tarball local verificado: {tb.name}")

    return {"checks": checks, "sdk_version": version, "runtime_version": runtime, "tarballs_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[], help="tarball local del SDK cuyo SHA-512 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/dotnet/scripts/validate_dotnet_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (.NET SDK {report['sdk_version']}, runtime {report['runtime_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
