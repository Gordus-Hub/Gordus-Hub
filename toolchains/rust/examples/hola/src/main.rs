//! Ejemplo de Rust de Gordus-Hub: sin dependencias externas.

/// Suma los numeros de 1 a `n` (inclusive).
fn suma_hasta(n: u32) -> u32 {
    (1..=n).sum()
}

/// Divide `a` entre `b`; devuelve un error en vez de entrar en panico si `b` es cero.
fn dividir(a: i32, b: i32) -> Result<i32, String> {
    if b == 0 {
        return Err(String::from("division por cero"));
    }
    Ok(a / b)
}

fn main() {
    println!("Hola, Gordus-Hub!");
    println!("Suma 1..10 = {}", suma_hasta(10));
    let pares: Vec<u32> = (1..=10).filter(|x| x % 2 == 0).rev().collect();
    println!("Pares al reves: {pares:?}");
    match (dividir(10, 2), dividir(1, 0)) {
        (Ok(v), Err(e)) => println!("Result: 10/2 = {v}, 1/0 -> {e}"),
        other => println!("inesperado: {other:?}"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn suma_de_uno_a_diez() {
        assert_eq!(suma_hasta(10), 55);
    }

    #[test]
    fn dividir_por_cero_es_error() {
        assert_eq!(dividir(10, 2), Ok(5));
        assert!(dividir(1, 0).is_err());
    }
}
