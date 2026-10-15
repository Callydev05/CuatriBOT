"""
Crea en Notion todo lo que necesita el bot y guarda los IDs en .env.

Antes de ejecutarlo:
  1. Pon tu NOTION_TOKEN en .env.
  2. Crea en Notion una página vacía (por ejemplo "Cuatrimestre") y conéctale tu
     integración: ••• → Conexiones → tu integración.
  3. Copia el enlace de esa página (••• → Copiar enlace).

Uso:
  python setup_notion.py <enlace o id de la página>

Crea dentro de la página:
  - Base de datos "Asignaturas" (una página por asignatura con su lista de tareas)
  - Base de datos "Exámenes y entregas" (donde guarda el bot)
  - Base de datos "Horario" (tus clases semanales, para el comando /horario)
  - Página "Notas rápidas"
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ENV = Path(__file__).with_name(".env")
load_dotenv(ENV)


def die(msg: str):
    print(f"\n❌ {msg}")
    sys.exit(1)


def page_id(arg: str) -> str:
    m = re.findall(r"[0-9a-fA-F]{32}|[0-9a-fA-F-]{36}", arg)
    if not m:
        die("No encuentro un id de página en lo que has pasado. Copia el enlace de la página de Notion.")
    return m[-1].replace("-", "")


def guardar_env(valores: dict[str, str]):
    lineas = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    hechos = set()
    for i, l in enumerate(lineas):
        clave = l.split("=", 1)[0].strip()
        if clave in valores:
            lineas[i] = f"{clave}={valores[clave]}"
            hechos.add(clave)
    lineas += [f"{k}={v}" for k, v in valores.items() if k not in hechos]
    ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        die("Falta NOTION_TOKEN en .env")
    if len(sys.argv) < 2:
        die("Uso: python setup_notion.py <enlace de tu página de Notion>")
    padre = page_id(sys.argv[1])

    http = httpx.Client(base_url="https://api.notion.com/v1", timeout=30, headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    })

    def req(method, url, **kw):
        r = http.request(method, url, **kw)
        if r.status_code == 404:
            die("Notion no encuentra la página. ¿Has conectado la integración a ella (••• → Conexiones)?")
        if r.status_code == 401:
            die("El NOTION_TOKEN no es válido.")
        if r.status_code >= 400:
            die(f"Error de Notion {r.status_code}: {r.text[:300]}")
        return r.json()

    req("GET", f"/pages/{padre}")
    print("✅ Acceso a la página correcto.\n")

    print("Escribe tus asignaturas separadas por comas, con su abreviatura detrás de dos puntos.")
    print("Ejemplo:  Matemáticas:MAT, Programación:PROG, Física, Historia")
    texto = input("> ").strip()
    asignaturas = []
    for trozo in filter(None, (t.strip() for t in texto.split(","))):
        nombre, _, abrev = trozo.partition(":")
        asignaturas.append((nombre.strip(), (abrev or nombre).strip()))

    asig_db = req("POST", "/databases", json={
        "parent": {"type": "page_id", "page_id": padre},
        "title": [{"text": {"content": "Asignaturas"}}],
        "properties": {"Asignatura": {"title": {}}, "Abreviatura": {"rich_text": {}}},
    })
    print("✅ Base de datos Asignaturas creada")

    exam_db = req("POST", "/databases", json={
        "parent": {"type": "page_id", "page_id": padre},
        "title": [{"text": {"content": "Exámenes y entregas"}}],
        "properties": {
            "Nombre": {"title": {}},
            "Tipo": {"select": {"options": [
                {"name": "Examen", "color": "red"},
                {"name": "Entrega", "color": "orange"},
                {"name": "Tarea", "color": "blue"},
            ]}},
            "Asignatura": {"relation": {"database_id": asig_db["id"], "single_property": {}}},
            "Fecha": {"date": {}},
            "Hecho": {"checkbox": {}},
            "Notas": {"rich_text": {}},
        },
    })
    print("✅ Base de datos Exámenes y entregas creada")

    horario_db = req("POST", "/databases", json={
        "parent": {"type": "page_id", "page_id": padre},
        "title": [{"text": {"content": "Horario"}}],
        "properties": {
            "Clase": {"title": {}},
            "Día": {"select": {"options": [
                {"name": d, "color": c} for d, c in (
                    ("Lunes", "blue"), ("Martes", "green"), ("Miércoles", "yellow"),
                    ("Jueves", "orange"), ("Viernes", "purple"), ("Sábado", "pink"), ("Domingo", "red"))
            ]}},
            "Inicio": {"rich_text": {}},
            "Fin": {"rich_text": {}},
            "Tipo": {"select": {"options": [
                {"name": "Teoría", "color": "blue"}, {"name": "Prácticas", "color": "green"}]}},
            "Notas": {"rich_text": {}},
        },
    })
    print("✅ Base de datos Horario creada (rellénala con tus clases: día, inicio y fin tipo 9:30)")

    contenido = [
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"text": {"content": "📝 Tareas y notas"}}]}},
        {"object": "block", "type": "to_do",
         "to_do": {"rich_text": [{"text": {"content": "Nueva tarea"}}], "checked": False}},
    ]
    for nombre, abrev in asignaturas:
        req("POST", "/pages", json={
            "parent": {"database_id": asig_db["id"]},
            "properties": {
                "Asignatura": {"title": [{"text": {"content": nombre}}]},
                "Abreviatura": {"rich_text": [{"text": {"content": abrev}}]},
            },
            "children": contenido,
        })
        print(f"   · {nombre} ({abrev})")

    notas = req("POST", "/pages", json={
        "parent": {"type": "page_id", "page_id": padre},
        "icon": {"type": "emoji", "emoji": "⚡"},
        "properties": {"title": {"title": [{"text": {"content": "Notas rápidas"}}]}},
        "children": [{"object": "block", "type": "to_do",
                      "to_do": {"rich_text": [], "checked": False}}],
    })
    print("✅ Página Notas rápidas creada")

    guardar_env({
        "EXAMENES_DB_ID": exam_db["id"].replace("-", ""),
        "ASIGNATURAS_DB_ID": asig_db["id"].replace("-", ""),
        "NOTAS_RAPIDAS_PAGE_ID": notas["id"].replace("-", ""),
        "HORARIO_DB_ID": horario_db["id"].replace("-", ""),
    })
    print("\n🎉 Listo. He guardado los IDs en .env. Ya puedes arrancar el bot con: python bot.py")


if __name__ == "__main__":
    main()
