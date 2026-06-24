#!/usr/bin/env python3
"""
Simulador Completo de Caficultor ☕
====================================
Genera datos realistas de una finca cafetera con 20 lotes y 300+ transacciones
en 3 años (2023-2025) usando TODAS las categorías del sistema.

Uso:
    # Simulación completa
    python3 tests/simulador_caficultor.py

    # Fases individuales
    python3 tests/simulador_caficultor.py --fase limpiar
    python3 tests/simulador_caficultor.py --fase admin
    python3 tests/simulador_caficultor.py --fase finca
    python3 tests/simulador_caficultor.py --fase lotes
    python3 tests/simulador_caficultor.py --fase ingresos
    python3 tests/simulador_caficultor.py --fase costos
    python3 tests/simulador_caficultor.py --fase resumen
    python3 tests/simulador_caficultor.py --fase todo

    # Solo imprimir resumen sin modificar DB
    python3 tests/simulador_caficultor.py --fase verificar

    # Verbose
    python3 tests/simulador_caficultor.py -v
"""

import argparse
import logging
import math
import os
import random
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Rutas ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.resolve()
DB_PATH = BASE_DIR / "data" / "finca.db"
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "simulador_caficultor.log"

# Nos aseguramos que los directorios existan
LOGS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

# ── Configuración del usuario ───────────────────────────────────────────
ADMIN_ID = 810796748
ADMIN_USERNAME = "Mateo"
FINCA_NOMBRE = "Finca La Esperanza"
FINCA_REGION = "Manizales"
FINCA_DEPARTAMENTO = "Caldas"

# ── Precios reales investigados ─────────────────────────────────────────
# Café pergamino seco por año (precios promedio mensuales)
PRECIOS_CAFE = {
    2023: [12010, 11800, 11500, 11200, 10800, 10500, 10200, 10500, 11000, 12500, 13500, 14000],
    2024: [15000, 16000, 17000, 17700, 18000, 18500, 19000, 19500, 20000, 21000, 22000, 23000],
    2025: [25000, 27000, 28000, 29000, 28500, 27000, 26000, 25500, 25000, 24500, 24000, 23500],
}

# Precio pasilla = 40% del CPS, Re-re = 20% del CPS
PRECIO_PASILLA_FACTOR = 0.40
PRECIO_RERE_FACTOR = 0.20

# Precios unitarios de insumos y mano de obra
JORNAL = 55_000          # $/día
FERTILIZANTE_NPK = 3_200  # $/kg
HERBICIDA_GLIFOSATO = 18_000  # $/L
FUNGICIDA_CUPRICO = 22_000    # $/kg
INSECTICIDA_CIPERMETRINA = 25_000  # $/L
COMPOST_ORGANICO = 2_800   # $/kg
CAL_AGRICOLA = 1_500       # $/kg

# Datos de costos de insumos y sus variaciones
INSUMOS_DATA = {
    "fertilizacion": [
        ("NPK 15-15-15", FERTILIZANTE_NPK, "kg"),
        ("Urea", 2_800, "kg"),
        ("Cloruro de Potasio", 3_500, "kg"),
        ("DAP", 4_200, "kg"),
        ("Cal dolomita", CAL_AGRICOLA, "kg"),
        ("Boro", 8_000, "kg"),
        ("Zinc", 7_500, "kg"),
        ("Compost orgánico", COMPOST_ORGANICO, "kg"),
    ],
    "arvenses": [
        ("Glifosato", HERBICIDA_GLIFOSATO, "L"),
        ("Paraquat", 22_000, "L"),
        ("Herbicida selectivo", 35_000, "L"),
    ],
    "fitosanitario": [
        ("Fungicida cúprico", FUNGICIDA_CUPRICO, "kg"),
        ("Insecticida cipermetrina", INSECTICIDA_CIPERMETRINA, "L"),
        ("Mancozeb", 18_000, "kg"),
        ("Aceite agrícola", 12_000, "L"),
        ("Benomyl", 45_000, "kg"),
        ("Clorotalonil", 28_000, "kg"),
    ],
    "instalacion": [
        ("Plántulas de café", 1_200, "unidad"),
        ("Cal agrícola", CAL_AGRICOLA, "kg"),
        ("Compost orgánico", COMPOST_ORGANICO, "kg"),
        ("Yeso agrícola", 2_000, "kg"),
    ],
    "sombrio": [
        ("Machetes", 15_000, "unidad"),
        ("Tijeras podadoras", 45_000, "unidad"),
        ("Motoguadaña (combustible)", 12_000, "L"),
    ],
    "otras_labores": [
        ("Tijeras de podar", 35_000, "unidad"),
        ("Serrucho", 25_000, "unidad"),
        ("Pintura", 18_000, "L"),
        ("Cal", CAL_AGRICOLA, "kg"),
    ],
}

# Precios de pasilla y rere por año (factor del precio CPS)
PASILLA_PRECIO_FACTOR = 0.40
RERE_PRECIO_FACTOR = 0.20

# ── Rendimiento por edad del lote (kg/ha) ──────────────────────────────
# Basado en datos técnicos para la zona cafetera colombiana
RENDIMIENTO_POR_EDAD = [
    (0, 1, 0),       # 0-1 años: recién sembrado, no produce
    (1, 2, 500),     # 1-2 años: primer año de formación
    (2, 3, 1000),    # 2-3 años: inicio de producción
    (3, 5, 1500),    # 3-5 años: producción creciente
    (5, 7, 1668),    # 5-7 años: máxima producción
    (7, 10, 1500),   # 7-10 años: producción estable alta
    (10, 15, 1300),  # 10-15 años: declive gradual
    (15, 999, 1000), # 15+ años: producción baja
]


def obtener_rendimiento(edad: int) -> int:
    """Retorna kg/ha según la edad del lote."""
    for min_edad, max_edad, rend in RENDIMIENTO_POR_EDAD:
        if min_edad <= edad < max_edad:
            return rend
    return 1000


