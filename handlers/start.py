"""
Handler de /start - Registro y verificación de acceso.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart

from database import Database
from config import ADMIN_IDS, BOT_NAME

logger = logging.getLogger(__name__)


def get_start_router(db: Database) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def cmd_start(message: types.Message):
        user_id = message.from_user.id
        username = message.from_user.username or "sin_username"
        full_name = message.from_user.full_name or "Caficultor"

        logger.info(f"/start recibido de user {user_id} (@{username})")

        try:
            # Verificar si el usuario existe
            status = db.get_user_status(user_id)

            if status is None:
                # Nuevo usuario - registrar como pending
                es_nuevo = db.register_user(user_id, username)

                if es_nuevo:
                    await message.answer(
                        f"☕ *¡Bienvenido al {BOT_NAME}!* 🌱\n\n"
                        f"Hola {full_name}, gracias por tu interés.\n\n"
                        "Tu solicitud de acceso ha sido enviada al administrador. "
                        "En breve recibirás una notificación cuando sea aprobada. ⏳\n\n"
                        "☕ *¡Gracias por confiar en nosotros para gestionar tu finca!*",
                        parse_mode="Markdown",
                    )

                    # Notificar a los admins
                    for admin_id in ADMIN_IDS:
                        try:
                            await message.bot.send_message(
                                admin_id,
                                f"🆕 *Nuevo usuario pendiente:*\n\n"
                                f"👤 ID: `{user_id}`\n"
                                f"📝 Username: @{username}\n"
                                f"📛 Nombre: {full_name}\n\n"
                                f"Usa `/usuarios` para gestionar las solicitudes.",
                                parse_mode="Markdown",
                            )
                        except Exception as e:
                            logger.error(f"Error notificando a admin {admin_id}: {e}")
                else:
                    # Usuario ya registrado, verificar si está aprobado
                    if db.is_approved(user_id):
                        await mostrar_menu_principal(message)
                    elif db.is_pending(user_id):
                        await message.answer(
                            "⏳ *Tu solicitud ya está en revisión.*\n\n"
                            "El administrador te notificará cuando sea aprobada. "
                            "¡Gracias por tu paciencia! ☕",
                            parse_mode="Markdown",
                        )
                    else:
                        await message.answer(
                            "❌ *Tu solicitud fue rechazada.*\n\n"
                            "No tienes acceso al bot. Contacta al administrador "
                            "si consideras que esto es un error.",
                            parse_mode="Markdown",
                        )

            elif status == "pending":
                await message.answer(
                    "⏳ *Tu solicitud está pendiente de aprobación.*\n\n"
                    "El administrador te notificará cuando sea aprobada. "
                    "¡Gracias por tu paciencia! ☕",
                    parse_mode="Markdown",
                )

            elif status == "approved":
                await mostrar_menu_principal(message)

            elif status == "rejected":
                await message.answer(
                    "❌ *No tienes acceso al bot.*\n\n"
                    "Tu solicitud fue rechazada. Contacta al administrador "
                    "si consideras que esto es un error.",
                    parse_mode="Markdown",
                )

            else:
                await message.answer(
                    "⚠️ *Error de estado.*\n\n"
                    "Contacta al administrador para resolver este problema.",
                    parse_mode="Markdown",
                )

        except Exception as e:
            logger.error(f"Error en /start para user {user_id}: {e}", exc_info=True)
            await message.answer(
                "❌ *Error interno.*\n\n"
                "Ocurrió un error al procesar tu solicitud. Intenta de nuevo más tarde.",
                parse_mode="Markdown",
            )

    @router.callback_query(F.data == "volver_menu")
    async def volver_al_menu(callback: types.CallbackQuery):
        """Vuelve al menú principal."""
        await callback.answer()
        await mostrar_menu_principal(callback.message)

    return router


async def mostrar_menu_principal(message: types.Message):
    """Muestra el menú principal del bot."""
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🗺️ Fincas", callback_data="menu_fincas"),
                types.InlineKeyboardButton(text="🌱 Lotes", callback_data="menu_lotes"),
            ],
            [
                types.InlineKeyboardButton(text="💰 Ingresos", callback_data="menu_ingresos"),
                types.InlineKeyboardButton(text="📉 Costos", callback_data="menu_costos"),
            ],
            [
                types.InlineKeyboardButton(text="📊 Resumen", callback_data="menu_resumen"),
                types.InlineKeyboardButton(text="📊 Excel", callback_data="menu_excel"),
            ],
            [
                types.InlineKeyboardButton(text="❓ Ayuda", callback_data="menu_ayuda"),
            ],
        ]
    )

    await message.answer(
        "☕ *¡Bienvenido al Asistente Caficultor!* 🌱\n\n"
        "Selecciona una opción del menú para comenzar:\n\n"
        "🗺️ *Fincas* — Gestionar tus fincas\n"
        "🌱 *Lotes* — Administrar lotes\n"
        "💰 *Ingresos* — Registrar ventas de café\n"
        "📉 *Costos* — Registrar costos de producción\n"
        "📊 *Resumen* — Ver datos y exportar Excel\n"
        "❓ *Ayuda* — Guía de uso",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
