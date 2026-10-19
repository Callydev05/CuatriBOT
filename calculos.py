"""
Cálculos sin Telegram ni Notion (fáciles de probar con pytest).

- Notas: /nota IGV práctica1 8.5 30%  →  media ponderada y nota necesaria para aprobar.
- Estudio: minutos por asignatura desde una fecha (para /stats).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

APROBADO = 5.0


@dataclass
class Nota:
    nombre: str
    nota: float   # sobre 10
    peso: float   # % de la nota final (30 = 30 %)
    asignaturas: list[str] = field(default_factory=list)  # ids de asignatura (sin guiones)


@dataclass
class Sesion:
    id: str
    asignaturas: list[str]
    inicio: datetime
    minutos: int | None  # None: sesión en curso


@dataclass
class ResumenNotas:
    peso_evaluado: float     # % de la asignatura que ya tiene nota
    puntos: float            # lo que llevas sobre 10 (8.5 al 30 % = 2.55)
    media: float | None      # media de lo evaluado (None si no hay pesos)
    restante: float          # % que queda por evaluar
    necesaria: float | None  # nota media necesaria en lo que queda (None si no queda nada)


def _numero(s: str) -> float:
    """'8.5', '8,5' o '30%' → float. ValueError si no es un número."""
    return float(s.strip().rstrip("%").replace(",", "."))


def parsear_nota(args: list[str]) -> tuple[str, str, float, float]:
    """Argumentos de /nota → (asignatura, nombre, nota, peso).

    /nota IGV práctica1 8.5 30%      → ("IGV", "Práctica1", 8.5, 30.0)
    /nota IGV parcial tema 1 6,25 20 → ("IGV", "Parcial tema 1", 6.25, 20.0)
    /nota IGV 7 10%                  → ("IGV", "Nota", 7.0, 10.0)
    """
    if len(args) < 3:
        raise ValueError("Faltan datos: asignatura, nota y peso.")
    alias, *medio, txt_nota, txt_peso = args
    try:
        nota, peso = _numero(txt_nota), _numero(txt_peso)
    except ValueError:
        raise ValueError("La nota y el peso tienen que ser números (8.5 y 30%).") from None
    if not 0 <= nota <= 10:
        raise ValueError("La nota tiene que estar entre 0 y 10.")
    if not 0 < peso <= 100:
        raise ValueError("El peso tiene que estar entre 1 y 100 %.")
    nombre = " ".join(medio).strip() or "Nota"
    return alias, nombre[:1].upper() + nombre[1:], nota, peso


def resumen_notas(notas: list[Nota], aprobado: float = APROBADO) -> ResumenNotas:
    peso = sum(n.peso for n in notas)
    suma = sum(n.nota * n.peso for n in notas)
    restante = max(0.0, 100 - peso)
    puntos = suma / 100
    return ResumenNotas(
        peso_evaluado=peso,
        puntos=puntos,
        media=suma / peso if peso else None,
        restante=restante,
        necesaria=(aprobado - puntos) / (restante / 100) if restante else None,
    )


def fmt_num(x: float) -> str:
    """8.5 → '8,5', 7.0 → '7', 6.666 → '6,67'."""
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def minutos_por_asignatura(sesiones: list[Sesion], desde: date) -> dict[str, int]:
    """Minutos de estudio por id de asignatura en las sesiones terminadas desde 'desde'."""
    total: dict[str, int] = {}
    for s in sesiones:
        if s.minutos is None or s.inicio.date() < desde:
            continue
        for a in s.asignaturas or [""]:  # "" = sin asignatura
            total[a] = total.get(a, 0) + s.minutos
    return total


def fmt_duracion(minutos: int) -> str:
    """95 → '1 h 35 min', 60 → '1 h', 20 → '20 min'."""
    h, m = divmod(minutos, 60)
    if h and m:
        return f"{h} h {m} min"
    return f"{h} h" if h else f"{m} min"
