// Ejemplo de Scala 3 para Gordus-Hub: funciones simples + punto de entrada @main.
object HolaCore:
  def saludo(nombre: String = "Gordus-Hub"): String = s"Hola, $nombre!"
  def suma(hasta: Int): Int = (1 to hasta).sum
  def paresAlReves(hasta: Int): List[Int] = (1 to hasta).filter(_ % 2 == 0).reverse.toList

@main def hola(args: String*): Unit =
  println(HolaCore.saludo(args.headOption.getOrElse("Gordus-Hub")))
  println(s"Suma 1..10 = ${HolaCore.suma(10)}")
  println(s"Pares al reves: ${HolaCore.paresAlReves(10).mkString("[", ", ", "]")}")
  println(s"Scala 3 en Java ${Runtime.version().feature()}")
