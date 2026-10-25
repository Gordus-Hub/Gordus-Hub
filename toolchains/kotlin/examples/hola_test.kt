// Pruebas del ejemplo con kotlin.test (viene incluido con kotlinc, sin descargas).
import kotlin.test.assertEquals

fun main() {
    val pruebas = listOf(
        "saludo" to { assertEquals("Hola, Mundo!", saludo("Mundo")) },
        "suma" to { assertEquals(55, suma(10)) },
        "pares" to { assertEquals(listOf(10, 8, 6, 4, 2), paresAlReves(10)) },
    )
    for ((nombre, prueba) in pruebas) {
        prueba()
        println("ok: $nombre")
    }
    println("Tests: ${pruebas.size} OK, 0 fallos")
}
