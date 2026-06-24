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

# ── Grupo de notificaciones (centro de mando) ──
NOTIFICATION_GROUP_ID = int(os.environ.get("NOTIFICATION_GROUP_ID", "-1003545220692"))

# ── Rutas ──
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = str(BASE_DIR / "data" / "finca.db")
EXCEL_TEMPLATE = str(BASE_DIR / "data" / "plantilla" / "Costos de produccion - 2026.xlsx")
EXPORTS_DIR = str(BASE_DIR / "exports")

# Crear directorios si no existan
os.makedirs(BASE_DIR / "data", exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# ── Categorías de transacciones ──
BOT_NAME = "Asistente Caficultor ☕"

CATEGORIAS_PADRE = {
    "instalacion": {"nombre": "🌱 Instalación", "mo": "instalacion_mo", "insumos": "instalacion_insumos"},
    "arvenses": {"nombre": "🌿 Arvenses", "mo": "arvenses_mo", "insumos": "arvenses_insumos"},
    "fertilizacion": {"nombre": "🧪 Fertilización", "mo": "fertilizacion_mo", "insumos": "fertilizacion_insumos"},
    "fitosanitario": {"nombre": "🛡️ Fitosanitario", "mo": "fitosanitario_mo", "insumos": "fitosanitario_insumos"},
    "sombrio": {"nombre": "🌳 Sombrío", "mo": "sombrio_mo", "insumos": "sombrio_insumos"},
    "otras_labores": {"nombre": "🔧 Otras Labores", "mo": "otras_labores_mo", "insumos": "otras_labores_insumos"},
    "recoleccion": {"nombre": "☕ Recolección", "mo": "recoleccion"},
    "beneficio": {"nombre": "🏭 Beneficio", "mo": "beneficio"},
    "administrativo": {"nombre": "📋 Administrativo", "mo": "administrativo"},
}

CATEGORIAS_SIMPLE = {
    "recoleccion": {"nombre": "☕ Recolección", "mo": "recoleccion"},
    "beneficio": {"nombre": "🏭 Beneficio", "mo": "beneficio"},
    "administrativo": {"nombre": "📋 Administrativo", "mo": "administrativo"},
}

TIPOS_CAFE_LIST = [
    "CPS (Café Pergamino Seco)",
    "Pasilla",
]

TIPOS_CAFE = {
    "CPS (Café Pergamino Seco)": "CPS",
    "Pasilla": "Pasilla",
}

CATEGORIAS = {
    "ingreso_cps": {"nombre": "Ingreso CPS", "hoja": "Ingresos", "tipo": "ingreso"},
    "ingreso_pasilla": {"nombre": "Ingreso Pasilla", "hoja": "Ingresos", "tipo": "ingreso"},
    "instalacion_mo": {"nombre": "Instalación MO", "hoja": "Instalacion de Cafe", "seccion": "MO"},
    "instalacion_insumos": {"nombre": "Instalación Insumos", "hoja": "Instalacion de Cafe", "seccion": "Insumos"},
    "instalacion": {"nombre": "Instalación", "hoja": "Instalacion de Cafe", "seccion": "Total"},
    "arvenses_mo": {"nombre": "Arvenses MO", "hoja": "Control de arvenses", "seccion": "MO"},
    "arvenses_insumos": {"nombre": "Arvenses Insumos", "hoja": "Control de arvenses", "seccion": "Insumos"},
    "arvenses": {"nombre": "Arvenses", "hoja": "Control de arvenses", "seccion": "Total"},
    "fertilizacion_mo": {"nombre": "Fertilización MO", "hoja": "Fertilizacion", "seccion": "MO"},
    "fertilizacion_insumos": {"nombre": "Fertilización Insumos", "hoja": "Fertilizacion", "seccion": "Insumos"},
    "fertilizacion": {"nombre": "Fertilización", "hoja": "Fertilizacion", "seccion": "Total"},
    "fitosanitario_mo": {"nombre": "Fitosanitario MO", "hoja": "Control Fitosanitario", "seccion": "MO"},
    "fitosanitario_insumos": {"nombre": "Fitosanitario Insumos", "hoja": "Control Fitosanitario", "seccion": "Insumos"},
    "fitosanitario": {"nombre": "Fitosanitario", "hoja": "Control Fitosanitario", "seccion": "Total"},
    "sombrio_mo": {"nombre": "Sombrío MO", "hoja": "Regulacion de sombrio", "seccion": "MO"},
    "sombrio_insumos": {"nombre": "Sombrío Insumos", "hoja": "Regulacion de sombrio", "seccion": "Insumos"},
    "sombrio": {"nombre": "Sombrío", "hoja": "Regulacion de sombrio", "seccion": "Total"},
    "otras_labores_mo": {"nombre": "Otras Labores MO", "hoja": "Otras Labores", "seccion": "MO"},
    "otras_labores_insumos": {"nombre": "Otras Labores Insumos", "hoja": "Otras Labores", "seccion": "Insumos"},
    "otras_labores": {"nombre": "Otras Labores", "hoja": "Otras Labores", "seccion": "Total"},
    "recoleccion": {"nombre": "Recolección", "hoja": "Recoleccion", "seccion": "unico"},
    "beneficio": {"nombre": "Beneficio", "hoja": "Beneficio", "seccion": "unico"},
    "administrativo": {"nombre": "Gastos Admin", "hoja": "Gastos Administrativos", "seccion": "unico"},
}
