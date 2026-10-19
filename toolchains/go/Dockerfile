# Gordus-Hub - Go toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/ ni .devcontainer/.
# Fuente oficial fijada: distribucion de go.dev/dl, version exacta y SHA-256 por arquitectura
# (los mismos que publica https://go.dev/dl/?mode=json).
# Cualquier cambio de version debe actualizar tambien toolchains/go/components.json;
# toolchains/go/scripts/validate_go_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS go-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG GO_VERSION=1.27.2
ARG GO_URL_BASE=https://go.dev/dl
ARG GO_FILE_AMD64=go1.27.2.linux-amd64.tar.gz
ARG GO_SHA256_AMD64=ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5
ARG GO_FILE_ARM64=go1.27.2.linux-arm64.tar.gz
ARG GO_SHA256_ARM64=94f3e30b8e374bc285e7dadc11e0865726b9bc6e85b841ccceaabc0214c6b7c8

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) file="$GO_FILE_AMD64"; sha="$GO_SHA256_AMD64" ;; \
      arm64) file="$GO_FILE_ARM64"; sha="$GO_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
      -o /tmp/go.tar.gz "$GO_URL_BASE/$file"; \
    echo "$sha  /tmp/go.tar.gz" | sha256sum -c -; \
    install -d /opt/go; \
    tar -xzf /tmp/go.tar.gz -C /opt/go --strip-components=1 --no-same-owner; \
    rm -f /tmp/go.tar.gz; \
    test "$(head -n 1 /opt/go/VERSION)" = "go$GO_VERSION"; \
    chown -R root:root /opt/go; \
    chmod -R go-w /opt/go

FROM debian:13-slim

# GOTOOLCHAIN=local : Go nunca descarga otro toolchain (falla cerrado si go.mod pide otro).
# GOFLAGS=-mod=readonly : go build/test no reescriben go.mod/go.sum.
# GOPROXY=off       : sin descargas de modulos por defecto (los ejemplos no tienen dependencias);
#                     para un proyecto con dependencias: -e GOPROXY=https://proxy.golang.org,direct
# GOSUMDB=sum.golang.org : se mantiene la verificacion de checksums por defecto.
# CGO_ENABLED=0     : binarios estaticos; la imagen no trae compilador C.
ENV GOROOT=/opt/go \
    PATH=/opt/go/bin:/var/lib/gordus-go/gopath/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    GOPATH=/var/lib/gordus-go/gopath \
    GOCACHE=/var/lib/gordus-go/cache \
    GOMODCACHE=/var/lib/gordus-go/modcache \
    GOENV=/var/lib/gordus-go/env/go.env \
    GOTOOLCHAIN=local \
    GOFLAGS=-mod=readonly \
    GOPROXY=off \
    GOSUMDB=sum.golang.org \
    CGO_ENABLED=0 \
    LANG=C.UTF-8 \
    GORDUS_GO_WORK=/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=go-fetch /opt/go /opt/go

RUN groupadd --system gouser \
    && useradd --system --gid gouser --home-dir /home/gouser --create-home gouser \
    && install -d -o gouser -g gouser /workspace /var/lib/gordus-go \
       /var/lib/gordus-go/gopath /var/lib/gordus-go/cache /var/lib/gordus-go/modcache \
    && install -d -o root -g root -m 0755 /var/lib/gordus-go/env \
    && install -m 0444 /dev/null /var/lib/gordus-go/env/go.env

# Telemetria de Go: por defecto es "local" (no sube nada). Se fija en "off" y el archivo
# de modo queda de root y solo lectura, asi "go telemetry on" no puede activarla.
RUN install -d -o root -g root -m 0755 /home/gouser/.config /home/gouser/.config/go \
       /home/gouser/.config/go/telemetry \
    && printf 'off\n' > /home/gouser/.config/go/telemetry/mode \
    && chmod 0444 /home/gouser/.config/go/telemetry/mode

WORKDIR /opt/gordus-go
COPY toolchains/go/components.json /opt/gordus-go/components.json
COPY toolchains/go/examples /opt/gordus-go/examples
COPY toolchains/go/tests /opt/gordus-go/tests
RUN chown -R root:root /opt/gordus-go \
    && chmod -R a=rX /opt/gordus-go

USER gouser
RUN test "$(go env GOTELEMETRY)" = off && test "$(go env GOTOOLCHAIN)" = local
WORKDIR /workspace
CMD ["bash"]
