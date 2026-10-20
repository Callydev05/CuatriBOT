<div align="center">

# 📚 CuatriBOT

**Tu cuatrimestre organizado desde Telegram, guardado en Notion.**

Apunta exámenes, entregas y tareas con un mensaje, recibe avisos cada día, lleva tus notas y mide cuánto estudias de cada asignatura.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)
![Notion](https://img.shields.io/badge/Notion-API-000000?logo=notion&logoColor=white)
![pytest](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)

</div>

---

## 📑 Índice

- [✨ Qué hace](#-qué-hace)
- [💬 Cómo escribirle](#-cómo-escribirle)
- [🎛️ Panel de botones](#️-panel-de-botones)
- [⌨️ Comandos](#️-comandos)
- [📊 Notas y media](#-notas-y-media)
- [⏱️ Horas de estudio](#️-horas-de-estudio)
- [🗓️ Horario](#️-horario)
- [🧹 Limpiar el chat](#-limpiar-el-chat)
- [🚀 Instalación](#-instalación)
- [☁️ Tenerlo encendido 24/7](#️-tenerlo-encendido-247)
- [⚙️ Configuración (`.env`)](#️-configuración-env)
- [🗂️ Qué crea en Notion](#️-qué-crea-en-notion)
- [🧪 Tests](#-tests)
- [📁 Estructura del proyecto](#-estructura-del-proyecto)
- [🛠️ Problemas frecuentes](#️-problemas-frecuentes)

---

## ✨ Qué hace

| | Función | Descripción |
|---|---|---|
| 📝 | **Apuntar con un mensaje** | Le escribes «Examen MAT 15/11» y lo guarda en Notion: detecta tipo, asignatura, fecha y hora. |
| ⏰ | **Avisos diarios** | Desde una semana antes de cada fecha, con un botón **✅ Hecho**. |
| 📋 | **Resumen diario** | Atrasado, próximos días, más adelante, sin fecha, tareas de cada asignatura y notas rápidas. |
| 🗓️ | **Horario** | Tus clases de hoy, mañana o cualquier día de la semana. |
| 📊 | **Notas y media** | Media ponderada por asignatura y la nota que necesitas en lo que queda para aprobar. |
| ⏱️ | **Horas de estudio** | Cronómetro por asignatura y estadísticas semanales para ver qué tienes abandonado. |
| 🎛️ | **Panel de botones** | Los comandos más usados a un toque, bajo la caja de texto. |
| 🧹 | **Limpiar el chat** | Borra la conversación de Telegram sin tocar Notion. |

> 🔒 Cada persona usa **su propio bot y su propio Notion**: nadie ve las cosas de nadie, y el bot solo responde a tu `CHAT_ID`.

---

## 💬 Cómo escribirle

Escribe con naturalidad y el bot lo entiende:

| Mensaje | Se guarda como |
|---|---|
| `Examen MAT parcial temas 1-3 15/11` | 📝 Examen · Matemáticas · 15 nov |
| `Entrega PROG práctica 2 el 20/10 a las 23:59` | 📦 Entrega · Programación · 20 oct 23:59 |
| `Tarea física repasar el tema 4 mañana` | ✏️ Tarea · Física · mañana |
| `Estudiar historia el viernes` | ✏️ Tarea · Historia · próximo viernes |
| `Comprar folios` | ✏️ Tarea sin fecha (sale en el resumen, sin avisos) |

- **Tipo** (primera palabra, opcional): `examen`, `entrega` o `tarea`. Si no la pones lo deduce: *parcial/final* → examen, *práctica/memoria/trabajo* → entrega y, si no, tarea.
- **Asignatura**: su nombre o abreviatura tal como estén en la base **Asignaturas** de Notion. En *Abreviatura* puedes poner varios alias separados por comas (`MAT, mates, cálculo`): el primero es el que se muestra y cualquiera sirve al escribir.
- **Fechas**: `15/11`, `15/11/2026`, `15 de noviembre`, `hoy`, `mañana`, `pasado mañana`, `el viernes`, `en 3 días`.
- **Hora** (opcional): `10:30`, `23h59`, `a las 9`.
- **Notas**: lo que escribas en una **segunda línea** se guarda como notas.
- Tras guardar te responde con lo que ha entendido y un botón **↩️ Deshacer**.

---

## 🎛️ Panel de botones

Bajo la caja de texto tienes siempre un panel. Si no lo ves, manda `/ayuda`.

```
 Panel principal                    📋 Comandos
┌──────────────┬──────────────┐    ┌────────────────┬──────────────┐
│   ❓ Ayuda   │   📊 Notas   │    │ 📋 Pendientes  │  🗓 Horario  │
├──────────────┼──────────────┤ ─▶ ├────────────────┼──────────────┤
│  ⏱ Estudiar  │ 📋 Comandos  │    │   🔔 Avisos    │   ✅ Hecho   │
└──────────────┴──────────────┘    ├────────────────┼──────────────┤
                                   │ 📝 Apuntar nota│   ⏹ Parar    │
                                   ├────────────────┼──────────────┤
                                   │    📈 Stats    │  ⬅️ Volver   │
                                   └────────────────┴──────────────┘
```

**🗓 Horario** abre un teclado con los días de la semana: pulsa uno para ver sus clases, o 📋 Comandos para volver.

**📊 Notas** y **⏱ Estudiar** te enseñan un botón por cada asignatura de Notion: pulsa la que quieras (en Notas también hay **📊 Todas**).

```
Tú:   [📊 Notas]
Bot:  📊 ¿De qué asignatura quieres ver las notas?
      [ IGV ] [ BBDD ] [ SO ]
      [     📊 Todas      ]
Tú:   (pulsas IGV)   ← equivale a /notas IGV
```

**📝 Apuntar nota** necesita más datos: el bot te pregunta lo que falta, con una pista en la caja de texto, y lo ejecuta cuando respondes.

En el resumen de **📋 Pendientes** cada examen, entrega y tarea con fecha muestra cuántos días quedan (o cuántos lleva atrasado).

---

## ⌨️ Comandos

También están en el botón **Menú** de Telegram.

| Comando | Qué hace | Ejemplo |
|---|---|---|
| `/pendientes` | Resumen de todo lo pendiente ahora mismo | `/pendientes` |
| `/avisos` | Los avisos de hoy (útil para probar) | `/avisos` |
| `/hecho` | Lista de pendientes para marcar como hechos | `/hecho` |
| `/horario` | Clases de un día | `/horario mañana` |
| `/nota` | Apunta una nota con su peso | `/nota IGV práctica1 8.5 30%` |
| `/notas` | Media y nota necesaria para aprobar | `/notas IGV` |
| `/estudiar` | Empieza a contar tiempo de estudio | `/estudiar BBDD` |
| `/parar` | Termina y guarda la sesión de estudio | `/parar` |
| `/stats` | Horas de estudio por asignatura esta semana | `/stats` |
| `/comandos` | Abre el panel con el resto de comandos | `/comandos` |
| `/clear` | Limpia el chat (pide confirmación) | `/clear 50` |
| `/ayuda` | Cómo usar el bot y muestra el panel | `/ayuda` |
| `/id` | Muestra el id de este chat | `/id` |

---

## 📊 Notas y media

```
/nota IGV práctica1 8.5 30%
        │    │       │   └─ peso en la nota final (vale 30 o 30%)
        │    │       └───── nota sobre 10 (vale 8.5 o 8,5)
        │    └───────────── nombre (puede tener varias palabras; si no lo pones: «Nota»)
        └────────────────── asignatura (nombre, abreviatura o alias)
```

`/notas IGV` responde algo así:

```
📊 Notas de Informática Gráfica

• Práctica1: 8,5 (30 %)
• Parcial: 6 (30 %)

Media de lo evaluado: 7,25 (60 % de la nota)
Llevas 4,35 puntos de 10.

🎯 Para aprobar necesitas un 1,63 de media en el 40 % que queda.
```

También te avisa si **ya tienes el aprobado asegurado**, si **no llegas ni con un 10** o si **ya está todo evaluado**. `/notas` a secas resume todas las asignaturas en una línea cada una.

**Cómo se calcula:**

```
puntos      = Σ (nota × peso) / 100
media       = Σ (nota × peso) / Σ peso
restante    = 100 − Σ peso
necesaria   = (5 − puntos) / (restante / 100)
```

---

## ⏱️ Horas de estudio

1. `/estudiar BBDD` → empieza a contar.
2. `/parar` → guarda la sesión y te dice cuánto llevas esta semana en esa asignatura.
3. `/stats` → horas por asignatura desde el lunes:

```
📈 Horas de estudio esta semana (desde el lunes 19 de octubre)

BBDD ▓▓▓▓▓▓▓▓▓▓ 3 h 20 min
IGV  ▓▓ 45 min

Total: 4 h 5 min

😴 Sin tocar esta semana: MAT
```

> 💡 La sesión en curso se guarda en Notion, no en la memoria del bot: si el bot se reinicia mientras estudias, `/parar` sigue funcionando.

---

## 🗓️ Horario

`/horario` te dice las clases de hoy; también `/horario mañana`, `/horario pasado mañana` o `/horario viernes`.

Lee la base **Horario** de Notion: una fila por clase con *Día*, *Inicio* y *Fin* (por ejemplo `9:30` y `11:30`), *Tipo* (Teoría/Prácticas) y *Notas* opcionales (aula, profesor...).

---

## 🧹 Limpiar el chat

`/clear` borra los últimos 500 mensajes de la conversación (o `/clear 50` para los últimos 50, máximo 3000) tras pedir confirmación con **🧹 Sí, limpiar / Cancelar**.

- Solo borra la conversación de Telegram: **Notion no se toca**.
- Telegram no deja borrar mensajes de **más de 48 horas**; esos se quedan.

---

## 🚀 Instalación

> Necesitas **Python 3.10 o superior**, una cuenta de **Telegram** y una de **Notion**.

### 1️⃣ Descargar

```bash
git clone https://github.com/Callydev05/CuatriBOT.git
cd CuatriBOT
python -m venv .venv
# Windows:  .venv\Scripts\activate      Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

> En Windows, si `python` o `pip` no se reconocen, usa `py` (por ejemplo `py -m venv .venv`).

### 2️⃣ Crear tu bot de Telegram

En Telegram abre **@BotFather** → `/newbot`, ponle nombre y usuario (acabado en `bot`) y copia el **token** en `TELEGRAM_TOKEN` del `.env`.

### 3️⃣ Preparar Notion

1. Ve a <https://www.notion.so/profile/integrations> → **Nueva integración** (tipo **Interna**) y copia su token en `NOTION_TOKEN` del `.env`.
2. En Notion crea una página vacía (por ejemplo **Estudios**).
3. En la integración pulsa **Edit access** y marca esa página (o desde la página: `•••` → **Conexiones** → tu integración).
4. Copia el enlace de la página (`•••` → **Copiar enlace**) y ejecuta:

   ```bash
   python setup_notion.py "<enlace de tu página>"
   ```

   Te pedirá tus asignaturas (`Matemáticas:MAT, Programación:PROG, Física, ...`), creará todo dentro de la página y guardará los IDs en el `.env`. Después rellena la base **Horario** con tus clases.

> 🔄 **¿Actualizas desde una versión anterior?** Vuelve a ejecutar el mismo comando: solo crea lo que falte en el `.env` (por ejemplo *Notas* y *Sesiones de estudio*) y no toca lo que ya tienes.

### 4️⃣ Arrancar

```bash
python bot.py
```

Mándale `/start` a tu bot: te dirá tu **CHAT_ID**. Ponlo en el `.env`, para el bot (`Ctrl+C`) y vuelve a arrancarlo. A partir de ahí solo te responde a ti.

### ✅ Primera prueba

1. `Examen prueba en 3 días` → se guarda en Notion.
2. `/avisos` y `/pendientes` → aparece el examen.
3. Bórralo con **↩️ Deshacer**.

---

## ☁️ Tenerlo encendido 24/7

Los avisos diarios solo llegan si el bot está en marcha.

> ⚠️ **No ejecutes el mismo bot en dos sitios a la vez** (por ejemplo, en tu PC y en el servidor): Telegram solo deja a uno recibir mensajes y el otro dará error de conflicto.

### Opción A · Servidor Linux (VPS, Raspberry Pi...)

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/Callydev05/CuatriBOT.git && cd CuatriBOT
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
nano .env                         # pega aquí tu .env
sudo cp cuatribot.service /etc/systemd/system/   # antes cambia usuario y rutas dentro
sudo systemctl daemon-reload && sudo systemctl enable --now cuatribot
journalctl -u cuatribot -f        # ver el log
```

Se reinicia solo si falla o si se reinicia el servidor.

### Opción B · Render (u otro hosting similar)

1. Crea un **Web Service** desde tu repositorio de GitHub.
2. *Build command*: `pip install -r requirements.txt` · *Start command*: `python bot.py`.
3. Copia las variables de tu `.env` en **Environment** (todas, incluidos los `..._DB_ID`).

Si el hosting define la variable `PORT`, el bot abre una mini web que responde `ok`, para que el hosting lo dé por vivo.

---

## ⚙️ Configuración (`.env`)

| Variable | Obligatoria | Por defecto | Descripción |
|---|:---:|---|---|
| `TELEGRAM_TOKEN` | ✅ | — | Token de tu bot (@BotFather) |
| `NOTION_TOKEN` | ✅ | — | Token de tu integración de Notion |
| `CHAT_ID` | ✅ | — | Tu chat con el bot (te lo dice `/start`) |
| `HORA_RESUMEN` | | `09:00` | Hora de los avisos y el resumen diario |
| `ZONA_HORARIA` | | `Europe/Madrid` | Zona horaria en formato IANA |
| `DIAS_AVISO` | | `7` | Días de antelación de los avisos |
| `EXAMENES_DB_ID` | ✅ | *setup* | Base «Exámenes y entregas» |
| `ASIGNATURAS_DB_ID` | ✅ | *setup* | Base «Asignaturas» |
| `NOTAS_RAPIDAS_PAGE_ID` | | *setup* | Página «Notas rápidas» |
| `HORARIO_DB_ID` | | *setup* | Base «Horario» (para `/horario`) |
| `NOTAS_DB_ID` | | *setup* | Base «Notas» (para `/nota` y `/notas`) |
| `ESTUDIO_DB_ID` | | *setup* | Base «Sesiones de estudio» (para `/estudiar`, `/parar` y `/stats`) |

*setup* = lo rellena solo `python setup_notion.py`. Reinicia el bot tras cambiar cualquier variable.

---

## 🗂️ Qué crea en Notion

```
📄 Estudios (tu página)
├── 🗃 Asignaturas            Asignatura · Abreviatura (+ lista de tareas en cada página)
├── 🗃 Exámenes y entregas    Nombre · Tipo · Asignatura · Fecha · Hecho · Notas
├── 🗃 Horario                Clase · Día · Inicio · Fin · Tipo · Notas
├── 🗃 Notas                  Nombre · Asignatura · Nota · Peso
├── 🗃 Sesiones de estudio    Nombre · Asignatura · Inicio · Minutos
└── ⚡ Notas rápidas          casillas que salen en el resumen diario
```

Puedes editar todo directamente en Notion: el bot lee siempre lo que haya allí.

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

Prueban la lógica que no depende de Telegram ni de Notion: `calculos.py` (medias, nota necesaria, minutos de estudio, formatos) y la búsqueda de asignaturas.

---

## 📁 Estructura del proyecto

```
CuatriBOT/
├── bot.py               Telegram: comandos, panel, botones, avisos y resumen diario
├── parsing.py           Entiende los mensajes (tipo, asignatura, fecha, hora)
├── calculos.py          Medias, nota para aprobar y horas de estudio (sin Telegram ni Notion)
├── notion_api.py        Lee y escribe en Notion
├── setup_notion.py      Crea la estructura de Notion (o solo lo que falte)
├── tests/               Tests con pytest
├── cuatribot.service    Servicio systemd para dejarlo 24/7 en Linux
├── requirements.txt     Dependencias del bot
├── requirements-dev.txt Dependencias para desarrollo (pytest)
└── .env.example         Plantilla de configuración
```

---

## 🛠️ Problemas frecuentes

| Síntoma | Solución |
|---|---|
| El bot no responde | Comprueba que está en marcha y que `CHAT_ID` es el tuyo (`/id`). |
| `404` / `object_not_found` | La integración no está conectada a tu página: `•••` → **Conexiones** → tu integración. |
| `401` / `unauthorized` | El `NOTION_TOKEN` del `.env` está mal. |
| `Conflict: terminated by other getUpdates request` | El bot está encendido en dos sitios a la vez: apaga uno. |
| «No tengo configuradas las notas / el registro de estudio» | Ejecuta otra vez `python setup_notion.py "<enlace>"` y reinicia el bot (en un hosting, añade `NOTAS_DB_ID` y `ESTUDIO_DB_ID`). |
| No veo el panel de botones | Manda `/ayuda`. |
| `/clear` no borra mensajes antiguos | Telegram no deja borrar mensajes de más de 48 horas. |
| No reconoce una asignatura | Añade el alias en el campo *Abreviatura* de Notion, separado por comas. |