# ── Definición de los 20 lotes ─────────────────────────────────────────
# Distribución: 4 nuevos (0-1), 4 formación (1-3), 6 producción (3-7),
#               4 maduros (7-15), 2 viejos (15+)
# Variedades: Castillo, Caturra, Colombia
LOTES_DATA = [
    # Nuevos (0-1 años) — 4 lotes
    ("Lote El Renuevo", 1.0, 3800, "Castillo", 0),
    ("Lote La Promesa", 0.8, 3000, "Colombia", 0),
    ("Lote El Brote", 0.9, 3400, "Caturra", 1),
    ("Lote La Semilla", 0.7, 2600, "Castillo", 1),
    # Formación (1-3 años) — 4 lotes
    ("Lote El Crecimiento", 1.1, 4100, "Colombia", 2),
    ("Lote La Formación", 0.9, 3400, "Caturra", 2),
    ("Lote El Aprendiz", 1.2, 4500, "Castillo", 3),
    ("Lote La Esperanza II", 1.0, 3700, "Colombia", 3),
    # Producción (3-7 años) — 6 lotes
    ("Lote La Cosecha", 1.3, 4800, "Castillo", 4),
    ("Lote El Fruto", 1.1, 4000, "Caturra", 5),
    ("Lote La Bonanza", 1.4, 5100, "Castillo", 5),
    ("Lote El Rendidor", 1.2, 4400, "Colombia", 6),
    ("Lote La Abundancia", 1.0, 3800, "Caturra", 6),
    ("Lote El Productor", 1.5, 5500, "Castillo", 7),
    # Maduros (7-15 años) — 4 lotes
    ("Lote La Tradición", 1.3, 4800, "Colombia", 8),
    ("Lote El Maduro", 1.1, 4000, "Castillo", 10),
    ("Lote La Experiencia", 1.2, 4400, "Caturra", 12),
    ("Lote El Consolidado", 1.0, 3700, "Colombia", 14),
    # Viejos (15+ años) — 2 lotes
    ("Lote El Abuelo", 0.9, 3400, "Castillo", 17),
    ("Lote La Historia", 0.8, 3000, "Caturra", 16),
]

# Año base para calcular fecha_siembra
ANO_BASE = 2025

# ── Calendario de labores (Caldas) ─────────────────────────────────────
# (mes, categoría, es_mo, nombre_labor, frecuencia_opcional)
LABORES_CALENDARIO = [
    # Arvenses MO: Mar, Jun, Sep, Nov
    (3, "arvenses", True, "Control manual de arvenses"),
    (6, "arvenses", True, "Control manual de arvenses"),
    (9, "arvenses", True, "Control manual de arvenses"),
    (11, "arvenses", True, "Control manual de arvenses"),
    # Arvenses químico: Mar, Sep (2x insumos)
    (3, "arvenses", False, "Aplicación herbicida"),
    (9, "arvenses", False, "Aplicación herbicida"),
    # Fertilización MO: Mar, Jul, Oct
    (3, "fertilizacion", True, "Aplicación de fertilizante edáfico"),
    (7, "fertilizacion", True, "Aplicación de fertilizante edáfico"),
    (10, "fertilizacion", True, "Aplicación de fertilizante edáfico"),
    # Fertilización Insumos: Mar, Jul, Oct
    (3, "fertilizacion", False, "Fertilizante NPK 15-15-15"),
    (7, "fertilizacion", False, "Fertilizante NPK 15-15-15"),
    (10, "fertilizacion", False, "Fertilizante NPK 15-15-15"),
    # Fitosanitario MO: Abr-Sep (cada mes)
    (4, "fitosanitario", True, "Monitoreo y aplicación fitosanitaria"),
    (5, "fitosanitario", True, "Monitoreo y aplicación fitosanitaria"),
    (6, "fitosanitario", True, "Monitoreo y aplicación fitosanitaria"),
    (7, "fitosanitario", True, "Monitoreo y aplicación fitosanitaria"),
    (8, "fitosanitario", True, "Monitoreo y aplicación fitosanitaria"),
    (9, "fitosanitario", True, "Monitoreo y aplicación fitosanitaria"),
    # Fitosanitario Insumos: Abr, Jun, Ago, Sep
    (4, "fitosanitario", False, "Fungicida preventivo cúprico"),
    (6, "fitosanitario", False, "Insecticida cipermetrina"),
    (8, "fitosanitario", False, "Fungicida + Insecticida"),
    (9, "fitosanitario", False, "Fungicida preventivo"),
    # Poda: Ene-Feb (MO)
    (1, "otras_labores", True, "Poda de formación"),
    (2, "otras_labores", True, "Poda de mantenimiento"),
    # Deshije: May, Ago, Oct (MO)
    (5, "otras_labores", True, "Deshije selectivo"),
    (8, "otras_labores", True, "Deshije selectivo"),
    (10, "otras_labores", True, "Deshije selectivo"),
    # Limpieza general: Dic (MO)
    (12, "otras_labores", True, "Limpieza general de la finca"),
    # Otras labores Insumos: Ene, Abr, Oct, Dic
    (1, "otras_labores", False, "Herramientas de poda"),
    (4, "otras_labores", False, "Cal agrícola para encalado"),
    (10, "otras_labores", False, "Insumos de limpieza"),
    (12, "otras_labores", False, "Insumos de mantenimiento"),
    # Resiembra: Mar-Abr (MO + Insumos)
    (3, "instalacion", True, "Resiembra de plántulas"),
    (4, "instalacion", True, "Resiembra de plántulas"),
    (3, "instalacion", False, "Plántulas para resiembra"),
    (4, "instalacion", False, "Abono orgánico para resiembra"),
    # Instalación nueva: Ene-Feb (MO + Insumos en lotes nuevos)
    (1, "instalacion", True, "Preparación de terreno para nueva siembra"),
    (2, "instalacion", True, "Trazo y ahoyado"),
    (1, "instalacion", False, "Plántulas de café"),
    (2, "instalacion", False, "Fertilizante para nueva siembra"),
    # Sombrío MO: Jun
    (6, "sombrio", True, "Regulación de sombrío (raleo)"),
    # Sombrío Insumos: Jun
    (6, "sombrio", False, "Herramientas para sombrío"),
    # ── RECOLECCIÓN (Cosecha Principal + Mitaca) ──
    # Cosecha Principal: Oct, Nov, Dic (MO)
    (10, "recoleccion", True, "Recolección cosecha principal"),
    (11, "recoleccion", True, "Recolección cosecha principal"),
    (12, "recoleccion", True, "Recolección cosecha principal"),
    # Mitaca: Abr, May (MO)
    (4, "recoleccion", True, "Recolección mitaca"),
    (5, "recoleccion", True, "Recolección mitaca"),
    # ── BENEFICIO (después de cosecha) ──
    # Café despachado a beneficio: Oct, Nov, Dic
    (10, "beneficio", True, "Beneficio húmedo del café"),
    (11, "beneficio", True, "Beneficio húmedo del café"),
    (12, "beneficio", True, "Beneficio húmedo del café"),
    # Mitaca: May
    (5, "beneficio", True, "Beneficio de café mitaca"),
    # ── ADMINISTRATIVO (todos los meses) ──
    (1, "administrativo", True, "Gastos administrativos"),
    (2, "administrativo", True, "Gastos administrativos"),
    (3, "administrativo", True, "Gastos administrativos"),
    (4, "administrativo", True, "Gastos administrativos"),
    (5, "administrativo", True, "Gastos administrativos"),
    (6, "administrativo", True, "Gastos administrativos"),
    (7, "administrativo", True, "Gastos administrativos"),
    (8, "administrativo", True, "Gastos administrativos"),
    (9, "administrativo", True, "Gastos administrativos"),
    (10, "administrativo", True, "Gastos administrativos"),
    (11, "administrativo", True, "Gastos administrativos"),
    (12, "administrativo", True, "Gastos administrativos"),
]

