"""
Módulo de manejo de errores para handlers de aiogram.
Provee un decorador reutilizable @error_handler que:
  1. Envuelve la lógica del handler en try/except
  2. Envía alerta al admin con traceback completo
  3. Responde al usuario con mensaje amigable
  4. Loguea el error con exc_info=True

Uso:
    from .error_handler import error_handler

    @router.message(Command("ejemplo"))
    @error_handler
    async def mi_handler(message: types.Message):
        ...
"""
import functools
import logging
import traceback

from aiogram import types

logger = logging.getLogger(__name__)

# ── Configuración ──────────────────────────────────────────────
ADMIN_CHAT_ID = 810796748


def error_handler(func):
    """Decorador que envuelve un handler de aiogram con try/except.

    Se aplica justo encima de la definición de la función handler,
    debajo de los decoradores @router.message / @router.callback_query.

    Soporta handlers con estas firmas:
      - (event: Message)
      - (event: Message, state: FSMContext)
      - (event: CallbackQuery)
      - (event: CallbackQuery, state: FSMContext)
      - (event: Message | CallbackQuery)
      - (event: Message | CallbackQuery, state: FSMContext)
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Identificar el objeto evento (primer argumento posicional)
            event = args[0] if args else None

            chat_id = None
            send_func = None
            bot = None
            caller_type = "desconocido"

            if isinstance(event, types.Message):
                chat_id = event.chat.id
                send_func = event.answer
                bot = event.bot
                caller_type = "message"
            elif isinstance(event, types.CallbackQuery):
                chat_id = event.message.chat.id
                send_func = event.message.answer
                bot = event.bot
                caller_type = "callback"

            # 1. Loguear el error con traceback completo
            logger.error(
                f"❌ Error en handler '{func.__name__}' ({caller_type}): {e}",
                exc_info=True,
            )

            # 2. Enviar alerta al admin con traceback
            if bot and chat_id:
                tb_str = traceback.format_exc()
                try:
                    await bot.send_message(
                        ADMIN_CHAT_ID,
                        f"🚨 <b>Error en handler</b> <code>{func.__name__}</code>\n\n"
                        f"👤 <b>Usuario:</b> <code>{chat_id}</code>\n"
                        f"📱 <b>Tipo:</b> {caller_type}\n\n"
                        f"<b>Error:</b>\n<code>{str(e)[:500]}</code>\n\n"
                        f"<b>Traceback:</b>\n<pre>{tb_str[:2000]}</pre>",
                        parse_mode="HTML",
                    )
                except Exception as alert_err:
                    logger.error(
                        f"Error enviando alerta al admin: {alert_err}"
                    )

            # 3. Responder al usuario con mensaje amigable
            if send_func:
                try:
                    await send_func(
                        "❌ <b>Ocurrió un error inesperado.</b> 🙇\n\n"
                        "El administrador ya fue notificado. "
                        "Por favor, intentá de nuevo más tarde "
                        "o usá /ayuda para contactar con soporte.",
                        parse_mode="HTML",
                    )
                except Exception as reply_err:
                    logger.error(
                        f"Error al responder al usuario: {reply_err}"
                    )

    return wrapper
