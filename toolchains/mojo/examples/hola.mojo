# Ejemplo minimo para comprobar el toolchain Mojo del Gordus-Hub.
# Ejecutar sin compilar:   mojo run hola.mojo
# Compilar a binario:      mojo build hola.mojo -o hola  &&  ./hola


def suma_hasta(n: Int) -> Int:
    var total = 0
    for i in range(1, n + 1):
        total += i
    return total


def main():
    var nombre = "Gordus-Hub"
    print("Hola, " + nombre + "!")
    print("Suma 1..10 =", suma_hasta(10))
