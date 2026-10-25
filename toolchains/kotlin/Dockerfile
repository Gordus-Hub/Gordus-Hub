# Gordus-Hub - Kotlin toolchain (kotlinc 2.4.21 + JDK 25 propio) - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/ (JDK 25 de Java) ni .devcontainer/ (JDK 21 Android).
# Fuentes oficiales fijadas: Eclipse Temurin (Adoptium, SHA-256 + firma GPG con huella fijada)
# y el compilador oficial de Kotlin publicado por JetBrains en GitHub (SHA-256).
# Cualquier cambio de version debe actualizar tambien toolchains/kotlin/components.json;
# toolchains/kotlin/scripts/validate_kotlin_toolchain.py falla cerrado si no coinciden.

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
ARG KOTLIN_VERSION=2.4.21
ARG KOTLIN_URL=https://github.com/JetBrains/kotlin/releases/download/v2.4.21/kotlin-compiler-2.4.21.zip
ARG KOTLIN_SHA256=7cc140e76daf416a0424a5557f99afd7ca89ebd463ea1101261e3e01c33e75cd

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gpg gpgv unzip \
    && rm -rf /var/lib/apt/lists/*

# Clave publica de Adoptium guardada en el repo (no se baja de un keyserver: evita fallos de red).
COPY toolchains/kotlin/keys/adoptium-release-key.asc /tmp/keys/adoptium-release-key.asc

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
    install -d /opt/kotlin/jdk-25; \
    tar -xzf /tmp/jdk.tar.gz -C /opt/kotlin/jdk-25 --strip-components=1 --no-same-owner; \
    rm -rf /tmp/jdk.tar.gz /tmp/jdk.tar.gz.sig /tmp/keys; \
    grep -qx "JAVA_VERSION=\"25.0.5\"" /opt/kotlin/jdk-25/release

RUN set -eu; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
      -o /tmp/kotlin.zip "$KOTLIN_URL"; \
    echo "$KOTLIN_SHA256  /tmp/kotlin.zip" | sha256sum -c -; \
    unzip -q /tmp/kotlin.zip -d /tmp/kotlin-unpacked; \
    mv /tmp/kotlin-unpacked/kotlinc /opt/kotlin/kotlinc; \
    rm -rf /tmp/kotlin.zip /tmp/kotlin-unpacked; \
    find /opt/kotlin/kotlinc -name '*.bat' -delete; \
    grep -qx "$KOTLIN_VERSION" /opt/kotlin/kotlinc/build.txt

FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG PKG_BASH_VERSION=5.2.37-2+b10
ARG PKG_CA_CERTIFICATES_VERSION=20250419+deb13u1
ARG PKG_FONTCONFIG_VERSION=2.15.0-2.3
ARG PKG_LIBFREETYPE6_VERSION=2.13.3+dfsg-1+deb13u1
ARG PKG_ZLIB1G_VERSION=1:1.3.dfsg+really1.3.1-1+b1

ENV JAVA_HOME=/opt/kotlin/jdk-25 \
    KOTLIN_HOME=/opt/kotlin/kotlinc \
    PATH=/opt/kotlin/kotlinc/bin:/opt/kotlin/jdk-25/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 \
    GORDUS_KOTLIN_OFFLINE=true \
    GORDUS_KOTLIN_WORK=/workspace

# bash (lo exigen los lanzadores kotlinc/kotlin) y bibliotecas minimas del JDK, con version fija.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash="$PKG_BASH_VERSION" \
       ca-certificates="$PKG_CA_CERTIFICATES_VERSION" \
       fontconfig="$PKG_FONTCONFIG_VERSION" \
       libfreetype6="$PKG_LIBFREETYPE6_VERSION" \
       zlib1g="$PKG_ZLIB1G_VERSION" \
    && rm -rf /var/lib/apt/lists/*

COPY --from=fetch /opt/kotlin /opt/kotlin

RUN groupadd --system kotlin \
    && useradd --system --gid kotlin --home-dir /home/kotlin --create-home kotlin \
    && install -d -o kotlin -g kotlin /workspace

WORKDIR /opt/gordus-kotlin
COPY toolchains/kotlin/components.json /opt/gordus-kotlin/components.json
COPY toolchains/kotlin/examples /opt/gordus-kotlin/examples
COPY toolchains/kotlin/tests /opt/gordus-kotlin/tests
RUN chown -R root:root /opt/kotlin /opt/gordus-kotlin \
    && chmod -R a=rX /opt/gordus-kotlin \
    && chmod -R go-w /opt/kotlin

USER kotlin
WORKDIR /workspace
CMD ["bash"]
