"""
Middleware de cancelación — Intercepta /menu, /cancelar y / en CUALQUIER estado FSM.
Limpia el estado y deja que el mensaje original continúe hacia el handler de menú.
"""
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

logger = logging.getLogger(__name__)


class CancelMiddleware(BaseMiddleware):
    """Middleware que intercepta /menu, /cancelar, / y limpia el estado FSM.
    Se ejecuta ANTES de que el dispatcher resuelva qué handler llamar,
    garantizando que el menú tenga prioridad absoluta sobre cualquier FSM.
    """

    COMMANDS = {"/menu", "/cancelar", "/start", "/ayuda", "/", "/excel", "/fincas", "/lotes", "/ingreso", "/costo", "/resumen", "/usuarios", "/presupuesto", "/indicadores", "/importar"}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            text = event.text or ""
            # Normalizar: quitar @botname si existe
            if text.startswith("/"):
                parts = text.split(" ", 1)
                cmd = parts[0].split("@")[0].lower()
                if cmd in self.COMMANDS:
                    state: FSMContext = data.get("state")
                    if state:
                        current = await state.get_state()
                        if current:
                            logger.info(f"🔄 [Middleware] Cancelando estado {current} por {cmd}")
                            await state.clear()

        # Limpiar estado para callbacks de menú (botones inline)
        if isinstance(event, CallbackQuery):
            callback_data = event.data or ""
            if callback_data.startswith("menu_") or callback_data.startswith("ir_"):
                state: FSMContext = data.get("state")
                if state:
                    current = await state.get_state()
                    if current:
                        logger.info(f"🔄 [Middleware] Cancelando estado {current} por callback {callback_data}")
                        await state.clear()

        return await handler(event, data)
