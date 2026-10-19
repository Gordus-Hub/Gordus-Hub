# Gordus-Hub - C++23 toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/ ni .devcontainer/.
# Fuente: paquetes oficiales de Debian 13 (trixie), firmados por Debian (apt verifica la firma
# del archivo Release y el SHA-256 de cada .deb). Cada paquete principal se fija con pkg=version.
# Cualquier cambio de version debe actualizar tambien toolchains/cpp/components.json;
# toolchains/cpp/scripts/validate_cpp_toolchain.py falla cerrado si no coinciden.

# Etapa 1: clang-tools-19 y clang-format-19 dependen de python3 (por scripts auxiliares).
# Se instalan aqui, con la misma version fijada, y solo se copian los dos binarios
# compilados (clang-scan-deps, que CMake necesita para "import std", y clang-format).
FROM debian:13-slim AS llvm-extras

ARG DEBIAN_FRONTEND=noninteractive
ARG LLVM_VERSION=1:19.1.7-3+b1
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       "clang-tools-19=$LLVM_VERSION" "clang-format-19=$LLVM_VERSION" \
    && test "$(dpkg-query -W -f '${Version}' clang-tools-19)" = "$LLVM_VERSION" \
    && install -d /out \
    && cp /usr/lib/llvm-19/bin/clang-scan-deps /usr/lib/llvm-19/bin/clang-format /out/ \
    && sha256sum /out/* > /out/SHA256SUMS

# Etapa 2: imagen final (sin Python).
FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG GCC_VERSION=14.2.0-19
ARG LLVM_VERSION=1:19.1.7-3+b1
ARG BINUTILS_VERSION=2.44-3
ARG CMAKE_VERSION=3.31.6-2
ARG NINJA_VERSION_AMD64=1.12.1-1
ARG NINJA_VERSION_ARM64=1.12.1-1+b1
ARG MAKE_VERSION=4.4.1-2
ARG PKGCONF_VERSION=1.8.1-4
ARG LIBC_DEV_VERSION=2.41-12+deb13u4

# Compiladores: g++-14 (libstdc++) y clang++-19 (libstdc++ o libc++).
# Enlazadores: GNU ld (binutils, por defecto) y LLD 19 (para clang/libc++).
# No se instalan gdb ni clang-tidy: ambos arrastran Python (libpython / python3).
RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) ninja="$NINJA_VERSION_AMD64" ;; \
      arm64) ninja="$NINJA_VERSION_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      "g++-14=$GCC_VERSION" "gcc-14=$GCC_VERSION" "cpp-14=$GCC_VERSION" "libstdc++-14-dev=$GCC_VERSION" \
      "clang-19=$LLVM_VERSION" \
      "lld-19=$LLVM_VERSION" "libc++-19-dev=$LLVM_VERSION" "libc++abi-19-dev=$LLVM_VERSION" \
      "binutils=$BINUTILS_VERSION" \
      "cmake=$CMAKE_VERSION" "ninja-build=$ninja" "make=$MAKE_VERSION" "pkg-config=$PKGCONF_VERSION" \
      "libc6-dev=$LIBC_DEV_VERSION"; \
    rm -rf /var/lib/apt/lists/*; \
    if command -v python3 || command -v python || command -v curl || command -v wget; then \
      echo "BLOCKED: la imagen final no debe traer Python ni curl/wget" >&2; exit 3; fi; \
    test "$(dpkg-query -W -f '${Version}' g++-14)" = "$GCC_VERSION"; \
    test "$(dpkg-query -W -f '${Version}' clang-19)" = "$LLVM_VERSION"; \
    test "$(dpkg-query -W -f '${Version}' cmake)" = "$CMAKE_VERSION"

COPY --from=llvm-extras /out/clang-scan-deps /out/clang-format /usr/lib/llvm-19/bin/
COPY --from=llvm-extras /out/SHA256SUMS /usr/share/gordus-cpp/llvm-extras.SHA256SUMS
RUN cd /usr/lib/llvm-19/bin \
    && sed 's#/out/##' /usr/share/gordus-cpp/llvm-extras.SHA256SUMS | sha256sum -c - \
    && ./clang-scan-deps --version >/dev/null && ./clang-format --version >/dev/null

# Nombres cortos: g++/gcc -> 14, clang/clang++/ld.lld -> 19 (via /usr/lib/llvm-19/bin en PATH).
RUN ln -s /usr/bin/g++-14 /usr/local/bin/g++ \
    && ln -s /usr/bin/gcc-14 /usr/local/bin/gcc \
    && ln -s /usr/bin/g++-14 /usr/local/bin/c++ \
    && ln -s /usr/bin/gcc-14 /usr/local/bin/cc

ENV PATH=/usr/local/bin:/usr/lib/llvm-19/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    CC=gcc \
    CXX=g++ \
    CMAKE_GENERATOR=Ninja \
    LANG=C.UTF-8 \
    GORDUS_CPP_WORK=/workspace

RUN groupadd --system cppuser \
    && useradd --system --gid cppuser --home-dir /home/cppuser --create-home cppuser \
    && install -d -o cppuser -g cppuser /workspace

WORKDIR /opt/gordus-cpp
COPY toolchains/cpp/components.json /opt/gordus-cpp/components.json
COPY toolchains/cpp/examples /opt/gordus-cpp/examples
COPY toolchains/cpp/tests /opt/gordus-cpp/tests
RUN chown -R root:root /opt/gordus-cpp \
    && chmod -R a=rX /opt/gordus-cpp

USER cppuser
RUN g++ --version >/dev/null && clang++ --version >/dev/null && cmake --version >/dev/null
WORKDIR /workspace
CMD ["bash"]
