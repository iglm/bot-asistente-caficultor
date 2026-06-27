"""
Handler de /start - Registro, aviso legal y verificación de acceso.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart

from database import Database
from config import ADMIN_IDS, BOT_NAME, AVISO_LEGAL, NOTIFICATION_GROUP_ID
from utils import boton_menu, construir_menu_principal
from .error_handler import error_handler

logger = logging.getLogger(__name__)


async def mostrar_aviso_legal(message: types.Message, db: Database):
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
    @error_handler
    async def cmd_start(message: types.Message):
        user_id = message.from_user.id
        username = message.from_user.username or "sin_username"
        full_name = message.from_user.full_name or "Caficultor"

        logger.info(f"/start recibido de user {user_id} (@{username})")

        # Verificar si ya aceptó términos
        user = db.get_user(user_id)

        if user and user.get('acepto_terminos', 0) == 1:
            # Ya aceptó: directo al menú principal
            is_admin = user_id in ADMIN_IDS
            keyboard = construir_menu_principal(db=None, user_id=user_id, is_admin=is_admin)
            await message.answer(
                "☕ <b>Asistente de Costos</b>\n\n¿Qué querés hacer?",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            # No aceptó o es nuevo: mostrar aviso legal
            await mostrar_aviso_legal(message, db)

    @router.callback_query(F.data == "aceptar_terminos")
    @error_handler
    async def aceptar_terminos(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        await callback.answer()

        # Marcar como aceptado
        db.aceptar_terminos(user_id)

        # Mostrar menú principal
        is_admin = user_id in ADMIN_IDS
        keyboard = construir_menu_principal(db=None, user_id=user_id, is_admin=is_admin)
        await callback.message.edit_text(
            "☕ <b>¡Bienvenido al Asistente de Costos!</b>\n\n¿Qué querés hacer?",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @router.callback_query(F.data == "no_aceptar_terminos")
    @error_handler
    async def no_aceptar_terminos(callback: types.CallbackQuery):
        await callback.answer()
        await callback.message.edit_text(
            "❌ <b>No podés usar este bot sin aceptar los términos.</b>\n\n"
            "Si cambiás de opinión, enviá /start de nuevo.",
            parse_mode="HTML",
        )

    return router
