"""Tests de la lógica pura (calculos.py y buscar_asignatura). Ejecuta: pytest"""
from datetime import date, datetime

import pytest

from calculos import (Nota, Sesion, fmt_duracion, fmt_num, minutos_por_asignatura,
                      parsear_nota, resumen_notas)
from parsing import Asignatura, buscar_asignatura


# ---------- parsear_nota ----------

def test_parsear_nota_basico():
    assert parsear_nota(["IGV", "práctica1", "8.5", "30%"]) == ("IGV", "Práctica1", 8.5, 30.0)


def test_parsear_nota_coma_decimal_y_sin_porcentaje():
    assert parsear_nota(["IGV", "parcial", "6,25", "20"]) == ("IGV", "Parcial", 6.25, 20.0)


def test_parsear_nota_nombre_de_varias_palabras():
    assert parsear_nota(["BBDD", "examen", "tema", "1", "7", "10%"])[1] == "Examen tema 1"


def test_parsear_nota_sin_nombre():
    assert parsear_nota(["IGV", "7", "10%"]) == ("IGV", "Nota", 7.0, 10.0)


@pytest.mark.parametrize("args", [
    [],
    ["IGV", "8.5"],                    # falta el peso
    ["IGV", "x", "ocho", "30%"],       # nota no numérica
    ["IGV", "x", "11", "30%"],         # nota > 10
    ["IGV", "x", "-1", "30%"],         # nota < 0
    ["IGV", "x", "5", "0%"],           # peso 0
    ["IGV", "x", "5", "120%"],         # peso > 100
])
def test_parsear_nota_errores(args):
    with pytest.raises(ValueError):
        parsear_nota(args)


# ---------- resumen_notas ----------

def test_resumen_sin_notas():
    r = resumen_notas([])
    assert r.media is None
    assert r.puntos == 0
    assert r.restante == 100
    assert r.necesaria == pytest.approx(5)


def test_resumen_media_ponderada_y_necesaria():
    r = resumen_notas([Nota("P1", 8.5, 30), Nota("P2", 6, 30)])
    assert r.peso_evaluado == 60
    assert r.media == pytest.approx(7.25)       # (8.5*30 + 6*30) / 60
    assert r.puntos == pytest.approx(4.35)      # 2.55 + 1.8
    assert r.restante == 40
    assert r.necesaria == pytest.approx(1.625)  # (5 - 4.35) / 0.4


def test_resumen_aprobado_asegurado():
    r = resumen_notas([Nota("Parcial", 10, 60)])
    assert r.necesaria <= 0


def test_resumen_imposible_aprobar():
    r = resumen_notas([Nota("Parcial", 0, 60)])
    assert r.necesaria > 10  # necesitaría un 12,5


def test_resumen_todo_evaluado():
    r = resumen_notas([Nota("A", 4, 50), Nota("B", 7, 50)])
    assert r.restante == 0
    assert r.necesaria is None
    assert r.puntos == pytest.approx(5.5)


# ---------- formato ----------

@pytest.mark.parametrize("x, esperado", [(8.5, "8,5"), (7.0, "7"), (6.666, "6,67"), (0, "0")])
def test_fmt_num(x, esperado):
    assert fmt_num(x) == esperado


@pytest.mark.parametrize("minutos, esperado", [(0, "0 min"), (20, "20 min"), (60, "1 h"), (95, "1 h 35 min")])
def test_fmt_duracion(minutos, esperado):
    assert fmt_duracion(minutos) == esperado


# ---------- minutos_por_asignatura ----------

def _sesion(asig: str, dia: int, minutos: int | None) -> Sesion:
    return Sesion(id="x", asignaturas=[asig] if asig else [], inicio=datetime(2026, 10, dia, 17, 0),
                  minutos=minutos)


def test_minutos_suma_por_asignatura_desde_el_lunes():
    lunes = date(2026, 10, 19)
    sesiones = [
        _sesion("bbdd", 19, 60),
        _sesion("bbdd", 21, 30),
        _sesion("igv", 20, 45),
        _sesion("igv", 18, 120),  # domingo anterior: no cuenta
        _sesion("igv", 22, None),  # en curso: no cuenta
        _sesion("", 20, 10),       # sin asignatura
    ]
    assert minutos_por_asignatura(sesiones, lunes) == {"bbdd": 90, "igv": 45, "": 10}


# ---------- buscar_asignatura ----------

ASIGS = [Asignatura(id="1", nombre="Bases de Datos", abrev="BBDD", extra=["bases"]),
         Asignatura(id="2", nombre="Informática Gráfica y Visualización", abrev="IGV")]


@pytest.mark.parametrize("texto, id_", [("BBDD", "1"), ("bbdd", "1"), ("Bases", "1"),
                                        ("bases de datos", "1"), ("igv", "2"),
                                        ("informatica grafica y visualizacion", "2")])
def test_buscar_asignatura(texto, id_):
    assert buscar_asignatura(texto, ASIGS).id == id_


def test_buscar_asignatura_desconocida():
    assert buscar_asignatura("MAT", ASIGS) is None
