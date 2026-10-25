// Ejemplo minimo de C# 14 sobre .NET 10 para Gordus-Hub.
namespace Gordus.Hola;

public static class Saludo
{
    public static string Hola(string nombre) => $"Hola, {nombre}!";

    public static int Suma(int desde, int hasta) =>
        Enumerable.Range(desde, hasta - desde + 1).Sum();

    public static string ParesAlReves(int hasta) =>
        string.Join(' ', Enumerable.Range(1, hasta).Where(n => n % 2 == 0).Reverse());

    public static bool Dividir(int a, int b, out int resultado)
    {
        if (b == 0)
        {
            resultado = 0;
            return false;
        }
        resultado = a / b;
        return true;
    }
}

public static class Program
{
    public static int Main(string[] args)
    {
        string nombre = args.Length > 0 ? args[0] : "Gordus-Hub";
        Console.WriteLine(Saludo.Hola(nombre));
        Console.WriteLine($"Suma 1..10 = {Saludo.Suma(1, 10)}");
        Console.WriteLine($"Pares al reves: {Saludo.ParesAlReves(10)}");
        string cero = Saludo.Dividir(1, 0, out _) ? "?" : "division por cero";
        Saludo.Dividir(10, 2, out int r);
        Console.WriteLine($"Resultado: 10/2 = {r}, 1/0 -> {cero}");
        Console.WriteLine($".NET {Environment.Version}");
        return 0;
    }
}
