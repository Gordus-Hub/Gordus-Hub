#!/usr/bin/env python3
"""Validador fail-closed del toolchain Node.js / TypeScript de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/node/components.json y toolchains/node/Dockerfile
fijan exactamente la misma version oficial de Node.js (archivo, URL y SHA-256 por
arquitectura, huella GPG de la clave de release), la configuracion fail-closed de npm
(offline, sin scripts, sin update-notifier/fund/audit), que TypeScript esta fijado en
package.json y package-lock.json con hashes de integridad, los nombres exactos y el aislamiento.

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
SHA512_SRI_RE = re.compile(r"^sha512-[A-Za-z0-9+/]{86}==$")
FPR_RE = re.compile(r"^[0-9A-F]{40}$")
NODE_ARCH = {"amd64": "x64", "arm64": "arm64"}
ARCH_SUFFIX = {"amd64": "AMD64", "arm64": "ARM64"}
NODE_URL_BASE = "https://nodejs.org/dist"
INSTALL_PATH = "/opt/node"
STATE_ROOT = "/var/lib/gordus-node/"
REQUIRED_ENV = {
    "NPM_CONFIG_CACHE": "/var/lib/gordus-node/npm-cache",
    "NPM_CONFIG_PREFIX": "/var/lib/gordus-node/npm-global",
    "NPM_CONFIG_OFFLINE": "true",
    "NPM_CONFIG_IGNORE_SCRIPTS": "true",
    "NPM_CONFIG_UPDATE_NOTIFIER": "false",
    "NPM_CONFIG_FUND": "false",
    "NPM_CONFIG_AUDIT": "false",
    "NO_UPDATE_NOTIFIER": "1",
}
REQUIRED_LICENSES = {"node": "MIT", "npm": "Artistic-2.0", "typescript": "Apache-2.0"}
# Nombres exactos, todo en minusculas salvo Dockerfile y README.md (Linux distingue mayusculas).
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json",
    "examples/hola/package.json", "examples/hola/package-lock.json", "examples/hola/tsconfig.json",
    "examples/hola/src/hola.ts", "examples/hola/src/saludo.js", "examples/hola/test/hola.test.js",
    "tests/test_node_toolchain.sh", "scripts/validate_node_toolchain.py",
    "kestra/node_toolchain_smoke.yaml",
}
CASE_EXEMPT = {"Dockerfile", "README.md"}
WORKFLOW = ".github/workflows/node-toolchain.yml"
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen Node no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen Node no debe copiar scripts/ai/",
    r"toolchains/(java|mojo|go|cpp|rust)\b": "la imagen Node no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen Node no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen Node no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(nodejs|npm|python3?)\b": "sin Node/npm de apt ni Python de sistema",
    r"npm (i|install)\b|npm install -g|corepack enable|\bnvm\b": "solo 'npm ci' (sin npm install / globales / nvm)",
    r"NPM_CONFIG_IGNORE_SCRIPTS=false|NPM_CONFIG_OFFLINE=false|--allow-unauthenticated|strict-ssl": "no se desactivan scripts, offline ni TLS",
    r"/latest(-v\d+\.x)?/|nodejs\.org/dist/latest": "sin carpetas mutables 'latest'",
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


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"JSON invalido en {path.name}: {exc}") from exc


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "node"
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

    # --- nombres exactos y sin archivos sueltos (node_modules/dist no se suben)
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    present = {p for p in present if "__pycache__" not in p}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/node" + (f"; sobran: {sorted(extra)[:10]}" if extra else ""))
    for rel in sorted(present - CASE_EXEMPT):
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "node", "toolchain == node")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("signature_required", True),
                      ("mutable_versions_allowed", False), ("package_lock_required", True),
                      ("install_scripts_allowed", False), ("package_downloads_by_default", False),
                      ("update_notifier", "off"), ("system_python_allowed", False),
                      ("network_tools_allowed", False), ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    need(manifest.get("dockerfile") == "toolchains/node/Dockerfile", "dockerfile apunta a toolchains/node/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == ["node", "npm", "typescript"],
         "componentes exactos: node + npm + typescript")
    node, npm, ts = comps
    for comp in comps:
        lic = REQUIRED_LICENSES[comp["id"]]
        need((comp.get("license") or {}).get("value") == lic, f"licencia {comp['id']}: {lic}")
    version = str(node.get("version", ""))
    need(re.fullmatch(r"\d+\.\d+\.\d+", version) is not None, f"version exacta de Node: {version}")
    need(int(version.split(".")[0]) % 2 == 0 and bool(node.get("lts")), "Node es una linea LTS (version par con nombre LTS)")
    need(node.get("install_path") == INSTALL_PATH, f"install_path == {INSTALL_PATH}")
    sig = node.get("signature") or {}
    fpr = str(sig.get("fingerprint", ""))
    need(FPR_RE.fullmatch(fpr) is not None, "huella GPG de 40 hex en mayusculas")
    need(re.fullmatch(r"[0-9a-f]{40}", str(sig.get("key_repo_commit", ""))) is not None, "commit fijo de nodejs/release-keys")
    need(sig.get("file") == f"{NODE_URL_BASE}/v{version}/SHASUMS256.txt.sig", "firma SHASUMS256.txt.sig de la version")
    need(re.fullmatch(r"\d+\.\d+\.\d+", str(npm.get("version", ""))) is not None, "version exacta de npm (incluida en Node)")
    menv = npm.get("environment") or {}
    for key, want in REQUIRED_ENV.items():
        need(menv.get(key) == want, f"components.json npm.environment.{key} == {want}")
    smoke = manifest.get("smoke_test", "")
    need(bool(smoke) and (repo_root / smoke).is_file(), f"smoke_test existe: {smoke}")

    # --- pines del Dockerfile
    args = parse_dockerfile_args(dockerfile)
    need(args.get("NODE_VERSION") == version, "Dockerfile NODE_VERSION == components.json version")
    need(args.get("NODE_URL_BASE") == NODE_URL_BASE, "Dockerfile NODE_URL_BASE es https://nodejs.org/dist")
    need(args.get("NODE_GPG_FINGERPRINT") == fpr, "Dockerfile NODE_GPG_FINGERPRINT == components.json")
    need(args.get("NODE_RELEASE_KEYS_COMMIT") == sig.get("key_repo_commit"), "Dockerfile NODE_RELEASE_KEYS_COMMIT == components.json")
    artifacts = node.get("artifacts") or []
    need({a.get("arch") for a in artifacts} == set(NODE_ARCH) and len(artifacts) == 2, "artefactos amd64 + arm64")
    by_file: dict[str, str] = {}
    for art in artifacts:
        arch, sha = art["arch"], str(art.get("sha256", ""))
        want_file = f"node-v{version}-linux-{NODE_ARCH[arch]}.tar.xz"
        need(art.get("file") == want_file, f"{arch}: archivo oficial {want_file}")
        need(art.get("url") == f"{NODE_URL_BASE}/v{version}/{want_file}", f"{arch}: URL coincide")
        need(SHA256_RE.fullmatch(sha) is not None, f"{arch}: sha256 con formato valido")
        need(args.get(f"NODE_SHA256_{ARCH_SUFFIX[arch]}") == sha, f"{arch}: Dockerfile NODE_SHA256_{ARCH_SUFFIX[arch]} coincide")
        by_file[want_file] = sha

    # --- etapas
    stages = split_stages(dockerfile)
    need(len(stages) == 3 and all(s.split()[1] == "debian:13-slim" for s in stages), "tres etapas, todas debian:13-slim")
    fetch, cache, final = stages
    need(fetch.split()[2:4] == ["AS", "node-fetch"] and cache.split()[2:4] == ["AS", "npm-cache"], "etapas node-fetch y npm-cache")
    fetch_i, cache_i, final_i = strip_comments(fetch), strip_comments(cache), strip_comments(final)
    need("gpgv --keyring" in fetch_i and "SHASUMS256.txt.sig" in fetch_i, "verifica la firma GPG de SHASUMS256.txt (gpgv)")
    need("--show-keys" in fetch_i and "$NODE_GPG_FINGERPRINT" in fetch_i, "comprueba la huella de la clave de release")
    need("raw.githubusercontent.com/nodejs/release-keys/$NODE_RELEASE_KEYS_COMMIT/" in fetch_i, "clave tomada de nodejs/release-keys en commit fijo")
    need('grep -qx "$sha  $file" SHASUMS256.txt' in fetch_i, "el SHA-256 fijado debe figurar en SHASUMS256.txt firmado")
    need("sha256sum -c" in fetch_i, "verifica el SHA-256 del tarball (sha256sum -c)")
    need("chmod -R go-w /opt/node" in fetch_i, "/opt/node sin escritura para grupo/otros")
    need(re.search(r"npm ci --ignore-scripts\b", cache_i) is not None, "npm-cache usa 'npm ci --ignore-scripts'")
    need("package-lock.json" in cache_i, "npm-cache copia package-lock.json")
    final_apt = " ".join(re.findall(r"apt-get install([^;&|]*)", re.sub(r"\\\n", " ", final_i)))
    need(bool(final_apt) and re.search(r"\b(curl|wget|gpgv?|python3?|xz-utils)\b", final_apt) is None,
         "la imagen final no instala curl/wget/gpg/python")
    need("command -v python3" in final_i and "command -v curl" in final_i, "build falla si aparece Python o curl")
    copies = re.findall(r"^COPY --from=(\S+) (.+)$", final_i, re.M)
    need(copies == [("node-fetch", "/opt/node /opt/node"),
                    ("npm-cache", "--chown=nodeuser:nodeuser /var/lib/gordus-node/npm-cache /var/lib/gordus-node/npm-cache")],
         "la imagen final copia solo /opt/node y la cache de npm")
    fenv = parse_env(final)
    for key, want in REQUIRED_ENV.items():
        need(fenv.get(key) == want, f"ENV {key}={want} en la imagen final")
    need(fenv.get("PATH", "").startswith(f"{INSTALL_PATH}/bin:"), "PATH empieza con /opt/node/bin")
    for key in ("NPM_CONFIG_CACHE", "NPM_CONFIG_PREFIX"):
        need(fenv[key].startswith(STATE_ROOT), f"{key} bajo {STATE_ROOT}")
    need(re.search(r"^USER nodeuser\s*$", final, re.M) is not None, "imagen corre como usuario no-root 'nodeuser'")
    need("chmod -R a=rX /opt/gordus-node" in final, "codigo de solo lectura en /opt/gordus-node")
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, strip_comments(dockerfile)) is None, f"aislamiento: {reason}")

    # --- proyecto de ejemplo: TypeScript fijado con lock + integrity
    hola = base / "examples/hola"
    pkg = load_json(hola / "package.json")
    lock = load_json(hola / "package-lock.json")
    load_json(hola / "tsconfig.json")
    ts_version = str(ts.get("version", ""))
    need(pkg.get("private") is True, "package.json private: true (no se publica)")
    need(not pkg.get("dependencies"), "package.json sin dependencias de runtime")
    need(pkg.get("devDependencies") == {"typescript": ts_version}, f"package.json fija typescript exactamente en {ts_version}")
    scripts = pkg.get("scripts") or {}
    need(not ({"preinstall", "install", "postinstall", "prepare"} & set(scripts)), "package.json sin scripts de instalacion")
    need(lock.get("lockfileVersion") == 3, "package-lock.json lockfileVersion 3")
    root = (lock.get("packages") or {}).get("") or {}
    need(lock.get("name") == pkg.get("name") and root.get("devDependencies") == pkg.get("devDependencies"),
         "package-lock.json sincronizado con package.json")
    packages = {k: v for k, v in (lock.get("packages") or {}).items() if k}
    need(bool(packages), "package-lock.json tiene paquetes")
    for name, meta in sorted(packages.items()):
        need(str(meta.get("resolved", "")).startswith("https://registry.npmjs.org/"), f"{name}: resuelto desde registry.npmjs.org (https)")
        need(SHA512_SRI_RE.fullmatch(str(meta.get("integrity", ""))) is not None, f"{name}: integrity sha512")
        need(not meta.get("hasInstallScript"), f"{name}: sin script de instalacion")
    need(packages.get("node_modules/typescript", {}).get("version") == ts_version, f"lock: typescript {ts_version}")
    for key, want in (ts.get("integrity") or {}).items():
        need(packages.get(key, {}).get("integrity") == want, f"components.json integrity == lock para {key}")
    need({"node_modules/@typescript/typescript-linux-x64", "node_modules/@typescript/typescript-linux-arm64"} <= set(packages),
         "lock incluye el binario de tsc para linux-x64 y linux-arm64")
    need(re.search(r'"engines"\s*:', json.dumps(pkg)) is not None and str((pkg.get("engines") or {}).get("node", "")).startswith(f">={version}"),
         f"package.json engines.node >= {version}")
    test_js = (hola / "test/hola.test.js").read_text(encoding="utf-8")
    need('from "node:test"' in test_js, "la prueba usa node:test")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/node/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(r"toolchains/(java|mojo|go|cpp|rust)\b|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
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

    return {"checks": checks, "node_version": version, "npm_version": npm.get("version"),
            "typescript_version": ts_version, "tarballs_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[], help="tarball local de Node cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/node/scripts/validate_node_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (Node {report['node_version']}, npm {report['npm_version']}, TypeScript {report['typescript_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
