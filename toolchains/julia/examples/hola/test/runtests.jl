using Test
using Saludo

@testset "Saludo" begin
    @test saludar("Gordus-Hub") == "Hola, Gordus-Hub!"
    @test suma_hasta(10) == 55
    @test pares_al_reves(10) == [10, 8, 6, 4, 2]
    @test dividir(1, 0) == "division por cero"
end
