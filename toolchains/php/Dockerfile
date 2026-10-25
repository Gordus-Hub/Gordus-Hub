# Gordus-Hub - PHP toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/,
# toolchains/cpp/, toolchains/rust/, toolchains/node/, toolchains/dotnet/, toolchains/swift/,
# toolchains/ruby/ ni .devcontainer/.
# SEGURIDAD: PHP 8.5.12 (21/10/2026) corrige CVE-2026-109618 y CVE-2026-109619 (RCE criticas,
# CVSS 4.0 9.2). Nunca bajar de 8.5.12: el validador bloquea cualquier version sin el parche.
# Fuente oficial: https://www.php.net/distributions (codigo fuente, se compila aqui).
# Verificacion: 1) firma GPG (.asc) del tarball con la clave del release manager de PHP 8.5,
# guardada en toolchains/php/keys/ (sacada de php.net/distributions/php-keyring.gpg) y fijada
# por huella, 2) SHA-256 publicado en php.net fijado aqui. Las claves van en el repo para que el
# CI no dependa de bajar claves (keyserver caido = build roto).
# Composer y PHPUnit: PHAR oficiales con SHA-256 fijado y firma GPG con clave fijada por huella.
# Cualquier cambio de version debe actualizar tambien toolchains/php/components.json;
# toolchains/php/scripts/validate_php_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS php-build

ARG DEBIAN_FRONTEND=noninteractive
ARG PHP_VERSION=8.5.12
ARG PHP_URL_BASE=https://www.php.net/distributions
ARG PHP_SHA256=08bc2eba2a588654ade1357174aa646b761556c862dda0678345ee29ed481209
ARG PHP_GPG_FINGERPRINT=D95C03BC702BE9515344AE3374E44BC9067701A5

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils gpg gpgv \
       gcc g++ make pkg-config file libc6-dev libxml2-dev libonig-dev libssl-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY toolchains/php/keys/php-release-manager-daniel-scherzer.asc /tmp/keys/php-rm.asc

RUN set -eu; \
    file="php-$PHP_VERSION.tar.xz"; \
    export GNUPGHOME=/tmp/gnupg; install -d -m 0700 "$GNUPGHOME"; cd /tmp; \
    fpr="$(gpg --batch --show-keys --with-colons /tmp/keys/php-rm.asc | awk -F: '$1 == "fpr" {print $10; exit}')"; \
    [ "$fpr" = "$PHP_GPG_FINGERPRINT" ] \
      || { echo "BLOCKED: la clave guardada no es la del release manager fijado" >&2; exit 3; }; \
    gpg --batch --dearmor < /tmp/keys/php-rm.asc > php-keyring.kbx; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o "$file" "$PHP_URL_BASE/$file"; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o "$file.asc" "$PHP_URL_BASE/$file.asc"; \
    gpgv --status-fd 1 --keyring ./php-keyring.kbx "$file.asc" "$file" > gpgv.out; \
    grep -q "^\[GNUPG:\] VALIDSIG .* $PHP_GPG_FINGERPRINT\$" gpgv.out \
      || { echo "BLOCKED: la firma de PHP no es de la clave fijada" >&2; exit 3; }; \
    echo "$PHP_SHA256  $file" | sha256sum -c -; \
    install -d /usr/src/php; \
    tar -xJf "$file" -C /usr/src/php --strip-components=1 --no-same-owner; \
    rm -rf /tmp/gnupg /tmp/keys php-keyring.kbx gpgv.out "$file" "$file.asc"

