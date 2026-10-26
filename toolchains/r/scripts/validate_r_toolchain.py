#!/usr/bin/env python3
"""Validador fail-closed del toolchain R de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/r/components.json, toolchains/r/Dockerfile y
toolchains/r/packages.lock fijan exactamente la misma version oficial de R (tarball de CRAN,
SHA-256 y SHA-512) y los mismos paquetes CRAN (testthat, renv y sus dependencias, cada uno con
SHA-256), el piso de seguridad (CVE-2024-27322), la politica sin red, los nombres exactos y el
aislamiento.

CRAN no publica firmas GPG del tarball de R ni de los paquetes fuente; por eso se exigen hashes.

Codigos de salida (convencion del repo):
  0  PASS        todo coincide
  2  BAD_INPUT   falta un archivo, JSON invalido o argumentos invalidos
  3  BLOCKED     una regla de politica o un pin no coincide (falla cerrado)
  4  FAILED      error inesperado o un tarball local no coincide con su hash
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
SHA512_RE = re.compile(r"^[0-9a-f]{128}$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
CRAN_VERSION_RE = re.compile(r"^\d+(?:[.-]\d+)+$")
R_URL_BASE = "https://cran.r-project.org/src/base/R-4"
CRAN_URL = "https://cran.r-project.org/src/contrib"
LOCAL_REPO = "file:///opt/gordus-r/repo"
STATE_ROOT = "/var/lib/gordus-r/"
# Piso de seguridad: CVE-2024-27322 (deserializacion RDS -> ejecucion de codigo) afecta R < 4.4.0.
# Ademas se exige como minimo la ultima version estable con parches revisada (4.6.1, 2026-10-25).
CVE_FLOOR = (4, 4, 0)
MIN_PATCHED = (4, 6, 1)
REQUIRED_ENV = {
    "R_LIBS_SITE": "/opt/r-site-library",
    "R_LIBS_USER": "/var/lib/gordus-r/library",
    "R_PROFILE": "/opt/gordus-r/rprofile.site",
    "RENV_PATHS_ROOT": "/var/lib/gordus-r/renv",
    "RENV_CONFIG_UPDATES_CHECK": "FALSE",
}
REQUIRED_LICENSES = {"r": "GPL-2.0-or-later", "install-packages": "GPL-2.0-or-later", "renv": "MIT", "testthat": "MIT"}
# testthat 3.3.2 + renv 1.3.1 y su cierre de dependencias (sin paquetes base de R).
REQUIRED_PACKAGES = {
    "brio", "otel", "ps", "R6", "processx", "callr", "cli", "desc", "evaluate", "jsonlite", "rlang",
    "lifecycle", "magrittr", "fs", "glue", "pkgbuild", "rprojroot", "pkgload", "praise", "crayon",
    "diffobj", "waldo", "withr", "testthat", "renv",
}
# Nombres exactos, todo en minusculas salvo Dockerfile y README.md (convencion del repo).
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json", "packages.lock", "rprofile.site",
    "examples/hola/hola.r", "examples/hola/saludo.r", "examples/hola/renv.lock",
    "examples/hola/tests/testthat/test_saludo.r",
    "tests/test_r_toolchain.sh", "scripts/validate_r_toolchain.py",
    "kestra/r_toolchain_smoke.yaml",
}
CASE_EXEMPT = {"Dockerfile", "README.md"}
WORKFLOW = ".github/workflows/r-toolchain.yml"
OTHER_TOOLCHAINS = r"toolchains/(java|mojo|go|cpp|rust|node|dotnet|swift|kotlin|scala|php|ruby)\b"
# Acciones de GitHub que corren nativamente en Node 24.
MIN_ACTION_MAJOR = {"actions/checkout": 5, "actions/setup-python": 6, "actions/upload-artifact": 6}
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen R no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen R no debe copiar scripts/ai/",
    OTHER_TOOLCHAINS: "la imagen R no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen R no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen R no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(r-base[a-z-]*|r-cran-[a-z0-9.-]+|r-recommended|python3?)\b": "sin R/paquetes R de apt ni Python de sistema",
    r"\b(rig|rim|asdf|conda|mamba)\b": "sin gestores de versiones (rig/asdf/conda)",
    r"repos\s*=\s*\"https?:|install_github|remotes::|devtools::|pak::": "sin instalar paquetes desde la red fuera del lock",
    r"--allow-unauthenticated|--insecure\b|\s-k\s": "no se desactiva TLS",
    r"R-devel|R-patched|R-latest|/snapshot|/latest": "sin versiones mutables o de prueba",
}


class Gate(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def file_hash(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_version(text: str) -> tuple[int, int, int]:
    m = VERSION_RE.fullmatch(str(text))
    if not m:
        raise Gate(EXIT_BLOCKED, f"version no exacta (se espera X.Y.Z): {text!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


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


def parse_packages_lock(text: str) -> list[tuple[str, str, str]]:
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise Gate(EXIT_BLOCKED, f"packages.lock linea {n}: se espera 'nombre version sha256'")
        rows.append((parts[0], parts[1], parts[2]))
    return rows


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "r"
    manifest_path, dockerfile_path, lock_path = base / "components.json", base / "Dockerfile", base / "packages.lock"
    for p in (manifest_path, dockerfile_path, lock_path):
        if not p.is_file():
            raise Gate(EXIT_BAD_INPUT, f"falta el archivo {p}")
    manifest = load_json(manifest_path)
    dockerfile = dockerfile_path.read_text(encoding="utf-8")

    def need(cond: bool, reason: str) -> None:
        if not cond:
            raise Gate(EXIT_BLOCKED, reason)
        checks.append(reason)

    # --- nombres exactos y sin archivos sueltos (renv/ y .Rhistory no se suben)
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    present = {p for p in present if "__pycache__" not in p}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/r" + (f"; sobran: {sorted(extra)[:10]}" if extra else ""))
    for rel in sorted(present - CASE_EXEMPT):
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "r", "toolchain == r")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("signature_required", False),
                      ("mutable_versions_allowed", False), ("lockfile_required", True),
                      ("lockfile_checksums_required", True), ("package_downloads_by_default", False),
                      ("system_python_allowed", False), ("network_tools_allowed", False),
                      ("persistent_installation_authorized", False), ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    need("GPG" in str(policy.get("signature_note", "")), "policy.signature_note explica por que no hay firma GPG")
    isolated = set(policy.get("isolated_from") or [])
    need({"ai/", "scripts/ai/", ".devcontainer/", "kestra/flows/", "toolchains/php/", "toolchains/ruby/",
          "toolchains/kotlin/", "toolchains/scala/", "toolchains/java/"} <= isolated,
         "policy.isolated_from incluye ai/, .devcontainer/, kestra/flows/ y los otros toolchains")
    need(manifest.get("dockerfile") == "toolchains/r/Dockerfile", "dockerfile apunta a toolchains/r/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    need(manifest.get("architectures") == ["amd64", "arm64"], "arquitecturas amd64 + arm64")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == ["r", "install-packages", "renv", "testthat"],
         "componentes exactos: r + install-packages + renv + testthat")
    r, instpk, renv, testthat = comps
    for comp in comps:
        lic = comp.get("license") or {}
        need(lic.get("value") == REQUIRED_LICENSES[comp["id"]] and lic.get("status") == "DECLARED",
             f"licencia declarada de {comp['id']}: {REQUIRED_LICENSES[comp['id']]}")
        parse_version(str(comp.get("version", "")))
        checks.append(f"version exacta de {comp['id']}: {comp.get('version')}")

    # --- seguridad: piso de version
    version = str(r.get("version"))
    vt = parse_version(version)
    need(vt >= CVE_FLOOR, f"R {version} debe ser >= 4.4.0 (CVE-2024-27322 corregido)")
    need(vt >= MIN_PATCHED, f"R {version} debe ser >= {'.'.join(map(str, MIN_PATCHED))} (ultima estable con parches)")
    sec = manifest.get("security") or {}
    need(sec.get("minimum_safe_version") == "4.4.0", "security.minimum_safe_version == 4.4.0")
    need(any(a.get("id") == "CVE-2024-27322" for a in sec.get("advisories") or []), "security: CVE-2024-27322 registrado")
    need(instpk.get("version") == version, "install.packages es el de R fijado")

    # --- R: Dockerfile == components.json
    args = parse_dockerfile_args(dockerfile)
    rfile = f"R-{version}.tar.gz"
    url = f"{R_URL_BASE}/{rfile}"
    need(args.get("R_VERSION") == version, f"Dockerfile R_VERSION == {version}")
    need(args.get("R_URL_BASE") == R_URL_BASE, "Dockerfile R_URL_BASE oficial (cran.r-project.org)")
    need(args.get("CRAN_URL") == CRAN_URL, "Dockerfile CRAN_URL oficial")
    need(r.get("source") == url, f"source == {url}")
    mirrors = r.get("checksum_mirrors") or []
    need(len(mirrors) >= 2 and all(m.endswith(f"/src/base/R-4/{rfile}") and m.startswith("https://") for m in mirrors),
         "hash de R comprobado en dos espejos oficiales")
    need(SHA256_RE.fullmatch(str(r.get("sha256", ""))) is not None, "R sha256 con formato valido")
    need(SHA512_RE.fullmatch(str(r.get("sha512", ""))) is not None, "R sha512 con formato valido")
    need(args.get("R_SHA256") == r.get("sha256"), "Dockerfile R_SHA256 == components.json")
    need(args.get("R_SHA512") == r.get("sha512"), "Dockerfile R_SHA512 == components.json")
    need("sha256sum -c -" in dockerfile and "sha512sum -c -" in dockerfile, "el Dockerfile verifica SHA-256 y SHA-512")
    need("cat(as.character(getRversion()))')\" = \"$R_VERSION\"" in dockerfile, "el Dockerfile comprueba la version compilada")
    need("--without-recommended-packages" in dockerfile and "--without-x" in dockerfile, "R minimo: sin X11 ni paquetes recomendados")
    need(instpk.get("environment") == {k: REQUIRED_ENV[k] for k in ("R_LIBS_SITE", "R_LIBS_USER", "R_PROFILE")},
         "entorno de install.packages exacto")
    need(instpk.get("local_repo") == LOCAL_REPO, "install.packages usa el repositorio local")
    need(renv.get("environment") == {k: REQUIRED_ENV[k] for k in ("RENV_PATHS_ROOT", "RENV_CONFIG_UPDATES_CHECK")},
         "entorno de renv exacto")

    # --- packages.lock == components.json (cran_packages), con SHA-256
    rows = parse_packages_lock(lock_path.read_text(encoding="utf-8"))
    names = [n for n, _, _ in rows]
    need(len(names) == len(set(names)), "packages.lock sin paquetes repetidos")
    need(set(names) == REQUIRED_PACKAGES, "packages.lock == testthat + renv y sus dependencias")
    cran = manifest.get("cran_packages") or {}
    need(cran == {n: {"version": v, "sha256": s} for n, v, s in rows}, "packages.lock == components.json cran_packages")
    for n, v, s in rows:
        need(CRAN_VERSION_RE.fullmatch(v) is not None and SHA256_RE.fullmatch(s) is not None,
             f"paquete {n} {v}: version exacta y sha256 valido")
    need(names.index("testthat") > max(names.index(d) for d in ("brio", "callr", "cli", "waldo", "withr", "pkgload")),
         "packages.lock: dependencias antes que testthat")
    need(cran.get("testthat", {}).get("version") == testthat.get("version")
         and cran["testthat"]["sha256"] == testthat.get("sha256"), "testthat de components == packages.lock")
    need(cran.get("renv", {}).get("version") == renv.get("version")
         and cran["renv"]["sha256"] == renv.get("sha256"), "renv de components == packages.lock")
    need(manifest.get("packages_lock") == "toolchains/r/packages.lock", "packages_lock apunta a toolchains/r/packages.lock")
    need('echo "$sum  $f" | sha256sum -c -' in dockerfile, "el Dockerfile verifica el SHA-256 de cada paquete CRAN")
    need('repos = "file:///opt/gordus-r/repo"' in dockerfile and "dependencies = FALSE" in dockerfile,
         "los paquetes se instalan solo desde el repositorio local verificado")

    # --- rprofile.site: repositorio local, sin red
    prof = (base / "rprofile.site").read_text(encoding="utf-8")
    need(f'repos = c(GORDUS = "{LOCAL_REPO}")' in prof, "rprofile.site: repos = repositorio local")
    need(re.search(r"https?://", prof) is None, "rprofile.site sin URLs de red")
    need("renv.config.updates.check = FALSE" in prof, "rprofile.site: renv sin chequeo de actualizaciones")

    # --- Dockerfile: etapas, imagen final
    clean = strip_comments(dockerfile)
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, clean, flags=re.M) is None, reason)
    froms = re.findall(r"^FROM\s+(\S+)", clean, flags=re.M)
    need(froms == ["debian:13-slim"] * 2, "2 etapas, todas FROM debian:13-slim")
    final = split_stages(clean)[-1]
    need("command -v python3 || command -v python || command -v curl || command -v wget" in final,
         "la imagen final verifica que no haya Python ni curl/wget")
    pkgs = manifest.get("runtime_packages") or {}
    need(bool(pkgs), "runtime_packages declarados")
    installed = dict(re.findall(r"^\s+([a-z0-9][a-z0-9+.-]*)=(\S+)\s*\\?$", final, flags=re.M))
    need(installed == pkgs, "paquetes Debian de la imagen final fijados == runtime_packages")
    need(not ({"curl", "wget", "gpg", "gcc", "g++", "gfortran", "make", "python3", "python3-minimal"} & set(installed)),
         "la imagen final no instala curl, compiladores ni Python")
    copies = re.findall(r"^COPY --from=(\S+) (\S+) (\S+)$", final, flags=re.M)
    need(copies == [("r-build", "/opt/r", "/opt/r"), ("r-build", "/opt/r-site-library", "/opt/r-site-library"),
                    ("r-build", "/opt/gordus-r/repo", "/opt/gordus-r/repo")] and "/usr/src/r" not in final,
         "la imagen final solo copia R compilado, la biblioteca y el repositorio local (sin fuentes)")
    env = parse_env(final)
    for key, want in REQUIRED_ENV.items():
        need(env.get(key) == want, f"ENV {key}={want}")
    need(env.get("PATH", "").startswith("/opt/r/bin:"), "PATH empieza por /opt/r/bin")
    need(re.search(r"^USER\s+ruser\s*$", final, flags=re.M) is not None, "usuario no root: ruser")
    need(final.rstrip().splitlines()[-1].strip() == 'CMD ["bash"]', "CMD final bash")
    need("chmod -R a=rX /opt/gordus-r" in final, "codigo de /opt/gordus-r de solo lectura")
    need("chown -R root:root /opt/r /opt/r-site-library /opt/gordus-r" in dockerfile
         and "chmod -R go-w /opt/r /opt/r-site-library /opt/gordus-r" in dockerfile, "/opt/r y bibliotecas de root y sin escritura")
    for d in re.findall(r"install -d -o ruser -g ruser ([^\n&]+)", re.sub(r"\\\n\s*", " ", final)):
        for p in d.split():
            need(p == "/workspace" or p.startswith(STATE_ROOT.rstrip("/")), f"directorio escribible permitido: {p}")

    # --- ejemplo: renv.lock fijado al repositorio local
    hola = base / "examples" / "hola"
    rlock = load_json(hola / "renv.lock")
    need((rlock.get("R") or {}).get("Version") == version, f"renv.lock exige R {version}")
    need((rlock.get("R") or {}).get("Repositories") == [{"Name": "GORDUS", "URL": LOCAL_REPO}], "renv.lock: solo el repositorio local")
    for name, p in (rlock.get("Packages") or {}).items():
        need(p.get("Package") == name and cran.get(name, {}).get("version") == p.get("Version")
             and p.get("Repository") == "GORDUS", f"renv.lock: {name} {p.get('Version')} esta en packages.lock")
    need(bool(rlock.get("Packages")), "renv.lock con paquetes")
    test_r = (hola / "tests/testthat/test_saludo.r").read_text(encoding="utf-8")
    need("test_that(" in test_r and "expect_equal(" in test_r, "la prueba usa testthat")
    need(re.search(r"install\.packages|download\.file|url\(", (hola / "hola.r").read_text(encoding="utf-8")) is None,
         "hola.r no descarga nada")

    # --- prueba de humo
    smoke = (base / "tests/test_r_toolchain.sh").read_text(encoding="utf-8")
    for var, ver in (("R", version), ("TESTTHAT", testthat["version"]), ("RENV", renv["version"])):
        need(f"EXPECTED_{var}_VERSION:-{ver}" in smoke, f"test_r_toolchain.sh espera {var.lower()} {ver}")

    # --- flujo Kestra
    flow = (base / "kestra/r_toolchain_smoke.yaml").read_text(encoding="utf-8")
    need(re.search(r"^id: r_toolchain_smoke$", flow, flags=re.M) is not None, "Kestra: id r_toolchain_smoke")
    need(re.search(r"^namespace: gordus_hub\.toolchains$", flow, flags=re.M) is not None, "Kestra: namespace gordus_hub.toolchains")
    need(f"inputs.r_version == 'R {version}'" in flow and f"testthat {testthat['version']}" in flow
         and f"renv {renv['version']}" in flow, "Kestra exige las versiones fijadas")
    need("io.kestra.plugin.core.execution.Fail" in flow, "Kestra falla cerrado")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/r/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(OTHER_TOOLCHAINS + r"|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
    need("contents: read" in wf, "workflow con permisos de solo lectura")
    need("kestra/kestra:v1.3.40-slim" in wf and ":latest" not in wf, "workflow usa Kestra v1.3.40-slim fijado")
    uses = re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@v(\d+)", wf)
    need(bool(uses), "workflow usa acciones versionadas")
    for name, amajor in uses:
        need(name in MIN_ACTION_MAJOR and int(amajor) >= MIN_ACTION_MAJOR[name], f"accion {name}@v{amajor} nativa de Node 24")

    # --- tarballs locales opcionales (R o paquetes CRAN)
    verified = []
    by_file = {f"{n}_{v}.tar.gz": s for n, v, s in rows}
    for tb in tarballs:
        if not tb.is_file():
            raise Gate(EXIT_BAD_INPUT, f"no existe el tarball {tb}")
        if tb.name == rfile:
            if file_hash(tb, "sha256") != r["sha256"] or file_hash(tb, "sha512") != r["sha512"]:
                raise Gate(EXIT_FAILED, f"SHA-256/SHA-512 no coinciden para {tb.name}")
        elif tb.name in by_file:
            if file_hash(tb, "sha256") != by_file[tb.name]:
                raise Gate(EXIT_FAILED, f"SHA-256 no coincide para {tb.name}")
        else:
            raise Gate(EXIT_BLOCKED, f"tarball no aprobado: {tb.name}")
        verified.append({"file": tb.name, "sha256": file_hash(tb, "sha256")})
        checks.append(f"tarball local verificado: {tb.name}")

    return {"checks": checks, "r_version": version, "testthat_version": testthat["version"],
            "renv_version": renv["version"], "cran_packages": len(rows), "tarballs_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[],
                    help="tarball local de R o de un paquete CRAN cuyo hash se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/r/scripts/validate_r_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (R {report['r_version']}, testthat {report['testthat_version']}, "
              f"renv {report['renv_version']}, {report['cran_packages']} paquetes CRAN)")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
