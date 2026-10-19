"""Acceso mínimo a la API de Notion para el bot del cuatrimestre."""
from __future__ import annotations

import asyncio
import os
import time as _time
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx

from calculos import Nota, Sesion
from parsing import Asignatura, Entrada

API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
TZ = ZoneInfo(os.environ.get("ZONA_HORARIA", "Europe/Madrid"))


class NotionError(RuntimeError):
    pass


def _texto(rich: list[dict]) -> str:
    return "".join(t.get("plain_text", "") for t in rich or []).strip()


def _id(s: str) -> str:
    return s.replace("-", "")


def _fecha_hora(d: dict) -> datetime:
    """Propiedad de fecha de Notion con hora → datetime en nuestra zona horaria."""
    # Python < 3.11 no entiende la "Z" final
    dt = datetime.fromisoformat(d["start"].replace("Z", "+00:00"))
    if dt.tzinfo is None:  # sin desfase: la zona viene aparte o es la nuestra
        dt = dt.replace(tzinfo=ZoneInfo(d["time_zone"]) if d.get("time_zone") else TZ)
    return dt.astimezone(TZ)


def _relacion(props: dict) -> list[str]:
    return [_id(r["id"]) for r in props.get("Asignatura", {}).get("relation", [])]


@dataclass
class Pendiente:
    id: str
    nombre: str
    tipo: str
    fecha: date | None
    hora: str | None
    asignaturas: list[str]  # ids de asignatura (sin guiones)
    url: str


