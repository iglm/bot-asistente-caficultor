"""
config.py — Configuración central del bot
"""

import os
from pathlib import Path

# ── Token de Telegram ──
_token_file = Path.home() / "scripts" / ".bot_token_caficultor.txt"
BOT_TOKEN = _token_file.read_text().strip() if _token_file.exists() else os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("⚠️ Token no encontrado. Creá scripts/.bot_token_caficultor.txt o seteá BOT_TOKEN")
    import sys
    sys.exit(1)

# ── Admin IDs (pueden haber varios separados por coma) ──
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "810796748").split(",")]

# ── Rutas ──
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = str(BASE_DIR / "data" / "finca.db")
EXCEL_TEMPLATE = str(BASE_DIR / "data" / "plantilla" / "Costos de produccion - 2026.xlsx")
EXPORTS_DIR = str(BASE_DIR / "exports")

# Crear directorios si no existan
os.makedirs(BASE_DIR / "data", exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# ── Categorías de transacciones ──
CATEGORIAS = {
    "ingreso_cps": {"nombre": "Ingreso CPS", "hoja": "Ingresos", "tipo": "ingreso"},
    "ingreso_pasilla": {"nombre": "Ingreso Pasilla", "hoja": "Ingresos", "tipo": "ingreso"},
    "ingreso_rere": {"nombre": "Ingreso Re-re", "hoja": "Ingresos", "tipo": "ingreso"},
    "instalacion_mo": {"nombre": "Instalación MO", "hoja": "Instalacion de Cafe", "seccion": "MO"},
    "instalacion_insumos": {"nombre": "Instalación Insumos", "hoja": "Instalacion de Cafe", "seccion": "Insumos"},
    "arvenses_mo": {"nombre": "Arvenses MO", "hoja": "Control de arvenses", "seccion": "MO"},
    "arvenses_insumos": {"nombre": "Arvenses Insumos", "hoja": "Control de arvenses", "seccion": "Insumos"},
    "fertilizacion_mo": {"nombre": "Fertilización MO", "hoja": "Fertilizacion", "seccion": "MO"},
    "fertilizacion_insumos": {"nombre": "Fertilización Insumos", "hoja": "Fertilizacion", "seccion": "Insumos"},
    "fitosanitario_mo": {"nombre": "Fitosanitario MO", "hoja": "Control Fitosanitario", "seccion": "MO"},
    "fitosanitario_insumos": {"nombre": "Fitosanitario Insumos", "hoja": "Control Fitosanitario", "seccion": "Insumos"},
    "sombrio_mo": {"nombre": "Sombrío MO", "hoja": "Regulacion de sombrio", "seccion": "MO"},
    "sombrio_insumos": {"nombre": "Sombrío Insumos", "hoja": "Regulacion de sombrio", "seccion": "Insumos"},
    "otras_labores_mo": {"nombre": "Otras Labores MO", "hoja": "Otras Labores", "seccion": "MO"},
    "otras_labores_insumos": {"nombre": "Otras Labores Insumos", "hoja": "Otras Labores", "seccion": "Insumos"},
    "recoleccion": {"nombre": "Recolección", "hoja": "Recoleccion", "seccion": "unico"},
    "beneficio": {"nombre": "Beneficio", "hoja": "Beneficio", "seccion": "unico"},
    "administrativo": {"nombre": "Gastos Admin", "hoja": "Gastos Administrativos", "seccion": "unico"},
}
