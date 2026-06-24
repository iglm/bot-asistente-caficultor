"""
database.py — Manejo de SQLite para el bot de caficultores
"""

import sqlite3
import logging
from typing import Optional
from config import DB_PATH

log = logging.getLogger(__name__)


class Database:
    """Manejador de base de datos SQLite con WAL mode."""
    
    # Categorías que tienen subcategorías MO e Insumos
    CATEGORIAS_CON_MO_Y_INSUMOS = [
        "instalacion", "arvenses", "fertilizacion",
        "fitosanitario", "sombrio", "otras_labores",
    ]
    # Categorías simples (solo MO, sin subcategoría de insumos)
    CATEGORIAS_SIMPLE = ["recoleccion", "beneficio", "administrativo"]

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def get_conn(self) -> sqlite3.Connection:
        """Obtener conexión SQLite con WAL mode."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    
    def init_db(self):
        """Crear tablas si no existen y asegurar admin por defecto."""
        conn = self.get_conn()
        try:
            conn.executescript("""
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
                
                -- Índices para rendimiento
                CREATE INDEX IF NOT EXISTS idx_transacciones_finca ON transacciones(finca_id);
                CREATE INDEX IF NOT EXISTS idx_transacciones_categoria ON transacciones(categoria);
                CREATE INDEX IF NOT EXISTS idx_transacciones_fecha ON transacciones(fecha);
                CREATE INDEX IF NOT EXISTS idx_lotes_finca ON lotes(finca_id);
            """)
            
            # Asegurar que el admin exista (sin duplicar)
            admin_id = 810796748
            existing = conn.execute("SELECT user_id FROM usuarios WHERE user_id = ?", (admin_id,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO usuarios (user_id, username, nombre, status, admin_id, approved_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    (admin_id, "mateo", "Mateo", "approved", admin_id)
                )
                conn.commit()
                log.info(f"✅ Admin por defecto creado (ID: {admin_id})")
            
            conn.commit()
        finally:
            conn.close()
    
    # ─── Usuarios ───
    
    def upsert_user(self, user_id: int, username: str):
        """Insertar o actualizar usuario."""
        conn = self.get_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO usuarios (user_id, username, status) VALUES (?, ?, 'pending')",
                (user_id, username or ""),
            )
            conn.commit()
        finally:
            conn.close()
    
    def register_user(self, user_id: int, username: str) -> bool:
        """Registrar nuevo usuario. Retorna True si era nuevo, False si ya existía."""
        conn = self.get_conn()
        try:
            cur = conn.execute(
                "INSERT OR IGNORE INTO usuarios (user_id, username, status) VALUES (?, ?, 'pending')",
                (user_id, username or ""),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    
    def get_user_status(self, user_id: int) -> Optional[str]:
        """Obtener status de usuario."""
        conn = self.get_conn()
        try:
            row = conn.execute("SELECT status FROM usuarios WHERE user_id = ?", (user_id,)).fetchone()
            return row["status"] if row else None
        finally:
            conn.close()
    
    def is_approved(self, user_id: int) -> bool:
        return self.get_user_status(user_id) == "approved"
    
    def is_pending(self, user_id: int) -> bool:
        return self.get_user_status(user_id) == "pending"
    
    def approve_user(self, user_id: int, approved_by: int) -> bool:
        """Aprobar usuario. Retorna True si se aprobó, False si no existía."""
        conn = self.get_conn()
        try:
            cur = conn.execute(
                "UPDATE usuarios SET status='approved', admin_id=?, approved_at=CURRENT_TIMESTAMP WHERE user_id=? AND status='pending'",
                (approved_by, user_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    
    def reject_user(self, user_id: int) -> bool:
        """Rechazar usuario."""
        conn = self.get_conn()
        try:
            cur = conn.execute(
                "UPDATE usuarios SET status='rejected' WHERE user_id=? AND status='pending'",
                (user_id,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    
    def get_pending_users(self) -> list:
        """Obtener lista de usuarios pendientes."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT user_id, username, created_at FROM usuarios WHERE status='pending' ORDER BY created_at"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    def get_all_users(self) -> list:
        """Obtener todos los usuarios."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT user_id, username, status, created_at, approved_at FROM usuarios ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_approved_users(self) -> list:
        """Obtener lista de usuarios aprobados."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT user_id, username, created_at, approved_at FROM usuarios WHERE status='approved' ORDER BY approved_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_rejected_users(self) -> list:
        """Obtener lista de usuarios rechazados."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT user_id, username, created_at FROM usuarios WHERE status='rejected' ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def revoke_user(self, user_id: int) -> bool:
        """Revocar acceso de un usuario aprobado (cambia a rejected). Retorna True si se revocó."""
        conn = self.get_conn()
        try:
            cur = conn.execute(
                "UPDATE usuarios SET status='rejected' WHERE user_id=? AND status='approved'",
                (user_id,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def reactivate_user(self, user_id: int) -> bool:
        """Reactivar un usuario rechazado (cambia a pending). Retorna True si se reactivó."""
        conn = self.get_conn()
        try:
            cur = conn.execute(
                "UPDATE usuarios SET status='pending' WHERE user_id=? AND status='rejected'",
                (user_id,),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def delete_all_user_data(self, user_id: int) -> dict:
        """Borrar TODOS los datos de un usuario (transacciones, lotes, fincas).
        Retorna un resumen de lo borrado.
        """
        conn = self.get_conn()
        try:
            # Contar antes de borrar
            trans_count = conn.execute(
                "SELECT COUNT(*) FROM transacciones WHERE finca_id IN (SELECT id FROM fincas WHERE user_id=?)",
                (user_id,)
            ).fetchone()[0]
            lotes_count = conn.execute(
                "SELECT COUNT(*) FROM lotes WHERE finca_id IN (SELECT id FROM fincas WHERE user_id=?)",
                (user_id,)
            ).fetchone()[0]
            fincas_count = conn.execute(
                "SELECT COUNT(*) FROM fincas WHERE user_id=?",
                (user_id,)
            ).fetchone()[0]

            # Borrar en orden (transacciones primero por FK, luego lotes, luego fincas)
            conn.execute(
                "DELETE FROM transacciones WHERE finca_id IN (SELECT id FROM fincas WHERE user_id=?)",
                (user_id,)
            )
            conn.execute(
                "DELETE FROM lotes WHERE finca_id IN (SELECT id FROM fincas WHERE user_id=?)",
                (user_id,)
            )
            conn.execute(
                "DELETE FROM fincas WHERE user_id=?",
                (user_id,)
            )
            conn.commit()

            return {
                "transacciones": trans_count,
                "lotes": lotes_count,
                "fincas": fincas_count,
            }
        finally:
            conn.close()

    # ─── Fincas ───
    
    def create_finca(self, user_id: int, nombre: str, region: str = "", departamento: str = "") -> int:
        """Crear finca. Retorna el ID."""
        conn = self.get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO fincas (user_id, nombre, region, departamento) VALUES (?, ?, ?, ?)",
                (user_id, nombre, region, departamento),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
    
    def get_fincas(self, user_id: int) -> list:
        """Obtener fincas de un usuario."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM fincas WHERE user_id = ? ORDER BY created_at", (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    def get_finca(self, finca_id: int) -> Optional[dict]:
        """Obtener una finca por ID."""
        conn = self.get_conn()
        try:
            row = conn.execute("SELECT * FROM fincas WHERE id = ?", (finca_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_finca_by_id(self, finca_id: int) -> Optional[dict]:
        """Alias de get_finca para compatibilidad."""
        return self.get_finca(finca_id)

    @staticmethod
    def _es_categoria_compuesta(categoria: str) -> bool:
        """Verifica si una categoría tiene subcategorías MO e Insumos."""
        return categoria in Database.CATEGORIAS_CON_MO_Y_INSUMOS

    @staticmethod
    def _es_categoria_simple(categoria: str) -> bool:
        """Verifica si una categoría es simple (solo MO, sin Insumos)."""
        return categoria in Database.CATEGORIAS_SIMPLE

    # ─── Lotes ───
    
    def create_lote(self, finca_id: int, nombre: str, area: float = 0, num_arboles: int = 0, 
                    variedad: str = "", fecha_siembra: str = "") -> int:
        """Crear lote. Retorna el ID."""
        conn = self.get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO lotes (finca_id, nombre, area_hectareas, num_arboles, variedad, fecha_siembra) VALUES (?, ?, ?, ?, ?, ?)",
                (finca_id, nombre, area, num_arboles, variedad, fecha_siembra),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
    
    def get_lotes(self, finca_id: int) -> list:
        """Obtener lotes de una finca."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM lotes WHERE finca_id = ? ORDER BY nombre", (finca_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    # ─── Transacciones ───
    
    def insert_transaccion(self, finca_id: int, categoria: str, fecha: str,
                           labor: str = "", producto: str = "", cantidad: float = 0,
                           unidad: str = "", valor_unitario: float = 0, 
                           valor_total: float = 0, lote_id: int = 0) -> int:
        """Insertar transacción. Retorna el ID."""
        conn = self.get_conn()
        try:
            cur = conn.execute(
                """INSERT INTO transacciones 
                   (finca_id, lote_id, categoria, fecha, labor, producto, cantidad, unidad, valor_unitario, valor_total)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (finca_id, int(lote_id), categoria, fecha, labor, producto, cantidad, unidad, valor_unitario, valor_total),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()
    
    def get_transacciones(self, finca_id: int, categoria: str) -> list:
        """Obtener transacciones de una finca por categoría."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                (finca_id, categoria)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    def get_all_transacciones(self, finca_id: int) -> list:
        """Obtener todas las transacciones de una finca."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM transacciones WHERE finca_id = ? ORDER BY fecha, categoria, id",
                (finca_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_transacciones_por_finca(self, finca_id: int) -> dict:
        """Obtener transacciones organizadas por categoría, normalizando la nomenclatura.
        
        Para categorías compuestas (con MO e Insumos) retorna las dos subcategorías.
        Para categorías simples retorna la categoría tal cual.
        """
        conn = self.get_conn()
        try:
            result = {}

            # Categorías compuestas (MO + Insumos)
            for cat in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                rows_mo = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, f"{cat}_mo")
                ).fetchall()]
                rows_ins = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, f"{cat}_insumos")
                ).fetchall()]
                result[f"{cat}_mo"] = rows_mo
                result[f"{cat}_insumos"] = rows_ins

            # Categorías simples (solo MO, sin insumos)
            for cat in self.CATEGORIAS_SIMPLE:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, cat)
                ).fetchall()]
                result[cat] = rows

            # Ingresos
            for cat_ing in ["ingreso_cps", "ingreso_pasilla", "ingreso_rere"]:
                rows = [dict(r) for r in conn.execute(
                    "SELECT * FROM transacciones WHERE finca_id = ? AND categoria = ? ORDER BY fecha, id",
                    (finca_id, cat_ing)
                ).fetchall()]
                result[cat_ing] = rows

            return result
        finally:
            conn.close()
    
    def get_all_data_for_export(self, finca_id: int) -> dict:
        """Obtener TODOS los datos de una finca organizados para exportar a Excel."""
        conn = self.get_conn()
        try:
            # Lotes
            lotes = [dict(r) for r in conn.execute(
                "SELECT * FROM lotes WHERE finca_id = ? ORDER BY id", (finca_id,)
            ).fetchall()]
            
            # Transacciones por categoría
            data = {"lotes": lotes}
            
            categorias = [
                "ingreso_cps", "ingreso_pasilla", "ingreso_rere",
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
                    (finca_id, cat)
                ).fetchall()]
                data[cat] = rows
            
            return data
        finally:
            conn.close()
    
    def get_resumen_finca(self, finca_id: int) -> dict:
        """Obtener resumen financiero de una finca."""
        conn = self.get_conn()
        try:
            # Total ingresos
            ingresos = conn.execute(
                "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria LIKE 'ingreso_%'",
                (finca_id,)
            ).fetchone()["total"] or 0
            
            # Total egresos
            egresos = conn.execute(
                "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria NOT LIKE 'ingreso_%'",
                (finca_id,)
            ).fetchone()["total"] or 0
            
            # Área total
            area = conn.execute(
                "SELECT SUM(area_hectareas) as total FROM lotes WHERE finca_id = ?",
                (finca_id,)
            ).fetchone()["total"] or 0
            
            # Egresos por categoría
            egresos_cat = {}
            # Categorías con sufijo _mo/_insumos
            for cat in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                total_mo = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ?",
                    (finca_id, f"{cat}_mo")
                ).fetchone()["total"] or 0
                total_ins = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ?",
                    (finca_id, f"{cat}_insumos")
                ).fetchone()["total"] or 0
                egresos_cat[cat] = total_mo + total_ins
            # Categorías sin sufijo (recoleccion, beneficio, administrativo)
            for cat in self.CATEGORIAS_SIMPLE:
                total = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ?",
                    (finca_id, cat)
                ).fetchone()["total"] or 0
                egresos_cat[cat] = total

            # Ingresos por tipo
            ingresos_tipos = {}
            for cat_ing in ["ingreso_cps", "ingreso_pasilla", "ingreso_rere"]:
                total = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ?",
                    (finca_id, cat_ing)
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
        finally:
            conn.close()
