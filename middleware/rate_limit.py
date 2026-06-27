"""
Rate-limiting / anti-flood middleware.
Limita a 10 mensajes/minuto y 1 mensaje/segundo por usuario (cooldown).
Solo stdlib (time, collections) — sin Redis ni paquetes externos.
"""
import logging
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

logger = logging.getLogger(__name__)

# Almacén en memoria: user_id -> [timestamps de mensajes]
_user_messages: Dict[int, List[float]] = defaultdict(list)

# Constantes
MAX_MSG_PER_MINUTE = 10
COOLDOWN_SECONDS = 1.0
WINDOW_SECONDS = 60.0


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware anti-flood.
    - Máximo 10 mensajes por minuto por usuario.
    - Máximo 1 mensaje por segundo (cooldown).
    Si excede cualquiera de los límites, responde 'Espera un momento...' y descarta el mensaje.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Solo aplicar rate-limiting a messages (no a callback_query)
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        now = time.time()
        timestamps = _user_messages[user_id]

        # 1. Podar timestamps más viejos que la ventana de 60 segundos
        cutoff = now - WINDOW_SECONDS
        _user_messages[user_id] = [ts for ts in timestamps if ts > cutoff]

        # 2. Verificar cooldown de 1 segundo
        if _user_messages[user_id]:
            last_ts = _user_messages[user_id][-1]
            if now - last_ts < COOLDOWN_SECONDS:
                logger.info(
                    "⛔ Rate-limit (cooldown) user=%s wait=%.2fs",
                    user_id,
                    now - last_ts,
                )
                await event.answer("Espera un momento...")
                return  # Descartar el mensaje

        # 3. Verificar límite de 10 mensajes por minuto
        if len(_user_messages[user_id]) >= MAX_MSG_PER_MINUTE:
            logger.info(
                "⛔ Rate-limit (10/min) user=%s count=%d",
                user_id,
                len(_user_messages[user_id]),
            )
            await event.answer("Espera un momento...")
            return  # Descartar el mensaje

        # 4. Registrar este mensaje y continuar
        _user_messages[user_id].append(now)
        return await handler(event, data)
