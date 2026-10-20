// Pruebas con el runner integrado de Node (node:test), sobre el JS compilado por tsc.
import { test } from "node:test";
import assert from "node:assert/strict";
import { sumaHasta, dividir, pares, main } from "../dist/hola.js";

test("suma de 1 a 10 es 55", () => {
  assert.equal(sumaHasta(10), 55);
});

test("dividir por cero devuelve un error, no una excepcion", () => {
  assert.deepEqual(dividir(10, 2), { ok: true, valor: 5 });
  assert.deepEqual(dividir(1, 0), { ok: false, error: "division por cero" });
});

test("pares al reves", () => {
  assert.deepEqual(pares(10), [10, 8, 6, 4, 2]);
});

test("main devuelve 4 lineas", () => {
  assert.equal(main().length, 4);
});
