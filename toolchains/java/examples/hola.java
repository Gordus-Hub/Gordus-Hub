// Ejemplo minimo para comprobar el toolchain Java del Gordus-Hub.
// Se compila con:  javac Hola.java   y se ejecuta con:  java Hola
public class Hola {
    public static void main(String[] args) {
        String nombre = args.length > 0 ? args[0] : "Gordus-Hub";
        System.out.println("Hola, " + nombre + "!");
        System.out.println("Java " + Runtime.version().feature());
    }
}
