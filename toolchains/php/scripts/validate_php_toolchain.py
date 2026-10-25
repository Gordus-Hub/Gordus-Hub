#!/usr/bin/env python3
"""Validador fail-closed del toolchain PHP de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/php/components.json y toolchains/php/Dockerfile
fijan exactamente la misma version oficial de PHP (tarball, SHA-256 y huella GPG del release
manager), de Composer y de PHPUnit (PHAR, SHA-256 y huella GPG), que PHP tiene el parche de
seguridad del 21/10/2026 (CVE-2026-109618 y CVE-2026-109619: minimo 8.5.12 / 8.4.27 / 8.3.36 /
8.2.35), las mitigaciones de php.ini, la politica sin red de Composer, los nombres exactos y el
aislamiento.

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
# Piso de seguridad: versiones que corrigen CVE-2026-109618 y CVE-2026-109619 (php.net, 21/10/2026).
# Ramas sin soporte de php.net (8.1 o anteriores) quedan bloqueadas.
PHP_SECURITY_FLOOR = {(8, 5): (8, 5, 12), (8, 4): (8, 4, 27), (8, 3): (8, 3, 36), (8, 2): (8, 2, 35)}
PHP_FLOOR_ID = 80512  # la imagen usa la rama 8.5
COMPOSER_FLOOR = (2, 10, 3)  # GHSA-96h3-5x6v-m776 / GHSA-rvx4-ffvw-m9q3 corregidos en 2.10.3
KEY_FILES = {"composer": "composer-packagist.asc", "phpunit": "phpunit-sebastian-bergmann.asc"}
PHPUNIT_VULNERABLE = {"12.5.21", "13.1.5"}  # GHSA-qrr6-mg7r-m243 (CVE-2026-41570)
PHP_URL_BASE = "https://www.php.net/distributions"
STATE_ROOT = "/var/lib/gordus-php/"
REQUIRED_ENV = {
    "COMPOSER_HOME": "/var/lib/gordus-php/composer",
    "COMPOSER_CACHE_DIR": "/var/lib/gordus-php/composer-cache",
    "COMPOSER_DISABLE_NETWORK": "1",
    "COMPOSER_NO_AUDIT": "1",
    "COMPOSER_NO_INTERACTION": "1",
    "COMPOSER_ALLOW_SUPERUSER": "0",
}
REQUIRED_INI = {
    "session.upload_progress.enabled": "0",
    "fatal_error_backtraces": "0",
    "expose_php": "Off",
    "allow_url_include": "Off",
}
REQUIRED_LICENSES = {"php": "PHP-3.01", "composer": "MIT", "phpunit": "BSD-3-Clause"}
# Nombres exactos, todo en minusculas salvo los que exige una herramienta:
# Dockerfile y README.md (convencion del repo) y SaludoTest.php (PHPUnit exige que el archivo
# se llame igual que la clase de prueba).
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json", "php-gordus.ini",
    "keys/php-release-manager-daniel-scherzer.asc", "keys/composer-packagist.asc", "keys/phpunit-sebastian-bergmann.asc",
    "examples/hola/composer.json", "examples/hola/composer.lock", "examples/hola/phpunit.xml",
    "examples/hola/hola.php", "examples/hola/src/saludo.php", "examples/hola/tests/SaludoTest.php",
    "tests/test_php_toolchain.sh", "scripts/validate_php_toolchain.py",
    "kestra/php_toolchain_smoke.yaml",
}
CASE_EXEMPT = {"Dockerfile", "README.md", "examples/hola/tests/SaludoTest.php"}
WORKFLOW = ".github/workflows/php-toolchain.yml"
OTHER_TOOLCHAINS = r"toolchains/(java|mojo|go|cpp|rust|node|dotnet|swift|ruby)\b"
# Acciones de GitHub que corren nativamente en Node 24 (verificado en su action.yml).
MIN_ACTION_MAJOR = {"actions/checkout": 5, "actions/setup-python": 6, "actions/upload-artifact": 6}
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen PHP no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen PHP no debe copiar scripts/ai/",
    OTHER_TOOLCHAINS: "la imagen PHP no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen PHP no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen PHP no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(php[0-9.]*(-[a-z]+)?|composer|phpunit|python3?)\b": "sin PHP/Composer de apt ni Python de sistema",
    r"--enable-fpm|--with-apxs|--enable-cgi\b|--enable-phpdbg\b": "solo PHP CLI (sin FPM, mod_php, CGI ni phpdbg)",
    r"getcomposer\.org/installer|composer-setup": "sin el instalador web de Composer (se usa el PHAR firmado)",
    r"COMPOSER_DISABLE_NETWORK=0|--allow-unauthenticated|--insecure\b|\s-k\s|secure-http\W+false": "no se desactiva la red controlada ni TLS",
    r"/latest/|/stable/|latest-stable|getcomposer\.org/composer\.phar|phar\.phpunit\.de/phpunit\.phar": "sin URLs mutables 'latest'/'stable'",
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


def php_security_ok(version: str) -> tuple[bool, str]:
    v = parse_version(version)
    floor = PHP_SECURITY_FLOOR.get(v[:2])
    if floor is None:
        return False, f"rama PHP {v[0]}.{v[1]} sin soporte o sin parche conocido"
    if v < floor:
        return False, f"PHP {version} es anterior al parche {'.'.join(map(str, floor))} (CVE-2026-109618/109619)"
    return True, f"PHP {version} >= {'.'.join(map(str, floor))}"


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


def validate(repo_root: Path, local_files: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "php"
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

    # --- nombres exactos y sin archivos sueltos (vendor/ no se sube)
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    present = {p for p in present if "__pycache__" not in p}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/php" + (f"; sobran: {sorted(extra)[:10]}" if extra else ""))
    for rel in sorted(present - CASE_EXEMPT):
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "php", "toolchain == php")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("signature_required", True),
                      ("mutable_versions_allowed", False), ("lockfile_required", True),
                      ("composer_plugins_allowed", False), ("package_downloads_by_default", False),
                      ("system_python_allowed", False), ("network_tools_allowed", False),
                      ("persistent_installation_authorized", False), ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    isolated = set(policy.get("isolated_from") or [])
    need({"ai/", "scripts/ai/", ".devcontainer/", "kestra/flows/", "toolchains/ruby/", "toolchains/node/"} <= isolated,
         "policy.isolated_from incluye ai/, .devcontainer/, kestra/flows/ y los otros toolchains")
    need(manifest.get("dockerfile") == "toolchains/php/Dockerfile", "dockerfile apunta a toolchains/php/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    need(manifest.get("architectures") == ["amd64", "arm64"], "arquitecturas amd64 + arm64")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == ["php", "composer", "phpunit"],
         "componentes exactos: php + composer + phpunit")
    php, composer, phpunit = comps
    for comp in comps:
        lic = comp.get("license") or {}
        need(lic.get("value") == REQUIRED_LICENSES[comp["id"]] and lic.get("status") == "DECLARED",
             f"licencia declarada de {comp['id']}: {REQUIRED_LICENSES[comp['id']]}")

    args = parse_dockerfile_args(dockerfile)

    # --- PHP: version, piso de seguridad, tarball, SHA-256, firma
    version = str(php.get("version", ""))
    parse_version(version)
    ok, why = php_security_ok(version)
    if not ok:
        raise Gate(EXIT_BLOCKED, f"SEGURIDAD: {why}")
    checks.append(f"SEGURIDAD: {why}")
    vt = parse_version(version)
    need(vt[:2] == (8, 5), "PHP usa la rama estable mas nueva con parche (8.5)")
    need(vt[0] * 10000 + vt[1] * 100 + vt[2] >= PHP_FLOOR_ID, f"PHP_VERSION_ID >= {PHP_FLOOR_ID}")
    sec = manifest.get("security") or {}
    floors = sec.get("php_minimum_patched") or {}
    need(floors == {f"{a}.{b}": ".".join(map(str, f)) for (a, b), f in PHP_SECURITY_FLOOR.items()},
         "security.php_minimum_patched == 8.5.12 / 8.4.27 / 8.3.36 / 8.2.35")
    need({f.get("id") for f in sec.get("fixes") or []} == {"CVE-2026-109618", "CVE-2026-109619"},
         "security.fixes registra CVE-2026-109618 y CVE-2026-109619")
    need(sec.get("ini_mitigations") == REQUIRED_INI, "security.ini_mitigations completas")
    need(args.get("PHP_VERSION") == version, f"Dockerfile PHP_VERSION == {version}")
    need(args.get("PHP_URL_BASE") == PHP_URL_BASE, "Dockerfile PHP_URL_BASE oficial (php.net)")
    php_file = f"php-{version}.tar.xz"
    need(php.get("source") == f"{PHP_URL_BASE}/{php_file}", f"source == {PHP_URL_BASE}/{php_file}")
    need(SHA256_RE.fullmatch(str(php.get("sha256", ""))) is not None, "php sha256 con formato valido")
    need(args.get("PHP_SHA256") == php.get("sha256"), "Dockerfile PHP_SHA256 == components.json")
    sig = php.get("signature") or {}

    def check_key(sg: dict, cid: str, fname: str, dest: str) -> None:
        rel = f"toolchains/php/keys/{fname}"
        need(sg.get("key_file") == rel, f"{cid}: clave guardada en {rel}")
        text = (repo_root / rel).read_text(encoding="utf-8")
        need(openpgp_primary_fingerprint(text) == sg.get("fingerprint"), f"{cid}: la clave de keys/ tiene exactamente la huella fijada")
        need(text.count("-----BEGIN PGP PUBLIC KEY BLOCK-----") == 1, f"{cid}: keys/ trae una sola clave")
        need(f"COPY {rel} {dest}" in dockerfile, f"{cid}: el Dockerfile copia la clave desde keys/")
    need(sig.get("file") == f"{PHP_URL_BASE}/{php_file}.asc", "firma .asc oficial del tarball")
    need(FPR_RE.fullmatch(str(sig.get("fingerprint", ""))) is not None, "huella GPG de PHP de 40 hex")
    need(args.get("PHP_GPG_FINGERPRINT") == sig.get("fingerprint"), "Dockerfile PHP_GPG_FINGERPRINT == components.json")
    need(sig.get("keyring") == f"{PHP_URL_BASE}/php-keyring.gpg", "origen de la clave: keyring oficial de php.net")
    check_key(sig, "php", "php-release-manager-daniel-scherzer.asc", "/tmp/keys/php-rm.asc")
    need("VALIDSIG" in dockerfile and "gpgv --status-fd 1" in dockerfile, "gpgv exige VALIDSIG de la huella fijada")
    need(f"PHP_VERSION_ID >= {PHP_FLOOR_ID}" in dockerfile, f"la imagen bloquea PHP_VERSION_ID < {PHP_FLOOR_ID} al construir")
    conf = php.get("configure") or []
    for flag in conf:
        need(flag in dockerfile, f"configure usa {flag}")
    need("--disable-cgi" in conf and "--disable-phpdbg" in conf, "configure solo CLI")

    # --- Composer y PHPUnit
    cv = str(composer.get("version", ""))
    need(parse_version(cv) >= COMPOSER_FLOOR, f"Composer {cv} >= 2.10.3 (avisos de seguridad corregidos)")
    pv = str(phpunit.get("version", ""))
    parse_version(pv)
    need(pv not in PHPUNIT_VULNERABLE and pv not in set(sec.get("phpunit_vulnerable_versions") or []),
         f"PHPUnit {pv} fuera de las versiones vulnerables")
    need(sec.get("composer_minimum_patched") == "2.10.3", "security.composer_minimum_patched == 2.10.3")
    for comp, prefix, url in ((composer, "COMPOSER", f"https://getcomposer.org/download/{cv}/composer.phar"),
                              (phpunit, "PHPUNIT", f"https://phar.phpunit.de/phpunit-{pv}.phar")):
        cid = comp["id"]
        need(args.get(f"{prefix}_VERSION") == comp.get("version"), f"Dockerfile {prefix}_VERSION == components.json")
        need(comp.get("source") == url, f"{cid}: source == {url}")
        need(SHA256_RE.fullmatch(str(comp.get("sha256", ""))) is not None, f"{cid}: sha256 con formato valido")
        need(args.get(f"{prefix}_SHA256") == comp.get("sha256"), f"Dockerfile {prefix}_SHA256 == components.json")
        csig = comp.get("signature") or {}
        need(csig.get("file") == url + ".asc", f"{cid}: firma .asc oficial")
        need(FPR_RE.fullmatch(str(csig.get("fingerprint", ""))) is not None, f"{cid}: huella GPG de 40 hex")
        need(args.get(f"{prefix}_GPG_FINGERPRINT") == csig.get("fingerprint"), f"Dockerfile {prefix}_GPG_FINGERPRINT == components.json")
        need(csig.get("key_source") == f"https://keys.openpgp.org/vks/v1/by-fingerprint/{csig.get('fingerprint')}",
             f"{cid}: origen de la clave por huella")
        check_key(csig, cid, KEY_FILES[cid], f"/tmp/keys/{cid}.phar.key.asc")
    need(re.search(r"keys\.openpgp\.org|php-keyring\.gpg\"|KEYSERVER_URL|PHP_KEYRING_URL", strip_comments(dockerfile)) is None,
         "el Dockerfile no baja claves GPG (estan en keys/)")
    need(composer.get("environment") == REQUIRED_ENV, "components.json: entorno de Composer exacto")

    # --- Dockerfile: etapas, imagen final
    clean = strip_comments(dockerfile)
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, clean, flags=re.M) is None, reason)
    froms = re.findall(r"^FROM\s+(\S+)", clean, flags=re.M)
    need(froms == ["debian:13-slim"] * 3, "3 etapas, todas FROM debian:13-slim")
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
    need(re.search(r"^COPY --from=php-build /opt/php /opt/php$", final, flags=re.M) is not None
         and "/usr/src/php" not in final, "la imagen final solo copia /opt/php compilado (sin fuentes)")
    env = parse_env(final)
    for key, want in REQUIRED_ENV.items():
        need(env.get(key) == want, f"ENV {key}={want}")
    need(env.get("PATH", "").startswith("/opt/php/bin:"), "PATH empieza por /opt/php/bin")
    need(re.search(r"^USER\s+phpuser\s*$", final, flags=re.M) is not None, "usuario no root: phpuser")
    need(final.rstrip().splitlines()[-1].strip() == 'CMD ["bash"]', "CMD final bash")
    need("chmod -R a=rX /opt/gordus-php" in final, "codigo de /opt/gordus-php de solo lectura")
    need("chown -R root:root /opt/php" in final and "chmod -R go-w /opt/php" in final, "/opt/php de root y sin escritura")
    need("COPY toolchains/php/php-gordus.ini /opt/php/etc/conf.d/90-gordus.ini" in final, "se instalan las mitigaciones de php.ini")
    for d in re.findall(r"install -d -o phpuser -g phpuser ([^\n&]+)", re.sub(r"\\\n\s*", " ", final)):
        for p in d.split():
            need(p == "/workspace" or p.startswith(STATE_ROOT.rstrip("/")), f"directorio escribible permitido: {p}")

    # --- php-gordus.ini
    ini = {}
    for line in (base / "php-gordus.ini").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(";"):
            k, _, v = line.partition("=")
            ini[k.strip()] = v.strip()
    for key, want in REQUIRED_INI.items():
        need(ini.get(key) == want, f"php-gordus.ini: {key} = {want}")

    # --- ejemplo
    hola = base / "examples" / "hola"
    cj = load_json(hola / "composer.json")
    lock = load_json(hola / "composer.lock")
    need((cj.get("require") or {}).get("php") == f">={version}", f"composer.json exige php >={version}")
    need(set((cj.get("require") or {})) == {"php"} and not cj.get("require-dev"), "composer.json sin dependencias de terceros")
    cfg = cj.get("config") or {}
    need(cfg.get("allow-plugins") is False, "composer.json: allow-plugins false")
    need(cfg.get("secure-http") is True, "composer.json: secure-http true")
    need(not (cj.get("scripts") or {}), "composer.json sin scripts")
    need(re.fullmatch(r"[0-9a-f]{32}", str(lock.get("content-hash", ""))) is not None, "composer.lock con content-hash")
    need(lock.get("packages") == [] and lock.get("packages-dev") == [], "composer.lock sin paquetes de terceros")
    need((lock.get("platform") or {}).get("php") == f">={version}", "composer.lock sincronizado (platform php)")
    pxml = (hola / "phpunit.xml").read_text(encoding="utf-8")
    need('failOnWarning="true"' in pxml and 'suffix="Test.php"' in pxml, "phpunit.xml estricto (failOnWarning) y sufijo Test.php")
    test_php = (hola / "tests/SaludoTest.php").read_text(encoding="utf-8")
    need("final class SaludoTest extends TestCase" in test_php, "la prueba usa PHPUnit TestCase")
    for f in ("hola.php", "src/saludo.php", "tests/SaludoTest.php"):
        need("declare(strict_types=1);" in (hola / f).read_text(encoding="utf-8"), f"{f}: strict_types")

    # --- prueba de humo
    smoke = (base / "tests/test_php_toolchain.sh").read_text(encoding="utf-8")
    need(f'EXPECTED_PHP_VERSION:-{version}' in smoke and f'EXPECTED_COMPOSER_VERSION:-{cv}' in smoke
         and f'EXPECTED_PHPUNIT_VERSION:-{pv}' in smoke, "test_php_toolchain.sh espera las mismas versiones")
    need(f"min_php_id={PHP_FLOOR_ID}" in smoke, f"test_php_toolchain.sh bloquea PHP_VERSION_ID < {PHP_FLOOR_ID}")

    # --- flujo Kestra
    flow = (base / "kestra/php_toolchain_smoke.yaml").read_text(encoding="utf-8")
    need(re.search(r"^id: php_toolchain_smoke$", flow, flags=re.M) is not None, "Kestra: id php_toolchain_smoke")
    need(re.search(r"^namespace: gordus_hub\.toolchains$", flow, flags=re.M) is not None, "Kestra: namespace gordus_hub.toolchains")
    need(f"inputs.php_version == 'php {version}'" in flow and "inputs.security_patch == 'PASS'" in flow
         and f"composer {cv}" in flow and f"phpunit {pv}" in flow, "Kestra exige las versiones y el parche")
    need("io.kestra.plugin.core.execution.Fail" in flow, "Kestra falla cerrado")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/php/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(OTHER_TOOLCHAINS + r"|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
    need("contents: read" in wf, "workflow con permisos de solo lectura")
    need("kestra/kestra:v1.3.40-slim" in wf and ":latest" not in wf, "workflow usa Kestra v1.3.40-slim fijado")
    uses = re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@v(\d+)", wf)
    need(bool(uses), "workflow usa acciones versionadas")
    for name, major in uses:
        need(name in MIN_ACTION_MAJOR and int(major) >= MIN_ACTION_MAJOR[name], f"accion {name}@v{major} nativa de Node 24")

    verified = []
    expected_local = {php_file: php.get("sha256"), "composer.phar": composer.get("sha256"),
                      f"phpunit-{pv}.phar": phpunit.get("sha256")}
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

    return {"checks": checks, "php_version": version, "composer_version": cv, "phpunit_version": pv,
            "security_floor": "8.5.12", "files_verified": verified}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[],
                    help="tarball de PHP o PHAR local cuyo SHA-256 se verifica (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/php/scripts/validate_php_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (PHP {report['php_version']} con parche de seguridad, "
              f"Composer {report['composer_version']}, PHPUnit {report['phpunit_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
