# frozen_string_literal: true

require_relative "lib/saludo"

puts Gordus::Saludo.hola("Gordus-Hub")
puts "Suma 1..10 = #{Gordus::Saludo.suma(1, 10)}"
puts "Pares al reves: #{Gordus::Saludo.pares_al_reves(10).join(' ')}"
puts "Resultado: #{Gordus::Saludo.dividir(10, 2)}, #{Gordus::Saludo.dividir(1, 0)}"
