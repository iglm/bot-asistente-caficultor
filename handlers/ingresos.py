"""
Handler de /ingreso - Registro de ingresos por ventas de café.
"""
import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from config import TIPOS_CAFE, TIPOS_CAFE_LIST
from utils import boton_menu, botones_menu_cancelar, agregar_boton_menu, botones_fecha, fecha_hoy, fecha_ayer

logger = logging.getLogger(__name__)


class IngresoForm(StatesGroup):
    esperando_finca = State()
    esperando_fecha = State()
    esperando_tipo = State()
    esperando_cantidad = State()
    esperando_valor_total = State()
    esperando_confirmar = State()
    # Estados de edición
    esperando_edicion = State()
    esperando_edicion_fecha = State()
    esperando_edicion_cantidad = State()
    esperando_edicion_valor_total = State()


async def preguntar_fecha(message: types.Message, state: FSMContext):
    """Pregunta la fecha de la venta."""
    await message.answer(
        "💰 <b>Registrar Ingreso</b>\n\n"
        "¿Cuál es la <b>fecha</b> de la venta?",
        parse_mode="HTML",
        reply_markup=botones_fecha(),
    )
    await state.set_state(IngresoForm.esperando_fecha)


def get_ingresos_router(db: Database) -> Router:
    router = Router()

    @router.message(Command("ingreso"))
    @router.callback_query(F.data == "menu_ingresos")
    async def cmd_ingreso(event: types.Message | types.CallbackQuery, state: FSMContext):
        """Inicia el registro de un ingreso. Limpia estado previo primero."""
        # Garantizar que NO haya estado FSM residual
        await state.clear()
        user_id = event.from_user.id

        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
        else:
            message = event
            send = message.answer

        if not db.is_approved(user_id):
            await send("⏳ <b>No tienes acceso.</b> Usa /start para solicitar aprobación.", parse_mode="HTML", reply_markup=boton_menu())
            return

        try:
            fincas = db.get_fincas(user_id)
            if not fincas:
                await send(
                    "❌ <b>No tienes fincas registradas.</b>\n\n"
                    "Primero crea una finca con /fincas 🗺️",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )
                return

            if len(fincas) == 1:
                await state.update_data(finca_id=fincas[0]["id"], finca_nombre=fincas[0]["nombre"])
                await preguntar_fecha(message, state)
                return

            # Varias fincas - seleccionar
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(
                        text=f"🏠 {f['nombre']}",
                        callback_data=f"ingreso_finca:{f['id']}",
                    )]
                    for f in fincas
                ]
                + [
                    [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
                ]
            )
            keyboard = agregar_boton_menu(keyboard)

            await send(
                "💰 <b>Registrar Ingreso</b>\n\nSelecciona la finca:",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            await state.set_state(IngresoForm.esperando_finca)

        except Exception as e:
            logger.error(f"Error en /ingreso: {e}", exc_info=True)
            await send("❌ <b>Error al iniciar registro.</b>", parse_mode="HTML", reply_markup=boton_menu())

    @router.callback_query(IngresoForm.esperando_finca, F.data.startswith("ingreso_finca:"))
    async def seleccionar_finca_ingreso(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        user_id = callback.from_user.id
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML", reply_markup=boton_menu())
            await state.clear()
            return
        # Validar que la finca pertenezca al usuario
        if finca["user_id"] != user_id:
            await callback.message.edit_text("❌ <b>Esta finca no te pertenece.</b>", parse_mode="HTML", reply_markup=boton_menu())
            await state.clear()
            return

        await state.update_data(finca_id=finca_id, finca_nombre=finca["nombre"])
        await preguntar_fecha(callback.message, state)

    @router.message(IngresoForm.esperando_fecha, F.text)
    async def recibir_fecha(message: types.Message, state: FSMContext):
        fecha_str = message.text.strip()

        # Atajos de texto
        if fecha_str.lower() in ["hoy", "today"]:
            fecha_str = fecha_hoy()
        elif fecha_str.lower() in ["ayer", "yesterday"]:
            fecha_str = fecha_ayer()

        fecha_valida = None
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                fecha_valida = datetime.strptime(fecha_str, fmt)
                break
            except ValueError:
                continue

        if not fecha_valida:
            await message.answer("❌ Fecha inválida. Usá los botones o escribí en formato DD/MM/AAAA:", reply_markup=botones_fecha())
            return

        # Guardar en ISO
        fecha_iso = fecha_valida.strftime("%Y-%m-%d")
        await state.update_data(fecha=fecha_iso)

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=tipo, callback_data=f"tipo_cafe:{tipo}")]
                for tipo in TIPOS_CAFE_LIST
            ] + [
                [types.InlineKeyboardButton(text="🔙 Volver", callback_data="ingreso_volver_fecha")],
            ]
        )
        keyboard = agregar_boton_menu(keyboard)

        await message.answer(
            f"✅ <b>Fecha:</b> {fecha_str}\n\n"
            "¿Qué <b>tipo de café</b> vendiste?",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await state.set_state(IngresoForm.esperando_tipo)

    @router.callback_query(IngresoForm.esperando_fecha, F.data.startswith("fecha:"))
    async def procesar_fecha_callback_ingreso(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        opcion = callback.data.split(":", 1)[1]

        if opcion == "hoy":
            fecha_str = fecha_hoy()
        elif opcion == "ayer":
            fecha_str = fecha_ayer()
        else:  # custom
            await callback.message.answer("✏️ Escribí la fecha en formato DD/MM/AAAA:", reply_markup=botones_fecha())
            return

        fecha_iso = datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        await state.update_data(fecha=fecha_iso)

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=tipo, callback_data=f"tipo_cafe:{tipo}")]
                for tipo in TIPOS_CAFE_LIST
            ] + [
                [types.InlineKeyboardButton(text="🔙 Volver", callback_data="ingreso_volver_fecha")],
            ]
        )
        keyboard = agregar_boton_menu(keyboard)

        await callback.message.answer(
            f"✅ <b>Fecha:</b> {fecha_str}\n\n"
            "¿Qué <b>tipo de café</b> vendiste?",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await state.set_state(IngresoForm.esperando_tipo)

    @router.callback_query(IngresoForm.esperando_tipo, F.data == "ingreso_volver_fecha")
    async def volver_fecha(callback: types.CallbackQuery, state: FSMContext):
        """Vuelve al paso de fecha."""
        await callback.answer()
        await preguntar_fecha(callback.message, state)

    @router.callback_query(IngresoForm.esperando_tipo, F.data.startswith("tipo_cafe:"))
    async def recibir_tipo(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        tipo = callback.data.split(":", 1)[1]
        await state.update_data(tipo=tipo)

        await callback.message.edit_text(
            f"✅ <b>Tipo:</b> {tipo}\n\n"
            "¿Cuántos <b>kilos</b> vendiste?\n\n"
            "<i>(Escribe el número)</i>",
            parse_mode="HTML",
            reply_markup=botones_menu_cancelar(),
        )
        await state.set_state(IngresoForm.esperando_cantidad)

    @router.message(IngresoForm.esperando_cantidad, F.text)
    async def recibir_cantidad(message: types.Message, state: FSMContext):
        try:
            cantidad = float(message.text.strip().replace(",", "."))
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa una cantidad válida (mayor a 0):", reply_markup=botones_menu_cancelar())
            return

        await state.update_data(cantidad=cantidad)
        await message.answer(
            f"✅ <b>Cantidad:</b> {cantidad} kg\n\n"
            "¿Cuál fue el <b>valor total</b> de la venta?\n\n"
            "<i>(Escribe el valor en pesos, ej: 1500000)</i>",
            parse_mode="HTML",
            reply_markup=botones_menu_cancelar(),
        )
        await state.set_state(IngresoForm.esperando_valor_total)

    @router.message(IngresoForm.esperando_valor_total, F.text)
    async def recibir_valor_total(message: types.Message, state: FSMContext):
        try:
            valor = float(message.text.strip().replace(".", "").replace(",", "."))
            if valor <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un valor válido (mayor a 0):", reply_markup=botones_menu_cancelar())
            return

        await state.update_data(valor_total=valor)

        data = await state.get_data()
        tipo = data["tipo"]
        cantidad = data["cantidad"]
        valor_unitario = valor / cantidad if cantidad > 0 else 0

        # Resumen para confirmar con botones
        texto = (
            f"📋 <b>Resumen del Ingreso</b>\n\n"
            f"🏠 <b>Finca:</b> {data.get('finca_nombre', '')}\n"
            f"📅 <b>Fecha:</b> {data.get('fecha', '')}\n"
            f"☕ <b>Tipo:</b> {tipo}\n"
            f"⚖️ <b>Cantidad:</b> {cantidad} kg\n"
            f"💰 <b>Valor Total:</b> ${valor:,.0f}\n"
            f"💵 <b>Valor Unitario:</b> ${valor_unitario:,.0f}/kg\n\n"
        )

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="✅ Confirmar", callback_data="conf_ingreso:si"),
                    types.InlineKeyboardButton(text="✏️ Editar", callback_data="editar_ingreso"),
                    types.InlineKeyboardButton(text="❌ Cancelar", callback_data="conf_ingreso:no"),
                ],
            ]
        )
        keyboard = agregar_boton_menu(keyboard)

        await message.answer(texto, parse_mode="HTML", reply_markup=keyboard)
        await state.set_state(IngresoForm.esperando_confirmar)

    # ── EDICIÓN DE INGRESO ──────────────────────────────────────

    @router.callback_query(IngresoForm.esperando_confirmar, F.data == "editar_ingreso")
    async def editar_ingreso(callback: types.CallbackQuery, state: FSMContext):
        """Muestra opciones de edición para Ingreso."""
        await callback.answer()

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📅 Fecha", callback_data="edit_ingreso_fecha")],
            [types.InlineKeyboardButton(text="⚖️ Cantidad", callback_data="edit_ingreso_cantidad")],
            [types.InlineKeyboardButton(text="💰 Valor Total", callback_data="edit_ingreso_valor_total")],
            [types.InlineKeyboardButton(text="← Volver al resumen", callback_data="volver_resumen_ingreso")],
        ])

        await callback.message.edit_text(
            "✏️ <b>¿Qué querés editar del ingreso?</b>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await state.set_state(IngresoForm.esperando_edicion)

    @router.callback_query(IngresoForm.esperando_edicion, F.data.startswith("edit_ingreso_"))
    async def editar_ingreso_campo(callback: types.CallbackQuery, state: FSMContext):
        """Redirige al campo a editar en Ingreso."""
        await callback.answer()
        campo = callback.data.split("_", 2)[2]  # edit_ingreso_{campo}

        if campo == "fecha":
            await callback.message.edit_text(
                "✏️ <b>¿Cuál es la nueva fecha?</b>",
                parse_mode="HTML",
                reply_markup=botones_fecha(),
            )
            await state.set_state(IngresoForm.esperando_edicion_fecha)

        elif campo == "cantidad":
            await callback.message.edit_text(
                "✏️ <b>¿Cuántos kilos?</b>",
                parse_mode="HTML",
                reply_markup=botones_menu_cancelar(),
            )
            await state.set_state(IngresoForm.esperando_edicion_cantidad)

        elif campo == "valor_total":
            await callback.message.edit_text(
                "✏️ <b>¿Cuál es el nuevo valor total?</b>",
                parse_mode="HTML",
                reply_markup=botones_menu_cancelar(),
            )
            await state.set_state(IngresoForm.esperando_edicion_valor_total)

    @router.message(IngresoForm.esperando_edicion_fecha, F.text)
    async def recibir_edicion_fecha_ingreso(message: types.Message, state: FSMContext):
        fecha_str = message.text.strip()
        if fecha_str.lower() in ["hoy", "today"]:
            fecha_str = fecha_hoy()
        elif fecha_str.lower() in ["ayer", "yesterday"]:
            fecha_str = fecha_ayer()

        fecha_valida = None
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                fecha_valida = datetime.strptime(fecha_str, fmt)
                break
            except ValueError:
                continue

        if not fecha_valida:
            await message.answer("❌ Fecha inválida. Usá formato DD/MM/AAAA:", reply_markup=botones_fecha())
            return

        fecha_iso = fecha_valida.strftime("%Y-%m-%d")
        await state.update_data(fecha=fecha_iso)
        await mostrar_resumen_ingreso(message, state)

    @router.callback_query(IngresoForm.esperando_edicion_fecha, F.data.startswith("fecha:"))
    async def procesar_edicion_fecha_ingreso(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        opcion = callback.data.split(":", 1)[1]
        if opcion == "hoy":
            fecha_str = fecha_hoy()
        elif opcion == "ayer":
            fecha_str = fecha_ayer()
        else:
            await callback.message.answer("✏️ Escribí la fecha en formato DD/MM/AAAA:", reply_markup=botones_fecha())
            return
        fecha_iso = datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        await state.update_data(fecha=fecha_iso)
        await mostrar_resumen_ingreso(callback.message, state, edit=True)

    @router.message(IngresoForm.esperando_edicion_cantidad, F.text)
    async def recibir_edicion_cantidad_ingreso(message: types.Message, state: FSMContext):
        try:
            cantidad = float(message.text.strip().replace(",", "."))
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa una cantidad válida (mayor a 0):", reply_markup=botones_menu_cancelar())
            return
        await state.update_data(cantidad=cantidad)
        await mostrar_resumen_ingreso(message, state)

    @router.message(IngresoForm.esperando_edicion_valor_total, F.text)
    async def recibir_edicion_valor_total_ingreso(message: types.Message, state: FSMContext):
        try:
            valor = float(message.text.strip().replace(".", "").replace(",", "."))
            if valor <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un valor válido (mayor a 0):", reply_markup=botones_menu_cancelar())
            return
        await state.update_data(valor_total=valor)
        await mostrar_resumen_ingreso(message, state)

    @router.callback_query(F.data == "volver_resumen_ingreso")
    async def volver_resumen_ingreso(callback: types.CallbackQuery, state: FSMContext):
        """Vuelve a mostrar el resumen de ingreso desde la edición."""
        await callback.answer()
        await mostrar_resumen_ingreso(callback.message, state, edit=True)

    async def mostrar_resumen_ingreso(message: types.Message, state: FSMContext, edit: bool = False):
        """Muestra el resumen de ingreso con botones Confirmar/Editar/Cancelar."""
        data = await state.get_data()
        tipo = data.get("tipo", "")
        cantidad = data.get("cantidad", 0)
        valor = data.get("valor_total", 0)
        valor_unitario = valor / cantidad if cantidad > 0 else 0

        texto = (
            f"📋 <b>Resumen del Ingreso</b>\n\n"
            f"🏠 <b>Finca:</b> {data.get('finca_nombre', '')}\n"
            f"📅 <b>Fecha:</b> {data.get('fecha', '')}\n"
            f"☕ <b>Tipo:</b> {tipo}\n"
            f"⚖️ <b>Cantidad:</b> {cantidad} kg\n"
            f"💰 <b>Valor Total:</b> ${valor:,.0f}\n"
            f"💵 <b>Valor Unitario:</b> ${valor_unitario:,.0f}/kg\n\n"
        )

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="✅ Confirmar", callback_data="conf_ingreso:si"),
                    types.InlineKeyboardButton(text="✏️ Editar", callback_data="editar_ingreso"),
                    types.InlineKeyboardButton(text="❌ Cancelar", callback_data="conf_ingreso:no"),
                ],
            ]
        )
        keyboard = agregar_boton_menu(keyboard)

        if edit:
            try:
                await message.edit_text(texto, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                await message.answer(texto, parse_mode="HTML", reply_markup=keyboard)
        else:
            await message.answer(texto, parse_mode="HTML", reply_markup=keyboard)

        await state.set_state(IngresoForm.esperando_confirmar)

    @router.callback_query(IngresoForm.esperando_confirmar, F.data.startswith("conf_ingreso:"))
    async def confirmar_ingreso(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        decision = callback.data.split(":", 1)[1]

        if decision == "no":
            await callback.message.edit_text(
                "❌ <b>Registro cancelado.</b>\n\n"
                "Usa /ingreso cuando quieras intentarlo de nuevo.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            await state.clear()
            return

        data = await state.get_data()

        # Mapear tipo a categoría
        tipo_raw = data.get("tipo") or ""
        tipo_corto = TIPOS_CAFE.get(tipo_raw, tipo_raw)
        tipo_map = {"CPS": "ingreso_cps", "Pasilla": "ingreso_pasilla"}
        categoria = tipo_map.get(tipo_corto, "ingreso_cps")

        try:
            db.insert_transaccion(
                finca_id=data["finca_id"],
                lote_id=0,
                categoria=categoria,
                fecha=data["fecha"],
                labor=f"Venta {data['tipo']}",
                producto=data["tipo"],
                cantidad=data["cantidad"],
                unidad="kg",
                valor_unitario=data["valor_total"] / data["cantidad"] if data["cantidad"] > 0 else 0,
                valor_total=data["valor_total"],
            )

            keyboard_success = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="💰 Otro Ingreso", callback_data="menu_ingresos")],
                ]
            )
            keyboard_success = agregar_boton_menu(keyboard_success)

            await callback.message.edit_text(
                f"✅ <b>¡Ingreso registrado exitosamente!</b> 🎉☕\n\n"
                f"☕ <b>Tipo:</b> {data['tipo']}\n"
                f"⚖️ <b>Cantidad:</b> {data['cantidad']} kg\n"
                f"💰 <b>Valor:</b> ${data['valor_total']:,.0f}\n\n"
                "Usa /resumen para ver tus datos o /ingreso para agregar otro.",
                parse_mode="HTML",
                reply_markup=keyboard_success,
            )

        except Exception as e:
            logger.error(f"Error al guardar ingreso: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ <b>Error al guardar el ingreso.</b> Intenta de nuevo.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

        await state.clear()


    return router
