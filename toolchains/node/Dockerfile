# Gordus-Hub - Node.js / TypeScript toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/,
# toolchains/cpp/, toolchains/rust/ ni .devcontainer/.
# Fuente oficial fijada: tarballs de https://nodejs.org/dist (Node.js 24 LTS "Krypton").
# Verificacion: 1) firma GPG de SHASUMS256.txt con la clave de release fijada por huella
# (tomada del repo oficial nodejs/release-keys en un commit fijo), 2) SHA-256 del tarball
# fijado aqui y presente en ese SHASUMS256.txt firmado.
# TypeScript se instala desde package-lock.json (hashes sha512 "integrity") con npm ci.
# Cualquier cambio de version debe actualizar tambien toolchains/node/components.json;
# toolchains/node/scripts/validate_node_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS node-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG NODE_VERSION=24.22.0
ARG NODE_URL_BASE=https://nodejs.org/dist
ARG NODE_SHA256_AMD64=cc2f601cee82d9a5a233302fe307abc600727035fd7d2c3a3571755989e95008
ARG NODE_SHA256_ARM64=fef00bb4d36e1c50104a9775a10359beee98f162b4104dd12472c75065c6a143
ARG NODE_RELEASE_KEYS_COMMIT=481637f813e912c4aa3622d7964ab426c97b8e8d
ARG NODE_GPG_FINGERPRINT=C82FA3AE1CBEDC6BE46B9360C43CEC45C17AB93C

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils gpg gpgv \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) narch=x64; sha="$NODE_SHA256_AMD64" ;; \
      arm64) narch=arm64; sha="$NODE_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    file="node-v$NODE_VERSION-linux-$narch.tar.xz"; base="$NODE_URL_BASE/v$NODE_VERSION"; \
    export GNUPGHOME=/tmp/gnupg; install -d -m 0700 "$GNUPGHOME"; cd /tmp; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o key.asc \
      "https://raw.githubusercontent.com/nodejs/release-keys/$NODE_RELEASE_KEYS_COMMIT/keys/$NODE_GPG_FINGERPRINT.asc"; \
    test "$(gpg --batch --show-keys --with-colons key.asc | awk -F: '$1 == "fpr" {print $10; exit}')" = "$NODE_GPG_FINGERPRINT" \
      || { echo "BLOCKED: la clave de release de Node no tiene la huella esperada" >&2; exit 3; }; \
    gpg --batch --dearmor < key.asc > node-keyring.gpg; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o SHASUMS256.txt "$base/SHASUMS256.txt"; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o SHASUMS256.txt.sig "$base/SHASUMS256.txt.sig"; \
    gpgv --keyring ./node-keyring.gpg SHASUMS256.txt.sig SHASUMS256.txt; \
    grep -qx "$sha  $file" SHASUMS256.txt \
      || { echo "BLOCKED: el SHA-256 fijado no figura en SHASUMS256.txt firmado" >&2; exit 3; }; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 -o "$file" "$base/$file"; \
    echo "$sha  $file" | sha256sum -c -; \
    install -d /opt/node; \
    tar -xJf "$file" -C /opt/node --strip-components=1 --no-same-owner; \
    rm -rf /tmp/gnupg key.asc node-keyring.gpg SHASUMS256.txt SHASUMS256.txt.sig "$file" \
       /opt/node/share/doc /opt/node/share/man /opt/node/include; \
    test "$(/opt/node/bin/node --version)" = "v$NODE_VERSION"; \
    chown -R root:root /opt/node; \
    chmod -R go-w /opt/node

# Etapa 2: llena la cache de npm con los paquetes del package-lock.json (verificados por
# su hash sha512 "integrity"), para que la imagen final pueda hacer "npm ci --offline".
FROM debian:13-slim AS npm-cache

COPY --from=node-fetch /opt/node /opt/node
ENV PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    NPM_CONFIG_CACHE=/var/lib/gordus-node/npm-cache \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_IGNORE_SCRIPTS=true
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY toolchains/node/examples/hola/package.json toolchains/node/examples/hola/package-lock.json /tmp/hola/
RUN cd /tmp/hola \
    && npm ci --ignore-scripts --no-audit --no-fund \
    && ./node_modules/.bin/tsc --version \
    && rm -rf /tmp/hola /var/lib/gordus-node/npm-cache/_logs

FROM debian:13-slim

# NPM_CONFIG_OFFLINE=true : npm nunca usa la red salvo que se pida (-e NPM_CONFIG_OFFLINE=false).
# NPM_CONFIG_IGNORE_SCRIPTS=true : npm no ejecuta scripts de instalacion de paquetes.
# Sin update-notifier, sin "fund", sin "audit" (que contacta al registro). Node y npm no
# tienen telemetria propia.
ENV PATH=/opt/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    NODE_HOME=/opt/node \
    NPM_CONFIG_CACHE=/var/lib/gordus-node/npm-cache \
    NPM_CONFIG_PREFIX=/var/lib/gordus-node/npm-global \
    NPM_CONFIG_OFFLINE=true \
    NPM_CONFIG_IGNORE_SCRIPTS=true \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    NO_UPDATE_NOTIFIER=1 \
    LANG=C.UTF-8 \
    GORDUS_NODE_WORK=/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && if command -v python3 || command -v python || command -v curl || command -v wget; then \
         echo "BLOCKED: la imagen final no debe traer Python ni curl/wget" >&2; exit 3; fi

COPY --from=node-fetch /opt/node /opt/node

RUN groupadd --system nodeuser \
    && useradd --system --gid nodeuser --home-dir /home/nodeuser --create-home nodeuser \
    && install -d -o nodeuser -g nodeuser /workspace /var/lib/gordus-node \
       /var/lib/gordus-node/npm-global

COPY --from=npm-cache --chown=nodeuser:nodeuser /var/lib/gordus-node/npm-cache /var/lib/gordus-node/npm-cache

WORKDIR /opt/gordus-node
COPY toolchains/node/components.json /opt/gordus-node/components.json
COPY toolchains/node/examples /opt/gordus-node/examples
COPY toolchains/node/tests /opt/gordus-node/tests
RUN chown -R root:root /opt/gordus-node \
    && chmod -R a=rX /opt/gordus-node

USER nodeuser
RUN node --version && npm --version && test "$(npm config get offline)" = true
WORKDIR /workspace
CMD ["bash"]
