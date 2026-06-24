"""
Handler de /menu y /cancelar — Intercepta TODOS los estados FSM.
Prioridad máxima: se registra ANTES que cualquier otro handler.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import Database
from config import ADMIN_IDS
from utils import boton_menu, agregar_boton_menu

logger = logging.getLogger(__name__)


def get_menu_router(db: Database) -> Router:
    """Router de menú con prioridad máxima sobre todos los FSM states."""
    router = Router()

    @router.message(Command("menu"))
    @router.message(Command("cancelar"))
    @router.message(F.text == "/")
    async def cmd_menu(event: types.Message, state: FSMContext):
        """Intercepta /menu, /cancelar o / en CUALQUIER estado FSM."""
        # Limpiar CUALQUIER estado activo
        current_state = await state.get_state()
        if current_state:
            logger.info(f"🔄 Cancelando estado {current_state} por /menu o /cancelar")
            await state.clear()

        user_id = event.from_user.id
        is_admin = user_id in ADMIN_IDS
        is_approved = db.is_approved(user_id)

        # Construir menú según estado del usuario
        if not is_approved and not is_admin:
            # Usuario no aprobado
            await event.answer(
                "⏳ <b>Esperando aprobación</b>\n\n"
                "Tu solicitud está pendiente. El administrador debe aprobar tu acceso.\n\n"
                "Usa /start para verificar el estado de tu solicitud.",
                parse_mode="HTML",
            )
            return

        # Menú principal para usuarios aprobados
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="🏠 Fincas", callback_data="menu_fincas"),
                    types.InlineKeyboardButton(text="🌱 Lotes", callback_data="menu_lotes"),
                ],
                [
                    types.InlineKeyboardButton(text="💰 Ingresos", callback_data="menu_ingresos"),
                    types.InlineKeyboardButton(text="📉 Costos", callback_data="menu_costos"),
                ],
                [
                    types.InlineKeyboardButton(text="📊 Resumen", callback_data="menu_resumen"),
                    types.InlineKeyboardButton(text="📋 Exportar Excel", callback_data="menu_excel"),
                ],
                [
                    types.InlineKeyboardButton(text="📥 Importar Excel", callback_data="menu_importar"),
                    types.InlineKeyboardButton(text="🗑️ Borrar datos", callback_data="ir_borrar"),
                ],
                [
                    types.InlineKeyboardButton(text="❓ Ayuda", callback_data="menu_ayuda"),
                ],
            ]
        )

        if is_admin:
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(text="🔧 Admin", callback_data="ir_admin"),
            ])

        await event.answer(
            "☕ <b>Asistente de Costos</b>\n\n"
            "¿Qué querés hacer? Usá los botones:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    # ── Callbacks del menú (solo responden, no cambian state) ──

    @router.callback_query(F.data == "ir_borrar")
    async def menu_borrar(callback: types.CallbackQuery, state: FSMContext):
        """Muestra primera confirmación antes de borrar todos los datos."""
        await callback.answer()
        await state.clear()
        user_id = callback.from_user.id

        # Verificar si tiene datos
        fincas = db.get_fincas(user_id)
        if not fincas:
            await callback.message.answer(
                "✅ <b>No tenés datos en el sistema.</b>\n\n"
                "Ya está todo limpio. Podés empezar creando una finca con /fincas ☕",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="✅ Sí, borrar todo", callback_data="confirmar_borrar:si"),
                    types.InlineKeyboardButton(text="❌ No, cancelar", callback_data="confirmar_borrar:no"),
                ],
            ]
        )
        keyboard = agregar_boton_menu(keyboard)

        await callback.message.answer(
            "⚠️ <b>¿Estás seguro de que querés borrar TODOS tus datos?</b>\n\n"
            f"🏠 Fincas: {len(fincas)}\n"
            "Esta acción NO se puede deshacer.\n\n"
            "Tus datos incluyen: fincas, lotes, ingresos y costos.",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @router.callback_query(F.data.startswith("confirmar_borrar:"))
    async def confirmar_borrar(callback: types.CallbackQuery, state: FSMContext):
        """Primera confirmación → si es 'si', pide SEGUNDA confirmación más fuerte."""
        await callback.answer()
        await state.clear()
        decision = callback.data.split(":", 1)[1]
        user_id = callback.from_user.id

        if decision == "no":
            await callback.message.edit_text(
                "✅ <b>Operación cancelada.</b>\n\n"
                "Tus datos están a salvo. Usá /menu para continuar.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        # Segunda confirmación — más fuerte y clara
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="⚠️ Sí, estoy 100% seguro", callback_data="confirmar_borrar_2:si"),
                    types.InlineKeyboardButton(text="❌ No, cancelar", callback_data="confirmar_borrar_2:no"),
                ],
            ]
        )
        keyboard = agregar_boton_menu(keyboard)

        await callback.message.edit_text(
            "🚨 <b>⚠️ ¡ÚLTIMA ADVERTENCIA! ⚠️</b>\n\n"
            "<b>¿REALMENTE querés borrar TODOS tus datos?</b>\n\n"
            "🔴 <b>Esta acción NO se puede deshacer.</b>\n"
            "🔴 Se eliminarán TODAS tus fincas, lotes, ingresos y costos.\n"
            "🔴 No hay forma de recuperarlos.\n\n"
            "<i>Si estás completamente seguro, presioná el botón de abajo.</i>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @router.callback_query(F.data.startswith("confirmar_borrar_2:"))
    async def confirmar_borrar_2(callback: types.CallbackQuery, state: FSMContext):
        """Ejecuta el borrado SOLO si el usuario confirma por segunda vez."""
        await callback.answer()
        await state.clear()
        decision = callback.data.split(":", 1)[1]
        user_id = callback.from_user.id

        if decision == "no":
            await callback.message.edit_text(
                "✅ <b>Operación cancelada.</b>\n\n"
                "Tus datos están a salvo. Usá /menu para continuar.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        # Borrar todos los datos
        try:
            resultado = db.delete_all_user_data(user_id)
            await callback.message.edit_text(
                f"🗑️ <b>Datos borrados exitosamente.</b>\n\n"
                f"🏠 Fincas eliminadas: {resultado['fincas']}\n"
                f"🌱 Lotes eliminados: {resultado['lotes']}\n"
                f"💰 Transacciones eliminadas: {resultado['transacciones']}\n\n"
                "Podés empezar de nuevo con /fincas ☕",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
        except Exception as e:
            logger.error(f"Error al borrar datos: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ <b>Error al borrar los datos.</b>\n\n"
                "Intentá de nuevo o contactá al administrador.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

    @router.callback_query(F.data == "ir_admin")
    async def menu_admin(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.clear()
        user_id = callback.from_user.id
        if user_id in ADMIN_IDS:
            await callback.message.answer(
                "🔧 <b>Panel de Administración</b>\n\n"
                "• /usuarios — Ver todos los usuarios\n"
                "• /revocar — Revocar acceso a un usuario\n"
                "• /aprobar — Aprobar usuario pendiente\n\n"
                "Usá los comandos para gestionar.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
        else:
            await callback.message.answer(
                "❌ <b>Acceso denegado.</b>\n\nSolo administradores.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

    @router.callback_query(F.data == "volver_menu")
    async def volver_menu(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await state.clear()
        # Reutilizar cmd_menu creando un mensaje falso
        user_id = callback.from_user.id
        is_admin = user_id in ADMIN_IDS
        is_approved = db.is_approved(user_id)

        if not is_approved and not is_admin:
            await callback.message.answer(
                "⏳ <b>Esperando aprobación</b>\n\nUsa /start para verificar.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="🏠 Fincas", callback_data="menu_fincas"),
                    types.InlineKeyboardButton(text="🌱 Lotes", callback_data="menu_lotes"),
                ],
                [
                    types.InlineKeyboardButton(text="💰 Ingresos", callback_data="menu_ingresos"),
                    types.InlineKeyboardButton(text="📉 Costos", callback_data="menu_costos"),
                ],
                [
                    types.InlineKeyboardButton(text="📊 Resumen", callback_data="menu_resumen"),
                    types.InlineKeyboardButton(text="📋 Exportar Excel", callback_data="menu_excel"),
                ],
                [
                    types.InlineKeyboardButton(text="📥 Importar Excel", callback_data="menu_importar"),
                    types.InlineKeyboardButton(text="🗑️ Borrar datos", callback_data="ir_borrar"),
                ],
                [
                    types.InlineKeyboardButton(text="❓ Ayuda", callback_data="menu_ayuda"),
                ],
            ]
        )

        if is_admin:
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(text="🔧 Admin", callback_data="ir_admin"),
            ])

        await callback.message.answer(
            "☕ <b>Asistente de Costos</b>\n\n"
            "¿Qué querés hacer? Usá los botones:",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @router.callback_query(F.data == "cancelar_operacion")
    async def cancelar_operacion(callback: types.CallbackQuery, state: FSMContext):
        """Cancela cualquier operación actual y vuelve al menú."""
        await callback.answer()
        await state.clear()
        await callback.message.answer(
            "✅ <b>Operación cancelada.</b>\n\nUsá los botones para continuar:",
            parse_mode="HTML",
            reply_markup=boton_menu(),
        )

    return router
