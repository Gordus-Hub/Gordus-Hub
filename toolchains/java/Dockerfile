# Gordus-Hub - Java toolchain (JDK 25) - imagen aislada.
# No comparte nada con ai/ (Python) ni con .devcontainer/ (JDK 21 para Android).
# Fuente oficial fijada: Eclipse Temurin (Adoptium), tarball GA verificado por SHA-256.
# Cualquier cambio de version debe actualizar tambien toolchains/java/components.json;
# toolchains/java/scripts/validate_java_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS jdk-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG JDK_VENDOR=eclipse-temurin
ARG JDK_VERSION=25.0.4.1+1
ARG JDK_RELEASE_TAG=jdk-25.0.4.1%2B1
ARG JDK_URL_BASE=https://github.com/adoptium/temurin25-binaries/releases/download
ARG JDK_FILE_AMD64=OpenJDK25U-jdk_x64_linux_hotspot_25.0.4.1_1.tar.gz
ARG JDK_SHA256_AMD64=dbb698396d478e7fa2b1e50f4103324b2a99b90569ee27c33f2261f9215cf41e
ARG JDK_FILE_ARM64=OpenJDK25U-jdk_aarch64_linux_hotspot_25.0.4.1_1.tar.gz
ARG JDK_SHA256_ARM64=69df11a02cfa3ef7d7ca645e03edce6778ec090e100f6ae2b42097865730ac52

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) file="$JDK_FILE_AMD64"; sha="$JDK_SHA256_AMD64" ;; \
      arm64) file="$JDK_FILE_ARM64"; sha="$JDK_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
      -o /tmp/jdk.tar.gz "$JDK_URL_BASE/$JDK_RELEASE_TAG/$file"; \
    echo "$sha  /tmp/jdk.tar.gz" | sha256sum -c -; \
    install -d /opt/java/jdk-25; \
    tar -xzf /tmp/jdk.tar.gz -C /opt/java/jdk-25 --strip-components=1 --no-same-owner; \
    rm -f /tmp/jdk.tar.gz; \
    grep -qx "JAVA_VERSION=\"25.0.4.1\"" /opt/java/jdk-25/release

FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive

ENV JAVA_HOME=/opt/java/jdk-25 \
    PATH=/opt/java/jdk-25/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=C.UTF-8 \
    GORDUS_JAVA_WORK=/workspace

# Bibliotecas minimas que el JDK necesita en tiempo de ejecucion (fuentes/zlib/certificados).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates fontconfig libfreetype6 zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY --from=jdk-fetch /opt/java/jdk-25 /opt/java/jdk-25

RUN groupadd --system java \
    && useradd --system --gid java --home-dir /home/java --create-home java \
    && install -d -o java -g java /workspace

WORKDIR /opt/gordus-java
COPY toolchains/java/components.json /opt/gordus-java/components.json
COPY toolchains/java/examples /opt/gordus-java/examples
COPY toolchains/java/tests /opt/gordus-java/tests
RUN chown -R root:root /opt/java /opt/gordus-java \
    && chmod -R a=rX /opt/gordus-java \
    && chmod -R go-w /opt/java

USER java
WORKDIR /workspace
CMD ["bash"]
