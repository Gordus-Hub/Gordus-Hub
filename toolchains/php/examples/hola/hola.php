<?php

declare(strict_types=1);

require __DIR__ . '/vendor/autoload.php';

use Gordus\Hola\Saludo;

echo Saludo::hola('Gordus-Hub'), PHP_EOL;
echo 'Suma 1..10 = ', Saludo::suma(1, 10), PHP_EOL;
echo 'Pares al reves: ', implode(' ', Saludo::paresAlReves(10)), PHP_EOL;
echo 'Resultado: ', Saludo::dividir(10, 2), ', ', Saludo::dividir(1, 0), PHP_EOL;
