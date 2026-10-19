"""
Bot de Telegram para el cuatrimestre.

- Cualquier mensaje que le mandes se guarda en la base "Exámenes y entregas" de Notion.
- Cada día, a la hora configurada, te manda:
    1. Un aviso por cada examen/entrega/tarea que caiga en los próximos 7 días.
    2. Un resumen con todo lo que tienes pendiente.

Comandos:
    /pendientes  resumen ahora mismo
    /avisos      los avisos de hoy ahora mismo (para probar)
    /hecho       marcar cosas como hechas
    /horario     clases de hoy (o /horario mañana, /horario viernes)
    /nota        apunta una nota: /nota IGV práctica1 8.5 30%
    /notas       media y nota necesaria para aprobar (/notas IGV, o /notas para todas)
    /estudiar    empieza a contar tiempo de estudio: /estudiar BBDD
    /parar       termina y guarda la sesión de estudio
    /stats       horas de estudio por asignatura esta semana
    /comandos    panel de botones con el resto de comandos
    /ayuda      cómo escribir los mensajes
    /id          muestra el id de este chat
"""
from __future__ import annotations

import html
import logging
import os
from datetime import date, datetime, time, timedelta

from dotenv import load_dotenv

# Antes de importar notion_api: ahí se lee ZONA_HORARIA al importar
load_dotenv()

from telegram import (BotCommand, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup,  # noqa: E402
                      ReplyKeyboardMarkup, Update)
from telegram.constants import ParseMode  # noqa: E402
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,  # noqa: E402
                          ContextTypes, MessageHandler, filters)

from calculos import (Nota, fmt_duracion, fmt_num, minutos_por_asignatura,  # noqa: E402
                      parsear_nota, resumen_notas)
from notion_api import TZ, Notion, NotionError, Pendiente  # noqa: E402
from parsing import Asignatura, analizar, buscar_asignatura, norm  # noqa: E402

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("cuatribot")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
CHAT_ID = int(os.environ.get("CHAT_ID") or 0)
EXAMENES_DB_ID = os.environ.get("EXAMENES_DB_ID", "")
ASIGNATURAS_DB_ID = os.environ.get("ASIGNATURAS_DB_ID", "")
NOTAS_RAPIDAS_PAGE_ID = os.environ.get("NOTAS_RAPIDAS_PAGE_ID", "")
HORARIO_DB_ID = os.environ.get("HORARIO_DB_ID", "")
NOTAS_DB_ID = os.environ.get("NOTAS_DB_ID", "")
ESTUDIO_DB_ID = os.environ.get("ESTUDIO_DB_ID", "")
if not (EXAMENES_DB_ID and ASIGNATURAS_DB_ID):
    raise SystemExit("Faltan EXAMENES_DB_ID y ASIGNATURAS_DB_ID en .env. Ejecuta antes: python setup_notion.py")
HORA_RESUMEN = os.environ.get("HORA_RESUMEN", "09:00")
DIAS_AVISO = int(os.environ.get("DIAS_AVISO", "7"))

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_CORTOS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
EMOJI_TIPO = {"Examen": "📝", "Entrega": "📦", "Tarea": "✏️"}

AYUDA = (
    "<b>Cómo apuntar cosas</b>\n"
    "Escríbeme y lo guardo en Notion. Ejemplos:\n"
    "• <code>Examen MAT parcial temas 1-3 15/11</code>\n"
    "• <code>Entrega PROG práctica 2 el 20/10 a las 23:59</code>\n"
    "• <code>Tarea física repasar el tema 4 mañana</code>\n"
    "• <code>Estudiar historia el viernes</code>\n"
    "• <code>Comprar folios</code> (sin fecha)\n\n"
    "Primera palabra opcional: <i>examen</i>, <i>entrega</i> o <i>tarea</i>.\n"
    "Fechas: 15/11, 15 de noviembre, hoy, mañana, el viernes, en 3 días.\n"
    "Lo que pongas en otra línea se guarda como notas.\n\n"
    f"Te aviso cada día a las {HORA_RESUMEN} desde {DIAS_AVISO} días antes de cada fecha, "
    "y te mando un resumen de todo lo pendiente.\n\n"
    "<b>Horario</b>: /horario (hoy), /horario mañana o /horario viernes\n\n"
    "<b>Notas</b>: <code>/nota IGV práctica1 8.5 30%</code> la apunta; "
    "<code>/notas IGV</code> te da la media y lo que necesitas para aprobar.\n\n"
    "<b>Estudio</b>: <code>/estudiar BBDD</code> empieza a contar, /parar lo guarda "
    "y /stats te enseña las horas de la semana.\n\n"
    "Usa los botones de abajo o escribe: /pendientes · /horario · /avisos · /hecho · /notas · /stats · "
    "/comandos · /ayuda"
)


