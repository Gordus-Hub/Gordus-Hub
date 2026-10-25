# Gordus-Hub - Scala toolchain (Scala 3.10.0 + scala-cli incluido + JDK 25 propio) - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/ (JDK 25 de Java), toolchains/kotlin/ ni .devcontainer/.
# Fuentes oficiales fijadas: Eclipse Temurin (Adoptium, SHA-256 + firma GPG con huella fijada)
# y la distribucion oficial de Scala 3 para Linux publicada en GitHub (scala/scala3, SHA-256 por arquitectura).
# Cualquier cambio de version debe actualizar tambien toolchains/scala/components.json;
# toolchains/scala/scripts/validate_scala_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG JDK_VERSION=25.0.5+8
ARG JDK_RELEASE_TAG=jdk-25.0.5%2B8
ARG JDK_URL_BASE=https://github.com/adoptium/temurin25-binaries/releases/download
ARG JDK_FILE_AMD64=OpenJDK25U-jdk_x64_linux_hotspot_25.0.5_8.tar.gz
ARG JDK_SHA256_AMD64=68982529869257d0ee6b824ec5aa270ff8b118bb438670da0b97ebdab178d7fb
ARG JDK_FILE_ARM64=OpenJDK25U-jdk_aarch64_linux_hotspot_25.0.5_8.tar.gz
ARG JDK_SHA256_ARM64=bb5b2ded252f21c6090cf780b0a408ad0d83bbb557e702955643557f13231880
ARG ADOPTIUM_GPG_FINGERPRINT=3B04D753C9050D9A5D343F39843C48A565F8F04B
ARG SCALA_VERSION=3.10.0
ARG SCALA_URL_BASE=https://github.com/scala/scala3/releases/download/3.10.0
ARG SCALA_FILE_AMD64=scala3-3.10.0-x86_64-pc-linux.tar.gz
ARG SCALA_SHA256_AMD64=5dc94c2d4c653e29277f8b482b2c7bb90d2737838930c41422c7b253dfec1b3a
ARG SCALA_FILE_ARM64=scala3-3.10.0-aarch64-pc-linux.tar.gz
ARG SCALA_SHA256_ARM64=a14242e269847cd46a80d45e2ba3f0ea3bdecda9b2b5ac78effad07adc499aea

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gpg gpgv \
    && rm -rf /var/lib/apt/lists/*

# Clave publica de Adoptium guardada en el repo (no se baja de un keyserver: evita fallos de red).
COPY toolchains/scala/keys/adoptium-release-key.asc /tmp/keys/adoptium-release-key.asc

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) file="$JDK_FILE_AMD64"; sha="$JDK_SHA256_AMD64" ;; \
      arm64) file="$JDK_FILE_ARM64"; sha="$JDK_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
      -o /tmp/jdk.tar.gz "$JDK_URL_BASE/$JDK_RELEASE_TAG/$file"; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
      -o /tmp/jdk.tar.gz.sig "$JDK_URL_BASE/$JDK_RELEASE_TAG/$file.sig"; \
    echo "$sha  /tmp/jdk.tar.gz" | sha256sum -c -; \
    fpr="$(gpg --batch --with-colons --show-keys /tmp/keys/adoptium-release-key.asc | awk -F: '/^fpr:/ {print $10; exit}')"; \
    [ "$fpr" = "$ADOPTIUM_GPG_FINGERPRINT" ] || { echo "BLOCKED: huella GPG inesperada: $fpr" >&2; exit 3; }; \
    gpg --batch --dearmor -o /tmp/keys/adoptium.gpg /tmp/keys/adoptium-release-key.asc; \
    gpgv --keyring /tmp/keys/adoptium.gpg /tmp/jdk.tar.gz.sig /tmp/jdk.tar.gz; \
    install -d /opt/scala/jdk-25; \
    tar -xzf /tmp/jdk.tar.gz -C /opt/scala/jdk-25 --strip-components=1 --no-same-owner; \
    rm -rf /tmp/jdk.tar.gz /tmp/jdk.tar.gz.sig /tmp/keys; \
    grep -qx "JAVA_VERSION=\"25.0.5\"" /opt/scala/jdk-25/release

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) file="$SCALA_FILE_AMD64"; sha="$SCALA_SHA256_AMD64" ;; \
      arm64) file="$SCALA_FILE_ARM64"; sha="$SCALA_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
      -o /tmp/scala.tar.gz "$SCALA_URL_BASE/$file"; \
    echo "$sha  /tmp/scala.tar.gz" | sha256sum -c -; \
    install -d /opt/scala/scala3; \
    tar -xzf /tmp/scala.tar.gz -C /opt/scala/scala3 --strip-components=1 --no-same-owner; \
    rm -f /tmp/scala.tar.gz; \
    find /opt/scala/scala3 -name '*.bat' -delete; \
    grep -qx "version:=$SCALA_VERSION" /opt/scala/scala3/VERSION

FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG PKG_BASH_VERSION=5.2.37-2+b10
ARG PKG_CA_CERTIFICATES_VERSION=20250419+deb13u1
ARG PKG_FONTCONFIG_VERSION=2.15.0-2.3
ARG PKG_LIBFREETYPE6_VERSION=2.13.3+dfsg-1+deb13u1
ARG PKG_ZLIB1G_VERSION=1:1.3.dfsg+really1.3.1-1+b1

ENV JAVA_HOME=/opt/scala/jdk-25 \
    SCALA_HOME=/opt/scala/scala3 \
    PATH=/opt/scala/scala3/bin:/opt/scala/jdk-25/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 \
    GORDUS_SCALA_OFFLINE=true \
    GORDUS_SCALA_WORK=/workspace

# bash (lo exigen los lanzadores scalac/scala/scala-cli) y bibliotecas minimas del JDK, con version fija.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash="$PKG_BASH_VERSION" \
       ca-certificates="$PKG_CA_CERTIFICATES_VERSION" \
       fontconfig="$PKG_FONTCONFIG_VERSION" \
       libfreetype6="$PKG_LIBFREETYPE6_VERSION" \
       zlib1g="$PKG_ZLIB1G_VERSION" \
    && rm -rf /var/lib/apt/lists/*

COPY --from=fetch /opt/scala /opt/scala

RUN groupadd --system scala \
    && useradd --system --gid scala --home-dir /home/scala --create-home scala \
    && install -d -o scala -g scala /workspace

WORKDIR /opt/gordus-scala
COPY toolchains/scala/components.json /opt/gordus-scala/components.json
COPY toolchains/scala/examples /opt/gordus-scala/examples
COPY toolchains/scala/tests /opt/gordus-scala/tests
RUN chown -R root:root /opt/scala /opt/gordus-scala \
    && chmod -R a=rX /opt/gordus-scala \
    && chmod -R go-w /opt/scala

USER scala
WORKDIR /workspace
CMD ["bash"]
