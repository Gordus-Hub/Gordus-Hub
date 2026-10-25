# Gordus-Hub - Ruby toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/,
# toolchains/cpp/, toolchains/rust/, toolchains/node/, toolchains/dotnet/, toolchains/swift/, toolchains/kotlin/,
# toolchains/scala/ ni .devcontainer/.
# Fuente oficial: https://cache.ruby-lang.org/pub/ruby (codigo fuente, se compila aqui).
# Ruby no publica firmas GPG de sus tarballs: la verificacion es doble, SHA-256 (anuncio
# oficial en ruby-lang.org) y SHA-512 (indice oficial cache.ruby-lang.org/pub/ruby/index.txt),
# ambos fijados aqui. RubyGems, Bundler, Minitest y Rake vienen dentro del tarball de Ruby.
# Cualquier cambio de version debe actualizar tambien toolchains/ruby/components.json;
# toolchains/ruby/scripts/validate_ruby_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS ruby-build

ARG DEBIAN_FRONTEND=noninteractive
ARG RUBY_VERSION=4.0.9
ARG RUBY_SERIES=4.0
ARG RUBY_URL_BASE=https://cache.ruby-lang.org/pub/ruby
ARG RUBY_SHA256=a8057adb39f51ad6dc3106237504c93dd792bb515837b4fe7817ae21ed7e51f4
ARG RUBY_SHA512=7160b1c6fb61b0e369cddccb29eadae85390d86777c875efc18a56de390b1fe1ff47d6e37ccaf39d2ed477c9811f1224cbb3d2f54a0cbd5d5daf418b1cf2557e

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
       gcc make pkg-config file libc6-dev libssl-dev zlib1g-dev libyaml-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    file="ruby-$RUBY_VERSION.tar.xz"; cd /tmp; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o "$file" "$RUBY_URL_BASE/$RUBY_SERIES/$file"; \
    echo "$RUBY_SHA256  $file" | sha256sum -c -; \
    echo "$RUBY_SHA512  $file" | sha512sum -c -; \
    install -d /usr/src/ruby; \
    tar -xJf "$file" -C /usr/src/ruby --strip-components=1 --no-same-owner; \
    rm -f "$file"

RUN set -eu; cd /usr/src/ruby; \
    ./configure --prefix=/opt/ruby --disable-install-doc --disable-install-rdoc > /tmp/configure.log; \
    make -j"$(nproc)" > /tmp/make.log; \
    make install > /tmp/install.log; \
    rm -rf /usr/src/ruby /tmp/*.log /opt/ruby/share/man /opt/ruby/include; \
    find /opt/ruby -name '*.a' -delete; \
    strip --strip-unneeded /opt/ruby/bin/ruby; \
    test "$(/opt/ruby/bin/ruby -e 'print RUBY_VERSION')" = "$RUBY_VERSION"; \
    chown -R root:root /opt/ruby; \
    chmod -R go-w /opt/ruby

FROM debian:13-slim

# Sin red por defecto: "bundle install --local" solo usa gemas ya instaladas; las gemas nuevas
# van a GEM_HOME (escribible) y nunca a /opt/ruby. BUNDLE_FROZEN=true exige Gemfile.lock.
# Ruby, RubyGems y Bundler no tienen telemetria.
ENV PATH=/opt/ruby/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    RUBY_HOME=/opt/ruby \
    GEM_HOME=/var/lib/gordus-ruby/gems \
    GEM_PATH=/var/lib/gordus-ruby/gems:/opt/ruby/lib/ruby/gems/4.0.0 \
    BUNDLE_USER_HOME=/var/lib/gordus-ruby/bundle \
    BUNDLE_FROZEN=true \
    BUNDLE_DISABLE_VERSION_CHECK=true \
    BUNDLE_IGNORE_FUNDING_REQUESTS=true \
    BUNDLE_SILENCE_ROOT_WARNING=true \
    LANG=C.UTF-8 \
    GORDUS_RUBY_WORK=/workspace

# Bibliotecas que necesita Ruby, fijadas por version exacta de Debian 13.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates=20250419+deb13u1 \
       libffi8=3.4.8-2 \
       libssl3t64=3.5.7-1~deb13u3 \
       libyaml-0-2=0.2.5-2 \
       zlib1g=1:1.3.dfsg+really1.3.1-1+b1 \
    && rm -rf /var/lib/apt/lists/* \
    && if command -v python3 || command -v python || command -v curl || command -v wget; then \
         echo "BLOCKED: la imagen final no debe traer Python ni curl/wget" >&2; exit 3; fi

COPY --from=ruby-build /opt/ruby /opt/ruby

RUN groupadd --system rubyuser \
    && useradd --system --gid rubyuser --home-dir /home/rubyuser --create-home rubyuser \
    && install -d -o rubyuser -g rubyuser /workspace /var/lib/gordus-ruby \
       /var/lib/gordus-ruby/gems /var/lib/gordus-ruby/bundle

WORKDIR /opt/gordus-ruby
COPY toolchains/ruby/components.json /opt/gordus-ruby/components.json
COPY toolchains/ruby/examples /opt/gordus-ruby/examples
COPY toolchains/ruby/tests /opt/gordus-ruby/tests
RUN chown -R root:root /opt/gordus-ruby \
    && chmod -R a=rX /opt/gordus-ruby

USER rubyuser
RUN ruby --version && gem --version && bundle --version
WORKDIR /workspace
CMD ["bash"]
