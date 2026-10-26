module Saludo

using Printf

export saludar, suma_hasta, pares_al_reves, dividir

"Devuelve un saludo para `nombre`."
saludar(nombre::AbstractString) = "Hola, $(nombre)!"

"Suma los numeros de 1 a `n`."
suma_hasta(n::Integer) = sum(1:n)

"Numeros pares de 1 a `n`, de mayor a menor."
pares_al_reves(n::Integer) = reverse(filter(iseven, 1:n))

"Divide `a` por `b`; devuelve un texto amable si `b` es cero."
function dividir(a::Integer, b::Integer)
    b == 0 && return "division por cero"
    return @sprintf("%d", div(a, b))
end

end # module
