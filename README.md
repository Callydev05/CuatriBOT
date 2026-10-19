# CuatriBOT · Telegram ↔ Notion

Bot de Telegram para organizar los estudios con Notion: apuntas exámenes, entregas y tareas con un mensaje, y el bot te avisa cada día desde una semana antes y te manda un resumen de todo lo pendiente.

- **Le escribes y lo guarda en Notion**: detecta solo si es examen, entrega o tarea, la asignatura, la fecha y la hora.
- **Avisos diarios desde una semana antes** de cada fecha, con botón ✅ Hecho.
- **Resumen diario** de todo lo pendiente: atrasado, próximos días, más adelante, sin fecha, las casillas sin marcar de cada asignatura y las notas rápidas.

Cada persona usa **su propio bot y su propio Notion**: nadie ve las cosas de nadie.

## Cómo escribirle

| Mensaje | Se guarda como |
|---|---|
| `Examen MAT parcial temas 1-3 15/11` | Examen · Matemáticas · 15 nov |
| `Entrega PROG práctica 2 el 20/10 a las 23:59` | Entrega · Programación · 20 oct 23:59 |
| `Tarea física repasar el tema 4 mañana` | Tarea · Física · mañana |
| `Estudiar historia el viernes` | Tarea · Historia · próximo viernes |
| `Comprar folios` | Tarea sin fecha (sale en el resumen, sin avisos) |

- Primera palabra opcional: `examen`, `entrega` o `tarea`. Si no la pones, lo deduce (*parcial* → examen, *práctica/memoria* → entrega, si no → tarea).
- **Asignatura**: su nombre o su abreviatura, tal como estén en la base **Asignaturas** de Notion. En el campo *Abreviatura* puedes poner varios alias separados por comas, por ejemplo `MAT, mates, cálculo`: el primero es el que se muestra y cualquiera de ellos sirve al escribir.
- **Fechas**: `15/11`, `15/11/2026`, `15 de noviembre`, `hoy`, `mañana`, `pasado mañana`, `el viernes`, `en 3 días`. Hora opcional: `10:30`, `23h59`, `a las 9`.
- Lo que escribas en una **segunda línea** se guarda como notas.
- Tras guardar te responde con lo que ha entendido y un botón **↩️ Deshacer**.

Comandos: `/pendientes`, `/horario`, `/avisos` (los avisos de hoy, para probar), `/hecho`, `/nota`, `/notas`, `/estudiar`, `/parar`, `/stats`, `/comandos`, `/clear`, `/ayuda`, `/id`.

**Panel de botones:** bajo la caja de texto tienes *❓ Ayuda*, *📊 Notas*, *⏱ Estudiar* y *📋 Comandos* (este último abre el resto de comandos; *⬅️ Volver* regresa). Los botones de comandos que necesitan datos (Notas, Estudiar, Apuntar nota) no ejecutan nada: te preguntan lo que falta y lo ejecutan cuando respondes. Si no ves el panel, manda `/ayuda`.

**Limpiar el chat:** `/clear` borra los últimos 500 mensajes de la conversación (o `/clear 50` para los últimos 50) tras pedir confirmación. Solo afecta a Telegram, no a Notion, y Telegram no deja borrar mensajes de más de 48 horas.

**Horario:** `/horario` te dice las clases de hoy; también `/horario mañana` o `/horario viernes`. Lee la base de datos **Horario** de Notion: una fila por clase con *Día*, *Inicio* y *Fin* (por ejemplo `9:30` y `11:30`), *Tipo* (Teoría/Prácticas) y *Notas* opcionales (aula, profesor...).

**Notas:** `/nota IGV práctica1 8.5 30%` guarda en la base **Notas** que en la práctica 1 de IGV sacaste un 8,5 y que vale el 30 % de la nota final (vale `8,5` y `30` sin `%`). `/notas IGV` te dice la media de lo evaluado, los puntos que llevas sobre 10 y qué nota media necesitas en lo que queda para llegar al 5. `/notas` a secas resume todas las asignaturas.

