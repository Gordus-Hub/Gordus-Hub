// Ejemplo de Kotlin para Gordus-Hub: funciones simples + main.
fun saludo(nombre: String = "Gordus-Hub"): String = "Hola, $nombre!"

fun suma(hasta: Int): Int = (1..hasta).sum()

fun paresAlReves(hasta: Int): List<Int> = (1..hasta).filter { it % 2 == 0 }.reversed()

fun main(args: Array<String>) {
    println(saludo(args.firstOrNull() ?: "Gordus-Hub"))
    println("Suma 1..10 = ${suma(10)}")
    println("Pares al reves: ${paresAlReves(10)}")
    println("Kotlin ${KotlinVersion.CURRENT} en Java ${Runtime.version().feature()}")
}
