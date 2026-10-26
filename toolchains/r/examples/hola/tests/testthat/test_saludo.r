# Pruebas con testthat: Rscript -e 'testthat::test_dir("tests/testthat")'
source(file.path("..", "..", "saludo.r"))

test_that("saludar arma el saludo", {
  expect_equal(saludar("Gordus-Hub"), "Hola, Gordus-Hub!")
  expect_error(saludar(""))
})

test_that("suma_hasta suma de 1 a n", {
  expect_equal(suma_hasta(10), 55)
})

test_that("pares_al_reves devuelve los pares de mayor a menor", {
  expect_equal(pares_al_reves(10), c(10, 8, 6, 4, 2))
})

test_that("dividir rechaza la division por cero", {
  expect_equal(dividir(10, 2), 5)
  expect_error(dividir(1, 0), "division por cero")
})
