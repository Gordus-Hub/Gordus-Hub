# Ejemplo: se ejecuta con  julia --project=. hola.jl
using Saludo

println(saludar("Gordus-Hub"))
println("Suma 1..10 = ", suma_hasta(10))
println("Pares al reves: ", join(pares_al_reves(10), " "))
println("Resultado: 10/2 = ", dividir(10, 2), ", 1/0 -> ", dividir(1, 0))
