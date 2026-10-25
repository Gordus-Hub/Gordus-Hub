# Gordus-Hub - Swift toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/,
# toolchains/cpp/, toolchains/rust/, toolchains/node/, toolchains/dotnet/ ni .devcontainer/.
# Fuente oficial fijada: tarball de swift.org para Debian 13 (Swift 6.4.1, 2026-10-12).
# swift.org no publica .sha256: el SHA-256 fijado aqui se calculo sobre el tarball cuya
# firma .sig fue verificada con la clave "Swift 6.x Release Signing Key", fijada por huella.
# Dentro del build se verifican LAS DOS cosas: 1) SHA-256 fijado y 2) firma GPG (gpgv).
# Cualquier cambio de version debe actualizar tambien toolchains/swift/components.json;
# toolchains/swift/scripts/validate_swift_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS swift-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG SWIFT_VERSION=6.4.1
ARG SWIFT_TAG=swift-6.4.1-RELEASE
ARG SWIFT_BRANCH=swift-6.4.1-release
ARG SWIFT_PLATFORM=debian13
ARG SWIFT_URL_BASE=https://download.swift.org
ARG SWIFT_GPG_KEY_URL=https://www.swift.org/keys/release-key-swift-6.x.asc
ARG SWIFT_GPG_FINGERPRINT=52BB7E3DE28A71BE22EC05FFEF80A866B47A981F
ARG SWIFT_SHA256_AMD64=3273c647a4e29231e1d0962a170f4ba14eca06675591dfe384e7c22b0e476a47
ARG SWIFT_SHA256_ARM64=bdddd98544ab2b3c569a405d6b377e50945d5b4621f5fa503114af342f55a5cd

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gpg gpgv \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) suffix=""; sha="$SWIFT_SHA256_AMD64" ;; \
      arm64) suffix="-aarch64"; sha="$SWIFT_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    file="$SWIFT_TAG-$SWIFT_PLATFORM$suffix.tar.gz"; \
    url="$SWIFT_URL_BASE/$SWIFT_BRANCH/$SWIFT_PLATFORM$suffix/$SWIFT_TAG/$file"; \
    export GNUPGHOME=/tmp/gnupg; install -d -m 0700 "$GNUPGHOME"; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 -o /tmp/swift-key.asc "$SWIFT_GPG_KEY_URL"; \
    test "$(gpg --batch --show-keys --with-colons /tmp/swift-key.asc | awk -F: '$1 == "fpr" {print $10; exit}')" = "$SWIFT_GPG_FINGERPRINT" \
      || { echo "BLOCKED: la clave GPG de Swift no tiene la huella esperada" >&2; exit 3; }; \
    gpg --batch --dearmor < /tmp/swift-key.asc > /tmp/swift-keyring.gpg; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 -o "/tmp/$file" "$url"; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 -o "/tmp/$file.sig" "$url.sig"; \
    echo "$sha  /tmp/$file" | sha256sum -c -; \
    gpgv --keyring /tmp/swift-keyring.gpg "/tmp/$file.sig" "/tmp/$file"; \
    install -d /opt/swift; \
    tar -xzf "/tmp/$file" -C /opt/swift --strip-components=1 --no-same-owner; \
    # Se conserva el layout oficial usr/ (SwiftPM ubica el toolchain como <raiz>/usr/bin).
    # Sin LLDB ni REPL: LLDB necesita libpython3 y la imagen no lleva Python (ver README).
    rm -rf /opt/swift/usr/bin/lldb /opt/swift/usr/bin/lldb-* /opt/swift/usr/bin/repl_swift \
           /opt/swift/usr/lib/liblldb.so* /opt/swift/usr/lib/python3* /opt/swift/usr/bin/swift-api-checker.py \
           /opt/swift/usr/share/doc /opt/swift/usr/local; \
    rm -rf "/tmp/$file" "/tmp/$file.sig" /tmp/gnupg /tmp/swift-key.asc /tmp/swift-keyring.gpg; \
    test -x /opt/swift/usr/bin/swiftc && test -x /opt/swift/usr/bin/swift-build && test ! -e /opt/swift/usr/bin/lldb; \
    chown -R root:root /opt/swift; \
    chmod -R go-w /opt/swift

FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive
# Dependencias de sistema que necesita el toolchain oficial en Debian 13 (versiones fijadas).
ARG BINUTILS_VERSION=2.44-3
ARG BINUTILS_GOLD_VERSION=2.44-2
ARG LIBC_DEV_VERSION=2.41-12+deb13u4
ARG GCC_LIBS_VERSION=14.2.0-19
ARG LIBCURL_VERSION=8.14.1-2+deb13u7
ARG LIBXML2_VERSION=2.12.7+dfsg+really2.9.14-2.1+deb13u3
ARG LIBSQLITE_VERSION=3.46.1-7+deb13u2
ARG LIBEDIT_VERSION=3.1-20250104-1
ARG LIBNCURSES_VERSION=6.5+20250216-2
ARG UUID_DEV_VERSION=2.41.5-0+deb13u1
ARG TZDATA_VERSION=2026e-0+deb13u1

# GORDUS_SWIFT_OFFLINE=true es una marca del proyecto (no de SwiftPM): las pruebas usan
# --disable-automatic-resolution y la imagen no trae git, asi SwiftPM no descarga paquetes.
# Caches escribibles bajo /var/lib/gordus-swift; /opt/swift y /opt/gordus-swift son solo lectura.
ENV PATH=/opt/swift/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    SWIFT_HOME=/opt/swift \
    XDG_CACHE_HOME=/var/lib/gordus-swift/cache \
    CLANG_MODULE_CACHE_PATH=/var/lib/gordus-swift/module-cache \
    GORDUS_SWIFT_OFFLINE=true \
    LANG=C.UTF-8 \
    GORDUS_SWIFT_WORK=/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       "binutils=$BINUTILS_VERSION" "binutils-gold=$BINUTILS_GOLD_VERSION" "libc6-dev=$LIBC_DEV_VERSION" \
       "libgcc-14-dev=$GCC_LIBS_VERSION" "libstdc++-14-dev=$GCC_LIBS_VERSION" \
       "libcurl4t64=$LIBCURL_VERSION" "libxml2=$LIBXML2_VERSION" "libsqlite3-0=$LIBSQLITE_VERSION" \
       "libedit2=$LIBEDIT_VERSION" "libncurses6=$LIBNCURSES_VERSION" "uuid-dev=$UUID_DEV_VERSION" \
       "tzdata=$TZDATA_VERSION" \
    && rm -rf /var/lib/apt/lists/* \
    && test "$(dpkg-query -W -f '${Version}' libstdc++-14-dev)" = "$GCC_LIBS_VERSION" \
    && if command -v python3 || command -v python || command -v curl || command -v wget || command -v git; then \
         echo "BLOCKED: la imagen final no debe traer Python, curl/wget ni git" >&2; exit 3; fi

COPY --from=swift-fetch /opt/swift /opt/swift

RUN groupadd --system swiftuser \
    && useradd --system --gid swiftuser --home-dir /home/swiftuser --create-home swiftuser \
    && install -d -o swiftuser -g swiftuser /workspace /var/lib/gordus-swift \
       /var/lib/gordus-swift/cache /var/lib/gordus-swift/module-cache /var/lib/gordus-swift/build

WORKDIR /opt/gordus-swift
COPY toolchains/swift/components.json /opt/gordus-swift/components.json
COPY toolchains/swift/examples /opt/gordus-swift/examples
COPY toolchains/swift/tests /opt/gordus-swift/tests
RUN chown -R root:root /opt/gordus-swift \
    && chmod -R a=rX /opt/gordus-swift

USER swiftuser
RUN swiftc --version 2>&1 | grep -q "Swift version 6.4.1 " \
    && swiftc --version && swift build --version
WORKDIR /workspace
CMD ["bash"]
