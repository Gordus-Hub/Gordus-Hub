// swift-tools-version:6.0
// Gordus-Hub - paquete de ejemplo SIN dependencias externas (funciona sin internet).
import PackageDescription

let package = Package(
    name: "hola",
    targets: [
        .target(name: "HolaCore"),
        .executableTarget(name: "Hola", dependencies: ["HolaCore"]),
        .testTarget(name: "HolaCoreTests", dependencies: ["HolaCore"]),
    ]
)