class Notion:
    def __init__(self, token: str, examenes_db: str, asignaturas_db: str, notas_rapidas_page: str | None,
                 horario_db: str | None = None, notas_db: str | None = None, estudio_db: str | None = None):
        self.examenes_db = _id(examenes_db)
        self.horario_db = _id(horario_db) if horario_db else None
        self.notas_db = _id(notas_db) if notas_db else None
        self.estudio_db = _id(estudio_db) if estudio_db else None
        self.asignaturas_db = _id(asignaturas_db)
        self.notas_rapidas_page = _id(notas_rapidas_page) if notas_rapidas_page else None
        self.http = httpx.AsyncClient(
            base_url=API,
            timeout=30,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
        )
        self._asig_cache: tuple[float, list[Asignatura]] | None = None

    async def close(self):
        await self.http.aclose()

    async def _req(self, method: str, url: str, **kw) -> dict:
        for intento in range(3):
            try:
                r = await self.http.request(method, url, **kw)
            except httpx.HTTPError as e:  # sin conexión, timeout...
                raise NotionError(f"Notion: error de conexión ({e.__class__.__name__})") from e
            if r.status_code == 429 and intento < 2:  # límite de peticiones
                await asyncio.sleep(float(r.headers.get("Retry-After", 1)))
                continue
            if r.status_code >= 400:
                raise NotionError(f"Notion {r.status_code}: {r.text[:300]}")
            return r.json()
        raise NotionError("Notion: demasiadas peticiones")

    async def _query(self, db_id: str, body: dict | None = None) -> list[dict]:
        resultados, cursor = [], None
        while True:
            payload = dict(body or {})
            if cursor:
                payload["start_cursor"] = cursor
            data = await self._req("POST", f"/databases/{db_id}/query", json=payload)
            resultados += data["results"]
            if not data.get("has_more"):
                return resultados
            cursor = data["next_cursor"]

    async def _hijos(self, block_id: str) -> list[dict]:
        resultados, cursor = [], None
        while True:
            params = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            data = await self._req("GET", f"/blocks/{block_id}/children", params=params)
            resultados += data["results"]
            if not data.get("has_more"):
                return resultados
            cursor = data["next_cursor"]

    # ---------- Asignaturas ----------

    async def asignaturas(self, forzar: bool = False) -> list[Asignatura]:
        if self._asig_cache and not forzar and _time.time() - self._asig_cache[0] < 600:
            return self._asig_cache[1]
        lista = []
        for p in await self._query(self.asignaturas_db):
            props = p["properties"]
            nombre = _texto(props.get("Asignatura", {}).get("title", []))
            # "Abreviatura" admite alias separados por comas: el primero es el que se muestra
            partes = [x.strip() for x in _texto(props.get("Abreviatura", {}).get("rich_text", [])).split(",")]
            partes = [x for x in partes if x] or [nombre]
            if nombre:
                lista.append(Asignatura(id=_id(p["id"]), nombre=nombre, abrev=partes[0], extra=partes[1:]))
        self._asig_cache = (_time.time(), lista)
        return lista

    # ---------- Exámenes y entregas ----------

    async def crear(self, e: Entrada) -> dict:
        props: dict = {
            "Nombre": {"title": [{"text": {"content": e.nombre[:2000]}}]},
            "Tipo": {"select": {"name": e.tipo}},
            "Hecho": {"checkbox": False},
        }
        if e.asignatura:
            props["Asignatura"] = {"relation": [{"id": e.asignatura.id}]}
        if e.fecha:
            if e.hora:
                inicio = datetime.combine(e.fecha, time(*e.hora), TZ).isoformat()
            else:
                inicio = e.fecha.isoformat()
            props["Fecha"] = {"date": {"start": inicio}}
        if e.notas:
            props["Notas"] = {"rich_text": [{"text": {"content": e.notas[:2000]}}]}
        return await self._req("POST", "/pages", json={
            "parent": {"database_id": self.examenes_db},
            "properties": props,
        })

    async def pendientes(self) -> list[Pendiente]:
        paginas = await self._query(self.examenes_db, {
            "filter": {"property": "Hecho", "checkbox": {"equals": False}},
        })
        lista = []
        for p in paginas:
            props = p["properties"]
            fecha = hora = None
            d = props.get("Fecha", {}).get("date")
            if d and d.get("start"):
                inicio = d["start"]
                if "T" in inicio:
                    dt = _fecha_hora(d)
                    fecha, hora = dt.date(), dt.strftime("%H:%M")
                else:
                    fecha = date.fromisoformat(inicio[:10])
            lista.append(Pendiente(
                id=_id(p["id"]),
                nombre=_texto(props.get("Nombre", {}).get("title", [])) or "(sin nombre)",
                tipo=(props.get("Tipo", {}).get("select") or {}).get("name", "Tarea"),
                fecha=fecha,
                hora=hora,
                asignaturas=_relacion(props),
                url=p.get("url", ""),
            ))
        lista.sort(key=lambda x: (x.fecha is None, x.fecha or date.max, x.hora or ""))
        return lista

    async def marcar_hecho(self, page_id: str):
        await self._req("PATCH", f"/pages/{page_id}", json={"properties": {"Hecho": {"checkbox": True}}})

    async def borrar(self, page_id: str):
        # Lo manda a la papelera de Notion (se puede recuperar desde allí)
        await self._req("PATCH", f"/pages/{page_id}", json={"archived": True})

    # ---------- Listas de tareas dentro de las páginas ----------

    async def todos_de_pagina(self, page_id: str) -> list[str]:
        try:
            bloques = await self._hijos(page_id)
        except NotionError:
            return []
        tareas = []
        for b in bloques:
            if b.get("type") == "to_do" and not b["to_do"].get("checked"):
                txt = _texto(b["to_do"].get("rich_text", []))
                if txt and txt.lower() != "nueva tarea":
                    tareas.append(txt)
        return tareas

    async def todos_por_asignatura(self) -> tuple[dict[str, list[str]], list[str]]:
        asigs = await self.asignaturas()
        resultados = await asyncio.gather(*(self.todos_de_pagina(a.id) for a in asigs))
        por_asig = {a.abrev: r for a, r in zip(asigs, resultados) if r}
        rapidas = await self.todos_de_pagina(self.notas_rapidas_page) if self.notas_rapidas_page else []
        return por_asig, rapidas

    # ---------- Horario ----------

    async def clases_del_dia(self, dia: str) -> list[dict]:
        """Clases de un día de la semana ("Lunes", "Martes"...), ordenadas por hora de inicio."""
        if not self.horario_db:
            return []
        # Filtramos aquí y no en Notion: si el día no existe como opción (p. ej. "Sábado"), Notion da error 400
        paginas = await self._query(self.horario_db)
        clases = []
        for p in paginas:
            props = p["properties"]
            if (props.get("Día", {}).get("select") or {}).get("name") != dia:
                continue
            clases.append({
                "clase": _texto(props.get("Clase", {}).get("title", [])) or "(sin nombre)",
                "inicio": _texto(props.get("Inicio", {}).get("rich_text", [])),
                "fin": _texto(props.get("Fin", {}).get("rich_text", [])),
                "tipo": (props.get("Tipo", {}).get("select") or {}).get("name", ""),
                "notas": _texto(props.get("Notas", {}).get("rich_text", [])),
            })

        def clave(c):  # "8:30" y "08:30" se ordenan igual
            h, _, m = c["inicio"].partition(":")
            return (int(h) if h.isdigit() else 99, int(m) if m.isdigit() else 0)

        return sorted(clases, key=clave)

    # ---------- Notas ----------

    async def guardar_nota(self, asignatura_id: str, nombre: str, nota: float, peso: float) -> dict:
        return await self._req("POST", "/pages", json={
            "parent": {"database_id": self.notas_db},
            "properties": {
                "Nombre": {"title": [{"text": {"content": nombre[:2000]}}]},
                "Asignatura": {"relation": [{"id": asignatura_id}]},
                "Nota": {"number": nota},
                "Peso": {"number": peso},
            },
        })

    async def notas(self, asignatura_id: str | None = None) -> list[Nota]:
        """Notas de una asignatura (o de todas), en el orden en que se apuntaron."""
        body: dict = {"sorts": [{"timestamp": "created_time", "direction": "ascending"}]}
        if asignatura_id:
            body["filter"] = {"property": "Asignatura", "relation": {"contains": asignatura_id}}
        lista = []
        for p in await self._query(self.notas_db, body):
            props = p["properties"]
            nota = props.get("Nota", {}).get("number")
            peso = props.get("Peso", {}).get("number")
            if nota is None or peso is None:  # fila a medio rellenar en Notion
                continue
            lista.append(Nota(nombre=_texto(props.get("Nombre", {}).get("title", [])) or "Nota",
                              nota=nota, peso=peso, asignaturas=_relacion(props)))
        return lista

    # ---------- Sesiones de estudio ----------

    @staticmethod
    def _sesion(p: dict) -> Sesion | None:
        props = p["properties"]
        d = props.get("Inicio", {}).get("date")
        if not d or "T" not in (d.get("start") or ""):
            return None
        return Sesion(id=_id(p["id"]), asignaturas=_relacion(props), inicio=_fecha_hora(d),
                      minutos=props.get("Minutos", {}).get("number"))

    async def empezar_estudio(self, asignatura: Asignatura) -> dict:
        return await self._req("POST", "/pages", json={
            "parent": {"database_id": self.estudio_db},
            "properties": {
                "Nombre": {"title": [{"text": {"content": f"Estudio {asignatura.abrev}"}}]},
                "Asignatura": {"relation": [{"id": asignatura.id}]},
                "Inicio": {"date": {"start": datetime.now(TZ).isoformat(timespec="seconds")}},
            },
        })

    async def estudio_en_curso(self) -> Sesion | None:
        """La sesión empezada con /estudiar y aún sin /parar (la que no tiene minutos)."""
        paginas = await self._query(self.estudio_db, {
            "filter": {"property": "Minutos", "number": {"is_empty": True}},
            "sorts": [{"property": "Inicio", "direction": "descending"}],
        })
        sesiones = [s for s in map(self._sesion, paginas) if s]
        return sesiones[0] if sesiones else None

    async def terminar_estudio(self, page_id: str, minutos: int):
        await self._req("PATCH", f"/pages/{page_id}", json={"properties": {"Minutos": {"number": minutos}}})

    async def sesiones_desde(self, desde: date) -> list[Sesion]:
        # Un día de margen: Notion compara en UTC y lo estudiado a las 00:30 en España allí es aún el día
        # anterior. El corte exacto lo hace minutos_por_asignatura con la hora local.
        paginas = await self._query(self.estudio_db, {
            "filter": {"property": "Inicio", "date": {"on_or_after": (desde - timedelta(days=1)).isoformat()}},
        })
        return [s for s in map(self._sesion, paginas) if s]
