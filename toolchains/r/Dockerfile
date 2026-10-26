# Gordus-Hub - R toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/,
# toolchains/cpp/, toolchains/rust/, toolchains/node/, toolchains/dotnet/, toolchains/swift/,
# toolchains/kotlin/, toolchains/scala/, toolchains/php/, toolchains/ruby/ ni .devcontainer/.
# Fuente oficial: https://cran.r-project.org/src/base/R-4 (codigo fuente, se compila aqui).
# CRAN no publica firmas GPG del tarball de R ni de los paquetes fuente: R se verifica con
# SHA-256 (igual en dos espejos oficiales) y SHA-512; cada paquete de toolchains/r/packages.lock
# con su SHA-256 (comprobado contra el MD5sum del indice oficial de CRAN).
# Cualquier cambio de version debe actualizar tambien toolchains/r/components.json;
# toolchains/r/scripts/validate_r_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS r-build

ARG DEBIAN_FRONTEND=noninteractive
ARG R_VERSION=4.6.1
ARG R_URL_BASE=https://cran.r-project.org/src/base/R-4
ARG R_SHA256=4da6e61d2c0aac5f14a2e7e432cb5fcc269efe83da4293050ba7f03dff4e2cf4
ARG R_SHA512=2f40e7e0b5808052bb177c9cdac8045a365a42835bb98e183421282dfd3ba8cbdc13e4efccf7753c0ba0faed1f289a77697ae1fe1659bca1fb54008f8b9d98d2
ARG CRAN_URL=https://cran.r-project.org/src/contrib

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
       gcc g++ gfortran make cmake perl file libc6-dev libreadline-dev libpcre2-dev libbz2-dev \
       liblzma-dev zlib1g-dev libcurl4-openssl-dev libzstd-dev \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    file="R-$R_VERSION.tar.gz"; cd /tmp; \
    curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o "$file" "$R_URL_BASE/$file"; \
    echo "$R_SHA256  $file" | sha256sum -c -; \
    echo "$R_SHA512  $file" | sha512sum -c -; \
    install -d /usr/src/r; \
    tar -xzf "$file" -C /usr/src/r --strip-components=1 --no-same-owner; \
    rm -f "$file"

RUN set -eu; cd /usr/src/r; \
    ./configure --prefix=/opt/r --without-x --with-readline --without-recommended-packages \
       --disable-java --without-tcltk --without-cairo --without-libpng --without-jpeglib \
       --without-libtiff --without-ICU --disable-nls --enable-R-shlib=no > /tmp/configure.log; \
    make -j"$(nproc)" > /tmp/make.log 2>&1; \
    make install > /tmp/install.log; \
    rm -rf /usr/src/r /tmp/*.log /opt/r/share/man; \
    test "$(/opt/r/bin/Rscript -e 'cat(as.character(getRversion()))')" = "$R_VERSION"

# Repositorio local tipo CRAN (offline) con los paquetes fijados y verificados por SHA-256.
COPY toolchains/r/packages.lock /tmp/packages.lock
RUN set -eu; repo=/opt/gordus-r/repo/src/contrib; install -d "$repo"; cd "$repo"; \
    grep -v '^#' /tmp/packages.lock | while read -r name ver sum; do \
      f="${name}_${ver}.tar.gz"; \
      curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o "$f" "$CRAN_URL/$f" \
        || curl --fail --silent --show-error --proto '=https' --tlsv1.2 -o "$f" "$CRAN_URL/Archive/$name/$f"; \
      echo "$sum  $f" | sha256sum -c -; \
    done; \
    test "$(ls | wc -l)" = "$(grep -vc '^#' /tmp/packages.lock)"; \
    /opt/r/bin/Rscript -e 'tools::write_PACKAGES(".", type = "source")'

# fs usa su libuv incluido (dentro del tarball verificado): no hace falta libuv en la imagen final.
RUN set -eu; install -d /opt/r-site-library; \
    USE_BUNDLED_LIBUV=1 MAKEFLAGS="-j$(nproc)" /opt/r/bin/Rscript -e ' \
      pk <- read.table("/tmp/packages.lock", comment.char = "#", col.names = c("p", "v", "s")); \
      install.packages(pk$p, lib = "/opt/r-site-library", repos = "file:///opt/gordus-r/repo", \
                       type = "source", dependencies = FALSE, Ncpus = 1); \
      ip <- installed.packages("/opt/r-site-library")[, "Version"]; \
      bad <- pk$p[ip[pk$p] != pk$v | is.na(ip[pk$p])]; \
      if (length(bad)) { message("FAILED: ", paste(bad, collapse = " ")); quit(status = 4) }'; \
    find /opt/r-site-library -name '*.so' -exec strip --strip-unneeded {} +; \
    rm -rf /opt/r-site-library/*/help /opt/r-site-library/*/doc /opt/r-site-library/*/html; \
    chown -R root:root /opt/r /opt/r-site-library /opt/gordus-r; \
    chmod -R go-w /opt/r /opt/r-site-library /opt/gordus-r

