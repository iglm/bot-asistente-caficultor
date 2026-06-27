"""
database/crud_fincas_lotes.py — Operaciones CRUD de fincas y lotes.
"""

from typing import Optional


class FincasLotesMixin:
    """Mixin con operaciones de fincas y lotes."""

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

    def get_lote_by_id(self, lote_id: int) -> Optional[dict]:
        """Obtener un lote por su ID."""
        conn = self.get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM lotes WHERE id = ?", (lote_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
