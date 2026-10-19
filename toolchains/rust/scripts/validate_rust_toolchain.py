#!/usr/bin/env python3
"""Validador fail-closed del toolchain Rust de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/rust/components.json y toolchains/rust/Dockerfile
fijan exactamente la misma version oficial de Rust (archivos, URLs y SHA-256 por componente y
arquitectura, huella GPG), las variables fail-closed (CARGO_NET_OFFLINE=true, ...), que el
ejemplo fija la version con rust-toolchain.toml, los nombres exactos de archivos y las reglas
de aislamiento.

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
TRIPLES = {"amd64": "x86_64-unknown-linux-gnu", "arm64": "aarch64-unknown-linux-gnu"}
ARCH_SUFFIX = {"amd64": "AMD64", "arm64": "ARM64"}
COMPONENT_ARG = {"rustc": "RUSTC", "rust-std": "RUST_STD", "cargo": "CARGO", "rustfmt": "RUSTFMT", "clippy": "CLIPPY"}
RUST_URL_BASE = "https://static.rust-lang.org/dist"
RUST_KEY_URL = "https://static.rust-lang.org/rust-key.gpg.ascii"
RUST_FINGERPRINT = "108F66205EAEB0AAA8DD5E1C85AB96E6FA1BE5FE"
INSTALL_PATH = "/opt/rust"
STATE_ROOT = "/var/lib/gordus-rust/"
REQUIRED_ENV = {
    "CARGO_HOME": "/var/lib/gordus-rust/cargo",
    "CARGO_TARGET_DIR": "/var/lib/gordus-rust/target",
    "CARGO_NET_OFFLINE": "true",
    "CARGO_INCREMENTAL": "0",
}
LINKER_PACKAGES = {"gcc-14": "GCC_VERSION", "binutils": "BINUTILS_VERSION", "libc6-dev": "LIBC_DEV_VERSION"}
# Nombres exactos. Todo en minusculas salvo Dockerfile, README.md, Cargo.toml y Cargo.lock:
# Cargo SOLO reconoce "Cargo.toml" / "Cargo.lock" con C mayuscula.
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json",
    "examples/hola/Cargo.toml", "examples/hola/Cargo.lock", "examples/hola/rust-toolchain.toml",
    "examples/hola/src/main.rs",
    "tests/test_rust_toolchain.sh", "scripts/validate_rust_toolchain.py",
    "kestra/rust_toolchain_smoke.yaml",
}
CASE_EXEMPT = {"Dockerfile", "README.md", "examples/hola/Cargo.toml", "examples/hola/Cargo.lock"}
WORKFLOW = ".github/workflows/rust-toolchain.yml"
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen Rust no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen Rust no debe copiar scripts/ai/",
    r"toolchains/(java|mojo|go|cpp)\b": "la imagen Rust no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen Rust no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen Rust no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh' (sh.rustup.rs)",
    r"rustup|sh\.rustup\.rs": "sin rustup (sin auto-actualizaciones)",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(rustc|cargo|python3?)\b": "sin Rust de apt ni Python de sistema",
    r"CARGO_NET_OFFLINE=false|--allow-unauthenticated|trusted=yes": "no se desactiva offline ni la verificacion de firmas",
    r"channel-rust-(stable|beta|nightly)": "sin canales mutables (stable/beta/nightly)",
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


def load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"TOML invalido en {path.name}: {exc}") from exc


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "rust"
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
    present = {p for p in present if "__pycache__" not in p}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/rust" + (f"; sobran: {sorted(extra)}" if extra else ""))
    for rel in sorted(present - CASE_EXEMPT):
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "rust", "toolchain == rust")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("signature_required", True),
                      ("mutable_versions_allowed", False), ("rustup_allowed", False),
                      ("toolchain_auto_download_allowed", False), ("crate_downloads_by_default", False),
                      ("system_python_allowed", False), ("network_tools_allowed", False),
                      ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    need(manifest.get("dockerfile") == "toolchains/rust/Dockerfile", "dockerfile apunta a toolchains/rust/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == ["rust", "linker"], "componentes exactos: rust + linker")
    rust, linker = comps
    version = str(rust.get("version", ""))
    need(re.fullmatch(r"1\.\d+\.\d+", version) is not None, f"version exacta de Rust: {version}")
    need(rust.get("channel") == "stable", "canal stable")
    dist_date = str(rust.get("dist_date", ""))
    need(re.fullmatch(r"\d{4}-\d{2}-\d{2}", dist_date) is not None, f"fecha de distribucion fija: {dist_date}")
    need(str(rust.get("rustc_version", "")).startswith(f"{version} "), "rustc_version coincide con version")
    need(rust.get("install_path") == INSTALL_PATH, f"install_path == {INSTALL_PATH}")
    need((rust.get("license") or {}).get("value") == "MIT OR Apache-2.0", "licencia Rust: MIT OR Apache-2.0")
    need(set(rust.get("installed_components") or []) == set(COMPONENT_ARG), "componentes rustc, rust-std, cargo, rustfmt, clippy")
    sig = rust.get("signature") or {}
    need(sig.get("fingerprint") == RUST_FINGERPRINT and sig.get("key_url") == RUST_KEY_URL, "clave GPG oficial de Rust fijada por huella")
    menv = rust.get("environment") or {}
    for key, want in REQUIRED_ENV.items():
        need(menv.get(key) == want, f"components.json environment.{key} == {want}")
    smoke = manifest.get("smoke_test", "")
    need(bool(smoke) and (repo_root / smoke).is_file(), f"smoke_test existe: {smoke}")
    need((linker.get("license") or {}).get("value") == "GPL-3.0-or-later WITH GCC-exception-3.1", "licencia del linker gcc declarada")

    # --- pines del Dockerfile
    args = parse_dockerfile_args(dockerfile)
    need(args.get("RUST_VERSION") == version, "Dockerfile RUST_VERSION == components.json version")
    need(args.get("RUST_DIST_DATE") == dist_date, "Dockerfile RUST_DIST_DATE == components.json dist_date")
    need(args.get("RUST_URL_BASE") == RUST_URL_BASE, "Dockerfile RUST_URL_BASE es https://static.rust-lang.org/dist")
    need(args.get("RUST_GPG_KEY_URL") == RUST_KEY_URL, "Dockerfile RUST_GPG_KEY_URL oficial")
    need(args.get("RUST_GPG_FINGERPRINT") == RUST_FINGERPRINT, "Dockerfile RUST_GPG_FINGERPRINT == huella oficial")
    artifacts = rust.get("artifacts") or []
    need(len(artifacts) == len(COMPONENT_ARG) * len(TRIPLES), "10 artefactos (5 componentes x amd64/arm64)")
    by_file: dict[str, str] = {}
    seen = set()
    for art in artifacts:
        comp, arch, sha = art.get("component"), art.get("arch"), str(art.get("sha256", ""))
        need(comp in COMPONENT_ARG and arch in TRIPLES, f"artefacto conocido: {comp}/{arch}")
        seen.add((comp, arch))
        want_file = f"{comp}-{version}-{TRIPLES[arch]}.tar.xz"
        want_url = f"{RUST_URL_BASE}/{dist_date}/{want_file}"
        need(art.get("file") == want_file, f"{comp}/{arch}: archivo oficial {want_file}")
        need(art.get("url") == want_url, f"{comp}/{arch}: URL fija por fecha")
        need(art.get("signature_url") == want_url + ".asc", f"{comp}/{arch}: firma .asc declarada")
        need(SHA256_RE.fullmatch(sha) is not None, f"{comp}/{arch}: sha256 con formato valido")
        arg = f"{COMPONENT_ARG[comp]}_SHA256_{ARCH_SUFFIX[arch]}"
        need(args.get(arg) == sha, f"{comp}/{arch}: Dockerfile {arg} coincide")
        by_file[want_file] = sha
    need(len(seen) == 10, "sin artefactos duplicados")
    for pkg, arg in LINKER_PACKAGES.items():
        want = (linker.get("packages") or {}).get(pkg)
        need(bool(want) and args.get(arg) == want, f"linker: {pkg}={want} fijado en el Dockerfile")

    # --- etapas e imagen final
    stages = split_stages(dockerfile)
    need(len(stages) == 2 and all(s.split()[1] == "debian:13-slim" for s in stages), "dos etapas, ambas debian:13-slim")
    fetch, final = stages
    need(fetch.split()[2:4] == ["AS", "rust-fetch"], "primera etapa se llama rust-fetch")
    fetch_i, final_i = strip_comments(fetch), strip_comments(final)
    need("sha256sum -c" in fetch_i, "Dockerfile verifica el SHA-256 (sha256sum -c)")
    need("gpgv --keyring" in fetch_i and ".asc" in fetch_i, "Dockerfile verifica la firma GPG (gpgv)")
    need("$RUST_GPG_FINGERPRINT" in fetch_i and "--show-keys" in fetch_i, "Dockerfile comprueba la huella de la clave")
    need("$RUST_URL_BASE/$RUST_DIST_DATE/" in fetch_i, "descargas desde la carpeta fechada (no 'stable')")
    need("--prefix=/opt/rust" in fetch_i, "instalado en /opt/rust")
    need("chmod -R go-w /opt/rust" in fetch_i, "/opt/rust sin escritura para grupo/otros")
    for token in ('"gcc-14=$GCC_VERSION"', '"binutils=$BINUTILS_VERSION"', '"libc6-dev=$LIBC_DEV_VERSION"'):
        need(token in final_i, f"imagen final instala {token} fijado")
    final_apt = " ".join(re.findall(r"apt-get install([^;&|]*)", re.sub(r"\\\n", " ", final_i)))
    need(bool(final_apt) and re.search(r"\b(curl|wget|gpgv?|python3?)\b", final_apt) is None,
         "la imagen final no instala curl/wget/gpg/python")
    need("command -v python3" in final_i, "build falla si aparece Python")
    copies = re.findall(r"^COPY --from=(\S+) (.+)$", final_i, re.M)
    need(copies == [("rust-fetch", "/opt/rust /opt/rust")], "la imagen final copia solo /opt/rust de rust-fetch")
    fenv = parse_env(final)
    for key, want in REQUIRED_ENV.items():
        need(fenv.get(key) == want, f"ENV {key}={want} en la imagen final")
    need(fenv.get("PATH", "").startswith(f"{INSTALL_PATH}/bin:"), "PATH empieza con /opt/rust/bin")
    for key in ("CARGO_HOME", "CARGO_TARGET_DIR"):
        need(fenv[key].startswith(STATE_ROOT), f"{key} bajo {STATE_ROOT}")
    need(re.search(r"^USER rustuser\s*$", final, re.M) is not None, "imagen corre como usuario no-root 'rustuser'")
    need("chmod -R a=rX /opt/gordus-rust" in final, "codigo de solo lectura en /opt/gordus-rust")
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, strip_comments(dockerfile)) is None, f"aislamiento: {reason}")

    # --- proyecto de ejemplo
    hola = base / "examples/hola"
    tc = load_toml(hola / "rust-toolchain.toml").get("toolchain") or {}
    need(tc.get("channel") == version, f"rust-toolchain.toml fija channel = {version} (no stable/nightly)")
    need({"rustfmt", "clippy"} <= set(tc.get("components") or []), "rust-toolchain.toml declara rustfmt + clippy")
    cargo = load_toml(hola / "Cargo.toml")
    pkg = cargo.get("package") or {}
    need(pkg.get("name") == "hola" and pkg.get("publish") is False, "Cargo.toml: paquete 'hola', publish = false")
    need(pkg.get("edition") == "2024", "Cargo.toml: edition 2024")
    rv = str(pkg.get("rust-version", ""))
    need(bool(rv) and (version == rv or version.startswith(rv + ".")), f"Cargo.toml rust-version ({rv}) compatible con {version}")
    for section in ("dependencies", "dev-dependencies", "build-dependencies"):
        need(not cargo.get(section), f"Cargo.toml sin {section} externas")
    need("build" not in pkg and not (hola / "build.rs").exists(), "sin build.rs")
    lock = load_toml(hola / "Cargo.lock")
    pkgs = lock.get("package") or []
    need(lock.get("version") == 4 and len(pkgs) == 1 and pkgs[0].get("name") == "hola"
         and pkgs[0].get("version") == pkg.get("version") and "source" not in pkgs[0],
         "Cargo.lock v4 con un solo paquete local (sin crates externos)")
    main_rs = (hola / "src/main.rs").read_text(encoding="utf-8")
    need("#[test]" in main_rs and "#[cfg(test)]" in main_rs, "main.rs incluye pruebas unitarias")
    need("unsafe" not in main_rs, "main.rs sin unsafe")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/rust/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(r"toolchains/(java|mojo|go|cpp)\b|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
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

    return {"checks": checks, "rust_version": version, "tarballs_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[], help="tarball local de Rust cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/rust/scripts/validate_rust_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (Rust {report['rust_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