# ── Costos unitarios por jornal y categoría ────────────────────────────
# Jornales requeridos por hectárea para cada labor
JORNALES_POR_LABOR = {
    "arvenses": 4,          # 4 jornales/ha para control manual
    "fertilizacion": 3,     # 3 jornales/ha para fertilización
    "fitosanitario": 2,     # 2 jornales/ha para aplicación
    "instalacion": 8,       # 8 jornales/ha para instalación
    "sombrio": 3,           # 3 jornales/ha para sombrío
    "otras_labores": 3,     # 3 jornales/ha para otras labores
}

# Cantidad de insumos por hectárea
INSUMOS_POR_HA = {
    "fertilizacion": 300,   # 300 kg/ha de fertilizante NPK
    "arvenses": 4,          # 4 L/ha de herbicida
    "fitosanitario": 3,     # 3 kg (o L)/ha de fungicida/insecticida
    "instalacion": 5000,    # 5000 plántulas/ha
    "sombrio": 2,           # 2 unidades/ha
    "otras_labores": 3,     # 3 unidades/ha
}

# Costos administrativos mensuales (promedio en zona cafetera)
COSTO_ADMINISTRATIVO_MENSUAL = 350_000

# ── Estructura objetivo de costos (sector cafetero colombiano) ──────────
# Basado en datos FNC Colombia, Cenicafé, SICA
# Costo total objetivo por hectárea: ~$16M en 3 años → ~$5.33M/ha/año
# Para una finca de 21.4 ha → ~$114M/año total
# Distribución porcentual real del sector:
COSTO_TOTAL_ANUAL_FINCA = 114_100_000  # ~$16M/ha en 3 años para 21.4 ha
COSTOS_TARGET_FINCA = {
    "recoleccion":     0.54,   # 54% — Recolección de café
    "fertilizacion":   0.19,   # 19% — Fertilización edáfica y foliar
    "administrativo":  0.07,   #  7% — Gastos administrativos
    "arvenses":        0.06,   #  6% — Control de arvenses (manual+químico)
    "beneficio":       0.06,   #  6% — Beneficio húmedo del café
    "instalacion":     0.05,   #  5% — Renovación de cafetales
    "fitosanitario":   0.02,   #  2% — Manejo fitosanitario
    "otras_labores":   0.01,   #  1% — Otras labores (poda, deshije, sombrío)
}
# Nota: sombrío está incluido dentro de otras_labores para ajustar al 1%

# ── Logger ──────────────────────────────────────────────────────────────
logger = logging.getLogger("simulador_caficultor")
logger.setLevel(logging.DEBUG)

# Handler para archivo
_fh = logging.FileHandler(str(LOG_FILE), mode="w", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s|%(message)s", datefmt="%H:%M:%S"))
logger.addHandler(_fh)

# Handler para consola
_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_ch)


# ── Helpers de DB ───────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    """Obtener conexión SQLite."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def db_exec(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """Ejecutar INSERT/UPDATE/DELETE."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur
    finally:
        conn.close()


