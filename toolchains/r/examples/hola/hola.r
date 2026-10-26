# Ejemplo de R: Rscript hola.r
source("saludo.r")
cat(saludar("Gordus-Hub"), "\n", sep = "")
cat("Suma 1..10 = ", suma_hasta(10), "\n", sep = "")
cat("Pares al reves: ", paste(pares_al_reves(10), collapse = " "), "\n", sep = "")
r <- tryCatch(dividir(1, 0), error = function(e) conditionMessage(e))
cat("Resultado: 10/2 = ", dividir(10, 2), ", 1/0 -> ", r, "\n", sep = "")
