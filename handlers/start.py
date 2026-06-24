"""
Handler de /start - Registro, aviso legal y verificación de acceso.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart

from database import Database
from config import ADMIN_IDS, BOT_NAME, AVISO_LEGAL, NOTIFICATION_GROUP_ID
from utils import boton_menu, construir_menu_principal

logger = logging.getLogger(__name__)


async def mostrar_aviso_legal(message: types.Message, db: Database, es_nuevo: bool):
    """Muestra el aviso legal con botones de aceptar/no aceptar."""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="✅ Acepto y continuar",
                callback_data="aceptar_terminos",
            ),
            types.InlineKeyboardButton(
                text="❌ No aceptar",
                callback_data="no_aceptar_terminos",
            ),
        ],
    ])

    await message.answer(
        f"☕ <b>¡Bienvenido al Asistente de Costos para Caficultores!</b>\n\n"
        f"Antes de empezar, necesitamos que aceptes lo siguiente:\n\n"
        f"{AVISO_LEGAL}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def notificar_admin_nuevo_usuario(message: types.Message, user_id: int, username: str, full_name: str):
    """Notifica a los administradores sobre un nuevo usuario pendiente."""
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


async def mostrar_menu_principal(message: types.Message):
    """Muestra el menú principal del bot."""
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    keyboard = construir_menu_principal(is_admin=is_admin)

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
            # Obtener datos completos del usuario
            user = db.get_user(user_id)

            if user is None:
                # Nuevo usuario — registrar como pending
                es_nuevo = db.register_user(user_id, username)
                if not es_nuevo:
                    # Ya existía (carrera de condiciones), recargar
                    user = db.get_user(user_id)

                # Mostrar aviso legal (nuevo usuario no ha aceptado términos)
                await mostrar_aviso_legal(message, db, es_nuevo=True)
                return

            # El usuario ya existe — verificar si aceptó términos
            if user.get('acepto_terminos', 0) == 0:
                # No ha aceptado los términos aún — mostrar aviso legal
                await mostrar_aviso_legal(message, db, es_nuevo=False)
                return

            # Ya aceptó términos, proceder según status
            status = user['status']

            if status == "pending":
                await message.answer(
                    "⏳ <b>Tu solicitud está pendiente de aprobación.</b>\n\n"
                    "El administrador te notificará cuando sea aprobada. "
                    "¡Gracias por tu paciencia! ☕",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )

            elif status == "approved":
                await mostrar_menu_principal(message)

            elif status == "rejected":
                await message.answer(
                    "❌ <b>No tienes acceso al bot.</b>\n\n"
                    "Tu solicitud fue rechazada. Contacta al administrador "
                    "si consideras que esto es un error.",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )

            else:
                await message.answer(
                    "⚠️ <b>Error de estado.</b>\n\n"
                    "Contacta al administrador para resolver este problema.",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )

        except Exception as e:
            logger.error(f"Error en /start para user {user_id}: {e}", exc_info=True)
            await message.answer(
                "❌ <b>Error interno.</b>\n\n"
                "Ocurrió un error al procesar tu solicitud. Intenta de nuevo más tarde.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

    @router.callback_query(F.data == "aceptar_terminos")
    async def callback_aceptar_terminos(callback: types.CallbackQuery):
        """Maneja la aceptación de términos legales."""
        user_id = callback.from_user.id
        await callback.answer()

        try:
            # Marcar como aceptado en DB
            db.aceptar_terminos(user_id)

            # Obtener datos actualizados del usuario
            user = db.get_user(user_id)

            if user is None:
                await callback.message.edit_text(
                    "❌ <b>Error:</b> No se pudo encontrar tu usuario. "
                    "Usá /start para intentar de nuevo.",
                    parse_mode="HTML",
                )
                return

            # Verificar si es un usuario nuevo (no aprobado aún)
            if user['status'] == 'pending':
                username = callback.from_user.username or "sin_username"
                full_name = callback.from_user.full_name or "Caficultor"

                # Si fue creado justo ahora, notificar a los admins
                await callback.message.edit_text(
                    "✅ <b>¡Gracias por aceptar los términos!</b>\n\n"
                    "Tu solicitud de acceso ha sido enviada al administrador. "
                    "En breve recibirás una notificación cuando sea aprobada. ⏳\n\n"
                    "☕ <b>¡Gracias por confiar en nosotros para gestionar tu finca!</b>",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )

                # Notificar al admin
                await notificar_admin_nuevo_usuario(
                    callback.message, user_id, username, full_name,
                )

            elif user['status'] == 'approved':
                await callback.message.edit_text(
                    "✅ <b>¡Gracias por aceptar los términos!</b>\n\n"
                    "Ya tenés acceso al bot. Usá /start para continuar.",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )

            else:
                await callback.message.edit_text(
                    "✅ <b>¡Gracias por aceptar los términos!</b>\n\n"
                    "Usá /start para continuar.",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )

        except Exception as e:
            logger.error(f"Error en aceptar_terminos para user {user_id}: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ <b>Error interno.</b>\n\n"
                "Ocurrió un error al procesar tu solicitud. Intenta de nuevo con /start.",
                parse_mode="HTML",
            )

    @router.callback_query(F.data == "no_aceptar_terminos")
    async def callback_no_aceptar_terminos(callback: types.CallbackQuery):
        """Maneja cuando el usuario no acepta los términos."""
        await callback.answer()
        await callback.message.edit_text(
            "❌ <b>No aceptaste los términos.</b>\n\n"
            "Lamentablemente, no podés usar este bot sin aceptar las condiciones "
            "de uso y protección de datos.\n\n"
            "Si cambias de opinión, usá /start en cualquier momento.",
            parse_mode="HTML",
        )

    return router
