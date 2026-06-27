"""
database/crud_usuarios.py — Operaciones CRUD de usuarios / administración.
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)


class UsuariosMixin:
    """Mixin con operaciones de usuarios."""

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

    def get_user(self, user_id: int) -> Optional[dict]:
        """Obtener todos los datos de un usuario.

        Retorna dict con todos los campos o None si no existe.
        """
        conn = self.get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE user_id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def aceptar_terminos(self, user_id: int) -> bool:
        """Marca que el usuario aceptó los términos legales.
        Retorna True si se actualizó, False si no existía.
        """
        conn = self.get_conn()
        try:
            cur = conn.execute(
                "UPDATE usuarios SET acepto_terminos=1 WHERE user_id=?",
                (user_id,),
            )
            conn.commit()
            return cur.rowcount > 0
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
