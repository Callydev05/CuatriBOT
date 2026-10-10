"""
Análisis de los mensajes que mandas al bot.

Ejemplos que entiende:
    Examen MAT parcial temas 1-3 15/11
    Entrega PROG práctica 2 para el 20/10 a las 23:59
    Tarea física repasar el tema 4 mañana
    Estudiar historia el viernes
    Comprar folios                       (tarea sin fecha ni asignatura)

Primera palabra (opcional): examen / entrega / tarea.
Asignatura: su nombre, su abreviatura o cualquier alias puesto en el campo
            "Abreviatura" de Notion separado por comas (p. ej. "MAT, mates, cálculo").
Fecha: 15/11, 15/11/2026, 15 de noviembre, hoy, mañana, pasado mañana,
       el viernes, en 3 días. Hora opcional: 10:30, 23h59, a las 9.
Lo que escribas en líneas siguientes se guarda como "Notas".
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

TIPOS_PRIMERA_PALABRA = {
    "examen": "Examen", "exam": "Examen", "parcial": "Examen",
    "entrega": "Entrega", "entregar": "Entrega",
    "tarea": "Tarea", "todo": "Tarea",
}
# "parcial" como primera palabra marca el tipo pero se queda en el nombre
TIPOS_QUE_SE_QUEDAN = {"parcial"}
PALABRAS_EXAMEN = {"examen", "parcial", "final", "test", "control"}
PALABRAS_ENTREGA = {"practica", "practicas", "memoria", "trabajo", "proyecto", "informe", "entregable"}


STOPWORDS_BORDE = {"de", "del", "para", "el", "la", "los", "las", "a", "al", "en", "con",
                   "y", "es", "el dia", "dia", "-", "—", ":", ",", "que", "tengo", "hay"}


def norm(s: str) -> str:
    """Minúsculas y sin tildes, conservando la longitud (para alinear posiciones)."""
    return "".join(unicodedata.normalize("NFD", ch)[0] for ch in s.lower())


@dataclass
class Asignatura:
    id: str
    nombre: str
    abrev: str
    extra: list[str] = field(default_factory=list)  # alias adicionales

    def alias(self) -> list[str]:
        base = {norm(self.abrev), norm(self.nombre)} | {norm(a) for a in self.extra}
        return [a.strip() for a in base if a.strip()]


@dataclass
class Entrada:
    nombre: str
    tipo: str
    asignatura: Asignatura | None
    fecha: date | None
    hora: tuple[int, int] | None
    notas: str


class _Texto:
    """Texto con posiciones 'consumidas', para ir quitando lo que ya se ha reconocido."""

    def __init__(self, original: str):
        self.orig = original
        self.norm = norm(original)
        self.quitado: list[tuple[int, int]] = []

    def _libre(self, a: int, b: int) -> bool:
        return all(b <= x or a >= y for x, y in self.quitado)

    def buscar(self, patron: str):
        for m in re.finditer(patron, self.norm):
            if self._libre(m.start(), m.end()):
                self.quitado.append((m.start(), m.end()))
                return m
        return None

    def resto(self) -> str:
        chars = list(self.orig)
        for a, b in self.quitado:
            for i in range(a, b):
                chars[i] = " "
        return "".join(chars)


def _siguiente_dia_semana(hoy: date, idx: int) -> date:
    dias = (idx - hoy.weekday()) % 7
    return hoy + timedelta(days=dias or 7)


def _con_anio(d: int, m: int, anio: int | None, hoy: date) -> date | None:
    try:
        if anio is not None:
            if anio < 100:
                anio += 2000
            return date(anio, m, d)
        f = date(hoy.year, m, d)
        return f if f >= hoy else date(hoy.year + 1, m, d)
    except ValueError:
        return None


def _extraer_fecha(t: _Texto, hoy: date) -> date | None:
    meses = "|".join(MESES + ["setiembre"])
    m = t.buscar(rf"\b(\d{{1,2}})\s+de\s+({meses})(?:\s+(?:de\s+)?(\d{{4}}))?\b")
    if m:
        mes = 9 if m.group(2) == "setiembre" else MESES.index(m.group(2)) + 1
        return _con_anio(int(m.group(1)), mes, int(m.group(3)) if m.group(3) else None, hoy)

    # dd/mm, dd/mm/aaaa o dd-mm-aaaa ("temas 1-3" no cuenta como fecha)
    m = (t.buscar(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?\b")
         or t.buscar(r"\b(\d{1,2})-(\d{1,2})-(\d{4}|\d{2})\b"))
    if m:
        return _con_anio(int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None, hoy)

    if t.buscar(r"\bpasado\s+manana\b"):
        return hoy + timedelta(days=2)
    if t.buscar(r"\bmanana\b"):
        return hoy + timedelta(days=1)
    if t.buscar(r"\bhoy\b"):
        return hoy

    m = t.buscar(r"\ben\s+(\d{1,3})\s+dias?\b")
    if m:
        return hoy + timedelta(days=int(m.group(1)))

    dias = "|".join(DIAS_SEMANA)
    m = t.buscar(rf"\b(?:(?:el|este)\s+)?(?:proximo\s+)?({dias})\b")
    if m:
        return _siguiente_dia_semana(hoy, DIAS_SEMANA.index(m.group(1)))
    return None


def _extraer_hora(t: _Texto) -> tuple[int, int] | None:
    for patron in (r"\b(?:a\s+las?\s+)?(\d{1,2})[:h](\d{2})\b",
                   r"\ba\s+las?\s+(\d{1,2})\b",
                   r"\b(\d{1,2})h\b"):
        m = t.buscar(patron)
        if m:
            h = int(m.group(1))
            mi = int(m.group(2)) if m.lastindex and m.lastindex >= 2 else 0
            if 0 <= h < 24 and 0 <= mi < 60:
                return h, mi
    return None


def _extraer_asignatura(t: _Texto, asignaturas: list[Asignatura]) -> Asignatura | None:
    candidatos = [(a, asig) for asig in asignaturas for a in asig.alias()]
    candidatos.sort(key=lambda x: len(x[0]), reverse=True)
    for alias, asig in candidatos:
        if t.buscar(rf"\b{re.escape(alias)}\b"):
            return asig
    return None


def _limpiar_nombre(s: str) -> str:
    palabras = s.split()
    while palabras and norm(palabras[0]) in STOPWORDS_BORDE:
        palabras.pop(0)
    while palabras and norm(palabras[-1]) in STOPWORDS_BORDE:
        palabras.pop()
    nombre = " ".join(palabras).strip(" ,.-:")
    return nombre[:1].upper() + nombre[1:] if nombre else ""


def analizar(mensaje: str, asignaturas: list[Asignatura], hoy: date) -> Entrada:
    lineas = mensaje.strip().splitlines()
    primera = lineas[0].strip() if lineas else ""
    notas = "\n".join(lineas[1:]).strip()

    t = _Texto(primera)
    tipo = None

    m = re.match(r"\s*(\w+)", t.norm)
    if m and m.group(1) in TIPOS_PRIMERA_PALABRA:
        tipo = TIPOS_PRIMERA_PALABRA[m.group(1)]
        if m.group(1) not in TIPOS_QUE_SE_QUEDAN:
            t.quitado.append((m.start(1), m.end(1)))

    fecha = _extraer_fecha(t, hoy)
    hora = _extraer_hora(t) if fecha else None
    asig = _extraer_asignatura(t, asignaturas)

    if tipo is None:
        palabras = set(re.findall(r"\w+", t.norm))
        if palabras & PALABRAS_EXAMEN:
            tipo = "Examen"
        elif palabras & PALABRAS_ENTREGA:
            tipo = "Entrega"
        else:
            tipo = "Tarea"

    nombre = _limpiar_nombre(t.resto())
    if not nombre:
        nombre = f"{tipo} {asig.abrev}" if asig else tipo

    return Entrada(nombre=nombre, tipo=tipo, asignatura=asig, fecha=fecha, hora=hora, notas=notas)
