"""
database/__init__.py — Re-exporta Database y todo lo necesario para compatibilidad.
El import existente 'from database import Database' sigue funcionando.
"""

from database.models import DatabaseBase
from database.crud_usuarios import UsuariosMixin
from database.crud_fincas_lotes import FincasLotesMixin
from database.crud_transacciones import TransaccionesMixin
from database.crud_presupuestos import PresupuestosMixin


class Database(
    DatabaseBase,
    UsuariosMixin,
    FincasLotesMixin,
    TransaccionesMixin,
    PresupuestosMixin,
):
    """Manejador de base de datos SQLite con WAL mode.

    Hereda métodos de los mixins especializados:
    - DatabaseBase: __init__, get_conn, init_db, helpers, sync_queue
    - UsuariosMixin: upsert_user, register_user, approve/reject, etc.
    - FincasLotesMixin: create_finca, get_fincas, create_lote, get_lotes, etc.
    - TransaccionesMixin: insert_transaccion, resúmenes, indicadores técnicos
    - PresupuestosMixin: guardar_presupuesto, ejecución, detalle
    """