# ---------------- utilidades de formato ----------------

def hoy() -> date:
    return datetime.now(TZ).date()


def fecha_corta(f: date, hora: str | None = None) -> str:
    s = f"{DIAS_CORTOS[f.weekday()]} {f.day} {MESES_CORTOS[f.month - 1]}"
    return f"{s} · {hora}" if hora else s


def cuanto_falta(dias: int) -> str:
    if dias < 0:
        return f"hace {-dias} día{'s' if dias != -1 else ''}"
    if dias == 0:
        return "HOY"
    if dias == 1:
        return "mañana"
    return f"en {dias} días"


def etiqueta(p: Pendiente, abrevs: dict[str, str]) -> str:
    asig = ", ".join(abrevs[a] for a in p.asignaturas if a in abrevs)
    emoji = EMOJI_TIPO.get(p.tipo, "•")
    base = f"{emoji} {html.escape(p.nombre)}"
    return f"{base} <i>({html.escape(asig)})</i>" if asig else base


def texto_aviso(p: Pendiente, abrevs: dict[str, str], ref: date) -> str:
    dias = (p.fecha - ref).days
    if dias == 0:
        cabecera = f"🚨 <b>¡HOY! {p.tipo}</b>"
    elif dias == 1:
        cabecera = f"⏰ <b>{p.tipo} mañana</b>"
    else:
        cabecera = f"⏰ <b>{p.tipo} en {dias} días</b>"
    return f"{cabecera}\n{etiqueta(p, abrevs)}\n📅 {fecha_corta(p.fecha, p.hora)}"


def texto_resumen(pend: list[Pendiente], abrevs: dict[str, str], todos_asig: dict[str, list[str]],
                  rapidas: list[str], ref: date, dias_aviso: int = DIAS_AVISO) -> str:
    atrasado = [p for p in pend if p.fecha and p.fecha < ref]
    pronto = [p for p in pend if p.fecha and 0 <= (p.fecha - ref).days <= dias_aviso]
    luego = [p for p in pend if p.fecha and (p.fecha - ref).days > dias_aviso]
    sin_fecha = [p for p in pend if not p.fecha]

    partes = [f"📋 <b>Pendientes · {DIAS[ref.weekday()]} {ref.day} de {MESES[ref.month - 1]}</b>"]

    def seccion(titulo: str, items: list[str]):
        if items:
            partes.append(f"\n<b>{titulo}</b>\n" + "\n".join(items))

    seccion("⚠️ Atrasado", [f"• {etiqueta(p, abrevs)} — {fecha_corta(p.fecha)}" for p in atrasado])
    seccion(f"🔥 Próximos {dias_aviso} días",
            [f"• <b>{cuanto_falta((p.fecha - ref).days)}</b> · {etiqueta(p, abrevs)}"
             f"{' · ' + p.hora if p.hora else ''}" for p in pronto])
    seccion("🗓 Más adelante", [f"• {fecha_corta(p.fecha)} · {etiqueta(p, abrevs)}" for p in luego])
    seccion("📌 Sin fecha", [f"• {etiqueta(p, abrevs)}" for p in sin_fecha])

    if todos_asig:
        lineas = []
        for asig, tareas in todos_asig.items():
            lineas.append(f"<u>{html.escape(asig)}</u>")
            lineas += [f"  ☐ {html.escape(t)}" for t in tareas]
        seccion("📚 Tareas en las asignaturas", lineas)
    seccion("⚡ Notas rápidas", [f"  ☐ {html.escape(t)}" for t in rapidas])

    if len(partes) == 1:
        partes.append("\n🎉 No tienes nada pendiente. ¡A disfrutar!")
    return "\n".join(partes)


def trocear(texto: str, limite: int = 4000) -> list[str]:
    trozos, actual = [], ""
    for linea in texto.split("\n"):
        if actual and len(actual) + len(linea) + 1 > limite:
            trozos.append(actual)
            actual = ""
        actual += linea + "\n"
    if actual.strip():
        trozos.append(actual)
    return trozos


