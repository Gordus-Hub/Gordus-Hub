# Toolchain .NET 10 (C#) de Gordus-Hub

Imagen Docker **aislada** con el SDK oficial de **.NET 10 LTS** de Microsoft. Trae:

- el comando `dotnet` (CLI),
- el compilador de **C# 14** (Roslyn),
- MSBuild y el cliente **NuGet**.

No comparte nada con Python (`ai/`), Java, Mojo, Go, C++, Rust, Node, Swift ni `.devcontainer/`.
Estado: **candidato, sin certificar** (`certification: NOT_GRANTED`).

## Por que la carpeta se llama `dotnet/`

Seguimos la regla del repo: la carpeta lleva el nombre de la herramienta, igual que `go/`, `rust/`
y `node/`. La herramienta es `dotnet`. Ademas el mismo SDK sirve para F# y VB, no solo para C#.

## Versiones fijadas

| Componente | Version | Licencia |
|---|---|---|
| .NET SDK | 10.0.402 | MIT |
| Runtime .NET (Microsoft.NETCore.App) | 10.0.13 | MIT |
| Lenguaje C# | 14.0 | MIT |
| Imagen base | debian:13-slim | — |
| libicu76 / libssl3t64 / ca-certificates / tzdata | 76.1-4 / 3.5.7-1~deb13u3 / 20250419+deb13u1 / 2026e-0+deb13u1 | varias (Debian) |

El SDK se baja de `builds.dotnet.microsoft.com`. Antes de instalarlo se comprueba su **SHA-512**
(`sha512sum -c`). Ese hash es el que publica Microsoft en su `releases.json` oficial:
<https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json>.
El workflow vuelve a comparar los hashes con ese archivo en cada corrida.
Hay un hash para amd64 (PC comunes) y otro para arm64 (Raspberry Pi 4/5, Mac M1+ con Docker).

## Reglas de seguridad (fallan cerrado)

- **Telemetria apagada**: `DOTNET_CLI_TELEMETRY_OPTOUT=1`. Tambien `DOTNET_NOLOGO=1` y
  `DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1`.
- **NuGet sin internet**: no hay fuentes remotas (`<clear />`). Nunca se baja nada de nuget.org.
- **Sin paquetes externos**: los proyectos no usan `PackageReference`.
- **Lock files**: cada proyecto tiene su `packages.lock.json`, y se restaura con `RestoreLockedMode`.
  Si el lock no coincide con el proyecto, la restauracion falla.
- **Carpeta de NuGet escribible** en `/var/lib/gordus-dotnet/nuget/packages`.
- Corre como el usuario **`dotnetuser`**, no como root.
- El codigo en `/opt/gordus-dotnet` y el SDK en `/usr/share/dotnet` son **de solo lectura**.
- La imagen final **no trae python, curl ni wget**. Si aparecen, el build se corta.

## Archivos

```
toolchains/dotnet/
├── Dockerfile                         imagen en 2 etapas (descarga+verificacion / final)
├── README.md                          este archivo
├── components.json                    registro de versiones, hashes y politica
├── examples/hola/
│   ├── Directory.Build.props          opciones comunes (net10.0, lock files, warnings = error)
│   ├── nuget.config                   sin fuentes remotas
│   ├── Hola/Hola.csproj               programa de ejemplo
│   ├── Hola/Program.cs
│   ├── Hola/packages.lock.json
│   ├── Hola.Tests/Hola.Tests.csproj   auto-chequeo (sin xUnit: necesitaria nuget.org)
│   ├── Hola.Tests/Program.cs
│   └── Hola.Tests/packages.lock.json
├── tests/test_dotnet_toolchain.sh     prueba de humo
├── scripts/validate_dotnet_toolchain.py  validador (solo Python estandar)
└── kestra/dotnet_toolchain_smoke.yaml flujo Kestra que da el visto bueno o falla
```

Ojo con las mayusculas: Linux las distingue. `Program.cs`, `Hola.csproj`, `Hola/` y `Hola.Tests/`
llevan mayuscula; el resto va en minusculas. El validador revisa los nombres exactos.

## Como usarlo (paso a paso)

1. Construir la imagen, desde la raiz del repo:
   ```sh
   docker build -f toolchains/dotnet/Dockerfile -t gordus-dotnet .
   ```
2. Correr la prueba de humo sin red:
   ```sh
   docker run --rm --network none gordus-dotnet sh /opt/gordus-dotnet/tests/test_dotnet_toolchain.sh
   ```
   Al final tiene que decir `PASS: toolchain .NET SDK 10.0.402 ...`.
3. Validar los archivos (no hace falta Docker):
   ```sh
   python3 toolchains/dotnet/scripts/validate_dotnet_toolchain.py --repo-root .
   ```
4. Probar tu propio codigo C#:
   ```sh
   docker run --rm -it --network none gordus-dotnet bash
   dotnet new console -o mi-app && cd mi-app
   dotnet run
   ```

## Que verifica la prueba de humo

1. `dotnet --version` es 10.0.402, el runtime es 10.0.13 y `dotnet --info` funciona.
2. `dotnet restore --locked-mode` funciona sin red y no cambia los lock files.
3. `dotnet build` en Release, con los warnings tratados como errores.
4. `dotnet run` imprime el saludo esperado.
5. El auto-chequeo (`Hola.Tests`) pasa 6 de 6.
6. Negativos (cosas que **tienen que fallar**):
   - codigo con un error de tipos (CS0029);
   - agregar un paquete de NuGet externo;
   - un lock file desincronizado.

Codigos de salida: `0` ok, `2` entrada invalida, `3` bloqueado, `4` fallo.

## Licencia

El SDK de .NET es **MIT** (`/usr/share/dotnet/LICENSE.txt`). Los archivos de esta carpeta siguen la
licencia del repositorio.
