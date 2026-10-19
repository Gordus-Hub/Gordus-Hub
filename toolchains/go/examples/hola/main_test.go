package main

import "testing"

func TestSaludo(t *testing.T) {
	if got := Saludo("Gordus-Hub"); got != "Hola, Gordus-Hub!" {
		t.Fatalf("Saludo() = %q", got)
	}
}

func TestSumaHasta(t *testing.T) {
	casos := map[int]int{0: 0, 1: 1, 10: 55, 100: 5050}
	for n, want := range casos {
		if got := SumaHasta(n); got != want {
			t.Errorf("SumaHasta(%d) = %d, want %d", n, got, want)
		}
	}
}