**Horas de estudio:** `/estudiar BBDD` empieza a contar, `/parar` guarda la sesión en la base **Sesiones de estudio** y `/stats` muestra las horas por asignatura de esta semana (desde el lunes) y cuáles no has tocado. La sesión en curso se guarda en Notion, así que no se pierde aunque el bot se reinicie.

## Instalación

Necesitas **Python 3.10 o superior**.

### 1. Descargar
```bash
git clone https://github.com/Callydev05/CuatriBOT.git
cd CuatriBOT
python -m venv .venv
# Windows:  .venv\Scripts\activate      Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```
En Windows, si `python` o `pip` no se reconocen, usa `py` (por ejemplo `py -m venv .venv`).

### 2. Crear tu bot de Telegram
En Telegram, abre **@BotFather** → `/newbot`, ponle nombre y usuario (acabado en `bot`) y copia el **token** en `TELEGRAM_TOKEN` del `.env`.

### 3. Preparar Notion
1. Ve a <https://www.notion.so/profile/integrations> → **Nueva integración** (tipo **Interna**). Copia su token en `NOTION_TOKEN` del `.env`.
2. En Notion crea una página vacía (por ejemplo **Estudios**).
3. En la integración, pulsa **Edit access** y marca esa página. (O desde la página: `•••` → **Conexiones** → tu integración.)
4. Copia el enlace de la página (`•••` → **Copiar enlace**) y ejecuta:
   ```bash
   python setup_notion.py "<enlace de tu página>"
   ```
   Te pedirá tus asignaturas (`Matemáticas:MAT, Programación:PROG, Física, ...`), creará todo dentro de la página (asignaturas, exámenes y entregas, horario, notas, sesiones de estudio y notas rápidas) y guardará los IDs en el `.env`. Después rellena la base **Horario** con tus clases.

   **¿Actualizas desde una versión anterior?** Vuelve a ejecutar el mismo comando: solo crea lo que falte en el `.env` (por ejemplo *Notas* y *Sesiones de estudio*) y no toca lo que ya tienes.

### 4. Arrancar
```bash
python bot.py
```
Mándale `/start` a tu bot: te dirá tu **CHAT_ID**. Ponlo en el `.env`, para el bot (Ctrl+C) y vuelve a arrancarlo. A partir de ahí solo te responde a ti.

Prueba: `Examen prueba en 3 días`, luego `/avisos` y `/pendientes`. Bórralo con **↩️ Deshacer**.

## Tenerlo encendido 24/7

Los avisos diarios solo llegan si el bot está en marcha. Lo ideal es un servidor Linux siempre encendido (un VPS, la capa gratuita de algún proveedor cloud o una Raspberry Pi):

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/Callydev05/CuatriBOT.git && cd CuatriBOT
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
nano .env                         # pega aquí tu .env
sudo cp cuatribot.service /etc/systemd/system/   # antes cambia usuario y rutas dentro
sudo systemctl daemon-reload && sudo systemctl enable --now cuatribot
journalctl -u cuatribot -f        # ver el log
```
Se reinicia solo si falla o si se reinicia el servidor. **No ejecutes el mismo bot en dos sitios a la vez**: Telegram solo deja a uno recibir mensajes.

## Ajustes (`.env`)
- `HORA_RESUMEN`: hora de los avisos y el resumen diario (por defecto `09:00`).
- `ZONA_HORARIA`: tu zona horaria en formato IANA (por defecto `Europe/Madrid`).
- `DIAS_AVISO`: días de antelación con los que empiezan los avisos (por defecto `7`).

Reinicia el bot tras cambiarlos.

## Tests
```bash
pip install -r requirements-dev.txt
pytest
```
Prueban la lógica que no depende de Telegram ni de Notion (`calculos.py` y la búsqueda de asignaturas).

## Archivos
- `bot.py` — Telegram: mensajes, botones, avisos y resumen diario.
- `parsing.py` — entiende los mensajes (tipo, asignatura, fecha, hora).
- `calculos.py` — medias, nota necesaria para aprobar y horas de estudio (sin Telegram ni Notion).
- `tests/` — tests con pytest.
- `notion_api.py` — lee y escribe en Notion.
- `setup_notion.py` — crea la estructura de Notion para un usuario nuevo.
- `cuatribot.service` — servicio systemd para dejarlo 24/7 en Linux.
