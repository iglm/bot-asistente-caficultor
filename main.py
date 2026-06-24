#!/usr/bin/env python3
"""
Bot Asistente Financiero para Caficultores ☕💰
=================================================
Bot de Telegram para registrar ingresos y egresos de fincas cafeteras.
Genera un Excel profesional de costos de producción.

Stack: aiogram 3.x + SQLite + openpyxl

Uso:
    source venv/bin/activate && python main.py
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database import Database
from handlers import start, admin, fincas, lotes, ingresos, costos, reportes, ayuda

# ─── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


async def main():
    """Entry point del bot."""
    log.info("🚀 Iniciando Bot Asistente Caficultor...")
    
    # ── Inicializar base de datos ──
    db = Database()
    db.init_db()
    log.info("✅ Base de datos inicializada")
    
    # ── Inicializar bot ──
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # ── Registrar handlers ──
    dp.include_routers(
        start.router,
        admin.router,
        fincas.router,
        lotes.router,
        ingresos.router,
        costos.router,
        reportes.router,
        ayuda.router,
    )
    log.info("✅ Handlers registrados")
    
    # ── Obtener info del bot ──
    bot_info = await bot.get_me()
    log.info(f"🤖 Bot @{bot_info.username} iniciado (ID: {bot_info.id})")
    
    # ── Iniciar polling ──
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("🛑 Bot detenido por el usuario")
        sys.exit(0)
    except Exception as e:
        log.exception(f"💥 Error fatal: {e}")
        sys.exit(1)
