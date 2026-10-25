# frozen_string_literal: true

module Gordus
  # Funciones chicas para mostrar el toolchain de Ruby.
  module Saludo
    module_function

    def hola(nombre)
      "Hola, #{nombre}!"
    end

    def suma(desde, hasta)
      (desde..hasta).sum
    end

    def pares_al_reves(hasta)
      (1..hasta).select(&:even?).reverse
    end

    def dividir(a, b)
      return "#{a}/#{b} -> division por cero" if b.zero?

      "#{a}/#{b} = #{a / b}"
    end
  end
end
