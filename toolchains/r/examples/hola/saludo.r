# Funciones simples del ejemplo (las prueba tests/testthat/test_saludo.r).
saludar <- function(nombre) {
  stopifnot(is.character(nombre), length(nombre) == 1L, nzchar(nombre))
  paste0("Hola, ", nombre, "!")
}

suma_hasta <- function(n) sum(seq_len(n))

pares_al_reves <- function(n) rev(Filter(function(x) x %% 2 == 0, seq_len(n)))

dividir <- function(a, b) {
  if (b == 0) stop("division por cero")
  a / b
}
