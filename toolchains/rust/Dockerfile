# Gordus-Hub - Rust toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/,
# toolchains/cpp/ ni .devcontainer/.
# Fuente oficial fijada: tarballs por componente de static.rust-lang.org (canal stable del
# 2026-10-15, Rust 1.99.1). Cada tarball se verifica con:
#   1) el SHA-256 fijado aqui (el mismo del manifiesto channel-rust-stable.toml y del .sha256), y
#   2) la firma GPG (.asc) con la clave de Rust, fijada por huella digital.
# Cualquier cambio de version debe actualizar tambien toolchains/rust/components.json;
# toolchains/rust/scripts/validate_rust_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS rust-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG RUST_VERSION=1.99.1
ARG RUST_DIST_DATE=2026-10-15
ARG RUST_URL_BASE=https://static.rust-lang.org/dist
ARG RUST_GPG_KEY_URL=https://static.rust-lang.org/rust-key.gpg.ascii
ARG RUST_GPG_FINGERPRINT=108F66205EAEB0AAA8DD5E1C85AB96E6FA1BE5FE
ARG RUSTC_SHA256_AMD64=2ff05ff9c08a90861e7f6e4065b40a8b87463b4576186fd613871c3e37f2091f
ARG RUST_STD_SHA256_AMD64=109b074225bf5b9ea3820890876bfdf4ed161adbfaf94b2b4b5984c85ee5d958
ARG CARGO_SHA256_AMD64=53f3521949404d595efb06a55c12c5658d4ed1c75566f33d3d514eaebe70bd8a
ARG RUSTFMT_SHA256_AMD64=e3b36c4c7ec3486c059d8067ff48787676612007123aad7a4e8ec12c48ee9ba2
ARG CLIPPY_SHA256_AMD64=458339712a058e52cc4522ff9ef8b59cd1ea1340312216cd94194c464a3f6dc5
ARG RUSTC_SHA256_ARM64=acdcdfe09ae1f103aa9a2b7f88903a9588bc2e99288af10e6fbf5514e2e49f25
ARG RUST_STD_SHA256_ARM64=e25668477083d6a9ddb87b9beb9c00742225f38233ccb4bfba3afa7a07427f52
ARG CARGO_SHA256_ARM64=5156832e0c1254e9b49a79edabdc6d4c35f32f8fc1cf3ca700f268ff96087ab0
ARG RUSTFMT_SHA256_ARM64=26b3200b1461921415927abf7fe410202a6eda2db3e419abde59e0abfcd93fc2
ARG CLIPPY_SHA256_ARM64=3bea76c26dcf30c176c0a8a8cc283eb59fabd754e24a68b4ca0701e5f3245f6b

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils gpg gpgv \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) triple=x86_64-unknown-linux-gnu; \
             set -- "rustc:$RUSTC_SHA256_AMD64" "rust-std:$RUST_STD_SHA256_AMD64" "cargo:$CARGO_SHA256_AMD64" \
                    "rustfmt:$RUSTFMT_SHA256_AMD64" "clippy:$CLIPPY_SHA256_AMD64" ;; \
      arm64) triple=aarch64-unknown-linux-gnu; \
             set -- "rustc:$RUSTC_SHA256_ARM64" "rust-std:$RUST_STD_SHA256_ARM64" "cargo:$CARGO_SHA256_ARM64" \
                    "rustfmt:$RUSTFMT_SHA256_ARM64" "clippy:$CLIPPY_SHA256_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    export GNUPGHOME=/tmp/gnupg; install -d -m 0700 "$GNUPGHOME"; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o /tmp/rust-key.asc "$RUST_GPG_KEY_URL"; \
    test "$(gpg --batch --show-keys --with-colons /tmp/rust-key.asc | awk -F: '$1 == "fpr" {print $10; exit}')" = "$RUST_GPG_FINGERPRINT" \
      || { echo "BLOCKED: la clave GPG de Rust no tiene la huella esperada" >&2; exit 3; }; \
    gpg --batch --dearmor < /tmp/rust-key.asc > /tmp/rust-keyring.gpg; \
    install -d /tmp/rust; \
    for entry in "$@"; do \
      comp="${entry%%:*}"; sha="${entry#*:}"; \
      file="$comp-$RUST_VERSION-$triple.tar.xz"; url="$RUST_URL_BASE/$RUST_DIST_DATE/$file"; \
      curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 -o "/tmp/rust/$file" "$url"; \
      curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 -o "/tmp/rust/$file.asc" "$url.asc"; \
      echo "$sha  /tmp/rust/$file" | sha256sum -c -; \
      gpgv --keyring /tmp/rust-keyring.gpg "/tmp/rust/$file.asc" "/tmp/rust/$file"; \
      tar -xJf "/tmp/rust/$file" -C /tmp/rust --no-same-owner; \
      dir="/tmp/rust/$comp-$RUST_VERSION-$triple"; \
      "$dir/install.sh" --prefix=/opt/rust --disable-ldconfig > /dev/null; \
      rm -rf "$dir" "/tmp/rust/$file" "/tmp/rust/$file.asc"; \
    done; \
    rm -rf /tmp/rust /tmp/gnupg /tmp/rust-key.asc /tmp/rust-keyring.gpg /opt/rust/share/doc; \
    /opt/rust/bin/rustc --version | grep -q "^rustc $RUST_VERSION "; \
    chown -R root:root /opt/rust; \
    chmod -R go-w /opt/rust

FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive
# Enlazador: rustc (target *-linux-gnu) llama a "cc" para enlazar. Se usa el gcc 14 de
# Debian (mismas versiones fijadas que toolchains/cpp/, pero en esta imagen aparte).
ARG GCC_VERSION=14.2.0-19
ARG BINUTILS_VERSION=2.44-3
ARG LIBC_DEV_VERSION=2.41-12+deb13u4

# CARGO_NET_OFFLINE=true : cargo nunca usa la red salvo que se pida (-e CARGO_NET_OFFLINE=false).
# CARGO_HOME bajo /var/lib/gordus-rust : registro y cache escribibles; /opt/rust es solo lectura.
ENV PATH=/opt/rust/bin:/var/lib/gordus-rust/cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    RUST_HOME=/opt/rust \
    CARGO_HOME=/var/lib/gordus-rust/cargo \
    CARGO_TARGET_DIR=/var/lib/gordus-rust/target \
    CARGO_NET_OFFLINE=true \
    CARGO_INCREMENTAL=0 \
    CARGO_TERM_COLOR=never \
    LANG=C.UTF-8 \
    GORDUS_RUST_WORK=/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       "gcc-14=$GCC_VERSION" "binutils=$BINUTILS_VERSION" "libc6-dev=$LIBC_DEV_VERSION" \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/gcc-14 /usr/local/bin/cc \
    && ln -s /usr/bin/gcc-14 /usr/local/bin/gcc \
    && test "$(dpkg-query -W -f '${Version}' gcc-14)" = "$GCC_VERSION" \
    && if command -v python3 || command -v python || command -v curl || command -v wget; then \
         echo "BLOCKED: la imagen final no debe traer Python ni curl/wget" >&2; exit 3; fi

COPY --from=rust-fetch /opt/rust /opt/rust

RUN groupadd --system rustuser \
    && useradd --system --gid rustuser --home-dir /home/rustuser --create-home rustuser \
    && install -d -o rustuser -g rustuser /workspace /var/lib/gordus-rust \
       /var/lib/gordus-rust/cargo /var/lib/gordus-rust/target

WORKDIR /opt/gordus-rust
COPY toolchains/rust/components.json /opt/gordus-rust/components.json
COPY toolchains/rust/examples /opt/gordus-rust/examples
COPY toolchains/rust/tests /opt/gordus-rust/tests
RUN chown -R root:root /opt/gordus-rust \
    && chmod -R a=rX /opt/gordus-rust

USER rustuser
RUN rustc --version && cargo --version && cargo fmt --version && cargo clippy --version
WORKDIR /workspace
CMD ["bash"]
