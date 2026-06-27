"""
database/models.py — Base de datos SQLite: conexión, inicialización, helpers y cola de sync.
"""

import sqlite3
import logging
from config import DB_PATH

log = logging.getLogger(__name__)


class DatabaseBase:
    """Mixin base con conexión, inicialización y helpers compartidos."""

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

        # Añadir columna acepto_terminos si no existe (migración)
        try:
            conn.execute("ALTER TABLE usuarios ADD COLUMN acepto_terminos INTEGER DEFAULT 0")
            log.info("✅ Columna acepto_terminos añadida a tabla usuarios")
        except sqlite3.OperationalError:
            pass  # Ya existe

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

                CREATE TABLE IF NOT EXISTS presupuestos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    finca_id INTEGER REFERENCES fincas(id),
                    anio INTEGER NOT NULL,
                    categoria TEXT NOT NULL,
                    monto_planificado REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(finca_id, anio, categoria)
                );

                -- Detalle del presupuesto (líneas por lote/rubro/mes)
                CREATE TABLE IF NOT EXISTS presupuesto_detalle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    presupuesto_id INTEGER REFERENCES presupuestos(id),
                    lote_id INTEGER DEFAULT 0,
                    rubro TEXT NOT NULL,
                    mes INTEGER DEFAULT 0,
                    cantidad_plan REAL DEFAULT 0,
                    unidad TEXT DEFAULT '',
                    valor_unitario REAL DEFAULT 0,
                    valor_total_plan REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Gastos reales ejecutados
                CREATE TABLE IF NOT EXISTS gastos_reales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    finca_id INTEGER REFERENCES fincas(id),
                    lote_id INTEGER DEFAULT 0,
                    fecha TEXT NOT NULL,
                    rubro TEXT NOT NULL,
                    labor TEXT DEFAULT '',
                    insumo TEXT DEFAULT '',
                    cantidad REAL DEFAULT 0,
                    unidad TEXT DEFAULT '',
                    valor_unitario REAL DEFAULT 0,
                    valor_total REAL DEFAULT 0,
                    estado TEXT DEFAULT 'confirmado',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_presupuesto_detalle_presupuesto ON presupuesto_detalle(presupuesto_id);
                CREATE INDEX IF NOT EXISTS idx_gastos_reales_finca ON gastos_reales(finca_id);
                CREATE INDEX IF NOT EXISTS idx_gastos_reales_fecha ON gastos_reales(fecha);

                -- Tabla para cola de sincronización offline
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
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

    @classmethod
    def _es_categoria_compuesta(cls, categoria: str) -> bool:
        """Verifica si una categoría tiene subcategorías MO e Insumos."""
        return categoria in cls.CATEGORIAS_CON_MO_Y_INSUMOS

    @classmethod
    def _es_categoria_simple(cls, categoria: str) -> bool:
        """Verifica si una categoría es simple (solo MO, sin Insumos)."""
        return categoria in cls.CATEGORIAS_SIMPLE

    # ─── Offline Sync Queue ───

    def add_sync_queue(self, action: str, data: dict):
        """Agrega una operación a la cola de sincronización offline."""
        import json
        conn = self.get_conn()
        try:
            conn.execute(
                "INSERT INTO sync_queue (action, data) VALUES (?, ?)",
                (action, json.dumps(data)),
            )
            conn.commit()
            log.info(f"📤 Sincronización en cola: {action}")
        finally:
            conn.close()

    def get_sync_queue(self) -> list:
        """Obtiene todas las operaciones pendientes de sincronización."""
        import json
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM sync_queue ORDER BY created_at"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def process_sync_queue(self):
        """Procesa la cola de sincronización (envía operaciones pendientes)."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM sync_queue ORDER BY created_at"
            ).fetchall()
            for row in rows:
                # Aquí iría la lógica de envío real (API, etc.)
                log.info(f"🔄 Procesando sync_queue ID {row['id']}: {row['action']}")
                conn.execute("DELETE FROM sync_queue WHERE id = ?", (row['id'],))
            conn.commit()
            log.info(f"✅ Cola de sincronización procesada: {len(rows)} items")
        finally:
            conn.close()
