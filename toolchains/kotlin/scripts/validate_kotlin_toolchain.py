#!/usr/bin/env python3
"""Validador fail-closed del toolchain Kotlin de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/kotlin/components.json y toolchains/kotlin/Dockerfile
fijan exactamente el mismo JDK 25 propio (Temurin: URL, SHA-256 por arquitectura y huella GPG,
que ademas se recalcula desde la clave guardada en keys/), el mismo compilador de Kotlin
(URL y SHA-256), los paquetes Debian fijados, los nombres exactos de archivos, el workflow
propio, el flujo Kestra y las reglas de aislamiento.

Codigos de salida (convencion del repo):
  0  PASS        todo coincide
  2  BAD_INPUT   falta un archivo, JSON invalido o argumentos invalidos
  3  BLOCKED     una regla de politica o un pin no coincide (falla cerrado)
  4  FAILED      error inesperado o un archivo local no coincide con su SHA-256
"""
from __future__ import annotations

LANG = "kotlin"

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
JDK_URL_BASE = "https://github.com/adoptium/temurin25-binaries/releases/download"
ADOPTIUM_FPR = "3B04D753C9050D9A5D343F39843C48A565F8F04B"
KEY_FILE_REL = "keys/adoptium-release-key.asc"
POLICY = {
    "fail_closed": True, "checksum_required": True, "gpg_signature_required_for_jdk": True,
    "mutable_versions_allowed": False, "system_package_manager_jdk_allowed": False,
    "network_at_runtime": False, "persistent_installation_authorized": False, "certification": "NOT_GRANTED",
}
JDK_EXPECT = {
    "kind": "jdk", "distribution": "eclipse-temurin", "feature_version": 25, "version": "25.0.5+8",
    "java_version": "25.0.5", "release_tag": "jdk-25.0.5+8", "lts": True,
    "install_path": f"/opt/{LANG}/jdk-25", "java_home": f"/opt/{LANG}/jdk-25",
}
DEB_PACKAGES = {
    "bash": "PKG_BASH_VERSION", "ca-certificates": "PKG_CA_CERTIFICATES_VERSION",
    "fontconfig": "PKG_FONTCONFIG_VERSION", "libfreetype6": "PKG_LIBFREETYPE6_VERSION", "zlib1g": "PKG_ZLIB1G_VERSION",
}
OTHER_TOOLCHAINS = [t for t in ("java", "mojo", "go", "cpp", "rust", "node", "dotnet", "swift", "kotlin", "scala") if t != LANG]
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen no debe copiar scripts/ai/",
    rf"toolchains/({'|'.join(OTHER_TOOLCHAINS)})\b": "la imagen no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(openjdk|default-jdk|default-jre|python3?|kotlin|scala|sbt|gradle|maven)\b": "sin JDK de apt, Python ni herramientas de apt",
    r"--allow-unauthenticated|trusted=yes|--skip-verify|--insecure|\s-k\s": "no se desactiva la verificacion",
    r"-(RC|Beta|M)\d|SNAPSHOT|nightly": "sin versiones preliminares (RC/Beta/SNAPSHOT/nightly)",
}
STATE = "KOTLIN_TOOLCHAIN_CANDIDATE_NOT_RUNTIME_CERTIFIED"
USER = "kotlin"
WORKFLOW = ".github/workflows/kotlin-toolchain.yml"
FLOW_FILE = "kotlin_toolchain_smoke.yaml"
COMPONENT_IDS = ["temurin-jdk-25-for-kotlin", "kotlin-compiler"]
# Nombres exactos, todo en minusculas salvo Dockerfile y README.md (convencion del repo).
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json", "keys/adoptium-release-key.asc",
    "examples/hola.kt", "examples/hola_test.kt",
    "tests/test_kotlin_toolchain.sh", "scripts/validate_kotlin_toolchain.py",
    "kestra/kotlin_toolchain_smoke.yaml",
}
CASE_EXEMPT = {"Dockerfile", "README.md"}
TOOL_EXPECT = {"kind": "compiler", "vendor": "JetBrains", "version": "2.4.21", "release_tag": "v2.4.21", "install_path": "/opt/kotlin/kotlinc"}
TOOL_ARCHES = ["any"]
TOOL_URL_PREFIX = "https://github.com/JetBrains/kotlin/releases/download/v2.4.21/"
def TOOL_ARG_MAP(art):
    return [("KOTLIN_URL", "url"), ("KOTLIN_SHA256", "sha256"), ("KOTLIN_VERSION", "2.4.21")]
