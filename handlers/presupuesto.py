"""
Handler de /presupuesto — Gestión de presupuestos, consulta y ejecución presupuestal.
"""
import os
import logging
from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from config import EXPORTS_DIR, EXCEL_TEMPLATE
from utils import boton_menu, agregar_boton_menu, botones_menu_cancelar

logger = logging.getLogger(__name__)

# ─── Estados FSM ───

class PresupuestoStates(StatesGroup):
    esperando_anio = State()
    esperando_area = State()
    editando_categoria = State()

# ─── Estructura de costos sugerida ───

FEPCAFE_CATEGORIAS = [
    ("recoleccion", "☕ Recolección", 54, 5320),
    ("fertilizacion", "🧪 Fertilización", 19, 1860),
    ("administrativo", "📋 Gastos Admin/Financieros", 7, 650),
    ("arvenses", "🌿 Manejo de Arvenses", 6, 620),
    ("beneficio", "🏭 Beneficio", 6, 610),
    ("instalacion", "🌱 Renovación", 5, 530),
    ("fitosanitario", "🛡️ Fitosanitarios", 2, 170),
    ("otras_labores", "🔧 Otras labores", 1, 40),
]

COSTO_TOTAL_POR_KG = 9790  # $/kg CPS


def _formato_pesos(monto: float) -> str:
    """Formatea un número como pesos colombianos: $1,234,567"""
    return f"${monto:,.0f}"


def _formato_pct(valor: float) -> str:
    """Formatea un porcentaje."""
    return f"{valor:.1f}%"


def _emoji_diferencia(diferencia: float) -> str:
    """Retorna emoji según diferencia positiva/negativa."""
    if diferencia > 0:
        return "🔴"  # Sobregiro
    elif diferencia < 0:
        return "🟢"  # Por debajo del presupuesto
    return "⚪"  # Exacto


def _obtener_presupuesto_como_dict(db: Database, finca_id: int, anio: int) -> dict:
    """Obtiene el presupuesto como dict {categoria: monto_planificado}."""
    rows = db.get_presupuesto(finca_id, anio)
    return {r["categoria"]: r["monto_planificado"] for r in rows}


def _calcular_montos_sugeridos(area: float) -> dict:
    """Calcula montos sugeridos basados en el área de la finca.

    Fórmula: (porcentaje * area * costo_estimado_por_ha) / 100
    """
    # Costo estimado de referencia: ~$16.34M/ha distribuido por %
    COSTO_TOTAL_POR_HA = 16_340_000  # $16.34M/ha
    sugeridos = {}
    for cat_id, nombre, pct, costo_kg in FEPCAFE_CATEGORIAS:
        monto_sugerido = (pct / 100) * COSTO_TOTAL_POR_HA * area
        sugeridos[cat_id] = round(monto_sugerido)
    return sugeridos


# ─── Helpers de teclado ───

def _menu_presupuesto_kb():
    """Teclado del menú principal de presupuestos."""
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📝 Crear presupuesto", callback_data="presup_crear")],
        [types.InlineKeyboardButton(text="📊 Consultar presupuesto", callback_data="presup_consultar")],
        [types.InlineKeyboardButton(text="📈 Ejecución presupuestal", callback_data="presup_ejecutar")],
        [types.InlineKeyboardButton(text="📥 Exportar presupuesto", callback_data="presup_exportar")],
        [types.InlineKeyboardButton(text="🏠 Menú Principal", callback_data="volver_menu")],
    ])
    return kb


def _teclado_anios(anios_disponibles: list, prefix: str) -> types.InlineKeyboardMarkup:
    """Genera teclado con años disponibles."""
    kb = types.InlineKeyboardMarkup(inline_keyboard=[])
    for anio in anios_disponibles:
        kb.inline_keyboard.append([
            types.InlineKeyboardButton(text=f"📅 {anio}", callback_data=f"{prefix}:{anio}")
        ])
    kb.inline_keyboard.append([
        types.InlineKeyboardButton(text="🔙 Volver", callback_data="menu_presupuesto")
    ])
    return kb


