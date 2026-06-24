"""Funciones reutilizables para botones de navegación.

Provee helpers para que TODOS los mensajes del bot tengan visible
el botón "🏠 Menú Principal" y/o "❌ Cancelar".
El usuario NUNCA debe quedarse sin opción de escape visible.
"""

from datetime import datetime, timedelta

from aiogram import types
from database import Database


def fecha_hoy() -> str:
    """Retorna la fecha de hoy en formato DD/MM/AAAA."""
    return datetime.now().strftime("%d/%m/%Y")


def fecha_ayer() -> str:
    """Retorna la fecha de ayer en formato DD/MM/AAAA."""
    return (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")


def botones_fecha() -> types.InlineKeyboardMarkup:
    """Retorna teclado con opciones rápidas de fecha."""
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📅 Hoy", callback_data="fecha:hoy"),
            types.InlineKeyboardButton(text="📆 Ayer", callback_data="fecha:ayer"),
        ],
        [types.InlineKeyboardButton(text="✏️ Otra fecha", callback_data="fecha:custom")],
    ])
    return agregar_menu_cancelar(kb)


def boton_menu():
    """Retorna teclado con solo botón Menú Principal."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🏠 Menú Principal", callback_data="volver_menu")],
    ])


def boton_cancelar():
    """Retorna teclado con solo botón Cancelar."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion")],
    ])


def botones_menu_cancelar():
    """Retorna teclado con Cancelar + Menú Principal."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion")],
        [types.InlineKeyboardButton(text="🏠 Menú Principal", callback_data="volver_menu")],
    ])


def agregar_boton_menu(keyboard):
    """Agrega botón '🏠 Menú Principal' al final de un teclado existente."""
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="🏠 Menú Principal", callback_data="volver_menu"),
    ])
    return keyboard


def agregar_boton_cancelar(keyboard):
    """Agrega botón '❌ Cancelar' al final de un teclado existente."""
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion"),
    ])
    return keyboard


def agregar_menu_cancelar(keyboard):
    """Agrega ambos botones (Cancelar + Menú) al final de un teclado existente."""
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion"),
    ])
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="🏠 Menú Principal", callback_data="volver_menu"),
    ])
    return keyboard


def construir_menu_principal(db=None, user_id=None, is_admin=False):
    """Retorna teclado del menú principal.

    Args:
        db: Instancia de Database (opcional, para verificar estado del usuario)
        user_id: ID del usuario (obligatorio si se pasa db)
        is_admin: Si el usuario es administrador (opcional, tiene prioridad)
    """
    if db is not None and user_id is not None:
        is_admin = is_admin or (user_id in __import__("config").ADMIN_IDS)

    kb = types.InlineKeyboardMarkup(
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
                types.InlineKeyboardButton(text="📈 Indicadores", callback_data="menu_indicadores"),
            ],
            [
                types.InlineKeyboardButton(text="📋 Exportar Excel", callback_data="menu_excel"),
                types.InlineKeyboardButton(text="📄 Exportar PDF", callback_data="menu_pdf"),
            ],
            [
                types.InlineKeyboardButton(text="📊 Dashboard", callback_data="menu_dashboard"),
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
        kb.inline_keyboard.append([
            types.InlineKeyboardButton(text="🔧 Admin", callback_data="ir_admin"),
        ])

    return kb
