#!/usr/bin/env python3
"""Validador fail-closed del toolchain Ruby de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de los
otros toolchains. Comprueba que toolchains/ruby/components.json y toolchains/ruby/Dockerfile
fijan exactamente la misma version oficial de Ruby (tarball, SHA-256 y SHA-512), que RubyGems,
Bundler, Minitest y Rake son los que vienen dentro de Ruby, que Gemfile.lock esta congelado con
checksums sha256, la politica sin red, los nombres exactos y el aislamiento.

Ruby no publica firmas GPG de sus tarballs; por eso se exigen DOS hashes de dos fuentes oficiales.

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
SHA512_RE = re.compile(r"^[0-9a-f]{128}$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
RUBY_URL_BASE = "https://cache.ruby-lang.org/pub/ruby"
STATE_ROOT = "/var/lib/gordus-ruby/"
REQUIRED_ENV = {
    "GEM_HOME": "/var/lib/gordus-ruby/gems",
    "GEM_PATH": "/var/lib/gordus-ruby/gems:/opt/ruby/lib/ruby/gems/4.0.0",
    "BUNDLE_USER_HOME": "/var/lib/gordus-ruby/bundle",
    "BUNDLE_FROZEN": "true",
    "BUNDLE_DISABLE_VERSION_CHECK": "true",
    "BUNDLE_IGNORE_FUNDING_REQUESTS": "true",
}
REQUIRED_LICENSES = {"ruby": "Ruby OR BSD-2-Clause", "rubygems": "Ruby OR MIT", "bundler": "MIT",
                     "minitest": "MIT", "rake": "MIT"}
# Nombres exactos, todo en minusculas salvo los que exige una herramienta:
# Dockerfile y README.md (convencion del repo), Gemfile y Gemfile.lock (Bundler) y Rakefile (Rake).
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json",
    "examples/hola/Gemfile", "examples/hola/Gemfile.lock", "examples/hola/Rakefile",
    "examples/hola/hola.rb", "examples/hola/lib/saludo.rb", "examples/hola/test/saludo_test.rb",
    "tests/test_ruby_toolchain.sh", "scripts/validate_ruby_toolchain.py",
    "kestra/ruby_toolchain_smoke.yaml",
}
CASE_EXEMPT = {"Dockerfile", "README.md", "examples/hola/Gemfile", "examples/hola/Gemfile.lock", "examples/hola/Rakefile"}
WORKFLOW = ".github/workflows/ruby-toolchain.yml"
OTHER_TOOLCHAINS = r"toolchains/(java|mojo|go|cpp|rust|node|dotnet|swift|kotlin|scala)\b"
# Acciones de GitHub que corren nativamente en Node 24 (verificado en su action.yml).
MIN_ACTION_MAJOR = {"actions/checkout": 5, "actions/setup-python": 6, "actions/upload-artifact": 6}
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen Ruby no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen Ruby no debe copiar scripts/ai/",
    OTHER_TOOLCHAINS: "la imagen Ruby no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen Ruby no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen Ruby no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"apt-get install[^\n]*\b(ruby[0-9.]*(-[a-z]+)?|bundler|rubygems|python3?)\b": "sin Ruby/gemas de apt ni Python de sistema",
    r"\b(rvm|rbenv|ruby-install|asdf)\b|(git clone|install)[^\n]*ruby-build": "sin gestores de versiones (rvm/rbenv/asdf)",
    r"gem install|bundle install(?! --local)|BUNDLE_FROZEN=false": "sin instalar gemas desde la red en la imagen",
    r"--allow-unauthenticated|--insecure\b|\s-k\s|ssl_verify_mode": "no se desactiva TLS",
    r"/snapshot|ruby-head|preview|/latest": "sin versiones mutables o de prueba",
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


def sha512_file(path: Path) -> str:
    h = hashlib.sha512()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_gemfile_lock(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line and not line.startswith(" "):
            current = line.strip()
            sections[current] = []
        elif current and line.strip():
            sections[current].append(line)
    return sections


def validate(repo_root: Path, tarballs: list[Path]) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "ruby"
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

    # --- nombres exactos y sin archivos sueltos (vendor/ y .bundle/ no se suben)
    present = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    present = {p for p in present if "__pycache__" not in p}
    missing = EXPECTED_FILES - present
    extra = present - EXPECTED_FILES
    need(not missing, "archivos esperados con nombre exacto" + (f"; faltan: {sorted(missing)}" if missing else ""))
    need(not extra, "sin archivos extra ni renombrados en toolchains/ruby" + (f"; sobran: {sorted(extra)[:10]}" if extra else ""))
    for rel in sorted(present - CASE_EXEMPT):
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "ruby", "toolchain == ruby")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("signature_required", False),
                      ("mutable_versions_allowed", False), ("lockfile_required", True),
                      ("lockfile_checksums_required", True), ("package_downloads_by_default", False),
                      ("system_python_allowed", False), ("network_tools_allowed", False),
                      ("persistent_installation_authorized", False), ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    need("GPG" in str(policy.get("signature_note", "")), "policy.signature_note explica por que no hay firma GPG")
    isolated = set(policy.get("isolated_from") or [])
    need({"ai/", "scripts/ai/", ".devcontainer/", "kestra/flows/", "toolchains/kotlin/", "toolchains/scala/", "toolchains/node/"} <= isolated,
         "policy.isolated_from incluye ai/, .devcontainer/, kestra/flows/ y los otros toolchains")
    need(manifest.get("dockerfile") == "toolchains/ruby/Dockerfile", "dockerfile apunta a toolchains/ruby/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    need(manifest.get("architectures") == ["amd64", "arm64"], "arquitecturas amd64 + arm64")
    comps = manifest.get("components")
    need(isinstance(comps, list) and [c.get("id") for c in comps] == ["ruby", "rubygems", "bundler", "minitest", "rake"],
         "componentes exactos: ruby + rubygems + bundler + minitest + rake")
    ruby, rubygems, bundler, minitest, rake = comps
    for comp in comps:
        lic = comp.get("license") or {}
        need(lic.get("value") == REQUIRED_LICENSES[comp["id"]] and lic.get("status") == "DECLARED",
             f"licencia declarada de {comp['id']}: {REQUIRED_LICENSES[comp['id']]}")
        parse_version(str(comp.get("version", "")))
        checks.append(f"version exacta de {comp['id']}: {comp.get('version')}")

    args = parse_dockerfile_args(dockerfile)
    version = str(ruby.get("version"))
    major, minor, _ = parse_version(version)
    series = f"{major}.{minor}"
    rfile = f"ruby-{version}.tar.xz"
    url = f"{RUBY_URL_BASE}/{series}/{rfile}"
    need(args.get("RUBY_VERSION") == version, f"Dockerfile RUBY_VERSION == {version}")
    need(args.get("RUBY_SERIES") == series, f"Dockerfile RUBY_SERIES == {series}")
    need(args.get("RUBY_URL_BASE") == RUBY_URL_BASE, "Dockerfile RUBY_URL_BASE oficial (cache.ruby-lang.org)")
    need(ruby.get("source") == url, f"source == {url}")
    need(ruby.get("checksum_source") == f"{RUBY_URL_BASE}/index.txt", "checksum_source == index.txt oficial")
    need(str(ruby.get("announcement", "")).startswith("https://www.ruby-lang.org/en/news/"), "anuncio oficial en ruby-lang.org")
    need(SHA256_RE.fullmatch(str(ruby.get("sha256", ""))) is not None, "ruby sha256 con formato valido")
    need(SHA512_RE.fullmatch(str(ruby.get("sha512", ""))) is not None, "ruby sha512 con formato valido")
    need(args.get("RUBY_SHA256") == ruby.get("sha256"), "Dockerfile RUBY_SHA256 == components.json")
    need(args.get("RUBY_SHA512") == ruby.get("sha512"), "Dockerfile RUBY_SHA512 == components.json")
    need('sha256sum -c -' in dockerfile and 'sha512sum -c -' in dockerfile, "el Dockerfile verifica SHA-256 y SHA-512")
    need(f'print RUBY_VERSION\')" = "$RUBY_VERSION"' in dockerfile, "el Dockerfile comprueba la version compilada")
    need("--disable-install-doc" in dockerfile, "sin documentacion instalada")
    need(rubygems.get("version") == bundler.get("version"), "RubyGems y Bundler de la misma entrega")
    need(rubygems.get("environment") == {k: REQUIRED_ENV[k] for k in ("GEM_HOME", "GEM_PATH")}, "entorno de RubyGems exacto")
    need(bundler.get("environment") == {k: REQUIRED_ENV[k] for k in REQUIRED_ENV if k.startswith("BUNDLE_")},
         "entorno de Bundler exacto")
    need(REQUIRED_ENV["GEM_PATH"].endswith(f"/opt/ruby/lib/ruby/gems/{major}.{minor}.0"), "GEM_PATH incluye las gemas de Ruby")
    for comp in (minitest, rake):
        need(SHA256_RE.fullmatch(str(comp.get("gem_sha256", ""))) is not None, f"{comp['id']}: gem_sha256 valido")
        need("inside the Ruby" in str(comp.get("distribution", "")), f"{comp['id']}: viene dentro de Ruby (sin red)")

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
    need(not ({"curl", "wget", "gpg", "gcc", "make", "python3", "python3-minimal"} & set(installed)),
         "la imagen final no instala curl, compiladores ni Python")
    need(re.search(r"^COPY --from=ruby-build /opt/ruby /opt/ruby$", final, flags=re.M) is not None
         and "/usr/src/ruby" not in final, "la imagen final solo copia /opt/ruby compilado (sin fuentes)")
    env = parse_env(final)
    for key, want in REQUIRED_ENV.items():
        need(env.get(key) == want, f"ENV {key}={want}")
    need(env.get("PATH", "").startswith("/opt/ruby/bin:"), "PATH empieza por /opt/ruby/bin")
    need(re.search(r"^USER\s+rubyuser\s*$", final, flags=re.M) is not None, "usuario no root: rubyuser")
    need(final.rstrip().splitlines()[-1].strip() == 'CMD ["bash"]', "CMD final bash")
    need("chmod -R a=rX /opt/gordus-ruby" in final, "codigo de /opt/gordus-ruby de solo lectura")
    need("chown -R root:root /opt/ruby" in dockerfile and "chmod -R go-w /opt/ruby" in dockerfile, "/opt/ruby de root y sin escritura")
    for d in re.findall(r"install -d -o rubyuser -g rubyuser ([^\n&]+)", re.sub(r"\\\n\s*", " ", final)):
        for p in d.split():
            need(p == "/workspace" or p.startswith(STATE_ROOT.rstrip("/")), f"directorio escribible permitido: {p}")

    # --- ejemplo: Gemfile y Gemfile.lock congelado con checksums
    hola = base / "examples" / "hola"
    gemfile = (hola / "Gemfile").read_text(encoding="utf-8")
    need(re.findall(r'^source "([^"]+)"', gemfile, flags=re.M) == ["https://rubygems.org"], "Gemfile: una sola fuente https://rubygems.org")
    need(f'ruby "{version}"' in gemfile, f"Gemfile exige ruby {version}")
    gems = dict(re.findall(r'^gem "([a-z0-9_-]+)", "([0-9.]+)"\s*$', gemfile, flags=re.M))
    need(gems == {"minitest": minitest["version"], "rake": rake["version"]}, "Gemfile: gemas con version exacta (minitest, rake)")
    need(re.search(r"\b(git|github|path):", gemfile) is None, "Gemfile sin gemas de git/github/path")
    lock = parse_gemfile_lock((hola / "Gemfile.lock").read_text(encoding="utf-8"))
    need(lock.get("GEM", [""])[0].strip() == "remote: https://rubygems.org/", "Gemfile.lock: remote https://rubygems.org/")
    need([l.strip() for l in lock.get("PLATFORMS", [])] == ["ruby"], "Gemfile.lock: plataforma ruby (amd64 y arm64)")
    need([l.strip() for l in lock.get("DEPENDENCIES", [])] == [f"minitest (= {minitest['version']})", f"rake (= {rake['version']})"],
         "Gemfile.lock sincronizado con Gemfile")
    need([l.strip() for l in lock.get("RUBY VERSION", [])] == [f"ruby {version}"], "Gemfile.lock: RUBY VERSION")
    need([l.strip() for l in lock.get("BUNDLED WITH", [])] == [bundler["version"]], "Gemfile.lock: BUNDLED WITH == Bundler fijado")
    sums = {}
    for l in lock.get("CHECKSUMS", []):
        m = re.fullmatch(r"\s+(\S+ \([0-9.]+\)) (sha256=[0-9a-f]{64})", l)
        need(m is not None, f"Gemfile.lock: checksum sha256 en '{l.strip()}'")
        sums[m.group(1)] = m.group(2)
    need(sums == manifest.get("lockfile_checksums"), "Gemfile.lock CHECKSUMS == components.json")
    need(sums.get(f"minitest ({minitest['version']})") == f"sha256={minitest['gem_sha256']}", "checksum de minitest == gem_sha256")
    need(sums.get(f"rake ({rake['version']})") == f"sha256={rake['gem_sha256']}", "checksum de rake == gem_sha256")
    specs = [l.strip() for l in lock.get("GEM", [])[2:] if l.startswith("    ") and not l.startswith("      ")]
    need(sorted(specs) == sorted(sums), "cada gema del lock tiene su checksum")
    test_rb = (hola / "test/saludo_test.rb").read_text(encoding="utf-8")
    need('require "minitest/autorun"' in test_rb and "< Minitest::Test" in test_rb, "la prueba usa Minitest")
    for f in ("hola.rb", "lib/saludo.rb", "test/saludo_test.rb", "Gemfile", "Rakefile"):
        need((hola / f).read_text(encoding="utf-8").startswith("# frozen_string_literal: true"), f"{f}: frozen_string_literal")

    # --- prueba de humo
    smoke = (base / "tests/test_ruby_toolchain.sh").read_text(encoding="utf-8")
    for var, comp in (("RUBY", ruby), ("RUBYGEMS", rubygems), ("BUNDLER", bundler), ("MINITEST", minitest), ("RAKE", rake)):
        need(f"EXPECTED_{var}_VERSION:-{comp['version']}" in smoke, f"test_ruby_toolchain.sh espera {comp['id']} {comp['version']}")

    # --- flujo Kestra
    flow = (base / "kestra/ruby_toolchain_smoke.yaml").read_text(encoding="utf-8")
    need(re.search(r"^id: ruby_toolchain_smoke$", flow, flags=re.M) is not None, "Kestra: id ruby_toolchain_smoke")
    need(re.search(r"^namespace: gordus_hub\.toolchains$", flow, flags=re.M) is not None, "Kestra: namespace gordus_hub.toolchains")
    need(f"inputs.ruby_version == 'ruby {version}'" in flow and f"bundler {bundler['version']}" in flow
         and f"minitest {minitest['version']}" in flow and f"gem {rubygems['version']}" in flow, "Kestra exige las versiones fijadas")
    need("io.kestra.plugin.core.execution.Fail" in flow, "Kestra falla cerrado")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/ruby/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(OTHER_TOOLCHAINS + r"|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
    need("contents: read" in wf, "workflow con permisos de solo lectura")
    need("kestra/kestra:v1.3.40-slim" in wf and ":latest" not in wf, "workflow usa Kestra v1.3.40-slim fijado")
    uses = re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@v(\d+)", wf)
    need(bool(uses), "workflow usa acciones versionadas")
    for name, amajor in uses:
        need(name in MIN_ACTION_MAJOR and int(amajor) >= MIN_ACTION_MAJOR[name], f"accion {name}@v{amajor} nativa de Node 24")

    verified = []
    for tb in tarballs:
        if not tb.is_file():
            raise Gate(EXIT_BAD_INPUT, f"no existe el tarball {tb}")
        if tb.name != rfile:
            raise Gate(EXIT_BLOCKED, f"tarball no aprobado: {tb.name}")
        got256, got512 = sha256_file(tb), sha512_file(tb)
        if got256 != ruby["sha256"] or got512 != ruby["sha512"]:
            raise Gate(EXIT_FAILED, f"SHA-256/SHA-512 no coinciden para {tb.name}")
        verified.append({"file": tb.name, "sha256": got256, "sha512": got512})
        checks.append(f"tarball local verificado: {tb.name}")

    return {"checks": checks, "ruby_version": version, "rubygems_version": rubygems["version"],
            "bundler_version": bundler["version"], "minitest_version": minitest["version"],
            "rake_version": rake["version"], "tarballs_verified": verified}

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    ap.add_argument("--verify-tarball", action="append", default=[],
                    help="tarball local de Ruby cuyo SHA-256 y SHA-512 se verifican (repetible)")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/ruby/scripts/validate_ruby_toolchain.py",
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (Ruby {report['ruby_version']}, RubyGems {report['rubygems_version']}, "
              f"Bundler {report['bundler_version']}, Minitest {report['minitest_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