def db_query(sql: str, params: tuple = ()) -> list:
    """Ejecutar SELECT."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def db_count(table: str = "transacciones", condition: str = "") -> int:
    """Contar registros en una tabla."""
    if condition and not condition.startswith("WHERE") and not condition.startswith("FROM"):
        condition = f"WHERE {condition}"
    sql = f"SELECT COUNT(*) as cnt FROM {table} {condition}"
    rows = db_query(sql)
    return rows[0]["cnt"] if rows else 0


def db_count_where(condition: str = "") -> int:
    """Contar transacciones con condición WHERE."""
    if condition and not condition.startswith("WHERE"):
        condition = f"WHERE {condition}"
    return db_count("transacciones", condition)


def db_sum(column: str = "valor_total", condition: str = "") -> float:
    """Sumar valores."""
    sql = f"SELECT COALESCE(SUM({column}), 0) as total FROM transacciones {condition}"
    rows = db_query(sql)
    return rows[0]["total"] if rows else 0


def format_pesos(valor: float) -> str:
    """Formatear como pesos colombianos."""
    if abs(valor) >= 1_000_000:
        return f"${valor:,.0f}"
    return f"${valor:,.0f}"


# ── Logging helpers con emojis ──────────────────────────────────────────

def log_info(msg: str):
    logger.info(f"ℹ️ {msg}")


def log_ok(msg: str):
    logger.info(f"✅ {msg}")


def log_warn(msg: str):
    logger.warning(f"⚠️ {msg}")


def log_error(msg: str):
    logger.error(f"❌ {msg}")


def log_step(msg: str):
    logger.info(f"🔷 {msg}")


def log_data(msg: str):
    logger.info(f"📊 {msg}")


def log_money(msg: str):
    logger.info(f"💰 {msg}")


def log_time(msg: str):
    logger.info(f"⏱️ {msg}")


def log_separator():
    logger.info("=" * 70)


# ── Clase Simulador ─────────────────────────────────────────────────────

class SimuladorCaficultor:
    """Simulador completo de datos de finca cafetera."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.finca_id = None
        self.lote_ids = []  # lista de IDs de lotes creados
        self.estadisticas = {
            "ingresos_creados": 0,
            "costos_creados": 0,
            "total_transacciones": 0,
            "errores": 0,
            "advertencias": 0,
        }
        if verbose:
            _ch.setLevel(logging.DEBUG)

    # ── Fase 0: Limpiar DB ──────────────────────────────────────────────

    def limpiar_admin(self):
        """Limpia SOLO datos del admin (user_id) — no borra toda la DB."""
        log_step("Limpiando datos anteriores del admin...")
        try:
            # Eliminar transacciones de las fincas del admin
            db_exec(
                "DELETE FROM transacciones WHERE finca_id IN "
                "(SELECT id FROM fincas WHERE user_id = ?)",
                (ADMIN_ID,)
            )
            # Eliminar lotes de las fincas del admin
            db_exec(
                "DELETE FROM lotes WHERE finca_id IN "
                "(SELECT id FROM fincas WHERE user_id = ?)",
                (ADMIN_ID,)
            )
            # Eliminar fincas del admin
            db_exec("DELETE FROM fincas WHERE user_id = ?", (ADMIN_ID,))
            # No eliminamos al usuario admin — solo reiniciamos su status
            db_exec(
                "UPDATE usuarios SET status='pending' WHERE user_id=?",
                (ADMIN_ID,)
            )

            deleted_tx = db_count_where(f"finca_id IN (SELECT id FROM fincas WHERE user_id={ADMIN_ID})")
            log_ok(f"Datos del admin limpiados (transacciones restantes: {deleted_tx})")
        except Exception as e:
            self.estadisticas["errores"] += 1
            log_error(f"Error limpiando admin: {e}")

    def limpiar_todo(self):
        """Limpia la DB por completo."""
        log_step("Limpiando toda la base de datos...")
        try:
            db_exec("DELETE FROM transacciones")
            db_exec("DELETE FROM lotes")
            db_exec("DELETE FROM fincas")
            db_exec("DELETE FROM usuarios")
            db_exec("DELETE FROM sqlite_sequence")
            log_ok("Base de datos limpiada completamente")
        except Exception as e:
            self.estadisticas["errores"] += 1
            log_error(f"Error limpiando DB: {e}")

    # ── Fase 1: Registrar admin ─────────────────────────────────────────

    def setup_admin(self):
        """Registra al admin como usuario aprobado."""
        log_step("Registrando administrador en DB...")
        try:
            db_exec(
                "INSERT OR IGNORE INTO usuarios (user_id, username, status, admin_id, approved_at) "
                "VALUES (?, ?, 'approved', ?, CURRENT_TIMESTAMP)",
                (ADMIN_ID, ADMIN_USERNAME, ADMIN_ID)
            )
            # Asegurar que quede approved
            db_exec(
                "UPDATE usuarios SET status='approved', admin_id=? WHERE user_id=?",
                (ADMIN_ID, ADMIN_ID)
            )
            users = db_query(
                "SELECT user_id, username, status FROM usuarios WHERE user_id=?",
                (ADMIN_ID,)
            )
            if users:
                u = users[0]
                log_ok(f"Admin registrado: ID={u['user_id']}, status={u['status']}")
            else:
                self.estadisticas["errores"] += 1
                log_error("No se pudo registrar admin")
        except Exception as e:
            self.estadisticas["errores"] += 1
            log_error(f"Error setup_admin: {e}")

    # ── Fase 2: Crear finca ─────────────────────────────────────────────

    def crear_finca(self):
        """Crea la finca 'Finca La Esperanza' en Manizales, Caldas."""
        log_step(f"Creando finca '{FINCA_NOMBRE}'...")
        try:
            db_exec(
                "INSERT INTO fincas (user_id, nombre, region, departamento) VALUES (?, ?, ?, ?)",
                (ADMIN_ID, FINCA_NOMBRE, FINCA_REGION, FINCA_DEPARTAMENTO)
            )
            fincas = db_query(
                "SELECT id, nombre FROM fincas WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (ADMIN_ID,)
            )
            if fincas:
                self.finca_id = fincas[0]["id"]
                log_ok(f"Finca creada: ID={self.finca_id}, '{fincas[0]['nombre']}'")
                log_data(f"   Ubicación: {FINCA_REGION}, {FINCA_DEPARTAMENTO}")
            else:
                self.estadisticas["errores"] += 1
                log_error("No se pudo crear la finca")
        except Exception as e:
            self.estadisticas["errores"] += 1
            log_error(f"Error crear_finca: {e}")

    # ── Fase 3: Crear 20 lotes ─────────────────────────────────────────

    def crear_lotes(self):
        """Crea 20 lotes con edades entre 0 y 17 años."""
        log_step("Creando 20 lotes con diferentes edades y variedades...")
        if not self.finca_id:
            log_error("No hay finca_id — abortando creación de lotes")
            return

        self.lote_ids = []
        for i, (nombre, area, arboles, variedad, edad) in enumerate(LOTES_DATA):
            año_siembra = ANO_BASE - edad
            fecha_siembra = f"{año_siembra}-03-15"
            try:
                cur = db_exec(
                    "INSERT INTO lotes (finca_id, nombre, area_hectareas, num_arboles, variedad, fecha_siembra) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (self.finca_id, nombre, area, arboles, variedad, fecha_siembra)
                )
                self.lote_ids.append(cur.lastrowid)
            except Exception as e:
                self.estadisticas["errores"] += 1
                log_error(f"Error lote '{nombre}': {e}")

        count = len(self.lote_ids)
        log_ok(f"{count}/20 lotes creados en DB")

        # Mostrar resumen de lotes
        log_data("   Distribución de lotes por edad:")
        rangos = [("Nuevos (0-1)", 0, 2), ("Formación (1-3)", 1, 4),
                   ("Producción (3-7)", 3, 8), ("Maduros (7-15)", 7, 16),
                   ("Viejos (15+)", 15, 99)]
        for label, min_e, max_e in rangos:
            lotes_rango = [l for l in LOTES_DATA if min_e <= l[4] < max_e]
            log_data(f"      {label}: {len(lotes_rango)} lotes")

        # Área total
        area_total = sum(l[1] for l in LOTES_DATA)
        log_data(f"   Área total: {area_total:.1f} ha")

    # ── Fase 4: Generar ingresos ────────────────────────────────────────

    def generar_ingresos(self):
        """Genera ingresos realistas basados en cosecha principal y mitaca."""
        log_step("Generando ingresos por ventas de café (3 años)...")
        if not self.finca_id:
            log_error("No hay finca_id — abortando")
            return

        ingresos_creados = 0

        for año in [2023, 2024, 2025]:
            # Calcular producción total del año basada en lotes productivos
            produccion_total = 0
            for _, area, _, _, edad in LOTES_DATA:
                # Edad al inicio del año (ajustar por año)
                edad_ajustada = edad - (2025 - año) if año <= 2025 else edad
                if edad_ajustada < 0:
                    edad_ajustada = 0
                rend = obtener_rendimiento(edad_ajustada)
                produccion_total += area * rend

            # La producción se divide en:
            # - 70% cosecha principal (Oct-Dic)
            # - 20% mitaca (Abr-May)
            # - 10% pasilla y re-re (mezclado en ambas épocas)
            cosecha_principal = produccion_total * 0.70
            mitaca = produccion_total * 0.20
            pasilla_total = produccion_total * 0.07
            rere_total = produccion_total * 0.03

            # Precios del año
            precios_mes = PRECIOS_CAFE[año]

            # -- Cosecha Principal (Oct-Dic) --
            # Dividir en 3-4 ventas mensuales
            meses_principal = [10, 11, 12]
            for mes in meses_principal:
                cantidad_cps = cosecha_principal / len(meses_principal)
                # Variación aleatoria ±20%
                cantidad_cps *= random.uniform(0.8, 1.2)

                # Si el lote tiene 0 producción, saltar (lotes nuevos)
                if cantidad_cps < 10:
                    continue

                precio = precios_mes[mes - 1]
                dia = random.randint(5, 25)
                fecha = f"{año}-{mes:02d}-{dia:02d}"

                try:
                    # Venta CPS
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, 'ingreso_cps', ?, ?, ?, ?, ?, ?, ?)",
                        (self.finca_id, fecha, f"Venta CPS", "CPS",
                         round(cantidad_cps, 1), "kg",
                         round(precio), int(cantidad_cps * precio))
                    )
                    ingresos_creados += 1
                except Exception as e:
                    self.estadisticas["errores"] += 1
                    log_error(f"Error ingreso CPS {año}-{mes}: {e}")

            # -- Mitaca (Abr-May) --
            for mes in [4, 5]:
                cantidad_cps = mitaca / 2
                cantidad_cps *= random.uniform(0.8, 1.2)

                if cantidad_cps < 10:
                    continue

                precio = precios_mes[mes - 1]
                dia = random.randint(5, 25)
                fecha = f"{año}-{mes:02d}-{dia:02d}"

                try:
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, 'ingreso_cps', ?, ?, ?, ?, ?, ?, ?)",
                        (self.finca_id, fecha, f"Venta CPS (Mitaca)", "CPS",
                         round(cantidad_cps, 1), "kg",
                         round(precio), int(cantidad_cps * precio))
                    )
                    ingresos_creados += 1
                except Exception as e:
                    self.estadisticas["errores"] += 1
                    log_error(f"Error ingreso mitaca {año}-{mes}: {e}")

            # -- Pasilla (subproducto) --
            # Distribuir en cosecha principal
            for mes in [10, 11, 12]:
                cantidad = pasilla_total / 3
                cantidad *= random.uniform(0.7, 1.3)
                if cantidad < 5:
                    continue

                precio_pasilla = precios_mes[mes - 1] * PASILLA_PRECIO_FACTOR
                dia = random.randint(5, 25)
                fecha = f"{año}-{mes:02d}-{dia:02d}"

                try:
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, 'ingreso_pasilla', ?, ?, ?, ?, ?, ?, ?)",
                        (self.finca_id, fecha, f"Venta Pasilla", "Pasilla",
                         round(cantidad, 1), "kg",
                         round(precio_pasilla), int(cantidad * precio_pasilla))
                    )
                    ingresos_creados += 1
                except Exception as e:
                    self.estadisticas["errores"] += 1
                    log_error(f"Error pasilla {año}-{mes}: {e}")

            # -- Re-re (re-recolección) --
            for mes in [11, 12]:
                cantidad = rere_total / 2
                cantidad *= random.uniform(0.5, 1.5)
                if cantidad < 3:
                    continue

                precio_rere = precios_mes[mes - 1] * RERE_PRECIO_FACTOR
                dia = random.randint(5, 25)
                fecha = f"{año}-{mes:02d}-{dia:02d}"

                try:
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, 'ingreso_rere', ?, ?, ?, ?, ?, ?, ?)",
                        (self.finca_id, fecha, f"Venta Re-re", "Re-re",
                         round(cantidad, 1), "kg",
                         round(precio_rere), int(cantidad * precio_rere))
                    )
                    ingresos_creados += 1
                except Exception as e:
                    self.estadisticas["errores"] += 1
                    log_error(f"Error rere {año}-{mes}: {e}")

        self.estadisticas["ingresos_creados"] = ingresos_creados
        log_ok(f"{ingresos_creados} ingresos creados")

        # Resumen por año
        for año in [2023, 2024, 2025]:
            cnt = db_count_where(f"categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            total = db_sum("valor_total", f"WHERE categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            cps = db_sum("valor_total", f"WHERE categoria='ingreso_cps' AND fecha LIKE '{año}-%'")
            pas = db_sum("valor_total", f"WHERE categoria='ingreso_pasilla' AND fecha LIKE '{año}-%'")
            rere = db_sum("valor_total", f"WHERE categoria='ingreso_rere' AND fecha LIKE '{año}-%'")
            log_money(f"   {año}: {cnt} ventas, total {format_pesos(total)} "
                      f"(CPS: {format_pesos(cps)}, Pasilla: {format_pesos(pas)}, Re-re: {format_pesos(rere)})")

    # ── Fase 5: Generar costos ─────────────────────────────────────────

    def _calcular_area_categoria(self, categoria: str, año: int, mes: int) -> float:
        """Calcula el área de lotes que aplica para una categoría y mes dado."""
        # Para instalación solo aplica en lotes nuevos (edad <= 2)
        if categoria == "instalacion":
            area = 0
            for _, l_area, _, _, edad in LOTES_DATA:
                edad_ajustada = edad - (2025 - año)
                if 0 <= edad_ajustada <= 2:
                    area += l_area
            return area

        # Para sombrío, aplica en todos los lotes
        if categoria == "sombrio":
            return sum(l[1] for l in LOTES_DATA)

        # Para recolección, solo lotes productivos (edad >= 1.5)
        if categoria == "recoleccion":
            area = 0
            for _, l_area, _, _, edad in LOTES_DATA:
                edad_ajustada = edad - (2025 - año)
                if edad_ajustada >= 1.5:
                    area += l_area
            return area

        # Para beneficio, solo lotes productivos
        if categoria == "beneficio":
            area = 0
            for _, l_area, _, _, edad in LOTES_DATA:
                edad_ajustada = edad - (2025 - año)
                if edad_ajustada >= 1.5:
                    area += l_area
            return area

        # Para el resto, aplican todos los lotes
        return sum(l[1] for l in LOTES_DATA)

    def _insertar_costo(self, año: int, mes: int, fecha: str, cat: str,
                        es_mo: bool, cat_mo: str, cat_ins: str,
                        labor_nombre: str, area: float,
                        valor_total_override: int | None = None):
        """Inserta una transacción de costo (MO o insumo) en la DB.
        
        Si se proporciona valor_total_override, se usa ese monto directamente
        en lugar de calcularlo desde jornales/insumos.
        """
        try:
            precios_mes = PRECIOS_CAFE[año]
            
            # ── Si hay override, insertar directamente ────────────────
            if valor_total_override is not None:
                if es_mo:
                    categoria_db_label = cat_mo
                else:
                    if cat_ins is None:
                        return
                    categoria_db_label = cat_ins
                db_exec(
                    "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                    "producto, cantidad, unidad, valor_unitario, valor_total) "
                    "VALUES (?, 0, ?, ?, ?, '', 1, 'global', 0, ?)",
                    (self.finca_id, categoria_db_label, fecha, labor_nombre, valor_total_override)
                )
                return

            # ── Lógica original (sin override) ───────────────────────
            if es_mo:
                # -- MANO DE OBRA --
                categoria_db_label = cat_mo

                if cat == "administrativo":
                    cantidad = 1
                    unidad = "mes"
                    valor_total = int(COSTO_ADMINISTRATIVO_MENSUAL * random.uniform(0.85, 1.15))
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, ?, ?, ?, '', ?, ?, 0, ?)",
                        (self.finca_id, categoria_db_label, fecha, labor_nombre,
                         cantidad, unidad, valor_total)
                    )
                    return

                elif cat == "recoleccion":
                    cosecha_mensual = area * 1000 * 0.2  # estimación por área
                    if cosecha_mensual < 20:
                        return
                    jornales_necesarios = math.ceil(cosecha_mensual / 80)
                    valor_total = int(jornales_necesarios * JORNAL * random.uniform(0.9, 1.1))
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, ?, ?, ?, '', ?, ?, ?, ?)",
                        (self.finca_id, categoria_db_label, fecha, labor_nombre,
                         jornales_necesarios, "jornal", JORNAL, valor_total)
                    )
                    return

                elif cat == "beneficio":
                    cafe_a_beneficiar = area * 500 * 0.25  # estimación
                    if cafe_a_beneficiar < 20:
                        return
                    costo_beneficio_kg = int(610 * (precios_mes[mes - 1] / 19000))
                    valor_total = int(cafe_a_beneficiar * costo_beneficio_kg * random.uniform(0.9, 1.1))
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, ?, ?, ?, '', ?, ?, ?, ?)",
                        (self.finca_id, categoria_db_label, fecha, labor_nombre,
                         round(cafe_a_beneficiar, 1), "kg",
                         costo_beneficio_kg, valor_total)
                    )
                    return

                else:
                    # MO general (arvenses, fertilización, fitosanitario, etc.)
                    jornales = JORNALES_POR_LABOR.get(cat, 3)
                    jornales_totales = max(1, round(jornales * area * random.uniform(0.8, 1.2)))
                    valor_total = jornales_totales * JORNAL
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, ?, ?, ?, '', ?, ?, ?, ?)",
                        (self.finca_id, categoria_db_label, fecha, labor_nombre,
                         jornales_totales, "jornal", JORNAL, valor_total)
                    )

            else:
                # -- INSUMOS --
                if cat_ins is None:
                    return
                categoria_db_label = cat_ins

                if cat in INSUMOS_DATA:
                    productos = INSUMOS_DATA[cat]
                    producto, precio_unitario, unidad = random.choice(productos)
                    cant_base = INSUMOS_POR_HA.get(cat, 1)
                    cantidad = max(1, round(cant_base * area * random.uniform(0.8, 1.2), 1))
                    precio_real = int(precio_unitario * random.uniform(0.9, 1.15))
                    valor_total = int(cantidad * precio_real)
                    db_exec(
                        "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                        "producto, cantidad, unidad, valor_unitario, valor_total) "
                        "VALUES (?, 0, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (self.finca_id, categoria_db_label, fecha, labor_nombre,
                         producto, cantidad, unidad, precio_real, valor_total)
                    )
        except Exception as e:
            self.estadisticas["errores"] += 1
            log_error(f"Error insertando costo {cat} ({fecha}): {e}")

    def generar_costos(self):
        """Genera costos realistas usando la estructura del sector cafetero colombiano.
        
        Distribución objetivo (basada en datos FNC/Cenicafé/SICA):
          Recolección 54% | Fertilización 19% | Admin 7% | Arvenses 6%
          Beneficio 6%    | Renovación 5%    | Fitosanitarios 2% | Otras 1%
        Costo total objetivo: ~$5.33M/ha/año → ~$16M/ha en 3 años acumulado.
        """
        log_step("Generando costos con estructura real del sector cafetero colombiano...")
        if not self.finca_id:
            log_error("No hay finca_id — abortando")
            return

        costos_creados = 0
        area_total = sum(l[1] for l in LOTES_DATA)

        # Mapeo de categorías DB
        categorias_db = {
            "instalacion": ("instalacion_mo", "instalacion_insumos"),
            "arvenses": ("arvenses_mo", "arvenses_insumos"),
            "fertilizacion": ("fertilizacion_mo", "fertilizacion_insumos"),
            "fitosanitario": ("fitosanitario_mo", "fitosanitario_insumos"),
            "sombrio": ("sombrio_mo", "sombrio_insumos"),
            "otras_labores": ("otras_labores_mo", "otras_labores_insumos"),
            "recoleccion": ("recoleccion", None),
            "beneficio": ("beneficio", None),
            "administrativo": ("administrativo", None),
        }

        # Porcentaje MO vs Insumos para categorías mixtas
        MO_PCT = {
            "fertilizacion": 0.25,    # 25% MO, 75% insumos
            "arvenses": 0.75,         # 75% MO (manual), 25% químico
            "fitosanitario": 0.65,    # 65% MO (monitoreo), 35% insumos
            "instalacion": 0.60,      # 60% MO, 40% insumos
            "otras_labores": 0.80,    # 80% MO, 20% insumos/herramientas
        }

        for año in [2023, 2024, 2025]:
            # Variación anual realista (±5% del total anual)
            factor_anual = random.uniform(0.95, 1.05)
            total_anual = int(COSTO_TOTAL_ANUAL_FINCA * factor_anual)

            for cat, pct in COSTOS_TARGET_FINCA.items():
                # Costo anual para esta categoría en toda la finca
                # (con variación ±8% adicional por categoría)
                costo_anual = int(total_anual * pct * random.uniform(0.92, 1.08))

                if costo_anual <= 0:
                    continue

                # Obtener entradas del calendario para esta categoría
                todas_entradas = [(m, es_mo, lab) for (m, c, es_mo, lab)
                                  in LABORES_CALENDARIO if c == cat]

                if not todas_entradas:
                    continue

                entradas_mo = [(m, lab) for (m, es_mo, lab) in todas_entradas if es_mo]
                entradas_ins = [(m, lab) for (m, es_mo, lab) in todas_entradas if not es_mo]

                # Determinar split MO/Insumos según la categoría
                if entradas_mo and entradas_ins:
                    mo_pct = MO_PCT.get(cat, 0.50)
                    mo_anual = int(costo_anual * mo_pct)
                    ins_anual = costo_anual - mo_anual

                    # Distribuir MO entre sus entradas de calendario
                    for i, (mes, labor) in enumerate(entradas_mo):
                        parte = mo_anual // len(entradas_mo)
                        if i < mo_anual % len(entradas_mo):
                            parte += 1
                        parte = max(1, int(parte * random.uniform(0.80, 1.20)))
                        dia = random.randint(1, 20)
                        fecha = f"{año}-{mes:02d}-{dia:02d}"
                        cat_mo, cat_ins = categorias_db[cat]
                        self._insertar_costo(
                            año, mes, fecha, cat, True,
                            cat_mo, cat_ins, labor, area_total,
                            valor_total_override=parte
                        )
                        costos_creados += 1

                    # Distribuir insumos entre sus entradas de calendario
                    for i, (mes, labor) in enumerate(entradas_ins):
                        parte = ins_anual // len(entradas_ins)
                        if i < ins_anual % len(entradas_ins):
                            parte += 1
                        parte = max(1, int(parte * random.uniform(0.80, 1.20)))
                        dia = random.randint(1, 20)
                        fecha = f"{año}-{mes:02d}-{dia:02d}"
                        cat_mo, cat_ins = categorias_db[cat]
                        self._insertar_costo(
                            año, mes, fecha, cat, False,
                            cat_mo, cat_ins, labor, area_total,
                            valor_total_override=parte
                        )
                        costos_creados += 1

                elif entradas_mo:
                    # Solo MO
                    for i, (mes, labor) in enumerate(entradas_mo):
                        parte = costo_anual // len(entradas_mo)
                        if i < costo_anual % len(entradas_mo):
                            parte += 1
                        parte = max(1, int(parte * random.uniform(0.85, 1.15)))
                        dia = random.randint(1, 20)
                        fecha = f"{año}-{mes:02d}-{dia:02d}"
                        cat_mo, cat_ins = categorias_db[cat]
                        self._insertar_costo(
                            año, mes, fecha, cat, True,
                            cat_mo, cat_ins, labor, area_total,
                            valor_total_override=parte
                        )
                        costos_creados += 1

                elif entradas_ins:
                    # Solo insumos
                    for i, (mes, labor) in enumerate(entradas_ins):
                        parte = costo_anual // len(entradas_ins)
                        if i < costo_anual % len(entradas_ins):
                            parte += 1
                        parte = max(1, int(parte * random.uniform(0.85, 1.15)))
                        dia = random.randint(1, 20)
                        fecha = f"{año}-{mes:02d}-{dia:02d}"
                        cat_mo, cat_ins = categorias_db[cat]
                        self._insertar_costo(
                            año, mes, fecha, cat, False,
                            cat_mo, cat_ins, labor, area_total,
                            valor_total_override=parte
                        )
                        costos_creados += 1

        self.estadisticas["costos_creados"] = costos_creados
        log_ok(f"{costos_creados} costos creados con estructura real del sector cafetero")

    # ── Fase 6: Verificar y resumir ─────────────────────────────────────

    def verificar(self):
        """Verifica la integridad de los datos generados."""
        log_step("Verificando datos generados...")

        checks = []
        # Verificar existencia
        checks.append(("Usuarios", db_count("usuarios")))
        checks.append(("Fincas", db_count("fincas")))
        checks.append(("Lotes", db_count("lotes")))
        checks.append(("Transacciones totales", db_count()))
        checks.append(("Ingresos", db_count_where("categoria LIKE 'ingreso_%'")))
        checks.append(("Costos", db_count_where("categoria NOT LIKE 'ingreso_%'")))

        # Verificar cada categoría
        categorias_check = [
            "ingreso_cps", "ingreso_pasilla", "ingreso_rere",
            "instalacion_mo", "instalacion_insumos",
            "arvenses_mo", "arvenses_insumos",
            "fertilizacion_mo", "fertilizacion_insumos",
            "fitosanitario_mo", "fitosanitario_insumos",
            "sombrio_mo", "sombrio_insumos",
            "otras_labores_mo", "otras_labores_insumos",
            "recoleccion", "beneficio", "administrativo",
        ]

        total_tx = db_count()
        total_ing = db_sum("valor_total", "WHERE categoria LIKE 'ingreso_%'")
        total_egr = db_sum("valor_total", "WHERE categoria NOT LIKE 'ingreso_%'")
        margen = total_ing - total_egr

        area_total = sum(l[1] for l in LOTES_DATA)

        log_separator()
        log_info("📋 VERIFICACIÓN DE DATOS")
        log_separator()

        log_info(f"   Tablas:")
        for label, count in checks:
            status = "✅" if count > 0 else "❌"
            log_info(f"      {status} {label}: {count}")

        log_info(f"   Categorías de transacciones:")
        for cat in categorias_check:
            cnt = db_count_where(f"categoria='{cat}'")
            total = db_sum("valor_total", f"WHERE categoria='{cat}'")
            if cnt > 0:
                log_info(f"      ✅ {cat}: {cnt} registros, {format_pesos(total)}")
            else:
                log_warn(f"      ⚠️ {cat}: 0 registros")

        log_separator()
        log_info("💰 RESUMEN FINANCIERO")
        log_separator()
        log_money(f"   Total Ingresos: {format_pesos(total_ing)}")
        log_money(f"   Total Egresos:  {format_pesos(total_egr)}")
        log_money(f"   Margen Neto:    {format_pesos(margen)}")
        log_data(f"   Área Total:     {area_total:.1f} ha")
        if area_total > 0:
            log_data(f"   Costo/ha:       {format_pesos(total_egr / area_total)}")
            log_data(f"   Ingreso/ha:     {format_pesos(total_ing / area_total)}")

        # Resumen por año
        log_separator()
        log_info("📅 RESUMEN POR AÑO")
        log_separator()
        for año in [2023, 2024, 2025]:
            ing_anual = db_sum("valor_total",
                               f"WHERE categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            egr_anual = db_sum("valor_total",
                               f"WHERE categoria NOT LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            cnt_ing = db_count_where(f"categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            cnt_egr = db_count_where(f"categoria NOT LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            margen_anual = ing_anual - egr_anual
            log_money(f"   {año}:")
            log_money(f"      Ingresos: {format_pesos(ing_anual)} ({cnt_ing} transacciones)")
            log_money(f"      Egresos:  {format_pesos(egr_anual)} ({cnt_egr} transacciones)")
            if margen_anual >= 0:
                log_money(f"      📈 Margen: {format_pesos(margen_anual)}")
            else:
                log_money(f"      📉 Margen: {format_pesos(margen_anual)}")

        # Verificar 300+ transacciones
        log_separator()
        if total_tx >= 300:
            log_ok(f"✅ META CUMPLIDA: {total_tx} transacciones totales (mínimo 300)")
        else:
            log_warn(f"⚠️ META NO CUMPLIDA: {total_tx} transacciones (necesario >= 300)")

        self.estadisticas["total_transacciones"] = total_tx

        return {
            "total_transacciones": total_tx,
            "total_ingresos": total_ing,
            "total_egresos": total_egr,
            "margen": margen,
            "area_total": area_total,
            "ingresos_count": db_count_where("categoria LIKE 'ingreso_%'"),
            "costos_count": db_count_where("categoria NOT LIKE 'ingreso_%'"),
        }

    def generar_informe_resumen(self, stats=None):
        """Genera un resumen al final, asegurando parse_mode='HTML'."""
        if stats is None:
            stats = {}

        total_tx = stats.get("total_transacciones", db_count())
        total_ing = stats.get("total_ingresos", 0)
        total_egr = stats.get("total_egresos", 0)
        margen = stats.get("margen", 0)
        area_total = stats.get("area_total", 0)

        log_separator()
        log_info("📊 RESUMEN FINAL — SIMULACIÓN CAFICULTOR ☕")
        log_separator()
        log_info(f"   <b>Finca:</b> {FINCA_NOMBRE}")
        log_info(f"   <b>Ubicación:</b> {FINCA_REGION}, {FINCA_DEPARTAMENTO}")
        log_info(f"   <b>Admin ID:</b> {ADMIN_ID}")
        log_info(f"   <b>Período:</b> 2023-2025")
        log_info(f"   <b>Área total:</b> {area_total:.1f} ha")
        log_info(f"   <b>Lotes:</b> {len(LOTES_DATA)}")
        log_info(f"   <b>Transacciones totales:</b> {total_tx}")
        log_info(f"   <b>Ingresos:</b> {stats.get('ingresos_count', 0)}")
        log_info(f"   <b>Costos:</b> {stats.get('costos_count', 0)}")
        log_info(f"   <b>Total ingresos:</b> {format_pesos(total_ing)}")
        log_info(f"   <b>Total egresos:</b> {format_pesos(total_egr)}")
        log_info(f"   <b>Margen neto:</b> {format_pesos(margen)}")
        if area_total > 0:
            log_info(f"   <b>Costo por hectárea:</b> {format_pesos(total_egr / area_total)}")
        log_info(f"   <b>Errores:</b> {self.estadisticas.get('errores', 0)}")
        log_info(f"   <b>Log:</b> {LOG_FILE}")
        log_separator()

    # ── Ejecución completa ──────────────────────────────────────────────

    def run_full(self):
        """Ejecuta todas las fases en secuencia."""
        log_separator()
        log_info("☕ <b>SIMULADOR COMPLETO DE CAFICULTOR</b>")
        log_info(f"   Finca: {FINCA_NOMBRE} — {FINCA_REGION}, {FINCA_DEPARTAMENTO}")
        log_info(f"   Período: 2023-2025")
        log_info(f"   Admin ID: {ADMIN_ID}")
        log_info(f"   DB: {DB_PATH}")
        log_info(f"   Log: {LOG_FILE}")
        log_separator()

        start_time = time.time()

        # Fase 0: Limpiar datos del admin
        self.limpiar_admin()

        # Fase 1: Registrar admin
        self.setup_admin()

        # Fase 2: Crear finca
        self.crear_finca()

        # Fase 3: Crear lotes
        self.crear_lotes()

        # Fase 4: Generar ingresos
        self.generar_ingresos()

        # Fase 5: Generar costos
        self.generar_costos()

        # Fase 6: Verificar
        stats = self.verificar()

        # Resumen final
        self.generar_informe_resumen(stats)

        duration = time.time() - start_time
        log_time(f"⏱️ Duración total: {duration:.1f} segundos")

        if self.estadisticas["errores"] > 0:
            log_error(f"Se detectaron {self.estadisticas['errores']} errores")
        else:
            log_ok("Simulación completada sin errores")


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Simulador Completo de Caficultor ☕ — Genera datos realistas para el bot"
    )
    parser.add_argument(
        "--fase", "-f",
        choices=["limpiar", "admin", "finca", "lotes", "ingresos", "costos",
                 "verificar", "todo"],
        default="todo",
        help="Fase a ejecutar (default: todo)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Logs detallados")
    args = parser.parse_args()

    # Verificar que la DB existe
    if not DB_PATH.exists():
        log_error(f"Base de datos no encontrada: {DB_PATH}")
        log_info("El bot debería haberla creado al iniciar. Inicia el bot primero:")
        log_info("   python3 main.py")
        sys.exit(1)

    log_info(f"📁 DB encontrada: {DB_PATH}")
    log_info(f"📁 Log: {LOG_FILE}")

    sim = SimuladorCaficultor(verbose=args.verbose)

    fases = {
        "limpiar": sim.limpiar_admin,
        "admin": sim.setup_admin,
        "finca": sim.crear_finca,
        "lotes": sim.crear_lotes,
        "ingresos": sim.generar_ingresos,
        "costos": sim.generar_costos,
        "verificar": sim.verificar,
    }

    if args.fase == "todo":
        sim.run_full()
    elif args.fase == "verificar":
        # Solo verificar sin modificar DB
        stats = sim.verificar()
        sim.generar_informe_resumen(stats)
    else:
        # Fase individual — necesita datos previos
        if args.fase in ("finca", "lotes", "ingresos", "costos"):
            # Asegurar que el admin está registrado
            sim.setup_admin()
            sim.crear_finca()

        fases[args.fase]()
        if args.fase in ("ingresos", "costos"):
            sim.verificar()
            sim.generar_informe_resumen()


if __name__ == "__main__":
    main()
