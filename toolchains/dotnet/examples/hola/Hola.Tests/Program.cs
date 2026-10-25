// Auto-chequeo del ejemplo: sale con codigo 0 si todo pasa, 1 si algo falla.
using Gordus.Hola;

namespace Gordus.Hola.Tests;

public static class Program
{
    private static int fallas;

    private static void Verificar(string nombre, bool ok)
    {
        Console.WriteLine($"{(ok ? "ok  " : "FAIL")} {nombre}");
        if (!ok) fallas++;
    }

    public static int Main()
    {
        Verificar("Hola", Saludo.Hola("Gordus-Hub") == "Hola, Gordus-Hub!");
        Verificar("Suma 1..10", Saludo.Suma(1, 10) == 55);
        Verificar("Pares al reves", Saludo.ParesAlReves(10) == "10 8 6 4 2");
        Verificar("Dividir 10/2", Saludo.Dividir(10, 2, out int r) && r == 5);
        Verificar("Dividir por cero", !Saludo.Dividir(1, 0, out _));
        Verificar(".NET 10", Environment.Version.Major == 10);
        Console.WriteLine(fallas == 0 ? "SELF_CHECK=PASS (6/6)" : $"SELF_CHECK=FAIL ({fallas})");
        return fallas == 0 ? 0 : 1;
    }
}
