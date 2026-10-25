<?php

declare(strict_types=1);

namespace Gordus\Hola\Tests;

use Gordus\Hola\Saludo;
use PHPUnit\Framework\TestCase;

final class SaludoTest extends TestCase
{
    public function testHola(): void
    {
        $this->assertSame('Hola, Gordus-Hub!', Saludo::hola('Gordus-Hub'));
    }

    public function testSuma(): void
    {
        $this->assertSame(55, Saludo::suma(1, 10));
    }

    public function testParesAlReves(): void
    {
        $this->assertSame([10, 8, 6, 4, 2], Saludo::paresAlReves(10));
    }

    public function testDivisionPorCero(): void
    {
        $this->assertSame('1/0 -> division por cero', Saludo::dividir(1, 0));
    }
}
