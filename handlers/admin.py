"""
Handler de comandos de administración: /aprobar, /rechazar, /usuarios, /revocar.
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
        """Lista todos los usuarios organizados por estado con botones inline."""
        if not is_admin(message.from_user.id):
            await message.answer("❌ <b>No tienes permiso para usar este comando.</b>", parse_mode="HTML")
            return

        try:
            aprobados = db.get_approved_users()
            pendientes = db.get_pending_users()
            rechazados = db.get_rejected_users()

            texto = "📋 <b>Lista de Usuarios</b>\n\n"

            # Aprobados
            if aprobados:
                texto += "✅ <b>Aprobados:</b>\n"
                for u in aprobados:
                    fecha_aprob = u.get("approved_at", "") or ""
                    if fecha_aprob:
                        fecha_aprob = fecha_aprob[:10]  # Solo YYYY-MM-DD
                    texto += f"  👤 <code>{u['user_id']}</code> — @{u['username'] or 'sin_username'}"
                    if fecha_aprob:
                        texto += f" — 🗓️ {fecha_aprob}"
                    texto += "\n"
                texto += "\n"

            # Pendientes
            if pendientes:
                texto += "⏳ <b>Pendientes:</b>\n"
                for u in pendientes:
                    fecha_reg = u.get("created_at", "") or ""
                    if fecha_reg:
                        fecha_reg = fecha_reg[:10]
                    texto += f"  👤 <code>{u['user_id']}</code> — @{u['username'] or 'sin_username'}"
                    if fecha_reg:
                        texto += f" — 🗓️ {fecha_reg}"
                    texto += "\n"
                texto += "\n"

            # Rechazados
            if rechazados:
                texto += "❌ <b>Rechazados:</b>\n"
                for u in rechazados:
                    fecha_reg = u.get("created_at", "") or ""
                    if fecha_reg:
                        fecha_reg = fecha_reg[:10]
                    texto += f"  👤 <code>{u['user_id']}</code> — @{u['username'] or 'sin_username'}"
                    if fecha_reg:
                        texto += f" — 🗓️ {fecha_reg}"
                    texto += "\n"
                texto += "\n"

            if not aprobados and not pendientes and not rechazados:
                texto += "No hay usuarios registrados.\n"

            # Construir botones inline
            inline_buttons = []

            # Botones de aprobar/rechazar para pendientes
            for p in pendientes[:10]:
                inline_buttons.append([
                    types.InlineKeyboardButton(
                        text=f"✅ Aprobar @{p['username'] or p['user_id']}",
                        callback_data=f"aprobar:{p['user_id']}",
                    ),
                    types.InlineKeyboardButton(
                        text=f"❌ Rechazar @{p['username'] or p['user_id']}",
                        callback_data=f"rechazar:{p['user_id']}",
                    ),
                ])

            # Botones de revocar para aprobados
            for a in aprobados[:10]:
                inline_buttons.append([
                    types.InlineKeyboardButton(
                        text=f"🚫 Revocar @{a['username'] or a['user_id']}",
                        callback_data=f"revocar:{a['user_id']}",
                    ),
                ])

            # Botones de re-activar para rechazados
            for r in rechazados[:10]:
                inline_buttons.append([
                    types.InlineKeyboardButton(
                        text=f"✅ Re-activar @{r['username'] or r['user_id']}",
                        callback_data=f"reactivar:{r['user_id']}",
                    ),
                ])

            if inline_buttons:
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=inline_buttons)
                await message.answer(texto, parse_mode="HTML", reply_markup=keyboard)
            else:
                await message.answer(texto, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Error en /usuarios: {e}", exc_info=True)
            await message.answer("❌ <b>Error al obtener la lista de usuarios.</b>", parse_mode="HTML")

    @router.message(Command("revocar"))
    async def cmd_revocar(message: types.Message):
        """Revoca acceso de un usuario aprobado. Uso: /revocar USER_ID"""
        if not is_admin(message.from_user.id):
            await message.answer("❌ <b>No tienes permiso para usar este comando.</b>", parse_mode="HTML")
            return

        args = message.text.strip().split()
        if len(args) < 2:
            await message.answer(
                "⚠️ <b>Uso:</b> <code>/revocar USER_ID</code>\n\n"
                "Ejemplo: <code>/revocar 123456789</code>",
                parse_mode="HTML",
            )
            return

        try:
            target_id = int(args[1])
        except ValueError:
            await message.answer("❌ <b>ID inválido.</b> Debe ser un número.", parse_mode="HTML")
            return

        try:
            success = db.revoke_user(target_id)
            if success:
                await message.answer(
                    f"✅ <b>Usuario revocado.</b>\n\n"
                    f"👤 ID: <code>{target_id}</code>\n"
                    f"El usuario ha sido cambiado a estado: <b>rechazado</b>.\n\n"
                    f"Puedes usar /usuarios para ver la lista actualizada.",
                    parse_mode="HTML",
                )
                # Notificar al usuario revocado
                try:
                    await message.bot.send_message(
                        target_id,
                        "❌ <b>Tu acceso al bot ha sido revocado.</b>\n\n"
                        "Si crees que esto es un error, contacta al administrador.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning(f"No se pudo notificar al usuario {target_id}: {e}")
            else:
                await message.answer(
                    f"❌ <b>No se pudo revocar al usuario.</b>\n\n"
                    f"ID: <code>{target_id}</code>\n\n"
                    "El usuario no existe o no está en estado <b>aprobado</b>.\n"
                    "Usa /usuarios para ver los usuarios aprobados.",
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.error(f"Error en /revocar para {target_id}: {e}", exc_info=True)
            await message.answer("❌ <b>Error al revocar usuario.</b>", parse_mode="HTML")

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
                    "✅ <b>¡Felicidades! Tu solicitud ha sido aprobada.</b> ☕\n\n"
                    "Ya puedes usar el bot para gestionar tu finca.\n"
                    "Usa /start para comenzar.",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"No se pudo notificar al usuario {user_id}: {e}")

            # Actualizar mensaje del admin
            await callback.message.edit_text(
                f"{callback.message.text}\n\n✅ <b>Usuario aprobado</b> ✅",
                parse_mode="HTML",
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
                    "❌ <b>Tu solicitud de acceso al bot ha sido rechazada.</b>\n\n"
                    "Si crees que esto es un error, contacta al administrador.",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"No se pudo notificar al usuario {user_id}: {e}")

            # Actualizar mensaje del admin
            await callback.message.edit_text(
                f"{callback.message.text}\n\n❌ <b>Usuario rechazado</b> ❌",
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"Error al rechazar usuario: {e}", exc_info=True)
            await callback.answer("❌ Error al rechazar usuario.", show_alert=True)

    @router.callback_query(F.data.startswith("revocar:"))
    async def callback_revocar(callback: types.CallbackQuery):
        """Revoca acceso de un usuario aprobado desde callback."""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ No tienes permiso.", show_alert=True)
            return

        try:
            user_id = int(callback.data.split(":")[1])
            success = db.revoke_user(user_id)

            if success:
                await callback.answer("🚫 Usuario revocado correctamente.")
                await callback.message.edit_reply_markup(reply_markup=None)

                # Notificar al usuario
                try:
                    await callback.bot.send_message(
                        user_id,
                        "❌ <b>Tu acceso al bot ha sido revocado.</b>\n\n"
                        "Si crees que esto es un error, contacta al administrador.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning(f"No se pudo notificar al usuario {user_id}: {e}")

                # Actualizar mensaje del admin
                await callback.message.edit_text(
                    f"{callback.message.text}\n\n🚫 <b>Usuario revocado</b> 🚫",
                    parse_mode="HTML",
                )
            else:
                await callback.answer("❌ El usuario no está aprobado.", show_alert=True)

        except Exception as e:
            logger.error(f"Error al revocar usuario: {e}", exc_info=True)
            await callback.answer("❌ Error al revocar usuario.", show_alert=True)

    @router.callback_query(F.data.startswith("reactivar:"))
    async def callback_reactivar(callback: types.CallbackQuery):
        """Re-activa a un usuario rechazado desde callback (lo pone como pending)."""
        if not is_admin(callback.from_user.id):
            await callback.answer("❌ No tienes permiso.", show_alert=True)
            return

        try:
            user_id = int(callback.data.split(":")[1])
            success = db.reactivate_user(user_id)

            if success:
                await callback.answer("✅ Usuario re-activado (pendiente de aprobación).")
                await callback.message.edit_reply_markup(reply_markup=None)

                # Notificar al usuario
                try:
                    await callback.bot.send_message(
                        user_id,
                        "🔄 <b>Tu solicitud ha sido re-activada.</b>\n\n"
                        "Un administrador revisará tu acceso nuevamente.\n"
                        "Gracias por tu paciencia.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning(f"No se pudo notificar al usuario {user_id}: {e}")

                # Actualizar mensaje del admin
                await callback.message.edit_text(
                    f"{callback.message.text}\n\n🔄 <b>Usuario re-activado</b> (pendiente) 🔄",
                    parse_mode="HTML",
                )
            else:
                await callback.answer("❌ El usuario no está rechazado.", show_alert=True)

        except Exception as e:
            logger.error(f"Error al reactivar usuario: {e}", exc_info=True)
            await callback.answer("❌ Error al reactivar usuario.", show_alert=True)

    return router
