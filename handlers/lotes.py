"""
Handler de /lotes - Gestión de lotes.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from utils import boton_menu, botones_menu_cancelar, agregar_boton_menu, botones_fecha, fecha_hoy, fecha_ayer

logger = logging.getLogger(__name__)


class LoteForm(StatesGroup):
    esperando_nombre = State()
    esperando_area = State()
    esperando_arboles = State()
    esperando_variedad = State()
    esperando_fecha_siembra = State()


def get_lotes_router(db: Database) -> Router:
    router = Router()

    async def mostrar_lotes(db: Database, message: types.Message, finca_id: int, finca_nombre: str, edit: bool = False):
        """Muestra los lotes de una finca."""
        try:
            lotes = db.get_lotes(finca_id)

            texto = f"🌱 <b>Lotes de {finca_nombre}</b>\n\n"

            if lotes:
                for l in lotes:
                    area = l["area_hectareas"] or 0
                    arboles = l["num_arboles"] or 0
                    variedad = l["variedad"] or "N/E"
                    texto += (
                        f"  📍 <b>{l['nombre']}</b>\n"
                        f"     Área: {area} ha | Árboles: {arboles}\n"
                        f"     Variedad: {variedad}\n\n"
                    )
            else:
                texto += "Aún no hay lotes registrados.\n\n"

            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(
                        text="➕ Nuevo Lote",
                        callback_data=f"nuevo_lote:{finca_id}",
                    )],
                ]
            )
            keyboard = agregar_boton_menu(keyboard)

            if edit:
                await message.edit_text(texto, parse_mode="HTML", reply_markup=keyboard)
            else:
                await message.answer(texto, parse_mode="HTML", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error al mostrar lotes: {e}", exc_info=True)
            error_text = "❌ Error al obtener lotes."
            if edit:
                await message.edit_text(error_text, parse_mode="HTML", reply_markup=boton_menu())
            else:
                await message.answer(error_text, parse_mode="HTML", reply_markup=boton_menu())

    @router.message(Command("lotes"))
    @router.callback_query(F.data == "menu_lotes")
    async def cmd_lotes(event: types.Message | types.CallbackQuery, state: FSMContext):
        """Muestra el menú de lotes."""
        await state.clear()
        user_id = event.from_user.id

        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
            is_callback = True
        else:
            message = event
            send = message.answer
            is_callback = False

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
                # Si solo tiene una finca, ir directo
                await mostrar_lotes(db, message, fincas[0]["id"], fincas[0]["nombre"], edit=is_callback)
                return

            # Varias fincas - seleccionar
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(
                        text=f"🏠 {f['nombre']}",
                        callback_data=f"lotes_finca:{f['id']}",
                    )]
                    for f in fincas
                ]
            )
            keyboard = agregar_boton_menu(keyboard)

            await send(
                "🌱 <b>Gestión de Lotes</b>\n\nSelecciona una finca:",
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        except Exception as e:
            logger.error(f"Error en /lotes: {e}", exc_info=True)
            await send("❌ <b>Error al obtener lotes.</b>", parse_mode="HTML", reply_markup=boton_menu())

    @router.callback_query(F.data.startswith("lotes_finca:"))
    async def seleccionar_finca_lotes(callback: types.CallbackQuery):
        """Muestra los lotes de una finca seleccionada."""
        await callback.answer()
        user_id = callback.from_user.id
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML", reply_markup=boton_menu())
            return
        if finca["user_id"] != user_id:
            await callback.message.edit_text("❌ <b>Esta finca no te pertenece.</b>", parse_mode="HTML", reply_markup=boton_menu())
            return

        await mostrar_lotes(db, callback.message, finca_id, finca["nombre"], edit=True)

    @router.callback_query(F.data.startswith("nuevo_lote:"))
    async def nuevo_lote(callback: types.CallbackQuery, state: FSMContext):
        """Inicia el proceso de crear un nuevo lote."""
        await callback.answer()
        user_id = callback.from_user.id

        if not db.is_approved(user_id):
            await callback.message.edit_text("⏳ <b>No tienes acceso.</b> Usa /start para solicitar aprobación.", parse_mode="HTML", reply_markup=boton_menu())
            return

        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML", reply_markup=boton_menu())
            return
        if finca["user_id"] != user_id:
            await callback.message.edit_text("❌ <b>Esta finca no te pertenece.</b>", parse_mode="HTML", reply_markup=boton_menu())
            return

        await state.update_data(finca_id=finca_id, finca_nombre=finca["nombre"])

        await callback.message.edit_text(
            f"🌱 <b>Nuevo Lote en {finca['nombre']}</b>\n\n"
            "Paso 1/5: ¿Cuál es el <b>nombre</b> del lote?\n\n"
            "<i>(Escribe el nombre o /cancelar)</i>",
            parse_mode="HTML",
            reply_markup=botones_menu_cancelar(),
        )
        await state.set_state(LoteForm.esperando_nombre)

    @router.message(LoteForm.esperando_nombre, F.text)
    async def recibir_nombre_lote(message: types.Message, state: FSMContext):
        nombre = message.text.strip()
        if not nombre:
            await message.answer("❌ El nombre no puede estar vacío:", reply_markup=botones_menu_cancelar())
            return

        await state.update_data(nombre=nombre)
        data = await state.get_data()
        await message.answer(
            f"✅ <b>Nombre:</b> {nombre}\n\n"
            "Paso 2/5: ¿Cuál es el <b>área</b> en hectáreas?\n\n"
            "<i>(Ej: 2.5 — escribe 0 si no sabes)</i>",
            parse_mode="HTML",
            reply_markup=botones_menu_cancelar(),
        )
        await state.set_state(LoteForm.esperando_area)

    @router.message(LoteForm.esperando_area, F.text)
    async def recibir_area_lote(message: types.Message, state: FSMContext):
        try:
            area = float(message.text.strip().replace(",", "."))
            if area < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un número válido (ej: 2.5):", reply_markup=botones_menu_cancelar())
            return

        await state.update_data(area=area)
        await message.answer(
            f"✅ <b>Área:</b> {area} ha\n\n"
            "Paso 3/5: ¿Cuántos <b>árboles</b> tiene el lote?\n\n"
            "<i>(Escribe 0 si no sabes)</i>",
            parse_mode="HTML",
            reply_markup=botones_menu_cancelar(),
        )
        await state.set_state(LoteForm.esperando_arboles)

    @router.message(LoteForm.esperando_arboles, F.text)
    async def recibir_arboles_lote(message: types.Message, state: FSMContext):
        try:
            arboles = int(message.text.strip())
            if arboles < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un número entero válido:", reply_markup=botones_menu_cancelar())
            return

        await state.update_data(arboles=arboles)
        await message.answer(
            f"✅ <b>Árboles:</b> {arboles}\n\n"
            "Paso 4/5: ¿Cuál es la <b>variedad</b> de café?\n\n"
            "<i>(Ej: Castillo, Caturra, Colombia — o '/' para omitir)</i>",
            parse_mode="HTML",
            reply_markup=botones_menu_cancelar(),
        )
        await state.set_state(LoteForm.esperando_variedad)

    @router.message(LoteForm.esperando_variedad, F.text)
    async def recibir_variedad_lote(message: types.Message, state: FSMContext):
        variedad = message.text.strip()
        if variedad == "/":
            variedad = ""

        await state.update_data(variedad=variedad)
        await message.answer(
            f"✅ <b>Variedad:</b> {variedad or '(omitido)'}\n\n"
            "Paso 5/5: ¿Cuál es la <b>fecha de siembra</b>?\n\n"
            "<i>(Formato: DD/MM/AAAA — o '/' para omitir)</i>",
            parse_mode="HTML",
            reply_markup=botones_fecha(),
        )
        await state.set_state(LoteForm.esperando_fecha_siembra)

    @router.message(LoteForm.esperando_fecha_siembra, F.text)
    async def recibir_fecha_lote(message: types.Message, state: FSMContext):
        fecha = message.text.strip()

        # Atajos de texto
        if fecha.lower() in ["hoy", "today"]:
            fecha = fecha_hoy()
        elif fecha.lower() in ["ayer", "yesterday"]:
            fecha = fecha_ayer()

        if fecha == "/":
            fecha = ""
        else:
            # Validar formato de fecha
            from datetime import datetime
            fecha_valida = False
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    d = datetime.strptime(fecha, fmt)
                    fecha = d.strftime("%Y-%m-%d")
                    fecha_valida = True
                    break
                except ValueError:
                    continue

            if not fecha_valida:
                await message.answer(
                    "❌ Fecha inválida. Usá los botones o escribí en formato DD/MM/AAAA:",
                    reply_markup=botones_fecha(),
                )
                return

        data = await state.get_data()
        nombre = data.get("nombre", "")
        area = data.get("area", 0)
        arboles = data.get("arboles", 0)
        variedad = data.get("variedad", "")
        finca_id = data.get("finca_id", 0)

        try:
            lote_id = db.create_lote(
                finca_id=finca_id,
                nombre=nombre,
                area=area,
                num_arboles=arboles,
                variedad=variedad,
                fecha_siembra=fecha,
            )

            await message.answer(
                f"✅ <b>¡Lote creado exitosamente!</b> 🎉\n\n"
                f"📍 <b>Nombre:</b> {nombre}\n"
                f"📐 <b>Área:</b> {area} ha\n"
                f"🌳 <b>Árboles:</b> {arboles}\n"
                f"🌱 <b>Variedad:</b> {variedad or 'No especificada'}\n"
                f"📅 <b>Siembra:</b> {fecha or 'No especificada'}\n\n"
                "Usa /lotes para ver tus lotes o /ingreso para registrar ventas. ☕",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

        except Exception as e:
            logger.error(f"Error al crear lote: {e}", exc_info=True)
            await message.answer("❌ <b>Error al crear el lote.</b> Intenta de nuevo.", parse_mode="HTML", reply_markup=boton_menu())

        await state.clear()

    @router.callback_query(LoteForm.esperando_fecha_siembra, F.data.startswith("fecha:"))
    async def procesar_fecha_callback_lote(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        opcion = callback.data.split(":", 1)[1]

        if opcion == "hoy":
            fecha = fecha_hoy()
        elif opcion == "ayer":
            fecha = fecha_ayer()
        else:  # custom
            await callback.message.answer("✏️ Escribí la fecha en formato DD/MM/AAAA:", reply_markup=botones_fecha())
            return

        # Convertir a ISO
        from datetime import datetime
        d = datetime.strptime(fecha, "%d/%m/%Y")
        fecha_iso = d.strftime("%Y-%m-%d")

        data = await state.get_data()
        nombre = data.get("nombre", "")
        area = data.get("area", 0)
        arboles = data.get("arboles", 0)
        variedad = data.get("variedad", "")
        finca_id = data.get("finca_id", 0)

        try:
            lote_id = db.create_lote(
                finca_id=finca_id,
                nombre=nombre,
                area=area,
                num_arboles=arboles,
                variedad=variedad,
                fecha_siembra=fecha_iso,
            )

            await callback.message.answer(
                f"✅ <b>¡Lote creado exitosamente!</b> 🎉\n\n"
                f"📍 <b>Nombre:</b> {nombre}\n"
                f"📐 <b>Área:</b> {area} ha\n"
                f"🌳 <b>Árboles:</b> {arboles}\n"
                f"🌱 <b>Variedad:</b> {variedad or 'No especificada'}\n"
                f"📅 <b>Siembra:</b> {fecha}\n\n"
                "Usa /lotes para ver tus lotes o /ingreso para registrar ventas. ☕",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

        except Exception as e:
            logger.error(f"Error al crear lote: {e}", exc_info=True)
            await callback.message.answer("❌ <b>Error al crear el lote.</b> Intenta de nuevo.", parse_mode="HTML", reply_markup=boton_menu())

        await state.clear()

    return router
