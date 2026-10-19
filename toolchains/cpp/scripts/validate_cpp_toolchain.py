#!/usr/bin/env python3
"""Validador fail-closed del toolchain C++23 de Gordus-Hub.

Solo usa la biblioteca estandar de Python: no importa nada de ai/, scripts/ai/ ni de
los otros toolchains. Comprueba que toolchains/cpp/components.json y
toolchains/cpp/Dockerfile fijan exactamente las mismas versiones de paquetes Debian
(pkg=version), que la imagen final no trae Python ni curl, corre como usuario no-root
con codigo de solo lectura, que el ejemplo pide C++23, los nombres exactos de archivos
y las reglas de aislamiento.

Codigos de salida (convencion del repo):
  0  PASS        todo coincide
  2  BAD_INPUT   falta un archivo, JSON invalido o argumentos invalidos
  3  BLOCKED     una regla de politica o un pin no coincide (falla cerrado)
  4  FAILED      error inesperado
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK, EXIT_BAD_INPUT, EXIT_BLOCKED, EXIT_FAILED = 0, 2, 3, 4

DEB_VERSION_RE = re.compile(r"^(\d+:)?[0-9][A-Za-z0-9.+~-]*$")
# paquete -> ARG del Dockerfile que fija su version
PACKAGE_ARGS = {
    "g++-14": "GCC_VERSION", "gcc-14": "GCC_VERSION", "cpp-14": "GCC_VERSION",
    "libstdc++-14-dev": "GCC_VERSION",
    "clang-19": "LLVM_VERSION", "lld-19": "LLVM_VERSION",
    "libc++-19-dev": "LLVM_VERSION", "libc++abi-19-dev": "LLVM_VERSION",
    "clang-tools-19": "LLVM_VERSION", "clang-format-19": "LLVM_VERSION",
    "binutils": "BINUTILS_VERSION", "cmake": "CMAKE_VERSION", "make": "MAKE_VERSION",
    "pkg-config": "PKGCONF_VERSION", "libc6-dev": "LIBC_DEV_VERSION",
}
NINJA_ARGS = {"amd64": "NINJA_VERSION_AMD64", "arm64": "NINJA_VERSION_ARM64"}
# Paquetes que dependen de python3: solo permitidos en la etapa auxiliar llvm-extras.
EXTRAS_ONLY = {"clang-tools-19", "clang-format-19"}
REQUIRED_COMPONENTS = {"gcc", "llvm", "lld", "binutils", "libc6-dev", "cmake", "ninja", "make", "pkg-config"}
REQUIRED_LICENSES = {
    "gcc": "GPL-3.0-or-later WITH GCC-exception-3.1",
    "llvm": "Apache-2.0 WITH LLVM-exception",
    "lld": "Apache-2.0 WITH LLVM-exception",
}
# Nombres exactos (minusculas salvo Dockerfile/README.md/CMakeLists.txt): Linux distingue mayusculas.
EXPECTED_FILES = {
    "Dockerfile", "README.md", "components.json",
    "examples/hola/CMakeLists.txt", "examples/hola/main.cpp",
    "tests/test_cpp_toolchain.sh", "scripts/validate_cpp_toolchain.py",
    "kestra/cpp_toolchain_smoke.yaml",
}
CASE_EXEMPT = {"Dockerfile", "README.md", "examples/hola/CMakeLists.txt"}
WORKFLOW = ".github/workflows/cpp-toolchain.yml"
FORBIDDEN_DOCKERFILE_PATTERNS = {
    r"\bCOPY\s+ai\b": "la imagen C++ no debe copiar ai/",
    r"\bCOPY\s+scripts/ai\b": "la imagen C++ no debe copiar scripts/ai/",
    r"toolchains/(java|mojo|go)\b": "la imagen C++ no debe tocar otros toolchains",
    r"\.devcontainer": "la imagen C++ no debe referenciar .devcontainer/",
    r"kestra/flows": "la imagen C++ no debe referenciar kestra/flows/",
    r"\|\s*(ba)?sh\b": "prohibido 'curl | sh'",
    r":latest\b": "no se permiten etiquetas mutables ':latest'",
    r"--allow-unauthenticated|AllowInsecureRepositories|trusted=yes|--force-yes": "apt no desactiva la verificacion de firmas",
    r"apt\.llvm\.org": "sin repositorios externos (apt.llvm.org) no fijados",
}


class Gate(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


def parse_dockerfile_args(text: str) -> dict[str, str]:
    args: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*ARG\s+([A-Za-z0-9_]+)=(\S+)\s*$", line)
        if m:
            if m.group(1) in args and args[m.group(1)] != m.group(2):
                raise Gate(EXIT_BLOCKED, f"ARG {m.group(1)} definido dos veces con valores distintos")
            args[m.group(1)] = m.group(2)
    return args


def split_stages(text: str) -> list[str]:
    parts = re.split(r"^(?=FROM\s)", text, flags=re.M)
    return [p for p in parts if p.startswith("FROM ")]


def strip_comments(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


def apt_packages(stage: str) -> list[str]:
    """Tokens de paquetes en cada 'apt-get install' de una etapa (con continuaciones)."""
    joined = re.sub(r"\\\n", " ", strip_comments(stage))
    pkgs: list[str] = []
    for m in re.finditer(r"apt-get install([^;&|]*)", joined):
        for tok in m.group(1).split():
            tok = tok.strip('"\'')
            if tok and not tok.startswith("-"):
                pkgs.append(tok)
    return pkgs


def parse_env(stage: str) -> dict[str, str]:
    env: dict[str, str] = {}
    joined = re.sub(r"\\\n", " ", stage)
    for line in joined.splitlines():
        if line.startswith("ENV "):
            for key, value in re.findall(r"([A-Z_][A-Z0-9_]*)=(\S+)", line[4:]):
                env[key] = value
    return env


def validate(repo_root: Path) -> dict:
    checks: list[str] = []
    base = repo_root / "toolchains" / "cpp"
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
    need(not extra, "sin archivos extra ni renombrados en toolchains/cpp" + (f"; sobran: {sorted(extra)}" if extra else ""))
    for rel in sorted(present - CASE_EXEMPT):
        need(rel == rel.lower(), f"nombre en minusculas: {rel}")

    # --- registro
    need(manifest.get("schema_version") == 1, "schema_version == 1")
    need(manifest.get("toolchain") == "cpp", "toolchain == cpp")
    policy = manifest.get("policy") or {}
    for key, want in (("fail_closed", True), ("checksum_required", True), ("mutable_versions_allowed", False),
                      ("system_python_allowed", False), ("network_tools_allowed", False),
                      ("certification", "NOT_GRANTED")):
        need(policy.get(key) == want, f"policy.{key} == {json.dumps(want)}")
    need(manifest.get("dockerfile") == "toolchains/cpp/Dockerfile", "dockerfile apunta a toolchains/cpp/Dockerfile")
    need(manifest.get("base_image") == "debian:13-slim", "base_image == debian:13-slim")
    need("202302" in str(manifest.get("language_standard", "")), "language_standard declara C++23 (202302L)")
    comps = manifest.get("components")
    need(isinstance(comps, list), "components es una lista")
    by_id = {c.get("id"): c for c in comps}
    need(len(by_id) == len(comps), "ids de componentes unicos")
    need(set(by_id) == REQUIRED_COMPONENTS, f"componentes exactos: {sorted(REQUIRED_COMPONENTS)}")
    for cid, lic in REQUIRED_LICENSES.items():
        need((by_id[cid].get("license") or {}).get("value") == lic, f"licencia {cid}: {lic}")
    for cid, comp in by_id.items():
        need(bool((comp.get("license") or {}).get("value")), f"licencia declarada: {cid}")
    smoke = manifest.get("smoke_test", "")
    need(bool(smoke) and (repo_root / smoke).is_file(), f"smoke_test existe: {smoke}")
    feats = {k: v for k, v in (manifest.get("cxx23_features") or {}).items() if isinstance(v, dict)}
    need(len(feats) >= 3 and all("import_std" in v and "print" in v for v in feats.values()),
         "matriz de funciones C++23 declarada (print, import_std, ...)")

    # --- pines: components.json == ARG del Dockerfile
    args = parse_dockerfile_args(dockerfile)
    declared: dict[str, str] = {}
    for comp in comps:
        for pkg, ver in (comp.get("packages") or {}).items():
            declared[pkg] = ver
    need(set(declared) == set(PACKAGE_ARGS), "paquetes declarados == paquetes aprobados")
    for pkg, arg in sorted(PACKAGE_ARGS.items()):
        ver = declared[pkg]
        need(DEB_VERSION_RE.fullmatch(ver) is not None, f"{pkg}: version Debian exacta ({ver})")
        need(args.get(arg) == ver, f"{pkg}: Dockerfile {arg} == components.json")
    ninja = (by_id["ninja"].get("packages_by_arch") or {})
    need(set(ninja) == set(NINJA_ARGS), "ninja-build fijado para amd64 + arm64")
    for arch, arg in NINJA_ARGS.items():
        ver = (ninja[arch] or {}).get("ninja-build", "")
        need(DEB_VERSION_RE.fullmatch(ver) is not None and args.get(arg) == ver, f"ninja-build {arch}: {arg} == components.json")

    # --- etapas e instalacion
    stages = split_stages(dockerfile)
    need(len(stages) == 2, "dos etapas: llvm-extras + final")
    need(all(s.split()[1] == "debian:13-slim" for s in stages), "todas las etapas usan debian:13-slim")
    extras, final = stages
    need(extras.split()[2:4] == ["AS", "llvm-extras"], "primera etapa se llama llvm-extras")
    ok_tokens = {f"{pkg}=${arg}" for pkg, arg in PACKAGE_ARGS.items()} | {"ninja-build=$ninja"}
    for name, stage in (("llvm-extras", extras), ("final", final)):
        pkgs = apt_packages(stage)
        need(bool(pkgs), f"{name}: instala paquetes con apt")
        for tok in pkgs:
            need(tok in ok_tokens, f"{name}: paquete fijado pkg=version: {tok}")
    final_pkgs = {t.split("=")[0] for t in apt_packages(final)}
    extras_pkgs = {t.split("=")[0] for t in apt_packages(extras)}
    need(extras_pkgs == EXTRAS_ONLY, "llvm-extras instala solo clang-tools-19 + clang-format-19")
    need(not (final_pkgs & EXTRAS_ONLY), "la imagen final no instala paquetes que dependen de python3")
    need({"g++-14", "clang-19", "lld-19", "libc++-19-dev", "cmake", "ninja-build", "make", "binutils"} <= final_pkgs,
         "imagen final: compiladores, enlazadores y herramientas de build")
    need("--no-install-recommends" in final, "apt sin paquetes recomendados")
    final_instr = strip_comments(final)
    need(re.search(r"\b(python3?|curl|wget)(=|\s|\")", " ".join(apt_packages(final))) is None, "sin python/curl/wget en apt")
    need("command -v python3" in final_instr and "command -v curl" in final_instr, "build falla si aparece Python o curl")
    copies = re.findall(r"^COPY --from=(\S+) (.+)$", final_instr, re.M)
    need(len(copies) == 2 and all(c[0] == "llvm-extras" for c in copies), "solo se copia de llvm-extras")
    need(any("clang-scan-deps" in c[1] and "clang-format" in c[1] for c in copies), "se copian solo clang-scan-deps y clang-format")
    need("sha256sum -c" in final_instr, "imagen final verifica el SHA-256 de los binarios copiados")
    need("rm -rf /var/lib/apt/lists/*" in final_instr, "listas de apt borradas")
    for pkg_arg in ("GCC_VERSION", "LLVM_VERSION", "CMAKE_VERSION"):
        need(f"= \"${pkg_arg}\"" in final_instr, f"build comprueba con dpkg-query la version instalada ({pkg_arg})")
    fenv = parse_env(final)
    need(fenv.get("CMAKE_GENERATOR") == "Ninja", "ENV CMAKE_GENERATOR=Ninja")
    need("/usr/lib/llvm-19/bin" in fenv.get("PATH", ""), "PATH incluye /usr/lib/llvm-19/bin")
    need(re.search(r"^USER cppuser\s*$", final, re.M) is not None, "imagen corre como usuario no-root 'cppuser'")
    need("chmod -R a=rX /opt/gordus-cpp" in final, "codigo de solo lectura en /opt/gordus-cpp")
    for pattern, reason in FORBIDDEN_DOCKERFILE_PATTERNS.items():
        need(re.search(pattern, strip_comments(dockerfile)) is None, f"aislamiento: {reason}")

    # --- ejemplo C++23
    cml = (base / "examples/hola/CMakeLists.txt").read_text(encoding="utf-8")
    need(re.search(r"set\(CMAKE_CXX_STANDARD 23\)", cml) is not None, "CMakeLists pide C++23")
    need(re.search(r"set\(CMAKE_CXX_STANDARD_REQUIRED ON\)", cml) is not None, "CMakeLists exige el estandar")
    need(re.search(r"FetchContent|ExternalProject|file\(DOWNLOAD", cml) is None, "CMakeLists sin descargas")
    cpp = (base / "examples/hola/main.cpp").read_text(encoding="utf-8")
    for header in ("<print>", "<expected>", "<ranges>"):
        need(f"#include {header}" in cpp, f"main.cpp usa {header}")

    # --- workflow propio con filtro de rutas
    wf_path = repo_root / WORKFLOW
    need(wf_path.is_file(), f"existe {WORKFLOW}")
    wf = wf_path.read_text(encoding="utf-8")
    need(wf.count('"toolchains/cpp/**"') >= 2 and wf.count(f'"{WORKFLOW}"') >= 2, "workflow con filtro de rutas propio")
    need(re.search(r"toolchains/(java|mojo|go)\b|\bai/|\.devcontainer", wf) is None, "workflow no toca otros toolchains")
    need("contents: read" in wf, "workflow con permisos de solo lectura")

    return {"checks": checks, "gcc_version": declared["g++-14"], "llvm_version": declared["clang-19"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=".", help="raiz del repositorio")
    ap.add_argument("--report", help="ruta para escribir el informe JSON")
    try:
        ns = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK

    report = {
        "validator": "toolchains/cpp/scripts/validate_cpp_toolchain.py",
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "certification": "NOT_GRANTED",
    }
    try:
        detail = validate(Path(ns.repo_root).resolve())
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
        print(f"PASS: {len(report['checks'])} comprobaciones OK (g++ {report['gcc_version']}, clang {report['llvm_version']})")
    else:
        print(f"{report['result']}: {report['reason']}", file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
