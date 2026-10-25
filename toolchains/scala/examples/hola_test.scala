// Pruebas del ejemplo sin bibliotecas externas (sin descargas): assert de Scala.
@main def holaTest(): Unit =
  val pruebas: List[(String, () => Unit)] = List(
    "saludo" -> (() => assert(HolaCore.saludo("Mundo") == "Hola, Mundo!")),
    "suma" -> (() => assert(HolaCore.suma(10) == 55)),
    "pares" -> (() => assert(HolaCore.paresAlReves(10) == List(10, 8, 6, 4, 2)))
  )
  for (nombre, prueba) <- pruebas do
    prueba()
    println(s"ok: $nombre")
  println(s"Tests: ${pruebas.size} OK, 0 fallos")
