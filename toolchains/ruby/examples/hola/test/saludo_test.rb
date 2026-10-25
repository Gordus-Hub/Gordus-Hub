# frozen_string_literal: true

require "minitest/autorun"
require_relative "../lib/saludo"

class SaludoTest < Minitest::Test
  def test_hola
    assert_equal "Hola, Gordus-Hub!", Gordus::Saludo.hola("Gordus-Hub")
  end

  def test_suma
    assert_equal 55, Gordus::Saludo.suma(1, 10)
  end

  def test_pares_al_reves
    assert_equal [10, 8, 6, 4, 2], Gordus::Saludo.pares_al_reves(10)
  end

  def test_division_por_cero
    assert_equal "1/0 -> division por cero", Gordus::Saludo.dividir(1, 0)
  end
end
