# Gordus-Hub - Mojo toolchain - imagen aislada.
# No comparte nada con ai/ (Python de gordus_ai), toolchains/java/ ni .devcontainer/.
# pixi (gestor de paquetes/entornos que recomienda Modular) se fija por version + SHA-256.
# Mojo y todas sus dependencias se fijan con toolchains/mojo/env/pixi.toml + pixi.lock
# (cada paquete conda del lock lleva su SHA-256); "pixi install --locked" falla cerrado
# si el lock no coincide con el manifiesto. Cualquier cambio de version debe actualizar
# tambien toolchains/mojo/components.json; scripts/validate_mojo_toolchain.py lo verifica.

FROM debian:13-slim AS pixi-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG PIXI_VERSION=0.82.0
ARG PIXI_URL_BASE=https://github.com/prefix-dev/pixi/releases/download
ARG PIXI_FILE_AMD64=pixi-x86_64-unknown-linux-musl.tar.gz
ARG PIXI_SHA256_AMD64=d305406a7630aab6484419833f9204b2fe9ea40632da8bb536496f123ca86e7f
ARG PIXI_FILE_ARM64=pixi-aarch64-unknown-linux-musl.tar.gz
ARG PIXI_SHA256_ARM64=b18dadba196c0c77781533184ec3e7757422c0ae9bed0047ff7ca1c688c0f62b

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) file="$PIXI_FILE_AMD64"; sha="$PIXI_SHA256_AMD64" ;; \
      arm64) file="$PIXI_FILE_ARM64"; sha="$PIXI_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 \
      -o /tmp/pixi.tar.gz "$PIXI_URL_BASE/v$PIXI_VERSION/$file"; \
    echo "$sha  /tmp/pixi.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/pixi.tar.gz -C /usr/local/bin pixi; \
    chmod 0755 /usr/local/bin/pixi; \
    rm -f /tmp/pixi.tar.gz; \
    test "$(/usr/local/bin/pixi --version)" = "pixi $PIXI_VERSION"

FROM debian:13-slim AS mojo-env

ARG DEBIAN_FRONTEND=noninteractive
ENV PIXI_HOME=/tmp/pixi-home \
    PIXI_CACHE_DIR=/tmp/pixi-cache \
    NO_COLOR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=pixi-fetch /usr/local/bin/pixi /usr/local/bin/pixi
COPY toolchains/mojo/env/pixi.toml toolchains/mojo/env/pixi.lock /opt/mojo/env/

# --locked: usa SOLO lo que dice pixi.lock (con sus SHA-256) y falla si no coincide.
# Se marca firstActivation para que el script de activacion de Modular no envie
# su evento de telemetria de "primera activacion".
RUN set -eu; \
    cd /opt/mojo/env; \
    pixi install --locked; \
    touch /opt/mojo/env/.pixi/envs/default/share/max/firstActivation; \
    /opt/mojo/env/.pixi/envs/default/bin/mojo --version | grep -q '^Mojo 1\.1\.0 '; \
    rm -rf /tmp/pixi-cache /tmp/pixi-home; \
    chown -R root:root /opt/mojo; \
    chmod -R go-w /opt/mojo

FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive

ENV MOJO_ENV=/opt/mojo/env/.pixi/envs/default \
    CONDA_PREFIX=/opt/mojo/env/.pixi/envs/default \
    MODULAR_HOME=/var/lib/gordus-mojo/max \
    PATH=/opt/mojo/env/.pixi/envs/default/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PIXI_HOME=/home/mojo/.pixi \
    PIXI_CACHE_DIR=/home/mojo/.cache/rattler \
    LANG=C.UTF-8 \
    GORDUS_MOJO_WORK=/workspace

# Modular exige "un compilador C (cc, gcc o clang) en Linux, usado como enlazador"
# para "mojo build" (https://mojolang.org/docs/requirements). Se usa el gcc de Debian 13.
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=pixi-fetch /usr/local/bin/pixi /usr/local/bin/pixi
COPY --from=mojo-env /opt/mojo /opt/mojo

# El SDK es de solo lectura (root). Mojo necesita escribir su cache y crashdb, asi que
# MODULAR_HOME apunta a un directorio de estado propio del usuario "mojo" con una copia
# de solo lectura de modular.cfg (solo cambia cache_dir). firstActivation ya existe:
# el script de activacion de Modular no envia su evento de telemetria.
RUN groupadd --system mojo \
    && useradd --system --gid mojo --home-dir /home/mojo --create-home mojo \
    && install -d -o mojo -g mojo /workspace /var/lib/gordus-mojo/max \
       /var/lib/gordus-mojo/max/cache /var/lib/gordus-mojo/max/crashdb \
       /var/lib/gordus-mojo/max/.max_cache \
    && sed 's#^cache_dir = .*#cache_dir = /var/lib/gordus-mojo/max/.max_cache#' \
       "$MOJO_ENV/share/max/modular.cfg" > /var/lib/gordus-mojo/max/modular.cfg \
    && chmod 0444 /var/lib/gordus-mojo/max/modular.cfg \
    && install -m 0444 /dev/null /var/lib/gordus-mojo/max/firstActivation

WORKDIR /opt/gordus-mojo
COPY toolchains/mojo/components.json /opt/gordus-mojo/components.json
COPY toolchains/mojo/examples /opt/gordus-mojo/examples
COPY toolchains/mojo/tests /opt/gordus-mojo/tests
# /opt/mojo ya llega como root y sin escritura para grupo/otros desde la etapa mojo-env
# (hacer chown aca duplicaria ~900 MB en otra capa).
RUN chown -R root:root /opt/gordus-mojo \
    && chmod -R a=rX /opt/gordus-mojo

USER mojo
WORKDIR /workspace
CMD ["bash"]
