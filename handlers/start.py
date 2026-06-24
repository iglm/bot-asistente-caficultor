"""
Handler de /start - Registro y verificación de acceso.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart

from database import Database
from config import ADMIN_IDS, BOT_NAME, NOTIFICATION_GROUP_ID

logger = logging.getLogger(__name__)


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
        "☕ <b>¡Bienvenido al Asistente Caficultor!</b> 🌱\n\n"
        "Selecciona una opción del menú para comenzar:\n\n"
        "🗺️ <b>Fincas</b> — Gestionar tus fincas\n"
        "🌱 <b>Lotes</b> — Administrar lotes\n"
        "💰 <b>Ingresos</b> — Registrar ventas de café\n"
        "📉 <b>Costos</b> — Registrar costos de producción\n"
        "📊 <b>Resumen</b> — Ver datos y exportar Excel\n"
        "❓ <b>Ayuda</b> — Guía de uso",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


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
                        f"☕ <b>¡Bienvenido al {BOT_NAME}!</b> 🌱\n\n"
                        f"Hola {full_name}, gracias por tu interés.\n\n"
                        "Tu solicitud de acceso ha sido enviada al administrador. "
                        "En breve recibirás una notificación cuando sea aprobada. ⏳\n\n"
                        "☕ <b>¡Gracias por confiar en nosotros para gestionar tu finca!</b>",
                        parse_mode="HTML",
                    )

                    # Notificar a los admins con botones inline
                    keyboard = types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                types.InlineKeyboardButton(
                                    text="✅ Aprobar",
                                    callback_data=f"aprobar:{user_id}",
                                ),
                                types.InlineKeyboardButton(
                                    text="❌ Rechazar",
                                    callback_data=f"rechazar:{user_id}",
                                ),
                            ],
                        ]
                    )
                    for admin_id in ADMIN_IDS:
                        try:
                            await message.bot.send_message(
                                admin_id,
                                f"🆕 <b>Nuevo usuario pendiente:</b>\n\n"
                                f"👤 ID: <code>{user_id}</code>\n"
                                f"📝 Username: @{username}\n"
                                f"📛 Nombre: {full_name}\n\n"
                                f"Usa los botones de abajo para gestionar la solicitud.",
                                parse_mode="HTML",
                                reply_markup=keyboard,
                            )
                        except Exception as e:
                            logger.error(f"Error notificando a admin {admin_id}: {e}")
                    
                    # Notificar también al grupo de supervision
                    try:
                        await message.bot.send_message(
                            NOTIFICATION_GROUP_ID,
                            f"🆕 <b>Nuevo usuario pendiente:</b>\n\n"
                            f"👤 ID: <code>{user_id}</code>\n"
                            f"📝 Username: @{username}\n"
                            f"📛 Nombre: {full_name}\n\n"
                            f"Usa los botones para gestionar.",
                            parse_mode="HTML",
                            reply_markup=keyboard,
                        )
                    except Exception as e:
                        logger.error(f"Error notificando al grupo: {e}")
                else:
                    # Usuario ya registrado, verificar si está aprobado
                    if db.is_approved(user_id):
                        await mostrar_menu_principal(message)
                    elif db.is_pending(user_id):
                        await message.answer(
                            "⏳ <b>Tu solicitud ya está en revisión.</b>\n\n"
                            "El administrador te notificará cuando sea aprobada. "
                            "¡Gracias por tu paciencia! ☕",
                            parse_mode="HTML",
                        )
                    else:
                        await message.answer(
                            "❌ <b>Tu solicitud fue rechazada.</b>\n\n"
                            "No tienes acceso al bot. Contacta al administrador "
                            "si consideras que esto es un error.",
                            parse_mode="HTML",
                        )

            elif status == "pending":
                await message.answer(
                    "⏳ <b>Tu solicitud está pendiente de aprobación.</b>\n\n"
                    "El administrador te notificará cuando sea aprobada. "
                    "¡Gracias por tu paciencia! ☕",
                    parse_mode="HTML",
                )

            elif status == "approved":
                await mostrar_menu_principal(message)

            elif status == "rejected":
                await message.answer(
                    "❌ <b>No tienes acceso al bot.</b>\n\n"
                    "Tu solicitud fue rechazada. Contacta al administrador "
                    "si consideras que esto es un error.",
                    parse_mode="HTML",
                )

            else:
                await message.answer(
                    "⚠️ <b>Error de estado.</b>\n\n"
                    "Contacta al administrador para resolver este problema.",
                    parse_mode="HTML",
                )

        except Exception as e:
            logger.error(f"Error en /start para user {user_id}: {e}", exc_info=True)
            await message.answer(
                "❌ <b>Error interno.</b>\n\n"
                "Ocurrió un error al procesar tu solicitud. Intenta de nuevo más tarde.",
                parse_mode="HTML",
            )

    @router.callback_query(F.data == "volver_menu")
    async def volver_al_menu(callback: types.CallbackQuery):
        """Vuelve al menú principal."""
        await callback.answer()
        await mostrar_menu_principal(callback.message)

    return router
