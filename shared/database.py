"""
Base de datos compartida entre Bot y Mini App.

Thread-safe, SQLite con WAL mode, compatible con la API del bot actual.
La ruta de la BD se configura via variable de entorno CAFE_DB_PATH o parámetro.
"""

import os
import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional

log = logging.getLogger(__name__)

# Ruta configurable: por defecto la del bot, la Mini App puede sobrescribir
_DEFAULT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.environ.get("CAFE_DB_PATH", os.path.join(_DEFAULT_DIR, "finca.db"))


# ═══════════════════════════════════════════════════════════════════════
# SCHEMA (idéntico al de database.py actual — mantener sincronizado)
# ═══════════════════════════════════════════════════════════════════════

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    nombre TEXT DEFAULT '',
    telefono TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    admin_id INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS fincas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES usuarios(user_id),
    nombre TEXT NOT NULL,
    region TEXT DEFAULT '',
    departamento TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finca_id INTEGER REFERENCES fincas(id),
    nombre TEXT NOT NULL,
    area_hectareas REAL DEFAULT 0,
    num_arboles INTEGER DEFAULT 0,
    variedad TEXT DEFAULT '',
    fecha_siembra TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS transacciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finca_id INTEGER REFERENCES fincas(id),
    lote_id INTEGER DEFAULT 0,
    categoria TEXT NOT NULL,
    fecha TEXT NOT NULL,
    labor TEXT DEFAULT '',
    producto TEXT DEFAULT '',
    cantidad REAL DEFAULT 0,
    unidad TEXT DEFAULT '',
    valor_unitario REAL DEFAULT 0,
    valor_total REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transacciones_finca ON transacciones(finca_id);
CREATE INDEX IF NOT EXISTS idx_transacciones_categoria ON transacciones(categoria);
CREATE INDEX IF NOT EXISTS idx_transacciones_fecha ON transacciones(fecha);
CREATE INDEX IF NOT EXISTS idx_lotes_finca ON lotes(finca_id);

CREATE TABLE IF NOT EXISTS presupuestos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finca_id INTEGER REFERENCES fincas(id),
    anio INTEGER NOT NULL,
    categoria TEXT NOT NULL,
    monto_planificado REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(finca_id, anio, categoria)
);

CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    """Base de datos SQLite compartida y thread-safe.

    Usa check_same_thread=False + context manager para conexiones
    seguras desde múltiples hilos (Bot + Mini App).
    """

    # Categorías que tienen subcategorías MO e Insumos
    CATEGORIAS_CON_MO_Y_INSUMOS = [
        "instalacion", "arvenses", "fertilizacion",
        "fitosanitario", "sombrio", "otras_labores",
    ]
    # Categorías simples (solo MO, sin subcategoría de insumos)
    CATEGORIAS_SIMPLE = ["recoleccion", "beneficio", "administrativo"]

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._init_db()

    # ─── Conexión thread-safe ──────────────────────────────────────

    @contextmanager
    def get_conn(self):
        """Context manager para conexiones thread-safe con WAL mode.

        Uso:
            with db.get_conn() as conn:
                rows = conn.execute("SELECT * FROM ...").fetchall()
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Inicializa la BD: crea tablas y admin por defecto."""
        with self.get_conn() as conn:
            conn.executescript(SCHEMA)

            # Asegurar que el admin exista (sin duplicar)
            admin_id = 810796748
            existing = conn.execute(
                "SELECT user_id FROM usuarios WHERE user_id = ?", (admin_id,)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO usuarios (user_id, username, nombre, status, admin_id, approved_at) "
                    "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    (admin_id, "mateo", "Mateo", "approved", admin_id),
                )
                log.info(f"✅ Admin por defecto creado (ID: {admin_id})")

    # ═══════════════════════════════════════════════════════════════
    # MÉTODOS DE COMPATIBILIDAD (API compatible con database.py)
    # ═══════════════════════════════════════════════════════════════

    # ─── Usuarios ───

    def upsert_user(self, user_id: int, username: str):
        """Insertar o actualizar usuario."""
        with self.get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO usuarios (user_id, username, status) VALUES (?, ?, 'pending')",
                (user_id, username or ""),
            )

    def register_user(self, user_id: int, username: str) -> bool:
        """Registrar nuevo usuario. Retorna True si era nuevo, False si ya existía."""
        with self.get_conn() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO usuarios (user_id, username, status) VALUES (?, ?, 'pending')",
                (user_id, username or ""),
            )
            return cur.rowcount > 0

    def get_user_status(self, user_id: int) -> Optional[str]:
        """Obtener status de usuario."""
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT status FROM usuarios WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row["status"] if row else None

    def is_approved(self, user_id: int) -> bool:
        return self.get_user_status(user_id) == "approved"

    def is_pending(self, user_id: int) -> bool:
        return self.get_user_status(user_id) == "pending"

    def approve_user(self, user_id: int, approved_by: int) -> bool:
        """Aprobar usuario. Retorna True si se aprobó, False si no existía."""
        with self.get_conn() as conn:
            cur = conn.execute(
                "UPDATE usuarios SET status='approved', admin_id=?, approved_at=CURRENT_TIMESTAMP "
                "WHERE user_id=? AND status='pending'",
                (approved_by, user_id),
            )
            return cur.rowcount > 0

    def reject_user(self, user_id: int) -> bool:
        with self.get_conn() as conn:
            cur = conn.execute(
                "UPDATE usuarios SET status='rejected' WHERE user_id=? AND status='pending'",
                (user_id,),
            )
            return cur.rowcount > 0

    def get_pending_users(self) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT user_id, username, created_at FROM usuarios WHERE status='pending' ORDER BY created_at"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_users(self) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT user_id, username, status, created_at, approved_at FROM usuarios ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_approved_users(self) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT user_id, username, created_at, approved_at FROM usuarios WHERE status='approved' ORDER BY approved_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_rejected_users(self) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT user_id, username, created_at FROM usuarios WHERE status='rejected' ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def revoke_user(self, user_id: int) -> bool:
        with self.get_conn() as conn:
            cur = conn.execute(
                "UPDATE usuarios SET status='rejected' WHERE user_id=? AND status='approved'",
                (user_id,),
            )
            return cur.rowcount > 0

    def reactivate_user(self, user_id: int) -> bool:
        with self.get_conn() as conn:
            cur = conn.execute(
                "UPDATE usuarios SET status='pending' WHERE user_id=? AND status='rejected'",
                (user_id,),
            )
            return cur.rowcount > 0

    def delete_all_user_data(self, user_id: int) -> dict:
        """Borrar TODOS los datos de un usuario (transacciones, lotes, fincas).
        Retorna un resumen de lo borrado."""
        with self.get_conn() as conn:
            trans_count = conn.execute(
                "SELECT COUNT(*) FROM transacciones WHERE finca_id IN (SELECT id FROM fincas WHERE user_id=?)",
                (user_id,),
            ).fetchone()[0]
            lotes_count = conn.execute(
                "SELECT COUNT(*) FROM lotes WHERE finca_id IN (SELECT id FROM fincas WHERE user_id=?)",
                (user_id,),
            ).fetchone()[0]
            fincas_count = conn.execute(
                "SELECT COUNT(*) FROM fincas WHERE user_id=?", (user_id,)
            ).fetchone()[0]

            conn.execute(
                "DELETE FROM transacciones WHERE finca_id IN (SELECT id FROM fincas WHERE user_id=?)",
                (user_id,),
            )
            conn.execute(
                "DELETE FROM lotes WHERE finca_id IN (SELECT id FROM fincas WHERE user_id=?)",
                (user_id,),
            )
            conn.execute("DELETE FROM fincas WHERE user_id=?", (user_id,))

            return {"transacciones": trans_count, "lotes": lotes_count, "fincas": fincas_count}

    # ─── Fincas ───

    def create_finca(self, user_id: int, nombre: str, region: str = "", departamento: str = "") -> int:
        with self.get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO fincas (user_id, nombre, region, departamento) VALUES (?, ?, ?, ?)",
                (user_id, nombre, region, departamento),
            )
            return cur.lastrowid

    def get_fincas(self, user_id: int) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM fincas WHERE user_id = ? ORDER BY created_at", (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_finca(self, finca_id: int) -> Optional[dict]:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM fincas WHERE id = ?", (finca_id,)).fetchone()
            return dict(row) if row else None

    def get_finca_by_id(self, finca_id: int) -> Optional[dict]:
        return self.get_finca(finca_id)

    # ─── Lotes ───

    def create_lote(
        self, finca_id: int, nombre: str, area: float = 0, num_arboles: int = 0,
        variedad: str = "", fecha_siembra: str = ""
    ) -> int:
        with self.get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO lotes (finca_id, nombre, area_hectareas, num_arboles, variedad, fecha_siembra) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (finca_id, nombre, area, num_arboles, variedad, fecha_siembra),
            )
            return cur.lastrowid

    def get_lotes(self, finca_id: int) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM lotes WHERE finca_id = ? ORDER BY nombre", (finca_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_lote_by_id(self, lote_id: int) -> Optional[dict]:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM lotes WHERE id = ?", (lote_id,)).fetchone()
            return dict(row) if row else None

    # ─── Transacciones ───

    def insert_transaccion(
        self, finca_id: int, categoria: str, fecha: str,
        labor: str = "", producto: str = "", cantidad: float = 0,
        unidad: str = "", valor_unitario: float = 0,
        valor_total: float = 0, lote_id: int = 0,
    ) -> int:
        with self.get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO transacciones "
                "(finca_id, lote_id, categoria, fecha, labor, producto, cantidad, unidad, valor_unitario, valor_total) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (finca_id, int(lote_id), categoria, fecha, labor, producto,
                 cantidad, unidad, valor_unitario, valor_total),
            )
            return cur.lastrowid

    def get_transacciones(self, finca_id: int, categoria: str) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                (finca_id, categoria),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_transacciones(self, finca_id: int) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM transacciones WHERE finca_id = ? ORDER BY fecha, categoria, id",
                (finca_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_transacciones_por_finca(self, finca_id: int) -> dict:
        """Obtener transacciones organizadas por categoría, normalizando la nomenclatura."""
        with self.get_conn() as conn:
            result = {}

            for cat in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                rows_mo = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, f"{cat}_mo"),
                ).fetchall()]
                rows_ins = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, f"{cat}_insumos"),
                ).fetchall()]
                result[f"{cat}_mo"] = rows_mo
                result[f"{cat}_insumos"] = rows_ins

            for cat in self.CATEGORIAS_SIMPLE:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, cat),
                ).fetchall()]
                result[cat] = rows

            for cat_ing in ["ingreso_cps", "ingreso_pasilla"]:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, cat_ing),
                ).fetchall()]
                result[cat_ing] = rows

            return result

    def get_all_data_for_export(self, finca_id: int) -> dict:
        """Obtener TODOS los datos de una finca organizados para exportar a Excel."""
        with self.get_conn() as conn:
            lotes = [dict(r) for r in conn.execute(
                "SELECT * FROM lotes WHERE finca_id = ? ORDER BY id", (finca_id,)
            ).fetchall()]

            data = {"lotes": lotes}

            categorias = [
                "ingreso_cps", "ingreso_pasilla",
                "instalacion_mo", "instalacion_insumos",
                "arvenses_mo", "arvenses_insumos",
                "fertilizacion_mo", "fertilizacion_insumos",
                "fitosanitario_mo", "fitosanitario_insumos",
                "sombrio_mo", "sombrio_insumos",
                "otras_labores_mo", "otras_labores_insumos",
                "recoleccion", "beneficio", "administrativo",
            ]

            for cat in categorias:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, cat),
                ).fetchall()]
                data[cat] = rows

            return data

    def get_resumen_finca(self, finca_id: int) -> dict:
        """Obtener resumen financiero de una finca."""
        with self.get_conn() as conn:
            ingresos = conn.execute(
                "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria LIKE 'ingreso_%'",
                (finca_id,),
            ).fetchone()["total"] or 0

            egresos = conn.execute(
                "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria NOT LIKE 'ingreso_%'",
                (finca_id,),
            ).fetchone()["total"] or 0

            area = conn.execute(
                "SELECT SUM(area_hectareas) as total FROM lotes WHERE finca_id = ?",
                (finca_id,),
            ).fetchone()["total"] or 0

            egresos_cat = {}
            for cat in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                total_mo = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ?",
                    (finca_id, f"{cat}_mo"),
                ).fetchone()["total"] or 0
                total_ins = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ?",
                    (finca_id, f"{cat}_insumos"),
                ).fetchone()["total"] or 0
                egresos_cat[cat] = total_mo + total_ins

            for cat in self.CATEGORIAS_SIMPLE:
                total = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ?",
                    (finca_id, cat),
                ).fetchone()["total"] or 0
                egresos_cat[cat] = total

            ingresos_tipos = {}
            for cat_ing in ["ingreso_cps", "ingreso_pasilla"]:
                total = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ?",
                    (finca_id, cat_ing),
                ).fetchone()["total"] or 0
                ingresos_tipos[cat_ing] = total

            return {
                "ingresos": ingresos,
                "egresos": egresos,
                "margen": ingresos - egresos,
                "area_total": area,
                "costo_por_hectarea": (egresos / area) if area > 0 else 0,
                "egresos_por_categoria": egresos_cat,
                "ingresos_por_tipo": ingresos_tipos,
            }

    # ─── Presupuestos ───

    def guardar_presupuesto(self, finca_id: int, anio: int, datos: dict):
        """Guarda o actualiza el presupuesto para un año."""
        with self.get_conn() as conn:
            for categoria, monto in datos.items():
                conn.execute(
                    "INSERT INTO presupuestos (finca_id, anio, categoria, monto_planificado) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(finca_id, anio, categoria) "
                    "DO UPDATE SET monto_planificado = excluded.monto_planificado",
                    (finca_id, anio, categoria, monto or 0),
                )
            log.info(f"✅ Presupuesto guardado finca={finca_id} año={anio}")

    def get_presupuesto(self, finca_id: int, anio: int) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM presupuestos WHERE finca_id = ? AND anio = ? ORDER BY categoria",
                (finca_id, anio),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_presupuesto_anios(self, finca_id: int) -> list:
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT anio FROM presupuestos WHERE finca_id = ? ORDER BY anio DESC",
                (finca_id,),
            ).fetchall()
            return [r["anio"] for r in rows]

    def delete_presupuesto(self, finca_id: int, anio: int):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM presupuestos WHERE finca_id = ? AND anio = ?", (finca_id, anio))

    # ─── Indicadores Técnicos ───

    @staticmethod
    def _lote_es_productivo(lote: dict) -> bool:
        return bool(lote.get("num_arboles", 0) and lote.get("fecha_siembra", ""))

    def _get_total_insumos_cantidad_convertida(self, finca_id: int) -> dict:
        """Obtiene la cantidad total de insumos convertida a unidad estándar."""
        from config import CONVERSION_A_KG, CONVERSION_A_LITROS, UNIDADES_SOLIDOS, UNIDADES_LIQUIDOS

        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT cantidad, unidad FROM transacciones WHERE finca_id = ? AND categoria LIKE '%_insumos'",
                (finca_id,),
            ).fetchall()

        total_kg = 0.0
        total_litros = 0.0

        for row in rows:
            cantidad = row["cantidad"] or 0
            unidad = (row["unidad"] or "").strip().lower()

            if unidad in UNIDADES_SOLIDOS:
                factor = CONVERSION_A_KG.get(unidad, 1)
                total_kg += cantidad * factor
            elif unidad in UNIDADES_LIQUIDOS:
                factor = CONVERSION_A_LITROS.get(unidad, 1)
                total_litros += cantidad * factor
            else:
                total_kg += cantidad

        return {
            "total_kg": total_kg,
            "total_litros": total_litros,
            "total_estandar": total_kg,
        }

    def _get_total_ingresos(self, finca_id: int) -> float:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones WHERE finca_id = ? AND categoria LIKE 'ingreso_%'",
                (finca_id,),
            ).fetchone()
            return row[0] if row else 0.0

    def _get_costos_por_tipo(self, finca_id: int, tipo: str) -> float:
        """Obtiene costos por tipo: 'mo' o 'insumos'."""
        with self.get_conn() as conn:
            if tipo == "mo":
                total = 0.0
                for cat_base in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                    row = conn.execute(
                        "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones WHERE finca_id = ? AND categoria = ?",
                        (finca_id, f"{cat_base}_mo"),
                    ).fetchone()
                    total += row[0] if row else 0.0
                for cat in self.CATEGORIAS_SIMPLE:
                    row = conn.execute(
                        "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones WHERE finca_id = ? AND categoria = ?",
                        (finca_id, cat),
                    ).fetchone()
                    total += row[0] if row else 0.0
                return total
            elif tipo == "insumos":
                total = 0.0
                for cat_base in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                    row = conn.execute(
                        "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones WHERE finca_id = ? AND categoria = ?",
                        (finca_id, f"{cat_base}_insumos"),
                    ).fetchone()
                    total += row[0] if row else 0.0
                return total
            return 0.0

    def _get_kg_producidos(self, finca_id: int) -> float:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(cantidad), 0) FROM transacciones "
                "WHERE finca_id = ? AND categoria IN ('ingreso_cps', 'ingreso_pasilla')",
                (finca_id,),
            ).fetchone()
            return row[0] if row else 0.0

    def _get_total_jornales(self, finca_id: int) -> float:
        with self.get_conn() as conn:
            categorias_mo = [f"{c}_mo" for c in self.CATEGORIAS_CON_MO_Y_INSUMOS] + list(self.CATEGORIAS_SIMPLE)
            placeholders = ",".join("?" for _ in categorias_mo)
            row = conn.execute(
                f"SELECT COALESCE(SUM(cantidad), 0) FROM transacciones "
                f"WHERE finca_id = ? AND categoria IN ({placeholders}) "
                f"AND (unidad IN ('día', 'dia', 'jornal', 'jornales', '') OR unidad IS NULL)",
                (finca_id, *categorias_mo),
            ).fetchone()
            return row[0] if row else 0.0

    def get_indicadores_tecnicos(self, finca_id: int) -> dict:
        """Calcula todos los indicadores técnicos de la finca."""
        with self.get_conn() as conn:
            lotes = [dict(r) for r in conn.execute(
                "SELECT * FROM lotes WHERE finca_id = ?", (finca_id,)
            ).fetchall()]

        area_total = sum(l["area_hectareas"] for l in lotes)
        area_productiva = sum(l["area_hectareas"] for l in lotes if self._lote_es_productivo(l))

        ingresos = self._get_total_ingresos(finca_id)
        costos_mo = self._get_costos_por_tipo(finca_id, "mo")
        costos_insumos = self._get_costos_por_tipo(finca_id, "insumos")
        costos_total = costos_mo + costos_insumos
        kg_producidos = self._get_kg_producidos(finca_id)
        total_jornales = self._get_total_jornales(finca_id)
        insumos_cant = self._get_total_insumos_cantidad_convertida(finca_id)

        return {
            "area_total": area_total,
            "area_productiva": area_productiva,
            "ingresos_totales": ingresos,
            "costos_mo": costos_mo,
            "costos_insumos": costos_insumos,
            "costos_total": costos_total,
            "kg_producidos": kg_producidos,
            "total_jornales": total_jornales,
            "productividad": kg_producidos / area_total if area_total > 0 else 0,
            "rendimiento": kg_producidos / area_productiva if area_productiva > 0 else 0,
            "jornales_por_ha": total_jornales / area_total if area_total > 0 else 0,
            "costo_mo_por_ha": costos_mo / area_total if area_total > 0 else 0,
            "costo_insumos_por_ha": costos_insumos / area_total if area_total > 0 else 0,
            "costo_total_por_ha": costos_total / area_total if area_total > 0 else 0,
            "costo_por_kilo": costos_total / kg_producidos if kg_producidos > 0 else 0,
            "margen_por_ha": (ingresos - costos_total) / area_total if area_total > 0 else 0,
            "precio_venta_promedio": ingresos / kg_producidos if kg_producidos > 0 else 0,
            "eficiencia_mo": kg_producidos / total_jornales if total_jornales > 0 else 0,
            "costo_insumos_por_kg_cps": costos_insumos / kg_producidos if kg_producidos > 0 else 0,
            "costo_mo_por_kg_cps": costos_mo / kg_producidos if kg_producidos > 0 else 0,
            "insumos_por_ha": insumos_cant["total_estandar"] / area_total if area_total > 0 else 0,
            "insumos_total_kg": insumos_cant["total_estandar"],
            "insumos_total_litros": insumos_cant["total_litros"],
            "eficiencia_insumos": kg_producidos / insumos_cant["total_estandar"] if insumos_cant["total_estandar"] > 0 else 0,
        }

    def get_ejecucion_presupuesto(self, finca_id: int, anio: int) -> dict:
        """Compara presupuesto planificado vs ejecutado real."""
        with self.get_conn() as conn:
            fecha_like = f"{anio}-%"

            CATEGORIAS_FEPCAFE = [
                ("recoleccion", ["recoleccion"]),
                ("fertilizacion", ["fertilizacion_mo", "fertilizacion_insumos"]),
                ("administrativo", ["administrativo"]),
                ("arvenses", ["arvenses_mo", "arvenses_insumos"]),
                ("beneficio", ["beneficio"]),
                ("instalacion", ["instalacion_mo", "instalacion_insumos"]),
                ("fitosanitario", ["fitosanitario_mo", "fitosanitario_insumos"]),
                ("otras_labores", ["otras_labores_mo", "otras_labores_insumos"]),
            ]

            categorias = []
            total_planificado = 0.0
            total_ejecutado = 0.0

            for cat_id, categorias_db in CATEGORIAS_FEPCAFE:
                row = conn.execute(
                    "SELECT monto_planificado FROM presupuestos WHERE finca_id = ? AND anio = ? AND categoria = ?",
                    (finca_id, anio, cat_id),
                ).fetchone()
                monto_planificado = row["monto_planificado"] if row else 0.0

                monto_ejecutado = 0.0
                for cat_db in categorias_db:
                    row_ej = conn.execute(
                        "SELECT COALESCE(SUM(valor_total), 0) as total FROM transacciones "
                        "WHERE finca_id = ? AND categoria = ? AND fecha LIKE ?",
                        (finca_id, cat_db, fecha_like),
                    ).fetchone()
                    monto_ejecutado += row_ej["total"] if row_ej else 0.0

                diferencia = monto_ejecutado - monto_planificado
                pct_ejecucion = (
                    (monto_ejecutado / monto_planificado * 100)
                    if monto_planificado > 0
                    else (0 if monto_ejecutado == 0 else 100)
                )

                categorias.append({
                    "categoria": cat_id,
                    "monto_planificado": monto_planificado,
                    "monto_ejecutado": monto_ejecutado,
                    "diferencia": diferencia,
                    "pct_ejecucion": round(pct_ejecucion, 1),
                })

                total_planificado += monto_planificado
                total_ejecutado += monto_ejecutado

            return {
                "categorias": categorias,
                "total_planificado": total_planificado,
                "total_ejecutado": total_ejecutado,
                "total_diferencia": total_ejecutado - total_planificado,
            }

    # ─── Offline Sync Queue ───

    def add_sync_queue(self, action: str, data: dict):
        import json
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO sync_queue (action, data) VALUES (?, ?)",
                (action, json.dumps(data)),
            )
            log.info(f"📤 Sincronización en cola: {action}")

    def get_sync_queue(self) -> list:
        import json
        with self.get_conn() as conn:
            rows = conn.execute("SELECT * FROM sync_queue ORDER BY created_at").fetchall()
            return [dict(r) for r in rows]

    def process_sync_queue(self):
        import json
        with self.get_conn() as conn:
            rows = conn.execute("SELECT * FROM sync_queue ORDER BY created_at").fetchall()
            for row in rows:
                log.info(f"🔄 Procesando sync_queue ID {row['id']}: {row['action']}")
                conn.execute("DELETE FROM sync_queue WHERE id = ?", (row["id"],))
            log.info(f"✅ Cola de sincronización procesada: {len(rows)} items")

    # ==================================================================
    # NUEVOS MÉTODOS para Mini App (FastAPI)
    # ==================================================================

    def get_transacciones_por_periodo(
        self, finca_id: int, fecha_inicio: str, fecha_fin: str
    ) -> list:
        """Obtiene transacciones en un rango de fechas."""
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM transacciones WHERE finca_id=? AND fecha BETWEEN ? AND ? ORDER BY fecha",
                (finca_id, fecha_inicio, fecha_fin),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_gastos_por_rubro(
        self, finca_id: int, fecha_inicio: str, fecha_fin: str
    ) -> list:
        """Gastos agrupados por rubro en un período."""
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT categoria, SUM(valor_total) as total, COUNT(*) as cantidad "
                "FROM transacciones WHERE finca_id=? AND fecha BETWEEN ? AND ? "
                "AND categoria NOT LIKE 'ingreso_%' "
                "GROUP BY categoria ORDER BY total DESC",
                (finca_id, fecha_inicio, fecha_fin),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_ingresos_por_tipo(
        self, finca_id: int, fecha_inicio: str, fecha_fin: str
    ) -> list:
        """Ingresos agrupados por tipo en un período."""
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT categoria, SUM(valor_total) as total, SUM(cantidad) as cantidad, COUNT(*) as num_transacciones "
                "FROM transacciones WHERE finca_id=? AND fecha BETWEEN ? AND ? "
                "AND categoria LIKE 'ingreso_%' "
                "GROUP BY categoria ORDER BY total DESC",
                (finca_id, fecha_inicio, fecha_fin),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_anios_con_datos(self, finca_id: int) -> list:
        """Retorna lista de años con transacciones."""
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT substr(fecha, 1, 4) as anio FROM transacciones "
                "WHERE finca_id=? ORDER BY anio DESC",
                (finca_id,),
            ).fetchall()
            return [r["anio"] for r in rows]

    def get_transacciones_finca(
        self, finca_id: int, fecha_inicio: Optional[str] = None, fecha_fin: Optional[str] = None
    ) -> list:
        """Obtener transacciones de una finca con filtro opcional por período."""
        with self.get_conn() as conn:
            if fecha_inicio and fecha_fin:
                rows = conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id=? AND fecha BETWEEN ? AND ? ORDER BY fecha DESC",
                    (finca_id, fecha_inicio, fecha_fin),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id=? ORDER BY fecha DESC",
                    (finca_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_resumen_periodo(self, finca_id: int, fecha_inicio: str, fecha_fin: str) -> dict:
        """Resumen financiero de una finca en un período específico."""
        with self.get_conn() as conn:
            ingresos = conn.execute(
                "SELECT COALESCE(SUM(valor_total), 0) as total FROM transacciones "
                "WHERE finca_id=? AND fecha BETWEEN ? AND ? AND categoria LIKE 'ingreso_%'",
                (finca_id, fecha_inicio, fecha_fin),
            ).fetchone()["total"]

            egresos = conn.execute(
                "SELECT COALESCE(SUM(valor_total), 0) as total FROM transacciones "
                "WHERE finca_id=? AND fecha BETWEEN ? AND ? AND categoria NOT LIKE 'ingreso_%'",
                (finca_id, fecha_inicio, fecha_fin),
            ).fetchone()["total"]

            return {
                "ingresos": ingresos,
                "egresos": egresos,
                "margen": ingresos - egresos,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            }


# ==================================================================
# Helper: instancia singleton por defecto
# ==================================================================
# Se crea una instancia global que puede usarse directamente.
# La Mini App puede crear su propia instancia con `Database(db_path=...)`.
db = Database()
