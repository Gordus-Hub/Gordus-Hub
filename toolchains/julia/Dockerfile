# Gordus-Hub - Julia toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/,
# toolchains/cpp/, toolchains/rust/, toolchains/node/, toolchains/dotnet/, toolchains/swift/,
# toolchains/kotlin/, toolchains/scala/, toolchains/php/, toolchains/ruby/ ni .devcontainer/.
# SEGURIDAD: Julia 1.13.2 (15/10/2026) actualiza OpenSSL_jll 3.5.8, LibCURL_jll 8.22.0,
# LibGit2_jll 1.9.7, nghttp2_jll 1.70.0 y Zlib_jll 1.3.2 (cierra varios avisos JLSEC).
# Nunca bajar de 1.13.2: el validador bloquea cualquier version anterior.
# Fuente oficial: binarios de julialang.org (julialang-s3.julialang.org/bin), amd64 y arm64.
# Verificacion: 1) firma GPG (.asc) del tarball con la "Julia Release Signing Key",
# guardada en toolchains/julia/keys/ (sacada de julialang.org/assets/juliareleases.asc) y fijada
# por huella, 2) SHA-256 publicado en versions.json fijado aqui por arquitectura.
# Las claves van en el repo para que el CI no dependa de bajarlas.
# Cualquier cambio de version debe actualizar tambien toolchains/julia/components.json;
# toolchains/julia/scripts/validate_julia_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS julia-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG JULIA_VERSION=1.13.2
ARG JULIA_MINOR=1.13
ARG JULIA_URL_BASE=https://julialang-s3.julialang.org/bin/linux
ARG JULIA_SHA256_AMD64=2ecdfc9890ab0a565fdd92404c915ba2a04a933dbd5d292cc224d13819d17d07
ARG JULIA_SHA256_ARM64=b366ac62162d42b272e82436397487dec719f0830d059cdd8a3f7a1810647128
ARG JULIA_GPG_FINGERPRINT=64B779A570972FFF7BFC2B54EAD471E1A1F2C10A

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gpg gpgv \
    && rm -rf /var/lib/apt/lists/*

COPY toolchains/julia/keys/julia-release-signing-key.asc /tmp/keys/julia.asc

RUN set -eu; \
    case "${TARGETARCH:-amd64}" in \
      amd64) dir=x64; arch=x86_64; sha="$JULIA_SHA256_AMD64" ;; \
      arm64) dir=aarch64; arch=aarch64; sha="$JULIA_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no soportada: $TARGETARCH" >&2; exit 3 ;; \
    esac; \
    file="julia-$JULIA_VERSION-linux-$arch.tar.gz"; \
    url="$JULIA_URL_BASE/$dir/$JULIA_MINOR/$file"; \
    export GNUPGHOME=/tmp/gnupg; install -d -m 0700 "$GNUPGHOME"; cd /tmp; \
    fpr="$(gpg --batch --show-keys --with-colons /tmp/keys/julia.asc | awk -F: '$1 == "fpr" {print $10; exit}')"; \
    [ "$fpr" = "$JULIA_GPG_FINGERPRINT" ] \
      || { echo "BLOCKED: la clave guardada no es la Julia Release Signing Key fijada" >&2; exit 3; }; \
    gpg --batch --dearmor < /tmp/keys/julia.asc > julia-keyring.kbx; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o "$file" "$url"; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o "$file.asc" "$url.asc"; \
    gpgv --status-fd 1 --keyring ./julia-keyring.kbx "$file.asc" "$file" > gpgv.out; \
    grep -q "^\[GNUPG:\] VALIDSIG .* $JULIA_GPG_FINGERPRINT\$" gpgv.out \
      || { echo "BLOCKED: la firma de Julia no es de la clave fijada" >&2; exit 3; }; \
    echo "$sha  $file" | sha256sum -c -; \
    install -d /opt/julia; \
    tar -xzf "$file" -C /opt/julia --strip-components=1 --no-same-owner; \
    rm -rf /tmp/gnupg /tmp/keys julia-keyring.kbx gpgv.out "$file" "$file.asc"; \
    test "$(/opt/julia/bin/julia --startup-file=no -e 'print(VERSION)')" = "$JULIA_VERSION"; \
    /opt/julia/bin/julia --startup-file=no -e 'exit(VERSION >= v"1.13.2" ? 0 : 3)' \
      || { echo "BLOCKED: Julia anterior a 1.13.2 (sin las actualizaciones de seguridad)" >&2; exit 3; }

FROM debian:13-slim

# JULIA_PKG_OFFLINE=true : Pkg nunca usa la red salvo que se pida (-e JULIA_PKG_OFFLINE=false).
# JULIA_PKG_SERVER vacio : no se contacta pkg.julialang.org (sin telemetria de Pkg).
ENV PATH=/opt/julia/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    JULIA_HOME=/opt/julia \
    JULIA_DEPOT_PATH=/var/lib/gordus-julia/depot: \
    JULIA_PKG_OFFLINE=true \
    JULIA_PKG_SERVER= \
    JULIA_PKG_PRECOMPILE_AUTO=0 \
    JULIA_HISTORY=/var/lib/gordus-julia/repl_history.jl \
    LANG=C.UTF-8 \
    GORDUS_JULIA_WORK=/workspace

# Julia trae sus propias bibliotecas; solo hacen falta los certificados, fijados por version.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates=20250419+deb13u1 \
    && rm -rf /var/lib/apt/lists/* \
    && if command -v python3 || command -v python || command -v curl || command -v wget; then \
         echo "BLOCKED: la imagen final no debe traer Python ni curl/wget" >&2; exit 3; fi

COPY --from=julia-fetch /opt/julia /opt/julia

RUN chown -R root:root /opt/julia \
    && chmod -R go-w /opt/julia \
    && groupadd --system juliauser \
    && useradd --system --gid juliauser --home-dir /home/juliauser --create-home juliauser \
    && install -d -o juliauser -g juliauser /workspace /var/lib/gordus-julia /var/lib/gordus-julia/depot

WORKDIR /opt/gordus-julia
COPY toolchains/julia/components.json /opt/gordus-julia/components.json
COPY toolchains/julia/examples /opt/gordus-julia/examples
COPY toolchains/julia/tests /opt/gordus-julia/tests
RUN chown -R root:root /opt/gordus-julia \
    && chmod -R a=rX /opt/gordus-julia

USER juliauser
RUN julia --version && julia --startup-file=no -e 'exit(VERSION >= v"1.13.2" ? 0 : 3)'
WORKDIR /workspace
CMD ["bash"]
