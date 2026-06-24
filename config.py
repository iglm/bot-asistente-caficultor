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

# ── Aviso Legal ──
AVISO_LEGAL = """
📋 <b>AVISO LEGAL Y PROTECCIÓN DE DATOS</b>

• Los datos que registres (fincas, lotes, costos, ingresos) serán almacenados en nuestra base de datos.
• Tus datos NO serán compartidos con terceros.
• Tus datos se sincronizan diariamente con un repositorio privado de GitHub para respaldo.
• Podés borrar TODOS tus datos en cualquier momento usando el botón "🗑️ Borrar datos".
• El uso de este bot es bajo tu propia responsabilidad.

👨‍💻 <b>Desarrollado por:</b>
Lucas Mateo Tabares Franco
Asesorado por: Ing. Jhoan Sebastian Bustamante Montes

Al usar este bot, aceptás los términos anteriores.
"""

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

# ── Unidades de insumo y factores de conversión ──
UNIDADES_INSUMO = ['g', 'kg', 'mg', 'ml', 'l', 'bulto']

UNIDADES_INSUMO_LABELS = {
    'g': 'Gramos (g)',
    'kg': 'Kilogramos (kg)',
    'mg': 'Miligramos (mg)',
    'ml': 'Mililitros (mL)',
    'l': 'Litros (L)',
    'bulto': 'Bulto 50kg',
}

# Factores de conversión a unidad estándar (kg para sólidos, L para líquidos)
CONVERSION_A_KG = {'g': 0.001, 'kg': 1, 'mg': 0.000001, 'ml': 0.001, 'l': 1, 'bulto': 50}
CONVERSION_A_LITROS = {'ml': 0.001, 'l': 1, 'cm3': 0.001, 'g': 0.001}

# Unidades que se consideran de sólidos (se convierten a kg)
UNIDADES_SOLIDOS = {'g', 'kg', 'mg', 'bulto'}
# Unidades que se consideran de líquidos (se convierten a L)
UNIDADES_LIQUIDOS = {'ml', 'l'}

def convertir_a_estandar(cantidad: float, unidad: str) -> tuple[float, str]:
    """Convierte una cantidad a unidad estándar (kg o L según el tipo).
    Retorna (cantidad_convertida, unidad_estandar).
    """
    if unidad in UNIDADES_SOLIDOS:
        factor = CONVERSION_A_KG.get(unidad, 1)
        return cantidad * factor, 'kg'
    elif unidad in UNIDADES_LIQUIDOS:
        factor = CONVERSION_A_LITROS.get(unidad, 1)
        return cantidad * factor, 'L'
    return cantidad, unidad

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

# ── Configuración de presupuesto ──
# Porcentajes de referencia para presupuesto (base 100%)
PRESUPUESTO_PORCENTAJES = {
    "recoleccion": 0.54,
    "fertilizacion": 0.19,
    "administrativo": 0.07,
    "arvenses": 0.06,
    "beneficio": 0.06,
    "instalacion": 0.05,
    "fitosanitario": 0.02,
    "otras_labores": 0.01,
}

# Rubros que aplican a toda la finca (no por lote)
RUBROS_GLOBALES = ["administrativo", "beneficio"]
