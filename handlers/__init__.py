"""
Handlers del Bot Asistente Caficultor.
Cada módulo exporta una función get_*_router(db) que retorna un Router de aiogram.
"""

from handlers.menu import get_menu_router
from handlers.start import get_start_router
from handlers.admin import get_admin_router
from handlers.fincas import get_fincas_router
from handlers.lotes import get_lotes_router
from handlers.ingresos import get_ingresos_router
from handlers.costos import get_costos_router
from handlers.reportes import get_reportes_router
from handlers.importar import get_importar_router
from handlers.ayuda import get_ayuda_router
from handlers.voice import get_voice_router
from handlers.presupuesto import get_presupuesto_router
from handlers.indicadores import get_indicadores_router
from handlers.asesoria import get_asesoria_router

__all__ = [
    "get_menu_router",
    "get_start_router",
    "get_admin_router",
    "get_fincas_router",
    "get_lotes_router",
    "get_ingresos_router",
    "get_costos_router",
    "get_reportes_router",
    "get_importar_router",
    "get_ayuda_router",
    "get_voice_router",
    "get_presupuesto_router",
    "get_indicadores_router",
    "get_asesoria_router",
]
