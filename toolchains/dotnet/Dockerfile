# Gordus-Hub - .NET 10 SDK (C#) toolchain - imagen aislada.
# No comparte nada con ai/ (Python), toolchains/java/, toolchains/mojo/, toolchains/go/,
# toolchains/cpp/, toolchains/rust/, toolchains/node/, toolchains/swift/ ni .devcontainer/.
# Fuente oficial fijada: SDK binario de Microsoft (builds.dotnet.microsoft.com), version exacta.
# Verificacion: SHA-512 fijado aqui, copiado de releases.json oficial
# (https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json).
# El workflow vuelve a comparar estos hashes con releases.json en cada corrida (pins-preflight).
# Cualquier cambio de version debe actualizar tambien toolchains/dotnet/components.json;
# toolchains/dotnet/scripts/validate_dotnet_toolchain.py falla cerrado si no coinciden.

FROM debian:13-slim AS dotnet-fetch

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ARG DOTNET_SDK_VERSION=10.0.402
ARG DOTNET_RUNTIME_VERSION=10.0.13
ARG DOTNET_URL_BASE=https://builds.dotnet.microsoft.com/dotnet/Sdk
ARG DOTNET_SHA512_AMD64=1904a98dda2db34ba78ba3c4fb1b224455329af91c341d83547843c1839e112b04ae699ee92fa2449a8f62249196a938723078c0c60b9f65c88539d5687729c2
ARG DOTNET_SHA512_ARM64=db85ae85527251fbb1290720ac3bf324bb1d9eea74516ef291ed4bb1f8ff6ec63a17593367f49b456115e8b24ead6d0c2ece2801e501f36a6cd4444ed01a498f

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) rid=x64; sha="$DOTNET_SHA512_AMD64" ;; \
      arm64) rid=arm64; sha="$DOTNET_SHA512_ARM64" ;; \
      *) echo "BLOCKED: arquitectura no aprobada: $arch" >&2; exit 3 ;; \
    esac; \
    file="dotnet-sdk-$DOTNET_SDK_VERSION-linux-$rid.tar.gz"; cd /tmp; \
    curl --fail --location --silent --show-error --proto '=https' --tlsv1.2 -o "$file" \
      "$DOTNET_URL_BASE/$DOTNET_SDK_VERSION/$file"; \
    echo "$sha  $file" | sha512sum -c -; \
    install -d /usr/share/dotnet; \
    tar -xzf "$file" -C /usr/share/dotnet --no-same-owner; \
    rm -f "$file"; \
    test -d "/usr/share/dotnet/sdk/$DOTNET_SDK_VERSION"; \
    test -d "/usr/share/dotnet/shared/Microsoft.NETCore.App/$DOTNET_RUNTIME_VERSION"; \
    chown -R root:root /usr/share/dotnet; \
    chmod -R go-w /usr/share/dotnet

FROM debian:13-slim

# Telemetria apagada, sin logo, sin "first time experience", sin aviso de workloads.
# NuGet: cache de paquetes escribible en /var/lib/gordus-dotnet; sin fuentes remotas
# (NuGet.Config del usuario con <clear/>), asi la restauracion es offline por defecto.
ENV DOTNET_ROOT=/usr/share/dotnet \
    PATH=/usr/share/dotnet:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_NOLOGO=1 \
    DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1 \
    DOTNET_GENERATE_ASPNET_CERTIFICATE=false \
    DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE=1 \
    DOTNET_ADD_GLOBAL_TOOLS_TO_PATH=0 \
    DOTNET_CLI_HOME=/var/lib/gordus-dotnet/cli-home \
    NUGET_PACKAGES=/var/lib/gordus-dotnet/nuget/packages \
    NUGET_HTTP_CACHE_PATH=/var/lib/gordus-dotnet/nuget/http-cache \
    NUGET_XMLDOC_MODE=skip \
    LANG=C.UTF-8 \
    GORDUS_DOTNET_WORK=/workspace

# Dependencias nativas del runtime .NET, fijadas por version exacta de Debian 13.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates=20250419+deb13u1 \
       libicu76=76.1-4 \
       libssl3t64=3.5.7-1~deb13u3 \
       tzdata=2026e-0+deb13u1 \
    && rm -rf /var/lib/apt/lists/* \
    && if command -v python3 || command -v python || command -v curl || command -v wget; then \
         echo "BLOCKED: la imagen final no debe traer Python ni curl/wget" >&2; exit 3; fi

COPY --from=dotnet-fetch /usr/share/dotnet /usr/share/dotnet

RUN groupadd --system dotnetuser \
    && useradd --system --gid dotnetuser --home-dir /home/dotnetuser --create-home dotnetuser \
    && install -d -o dotnetuser -g dotnetuser /workspace /var/lib/gordus-dotnet \
       /var/lib/gordus-dotnet/cli-home /var/lib/gordus-dotnet/nuget \
       /var/lib/gordus-dotnet/nuget/packages /var/lib/gordus-dotnet/nuget/http-cache \
    && install -d -m 0755 /home/dotnetuser/.nuget /home/dotnetuser/.nuget/NuGet \
    && printf '%s\n' '<?xml version="1.0" encoding="utf-8"?>' '<configuration>' \
       '  <packageSources>' '    <clear />' '  </packageSources>' '</configuration>' \
       > /home/dotnetuser/.nuget/NuGet/NuGet.Config \
    && chmod 0444 /home/dotnetuser/.nuget/NuGet/NuGet.Config

WORKDIR /opt/gordus-dotnet
COPY toolchains/dotnet/components.json /opt/gordus-dotnet/components.json
COPY toolchains/dotnet/examples /opt/gordus-dotnet/examples
COPY toolchains/dotnet/tests /opt/gordus-dotnet/tests
RUN chown -R root:root /opt/gordus-dotnet /home/dotnetuser/.nuget \
    && chmod -R a=rX /opt/gordus-dotnet

USER dotnetuser
RUN dotnet --version && dotnet --list-sdks
WORKDIR /workspace
CMD ["bash"]
