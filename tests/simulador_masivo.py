#!/usr/bin/env python3
"""
SIMULADOR MASIVO DE CAFICULTOR ☕ — 300+ Transacciones
=======================================================
Genera datos realistas de una finca cafetera con 20 lotes y MÍNIMO 300 transacciones
en 3 años (2023-2025) con estructura de costos FEPCafé 2024.

DIFERENCIA con simulador_caficultor.py:
- Costos generados POR LOTE en lugar de agregados por finca
- Más transacciones de ingreso (desglosadas)
- Incluye categorías sombrío
- Verificación automática de meta 300+

Uso:
    python3 tests/simulador_masivo.py
    python3 tests/simulador_masivo.py --fase todo
    python3 tests/simulador_masivo.py --fase verificar
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
EXPORTS_DIR = BASE_DIR / "exports"
LOG_FILE = LOGS_DIR / "simulador_masivo.log"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

# ── Configuración ───────────────────────────────────────────────────────
ADMIN_ID = 810796748
ADMIN_USERNAME = "Mateo"
FINCA_NOMBRE = "Finca La Esperanza"
FINCA_REGION = "Manizales"
FINCA_DEPARTAMENTO = "Caldas"

# ── Precios reales mensuales CPS ────────────────────────────────────────
PRECIOS_CAFE = {
    2023: [12010, 11800, 11500, 11200, 10800, 10500, 10200, 10500, 11000, 12500, 13500, 14000],
    2024: [15000, 16000, 17000, 17700, 18000, 18500, 19000, 19500, 20000, 21000, 22000, 23000],
    2025: [25000, 27000, 28000, 29000, 28500, 27000, 26000, 25500, 25000, 24500, 24000, 23500],
}

PASILLA_PRECIO_FACTOR = 0.40
RERE_PRECIO_FACTOR = 0.20

# Precios unitarios
JORNAL = 55_000
FERTILIZANTE_NPK = 3_200
HERBICIDA_GLIFOSATO = 18_000
FUNGICIDA_CUPRICO = 22_000
INSECTICIDA_CIPERMETRINA = 25_000
COMPOST_ORGANICO = 2_800
CAL_AGRICOLA = 1_500

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

# ── Rendimiento por edad ────────────────────────────────────────────────
RENDIMIENTO_POR_EDAD = [
    (0, 1, 0),
    (1, 2, 500),
    (2, 3, 1000),
    (3, 5, 1500),
    (5, 7, 1668),
    (7, 10, 1500),
    (10, 15, 1300),
    (15, 999, 1000),
]

def obtener_rendimiento(edad: int) -> int:
    for min_edad, max_edad, rend in RENDIMIENTO_POR_EDAD:
        if min_edad <= edad < max_edad:
            return rend
    return 1000

# ── Definición de los 20 lotes ─────────────────────────────────────────
LOTES_DATA = [
    # (nombre, area_ha, arboles, variedad, edad_inicial)
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

ANO_BASE = 2025

# ── Parámetros de costos ────────────────────────────────────────────────
COSTO_TOTAL_ANUAL_FINCA = 114_100_000  # ~$16M/ha en 3 años para ~21.4 ha

COSTOS_TARGET_FINCA = {
    "recoleccion":     0.54,   # 54%
    "fertilizacion":   0.19,   # 19%
    "administrativo":  0.07,   #  7%
    "arvenses":        0.06,   #  6%
    "beneficio":       0.06,   #  6%
    "instalacion":     0.05,   #  5%
    "fitosanitario":   0.02,   #  2%
    "sombrio":         0.003,  # 0.3% — Regulación de sombrío
    "otras_labores":   0.007,  # 0.7% — Otras labores (poda, deshije)
}

# Porcentaje MO vs Insumos para categorías mixtas
MO_PCT = {
    "fertilizacion": 0.25,
    "arvenses": 0.75,
    "fitosanitario": 0.65,
    "instalacion": 0.60,
    "otras_labores": 0.80,
    "sombrio": 0.55,
}

COSTO_ADMINISTRATIVO_MENSUAL = 350_000

# ── Logger ──────────────────────────────────────────────────────────────
logger = logging.getLogger("simulador_masivo")
logger.setLevel(logging.DEBUG)

_fh = logging.FileHandler(str(LOG_FILE), mode="w", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s|%(message)s", datefmt="%H:%M:%S"))
logger.addHandler(_fh)

_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_ch)


# ── Helpers DB ──────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def db_exec(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur
    finally:
        conn.close()

def db_exec_many(sql: str, params_list: list) -> int:
    """Ejecutar múltiples inserts en una transacción. Retorna cantidad."""
    if not params_list:
        return 0
    conn = get_conn()
    try:
        conn.execute("BEGIN")
        cur = conn.executemany(sql, params_list)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def db_query(sql: str, params: tuple = ()) -> list:
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def db_count(table: str = "transacciones", condition: str = "") -> int:
    if condition and not condition.startswith("WHERE") and not condition.startswith("FROM"):
        condition = f"WHERE {condition}"
    sql = f"SELECT COUNT(*) as cnt FROM {table} {condition}"
    rows = db_query(sql)
    return rows[0]["cnt"] if rows else 0

def db_count_where(condition: str = "") -> int:
    if condition and not condition.startswith("WHERE"):
        condition = f"WHERE {condition}"
    return db_count("transacciones", condition)

def db_sum(column: str = "valor_total", condition: str = "") -> float:
    sql = f"SELECT COALESCE(SUM({column}), 0) as total FROM transacciones {condition}"
    rows = db_query(sql)
    return rows[0]["total"] if rows else 0

def format_pesos(valor: float) -> str:
    return f"${valor:,.0f}"


# ── Logging helpers ─────────────────────────────────────────────────────
def log_info(msg):    logger.info(f"ℹ️ {msg}")
def log_ok(msg):      logger.info(f"✅ {msg}")
def log_warn(msg):    logger.warning(f"⚠️ {msg}")
def log_error(msg):   logger.error(f"❌ {msg}")
def log_step(msg):    logger.info(f"🔷 {msg}")
def log_data(msg):    logger.info(f"📊 {msg}")
def log_money(msg):   logger.info(f"💰 {msg}")
def log_time(msg):    logger.info(f"⏱️ {msg}")
def log_separator():  logger.info("=" * 70)


# ── Clase Simulador Masivo ──────────────────────────────────────────────
class SimuladorMasivo:
    """Simulador masivo de caficultor — 300+ transacciones."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.finca_id = None
        self.lote_ids = []
        self.lotes_en_db = []  # list of dicts with id, nombre, area, edad
        self.estadisticas = {
            "ingresos_creados": 0,
            "costos_creados": 0,
            "total_transacciones": 0,
            "errores": 0,
        }
        if verbose:
            _ch.setLevel(logging.DEBUG)

    # ── Fase 0: Limpiar ────────────────────────────────────────────────
    def limpiar_admin(self):
        log_step("Limpiando datos anteriores del admin...")
        try:
            db_exec(
                "DELETE FROM transacciones WHERE finca_id IN "
                "(SELECT id FROM fincas WHERE user_id = ?)",
                (ADMIN_ID,)
            )
            db_exec(
                "DELETE FROM lotes WHERE finca_id IN "
                "(SELECT id FROM fincas WHERE user_id = ?)",
                (ADMIN_ID,)
            )
            db_exec("DELETE FROM fincas WHERE user_id = ?", (ADMIN_ID,))
            db_exec(
                "UPDATE usuarios SET status='pending' WHERE user_id=?",
                (ADMIN_ID,)
            )
            log_ok("Datos del admin limpiados completamente")
        except Exception as e:
            self.estadisticas["errores"] += 1
            log_error(f"Error limpiando admin: {e}")

    def limpiar_todo(self):
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

    # ── Fase 1: Admin ──────────────────────────────────────────────────
    def setup_admin(self):
        log_step("Registrando administrador en DB...")
        try:
            db_exec(
                "INSERT OR IGNORE INTO usuarios (user_id, username, status, admin_id, approved_at) "
                "VALUES (?, ?, 'approved', ?, CURRENT_TIMESTAMP)",
                (ADMIN_ID, ADMIN_USERNAME, ADMIN_ID)
            )
            db_exec(
                "UPDATE usuarios SET status='approved', admin_id=? WHERE user_id=?",
                (ADMIN_ID, ADMIN_ID)
            )
            users = db_query("SELECT user_id, username, status FROM usuarios WHERE user_id=?", (ADMIN_ID,))
            if users:
                u = users[0]
                log_ok(f"Admin registrado: ID={u['user_id']}, status={u['status']}")
            else:
                self.estadisticas["errores"] += 1
                log_error("No se pudo registrar admin")
        except Exception as e:
            self.estadisticas["errores"] += 1
            log_error(f"Error setup_admin: {e}")

    # ── Fase 2: Finca ──────────────────────────────────────────────────
    def crear_finca(self):
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

    # ── Fase 3: 20 Lotes ───────────────────────────────────────────────
    def crear_lotes(self):
        log_step("Creando 20 lotes con diferentes edades y variedades...")
        if not self.finca_id:
            log_error("No hay finca_id — abortando creación de lotes")
            return

        self.lote_ids = []
        self.lotes_en_db = []
        for i, (nombre, area, arboles, variedad, edad) in enumerate(LOTES_DATA):
            año_siembra = ANO_BASE - edad
            fecha_siembra = f"{año_siembra}-03-15"
            try:
                cur = db_exec(
                    "INSERT INTO lotes (finca_id, nombre, area_hectareas, num_arboles, variedad, fecha_siembra) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (self.finca_id, nombre, area, arboles, variedad, fecha_siembra)
                )
                lote_id = cur.lastrowid
                self.lote_ids.append(lote_id)
                self.lotes_en_db.append({
                    "id": lote_id,
                    "nombre": nombre,
                    "area": area,
                    "arboles": arboles,
                    "variedad": variedad,
                    "edad": edad,
                })
            except Exception as e:
                self.estadisticas["errores"] += 1
                log_error(f"Error lote '{nombre}': {e}")

        count = len(self.lote_ids)
        log_ok(f"{count}/20 lotes creados en DB")

        # Resumen
        rangos = [("Nuevos (0-1)", 0, 2), ("Formación (1-3)", 1, 4),
                   ("Producción (3-7)", 3, 8), ("Maduros (7-15)", 7, 16),
                   ("Viejos (15+)", 15, 99)]
        for label, min_e, max_e in rangos:
            lotes_rango = [l for l in LOTES_DATA if min_e <= l[4] < max_e]
            log_data(f"      {label}: {len(lotes_rango)} lotes")
        area_total = sum(l[1] for l in LOTES_DATA)
        log_data(f"   Área total: {area_total:.1f} ha")

    def _edad_en_año(self, lote: dict, año: int) -> int:
        """Calcular edad del lote en un año dado."""
        edad_base = lote["edad"]
        return edad_base - (2025 - año)

    def _lotes_productivos(self, año: int) -> list:
        """Retorna lotes que producen en un año dado (edad >= 1.5)."""
        result = []
        for l in self.lotes_en_db:
            edad = self._edad_en_año(l, año)
            if edad >= 1.5:
                result.append(l)
        return result

    def _lotes_por_categoria(self, cat: str, año: int) -> list:
        """Retorna lotes que aplican para una categoría."""
        if cat == "instalacion":
            return [l for l in self.lotes_en_db if 0 <= self._edad_en_año(l, año) <= 2]
        elif cat in ("recoleccion", "beneficio"):
            return self._lotes_productivos(año)
        else:
            return self.lotes_en_db  # todos

    # ── Fase 4: Ingresos (35-45 transacciones) ─────────────────────────
    def generar_ingresos(self):
        log_step("Generando ingresos por ventas de café (3 años, 35+ transacciones)...")
        if not self.finca_id:
            log_error("No hay finca_id — abortando")
            return

        ingresos_creados = 0
        lotes_productivos_por_año = {}

        for año in [2023, 2024, 2025]:
            productivos = self._lotes_productivos(año)
            lotes_productivos_por_año[año] = productivos

            # Producción total del año
            produccion_total = 0
            for l in productivos:
                edad = self._edad_en_año(l, año)
                rend = obtener_rendimiento(edad)
                produccion_total += l["area"] * rend

            # Desglose 70% principal, 20% mitaca, 7% pasilla, 3% rere
            cosecha_principal = produccion_total * 0.70
            mitaca = produccion_total * 0.20
            pasilla_total = produccion_total * 0.07
            rere_total = produccion_total * 0.03

            precios_mes = PRECIOS_CAFE[año]

            # ── Cosecha Principal (Oct-Dic) — 2 ventas POR MES ──
            for mes in [10, 11, 12]:
                for batch in range(2):
                    cantidad_cps = cosecha_principal / 6  # 6 batches
                    cantidad_cps *= random.uniform(0.7, 1.3)
                    if cantidad_cps < 20:
                        continue
                    precio = precios_mes[mes - 1]
                    dia = random.randint(5, 25)
                    fecha = f"{año}-{mes:02d}-{dia:02d}"
                    try:
                        db_exec(
                            "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                            "producto, cantidad, unidad, valor_unitario, valor_total) "
                            "VALUES (?, 0, 'ingreso_cps', ?, ?, ?, ?, ?, ?, ?)",
                            (self.finca_id, fecha, f"Venta CPS #{batch+1}",
                             "CPS", round(cantidad_cps, 1), "kg",
                             round(precio), int(cantidad_cps * precio))
                        )
                        ingresos_creados += 1
                    except Exception as e:
                        self.estadisticas["errores"] += 1
                        log_error(f"Error ingreso CPS {año}-{mes}: {e}")

            # ── Mitaca (Abr-May) — 2 ventas POR MES ──
            for mes in [4, 5]:
                for batch in range(2):
                    cantidad_cps = mitaca / 4
                    cantidad_cps *= random.uniform(0.7, 1.3)
                    if cantidad_cps < 20:
                        continue
                    precio = precios_mes[mes - 1]
                    dia = random.randint(5, 25)
                    fecha = f"{año}-{mes:02d}-{dia:02d}"
                    try:
                        db_exec(
                            "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                            "producto, cantidad, unidad, valor_unitario, valor_total) "
                            "VALUES (?, 0, 'ingreso_cps', ?, ?, ?, ?, ?, ?, ?)",
                            (self.finca_id, fecha, f"Venta CPS (Mitaca) #{batch+1}",
                             "CPS", round(cantidad_cps, 1), "kg",
                             round(precio), int(cantidad_cps * precio))
                        )
                        ingresos_creados += 1
                    except Exception as e:
                        self.estadisticas["errores"] += 1
                        log_error(f"Error ingreso mitaca {año}-{mes}: {e}")

            # ── Pasilla (subproducto) — 2 ventas por cosecha ──
            for mes in [10, 11, 12]:
                for batch in range(2):
                    cantidad = pasilla_total / 6
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
                            (self.finca_id, fecha, f"Venta Pasilla #{batch+1}",
                             "Pasilla", round(cantidad, 1), "kg",
                             round(precio_pasilla), int(cantidad * precio_pasilla))
                        )
                        ingresos_creados += 1
                    except Exception as e:
                        self.estadisticas["errores"] += 1
                        log_error(f"Error pasilla {año}-{mes}: {e}")

            # ── Re-re — 2 ventas ──
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
                        (self.finca_id, fecha, f"Venta Re-re",
                         "Re-re", round(cantidad, 1), "kg",
                         round(precio_rere), int(cantidad * precio_rere))
                    )
                    ingresos_creados += 1
                except Exception as e:
                    self.estadisticas["errores"] += 1
                    log_error(f"Error rere {año}-{mes}: {e}")

        self.estadisticas["ingresos_creados"] = ingresos_creados
        log_ok(f"{ingresos_creados} ingresos creados")

        for año in [2023, 2024, 2025]:
            cnt = db_count_where(f"categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            total = db_sum("valor_total", f"WHERE categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            log_money(f"   {año}: {cnt} ventas, total {format_pesos(total)}")

    # ── Fase 5: Costos masivos (270+) ──────────────────────────────────
    def generar_costos(self):
        """Genera costos POR LOTE para alcanzar 270+ transacciones."""
        log_step("Generando costos masivos POR LOTE (270+ transacciones)...")
        if not self.finca_id:
            log_error("No hay finca_id — abortando")
            return

        area_total = sum(l["area"] for l in self.lotes_en_db)
        costos_creados = 0

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

        # Calendario de labores (mes, categoria, es_mo, nombre_labor)
        LABORES_CALENDARIO = [
            # Arvenses MO: Mar, Jun, Sep, Nov
            (3, "arvenses", True, "Control manual de arvenses"),
            (6, "arvenses", True, "Control manual de arvenses"),
            (9, "arvenses", True, "Control manual de arvenses"),
            (11, "arvenses", True, "Control manual de arvenses"),
            # Arvenses químico: Mar, Sep
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
            (4, "fitosanitario", True, "Monitoreo fitosanitario"),
            (5, "fitosanitario", True, "Monitoreo fitosanitario"),
            (6, "fitosanitario", True, "Monitoreo fitosanitario"),
            (7, "fitosanitario", True, "Monitoreo fitosanitario"),
            (8, "fitosanitario", True, "Monitoreo fitosanitario"),
            (9, "fitosanitario", True, "Monitoreo fitosanitario"),
            # Fitosanitario Insumos: Abr, Jun, Ago, Sep
            (4, "fitosanitario", False, "Fungicida preventivo cúprico"),
            (6, "fitosanitario", False, "Insecticida cipermetrina"),
            (8, "fitosanitario", False, "Fungicida + Insecticida"),
            (9, "fitosanitario", False, "Fungicida preventivo"),
            # Sombrío MO: Jun
            (6, "sombrio", True, "Regulación de sombrío (raleo)"),
            # Sombrío Insumos: Jun
            (6, "sombrio", False, "Herramientas para sombrío"),
            # Poda: Ene-Feb (MO)
            (1, "otras_labores", True, "Poda de formación"),
            (2, "otras_labores", True, "Poda de mantenimiento"),
            # Deshije: May, Ago, Oct (MO)
            (5, "otras_labores", True, "Deshije selectivo"),
            (8, "otras_labores", True, "Deshije selectivo"),
            (10, "otras_labores", True, "Deshije selectivo"),
            # Limpieza general: Dic (MO)
            (12, "otras_labores", True, "Limpieza general de la finca"),
            # Otras labores Insumos
            (1, "otras_labores", False, "Herramientas de poda"),
            (4, "otras_labores", False, "Cal agrícola para encalado"),
            (10, "otras_labores", False, "Insumos de limpieza"),
            (12, "otras_labores", False, "Insumos de mantenimiento"),
            # Instalación MO
            (3, "instalacion", True, "Resiembra de plántulas"),
            (4, "instalacion", True, "Resiembra de plántulas"),
            (1, "instalacion", True, "Preparación de terreno"),
            (2, "instalacion", True, "Trazo y ahoyado"),
            # Instalación Insumos
            (3, "instalacion", False, "Plántulas para resiembra"),
            (4, "instalacion", False, "Abono orgánico para resiembra"),
            (1, "instalacion", False, "Plántulas de café"),
            (2, "instalacion", False, "Fertilizante para nueva siembra"),
            # Recolección
            (10, "recoleccion", True, "Recolección cosecha principal"),
            (11, "recoleccion", True, "Recolección cosecha principal"),
            (12, "recoleccion", True, "Recolección cosecha principal"),
            (4, "recoleccion", True, "Recolección mitaca"),
            (5, "recoleccion", True, "Recolección mitaca"),
            # Beneficio
            (10, "beneficio", True, "Beneficio húmedo del café"),
            (11, "beneficio", True, "Beneficio húmedo del café"),
            (12, "beneficio", True, "Beneficio húmedo del café"),
            (5, "beneficio", True, "Beneficio de café mitaca"),
            # Administrativo (todos los meses)
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

        # Definir lotes objetivo para cada categoría MO
        # Para alcanzar ~270 costos, partimos MO en grupos y algunos en lotes individuales
        # Estrategia: 
        #   - administrativo: 36 (meses) → aggregated OK
        #   - recolección: 15 (5/mes × 3 años) → aggregated OK
        #   - beneficio: 12 (4/mes × 3 años) → aggregated OK
        #   - arvenses_mo: 12 slots × 3 años → Split en 4 grupos de lotes = 144 MO
        #   - arvenses_ins: 6 slots × 3 años = 18 → aggregated OK
        #   - fertilizacion_mo: 9 slots × 3 años → Split en 3 grupos = 81 MO
        #   - fertilizacion_ins: 9 slots × 3 años = 27 → aggregated OK
        #   - fitosanitario_mo: 18 slots × 3 años → Split en 2 grupos = 108 MO
        #   - fitosanitario_ins: 12 slots × 3 años = 36 → aggregated OK
        #   - instalacion_mo: 12 slots × 3 años → Split en lotes nuevos = 36-48
        #   - instalacion_ins: 12 slots × 3 años → aggregated OK
        #   - sombrio_mo: 3 slots × 3 años → Split en 2 grupos = 18
        #   - sombrio_ins: 3 slots × 3 años → aggregated OK
        #   - otras_labores_mo: 18 slots × 3 años → Split en 2 grupos = 108? no, too many
        # 
        # Let's refine: target ~270 costs = 30 income + 240 costs (but 30+240=270, risky)
        # Target: 300+ total → ~270 costs
        # 
        # Revised plan per year:
        #   administrativo: 12 × 3 = 36 (OK)
        #   recolección: 5 × 3 = 15 (OK)
        #   beneficio: 4 × 3 = 12 (OK)
        #   arvenses_mo: 4 × 3 × 3 grupos = 36
        #   arvenses_ins: 2 × 3 = 6
        #   fertilizacion_mo: 3 × 3 × 3 grupos = 27
        #   fertilizacion_ins: 3 × 3 = 9
        #   fitosanitario_mo: 6 × 3 × 3 grupos = 54
        #   fitosanitario_ins: 4 × 3 = 12
        #   instalacion_mo: 4 × 3 × 2 grupos = 24
        #   instalacion_ins: 4 × 3 = 12
        #   sombrio_mo: 1 × 3 × 2 grupos = 6
        #   sombrio_ins: 1 × 3 = 3
        #   otras_labores_mo: 6 × 3 × 2 grupos = 36
        #   otras_labores_ins: 4 × 3 = 12
        # Total cost = 36+15+12+36+6+27+9+54+12+24+12+6+3+36+12 = 300
        # That's borderline. Let me add a bit more: split fitosanitario_mo into 3 groups (54→81)

        # Estrategia de grupos por categoría
        # Cada grupo es una lista de índices de lotes_en_db
        GRUPOS_PRODUCTIVOS = [
            [l for l in range(len(self.lotes_en_db)) if self.lotes_en_db[l]["edad"] >= 1.5],
        ]

        # Grupo 1: lotes nuevos (edad 0-1) — para instalación
        GRUPO_NUEVOS = [i for i, l in enumerate(self.lotes_en_db) if l["edad"] <= 1]
        # Grupo 2: lotes jóvenes+productivos (edad 2-7)
        GRUPO_JOVENES = [i for i, l in enumerate(self.lotes_en_db) if 2 <= l["edad"] <= 7]
        # Grupo 3: lotes maduros+viejos (edad 8+)
        GRUPO_MADUROS = [i for i, l in enumerate(self.lotes_en_db) if l["edad"] >= 8]

        # Para arvenses: 3 grupos basados en área (norte, centro, sur = dividir 20 lotes)
        GRUPO_NORTE = list(range(0, 7))    # lotes 0-6
        GRUPO_CENTRO = list(range(7, 14))   # lotes 7-13
        GRUPO_SUR = list(range(14, 20))     # lotes 14-19

        # Para fitosanitario: lotes productivos en 3 grupos
        GRUPO_FITO_NORTE = [i for i in GRUPO_NORTE if self.lotes_en_db[i]["edad"] >= 0.5]
        GRUPO_FITO_CENTRO = [i for i in GRUPO_CENTRO if self.lotes_en_db[i]["edad"] >= 0.5]
        GRUPO_FITO_SUR = [i for i in GRUPO_SUR if self.lotes_en_db[i]["edad"] >= 0.5]

        AGrupamientos = {}

        for año in [2023, 2024, 2025]:
            factor_anual = random.uniform(0.95, 1.05)
            total_anual = int(COSTO_TOTAL_ANUAL_FINCA * factor_anual)

            for cat, pct in COSTOS_TARGET_FINCA.items():
                costo_anual = int(total_anual * pct * random.uniform(0.92, 1.08))
                if costo_anual <= 0:
                    continue

                todas_entradas = [(m, es_mo, lab) for (m, c, es_mo, lab)
                                  in LABORES_CALENDARIO if c == cat]
                if not todas_entradas:
                    continue

                entradas_mo = [(m, lab) for (m, es_mo, lab) in todas_entradas if es_mo]
                entradas_ins = [(m, lab) for (m, es_mo, lab) in todas_entradas if not es_mo]

                cat_mo, cat_ins = categorias_db[cat]

                # Calcular MO e insumos
                if entradas_mo and entradas_ins:
                    mo_pct_local = MO_PCT.get(cat, 0.50)
                    mo_anual = int(costo_anual * mo_pct_local)
                    ins_anual = costo_anual - mo_anual
                elif entradas_mo:
                    mo_anual = costo_anual
                    ins_anual = 0
                elif entradas_ins:
                    mo_anual = 0
                    ins_anual = costo_anual
                else:
                    continue

                # ── Determinar grupos de lotes para MO ──
                if cat == "administrativo":
                    # Administrativo: 1 entrada global por mes (ya definido)
                    lotes_grupos_mo = [[None]]  # None = sin lote específico
                elif cat in ("recoleccion", "beneficio"):
                    # Recolección/beneficio: agregado por finca
                    lotes_grupos_mo = [[None]]
                elif cat == "instalacion":
                    # Instalación: solo lotes nuevos (edad <= 2)
                    nuevos = [i for i, l in enumerate(self.lotes_en_db)
                              if 0 <= self._edad_en_año(l, año) <= 2]
                    if nuevos:
                        lotes_grupos_mo = [nuevos]  # Un grupo con todos los lotes nuevos
                    else:
                        lotes_grupos_mo = []
                elif cat == "sombrio":
                    # Sombrío: 2 grupos
                    lotes_grupos_mo = [GRUPO_JOVENES, GRUPO_MADUROS] if GRUPO_JOVENES and GRUPO_MADUROS else [[None]]
                elif cat == "fertilizacion":
                    # Fertilización: 3 grupos
                    lotes_grupos_mo = [GRUPO_NORTE, GRUPO_CENTRO, GRUPO_SUR]
                elif cat == "arvenses":
                    # Arvenses: 3 grupos
                    lotes_grupos_mo = [GRUPO_NORTE, GRUPO_CENTRO, GRUPO_SUR]
                elif cat == "fitosanitario":
                    # Fitosanitario: 3 grupos (solo productivos)
                    lotes_grupos_mo = []
                    for g in [GRUPO_FITO_NORTE, GRUPO_FITO_CENTRO, GRUPO_FITO_SUR]:
                        if g:
                            lotes_grupos_mo.append(g)
                    if not lotes_grupos_mo:
                        lotes_grupos_mo = [[None]]
                else:
                    # otras_labores: 2 grupos
                    lotes_grupos_mo = [GRUPO_NORTE, GRUPO_SUR]

                # ── Insertar MO por grupos de lotes ──
                if mo_anual > 0 and entradas_mo:
                    n_slots = len(entradas_mo) * max(len(lotes_grupos_mo), 1)
                    if n_slots == 0:
                        n_slots = len(entradas_mo)

                    for grupo_lotes in lotes_grupos_mo:
                        for i, (mes, labor) in enumerate(entradas_mo):
                            if n_slots == 0:
                                continue
                            parte = mo_anual // n_slots
                            if random.random() < 0.3:
                                parte += 1
                            parte = max(1, int(parte * random.uniform(0.75, 1.25)))

                            dia = random.randint(1, 20)
                            fecha = f"{año}-{mes:02d}-{dia:02d}"

                            # Asignar a un lote específico del grupo, o lote 0 si grupo=None
                            if grupo_lotes and grupo_lotes[0] is not None:
                                # Tomar un lote representativo del grupo
                                lote_idx = random.choice(grupo_lotes)
                                lote_id = self.lotes_en_db[lote_idx]["id"]
                            else:
                                lote_id = 0

                            try:
                                db_exec(
                                    "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                                    "producto, cantidad, unidad, valor_unitario, valor_total) "
                                    "VALUES (?, ?, ?, ?, ?, '', ?, 'global', 0, ?)",
                                    (self.finca_id, lote_id, cat_mo, fecha, labor,
                                     1, parte)
                                )
                                costos_creados += 1
                            except Exception as e:
                                self.estadisticas["errores"] += 1
                                log_error(f"Error costo MO {cat} ({fecha}): {e}")

                # ── Insertar Insumos por grupos de lotes ──
                if ins_anual > 0 and entradas_ins:
                    # Para insumos, también usar grupos de lotes para más granularidad
                    if cat in ("fertilizacion", "arvenses", "fitosanitario", "instalacion", "sombrio", "otras_labores"):
                        # Insumos con 2 grupos
                        ins_grupos = [GRUPO_NORTE, GRUPO_SUR]
                    else:
                        ins_grupos = [[None]]

                    n_ins_slots = len(entradas_ins) * len(ins_grupos)

                    for grupo_lotes in ins_grupos:
                        for i, (mes, labor) in enumerate(entradas_ins):
                            if n_ins_slots == 0:
                                continue
                            parte = ins_anual // n_ins_slots
                            if random.random() < 0.3:
                                parte += 1
                            parte = max(1, int(parte * random.uniform(0.75, 1.25)))

                            dia = random.randint(1, 20)
                            fecha = f"{año}-{mes:02d}-{dia:02d}"

                            if grupo_lotes and grupo_lotes[0] is not None:
                                lote_idx = random.choice(grupo_lotes)
                                lote_id = self.lotes_en_db[lote_idx]["id"]
                            else:
                                lote_id = 0

                            try:
                                db_exec(
                                    "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, "
                                    "producto, cantidad, unidad, valor_unitario, valor_total) "
                                    "VALUES (?, ?, ?, ?, ?, '', 1, 'global', 0, ?)",
                                    (self.finca_id, lote_id, cat_ins, fecha, labor,
                                     parte)
                                )
                                costos_creados += 1
                            except Exception as e:
                                self.estadisticas["errores"] += 1
                                log_error(f"Error costo ins {cat} ({fecha}): {e}")

        self.estadisticas["costos_creados"] = costos_creados
        log_ok(f"{costos_creados} costos creados con estructura FEPCafé 2024")

    # ── Fase 6: Verificar ──────────────────────────────────────────────
    def verificar(self):
        log_step("Verificando integridad de datos generados...")

        total_tx = db_count()
        total_ing = db_sum("valor_total", "WHERE categoria LIKE 'ingreso_%'")
        total_egr = db_sum("valor_total", "WHERE categoria NOT LIKE 'ingreso_%'")
        margen = total_ing - total_egr
        area_total = sum(l[1] for l in LOTES_DATA)

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

        log_separator()
        log_info("📋 VERIFICACIÓN DE DATOS")
        log_separator()

        checks = [
            ("Usuarios", db_count("usuarios")),
            ("Fincas", db_count("fincas")),
            ("Lotes", db_count("lotes")),
            ("Transacciones totales", total_tx),
            ("Ingresos", db_count_where("categoria LIKE 'ingreso_%'")),
            ("Costos", db_count_where("categoria NOT LIKE 'ingreso_%'")),
        ]
        for label, count in checks:
            status = "✅" if count > 0 else "❌"
            log_info(f"      {status} {label}: {count}")

        log_info(f"   Categorías de transacciones:")
        for cat in categorias_check:
            cnt = db_count_where(f"categoria='{cat}'")
            total = db_sum("valor_total", f"WHERE categoria='{cat}'")
            if cnt > 0:
                pct = (total / total_egr * 100) if total_egr > 0 else 0
                log_info(f"      ✅ {cat}: {cnt} registros, {format_pesos(total)} ({pct:.1f}%)")
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
            costo_ha = total_egr / area_total
            log_data(f"   Costo/ha (3 años): {format_pesos(costo_ha)}")
            log_data(f"   Costo/ha/año:      {format_pesos(costo_ha / 3)}")
            log_data(f"   Ingreso/ha:        {format_pesos(total_ing / area_total)}")

        # Distribución de costos
        log_separator()
        log_info("📊 DISTRIBUCIÓN DE COSTOS (vs target sector cafetero)")
        log_separator()
        targets = {
            "recoleccion": 0.54,
            "fertilizacion": 0.19,
            "administrativo": 0.07,
            "arvenses": 0.06,
            "beneficio": 0.06,
            "instalacion": 0.05,
            "fitosanitario": 0.02,
            "sombrio": 0.003,
            "otras_labores": 0.007,
        }
        for cat, target_pct in targets.items():
            # Sumar MO + Insumos para categorías compuestas
            if cat in ("recoleccion", "administrativo"):
                total_cat = db_sum("valor_total", f"WHERE categoria='{cat}'")
            elif cat == "beneficio":
                total_cat = db_sum("valor_total", f"WHERE categoria='{cat}'")
            else:
                total_cat = db_sum("valor_total", f"WHERE categoria='{cat}_mo'")
                total_cat += db_sum("valor_total", f"WHERE categoria='{cat}_insumos'")
            pct_real = (total_cat / total_egr * 100) if total_egr > 0 else 0
            diff = pct_real - (target_pct * 100)
            icon = "✅" if abs(diff) < 3 else ("⚠️" if abs(diff) < 6 else "❌")
            log_info(f"   {icon} {cat}: {pct_real:.1f}% (target: {target_pct*100:.0f}%, diff: {diff:+.1f}pp) — {format_pesos(total_cat)}")

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
            icon = "📈" if margen_anual >= 0 else "📉"
            log_money(f"      {icon} Margen: {format_pesos(margen_anual)}")

        # Verificar meta 300+
        log_separator()
        meta_ok = total_tx >= 300
        if meta_ok:
            log_ok(f"✅ META CUMPLIDA: {total_tx} transacciones totales (mínimo 300)")
        else:
            log_warn(f"⚠️ META NO CUMPLIDA: {total_tx} transacciones (necesario >= 300) — faltan {300 - total_tx}")

        self.estadisticas["total_transacciones"] = total_tx

        return {
            "total_transacciones": total_tx,
            "total_ingresos": total_ing,
            "total_egresos": total_egr,
            "margen": margen,
            "area_total": area_total,
            "ingresos_count": db_count_where("categoria LIKE 'ingreso_%'"),
            "costos_count": db_count_where("categoria NOT LIKE 'ingreso_%'"),
            "costo_por_ha": total_egr / area_total if area_total > 0 else 0,
            "meta_cumplida": meta_ok,
        }

    # ── Generar informe ────────────────────────────────────────────────
    def generar_informe_resumen(self, stats=None):
        if stats is None:
            stats = self.verificar()

        total_tx = stats.get("total_transacciones", db_count())
        total_ing = stats.get("total_ingresos", 0)
        total_egr = stats.get("total_egresos", 0)
        margen_val = stats.get("margen", 0)
        area_total = stats.get("area_total", 0)
        costo_ha = stats.get("costo_por_ha", 0)

        log_separator()
        log_info("📊 <b>RESUMEN FINAL — SIMULACIÓN MASIVA CAFICULTOR ☕</b>")
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
        log_info(f"   <b>Margen neto:</b> {format_pesos(margen_val)}")
        if area_total > 0:
            log_info(f"   <b>Costo por hectárea (3 años):</b> {format_pesos(costo_ha)}")
            log_info(f"   <b>Costo por hectárea/año:</b> ~{format_pesos(costo_ha / 3)}")
        log_info(f"   <b>Meta 300+:</b> {'✅ CUMPLIDA' if stats.get('meta_cumplida') else '❌ NO CUMPLIDA'}")
        log_info(f"   <b>Errores:</b> {self.estadisticas.get('errores', 0)}")
        log_info(f"   <b>Log:</b> {LOG_FILE}")
        log_separator()

    # ── Generar Excel ──────────────────────────────────────────────────
    def generar_excel(self) -> str:
        """Genera Excel usando el template y excel_manager. Retorna ruta."""
        log_step("Generando Excel con datos de la simulación...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = str(EXPORTS_DIR / f"simulacion_{FINCA_NOMBRE.replace(' ', '_')}_{timestamp}.xlsx")

        try:
            # Importar aquí para evitar dependencias tempranas
            sys.path.insert(0, str(BASE_DIR))
            from database import Database
            from excel_manager import ExcelManager
            from config import EXCEL_TEMPLATE

            db = Database()
            em = ExcelManager(EXCEL_TEMPLATE)
            em.generar_excel(self.finca_id, db, excel_path)

            if os.path.exists(excel_path):
                size_kb = os.path.getsize(excel_path) / 1024
                log_ok(f"Excel generado: {excel_path} ({size_kb:.1f} KB)")
                return excel_path
            else:
                log_error("No se generó el archivo Excel")
                return ""
        except Exception as e:
            log_error(f"Error generando Excel: {e}")
            import traceback
            traceback.print_exc()
            return ""

    # ── Generar informe detallado ──────────────────────────────────────
    def generar_informe_detallado(self, stats: dict) -> str:
        """Genera un archivo Markdown con el informe detallado."""
        log_step("Generando informe detallado en Markdown...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        informe_path = str(EXPORTS_DIR / f"informe_{FINCA_NOMBRE.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

        total_tx = stats.get("total_transacciones", db_count())
        total_ing = stats.get("total_ingresos", 0)
        total_egr = stats.get("total_egresos", 0)
        margen_val = stats.get("margen", 0)
        area_total = stats.get("area_total", 0)
        costo_ha = stats.get("costo_por_ha", 0)
        ing_count = stats.get("ingresos_count", 0)
        egr_count = stats.get("costos_count", 0)

        lines = []
        lines.append(f"# ☕ Simulación Masiva de Caficultor")
        lines.append(f"")
        lines.append(f"**Generado:** {timestamp}")
        lines.append(f"**Herramienta:** Bot Asistente Caficultor — Simulador Masivo")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 1. Información General")
        lines.append(f"")
        lines.append(f"| Campo | Valor |")
        lines.append(f"|-------|-------|")
        lines.append(f"| **Finca** | {FINCA_NOMBRE} |")
        lines.append(f"| **Ubicación** | {FINCA_REGION}, {FINCA_DEPARTAMENTO} |")
        lines.append(f"| **Período** | 2023 — 2025 (3 años) |")
        lines.append(f"| **Área total** | {area_total:.1f} ha |")
        lines.append(f"| **Número de lotes** | {len(LOTES_DATA)} |")
        lines.append(f"| **Variedades** | Castillo, Caturra, Colombia |")
        lines.append(f"| **Jornal** | $55,000/día |")
        lines.append(f"")
        lines.append(f"### Distribución de Lotes por Edad")
        lines.append(f"")
        lines.append(f"| Categoría | Rango | Cantidad |")
        lines.append(f"|-----------|-------|----------|")
        rangos = [("Nuevos", 0, 2, "0-1 años"), ("Formación", 1, 4, "1-3 años"),
                   ("Producción", 3, 8, "3-7 años"), ("Maduros", 7, 16, "7-15 años"),
                   ("Viejos", 15, 99, "15+ años")]
        for label, min_e, max_e, rango in rangos:
            count = len([l for l in LOTES_DATA if min_e <= l[4] < max_e])
            lines.append(f"| {label} | {rango} | {count} |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 2. Resumen Financiero Global")
        lines.append(f"")
        lines.append(f"| Indicador | Valor |")
        lines.append(f"|-----------|-------|")
        lines.append(f"| **Total Ingresos** | ${total_ing:,.0f} |")
        lines.append(f"| **Total Egresos** | ${total_egr:,.0f} |")
        lines.append(f"| **Margen Neto** | ${margen_val:,.0f} |")
        lines.append(f"| **Costo por ha (3 años)** | ${costo_ha:,.0f} |")
        lines.append(f"| **Costo por ha/año** | ${costo_ha/3:,.0f} |")
        lines.append(f"| **Ingreso por ha** | ${total_ing/area_total:,.0f} |")
        lines.append(f"| **Total transacciones** | {total_tx} |")
        lines.append(f"| **Transacciones de ingreso** | {ing_count} |")
        lines.append(f"| **Transacciones de costo** | {egr_count} |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 3. Distribución de Costos vs Target FEPCafé 2024")
        lines.append(f"")
        lines.append(f"| Categoría | Monto | % Real | % Target | Diferencia | Estado |")
        lines.append(f"|-----------|-------|--------|----------|------------|--------|")
        targets = {
            "recoleccion": ("Recolección", 0.54),
            "fertilizacion": ("Fertilización", 0.19),
            "administrativo": ("Administrativo", 0.07),
            "arvenses": ("Arvenses", 0.06),
            "beneficio": ("Beneficio", 0.06),
            "instalacion": ("Renovación/Instalación", 0.05),
            "fitosanitario": ("Fitosanitarios", 0.02),
            "sombrio": ("Sombrío", 0.003),
            "otras_labores": ("Otras Labores", 0.007),
        }
        for cat_key, (cat_name, target_pct) in targets.items():
            if cat_key in ("recoleccion", "administrativo"):
                total_cat = db_sum("valor_total", f"WHERE categoria='{cat_key}'")
            elif cat_key == "beneficio":
                total_cat = db_sum("valor_total", f"WHERE categoria='{cat_key}'")
            else:
                total_cat = db_sum("valor_total", f"WHERE categoria='{cat_key}_mo'")
                total_cat += db_sum("valor_total", f"WHERE categoria='{cat_key}_insumos'")
            pct_real = (total_cat / total_egr * 100) if total_egr > 0 else 0
            diff = pct_real - (target_pct * 100)
            estado = "✅" if abs(diff) < 3 else ("⚠️" if abs(diff) < 6 else "❌")
            lines.append(f"| {cat_name} | ${total_cat:,.0f} | {pct_real:.1f}% | {target_pct*100:.0f}% | {diff:+.1f}pp | {estado} |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 4. Resumen por Año")
        lines.append(f"")
        lines.append(f"| Año | Ingresos | Egresos | Margen | Tx Ingreso | Tx Costo |")
        lines.append(f"|-----|----------|---------|--------|------------|----------|")
        for año in [2023, 2024, 2025]:
            ing_a = db_sum("valor_total", f"WHERE categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            egr_a = db_sum("valor_total", f"WHERE categoria NOT LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            cnt_i = db_count_where(f"categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            cnt_e = db_count_where(f"categoria NOT LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            marg_a = ing_a - egr_a
            lines.append(f"| {año} | ${ing_a:,.0f} | ${egr_a:,.0f} | ${marg_a:,.0f} | {cnt_i} | {cnt_e} |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 5. Detalle por Categoría")
        lines.append(f"")
        lines.append(f"| Categoría | Registros | Valor Total |")
        lines.append(f"|-----------|-----------|-------------|")
        categorias = [
            ("ingreso_cps", "Venta CPS", True),
            ("ingreso_pasilla", "Venta Pasilla", True),
            ("ingreso_rere", "Venta Re-re", True),
            ("instalacion_mo", "Instalación MO", False),
            ("instalacion_insumos", "Instalación Insumos", False),
            ("arvenses_mo", "Arvenses MO", False),
            ("arvenses_insumos", "Arvenses Insumos", False),
            ("fertilizacion_mo", "Fertilización MO", False),
            ("fertilizacion_insumos", "Fertilización Insumos", False),
            ("fitosanitario_mo", "Fitosanitario MO", False),
            ("fitosanitario_insumos", "Fitosanitario Insumos", False),
            ("sombrio_mo", "Sombrío MO", False),
            ("sombrio_insumos", "Sombrío Insumos", False),
            ("otras_labores_mo", "Otras Labores MO", False),
            ("otras_labores_insumos", "Otras Labores Insumos", False),
            ("recoleccion", "Recolección", False),
            ("beneficio", "Beneficio", False),
            ("administrativo", "Administrativo", False),
        ]
        for cat_key, cat_label, is_income in categorias:
            cnt = db_count_where(f"categoria='{cat_key}'")
            val = db_sum("valor_total", f"WHERE categoria='{cat_key}'")
            icon = "💰" if is_income else "📉"
            lines.append(f"| {icon} {cat_label} | {cnt} | ${val:,.0f} |")
        lines.append(f"")

        # Precios usados
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 6. Precios Referencia")
        lines.append(f"")
        lines.append(f"### Precios CPS por Mes ($/kg)")
        lines.append(f"")
        lines.append(f"| Mes | 2023 | 2024 | 2025 |")
        lines.append(f"|-----|------|------|------|")
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        for i, mes in enumerate(meses):
            p23 = PRECIOS_CAFE[2023][i]
            p24 = PRECIOS_CAFE[2024][i]
            p25 = PRECIOS_CAFE[2025][i]
            lines.append(f"| {mes} | ${p23:,} | ${p24:,} | ${p25:,} |")
        lines.append(f"")
        lines.append(f"| **Pasilla** | 40% del CPS | | |")
        lines.append(f"| **Re-re** | 20% del CPS | | |")
        lines.append(f"")
        lines.append(f"### Costos Unitarios")
        lines.append(f"")
        lines.append(f"| Insumo/Labor | Precio |")
        lines.append(f"|--------------|--------|")
        lines.append(f"| Jornal | $55,000/día |")
        lines.append(f"| Fertilizante NPK 15-15-15 | $3,200/kg |")
        lines.append(f"| Glifosato | $18,000/L |")
        lines.append(f"| Fungicida cúprico | $22,000/kg |")
        lines.append(f"| Insecticida cipermetrina | $25,000/L |")
        lines.append(f"| Compost orgánico | $2,800/kg |")
        lines.append(f"| Cal agrícola | $1,500/kg |")
        lines.append(f"| Admin mensual | $350,000 |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## 7. Metodología")
        lines.append(f"")
        lines.append(f"- **Base de datos:** SQLite (finca.db)")
        lines.append(f"- **Simulador:** Python 3.11, acceso directo a DB")
        lines.append(f"- **Costos:** Basados en estructura FEPCafé 2024 y datos del sector cafetero colombiano")
        lines.append(f"- **Rendimientos:** Curva técnica Cenicafé por edad del cafetal")
        lines.append(f"- **Precios:** Precios reales del mercado colombiano 2023-2025")
        lines.append(f"- **Costo objetivo:** ~$16M/ha en 3 años (promedio nacional FEPCafé)")
        lines.append(f"- **Distribución:** Recolección ~54%, Fertilización ~19%, Admin ~7%, etc.")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*Informe generado automáticamente por Bot Asistente Caficultor ☕*")

        content = "\n".join(lines)
        with open(informe_path, "w", encoding="utf-8") as f:
            f.write(content)

        log_ok(f"Informe detallado generado: {informe_path}")
        return informe_path

    # ── Sincronizar GitHub ─────────────────────────────────────────────
    def sync_to_github(self):
        """Sincroniza datos con GitHub usando sync_to_github.py."""
        log_step("Sincronizando datos con GitHub...")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, str(BASE_DIR / "sync_to_github.py")],
                cwd=str(BASE_DIR),
                capture_output=True, text=True, timeout=120,
            )
            log_info(result.stdout)
            if result.returncode != 0:
                log_warn(f"GitHub sync stderr: {result.stderr[:500]}")
                log_warn("La sincronización con GitHub no se completó (puede requerir SSH configurado)")
                return False
            log_ok("Datos sincronizados con GitHub exitosamente")
            return True
        except FileNotFoundError:
            log_warn("sync_to_github.py no encontrado en el proyecto")
            return False
        except Exception as e:
            log_warn(f"Error sincronizando GitHub: {e}")
            return False

    # ── Run Full ───────────────────────────────────────────────────────
    def run_full(self):
        log_separator()
        log_info("☕ <b>SIMULADOR MASIVO DE CAFICULTOR — 300+ TRANSACCIONES</b>")
        log_info(f"   Finca: {FINCA_NOMBRE} — {FINCA_REGION}, {FINCA_DEPARTAMENTO}")
        log_info(f"   Período: 2023-2025")
        log_info(f"   Admin ID: {ADMIN_ID}")
        log_info(f"   DB: {DB_PATH}")
        log_separator()

        start_time = time.time()

        self.limpiar_admin()
        self.setup_admin()
        self.crear_finca()
        self.crear_lotes()
        self.generar_ingresos()
        self.generar_costos()
        stats = self.verificar()
        self.generar_informe_resumen(stats)

        # Generate Excel
        excel_path = self.generar_excel()

        # Generate detailed report
        informe_path = self.generar_informe_detallado(stats)

        # Sync to GitHub
        self.sync_to_github()

        duration = time.time() - start_time
        log_time(f"⏱️ Duración total: {duration:.1f} segundos")

        if self.estadisticas["errores"] > 0:
            log_error(f"Se detectaron {self.estadisticas['errores']} errores")
        else:
            log_ok("Simulación masiva completada sin errores")

        return stats, excel_path, informe_path


# ── Main ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Simulador Masivo de Caficultor ☕ — 300+ transacciones"
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

    if not DB_PATH.exists():
        log_error(f"Base de datos no encontrada: {DB_PATH}")
        log_info("Inicia el bot primero: python3 main.py")
        sys.exit(1)

    log_info(f"📁 DB encontrada: {DB_PATH}")
    log_info(f"📁 Log: {LOG_FILE}")

    sim = SimuladorMasivo(verbose=args.verbose)

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
        stats = sim.verificar()
        sim.generar_informe_resumen(stats)
    else:
        if args.fase in ("finca", "lotes", "ingresos", "costos"):
            sim.setup_admin()
            sim.crear_finca()
        fases[args.fase]()
        if args.fase in ("ingresos", "costos"):
            sim.verificar()
            sim.generar_informe_resumen()


if __name__ == "__main__":
    main()
