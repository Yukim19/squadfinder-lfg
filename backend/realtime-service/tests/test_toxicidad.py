"""Pruebas del filtro anti-toxicidad (sin base de datos)."""

import pytest

from app.toxicidad import clasificar, se_oculta


@pytest.mark.parametrize("texto", [
    "¡Hola! Entramos en 10 min",
    "jugué mal la ronda, perdón",
    "buen clutch, perdimos por poco",
    "te mato en la siguiente",  # lenguaje normal de juego
    "botella de agua",
    "La partida fue estupenda",
])
def test_mensajes_limpios(texto):
    assert clasificar(texto) == "NONE"


@pytest.mark.parametrize("texto", [
    "El de la otra sala es malísimo, que desinstale",
    "gg ez noob",
    "you are trash",
    "pésimo tiro",
])
def test_mensajes_leves(texto):
    assert clasificar(texto) == "MILD"


@pytest.mark.parametrize("texto", [
    "Diego eres un inútil, nos hiciste perder",
    "IDIOTAS todos",          # plural y mayúsculas (stemming)
    "eres un 1d10taaaa",      # leetspeak y letras repetidas
    "que mierda de equipo",
    "kys",                    # frase
    "noob y estúpido",        # lo más grave gana
])
def test_mensajes_graves(texto):
    assert clasificar(texto) == "SEVERE"


def test_cada_filtro_oculta_lo_suyo():
    assert [se_oculta(t, "OFF") for t in ("NONE", "MILD", "SEVERE")] == [False, False, False]
    assert [se_oculta(t, "MEDIUM") for t in ("NONE", "MILD", "SEVERE")] == [False, False, True]
    assert [se_oculta(t, "STRICT") for t in ("NONE", "MILD", "SEVERE")] == [False, True, True]