TOOL_DOCKERFILE_SNIPPETS = {
    'echo "$KOTLIN_SHA256  /tmp/kotlin.zip" | sha256sum -c -': "Dockerfile verifica el SHA-256 del compilador Kotlin",
    'grep -qx "$KOTLIN_VERSION" /opt/kotlin/kotlinc/build.txt': "Dockerfile comprueba build.txt == version de Kotlin",
}
REQUIRED_ENV = {
    "JAVA_HOME": "/opt/kotlin/jdk-25", "KOTLIN_HOME": "/opt/kotlin/kotlinc",
    "GORDUS_KOTLIN_OFFLINE": "true", "LANG": "C.UTF-8",
}
PATH_PREFIX = "/opt/kotlin/kotlinc/bin:/opt/kotlin/jdk-25/bin:"


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


def strip_comments(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


def split_stages(text: str) -> list[str]:
    return [p for p in re.split(r"^(?=FROM\s)", text, flags=re.M) if p.startswith("FROM ")]


def parse_env(stage: str) -> dict[str, str]:
    env: dict[str, str] = {}
    joined = re.sub(r"\\\n", " ", stage)
    for line in joined.splitlines():
        if line.startswith("ENV "):
            for key, value in re.findall(r"([A-Z_][A-Z0-9_]*)=(\S+)", line[4:]):
                env[key] = value
    return env


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


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []

    def need(cond: bool, label: str, code: int = EXIT_BLOCKED) -> None:
        if not cond:
            raise Gate(code, f"fallo: {label}")
        checks.append(label)

    base = repo_root / "toolchains" / LANG
    manifest_path, dockerfile_path = base / "components.json", base / "Dockerfile"
    for p in (manifest_path, dockerfile_path, base / KEY_FILE_REL):
        if not p.is_file():
            raise Gate(EXIT_BAD_INPUT, f"falta el archivo {p}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise Gate(EXIT_BAD_INPUT, f"components.json invalido: {exc}") from exc
    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    instructions = strip_comments(dockerfile)
    args = parse_dockerfile_args(dockerfile)

    # 1) Archivos exactos y nombres en minusculas (salvo los que la herramienta exige).
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    need(not (present - EXPECTED_FILES), f"sin archivos extra en toolchains/{LANG}/ ({sorted(present - EXPECTED_FILES)})")
    need(not (EXPECTED_FILES - present), f"no falta ningun archivo en toolchains/{LANG}/ ({sorted(EXPECTED_FILES - present)})", EXIT_BAD_INPUT)
    for rel in sorted(EXPECTED_FILES):
        if rel not in CASE_EXEMPT:
            need(rel == rel.lower(), f"nombre en minusculas: {rel}")
    for d in sorted({p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_dir()}):
        need(d == d.lower(), f"carpeta en minusculas: {d}")
    need((repo_root / WORKFLOW).is_file(), f"existe el workflow propio {WORKFLOW}", EXIT_BAD_INPUT)
    workflow = (repo_root / WORKFLOW).read_text(encoding="utf-8")
    need(f'"toolchains/{LANG}/**"' in workflow, "el workflow solo se dispara con cambios en su carpeta (paths)")
    need(re.search(r"uses:\s*actions/[\w-]+@v[1-4]\b", workflow) is None, "el workflow no usa acciones basadas en Node 20 (v1-v4)")
    for action in ("actions/checkout@v7", "actions/upload-artifact@v7", "actions/setup-python@v7"):
        need(action in workflow, f"workflow usa {action} (Node 24)")
    need("kestra/kestra:v1.3.40-slim" in workflow, "workflow fija Kestra v1.3.40-slim")
    need("--network none" in workflow, "workflow corre la prueba sin red (--network none)")
    flow_path = base / "kestra" / FLOW_FILE
    flow = flow_path.read_text(encoding="utf-8")
    need(re.search(rf"^id: {LANG}_toolchain_smoke\s*$", flow, re.M) is not None, f"flujo Kestra id {LANG}_toolchain_smoke")
    need(re.search(r"^namespace: gordus_hub\.toolchains\s*$", flow, re.M) is not None, "flujo Kestra en namespace gordus_hub.toolchains")
    need("io.kestra.plugin.core.execution.Fail" in flow, "flujo Kestra falla cerrado (Fail)")

    # 2) Manifiesto: politica.
    need(manifest.get("schema_version") == 1, "schema_version == 1", EXIT_BAD_INPUT)
    need(manifest.get("toolchain") == LANG, f"toolchain == {LANG}")
    need(manifest.get("state") == STATE, f"estado {STATE}")
    need(manifest.get("dockerfile") == f"toolchains/{LANG}/Dockerfile", "dockerfile declarado")
    policy = manifest.get("policy") or {}
    for key, value in POLICY.items():
        need(policy.get(key) == value, f"policy.{key} == {value!r}")
    for path in ("ai/", "scripts/ai/", ".devcontainer/", "toolchains/java/"):
        need(path in (policy.get("isolated_from") or []), f"aislado de {path}")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == COMPONENT_IDS, f"componentes exactos {COMPONENT_IDS}", EXIT_BAD_INPUT)
    jdk, tool = comps

    # 3) JDK propio: version, URL, SHA-256 y GPG.
    for key, value in JDK_EXPECT.items():
        need(jdk.get(key) == value, f"jdk.{key} == {value!r}")
    need(args.get("JDK_VERSION") == jdk["version"], "Dockerfile JDK_VERSION coincide")
    need(args.get("JDK_RELEASE_TAG") == jdk["release_tag"].replace("+", "%2B"), "Dockerfile JDK_RELEASE_TAG coincide")
    need(args.get("JDK_URL_BASE") == JDK_URL_BASE, "Dockerfile JDK_URL_BASE oficial (Adoptium en GitHub)")
    gpg = jdk.get("gpg") or {}
    need(gpg.get("fingerprint") == ADOPTIUM_FPR, "huella GPG de Adoptium fijada en components.json")
    need(args.get("ADOPTIUM_GPG_FINGERPRINT") == ADOPTIUM_FPR, "huella GPG de Adoptium fijada en el Dockerfile")
    need(gpg.get("key_file") == f"toolchains/{LANG}/{KEY_FILE_REL}", "components.json apunta a la clave guardada en el repo")
    key_text = (base / KEY_FILE_REL).read_text(encoding="ascii")
    need(openpgp_primary_fingerprint(key_text) == ADOPTIUM_FPR, "la clave guardada en keys/ tiene exactamente la huella fijada")
    need("gpgv --keyring" in instructions and ".sig" in instructions, "Dockerfile verifica la firma GPG del JDK (gpgv)")
    need("--show-keys" in instructions and '[ "$fpr" = "$ADOPTIUM_GPG_FINGERPRINT" ]' in instructions, "Dockerfile compara la huella antes de verificar")
    approved: dict[str, str] = {}
    arts = jdk.get("artifacts") or []
    need([a.get("arch") for a in arts] == ["amd64", "arm64"], "JDK: artefactos amd64 y arm64", EXIT_BAD_INPUT)
    for art in arts:
        suf = art["arch"].upper()
        need(SHA256_RE.match(str(art.get("sha256", ""))) is not None, f"JDK {art['arch']}: sha256 valido")
        need(art.get("url") == f"{JDK_URL_BASE}/{args.get('JDK_RELEASE_TAG')}/{art.get('file')}", f"JDK {art['arch']}: URL coincide")
        need(args.get(f"JDK_FILE_{suf}") == art.get("file"), f"JDK {art['arch']}: Dockerfile JDK_FILE_{suf} coincide")
        need(args.get(f"JDK_SHA256_{suf}") == art.get("sha256"), f"JDK {art['arch']}: Dockerfile JDK_SHA256_{suf} coincide")
        approved[art["file"]] = art["sha256"]
    need(f'grep -qx "JAVA_VERSION=\\"{jdk["java_version"]}\\""' in instructions, "Dockerfile comprueba JAVA_VERSION del release")

    # 4) Herramienta del lenguaje.
    for key, value in TOOL_EXPECT.items():
        need(tool.get(key) == value, f"{tool.get('id')}.{key} == {value!r}")
    tarts = tool.get("artifacts") or []
    need([a.get("arch") for a in tarts] == TOOL_ARCHES, f"{LANG}: artefactos {TOOL_ARCHES}", EXIT_BAD_INPUT)
    for art in tarts:
        need(SHA256_RE.match(str(art.get("sha256", ""))) is not None, f"{LANG} {art['arch']}: sha256 valido")
        for argname, field in TOOL_ARG_MAP(art):
            need(args.get(argname) == (art.get(field) if field in art else field), f"{LANG} {art['arch']}: Dockerfile {argname} coincide")
        need(str(art.get("url", "")).startswith(TOOL_URL_PREFIX), f"{LANG} {art['arch']}: URL oficial")
        approved[art["file"]] = art["sha256"]
    for snippet, label in TOOL_DOCKERFILE_SNIPPETS.items():
        need(snippet in instructions, label)
    need(instructions.count("sha256sum -c") >= 2, "Dockerfile verifica SHA-256 del JDK y de la herramienta")

    # 5) Imagen final: base, usuario, solo lectura, entorno, paquetes Debian fijados.
    stages = split_stages(instructions)
    need(len(stages) == 2, "Dockerfile multi-stage (2 etapas)")
    need(all(s.startswith("FROM debian:13-slim") for s in stages), "todas las etapas usan debian:13-slim")
    final = stages[-1]
    env = parse_env(final)
    for key, value in REQUIRED_ENV.items():
        need(env.get(key) == value, f"ENV {key}={value}")
    need(env.get("PATH", "").startswith(PATH_PREFIX), f"PATH empieza con {PATH_PREFIX}")
    need(re.search(rf"^USER {USER}\s*$", final, re.M) is not None, f"imagen corre como usuario no-root '{USER}'")
    need(f"chmod -R a=rX /opt/gordus-{LANG}" in final, f"codigo de solo lectura en /opt/gordus-{LANG}")
    need(f"chmod -R go-w /opt/{LANG}" in final, f"toolchain sin escritura para otros en /opt/{LANG}")
    need(f"COPY --from=fetch /opt/{LANG} /opt/{LANG}" in final, "la imagen final solo copia el toolchain desde la etapa fetch")
    pins = manifest.get("debian_packages") or {}
    need(set(pins) == set(DEB_PACKAGES), "components.json fija exactamente los paquetes Debian de la imagen final")
    for pkg, argname in DEB_PACKAGES.items():
        need(args.get(argname) == pins.get(pkg), f"Debian {pkg}={pins.get(pkg)} coincide con ARG {argname}")
        need(f'{pkg}="${argname}"' in final, f"apt instala {pkg} con version fija")
    need(re.search(r"\b(curl|wget|python3?|gpg|unzip|git)\b", final.split("COPY --from=fetch")[0].split("apt-get install", 1)[-1].split("rm -rf")[0]) is None,
         "imagen final sin curl, wget, python, gpg, unzip ni git")
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, instructions) is None, f"aislamiento: {reason}")

    # 6) Tarballs locales opcionales.
    verified = []
    for tb in tarballs:
        if not tb.is_file():
            raise Gate(EXIT_BAD_INPUT, f"no existe el archivo {tb}")
        if tb.name not in approved:
            raise Gate(EXIT_BLOCKED, f"archivo no aprobado: {tb.name}")
        got = sha256_file(tb)
        if got != approved[tb.name]:
            raise Gate(EXIT_FAILED, f"SHA-256 no coincide para {tb.name}: {got}")
        verified.append({"file": tb.name, "sha256": got})
        checks.append(f"archivo local verificado: {tb.name}")

    return {"checks": checks, "jdk_version": jdk["version"], "tool_version": tool["version"], "files_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[], help="archivo descargado cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": f"toolchains/{LANG}/scripts/validate_{LANG}_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK ({LANG} {report['tool_version']}, JDK {report['jdk_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
