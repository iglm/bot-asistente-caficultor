"""
Handler de comandos de administración: /aprobar, /rechazar, /usuarios.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command

from database import Database
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


def get_admin_router(db: Database) -> Router:
    router = Router()

    def is_admin(user_id: int) -> bool:
        return user_id in ADMIN_IDS

    @router.message(Command("usuarios"))
    async def cmd_usuarios(message: types.Message):
        """Lista todos los usuarios con su estado."""
        if not is_admin(message.from_user.id):
            await message.answer("❌ *No tienes permiso para usar este comando.*", parse_mode="Markdown")
            return

        try:
            pendientes = db.get_pending_users()
            todos = db.get_all_users()

            texto = "📋 *Lista de Usuarios*\n\n"

            if pendientes:
                texto += "⏳ *Pendientes:*\n"
                for u in pendientes:
                    texto += f"  👤 `{u['user_id']}` — @{u['username'] or 'sin_username'}\n"
                texto += "\n"

            texto += "*Todos los usuarios:*\n"
            for u in todos[:20]:  # Máximo 20
                status_emoji = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                }.get(u["status"], "❓")
                texto += f"  {status_emoji} `{u['user_id']}` — @{u['username'] or 'sin_username'} — *{u['status']}*\n"

            if len(todos) > 20:
                texto += f"\n... y {len(todos) - 20} más."

            # Si hay pendientes, agregar botones para aprobar/rechazar
            if pendientes:
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text=f"✅ Aprobar @{p['username'] or p['user_id']}",
                                callback_data=f"aprobar:{p['user_id']}",
                            )
                        ]
                        for p in pendientes[:5]  # Máximo 5 botones
                    ]
                    + [
                        [
                            types.InlineKeyboardButton(
                                text=f"❌ Rechazar @{p['username'] or p['user_id']}",
                                callback_data=f"rechazar:{p['user_id']}",
                            )
                        ]
                        for p in pendientes[:5]
                    ]
                )
                await message.answer(texto, parse_mode="Markdown", reply_markup=keyboard)
            else:
                await message.answer(texto, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error en /usuarios: {e}", exc_info=True)
            await message.answer("❌ *Error al obtener la lista de usuarios.*", parse_mode="Markdown")

    @router.callback_query(F.data.startswith("aprobar:"))
    async def callback_aprobar(callback: types.CallbackQuery):
        """Aprueba a un usuario desde callback."""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ No tienes permiso.", show_alert=True)
            return

        try:
            user_id = int(callback.data.split(":")[1])
            db.approve_user(user_id, callback.from_user.id)

            await callback.answer("✅ Usuario aprobado correctamente.")
            await callback.message.edit_reply_markup(reply_markup=None)

            # Notificar al usuario
            try:
                await callback.bot.send_message(
                    user_id,
                    "✅ *¡Felicidades! Tu solicitud ha sido aprobada.* ☕\n\n"
                    "Ya puedes usar el bot para gestionar tu finca.\n"
                    "Usa /start para comenzar.",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"No se pudo notificar al usuario {user_id}: {e}")

            # Actualizar mensaje del admin
            await callback.message.edit_text(
                f"{callback.message.text}\n\n✅ *Usuario aprobado* ✅",
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Error al aprobar usuario: {e}", exc_info=True)
            await callback.answer("❌ Error al aprobar usuario.", show_alert=True)

    @router.callback_query(F.data.startswith("rechazar:"))
    async def callback_rechazar(callback: types.CallbackQuery):
        """Rechaza a un usuario desde callback."""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ No tienes permiso.", show_alert=True)
            return

        try:
            user_id = int(callback.data.split(":")[1])
            db.reject_user(user_id)

            await callback.answer("❌ Usuario rechazado.")
            await callback.message.edit_reply_markup(reply_markup=None)

            # Notificar al usuario
            try:
                await callback.bot.send_message(
                    user_id,
                    "❌ *Tu solicitud de acceso al bot ha sido rechazada.*\n\n"
                    "Si crees que esto es un error, contacta al administrador.",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.warning(f"No se pudo notificar al usuario {user_id}: {e}")

            # Actualizar mensaje del admin
            await callback.message.edit_text(
                f"{callback.message.text}\n\n❌ *Usuario rechazado* ❌",
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Error al rechazar usuario: {e}", exc_info=True)
            await callback.answer("❌ Error al rechazar usuario.", show_alert=True)

    return router
