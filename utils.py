"""Funciones reutilizables para botones de navegación.

Provee helpers para que TODOS los mensajes del bot tengan visible
el botón "🏠 Menú Principal" y/o "❌ Cancelar".
El usuario NUNCA debe quedarse sin opción de escape visible.
"""

from aiogram import types


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