def _teclado_editar_categoria(categoria_actual: str, categorias: list) -> types.InlineKeyboardMarkup:
    """Teclado para elegir qué categoría editar durante la creación del presupuesto."""
    kb = types.InlineKeyboardMarkup(inline_keyboard=[])
    for cat_id, nombre, _, _ in FEPCAFE_CATEGORIAS:
        monto = categorias.get(cat_id, 0)
        check = "✅ " if cat_id == categoria_actual else ""
        kb.inline_keyboard.append([
            types.InlineKeyboardButton(
                text=f"{check}{nombre}: {_formato_pesos(monto)}",
                callback_data=f"presup_editar_cat:{cat_id}"
            )
        ])
    kb.inline_keyboard.append([
        types.InlineKeyboardButton(text="✅ Confirmar y guardar", callback_data="presup_confirmar"),
    ])
    kb.inline_keyboard.append([
        types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion"),
    ])
    return kb


# ─── Router ───

def get_presupuesto_router(db: Database) -> Router:
    router = Router()

    # ─── Comando /presupuesto ───

    @router.message(Command("presupuesto"))
    @router.callback_query(F.data == "menu_presupuesto")
    async def cmd_presupuesto(event: types.Message | types.CallbackQuery, state: FSMContext):
        """Muestra el menú de presupuestos."""
        await state.clear()

        user_id = event.from_user.id
        if isinstance(event, types.CallbackQuery):
            await event.answer()
            send = event.message.edit_text
        else:
            send = event.answer

        if not db.is_approved(user_id):
            await send(
                "⏳ <b>No tienes acceso.</b> Usa /start para solicitar aprobación.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        fincas = db.get_fincas(user_id)
        if not fincas:
            await send(
                "❌ <b>No tienes fincas registradas.</b>\n\n"
                "Primero creá una finca con /fincas 🗺️",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        texto = (
            "📋 <b>Gestión de Presupuesto</b>\n\n"
            "¿Qué querés hacer?"
        )
        await send(texto, parse_mode="HTML", reply_markup=_menu_presupuesto_kb())

    # ─── Helper: selección de finca ───

    async def _seleccionar_finca(send_func, user_id: int, callback_data_prefix: str, message_text: str):
        """Muestra selector de fincas."""
        fincas = db.get_fincas(user_id)
        if len(fincas) == 1:
            return fincas[0]["id"], fincas[0]["nombre"]

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"🏠 {f['nombre']}",
                callback_data=f"{callback_data_prefix}:{f['id']}"
            )] for f in fincas
        ] + [
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="menu_presupuesto")]
        ])
        await send_func(message_text, parse_mode="HTML", reply_markup=kb)
        return None, None

    # ════════════════════════════════════════════════════════════════
    # FLUJO 1: CREAR PRESUPUESTO
    # ════════════════════════════════════════════════════════════════

    @router.callback_query(F.data == "presup_crear")
    async def presup_crear_inicio(callback: types.CallbackQuery, state: FSMContext):
        """Inicia flujo de creación de presupuesto: seleccionar finca."""
        await callback.answer()
        user_id = callback.from_user.id
        fincas = db.get_fincas(user_id)

        if not fincas:
            await callback.message.edit_text(
                "❌ <b>No tenés fincas registradas.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        if len(fincas) == 1:
            await state.update_data(finca_id=fincas[0]["id"], finca_nombre=fincas[0]["nombre"])
            await _pedir_anio(callback.message.edit_text, state)
            return

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"🏠 {f['nombre']}",
                callback_data=f"presup_crear_finca:{f['id']}"
            )] for f in fincas
        ] + [
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="menu_presupuesto")]
        ])
        await callback.message.edit_text(
            "🏠 <b>Seleccioná la finca</b> para crear el presupuesto:",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("presup_crear_finca:"))
    async def presup_crear_finca_selected(callback: types.CallbackQuery, state: FSMContext):
        """Finca seleccionada para crear presupuesto."""
        await callback.answer()
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML")
            return
        await state.update_data(finca_id=finca_id, finca_nombre=finca["nombre"])
        await _pedir_anio(callback.message.edit_text, state)

    async def _pedir_anio(send_func, state: FSMContext):
        """Pide el año del presupuesto."""
        await state.set_state(PresupuestoStates.esperando_anio)
        anio_actual = datetime.now().year
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=str(a), callback_data=f"presup_anio:{a}")]
            for a in [anio_actual - 1, anio_actual, anio_actual + 1]
        ] + [
            [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion")]
        ])
        await send_func(
            "📅 <b>¿Para qué año querés crear el presupuesto?</b>",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("presup_anio:"))
    async def presup_anio_selected(callback: types.CallbackQuery, state: FSMContext):
        """Año seleccionado. Preguntar área."""
        await callback.answer()
        anio = int(callback.data.split(":")[1])
        await state.update_data(anio=anio)
        await state.set_state(PresupuestoStates.esperando_area)

        data = await state.get_data()
        finca_id = data["finca_id"]

        # Calcular área total de la finca
        area_total = 0.0
        lotes = db.get_lotes(finca_id)
        for lote in lotes:
            area_total += lote.get("area_hectareas", 0) or 0

        if area_total > 0:
            texto = (
                f"📐 <b>Área de la finca</b>\n\n"
                f"Tu finca tiene <b>{area_total:.2f} ha</b> registradas en lotes.\n\n"
                f"¿Querés usar este valor o ingresar uno diferente?"
            )
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(
                    text=f"✅ Usar {area_total:.2f} ha",
                    callback_data=f"presup_area:{area_total:.2f}"
                )],
                [types.InlineKeyboardButton(text="✏️ Ingresar otro valor", callback_data="presup_area_manual")],
                [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion")],
            ])
            await callback.message.edit_text(texto, parse_mode="HTML", reply_markup=kb)
        else:
            # No hay lotes, pedir área manual
            await callback.message.edit_text(
                "📐 <b>Área de la finca</b>\n\n"
                "No encontré lotes registrados. Ingresá el área total en hectáreas:\n"
                "(Ej: 1.5, 2.0, 5.5)",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion")]
                ]),
            )

    @router.callback_query(F.data.startswith("presup_area:"))
    async def presup_area_selected(callback: types.CallbackQuery, state: FSMContext):
        """Área seleccionada de las opciones rápidas."""
        await callback.answer()
        area = float(callback.data.split(":")[1])
        await state.update_data(area=area)
        await _mostrar_edicion_presupuesto(callback.message.edit_text, state, db)

    @router.callback_query(F.data == "presup_area_manual")
    async def presup_area_manual(callback: types.CallbackQuery, state: FSMContext):
        """El usuario quiere ingresar área manualmente."""
        await callback.answer()
        await state.set_state(PresupuestoStates.esperando_area)
        await callback.message.edit_text(
            "✏️ <b>Ingresá el área en hectáreas</b>\n\n"
            "Escribí el número (ej: 1.5, 2.0, 5.5):",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion")]
            ]),
        )

    @router.message(PresupuestoStates.esperando_area)
    async def presup_area_manual_text(message: types.Message, state: FSMContext):
        """Recibe el área manualmente."""
        try:
            area = float(message.text.strip().replace(",", "."))
            if area <= 0:
                raise ValueError
        except (ValueError, TypeError):
            await message.reply(
                "❌ <b>Valor inválido.</b> Ingresá un número positivo (ej: 1.5, 2.0, 5.5):",
                parse_mode="HTML",
            )
            return

        await state.update_data(area=area)
        await _mostrar_edicion_presupuesto(message.answer, state, db)

    async def _mostrar_edicion_presupuesto(send_func, state: FSMContext, db: Database):
        """Muestra la estructura de costos del sector con montos sugeridos y permite editar."""
        data = await state.get_data()
        area = data["area"]
        anio = data["anio"]
        finca_id = data["finca_id"]

        # Si ya hay categorías editadas, usarlas; si no, calcular sugeridos
        categorias_editadas = data.get("categorias", {})
        if not categorias_editadas:
            categorias_editadas = _calcular_montos_sugeridos(area)
            await state.update_data(categorias=categorias_editadas)

        texto = (
            f"📋 <b>Presupuesto {anio} — {data['finca_nombre']}</b>\n"
            f"📐 Área: {area:.2f} ha\n\n"
            f"<b>Estructura de costos sugerida:</b>\n"
        )

        total = 0
        for cat_id, nombre, pct, costo_kg in FEPCAFE_CATEGORIAS:
            monto = categorias_editadas.get(cat_id, 0)
            total += monto
            texto += f"• {nombre}: <b>{_formato_pesos(monto)}</b> ({pct}%)\n"

        # Ingresos sugeridos (producción)
        produccion_sugerida = area * 1670  # ~1670 kg/ha estimado
        ingreso_sugerido = produccion_sugerida * COSTO_TOTAL_POR_KG
        texto += (
            f"\n💰 <b>Ingresos estimados:</b> {_formato_pesos(ingreso_sugerido)} "
            f"({produccion_sugerida:.0f} kg CPS a ${COSTO_TOTAL_POR_KG:,}/kg)\n"
            f"📊 <b>Total costos planificados:</b> {_formato_pesos(total)}\n"
            f"📊 <b>Costo por kg:</b> {_formato_pesos(COSTO_TOTAL_POR_KG)}\n"
            f"📊 <b>Costo por ha:</b> {_formato_pesos(total / area) if area > 0 else 0}\n\n"
            f"<i>Seleccioná una categoría para editar su monto o confirmá para guardar.</i>"
        )

        await send_func(texto, parse_mode="HTML", reply_markup=_teclado_editar_categoria("", categorias_editadas))
        await state.set_state(PresupuestoStates.editando_categoria)

    @router.callback_query(F.data.startswith("presup_editar_cat:"))
    async def presup_editar_cat(callback: types.CallbackQuery, state: FSMContext):
        """Selecciona una categoría para editar su monto."""
        await callback.answer()
        cat_id = callback.data.split(":")[1]

        # Buscar nombre de la categoría
        nombre_cat = cat_id
        for cid, nombre, _, _ in FEPCAFE_CATEGORIAS:
            if cid == cat_id:
                nombre_cat = nombre
                break

        await state.update_data(editando_categoria=cat_id)
        await state.set_state(PresupuestoStates.editando_categoria)

        data = await state.get_data()
        categorias = data.get("categorias", {})
        monto_actual = categorias.get(cat_id, 0)

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="↩️ Volver sin cambios",
                callback_data="presup_volver_edicion"
            )],
            [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion")],
        ])

        await callback.message.edit_text(
            f"✏️ <b>Editar: {nombre_cat}</b>\n\n"
            f"Monto actual: <b>{_formato_pesos(monto_actual)}</b>\n\n"
            f"Escribí el nuevo monto en COP:\n"
            f"(Ej: 5000000, 12500000)",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.message(PresupuestoStates.editando_categoria)
    async def presup_recibir_monto(message: types.Message, state: FSMContext):
        """Recibe el nuevo monto para una categoría."""
        try:
            monto_text = message.text.strip().replace("$", "").replace(",", "").replace(".", "")
            monto = float(monto_text)
            if monto < 0:
                raise ValueError
        except (ValueError, TypeError):
            await message.reply(
                "❌ <b>Valor inválido.</b> Ingresá un número positivo (ej: 5000000):",
                parse_mode="HTML",
            )
            return

        data = await state.get_data()
        cat_id = data.get("editando_categoria", "")
        categorias = data.get("categorias", {})
        categorias[cat_id] = monto
        await state.update_data(categorias=categorias)

        # Mostrar edición actualizada
        await _mostrar_edicion_presupuesto(message.answer, state, db)

    @router.callback_query(F.data == "presup_volver_edicion")
    async def presup_volver_edicion(callback: types.CallbackQuery, state: FSMContext):
        """Vuelve a la vista de edición sin cambios."""
        await callback.answer()
        await _mostrar_edicion_presupuesto(callback.message.edit_text, state, db)

    @router.callback_query(F.data == "presup_confirmar")
    async def presup_confirmar(callback: types.CallbackQuery, state: FSMContext):
        """Confirma y guarda el presupuesto."""
        await callback.answer()
        data = await state.get_data()
        finca_id = data["finca_id"]
        anio = data["anio"]
        categorias = data.get("categorias", {})

        # Guardar en DB
        db.guardar_presupuesto(finca_id, anio, categorias)

        total = sum(categorias.values())

        # Mostrar confirmación con gráfico de texto y enviar a menu presupuesto
        await callback.message.edit_text(
            f"✅ <b>Presupuesto guardado exitosamente</b>\n\n"
            f"📅 <b>Año:</b> {anio}\n"
            f"🏠 <b>Finca:</b> {data['finca_nombre']}\n"
            f"📐 <b>Área:</b> {data['area']:.2f} ha\n"
            f"💰 <b>Total planificado:</b> {_formato_pesos(total)}\n\n"
            f"📊 <b>Distribución:</b>\n"
            f"{_generar_barra_categorias(categorias)}",
            parse_mode="HTML",
            reply_markup=_menu_presupuesto_kb(),
        )
        await state.clear()

    def _generar_barra_categorias(categorias: dict) -> str:
        """Genera una representación visual de texto para las categorías."""
        total = sum(categorias.values()) or 1
        lineas = []
        for cat_id, nombre, pct_ref, _ in FEPCAFE_CATEGORIAS:
            monto = categorias.get(cat_id, 0)
            pct = (monto / total) * 100
            barra_len = max(1, int(pct / 5))
            barra = "█" * barra_len
            lineas.append(f" {nombre}: {barra} {_formato_pesos(monto)} ({pct:.1f}%)")
        return "\n".join(lineas)

    # ════════════════════════════════════════════════════════════════
    # FLUJO 2: CONSULTAR PRESUPUESTO
    # ════════════════════════════════════════════════════════════════

    @router.callback_query(F.data == "presup_consultar")
    async def presup_consultar(callback: types.CallbackQuery, state: FSMContext):
        """Seleccionar finca y año para consultar presupuesto."""
        await callback.answer()
        user_id = callback.from_user.id
        fincas = db.get_fincas(user_id)

        if not fincas:
            await callback.message.edit_text(
                "❌ <b>No tenés fincas registradas.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        if len(fincas) == 1:
            finca_id = fincas[0]["id"]
            anios = db.get_presupuesto_anios(finca_id)
            if not anios:
                await callback.message.edit_text(
                    "📭 <b>No hay presupuestos guardados.</b>\n\n"
                    "Usá 📝 Crear presupuesto para definir uno.",
                    parse_mode="HTML",
                    reply_markup=_menu_presupuesto_kb(),
                )
                return
            await state.update_data(finca_id=finca_id, finca_nombre=fincas[0]["nombre"])
            kb = _teclado_anios(anios, "presup_consultar_anio")
            await callback.message.edit_text(
                "📅 <b>Seleccioná el año</b> a consultar:",
                parse_mode="HTML",
                reply_markup=kb,
            )
            return

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"🏠 {f['nombre']}",
                callback_data=f"presup_consultar_finca:{f['id']}"
            )] for f in fincas
        ] + [
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="menu_presupuesto")]
        ])
        await callback.message.edit_text(
            "🏠 <b>Seleccioná la finca:</b>",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("presup_consultar_finca:"))
    async def presup_consultar_finca(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML")
            return
        anios = db.get_presupuesto_anios(finca_id)
        if not anios:
            await callback.message.edit_text(
                "📭 <b>No hay presupuestos guardados.</b>",
                parse_mode="HTML",
                reply_markup=_menu_presupuesto_kb(),
            )
            return
        await state.update_data(finca_id=finca_id, finca_nombre=finca["nombre"])
        kb = _teclado_anios(anios, "presup_consultar_anio")
        await callback.message.edit_text(
            "📅 <b>Seleccioná el año</b> a consultar:",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("presup_consultar_anio:"))
    async def presup_consultar_mostrar(callback: types.CallbackQuery, state: FSMContext):
        """Muestra el presupuesto planificado."""
        await callback.answer()
        anio = int(callback.data.split(":")[1])
        data = await state.get_data()
        finca_id = data["finca_id"]

        rows = db.get_presupuesto(finca_id, anio)
        if not rows:
            await callback.message.edit_text(
                f"📭 <b>No hay presupuesto para {anio}.</b>",
                parse_mode="HTML",
                reply_markup=_menu_presupuesto_kb(),
            )
            return

        categorias_dict = {r["categoria"]: r["monto_planificado"] for r in rows}
        total = sum(categorias_dict.values())
        area = data.get("area", 0)

        texto = (
            f"📊 <b>Presupuesto Planificado — {anio}</b>\n"
            f"🏠 <b>Finca:</b> {data['finca_nombre']}\n\n"
            f"<b>Categoría</b>         │ <b>Monto</b>          │ <b>%</b>\n"
            f"{'─' * 50}\n"
        )

        for cat_id, nombre, pct_ref, costo_kg in FEPCAFE_CATEGORIAS:
            monto = categorias_dict.get(cat_id, 0)
            pct_real = (monto / total * 100) if total > 0 else 0
            texto += f" {nombre:<18s} │ {_formato_pesos(monto):>12s} │ {pct_real:5.1f}%\n"

        texto += f"{'─' * 50}\n"
        texto += f" <b>TOTAL</b>            │ <b>{_formato_pesos(total):>12s}</b> │ <b>100.0%</b>\n\n"

        if area > 0:
            texto += f"📐 <b>Costo por hectárea:</b> {_formato_pesos(total / area)}\n"

        texto += f"📊 <b>Costo total por kg:</b> {_formato_pesos(COSTO_TOTAL_POR_KG)}\n"

        await callback.message.edit_text(
            texto,
            parse_mode="HTML",
            reply_markup=_menu_presupuesto_kb(),
        )

    # ════════════════════════════════════════════════════════════════
    # FLUJO 3: EJECUCIÓN PRESUPUESTAL
    # ════════════════════════════════════════════════════════════════

    @router.callback_query(F.data == "presup_ejecutar")
    async def presup_ejecutar(callback: types.CallbackQuery, state: FSMContext):
        """Seleccionar finca y año para comparar ejecución."""
        await callback.answer()
        user_id = callback.from_user.id
        fincas = db.get_fincas(user_id)

        if not fincas:
            await callback.message.edit_text(
                "❌ <b>No tenés fincas registradas.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        if len(fincas) == 1:
            finca_id = fincas[0]["id"]
            anios = db.get_presupuesto_anios(finca_id)
            if not anios:
                await callback.message.edit_text(
                    "📭 <b>No hay presupuestos guardados.</b>\n\n"
                    "Primero creá un presupuesto con 📝 Crear presupuesto.",
                    parse_mode="HTML",
                    reply_markup=_menu_presupuesto_kb(),
                )
                return
            await state.update_data(finca_id=finca_id, finca_nombre=fincas[0]["nombre"])
            kb = _teclado_anios(anios, "presup_ejecutar_anio")
            await callback.message.edit_text(
                "📅 <b>Seleccioná el año</b> para ver la ejecución presupuestal:",
                parse_mode="HTML",
                reply_markup=kb,
            )
            return

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"🏠 {f['nombre']}",
                callback_data=f"presup_ejecutar_finca:{f['id']}"
            )] for f in fincas
        ] + [
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="menu_presupuesto")]
        ])
        await callback.message.edit_text(
            "🏠 <b>Seleccioná la finca:</b>",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("presup_ejecutar_finca:"))
    async def presup_ejecutar_finca(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML")
            return
        anios = db.get_presupuesto_anios(finca_id)
        if not anios:
            await callback.message.edit_text(
                "📭 <b>No hay presupuestos guardados.</b>",
                parse_mode="HTML",
                reply_markup=_menu_presupuesto_kb(),
            )
            return
        await state.update_data(finca_id=finca_id, finca_nombre=finca["nombre"])
        kb = _teclado_anios(anios, "presup_ejecutar_anio")
        await callback.message.edit_text(
            "📅 <b>Seleccioná el año</b> para ver la ejecución presupuestal:",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("presup_ejecutar_anio:"))
    async def presup_ejecutar_mostrar(callback: types.CallbackQuery, state: FSMContext):
        """Muestra la comparación de ejecución presupuestal."""
        await callback.answer()
        anio = int(callback.data.split(":")[1])
        data = await state.get_data()
        finca_id = data["finca_id"]

        ejecucion = db.get_ejecucion_presupuesto(finca_id, anio)

        texto = (
            f"📈 <b>Ejecución Presupuestal — {anio}</b>\n"
            f"🏠 <b>Finca:</b> {data['finca_nombre']}\n\n"
        )

        # Tabla de comparación
        texto += (
            f"<b>Categoría</b>          │ <b>Plan</b>            │ <b>Ejec</b>            │ <b>Diff</b>            │ <b>%Ejec</b>\n"
            f"{'─' * 75}\n"
        )

        for cat_item in ejecucion["categorias"]:
            cat_id = cat_item["categoria"]
            # Buscar nombre
            nombre = cat_id
            for cid, n, _, _ in FEPCAFE_CATEGORIAS:
                if cid == cat_id:
                    nombre = n
                    break

            plan = cat_item["monto_planificado"]
            ejec = cat_item["monto_ejecutado"]
            diff = cat_item["diferencia"]
            pct = cat_item["pct_ejecucion"]
            emoji = _emoji_diferencia(diff)

            texto += f" {nombre:<15s} │ {_formato_pesos(plan):>10s} │ {_formato_pesos(ejec):>10s} │ {emoji} {_formato_pesos(diff):>10s} │ {_formato_pesos(pct):>5s}\n"

        texto += f"{'─' * 75}\n"
        total_plan = ejecucion["total_planificado"]
        total_ejec = ejecucion["total_ejecutado"]
        total_diff = ejecucion["total_diferencia"]
        pct_total = (total_ejec / total_plan * 100) if total_plan > 0 else 0
        emoji_total = _emoji_diferencia(total_diff)

        texto += (
            f" <b>TOTAL</b>             │ <b>{_formato_pesos(total_plan):>10s}</b> │ <b>{_formato_pesos(total_ejec):>10s}</b> │ <b>{emoji_total} {_formato_pesos(total_diff):>10s}</b> │ <b>{pct_total:.1f}%</b>\n\n"
        )

        # Resumen
        if total_diff > 0:
            texto += f"⚠️ <b>Sobregiro total:</b> {_formato_pesos(abs(total_diff))}\n"
        elif total_diff < 0:
            texto += f"✅ <b>Ahorro total:</b> {_formato_pesos(abs(total_diff))}\n"
        else:
            texto += f"⚪ <b>Ejecución exacta al presupuesto.</b>\n"

        texto += f"📊 <b>% Ejecución general:</b> {pct_total:.1f}%\n"

        await callback.message.edit_text(
            texto,
            parse_mode="HTML",
            reply_markup=_menu_presupuesto_kb(),
        )

    # ════════════════════════════════════════════════════════════════
    # FLUJO 4: EXPORTAR PRESUPUESTO A EXCEL
    # ════════════════════════════════════════════════════════════════

    @router.callback_query(F.data == "presup_exportar")
    async def presup_exportar(callback: types.CallbackQuery, state: FSMContext):
        """Exporta presupuesto a Excel (usa el ExcelManager existente)."""
        await callback.answer()
        user_id = callback.from_user.id
        fincas = db.get_fincas(user_id)

        if not fincas:
            await callback.message.edit_text(
                "❌ <b>No tenés fincas registradas.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        if len(fincas) == 1:
            finca_id = fincas[0]["id"]
            anios = db.get_presupuesto_anios(finca_id)
            if not anios:
                await callback.message.edit_text(
                    "📭 <b>No hay presupuestos guardados.</b>",
                    parse_mode="HTML",
                    reply_markup=_menu_presupuesto_kb(),
                )
                return
            await state.update_data(finca_id=finca_id, finca_nombre=fincas[0]["nombre"])
            kb = _teclado_anios(anios, "presup_exportar_anio")
            await callback.message.edit_text(
                "📅 <b>Seleccioná el año</b> para exportar:",
                parse_mode="HTML",
                reply_markup=kb,
            )
            return

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text=f"🏠 {f['nombre']}",
                callback_data=f"presup_exportar_finca:{f['id']}"
            )] for f in fincas
        ] + [
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="menu_presupuesto")]
        ])
        await callback.message.edit_text(
            "🏠 <b>Seleccioná la finca:</b>",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("presup_exportar_finca:"))
    async def presup_exportar_finca(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML")
            return
        anios = db.get_presupuesto_anios(finca_id)
        if not anios:
            await callback.message.edit_text(
                "📭 <b>No hay presupuestos guardados.</b>",
                parse_mode="HTML",
                reply_markup=_menu_presupuesto_kb(),
            )
            return
        await state.update_data(finca_id=finca_id, finca_nombre=finca["nombre"])
        kb = _teclado_anios(anios, "presup_exportar_anio")
        await callback.message.edit_text(
            "📅 <b>Seleccioná el año</b> para exportar:",
            parse_mode="HTML",
            reply_markup=kb,
        )

    @router.callback_query(F.data.startswith("presup_exportar_anio:"))
    async def presup_exportar_anio(callback: types.CallbackQuery):
        """Genera y envía el Excel con la hoja Presupuesto."""
        await callback.answer()
        anio = int(callback.data.split(":")[1])
        data = await state.get_data()
        
        # Extraer finca_id del callback context
        # Re-obtener finca_id desde el mensaje original
        user_id = callback.from_user.id
        fincas = db.get_fincas(user_id)
        
        await callback.message.edit_text(
            "⏳ <b>Generando Excel con presupuesto...</b>",
            parse_mode="HTML",
        )

        try:
            from excel_manager import ExcelManager
            manager = ExcelManager(EXCEL_TEMPLATE)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"presupuesto_finca_{anio}_{timestamp}.xlsx"
            output_path = os.path.join(EXPORTS_DIR, output_filename)

            # Generar Excel (el método generar_excel ya incluye _llenar_hoja_presupuesto)
            if len(fincas) == 1:
                finca_id = fincas[0]["id"]
            else:
                # Need to parse from callback data or use state
                # For simplicity, parse finca_id from stored state
                sdata = await state.get_data()
                finca_id = sdata.get("finca_id", 0)
                if not finca_id:
                    await callback.message.edit_text(
                        "❌ <b>Error:</b> No se pudo identificar la finca.",
                        parse_mode="HTML",
                        reply_markup=_menu_presupuesto_kb(),
                    )
                    return

            manager.generar_excel(finca_id, db, output_path)

            # Enviar archivo
            with open(output_path, "rb") as f:
                await callback.message.answer_document(
                    types.FSInputFile(
                        output_path,
                        filename=f"Presupuesto_{anio}.xlsx",
                    ),
                    caption=f"📊 <b>Presupuesto {anio} exportado</b> ☕\n\n"
                            f"Incluye la hoja 'Presupuesto' con planificación y ejecución.",
                    parse_mode="HTML",
                )

            # Limpiar archivo temporal
            try:
                os.remove(output_path)
            except Exception:
                pass

        except FileNotFoundError as e:
            logger.error(f"Template no encontrado: {e}")
            await callback.message.edit_text(
                "❌ <b>Error:</b> El template Excel no está disponible.\n\n"
                "Contactá al administrador.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
        except Exception as e:
            logger.error(f"Error al generar Excel: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ <b>Error al generar el Excel.</b> Intentá de nuevo más tarde.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

    return router
