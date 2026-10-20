// Ejemplo de TypeScript de Gordus-Hub: tipos, Result sin excepciones y modulos ES.

// Declaracion minima de "process" para no depender de @types/node (sin paquetes extra).
declare const process: { argv: string[] };

export type Resultado<T> = { ok: true; valor: T } | { ok: false; error: string };

export function sumaHasta(n: number): number {
  let total = 0;
  for (let i = 1; i <= n; i++) {
    total += i;
  }
  return total;
}

export function dividir(a: number, b: number): Resultado<number> {
  if (b === 0) {
    return { ok: false, error: "division por cero" };
  }
  return { ok: true, valor: a / b };
}

export function pares(hasta: number): number[] {
  return Array.from({ length: hasta }, (_, i) => i + 1)
    .filter((x) => x % 2 === 0)
    .reverse();
}

export function main(): string[] {
  const bien = dividir(10, 2);
  const mal = dividir(1, 0);
  return [
    "Hola, Gordus-Hub!",
    `Suma 1..10 = ${sumaHasta(10)}`,
    `Pares al reves: ${pares(10).join(" ")}`,
    `Resultado: 10/2 = ${bien.ok ? bien.valor : "?"}, 1/0 -> ${mal.ok ? "?" : mal.error}`,
  ];
}

if (import.meta.url === `file://${process.argv[1]}`) {
  for (const linea of main()) {
    console.log(linea);
  }
}