def boton_hecho(page_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Hecho", callback_data=f"done:{page_id}")]])


# ---------------- lógica ----------------

def notion(ctx: ContextTypes.DEFAULT_TYPE) -> Notion:
    return ctx.application.bot_data["notion"]


def autorizado(update: Update) -> bool:
    return CHAT_ID != 0 and update.effective_chat and update.effective_chat.id == CHAT_ID


async def abrevs_por_id(n: Notion) -> dict[str, str]:
    return {a.id: a.abrev for a in await n.asignaturas()}


async def enviar_avisos(app: Application, chat_id: int) -> int:
    n: Notion = app.bot_data["notion"]
    ref = hoy()
    abrevs = await abrevs_por_id(n)
    enviados = 0
    for p in await n.pendientes():
        if p.fecha and 0 <= (p.fecha - ref).days <= DIAS_AVISO:
            await app.bot.send_message(chat_id, texto_aviso(p, abrevs, ref),
                                       parse_mode=ParseMode.HTML, reply_markup=boton_hecho(p.id))
            enviados += 1
    return enviados


async def enviar_resumen(app: Application, chat_id: int):
    n: Notion = app.bot_data["notion"]
    pend = await n.pendientes()
    abrevs = await abrevs_por_id(n)
    todos_asig, rapidas = await n.todos_por_asignatura()
    texto = texto_resumen(pend, abrevs, todos_asig, rapidas, hoy())
    for trozo in trocear(texto):
        await app.bot.send_message(chat_id, trozo, parse_mode=ParseMode.HTML,
                                   disable_web_page_preview=True)


async def tarea_diaria(ctx: ContextTypes.DEFAULT_TYPE):
    try:
        await enviar_avisos(ctx.application, CHAT_ID)
        await enviar_resumen(ctx.application, CHAT_ID)
    except Exception:
        log.exception("Fallo en el envío diario")
        await ctx.bot.send_message(CHAT_ID, "⚠️ No he podido leer Notion para el resumen de hoy. "
                                            "Prueba /pendientes en un rato.")


# ---------------- handlers ----------------

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if CHAT_ID == 0:
        await update.message.reply_text(
            f"👋 Tu CHAT_ID es <code>{chat_id}</code>.\n"
            "Ponlo en el archivo <code>.env</code> (CHAT_ID=...) y reinicia el bot.",
            parse_mode=ParseMode.HTML)
        return
    if not autorizado(update):
        return
    await update.message.reply_text("👋 ¡Listo! " + AYUDA, parse_mode=ParseMode.HTML, reply_markup=PANEL_INICIO)


async def cmd_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"CHAT_ID: <code>{update.effective_chat.id}</code>",
                                    parse_mode=ParseMode.HTML)


async def cmd_ayuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if autorizado(update):
        await update.message.reply_text(AYUDA, parse_mode=ParseMode.HTML, reply_markup=PANEL_INICIO)


async def cmd_pendientes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if autorizado(update):
        await enviar_resumen(ctx.application, update.effective_chat.id)


async def cmd_avisos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    if await enviar_avisos(ctx.application, update.effective_chat.id) == 0:
        await update.message.reply_text(f"No tienes nada en los próximos {DIAS_AVISO} días. 😌")


