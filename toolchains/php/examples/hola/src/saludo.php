<?php

declare(strict_types=1);

namespace Gordus\Hola;

final class Saludo
{
    public static function hola(string $nombre): string
    {
        return "Hola, {$nombre}!";
    }

    public static function suma(int $desde, int $hasta): int
    {
        return array_sum(range($desde, $hasta));
    }

    /** @return list<int> */
    public static function paresAlReves(int $hasta): array
    {
        return array_values(array_reverse(array_filter(range(1, $hasta), fn (int $n): bool => $n % 2 === 0)));
    }

    public static function dividir(int $a, int $b): string
    {
        if ($b === 0) {
            return "{$a}/{$b} -> division por cero";
        }
        return "{$a}/{$b} = " . intdiv($a, $b);
    }
}
