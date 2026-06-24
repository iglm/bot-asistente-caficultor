"""
Handler de /lotes - Gestión de lotes.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database

logger = logging.getLogger(__name__)


class LoteForm(StatesGroup):
    esperando_finca = State()
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
                    [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
                ]
            )

            if edit:
                await message.edit_text(texto, parse_mode="HTML", reply_markup=keyboard)
            else:
                await message.answer(texto, parse_mode="HTML", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error al mostrar lotes: {e}", exc_info=True)
            error_text = "❌ Error al obtener lotes."
            if edit:
                await message.edit_text(error_text, parse_mode="HTML")
            else:
                await message.answer(error_text, parse_mode="HTML")

    @router.message(Command("lotes"))
    @router.callback_query(F.data == "menu_lotes")
    async def cmd_lotes(event: types.Message | types.CallbackQuery, state: FSMContext):
        """Muestra el menú de lotes."""
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
            await send("⏳ <b>No tienes acceso.</b> Usa /start para solicitar aprobación.", parse_mode="HTML")
            return

        try:
            fincas = db.get_fincas(user_id)
            if not fincas:
                await send(
                    "❌ <b>No tienes fincas registradas.</b>\n\n"
                    "Primero crea una finca con /fincas 🗺️",
                    parse_mode="HTML",
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
                + [
                    [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
                ]
            )

            await send(
                "🌱 <b>Gestión de Lotes</b>\n\nSelecciona una finca:",
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        except Exception as e:
            logger.error(f"Error en /lotes: {e}", exc_info=True)
            await send("❌ <b>Error al obtener lotes.</b>", parse_mode="HTML")

    @router.callback_query(F.data.startswith("lotes_finca:"))
    async def seleccionar_finca_lotes(callback: types.CallbackQuery):
        """Muestra los lotes de una finca seleccionada."""
        await callback.answer()
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML")
            return

        await mostrar_lotes(db, callback.message, finca_id, finca["nombre"], edit=True)

    @router.callback_query(F.data.startswith("nuevo_lote:"))
    async def nuevo_lote(callback: types.CallbackQuery, state: FSMContext):
        """Inicia el proceso de crear un nuevo lote."""
        await callback.answer()
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ *Finca no encontrada.*", parse_mode="Markdown")
            return

        await state.update_data(finca_id=finca_id, finca_nombre=finca["nombre"])

        await callback.message.edit_text(
            f"🌱 *Nuevo Lote en {finca['nombre']}*\n\n"
            "Paso 1/5: ¿Cuál es el *nombre* del lote?\n\n"
            "*(Escribe el nombre o /cancelar)*",
            parse_mode="Markdown",
        )
        await state.set_state(LoteForm.esperando_nombre)

    @router.message(LoteForm.esperando_nombre, F.text)
    async def recibir_nombre_lote(message: types.Message, state: FSMContext):
        nombre = message.text.strip()
        if not nombre:
            await message.answer("❌ El nombre no puede estar vacío:")
            return

        await state.update_data(nombre=nombre)
        data = await state.get_data()
        await message.answer(
            f"✅ *Nombre:* {nombre}\n\n"
            "Paso 2/5: ¿Cuál es el *área* en hectáreas?\n\n"
            "*(Ej: 2.5 — escribe 0 si no sabes)*",
            parse_mode="Markdown",
        )
        await state.set_state(LoteForm.esperando_area)

    @router.message(LoteForm.esperando_area, F.text)
    async def recibir_area_lote(message: types.Message, state: FSMContext):
        try:
            area = float(message.text.strip().replace(",", "."))
            if area < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un número válido (ej: 2.5):")
            return

        await state.update_data(area=area)
        await message.answer(
            f"✅ *Área:* {area} ha\n\n"
            "Paso 3/5: ¿Cuántos *árboles* tiene el lote?\n\n"
            "*(Escribe 0 si no sabes)*",
            parse_mode="Markdown",
        )
        await state.set_state(LoteForm.esperando_arboles)

    @router.message(LoteForm.esperando_arboles, F.text)
    async def recibir_arboles_lote(message: types.Message, state: FSMContext):
        try:
            arboles = int(message.text.strip())
            if arboles < 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un número entero válido:")
            return

        await state.update_data(arboles=arboles)
        await message.answer(
            f"✅ *Árboles:* {arboles}\n\n"
            "Paso 4/5: ¿Cuál es la *variedad* de café?\n\n"
            "*(Ej: Castillo, Caturra, Colombia — o '/' para omitir)*",
            parse_mode="Markdown",
        )
        await state.set_state(LoteForm.esperando_variedad)

    @router.message(LoteForm.esperando_variedad, F.text)
    async def recibir_variedad_lote(message: types.Message, state: FSMContext):
        variedad = message.text.strip()
        if variedad == "/":
            variedad = ""

        await state.update_data(variedad=variedad)
        await message.answer(
            f"✅ *Variedad:* {variedad or '(omitido)'}\n\n"
            "Paso 5/5: ¿Cuál es la *fecha de siembra*?\n\n"
            "*(Formato: DD/MM/AAAA o AAAA-MM-DD — o '/' para omitir)*",
            parse_mode="Markdown",
        )
        await state.set_state(LoteForm.esperando_fecha_siembra)

    @router.message(LoteForm.esperando_fecha_siembra, F.text)
    async def recibir_fecha_lote(message: types.Message, state: FSMContext):
        fecha = message.text.strip()
        if fecha == "/":
            fecha = ""
        else:
            # Validar formato de fecha
            from datetime import datetime
            fecha_valida = False
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    datetime.strptime(fecha, fmt)
                    # Convertir a ISO
                    if fmt == "%d/%m/%Y":
                        d = datetime.strptime(fecha, fmt)
                        fecha = d.strftime("%Y-%m-%d")
                    elif fmt == "%d-%m-%Y":
                        d = datetime.strptime(fecha, fmt)
                        fecha = d.strftime("%Y-%m-%d")
                    fecha_valida = True
                    break
                except ValueError:
                    continue

            if not fecha_valida:
                await message.answer(
                    "❌ Fecha inválida. Usa formato DD/MM/AAAA o AAAA-MM-DD:"
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
                f"✅ *¡Lote creado exitosamente!* 🎉\n\n"
                f"📍 *Nombre:* {nombre}\n"
                f"📐 *Área:* {area} ha\n"
                f"🌳 *Árboles:* {arboles}\n"
                f"🌱 *Variedad:* {variedad or 'No especificada'}\n"
                f"📅 *Siembra:* {fecha or 'No especificada'}\n\n"
                "Usa /lotes para ver tus lotes o /ingreso para registrar ventas. ☕",
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Error al crear lote: {e}", exc_info=True)
            await message.answer("❌ *Error al crear el lote.* Intenta de nuevo.", parse_mode="Markdown")

        await state.clear()

    return router