# Solo PHP de linea de comandos (CLI): sin php-cgi, sin php-fpm, sin mod_php, sin SQLite.
# Extensiones que piden Composer y PHPUnit: dom, xml, xmlwriter, mbstring, tokenizer, openssl, phar.
RUN set -eu; cd /usr/src/php; \
    ./configure --prefix=/opt/php \
      --with-config-file-path=/opt/php/etc --with-config-file-scan-dir=/opt/php/etc/conf.d \
      --disable-cgi --disable-phpdbg --without-pear \
      --without-sqlite3 --without-pdo-sqlite \
      --enable-mbstring --with-openssl --with-zlib > /tmp/configure.log; \
    make -j"$(nproc)" > /tmp/make.log; \
    make install > /tmp/install.log; \
    install -d /opt/php/etc/conf.d; \
    install -m 0644 php.ini-production /opt/php/etc/php.ini; \
    strip --strip-unneeded /opt/php/bin/php; \
    rm -rf /opt/php/include /opt/php/lib/php/build /opt/php/php/man /opt/php/bin/phpize \
       /opt/php/bin/php-config /usr/src/php /tmp/*.log; \
    test "$(/opt/php/bin/php -r 'echo PHP_VERSION;')" = "$PHP_VERSION"; \
    /opt/php/bin/php -r 'exit(PHP_VERSION_ID >= 80512 ? 0 : 3);' \
      || { echo "BLOCKED: PHP sin el parche de seguridad de 21/10/2026" >&2; exit 3; }

# Etapa 2: Composer y PHPUnit (PHAR oficiales firmados).
FROM debian:13-slim AS php-tools-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG COMPOSER_VERSION=2.10.3
ARG COMPOSER_SHA256=7a2d379d5b8ffdaa028580ef26494c36d2feef4b178d3dd1473a4dbc5e17c8d6
ARG COMPOSER_GPG_FINGERPRINT=161DFBE342889F01DDAC4E61CBB3D576F2A0946F
ARG PHPUNIT_VERSION=13.4.3
ARG PHPUNIT_SHA256=f9f8f986f2b6e862187a04619eb01b5960cea77bb39bd1e38d3e396a99eae516
ARG PHPUNIT_GPG_FINGERPRINT=D8406D0D82947747293778314AA394086372C20A

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gpg gpgv \
    && rm -rf /var/lib/apt/lists/*

COPY toolchains/php/keys/composer-packagist.asc /tmp/keys/composer.phar.key.asc
COPY toolchains/php/keys/phpunit-sebastian-bergmann.asc /tmp/keys/phpunit.phar.key.asc

RUN set -eu; \
    export GNUPGHOME=/tmp/gnupg; install -d -m 0700 "$GNUPGHOME" /out; cd /tmp; \
    fetch() { curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 -o "$1" "$2"; }; \
    verify() { name="$1"; url="$2"; sha="$3"; fpr="$4"; \
      key="/tmp/keys/$name.key.asc"; \
      test "$(gpg --batch --show-keys --with-colons "$key" | awk -F: '$1 == "fpr" {print $10; exit}')" = "$fpr" \
        || { echo "BLOCKED: clave de $name con huella inesperada" >&2; exit 3; }; \
      gpg --batch --dearmor < "$key" > "$fpr.gpg"; \
      fetch "$name" "$url"; fetch "$name.asc" "$url.asc"; \
      gpgv --status-fd 1 --keyring "./$fpr.gpg" "$name.asc" "$name" > "$name.gpgv"; \
      grep -q "^\[GNUPG:\] VALIDSIG .* $fpr\$" "$name.gpgv" \
        || { echo "BLOCKED: firma de $name no es de la clave fijada" >&2; exit 3; }; \
      echo "$sha  $name" | sha256sum -c -; \
      install -m 0755 "$name" "/out/$name"; }; \
    verify composer.phar "https://getcomposer.org/download/$COMPOSER_VERSION/composer.phar" "$COMPOSER_SHA256" "$COMPOSER_GPG_FINGERPRINT"; \
    verify phpunit.phar "https://phar.phpunit.de/phpunit-$PHPUNIT_VERSION.phar" "$PHPUNIT_SHA256" "$PHPUNIT_GPG_FINGERPRINT"; \
    rm -rf /tmp/gnupg /tmp/keys /tmp/*

FROM debian:13-slim

# COMPOSER_DISABLE_NETWORK=1 : Composer nunca usa la red salvo que se pida
# (-e COMPOSER_DISABLE_NETWORK=0). COMPOSER_NO_AUDIT=1 : "composer audit" contacta Packagist.
# PHP y Composer no tienen telemetria.
ENV PATH=/opt/php/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PHP_HOME=/opt/php \
    COMPOSER_HOME=/var/lib/gordus-php/composer \
    COMPOSER_CACHE_DIR=/var/lib/gordus-php/composer-cache \
    COMPOSER_DISABLE_NETWORK=1 \
    COMPOSER_NO_AUDIT=1 \
    COMPOSER_NO_INTERACTION=1 \
    COMPOSER_ALLOW_SUPERUSER=0 \
    LANG=C.UTF-8 \
    GORDUS_PHP_WORK=/workspace

# Bibliotecas que necesita el binario php, fijadas por version exacta de Debian 13.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates=20250419+deb13u1 \
       libonig5=6.9.9-1+b1 \
       libssl3t64=3.5.7-1~deb13u3 \
       libxml2=2.12.7+dfsg+really2.9.14-2.1+deb13u3 \
       zlib1g=1:1.3.dfsg+really1.3.1-1+b1 \
    && rm -rf /var/lib/apt/lists/* \
    && if command -v python3 || command -v python || command -v curl || command -v wget; then \
         echo "BLOCKED: la imagen final no debe traer Python ni curl/wget" >&2; exit 3; fi

COPY --from=php-build /opt/php /opt/php
COPY --from=php-tools-fetch /out/composer.phar /opt/php/bin/composer
COPY --from=php-tools-fetch /out/phpunit.phar /opt/php/bin/phpunit
COPY toolchains/php/php-gordus.ini /opt/php/etc/conf.d/90-gordus.ini

RUN chown -R root:root /opt/php \
    && chmod -R go-w /opt/php \
    && groupadd --system phpuser \
    && useradd --system --gid phpuser --home-dir /home/phpuser --create-home phpuser \
    && install -d -o phpuser -g phpuser /workspace /var/lib/gordus-php \
       /var/lib/gordus-php/composer /var/lib/gordus-php/composer-cache

WORKDIR /opt/gordus-php
COPY toolchains/php/components.json /opt/gordus-php/components.json
COPY toolchains/php/examples /opt/gordus-php/examples
COPY toolchains/php/tests /opt/gordus-php/tests
RUN chown -R root:root /opt/gordus-php \
    && chmod -R a=rX /opt/gordus-php

USER phpuser
RUN php --version && php -r 'exit(PHP_VERSION_ID >= 80512 ? 0 : 3);' && composer --version && phpunit --version
WORKDIR /workspace
CMD ["bash"]
