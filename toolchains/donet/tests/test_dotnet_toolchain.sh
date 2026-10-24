#!/bin/sh
# Prueba de humo del toolchain .NET 10 / C# (POSIX sh).
# dotnet --info/--version, restore offline en modo bloqueado (packages.lock.json),
# build, run, auto-chequeo, error de compilacion detectado y reglas fail-closed.
# Codigos de salida: 0 ok, 2 entrada invalida, 3 bloqueado, 4 fallo.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="${DOTNET_EXAMPLE_DIR:-$here/../examples/hola}"
expected_sdk="${EXPECTED_DOTNET_SDK_VERSION:-10.0.402}"
expected_rt="${EXPECTED_DOTNET_RUNTIME_VERSION:-10.0.13}"

for f in Directory.Build.props nuget.config Hola/Hola.csproj Hola/Program.cs Hola/packages.lock.json \
         Hola.Tests/Hola.Tests.csproj Hola.Tests/Program.cs Hola.Tests/packages.lock.json; do
    if [ ! -f "$src/$f" ]; then
        echo "BAD_INPUT: no existe $src/$f (ojo con mayusculas/minusculas)" >&2; exit 2
    fi
done
command -v dotnet >/dev/null 2>&1 || { echo "BLOCKED: falta 'dotnet' en PATH" >&2; exit 3; }
for bad in python3 python curl wget; do
    if command -v "$bad" >/dev/null 2>&1; then echo "BLOCKED: '$bad' no debe estar en la imagen" >&2; exit 3; fi
done
[ "${DOTNET_CLI_TELEMETRY_OPTOUT:-}" = 1 ] || { echo "BLOCKED: la telemetria debe estar apagada" >&2; exit 3; }
[ "${DOTNET_NOLOGO:-}" = 1 ] || { echo "BLOCKED: DOTNET_NOLOGO debe ser 1" >&2; exit 3; }
[ "${DOTNET_SKIP_FIRST_TIME_EXPERIENCE:-}" = 1 ] || { echo "BLOCKED: DOTNET_SKIP_FIRST_TIME_EXPERIENCE debe ser 1" >&2; exit 3; }
case "${NUGET_PACKAGES:-}" in /var/lib/gordus-dotnet/*) ;; *) echo "BLOCKED: NUGET_PACKAGES fuera de /var/lib/gordus-dotnet" >&2; exit 3 ;; esac

sdk_v=$(dotnet --version)
echo "dotnet sdk $sdk_v"
[ "$sdk_v" = "$expected_sdk" ] || { echo "FAILED: el SDK no es $expected_sdk" >&2; exit 4; }
dotnet --list-runtimes | grep -q "^Microsoft.NETCore.App $expected_rt " \
    || { echo "FAILED: falta el runtime Microsoft.NETCore.App $expected_rt" >&2; exit 4; }
echo "dotnet runtime $expected_rt"
dotnet --info > /dev/null || { echo "FAILED: dotnet --info" >&2; exit 4; }
echo "dotnet --info OK"

work=$(mktemp -d "${TMPDIR:-/tmp}/gordus-dotnet-test.XXXXXX")
trap 'rm -rf "$work"' EXIT INT TERM
cp -R "$src" "$work/hola"
chmod -R u+w "$work/hola"
cd "$work/hola"
rm -rf Hola/bin Hola/obj Hola.Tests/bin Hola.Tests/obj

# 1) restore offline en modo bloqueado: los packages.lock.json no deben cambiar
lock_before=$(cksum Hola/packages.lock.json Hola.Tests/packages.lock.json)
dotnet restore Hola.Tests/Hola.Tests.csproj --locked-mode || { echo "FAILED: dotnet restore --locked-mode" >&2; exit 4; }
[ "$(cksum Hola/packages.lock.json Hola.Tests/packages.lock.json)" = "$lock_before" ] \
    || { echo "FAILED: restore modifico packages.lock.json" >&2; exit 4; }
echo "restore --locked-mode OK"

# 2) build (Release, warnings como errores)
dotnet build Hola.Tests/Hola.Tests.csproj -c Release --no-restore -nologo -v q \
    || { echo "FAILED: dotnet build" >&2; exit 4; }
echo "build OK"

# 3) run
want=$(printf 'Hola, Gordus-Hub!\nSuma 1..10 = 55\nPares al reves: 10 8 6 4 2\nResultado: 10/2 = 5, 1/0 -> division por cero\n.NET %s' "$expected_rt")
out=$(dotnet run --project Hola/Hola.csproj -c Release --no-build) || { echo "FAILED: dotnet run" >&2; exit 4; }
echo "$out"
[ "$out" = "$want" ] || { echo "FAILED: salida inesperada de Hola" >&2; exit 4; }
echo "run OK"

# 4) auto-chequeo (sin xUnit/MSTest: requeririan paquetes de NuGet.org)
dotnet Hola.Tests/bin/Release/net10.0/Hola.Tests.dll || { echo "FAILED: self-check" >&2; exit 4; }
echo "self-check OK"

# 5) el compilador C# debe rechazar un error de tipos
mkdir -p bad/Hola && cp Directory.Build.props nuget.config bad/ && cp Hola/Hola.csproj Hola/packages.lock.json bad/Hola/
printf 'int n = "no soy un numero";\nSystem.Console.WriteLine(n);\n' > bad/Hola/Program.cs
if dotnet build bad/Hola/Hola.csproj -nologo > bad/out.txt 2>&1; then
    echo "FAILED: el compilador acepto un error de tipos" >&2; exit 4
fi
grep -q "CS0029" bad/out.txt || { echo "FAILED: no se reporto CS0029" >&2; cat bad/out.txt >&2; exit 4; }
echo "compilador rechaza error de tipos (CS0029): OK"

# 6) Fail-closed: un paquete externo no se puede agregar/restaurar (sin fuentes remotas)
mkdir -p ext/Hola && cp Directory.Build.props nuget.config ext/ && cp Hola/Hola.csproj Hola/Program.cs ext/Hola/
sed -i 's#</Project>#  <ItemGroup><PackageReference Include="Newtonsoft.Json" Version="13.0.3" /></ItemGroup>\n</Project>#' ext/Hola/Hola.csproj
grep -q Newtonsoft ext/Hola/Hola.csproj || { echo "FAILED: no se pudo preparar el negativo" >&2; exit 4; }
if dotnet restore ext/Hola/Hola.csproj -p:RestoreLockedMode=false > ext/out.txt 2>&1; then
    echo "FAILED: se restauro un paquete externo" >&2; exit 4
fi
echo "paquetes externos bloqueados: OK"

# 7) Fail-closed: un lock desincronizado debe fallar en modo bloqueado
mkdir -p lock/Hola && cp Directory.Build.props nuget.config lock/ && cp Hola/Hola.csproj Hola/Program.cs lock/Hola/
printf '{\n  "version": 1,\n  "dependencies": {\n    "net10.0": {\n      "Fake.Package": {\n        "type": "Direct",\n        "requested": "[1.0.0, )",\n        "resolved": "1.0.0"\n      }\n    }\n  }\n}' > lock/Hola/packages.lock.json
if dotnet restore lock/Hola/Hola.csproj > lock/out.txt 2>&1; then
    echo "FAILED: restore acepto un lock desincronizado" >&2; exit 4
fi
echo "lock desincronizado bloqueado: OK"

echo "PASS: toolchain .NET SDK $expected_sdk (runtime $expected_rt, C# 14) (info + restore locked offline + build + run + self-check + negativos) OK"
