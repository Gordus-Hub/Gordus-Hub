# Interoperabilidad: Mojo llama al Python que vive DENTRO del entorno Mojo (pixi),
# nunca al Python del sistema ni al de gordus_ai.
from std.python import Python


def main() raises:
    var sys = Python.import_module("sys")
    var math = Python.import_module("math")
    print("python_prefix:", sys.prefix)
    print("sqrt(16) =", math.sqrt(16))
