#!/usr/bin/env python3
"""Validador fail-closed del toolchain Swift de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/swift/components.json y toolchains/swift/Dockerfile
fijan exactamente la misma version oficial de Swift (tarball de swift.org para Debian 13,
URLs y SHA-256 por arquitectura, huella GPG de la clave de firma), las dependencias de
Debian fijadas, el ejemplo SwiftPM sin dependencias, los nombres exactos de archivos y las
reglas de aislamiento.

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
ARCH_SUFFIX = {"amd64": "", "arm64": "-aarch64"}
ARCH_ARG = {"amd64": "SWIFT_SHA256_AMD64", "arm64": "SWIFT_SHA256_ARM64"}
SWIFT_URL_BASE = "https://download.swift.org"
SWIFT_KEY_URL = "https://www.swift.org/keys/release-key-swift-6.x.asc"
SWIFT_FINGERPRINT = "52BB7E3DE28A71BE22EC05FFEF80A866B47A981F"
PLATFORM = "debian13"
INSTALL_PATH = "/opt/swift"
BIN_PATH = "/opt/swift/usr/bin"
STATE_ROOT = "/var/lib/gordus-swift/"
REQUIRED_ENV = {
    "XDG_CACHE_HOME": "/var/lib/gordus-swift/cache",
    "CLANG_MODULE_CACHE_PATH": "/var/lib/gordus-swift/module-cache",
    "GORDUS_SWIFT_OFFLINE": "true",
}
# paquete Debian -> ARG del Dockerfile que fija su version
DEB_PACKAGES = {
    "binutils": "BINUTILS_VERSION", "binutils-gold": "BINUTILS_GOLD_VERSION",
    "libc6-dev": "LIBC_DEV_VERSION", "libgcc-14-dev": "GCC_LIBS_VERSION",
    "libstdc++-14-dev": "GCC_LIBS_VERSION", "libcurl4t64": "LIBCURL_VERSION",
    "libxml2": "LIBXML2_VERSION", "libsqlite3-0": "LIBSQLITE_VERSION",
    "libedit2": "LIBEDIT_VERSION", "libncurses6": "LIBNCURSES_VERSION",
    "uuid-dev": "UUID_DEV_VERSION", "tzdata": "TZDATA_VERSION",
}
# Nombres exactos. Todo en minusculas salvo Dockerfile, README.md y lo que SwiftPM exige:
# Package.swift, Sources/, Tests/ y las carpetas con el nombre de cada target.
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json",
    "examples/hola/Package.swift",
    "examples/hola/Sources/HolaCore/HolaCore.swift",
    "examples/hola/Sources/Hola/main.swift",
    "examples/hola/Tests/HolaCoreTests/HolaCoreTests.swift",
    "tests/test_swift_toolchain.sh", "scripts/validate_swift_toolchain.py",
    "kestra/swift_toolchain_smoke.yaml",
}
CASE_EXEMPT = {
    "Dockerfile", "README.md",
    "examples/hola/Package.swift",
    "examples/hola/Sources/HolaCore/HolaCore.swift",
    "examples/hola/Sources/Hola/main.swift",
    "examples/hola/Tests/HolaCoreTests/HolaCoreTests.swift",
}
WORKFLOW = ".github/workflows/swift-toolchain.yml"
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen Swift no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen Swift no debe copiar scripts/ai/",
    r"toolchains/(java|mojo|go|cpp|rust|node|dotnet)\b": "la imagen Swift no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen Swift no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen Swift no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r"swiftly": "sin swiftly (sin auto-actualizaciones)",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(swift|swiftlang|python3?|libpython3[\w.-]*|git|lldb)\b": "sin Swift de apt, Python, git ni lldb",
    r"--allow-unauthenticated|trusted=yes|--skip-verify": "no se desactiva la verificacion de firmas",
    r"swift-DEVELOPMENT|development-snapshot|-snapshot": "sin snapshots de desarrollo",
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


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "swift"
    manifest_path, dockerfile_path = base / "components.json", base / "Dockerfile"
    for p in (manifest_path, dockerfile_path):
        if not p.is_file():
            raise Gate(EXIT_BAD_INPUT, f"falta el archivo {p}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"components.json invalido: {exc}") from exc
    if not isinstance(manifest, dict):
        raise Gate(EXIT_BAD_INPUT, "components.json debe ser un objeto JSON")
    dockerfile = dockerfile_path.read_text(encoding="utf-8")

    def need(cond: bool, reason: str) -> None:
        if not cond:
            raise Gate(EXIT_BLOCKED, reason)
        checks.append(reason)

    # --- nombres exactos y sin archivos sueltos
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    present = {p for p in present if "__pycache__" not in p}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/swift" + (f"; sobran: {sorted(extra)}" if extra else ""))
    for rel in sorted(present - CASE_EXEMPT):
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "swift", "toolchain == swift")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("signature_required", True),
                      ("mutable_versions_allowed", False), ("swiftly_allowed", False),
                      ("toolchain_auto_download_allowed", False), ("package_downloads_by_default", False),
                      ("system_python_allowed", False), ("network_tools_allowed", False),
                      ("lldb_included", False), ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    need(manifest.get("dockerfile") == "toolchains/swift/Dockerfile", "dockerfile apunta a toolchains/swift/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == ["swift", "system-deps"], "componentes exactos: swift + system-deps")
    swift, deps = comps
    version = str(swift.get("version", ""))
    need(re.fullmatch(r"\d+\.\d+(\.\d+)?", version) is not None, f"version exacta de Swift: {version}")
    tag = f"swift-{version}-RELEASE"
    need(swift.get("tag") == tag, f"tag == {tag} (release estable, no snapshot)")
    need(swift.get("platform") == PLATFORM, "plataforma oficial debian13")
    need(swift.get("install_path") == INSTALL_PATH and swift.get("bin_path") == BIN_PATH, f"instalado en {INSTALL_PATH} (bin {BIN_PATH})")
    need((swift.get("license") or {}).get("value") == "Apache-2.0 WITH Swift-exception", "licencia Apache-2.0 con Runtime Library Exception")
    sig = swift.get("signature") or {}
    need(sig.get("fingerprint") == SWIFT_FINGERPRINT and sig.get("key_url") == SWIFT_KEY_URL, "clave GPG oficial de Swift 6.x fijada por huella")
    need({"swiftc", "swift-build", "swift-run", "swift-test"} <= set(swift.get("provided_tools") or []), "herramientas swiftc + swift build/run/test declaradas")
    need("lldb" in (swift.get("removed_tools") or []), "lldb declarado como removido")
    menv = swift.get("environment") or {}
    for key, want in REQUIRED_ENV.items():
        need(menv.get(key) == want, f"components.json environment.{key} == {want}")
    smoke = manifest.get("smoke_test", "")
    need(bool(smoke) and (repo_root / smoke).is_file(), f"smoke_test existe: {smoke}")

    # --- pines del Dockerfile
    args = parse_dockerfile_args(dockerfile)
    need(args.get("SWIFT_VERSION") == version, "Dockerfile SWIFT_VERSION == components.json version")
    need(args.get("SWIFT_TAG") == tag, "Dockerfile SWIFT_TAG coincide")
    need(args.get("SWIFT_BRANCH") == tag.lower(), "Dockerfile SWIFT_BRANCH coincide")
    need(args.get("SWIFT_PLATFORM") == PLATFORM, "Dockerfile SWIFT_PLATFORM == debian13")
    need(args.get("SWIFT_URL_BASE") == SWIFT_URL_BASE, "Dockerfile SWIFT_URL_BASE es https://download.swift.org")
    need(args.get("SWIFT_GPG_KEY_URL") == SWIFT_KEY_URL, "Dockerfile SWIFT_GPG_KEY_URL oficial")
    need(args.get("SWIFT_GPG_FINGERPRINT") == SWIFT_FINGERPRINT, "Dockerfile SWIFT_GPG_FINGERPRINT == huella oficial")
    artifacts = swift.get("artifacts") or []
    need(len(artifacts) == len(ARCH_SUFFIX), "2 artefactos (amd64 + arm64)")
    by_file: dict[str, str] = {}
    seen = set()
    for art in artifacts:
        arch, sha = art.get("arch"), str(art.get("sha256", ""))
        need(arch in ARCH_SUFFIX and arch not in seen, f"arquitectura aprobada y unica: {arch}")
        seen.add(arch)
        suf = ARCH_SUFFIX[arch]
        fname = f"{tag}-{PLATFORM}{suf}.tar.gz"
        url = f"{SWIFT_URL_BASE}/{tag.lower()}/{PLATFORM}{suf}/{tag}/{fname}"
        need(art.get("file") == fname, f"nombre de tarball {arch}: {fname}")
        need(art.get("url") == url, f"URL oficial {arch}")
        need(art.get("signature_url") == url + ".sig", f"URL de firma {arch}")
        need(SHA256_RE.fullmatch(sha) is not None, f"sha256 valido {arch}")
        need(args.get(ARCH_ARG[arch]) == sha, f"Dockerfile {ARCH_ARG[arch]} == components.json")
        by_file[fname] = sha

    pkgs = deps.get("packages") or []
    need([p.get("package") for p in pkgs] == list(DEB_PACKAGES), "lista exacta de paquetes Debian")
    for p in pkgs:
        argname = DEB_PACKAGES[p["package"]]
        need(bool(p.get("version")) and args.get(argname) == p.get("version"), f"version de {p['package']} fijada == {argname}")
        need(bool(p.get("license")), f"licencia declarada: {p['package']}")

    stages = split_stages(dockerfile)
    need(len(stages) == 2 and all(s.split()[1] == "debian:13-slim" for s in stages), "dos etapas, ambas debian:13-slim")
    fetch, final = stages
    need(fetch.split()[2:4] == ["AS", "swift-fetch"], "primera etapa se llama swift-fetch")
    fetch_i, final_i = strip_comments(fetch), strip_comments(final)
    need("sha256sum -c" in fetch_i, "Dockerfile verifica el SHA-256 (sha256sum -c)")
    need("gpgv --keyring" in fetch_i and ".sig" in fetch_i, "Dockerfile verifica la firma GPG (gpgv)")
    need("$SWIFT_GPG_FINGERPRINT" in fetch_i and "--show-keys" in fetch_i, "Dockerfile comprueba la huella de la clave")
    need("--proto '=https'" in fetch_i, "descargas solo por HTTPS")
    need("chmod -R go-w /opt/swift" in fetch_i, "/opt/swift sin escritura para grupo/otros")
    need("rm -rf /opt/swift/usr/bin/lldb /opt/swift/usr/bin/lldb-* /opt/swift/usr/bin/repl_swift" in fetch_i
         and "/opt/swift/usr/lib/liblldb.so*" in fetch_i and "test ! -e /opt/swift/usr/bin/lldb" in fetch_i,
         "LLDB/REPL removidos y comprobado (no hay Python)")
    for pkg, argname in DEB_PACKAGES.items():
        need(f'"{pkg}=${argname}"' in final_i, f"imagen final instala {pkg} fijado")
    final_apt = " ".join(re.findall(r"apt-get install([^;&|]*)", re.sub(r"\\\n", " ", final_i)))
    need(bool(final_apt) and re.search(r"\b(curl|wget|gpgv?|python3?|git)\b", re.sub(r"libcurl4t64=\$\w+", "", final_apt)) is None,
         "la imagen final no instala curl/wget/gpg/python/git")
    need("command -v python3" in final_i and "command -v git" in final_i, "build falla si aparece Python o git")
    copies = re.findall(r"^COPY --from=(\S+) (.+)$", final_i, re.M)
    need(copies == [("swift-fetch", "/opt/swift /opt/swift")], "la imagen final copia solo /opt/swift de swift-fetch")
    fenv = parse_env(final)
    for key, want in REQUIRED_ENV.items():
        need(fenv.get(key) == want, f"ENV {key}={want} en la imagen final")
    need(fenv.get("PATH", "").startswith(f"{BIN_PATH}:"), f"PATH empieza con {BIN_PATH}")
    for key in ("XDG_CACHE_HOME", "CLANG_MODULE_CACHE_PATH"):
        need(fenv[key].startswith(STATE_ROOT), f"{key} bajo {STATE_ROOT}")
    need(re.search(r"^USER swiftuser\s*$", final, re.M) is not None, "imagen corre como usuario no-root 'swiftuser'")
    need("chmod -R a=rX /opt/gordus-swift" in final, "codigo de solo lectura en /opt/gordus-swift")
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, strip_comments(dockerfile)) is None, f"aislamiento: {reason}")

    # --- paquete de ejemplo
    hola = base / "examples/hola"
    pkg_swift = (hola / "Package.swift").read_text(encoding="utf-8")
    need(pkg_swift.startswith("// swift-tools-version:"), "Package.swift declara swift-tools-version")
    tv = re.match(r"// swift-tools-version:(\d+)\.(\d+)", pkg_swift)
    need(tv is not None and (int(tv.group(1)), int(tv.group(2))) <= tuple(int(x) for x in version.split(".")[:2]),
         "swift-tools-version compatible con la version instalada")
    need(re.search(r"\.package\s*\(", pkg_swift) is None and "url:" not in pkg_swift, "Package.swift sin dependencias externas")
    need('name: "hola"' in pkg_swift, "paquete 'hola'")
    for t in ('.target(name: "HolaCore")', '.executableTarget(name: "Hola"', '.testTarget(name: "HolaCoreTests"'):
        need(t in pkg_swift, f"target declarado: {t}")
    need(not (hola / "Package.resolved").exists(), "sin Package.resolved (no hay dependencias)")
    tests_src = (hola / "Tests/HolaCoreTests/HolaCoreTests.swift").read_text(encoding="utf-8")
    need("import XCTest" in tests_src and tests_src.count("func test") >= 3, "tests XCTest (>= 3)")
    for rel in EXPECTED_FILES:
        if rel.endswith(".swift"):
            need("unsafe" not in (base / rel).read_text(encoding="utf-8").lower(), f"sin codigo unsafe: {rel}")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/swift/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(r"toolchains/(java|mojo|go|cpp|rust|node|dotnet)\b|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
    need("contents: read" in wf, "workflow con permisos de solo lectura")

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

    return {"checks": checks, "swift_version": version, "tarballs_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[], help="tarball local de Swift cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/swift/scripts/validate_swift_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (Swift {report['swift_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
