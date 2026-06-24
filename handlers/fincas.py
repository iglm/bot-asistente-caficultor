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
            await send("⏳ *No tienes acceso.* Usa /start para solicitar aprobación.", parse_mode="Markdown")
            return

        try:
            fincas = db.get_fincas(user_id)
            texto = "🗺️ *Gestión de Fincas*\n\n"

            if fincas:
                texto += "*Tus fincas registradas:*\n"
                for f in fincas:
                    texto += f"  🏠 *{f['nombre']}* — {f['region'] or 'Sin región'} / {f['departamento'] or 'Sin depto.'}\n"
                texto += "\n"
            else:
                texto += "Aún no tienes fincas registradas. ¡Crea tu primera finca! 🌱\n\n"

            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="➕ Nueva Finca", callback_data="nueva_finca")],
                    [types.InlineKeyboardButton(text="🔙 Volver al menú", callback_data="volver_menu")],
                ]
            )

            await send(texto, parse_mode="Markdown", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Error en /fincas: {e}", exc_info=True)
            await send("❌ *Error al obtener las fincas.*", parse_mode="Markdown")

    @router.callback_query(F.data == "nueva_finca")
    async def nueva_finca(callback: types.CallbackQuery, state: FSMContext):
        """Inicia el proceso de crear una nueva finca."""
        await callback.answer()
        await callback.message.edit_text(
            "🏠 *Crear Nueva Finca*\n\n"
            "Paso 1/3: ¿Cuál es el *nombre* de tu finca?\n\n"
            "*(Escribe el nombre o /cancelar para cancelar)*",
            parse_mode="Markdown",
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

        await state.update_data(nombre=nombre)
        await message.answer(
            f"✅ *Nombre:* {nombre}\n\n"
            "Paso 2/3: ¿Cuál es la *región* de tu finca?\n\n"
            "*(Escribe la región o '/' para omitir)*",
            parse_mode="Markdown",
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
            f"✅ *Región:* {region or '(omitido)'}\n\n"
            "Paso 3/3: ¿Cuál es el *departamento* de tu finca?\n\n"
            "*(Escribe el departamento o '/' para omitir)*",
            parse_mode="Markdown",
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
                f"✅ *¡Finca creada exitosamente!* 🎉\n\n"
                f"🏠 *Nombre:* {nombre}\n"
                f"📍 *Región:* {region or 'No especificada'}\n"
                f"📍 *Departamento:* {departamento or 'No especificado'}\n"
                f"🆔 *ID:* `{finca_id}`\n\n"
                "Ahora puedes registrar lotes con /lotes 🌱",
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Error al crear finca: {e}", exc_info=True)
            await message.answer(
                "❌ *Error al crear la finca.* Intenta de nuevo más tarde.",
                parse_mode="Markdown",
            )

        await state.clear()

    @router.message(FincaForm.esperando_nombre)
    @router.message(FincaForm.esperando_region)
    @router.message(FincaForm.esperando_departamento)
    async def entrada_invalida(message: types.Message):
        """Maneja entradas no textuales durante el formulario."""
        await message.answer(
            "❌ Por favor, escribe un texto válido o usa /cancelar para cancelar.",
            parse_mode="Markdown",
        )

    @router.message(Command("cancelar"))
    async def cmd_cancelar(message: types.Message, state: FSMContext):
        """Cancela el formulario actual."""
        current_state = await state.get_state()
        if current_state is None:
            await message.answer("No hay ninguna operación en curso.", parse_mode="Markdown")
            return

        await state.clear()
        await message.answer(
            "✅ *Operación cancelada.*\n\nUsa /fincas para volver al menú.",
            parse_mode="Markdown",
        )

    return router