FROM debian:13-slim

# Sin red por defecto: install.packages() y renv solo ven el repositorio local
# file:///opt/gordus-r/repo; los paquetes nuevos van a R_LIBS_USER (escribible), nunca a /opt.
# R, testthat y renv no tienen telemetria (renv: chequeo de actualizaciones apagado).
ENV PATH=/opt/r/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    R_HOME_DIR=/opt/r \
    R_LIBS_SITE=/opt/r-site-library \
    R_LIBS_USER=/var/lib/gordus-r/library \
    R_PROFILE=/opt/gordus-r/rprofile.site \
    RENV_PATHS_ROOT=/var/lib/gordus-r/renv \
    RENV_CONFIG_UPDATES_CHECK=FALSE \
    LANG=C.UTF-8 \
    GORDUS_R_WORK=/workspace

# Bibliotecas que necesita R, fijadas por version exacta de Debian 13.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates=20250419+deb13u1 \
       libbz2-1.0=1.0.8-6 \
       libcurl4t64=8.14.1-2+deb13u7 \
       libgfortran5=14.2.0-19 \
       libgomp1=14.2.0-19 \
       liblzma5=5.8.1-1+deb13u2 \
       libpcre2-8-0=10.46-1~deb13u3 \
       libreadline8t64=8.2-6 \
       libzstd1=1.5.7+dfsg-1 \
       zlib1g=1:1.3.dfsg+really1.3.1-1+b1 \
    && rm -rf /var/lib/apt/lists/* \
    && if command -v python3 || command -v python || command -v curl || command -v wget; then \
         echo "BLOCKED: la imagen final no debe traer Python ni curl/wget" >&2; exit 3; fi

COPY --from=r-build /opt/r /opt/r
COPY --from=r-build /opt/r-site-library /opt/r-site-library
COPY --from=r-build /opt/gordus-r/repo /opt/gordus-r/repo

RUN groupadd --system ruser \
    && useradd --system --gid ruser --home-dir /home/ruser --create-home ruser \
    && install -d -o ruser -g ruser /workspace /var/lib/gordus-r \
       /var/lib/gordus-r/library /var/lib/gordus-r/renv

WORKDIR /opt/gordus-r
COPY toolchains/r/components.json /opt/gordus-r/components.json
COPY toolchains/r/packages.lock /opt/gordus-r/packages.lock
COPY toolchains/r/rprofile.site /opt/gordus-r/rprofile.site
COPY toolchains/r/examples /opt/gordus-r/examples
COPY toolchains/r/tests /opt/gordus-r/tests
RUN chown -R root:root /opt/gordus-r \
    && chmod -R a=rX /opt/gordus-r

USER ruser
RUN R --version | head -n 1 && Rscript -e 'cat(format(packageVersion("testthat")), format(packageVersion("renv")), "\n")'
WORKDIR /workspace
CMD ["bash"]
