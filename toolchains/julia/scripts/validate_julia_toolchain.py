#!/usr/bin/env python3
"""Validador fail-closed del toolchain Julia de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/julia/components.json y toolchains/julia/Dockerfile
fijan exactamente la misma version oficial de Julia (binarios de julialang.org para amd64 y arm64,
SHA-256 y huella GPG de la Julia Release Signing Key), que Julia tiene las actualizaciones de
seguridad de 1.13.2 (15/10/2026), la politica sin red de Pkg, el ejemplo con Project.toml y
Manifest.toml solo con la biblioteca estandar, los nombres exactos y el aislamiento.

Codigos de salida (convencion del repo):
  0  PASS        todo coincide
  2  BAD_INPUT   falta un archivo, JSON invalido o argumentos invalidos
  3  BLOCKED     una regla de politica, un pin o el piso de seguridad no se cumple (falla cerrado)
  4  FAILED      error inesperado o un archivo local no coincide con su SHA-256
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_BAD_INPUT, EXIT_BLOCKED, EXIT_FAILED = 0, 2, 3, 4

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FPR_RE = re.compile(r"^[0-9A-F]{40}$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# Piso de seguridad: 1.13.2 actualiza OpenSSL_jll, LibCURL_jll, LibGit2_jll, nghttp2_jll y Zlib_jll.
JULIA_SECURITY_FLOOR = (1, 13, 2)
BUNDLED_UPDATES = {"OpenSSL_jll": "3.5.8", "LibCURL_jll": "8.22.0", "LibGit2_jll": "1.9.7",
                   "nghttp2_jll": "1.70.0", "Zlib_jll": "1.3.2"}
JULIA_URL_BASE = "https://julialang-s3.julialang.org/bin/linux"
ARCH_DIRS = {"amd64": ("x64", "x86_64"), "arm64": ("aarch64", "aarch64")}
KEY_FILE = "toolchains/julia/keys/julia-release-signing-key.asc"
KEY_SOURCE = "https://julialang.org/assets/juliareleases.asc"
STATE_ROOT = "/var/lib/gordus-julia/"
REQUIRED_ENV = {
    "JULIA_DEPOT_PATH": "/var/lib/gordus-julia/depot:",
    "JULIA_PKG_OFFLINE": "true",
    "JULIA_PKG_SERVER": "",
    "JULIA_PKG_PRECOMPILE_AUTO": "0",
}
# UUID oficiales de las bibliotecas estandar que usa el ejemplo.
STDLIB_UUIDS = {
    "Printf": "de0858da-6303-5e67-8744-51eddeeeb8d7",
    "Unicode": "4ec0a83e-493e-50e2-b9ac-8f72acf5a8f5",
    "Test": "8dfed614-e22c-5e08-85e1-65c5234f0b40",
}
# Nombres exactos, todo en minusculas salvo los que exige una herramienta:
# Dockerfile y README.md (convencion del repo), Project.toml y Manifest.toml (Pkg exige esos
# nombres) y src/Saludo.jl (Julia exige que el archivo se llame igual que el paquete).
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json",
    "keys/julia-release-signing-key.asc",
    "examples/hola/Project.toml", "examples/hola/Manifest.toml", "examples/hola/hola.jl",
    "examples/hola/src/Saludo.jl", "examples/hola/test/runtests.jl",
    "tests/test_julia_toolchain.sh", "scripts/validate_julia_toolchain.py",
    "kestra/julia_toolchain_smoke.yaml",
}
CASE_EXEMPT = {"Dockerfile", "README.md", "examples/hola/Project.toml", "examples/hola/Manifest.toml",
               "examples/hola/src/Saludo.jl"}
WORKFLOW = ".github/workflows/julia-toolchain.yml"
OTHER_TOOLCHAINS = r"toolchains/(java|mojo|go|cpp|rust|node|dotnet|swift|kotlin|scala|php|ruby|r)\b"
MIN_ACTION_MAJOR = {"actions/checkout": 5, "actions/setup-python": 6, "actions/upload-artifact": 6}
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen Julia no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen Julia no debe copiar scripts/ai/",
    OTHER_TOOLCHAINS: "la imagen Julia no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen Julia no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen Julia no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(julia|python3?)\b": "sin Julia de apt ni Python de sistema",
    r"juliaup|install\.julialang\.org": "sin el instalador web juliaup (se usa el binario firmado)",
    r"JULIA_PKG_OFFLINE=false|--allow-unauthenticated|--insecure\b|\s-k\s": "no se desactiva el modo sin red ni TLS",
    r"/latest/|/stable/|julia-latest|nightly": "sin URLs mutables 'latest'/'stable'/'nightly'",
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


def parse_version(text: str) -> tuple[int, int, int]:
    m = VERSION_RE.fullmatch(str(text))
    if not m:
        raise Gate(EXIT_BLOCKED, f"version no exacta (se espera X.Y.Z): {text!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def julia_security_ok(version: str) -> tuple[bool, str]:
    v = parse_version(version)
    if v < JULIA_SECURITY_FLOOR:
        return False, f"Julia {version} es anterior a 1.13.2 (sin OpenSSL_jll 3.5.8 / LibCURL_jll 8.22.0 / LibGit2_jll 1.9.7)"
    return True, f"Julia {version} >= 1.13.2"


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
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"JSON invalido en {path.name}: {exc}") from exc


def openpgp_primary_fingerprint(armored: str) -> str:
    """Huella v4 de la clave primaria de un bloque ASCII-armor (RFC 4880), solo stdlib."""
    m = re.search(r"-----BEGIN PGP PUBLIC KEY BLOCK-----\r?\n(.*?)-----END PGP PUBLIC KEY BLOCK-----", armored, re.S)
    if not m:
        raise Gate(EXIT_BLOCKED, "la clave GPG no es un bloque ASCII-armor de clave publica")
    lines = [l.strip() for l in m.group(1).splitlines()]
    if "" in lines:
        lines = lines[lines.index("") + 1:]
    body = "".join(l for l in lines if l and not l.startswith("="))
    data = base64.b64decode(body, validate=True)
    tag_byte = data[0]
    if not tag_byte & 0x80:
        raise Gate(EXIT_BLOCKED, "paquete OpenPGP invalido")
    if tag_byte & 0x40:  # formato nuevo
        tag = tag_byte & 0x3F
        first = data[1]
        if first < 192:
            length, start = first, 2
        elif first < 224:
            length, start = ((first - 192) << 8) + data[2] + 192, 3
        else:
            length, start = int.from_bytes(data[2:6], "big"), 6
    else:  # formato viejo
        tag = (tag_byte >> 2) & 0x0F
        ltype = tag_byte & 0x03
        size = {0: 1, 1: 2, 2: 4}.get(ltype)
        if size is None:
            raise Gate(EXIT_BLOCKED, "longitud OpenPGP indeterminada")
        length, start = int.from_bytes(data[1:1 + size], "big"), 1 + size
    if tag != 6:
        raise Gate(EXIT_BLOCKED, "el primer paquete no es una clave publica primaria")
    packet = data[start:start + length]
    if not packet or packet[0] != 4:
        raise Gate(EXIT_BLOCKED, "solo se aceptan claves OpenPGP v4")
    return hashlib.sha1(b"\x99" + len(packet).to_bytes(2, "big") + packet).hexdigest().upper()


def load_toml(path: Path) -> dict:
    import tomllib
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"TOML invalido en {path.name}: {exc}") from exc


def validate(repo_root: Path, local_files: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "julia"
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

    # --- nombres exactos y sin archivos sueltos
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    present = {p for p in present if "__pycache__" not in p}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/julia" + (f"; sobran: {sorted(extra)[:10]}" if extra else ""))
    for rel in sorted(present - CASE_EXEMPT):
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "julia", "toolchain == julia")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("signature_required", True),
                      ("mutable_versions_allowed", False), ("lockfile_required", True),
                      ("package_downloads_by_default", False), ("third_party_packages", False),
                      ("system_python_allowed", False), ("network_tools_allowed", False),
                      ("persistent_installation_authorized", False), ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    isolated = set(policy.get("isolated_from") or [])
    need({"ai/", "scripts/ai/", ".devcontainer/", "kestra/flows/", "toolchains/php/", "toolchains/ruby/",
          "toolchains/java/", "toolchains/kotlin/", "toolchains/scala/"} <= isolated,
         "policy.isolated_from incluye ai/, .devcontainer/, kestra/flows/ y los otros toolchains")
    need(manifest.get("dockerfile") == "toolchains/julia/Dockerfile", "dockerfile apunta a toolchains/julia/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    need(manifest.get("architectures") == ["amd64", "arm64"], "arquitecturas amd64 + arm64")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == ["julia", "pkg", "test"],
         "componentes exactos: julia + pkg + test")
    julia, pkg, test = comps
    for comp in comps:
        lic = comp.get("license") or {}
        need(lic.get("value") == "MIT" and lic.get("status") == "DECLARED", f"licencia declarada de {comp['id']}: MIT")

    args = parse_dockerfile_args(dockerfile)

    # --- Julia: version, piso de seguridad, binarios, SHA-256, firma
    version = str(julia.get("version", ""))
    vt = parse_version(version)
    ok, why = julia_security_ok(version)
    if not ok:
        raise Gate(EXIT_BLOCKED, f"SEGURIDAD: {why}")
    checks.append(f"SEGURIDAD: {why}")
    minor = f"{vt[0]}.{vt[1]}"
    sec = manifest.get("security") or {}
    need(sec.get("julia_minimum_patched") == "1.13.2", "security.julia_minimum_patched == 1.13.2")
    need(sec.get("bundled_updates") == BUNDLED_UPDATES, "security.bundled_updates registra OpenSSL/LibCURL/LibGit2/nghttp2/Zlib")
    need(args.get("JULIA_VERSION") == version, f"Dockerfile JULIA_VERSION == {version}")
    need(args.get("JULIA_MINOR") == minor, f"Dockerfile JULIA_MINOR == {minor}")
    need(args.get("JULIA_URL_BASE") == JULIA_URL_BASE, "Dockerfile JULIA_URL_BASE oficial (julialang-s3)")
    arts = julia.get("artifacts") or {}
    need(set(arts) == set(ARCH_DIRS), "binarios declarados para amd64 y arm64")
    expected_local: dict[str, str] = {}
    for arch, (d, a) in ARCH_DIRS.items():
        fname = f"julia-{version}-linux-{a}.tar.gz"
        url = f"{JULIA_URL_BASE}/{d}/{minor}/{fname}"
        art = arts.get(arch) or {}
        need(art.get("source") == url, f"{arch}: source == {url}")
        need(SHA256_RE.fullmatch(str(art.get("sha256", ""))) is not None, f"{arch}: sha256 con formato valido")
        need(args.get(f"JULIA_SHA256_{arch.upper()}") == art.get("sha256"), f"Dockerfile JULIA_SHA256_{arch.upper()} == components.json")
        expected_local[fname] = art.get("sha256")
    need(len({a.get("sha256") for a in arts.values()}) == 2, "sha256 distinto por arquitectura")
    need('amd64) dir=x64; arch=x86_64; sha="$JULIA_SHA256_AMD64"' in dockerfile
         and 'arm64) dir=aarch64; arch=aarch64; sha="$JULIA_SHA256_ARM64"' in dockerfile,
         "el Dockerfile elige el binario segun TARGETARCH")
    need("exit 3 ;;" in dockerfile, "arquitectura desconocida bloqueada")
    sig = julia.get("signature") or {}
    need(sig.get("file") == "<source>.asc" and 'url.asc' in dockerfile, "firma .asc oficial de cada tarball")
    need(FPR_RE.fullmatch(str(sig.get("fingerprint", ""))) is not None, "huella GPG de Julia de 40 hex")
    need(args.get("JULIA_GPG_FINGERPRINT") == sig.get("fingerprint"), "Dockerfile JULIA_GPG_FINGERPRINT == components.json")
    need(sig.get("key_source") == KEY_SOURCE, "origen de la clave: julialang.org/assets/juliareleases.asc")
    need(sig.get("key_file") == KEY_FILE, f"clave guardada en {KEY_FILE}")
    key_text = (repo_root / KEY_FILE).read_text(encoding="utf-8")
    need(openpgp_primary_fingerprint(key_text) == sig.get("fingerprint"), "la clave de keys/ tiene exactamente la huella fijada")
    need(key_text.count("-----BEGIN PGP PUBLIC KEY BLOCK-----") == 1, "keys/ trae una sola clave")
    need(f"COPY {KEY_FILE} /tmp/keys/julia.asc" in dockerfile, "el Dockerfile copia la clave desde keys/")
    need("VALIDSIG" in dockerfile and "gpgv --status-fd 1" in dockerfile, "gpgv exige VALIDSIG de la huella fijada")
    need("sha256sum -c -" in dockerfile, "el Dockerfile verifica SHA-256")
    need(re.search(r"keys\.openpgp\.org|keyserver|juliareleases\.asc", strip_comments(dockerfile)) is None,
         "el Dockerfile no baja claves GPG (estan en keys/)")
    need(dockerfile.count('VERSION >= v"1.13.2"') >= 2, "la imagen bloquea Julia < 1.13.2 al construir")

    # --- Pkg y Test (biblioteca estandar)
    pv, tv = str(pkg.get("version", "")), str(test.get("version", ""))
    parse_version(pv)
    parse_version(tv)
    need(pkg.get("environment") == REQUIRED_ENV, "components.json: entorno de Pkg exacto")
    need(f"v{minor}/Pkg" in str(pkg.get("install_path")) and f"v{minor}/Test" in str(test.get("install_path")),
         "Pkg y Test vienen de la biblioteca estandar de Julia")

    # --- Dockerfile: etapas, imagen final
    clean = strip_comments(dockerfile)
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, clean, flags=re.M) is None, reason)
    froms = re.findall(r"^FROM\s+(\S+)", clean, flags=re.M)
    need(froms == ["debian:13-slim"] * 2, "2 etapas, todas FROM debian:13-slim")
    stages = split_stages(clean)
    final = stages[-1]
    need("command -v python3 || command -v python || command -v curl || command -v wget" in final,
         "la imagen final verifica que no haya Python ni curl/wget")
    pkgs = manifest.get("runtime_packages") or {}
    need(bool(pkgs), "runtime_packages declarados")
    installed = dict(re.findall(r"^\s+([a-z0-9][a-z0-9+.-]*)=(\S+)\s*\\?$", final, flags=re.M))
    need(installed == pkgs, "paquetes Debian de la imagen final fijados == runtime_packages")
    need(not ({"curl", "wget", "gpg", "gpgv", "gcc", "make", "python3", "python3-minimal"} & set(installed)),
         "la imagen final no instala curl, gpg, compiladores ni Python")
    need(re.search(r"^COPY --from=julia-fetch /opt/julia /opt/julia$", final, flags=re.M) is not None,
         "la imagen final solo copia /opt/julia verificado")
    env = {}
    joined = re.sub(r"\\\n", " ", final)
    for line in joined.splitlines():
        if line.startswith("ENV "):
            for key, value in re.findall(r"([A-Z_][A-Z0-9_]*)=(\S*)", line[4:]):
                env[key] = value
    for key, want in REQUIRED_ENV.items():
        need(env.get(key) == want, f"ENV {key}={want}")
    need(env.get("PATH", "").startswith("/opt/julia/bin:"), "PATH empieza por /opt/julia/bin")
    need(re.search(r"^USER\s+juliauser\s*$", final, flags=re.M) is not None, "usuario no root: juliauser")
    need(final.rstrip().splitlines()[-1].strip() == 'CMD ["bash"]', "CMD final bash")
    need("chmod -R a=rX /opt/gordus-julia" in final, "codigo de /opt/gordus-julia de solo lectura")
    need("chown -R root:root /opt/julia" in final and "chmod -R go-w /opt/julia" in final, "/opt/julia de root y sin escritura")
    for d in re.findall(r"install -d -o juliauser -g juliauser ([^\n&]+)", re.sub(r"\\\n\s*", " ", final)):
        for p in d.split():
            need(p == "/workspace" or p.startswith(STATE_ROOT.rstrip("/")), f"directorio escribible permitido: {p}")

    # --- ejemplo: Project.toml + Manifest.toml solo con biblioteca estandar
    hola = base / "examples" / "hola"
    proj = load_toml(hola / "Project.toml")
    man = load_toml(hola / "Manifest.toml")
    need(proj.get("name") == "Saludo" and UUID_RE.fullmatch(str(proj.get("uuid", ""))) is not None,
         "Project.toml: paquete Saludo con uuid")
    deps = proj.get("deps") or {}
    need(deps == {"Printf": STDLIB_UUIDS["Printf"]}, "Project.toml: solo depende de Printf (stdlib)")
    need((proj.get("extras") or {}) == {"Test": STDLIB_UUIDS["Test"]} and (proj.get("targets") or {}) == {"test": ["Test"]},
         "Project.toml: Test (stdlib) como dependencia de prueba")
    need((proj.get("compat") or {}).get("julia") == version, f"Project.toml exige julia {version}")
    need(man.get("julia_version") == version, f"Manifest.toml generado con julia {version}")
    need(re.fullmatch(r"[0-9a-f]{40}", str(man.get("project_hash", ""))) is not None, "Manifest.toml con project_hash")
    mdeps = man.get("deps") or {}
    for name, entries in mdeps.items():
        for e in entries:
            if name == "Saludo":
                need(e.get("path") == "." and e.get("uuid") == proj.get("uuid"), "Manifest.toml: Saludo es el propio proyecto")
                continue
            need(STDLIB_UUIDS.get(name) == e.get("uuid"), f"Manifest.toml: {name} es biblioteca estandar")
            need(not ({"git-tree-sha1", "repo-url", "path"} & set(e)), f"Manifest.toml: {name} sin descargas externas")
    need(set(mdeps) == {"Printf", "Unicode", "Saludo"}, "Manifest.toml: exactamente Printf, Unicode y Saludo")
    mod = (hola / "src/Saludo.jl").read_text(encoding="utf-8")
    need(re.search(r"^module Saludo$", mod, flags=re.M) is not None, "src/Saludo.jl define module Saludo")
    rt = (hola / "test/runtests.jl").read_text(encoding="utf-8")
    need("using Test" in rt and "@testset" in rt and rt.count("@test ") == 4, "test/runtests.jl usa Test con 4 pruebas")

    # --- prueba de humo
    smoke = (base / "tests/test_julia_toolchain.sh").read_text(encoding="utf-8")
    need(f"EXPECTED_JULIA_VERSION:-{version}" in smoke, "test_julia_toolchain.sh espera la misma version")
    need("min_julia=1.13.2" in smoke, "test_julia_toolchain.sh bloquea Julia < 1.13.2")
    need('JULIA_PKG_OFFLINE:-}" = true' in smoke, "test_julia_toolchain.sh exige Pkg sin red")

    # --- flujo Kestra
    flow = (base / "kestra/julia_toolchain_smoke.yaml").read_text(encoding="utf-8")
    need(re.search(r"^id: julia_toolchain_smoke$", flow, flags=re.M) is not None, "Kestra: id julia_toolchain_smoke")
    need(re.search(r"^namespace: gordus_hub\.toolchains$", flow, flags=re.M) is not None, "Kestra: namespace gordus_hub.toolchains")
    need(f"inputs.julia_version == 'julia {version}'" in flow and "inputs.security_patch == 'PASS'" in flow
         and f"pkg {pv}" in flow, "Kestra exige las versiones y el parche")
    need("io.kestra.plugin.core.execution.Fail" in flow, "Kestra falla cerrado")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/julia/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(OTHER_TOOLCHAINS + r"|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
    need("contents: read" in wf, "workflow con permisos de solo lectura")
    need("kestra/kestra:v1.3.40-slim" in wf and ":latest" not in wf, "workflow usa Kestra v1.3.40-slim fijado")
    uses = re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@v(\d+)", wf)
    need(bool(uses), "workflow usa acciones versionadas")
    for name, major in uses:
        need(name in MIN_ACTION_MAJOR and int(major) >= MIN_ACTION_MAJOR[name], f"accion {name}@v{major} nativa de Node 24")

    verified = []
    for lf in local_files:
        if not lf.is_file():
            raise Gate(EXIT_BAD_INPUT, f"no existe el archivo {lf}")
        if lf.name not in expected_local:
            raise Gate(EXIT_BLOCKED, f"archivo no aprobado: {lf.name}")
        got = sha256_file(lf)
        if got != expected_local[lf.name]:
            raise Gate(EXIT_FAILED, f"SHA-256 no coincide para {lf.name}: {got}")
        verified.append({"file": lf.name, "sha256": got})
        checks.append(f"archivo local verificado: {lf.name}")

    return {"checks": checks, "julia_version": version, "pkg_version": pv, "test_version": tv,
            "security_floor": "1.13.2", "files_verified": verified}

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[],
                    help="tarball local de Julia cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/julia/scripts/validate_julia_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (Julia {report['julia_version']} con parche de seguridad, "
              f"Pkg {report['pkg_version']}, Test {report['test_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
