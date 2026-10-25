// Logica del ejemplo: se prueba con XCTest en Tests/HolaCoreTests.
public enum DivisionError: Error, Equatable {
    case divisionPorCero
}

public func saludo(_ nombre: String) -> String {
    "Hola, \(nombre)!"
}

public func suma(hasta n: Int) -> Int {
    (1...n).reduce(0, +)
}

public func paresAlReves(hasta n: Int) -> [Int] {
    (1...n).filter { $0 % 2 == 0 }.reversed()
}

public func dividir(_ a: Int, _ b: Int) -> Result<Int, DivisionError> {
    b == 0 ? .failure(.divisionPorCero) : .success(a / b)
}

public func describir(_ r: Result<Int, DivisionError>) -> String {
    switch r {
    case .success(let v): return "\(v)"
    case .failure: return "division por cero"
    }
}

public func lineas() -> [String] {
    [
        saludo("Gordus-Hub"),
        "Suma 1..10 = \(suma(hasta: 10))",
        "Pares al reves: \(paresAlReves(hasta: 10))",
        "Result: 10/2 = \(describir(dividir(10, 2))), 1/0 -> \(describir(dividir(1, 0)))",
    ]
}
