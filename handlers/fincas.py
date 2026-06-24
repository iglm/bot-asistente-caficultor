"""
Handler de /fincas - Gestión de fincas.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


class FincaForm(StatesGroup):
    esperando_nombre = State()
    esperando_region = State()
    esperando_departamento = State()


def get_fincas_router(db: Database) -> Router:
    router = Router()

    @router.message(Command("fincas"))
    @router.callback_query(F.data == "menu_fincas")
    async def cmd_fincas(event: types.Message | types.CallbackQuery):
        """Muestra el menú de fincas."""
        user_id = event.from_user.id

        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
        else:
            message = event
            send = message.answer

        # Verificar acceso
        if not db.is_approved(user_id):
            await send("⏳ <b>No tienes acceso.</b> Usa /start para solicitar aprobación.", parse_mode="HTML")
            return

        try:
            fincas = db.get_fincas(user_id)
            texto = "🗺️ <b>Gestión de Fincas</b>\n\n"

            if fincas:
                texto += "<b>Tus fincas registradas:</b>\n"
                for f in fincas:
                    texto += f"  🏠 <b>{f['nombre']}</b> — {f['region'] or 'Sin región'} / {f['departamento'] or 'Sin depto.'}\n"
                texto += "\n"
            else:
                texto += "Aún no tienes fincas registradas. ¡Crea tu primera finca! 🌱\n\n"

            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="➕ Nueva Finca", callback_data="nueva_finca")],
                    [types.InlineKeyboardButton(text="🔙 Volver al menú", callback_data="volver_menu")],
                ]
            )

            await send(texto, parse_mode="HTML", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error en /fincas: {e}", exc_info=True)
            await send("❌ <b>Error al obtener las fincas.</b>", parse_mode="HTML")

    @router.callback_query(F.data == "nueva_finca")
    async def nueva_finca(callback: types.CallbackQuery, state: FSMContext):
        """Inicia el proceso de crear una nueva finca."""
        await callback.answer()
        await callback.message.edit_text(
            "🏠 <b>Crear Nueva Finca</b>\n\n"
            "Paso 1/3: ¿Cuál es el <b>nombre</b> de tu finca?\n\n"
            "<i>(Escribe el nombre o /cancelar para cancelar)</i>",
            parse_mode="HTML",
        )
        await state.set_state(FincaForm.esperando_nombre)

    @router.message(FincaForm.esperando_nombre, F.text)
    async def recibir_nombre(message: types.Message, state: FSMContext):
        """Recibe el nombre de la finca."""
        nombre = message.text.strip()
        if not nombre:
            await message.answer("❌ El nombre no puede estar vacío. Intenta de nuevo:")
            return

        if len(nombre) > 100:
            await message.answer("❌ El nombre es demasiado largo (máx. 100 caracteres). Intenta de nuevo:")
            return

        # Verificar que no exista otra finca con el mismo nombre para este usuario
        user_id = message.from_user.id
        fincas_existentes = db.get_fincas(user_id)
        nombre_lower = nombre.lower()
        for finca in fincas_existentes:
            if finca["nombre"].strip().lower() == nombre_lower:
                await message.answer(
                    f"⚠️ <b>Ya tienes una finca llamada \"{nombre}\".</b>\n\n"
                    "Por favor, elige un nombre diferente o usa /cancelar para cancelar.",
                    parse_mode="HTML",
                )
                return

        await state.update_data(nombre=nombre)
        await message.answer(
            f"✅ <b>Nombre:</b> {nombre}\n\n"
            "Paso 2/3: ¿Cuál es la <b>región</b> de tu finca?\n\n"
            "<i>(Escribe la región o '/' para omitir)</i>",
            parse_mode="HTML",
        )
        await state.set_state(FincaForm.esperando_region)

    @router.message(FincaForm.esperando_region, F.text)
    async def recibir_region(message: types.Message, state: FSMContext):
        """Recibe la región de la finca."""
        region = message.text.strip()
        if region == "/":
            region = ""

        await state.update_data(region=region)
        await message.answer(
            f"✅ <b>Región:</b> {region or '(omitido)'}\n\n"
            "Paso 3/3: ¿Cuál es el <b>departamento</b> de tu finca?\n\n"
            "<i>(Escribe el departamento o '/' para omitir)</i>",
            parse_mode="HTML",
        )
        await state.set_state(FincaForm.esperando_departamento)

    @router.message(FincaForm.esperando_departamento, F.text)
    async def recibir_departamento(message: types.Message, state: FSMContext):
        """Recibe el departamento y guarda la finca."""
        departamento = message.text.strip()
        if departamento == "/":
            departamento = ""

        data = await state.get_data()
        nombre = data.get("nombre", "")
        region = data.get("region", "")

        try:
            finca_id = db.create_finca(
                user_id=message.from_user.id,
                nombre=nombre,
                region=region,
                departamento=departamento,
            )

            await message.answer(
                f"✅ <b>¡Finca creada exitosamente!</b> 🎉\n\n"
                f"🏠 <b>Nombre:</b> {nombre}\n"
                f"📍 <b>Región:</b> {region or 'No especificada'}\n"
                f"📍 <b>Departamento:</b> {departamento or 'No especificado'}\n"
                f"🆔 <b>ID:</b> <code>{finca_id}</code>\n\n"
                "Ahora puedes registrar lotes con /lotes 🌱",
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"Error al crear finca: {e}", exc_info=True)
            await message.answer(
                "❌ <b>Error al crear la finca.</b> Intenta de nuevo más tarde.",
                parse_mode="HTML",
            )

        await state.clear()

    @router.message(FincaForm.esperando_nombre)
    @router.message(FincaForm.esperando_region)
    @router.message(FincaForm.esperando_departamento)
    async def entrada_invalida(message: types.Message):
        """Maneja entradas no textuales durante el formulario."""
        await message.answer(
            "❌ Por favor, escribe un texto válido o usa /cancelar para cancelar.",
            parse_mode="HTML",
        )

    return router
