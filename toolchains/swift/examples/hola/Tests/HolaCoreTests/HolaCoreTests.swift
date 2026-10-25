import XCTest
@testable import HolaCore

final class HolaCoreTests: XCTestCase {
    func testSaludo() {
        XCTAssertEqual(saludo("Gordus-Hub"), "Hola, Gordus-Hub!")
    }

    func testSumaYPares() {
        XCTAssertEqual(suma(hasta: 10), 55)
        XCTAssertEqual(paresAlReves(hasta: 10), [10, 8, 6, 4, 2])
    }

    func testDivision() {
        XCTAssertEqual(dividir(10, 2), .success(5))
        XCTAssertEqual(dividir(1, 0), .failure(.divisionPorCero))
    }
}