async def cmd_hecho(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    n = notion(ctx)
    pend = await n.pendientes()
    if not pend:
        await update.message.reply_text("No tienes nada pendiente. 🎉")
        return
    abrevs = await abrevs_por_id(n)
    botones = []
    for p in pend[:30]:
        asig = ", ".join(abrevs[a] for a in p.asignaturas if a in abrevs)
        txt = f"{EMOJI_TIPO.get(p.tipo, '•')} {p.nombre}"
        if asig:
            txt += f" ({asig})"
        if p.fecha:
            txt += f" · {p.fecha.day}/{p.fecha.month}"
        botones.append([InlineKeyboardButton(txt[:60], callback_data=f"done:{p.id}")])
    await update.message.reply_text("¿Qué has terminado?", reply_markup=InlineKeyboardMarkup(botones))


DIAS_NOTION = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
EMOJI_CLASE = {"Teoría": "📖", "Prácticas": "💻"}


def dia_pedido(args: list[str], ref: date) -> date | None:
    """Fecha a partir de lo escrito tras /horario: nada (hoy), mañana, pasado mañana o un día de la semana."""
    texto = " ".join(args).strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        texto = texto.replace(a, b)
    if texto in ("", "hoy"):
        return ref
    if texto == "manana":
        return ref + timedelta(days=1)
    if texto == "pasado manana":
        return ref + timedelta(days=2)
    sin_tildes = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
    if texto in sin_tildes:
        dias = (sin_tildes.index(texto) - ref.weekday()) % 7
        return ref + timedelta(days=dias)
    return None


def texto_horario(clases: list[dict], dia: date, ref: date) -> str:
    if dia == ref:
        cuando, de_cuando = "hoy", "de hoy"
    elif dia == ref + timedelta(days=1):
        cuando, de_cuando = "mañana", "de mañana"
    else:
        cuando, de_cuando = "el " + DIAS[dia.weekday()], "del " + DIAS[dia.weekday()]
    titulo = f"🗓 <b>Clases {de_cuando}</b> · {DIAS[dia.weekday()]} {dia.day} de {MESES[dia.month - 1]}"
    if not clases:
        return f"{titulo}\n\n😎 No tienes clases {cuando}."
    lineas = [titulo, ""]
    for c in clases:
        horas = f"{c['inicio']}–{c['fin']}" if c["fin"] else c["inicio"]
        emoji = EMOJI_CLASE.get(c["tipo"], "•")
        linea = f"{emoji} <b>{html.escape(horas)}</b>  {html.escape(c['clase'])}"
        if c["notas"]:
            linea += f"\n      <i>{html.escape(c['notas'])}</i>"
        lineas.append(linea)
    return "\n".join(lineas)


async def cmd_horario(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    if not HORARIO_DB_ID:
        await update.message.reply_text("No tengo configurado el horario. Añade HORARIO_DB_ID en el .env "
                                        "(o en las variables de entorno del hosting) y reinicia el bot.")
        return
    ref = hoy()
    dia = dia_pedido(ctx.args, ref)
    if dia is None:
        await update.message.reply_text("No te he entendido. Usa /horario, /horario mañana o /horario viernes.")
        return
    try:
        clases = await notion(ctx).clases_del_dia(DIAS_NOTION[dia.weekday()])
    except NotionError as e:
        log.error("Error leyendo el horario: %s", e)
        await update.message.reply_text("⚠️ No he podido leer el horario de Notion.")
        return
    await update.message.reply_text(texto_horario(clases, dia, ref), parse_mode=ParseMode.HTML)


# ---------------- notas ----------------

def texto_notas(asig: Asignatura, notas: list[Nota]) -> str:
    titulo = f"📊 <b>Notas de {html.escape(asig.nombre)}</b>"
    if not notas:
        return f"{titulo}\n\nAún no tienes notas. Apunta una con /nota {html.escape(asig.abrev)} práctica1 8.5 30%"
    r = resumen_notas(notas)
    lineas = [titulo, ""]
    lineas += [f"• {html.escape(n.nombre)}: <b>{fmt_num(n.nota)}</b> ({fmt_num(n.peso)} %)" for n in notas]
    lineas.append("")
    if r.peso_evaluado > 100:
        lineas.append(f"⚠️ Los pesos suman {fmt_num(r.peso_evaluado)} %, más de 100. Revisa las notas en Notion.")
    if r.media is not None:
        lineas.append(f"Media de lo evaluado: <b>{fmt_num(r.media)}</b> ({fmt_num(r.peso_evaluado)} % de la nota)")
    lineas.append(f"Llevas <b>{fmt_num(r.puntos)}</b> puntos de 10.")
    if r.necesaria is None:
        estado = "✅ aprobada" if r.puntos >= 5 else "❌ suspensa"
        lineas.append(f"\n🏁 Todo evaluado: nota final <b>{fmt_num(r.puntos)}</b>, {estado}.")
    elif r.necesaria <= 0:
        lineas.append(f"\n✅ Ya tienes el aprobado asegurado, saques lo que saques en el {fmt_num(r.restante)} % que queda.")
    elif r.necesaria > 10:
        lineas.append(f"\n😬 Ni con un 10 en el {fmt_num(r.restante)} % que queda llegas al 5.")
    else:
        lineas.append(f"\n🎯 Para aprobar necesitas un <b>{fmt_num(r.necesaria)}</b> "
                      f"de media en el {fmt_num(r.restante)} % que queda.")
    return "\n".join(lineas)


def texto_todas_notas(asigs: list[Asignatura], notas: list[Nota]) -> str:
    lineas = ["📊 <b>Notas</b>", ""]
    for a in asigs:
        suyas = [n for n in notas if a.id in n.asignaturas]
        if not suyas:
            continue
        r = resumen_notas(suyas)
        linea = f"• <b>{html.escape(a.abrev)}</b>: llevas {fmt_num(r.puntos)} ({fmt_num(r.peso_evaluado)} % evaluado)"
        if r.necesaria is not None and 0 < r.necesaria <= 10:
            linea += f" · necesitas un {fmt_num(r.necesaria)}"
        elif r.necesaria is not None and r.necesaria <= 0:
            linea += " · ✅ aprobada"
        lineas.append(linea)
    if len(lineas) == 2:
        return "Aún no tienes notas. Apunta una con <code>/nota IGV práctica1 8.5 30%</code>"
    lineas.append("\nDetalle de una asignatura: <code>/notas IGV</code>")
    return "\n".join(lineas)


async def cmd_nota(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    if not NOTAS_DB_ID:
        await update.message.reply_text("No tengo configuradas las notas. Ejecuta otra vez setup_notion.py "
                                        "(o añade NOTAS_DB_ID en el .env) y reinicia el bot.")
        return
    try:
        alias, nombre, nota, peso = parsear_nota(ctx.args)
    except ValueError as e:
        await update.message.reply_text(f"{e}\nEjemplo: <code>/nota IGV práctica1 8.5 30%</code>",
                                        parse_mode=ParseMode.HTML)
        return
    n = notion(ctx)
    try:
        asig = buscar_asignatura(alias, await n.asignaturas())
        if not asig:
            await update.message.reply_text(f"No conozco la asignatura «{alias}». "
                                            "Usa su nombre o abreviatura de Notion.")
            return
        pagina = await n.guardar_nota(asig.id, nombre, nota, peso)
        notas = await n.notas(asig.id)
    except NotionError as e:
        log.error("Error guardando la nota: %s", e)
        await update.message.reply_text("⚠️ No he podido guardar la nota en Notion.")
        return
    texto = f"✅ <b>Guardada</b> · {html.escape(nombre)}: {fmt_num(nota)} ({fmt_num(peso)} %)\n\n"
    teclado = InlineKeyboardMarkup([[InlineKeyboardButton(
        "↩️ Deshacer", callback_data=f"undo:{pagina['id'].replace('-', '')}")]])
    await update.message.reply_text(texto + texto_notas(asig, notas), parse_mode=ParseMode.HTML,
                                    reply_markup=teclado)


async def cmd_notas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    if not NOTAS_DB_ID:
        await update.message.reply_text("No tengo configuradas las notas. Ejecuta otra vez setup_notion.py "
                                        "(o añade NOTAS_DB_ID en el .env) y reinicia el bot.")
        return
    n = notion(ctx)
    try:
        asigs = await n.asignaturas()
        if ctx.args:
            asig = buscar_asignatura(" ".join(ctx.args), asigs)
            if not asig:
                await update.message.reply_text(f"No conozco la asignatura «{' '.join(ctx.args)}».")
                return
            texto = texto_notas(asig, await n.notas(asig.id))
        else:
            texto = texto_todas_notas(asigs, await n.notas())
    except NotionError as e:
        log.error("Error leyendo las notas: %s", e)
        await update.message.reply_text("⚠️ No he podido leer las notas de Notion.")
        return
    await update.message.reply_text(texto, parse_mode=ParseMode.HTML)


# ---------------- horas de estudio ----------------

def inicio_semana(ref: date) -> date:
    return ref - timedelta(days=ref.weekday())


def texto_stats(minutos: dict[str, int], asigs: list[Asignatura], desde: date) -> str:
    lineas = [f"📈 <b>Horas de estudio esta semana</b> (desde el {DIAS[desde.weekday()]} "
              f"{desde.day} de {MESES[desde.month - 1]})", ""]
    nombres = {a.id: a.abrev for a in asigs}
    nombres[""] = "Sin asignatura"
    filas = sorted(((m, nombres.get(a, "?")) for a, m in minutos.items() if m > 0), reverse=True)
    if not filas:
        lineas.append("Aún no has estudiado nada esta semana. Empieza con <code>/estudiar BBDD</code>")
    else:
        maximo = filas[0][0]
        for m, nombre in filas:
            barra = "▓" * max(1, round(10 * m / maximo))
            lineas.append(f"<b>{html.escape(nombre)}</b> {barra} {fmt_duracion(m)}")
        lineas.append(f"\nTotal: <b>{fmt_duracion(sum(m for m, _ in filas))}</b>")
    olvidadas = [a.abrev for a in asigs if not minutos.get(a.id)]
    if olvidadas:
        lineas.append(f"\n😴 Sin tocar esta semana: {html.escape(', '.join(olvidadas))}")
    return "\n".join(lineas)


async def comprobar_estudio(update: Update) -> bool:
    if ESTUDIO_DB_ID:
        return True
    await update.message.reply_text("No tengo configurado el registro de estudio. Ejecuta otra vez "
                                    "setup_notion.py (o añade ESTUDIO_DB_ID en el .env) y reinicia el bot.")
    return False


async def cmd_estudiar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update) or not await comprobar_estudio(update):
        return
    if not ctx.args:
        await update.message.reply_text("¿Qué vas a estudiar? Ejemplo: <code>/estudiar BBDD</code>",
                                        parse_mode=ParseMode.HTML)
        return
    n = notion(ctx)
    try:
        asigs = await n.asignaturas()
        asig = buscar_asignatura(" ".join(ctx.args), asigs)
        if not asig:
            await update.message.reply_text(f"No conozco la asignatura «{' '.join(ctx.args)}».")
            return
        actual = await n.estudio_en_curso()
        if actual:
            abrevs = {a.id: a.abrev for a in asigs}
            de_que = ", ".join(abrevs.get(a, "?") for a in actual.asignaturas) or "algo"
            await update.message.reply_text(f"Ya estás estudiando {de_que} desde las "
                                            f"{actual.inicio:%H:%M}. Usa /parar antes de empezar otra.")
            return
        await n.empezar_estudio(asig)
    except NotionError as e:
        log.error("Error empezando a estudiar: %s", e)
        await update.message.reply_text("⚠️ No he podido guardar la sesión en Notion.")
        return
    await update.message.reply_text(f"⏱ Empiezo a contar <b>{html.escape(asig.nombre)}</b> "
                                    f"({datetime.now(TZ):%H:%M}). Cuando acabes: /parar",
                                    parse_mode=ParseMode.HTML)


async def cmd_parar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update) or not await comprobar_estudio(update):
        return
    n = notion(ctx)
    try:
        sesion = await n.estudio_en_curso()
        if not sesion:
            await update.message.reply_text("No estabas estudiando nada. Empieza con /estudiar BBDD")
            return
        minutos = int((datetime.now(TZ) - sesion.inicio).total_seconds() // 60)
        if minutos < 1:
            await n.borrar(sesion.id)
            await update.message.reply_text("Ha sido menos de un minuto, no lo guardo.")
            return
        await n.terminar_estudio(sesion.id, minutos)
        desde = inicio_semana(hoy())
        semana = minutos_por_asignatura(await n.sesiones_desde(desde), desde)
        abrevs = await abrevs_por_id(n)
    except NotionError as e:
        log.error("Error parando el estudio: %s", e)
        await update.message.reply_text("⚠️ No he podido guardar la sesión en Notion.")
        return
    lineas = [f"✅ Guardado: <b>{fmt_duracion(minutos)}</b>"]
    for a in sesion.asignaturas:
        lineas[0] += f" de {html.escape(abrevs.get(a, '?'))}"
        # max(): la consulta de Notion puede no ver aún la sesión que acabamos de cerrar
        lineas.append(f"Esta semana llevas {fmt_duracion(max(semana.get(a, 0), minutos))} en "
                      f"{html.escape(abrevs.get(a, '?'))}.")
    await update.message.reply_text("\n".join(lineas), parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update) or not await comprobar_estudio(update):
        return
    n = notion(ctx)
    desde = inicio_semana(hoy())
    try:
        sesiones = await n.sesiones_desde(desde)
        asigs = await n.asignaturas()
    except NotionError as e:
        log.error("Error leyendo las sesiones de estudio: %s", e)
        await update.message.reply_text("⚠️ No he podido leer las horas de estudio de Notion.")
        return
    texto = texto_stats(minutos_por_asignatura(sesiones, desde), asigs, desde)
    en_curso = next((s for s in sesiones if s.minutos is None), None)
    if en_curso:
        texto += f"\n\n⏱ Ahora mismo estás estudiando (desde las {en_curso.inicio:%H:%M}). /parar para guardarlo."
    await update.message.reply_text(texto, parse_mode=ParseMode.HTML)


# ---------------- panel de botones ----------------
# Teclado fijo bajo la caja de texto. Cada botón manda su texto como un mensaje normal: on_panel lo
# reconoce y ejecuta el comando o, si al comando le faltan datos, se los pide (ForceReply).

# Comandos que necesitan datos: (pregunta, pista gris en la caja de texto, comando)
PREGUNTAS = {
    "notas": ("📊 ¿De qué asignatura? Escribe su abreviatura (por ejemplo IGV) o «todas».",
              "IGV, BBDD o todas", cmd_notas),
    "estudiar": ("⏱ ¿Qué vas a estudiar? Escribe la asignatura.", "BBDD", cmd_estudiar),
    "nota": ("📝 Escribe asignatura, nombre, nota y peso.\nEjemplo: IGV práctica1 8.5 30%",
             "IGV práctica1 8.5 30%", cmd_nota),
}

# Texto del botón → comando sin datos (función) o que los pide (clave de PREGUNTAS)
BOTONES = {
    "❓ Ayuda": cmd_ayuda,
    "📊 Notas": "notas",
    "⏱ Estudiar": "estudiar",
    "📋 Comandos": "comandos",
    "📋 Pendientes": cmd_pendientes,
    "🗓 Horario": cmd_horario,
    "🔔 Avisos": cmd_avisos,
    "✅ Hecho": cmd_hecho,
    "📝 Apuntar nota": "nota",
    "⏹ Parar": cmd_parar,
    "📈 Stats": cmd_stats,
    "⬅️ Volver": "volver",
}

PANEL_INICIO = ReplyKeyboardMarkup([["❓ Ayuda", "📊 Notas"], ["⏱ Estudiar", "📋 Comandos"]],
                                   resize_keyboard=True, is_persistent=True)
PANEL_COMANDOS = ReplyKeyboardMarkup(
    [["📋 Pendientes", "🗓 Horario"], ["🔔 Avisos", "✅ Hecho"],
     ["📝 Apuntar nota", "⏹ Parar"], ["📈 Stats", "⬅️ Volver"]],
    resize_keyboard=True, is_persistent=True)


async def cmd_comandos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if autorizado(update):
        await update.message.reply_text("📋 Resto de comandos. Pulsa ⬅️ Volver para el panel principal.",
                                        reply_markup=PANEL_COMANDOS)


async def preguntar(update: Update, ctx: ContextTypes.DEFAULT_TYPE, clave: str):
    pregunta, pista, _ = PREGUNTAS[clave]
    msg = await update.message.reply_text(
        pregunta, reply_markup=ForceReply(selective=True, input_field_placeholder=pista))
    # La respuesta a este mensaje se tomará como los datos del comando (ver on_mensaje)
    ctx.user_data["pendiente"] = {"comando": clave, "msg_id": msg.message_id}


async def on_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    ctx.user_data.pop("pendiente", None)
    accion = BOTONES[update.message.text]
    if accion == "comandos":
        await cmd_comandos(update, ctx)
    elif accion == "volver":
        await update.message.reply_text("Panel principal.", reply_markup=PANEL_INICIO)
    elif isinstance(accion, str):
        await preguntar(update, ctx, accion)
    else:
        ctx.args = []  # como si se hubiera escrito el comando sin nada detrás
        await accion(update, ctx)


async def responder_pregunta(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """Si el mensaje responde a una pregunta del panel, ejecuta ese comando con lo escrito."""
    pendiente = ctx.user_data.get("pendiente")
    respuesta_a = update.message.reply_to_message
    if not (pendiente and respuesta_a and respuesta_a.message_id == pendiente["msg_id"]):
        return False
    del ctx.user_data["pendiente"]
    clave = pendiente["comando"]
    texto = update.message.text.strip()
    ctx.args = [] if clave == "notas" and norm(texto) == "todas" else texto.split()
    await PREGUNTAS[clave][2](update, ctx)
    return True


async def on_mensaje(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update):
        return
    if await responder_pregunta(update, ctx):
        return
    n = notion(ctx)
    ref = hoy()
    try:
        entrada = analizar(update.message.text, await n.asignaturas(), ref)
        pagina = await n.crear(entrada)
    except Exception as e:
        log.error("No se pudo guardar en Notion: %s", e)
        await update.message.reply_text(
            "⚠️ No he podido guardarlo en Notion.\n\n"
            f"<code>{html.escape(str(e)[:300])}</code>\n\n"
            "Si pone 404 o object_not_found: conecta la integración a la página Cuatrimestre "
            "(••• → Conexiones). Si pone 401 o unauthorized: el NOTION_TOKEN del .env está mal.",
            parse_mode=ParseMode.HTML)
        return

    lineas = [f"✅ <b>Guardado</b> · {EMOJI_TIPO.get(entrada.tipo, '')} {entrada.tipo}",
              f"<b>{html.escape(entrada.nombre)}</b>"]
    if entrada.asignatura:
        lineas.append(f"📚 {html.escape(entrada.asignatura.nombre)}")
    if entrada.fecha:
        hora = f"{entrada.hora[0]:02d}:{entrada.hora[1]:02d}" if entrada.hora else None
        dias = (entrada.fecha - ref).days
        lineas.append(f"📅 {fecha_corta(entrada.fecha, hora)} ({cuanto_falta(dias)})")
        if dias > DIAS_AVISO:
            lineas.append(f"🔔 Te aviso a diario desde {DIAS_AVISO} días antes.")
    else:
        lineas.append("📌 Sin fecha: saldrá en el resumen diario, pero sin avisos.")
    if entrada.notas:
        lineas.append(f"🗒 {html.escape(entrada.notas)}")

    page_id = pagina["id"].replace("-", "")
    teclado = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Deshacer", callback_data=f"undo:{page_id}")]])
    await update.message.reply_text("\n".join(lineas), parse_mode=ParseMode.HTML, reply_markup=teclado)


async def on_boton(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not autorizado(update):
        await q.answer()
        return
    accion, _, page_id = q.data.partition(":")
    n = notion(ctx)
    try:
        if accion == "done":
            await n.marcar_hecho(page_id)
            await q.answer("Marcado como hecho ✅")
            if q.message.text and q.message.text.startswith("¿Qué has terminado?"):
                # Quitamos el botón pulsado de la lista
                filas = [f for f in q.message.reply_markup.inline_keyboard
                         if f[0].callback_data != q.data]
                if filas:
                    await q.edit_message_reply_markup(InlineKeyboardMarkup(filas))
                else:
                    await q.edit_message_text("Todo hecho. 🎉")
            else:
                await q.edit_message_text(q.message.text_html + "\n\n✅ <b>Hecho</b>",
                                          parse_mode=ParseMode.HTML)
        elif accion == "undo":
            await n.borrar(page_id)
            await q.answer("Borrado")
            await q.edit_message_text("🗑 Borrado (está en la papelera de Notion).")
        else:
            await q.answer()
    except NotionError as e:
        log.error("Error con el botón: %s", e)
        await q.answer("No he podido actualizar Notion", show_alert=True)


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    log.error("Error no controlado", exc_info=ctx.error)


async def post_init(app: Application):
    app.bot_data["notion"] = Notion(NOTION_TOKEN, EXAMENES_DB_ID, ASIGNATURAS_DB_ID, NOTAS_RAPIDAS_PAGE_ID,
                                    HORARIO_DB_ID, NOTAS_DB_ID, ESTUDIO_DB_ID)
    # Lista del botón "Menú" de Telegram
    await app.bot.set_my_commands([
        BotCommand("ayuda", "Cómo usar el bot y mostrar el panel"),
        BotCommand("comandos", "Panel con el resto de comandos"),
        BotCommand("pendientes", "Resumen de lo pendiente"),
        BotCommand("horario", "Clases de hoy (o mañana, viernes...)"),
        BotCommand("nota", "Apuntar nota: IGV práctica1 8.5 30%"),
        BotCommand("notas", "Media y nota para aprobar: IGV"),
        BotCommand("estudiar", "Empezar a contar estudio: BBDD"),
        BotCommand("parar", "Terminar y guardar el estudio"),
        BotCommand("stats", "Horas de estudio de la semana"),
        BotCommand("hecho", "Marcar cosas como hechas"),
        BotCommand("avisos", "Avisos de hoy"),
    ])
    if CHAT_ID:
        h, m = (int(x) for x in HORA_RESUMEN.split(":"))
        app.job_queue.run_daily(tarea_diaria, time=time(h, m, tzinfo=TZ), name="diario")
        log.info("Resumen diario programado a las %s (%s)", HORA_RESUMEN, TZ.key)
    else:
        log.warning("CHAT_ID vacío: manda /start al bot para obtenerlo y ponlo en .env")


async def post_shutdown(app: Application):
    n = app.bot_data.get("notion")
    if n:
        await n.close()


def iniciar_web_salud():
    """Mini web para hostings tipo Render que exigen un puerto abierto.
    Solo se activa si existe la variable PORT. Responde "ok" a cualquier visita."""
    puerto = os.environ.get("PORT")
    if not puerto:
        return
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Salud(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass  # sin ruido en los logs

    servidor = HTTPServer(("0.0.0.0", int(puerto)), Salud)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    log.info("Web de salud escuchando en el puerto %s", puerto)


def main():
    iniciar_web_salud()
    app = (Application.builder().token(TELEGRAM_TOKEN)
           .post_init(post_init).post_shutdown(post_shutdown).build())
    # Solo mensajes nuevos: al editar un mensaje update.message es None (y se guardaría dos veces)
    nuevos = filters.UpdateType.MESSAGE
    app.add_handler(CommandHandler("start", cmd_start, filters=nuevos))
    app.add_handler(CommandHandler("id", cmd_id, filters=nuevos))
    app.add_handler(CommandHandler(["ayuda", "help"], cmd_ayuda, filters=nuevos))
    app.add_handler(CommandHandler("pendientes", cmd_pendientes, filters=nuevos))
    app.add_handler(CommandHandler("avisos", cmd_avisos, filters=nuevos))
    app.add_handler(CommandHandler("hecho", cmd_hecho, filters=nuevos))
    app.add_handler(CommandHandler("horario", cmd_horario, filters=nuevos))
    app.add_handler(CommandHandler("nota", cmd_nota, filters=nuevos))
    app.add_handler(CommandHandler("notas", cmd_notas, filters=nuevos))
    app.add_handler(CommandHandler("estudiar", cmd_estudiar, filters=nuevos))
    app.add_handler(CommandHandler("parar", cmd_parar, filters=nuevos))
    app.add_handler(CommandHandler("stats", cmd_stats, filters=nuevos))
    app.add_handler(CommandHandler("comandos", cmd_comandos, filters=nuevos))
    app.add_handler(CallbackQueryHandler(on_boton))
    # Antes que on_mensaje: si no, el texto de los botones se guardaría como tarea
    app.add_handler(MessageHandler(nuevos & filters.Text(list(BOTONES)), on_panel))
    app.add_handler(MessageHandler(nuevos & filters.TEXT & ~filters.COMMAND, on_mensaje))
    app.add_error_handler(on_error)
    log.info("Bot en marcha")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
