// Ejemplo minimo para comprobar el toolchain Go del Gordus-Hub.
// Ejecutar:  go run .        Compilar:  go build -o hola .  &&  ./hola
package main

import (
	"fmt"
	"runtime"
	"strings"
)

// Saludo arma el mensaje de bienvenida.
func Saludo(nombre string) string {
	return "Hola, " + nombre + "!"
}

// SumaHasta suma los numeros de 1 a n.
func SumaHasta(n int) int {
	total := 0
	for i := 1; i <= n; i++ {
		total += i
	}
	return total
}

func main() {
	fmt.Println(Saludo("Gordus-Hub"))
	fmt.Println("Suma 1..10 =", SumaHasta(10))
	fmt.Println("Go", strings.TrimPrefix(runtime.Version(), "go"), runtime.GOOS+"/"+runtime.GOARCH)
}
