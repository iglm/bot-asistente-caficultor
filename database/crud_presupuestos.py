"""
database/crud_presupuestos.py — Operaciones CRUD de presupuestos y ejecución.
"""

import logging

log = logging.getLogger(__name__)


class PresupuestosMixin:
    """Mixin con operaciones de presupuestos y ejecución presupuestal."""

    # ─── Presupuestos ───

    def guardar_presupuesto(self, finca_id: int, anio: int, datos: dict):
        """Guarda o actualiza el presupuesto para un año.

        Args:
            finca_id: ID de la finca
            anio: Año del presupuesto
            datos: Dict {categoria: monto_planificado}
        """
        conn = self.get_conn()
        try:
            for categoria, monto in datos.items():
                conn.execute(
                    """INSERT INTO presupuestos (finca_id, anio, categoria, monto_planificado)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(finca_id, anio, categoria)
                       DO UPDATE SET monto_planificado = excluded.monto_planificado""",
                    (finca_id, anio, categoria, monto or 0),
                )
            conn.commit()
            log.info(f"✅ Presupuesto guardado finca={finca_id} año={anio}")
        finally:
            conn.close()

    def get_presupuesto(self, finca_id: int, anio: int) -> list:
        """Obtener presupuesto planificado para un año."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM presupuestos WHERE finca_id = ? AND anio = ? ORDER BY categoria",
                (finca_id, anio),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_presupuesto_anios(self, finca_id: int) -> list:
        """Obtener lista de años disponibles de presupuesto."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT DISTINCT anio FROM presupuestos WHERE finca_id = ? ORDER BY anio DESC",
                (finca_id,),
            ).fetchall()
            return [r["anio"] for r in rows]
        finally:
            conn.close()

    def get_anios_con_datos(self, finca_id: int) -> list:
        """Obtiene años con transacciones para una finca (orden descendente).

        Útil para calcular presupuesto sugerido cuando no hay presupuesto guardado.
        """
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT DISTINCT CAST(SUBSTR(fecha, 1, 4) AS INTEGER) as anio "
                "FROM transacciones WHERE finca_id = ? AND fecha != '' "
                "ORDER BY anio DESC",
                (finca_id,),
            ).fetchall()
            return [r["anio"] for r in rows if r["anio"]]
        finally:
            conn.close()

    def delete_presupuesto(self, finca_id: int, anio: int):
        """Eliminar presupuesto de un año."""
        conn = self.get_conn()
        try:
            conn.execute(
                "DELETE FROM presupuestos WHERE finca_id = ? AND anio = ?",
                (finca_id, anio),
            )
            conn.commit()
        finally:
            conn.close()

    def get_ejecucion_presupuesto(self, finca_id: int, anio: int) -> dict:
        """Compara presupuesto planificado vs ejecutado real.

        Para cada categoría de la estructura de costos del sector, calcula:
        - monto_planificado (de la tabla presupuestos)
        - monto_ejecutado (suma de transacciones del año)
        - diferencia
        - % de ejecución

        Mapping de categorías del sector a categorías DB:
        - Recolección -> recoleccion
        - Fertilización -> fertilizacion_mo + fertilizacion_insumos
        - Gastos Admin -> administrativo
        - Arvenses -> arvenses_mo + arvenses_insumos
        - Beneficio -> beneficio
        - Renovación -> instalacion_mo + instalacion_insumos
        - Fitosanitarios -> fitosanitario_mo + fitosanitario_insumos
        - Otras labores -> otras_labores_mo + otras_labores_insumos

        Returns:
            dict con keys:
            - categorias: list de dicts con categoria, monto_planificado, monto_ejecutado, diferencia, pct_ejecucion
            - total_planificado: float
            - total_ejecutado: float
            - total_diferencia: float
        """
        conn = self.get_conn()
        try:
            fecha_like = f"{anio}-%"

            # Mapeo de categorías del sector a categorías DB
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
                # Obtener monto planificado
                row = conn.execute(
                    "SELECT monto_planificado FROM presupuestos WHERE finca_id = ? AND anio = ? AND categoria = ?",
                    (finca_id, anio, cat_id),
                ).fetchone()
                monto_planificado = row["monto_planificado"] if row else 0.0

                # Obtener monto ejecutado (suma de transacciones)
                monto_ejecutado = 0.0
                for cat_db in categorias_db:
                    row_ej = conn.execute(
                        "SELECT COALESCE(SUM(valor_total), 0) as total FROM transacciones WHERE finca_id = ? AND categoria = ? AND fecha LIKE ?",
                        (finca_id, cat_db, fecha_like),
                    ).fetchone()
                    monto_ejecutado += row_ej["total"] if row_ej else 0.0

                diferencia = monto_ejecutado - monto_planificado
                pct_ejecucion = (monto_ejecutado / monto_planificado * 100) if monto_planificado > 0 else (0 if monto_ejecutado == 0 else 100)

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
        finally:
            conn.close()

    # ─── Presupuesto Detalle ───

    def guardar_detalle_presupuesto(self, presupuesto_id: int, detalle: dict):
        """Guarda una línea de detalle del presupuesto."""
        conn = self.get_conn()
        try:
            conn.execute(
                """INSERT INTO presupuesto_detalle
                   (presupuesto_id, lote_id, rubro, mes, cantidad_plan, unidad, valor_unitario, valor_total_plan)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    presupuesto_id,
                    detalle.get("lote_id", 0),
                    detalle["rubro"],
                    detalle.get("mes", 0),
                    detalle.get("cantidad_plan", 0),
                    detalle.get("unidad", ""),
                    detalle.get("valor_unitario", 0),
                    detalle.get("valor_total_plan", 0),
                ),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def get_ejecucion_por_periodo(self, finca_id: int, fecha_inicio: str, fecha_fin: str) -> dict:
        """Ejecución presupuestal en un rango de fechas.
        Compara lo planificado vs lo ejecutado en un período específico.
        """
        conn = self.get_conn()
        try:
            # Obtener ejecutado real desde transacciones para el período
            rows = conn.execute(
                """SELECT categoria, SUM(valor_total) as total
                   FROM transacciones
                   WHERE finca_id = ? AND fecha BETWEEN ? AND ?
                   GROUP BY categoria""",
                (finca_id, fecha_inicio, fecha_fin),
            ).fetchall()

            ejecutado_por_categoria = {}
            total_ejecutado = 0.0
            for r in rows:
                cat = r["categoria"]
                total = r["total"] or 0
                # Normalizar: agrupar _mo y _insumos bajo su categoría base
                if cat.endswith("_mo"):
                    base = cat[:-3]
                    ejecutado_por_categoria[base] = ejecutado_por_categoria.get(base, 0) + total
                elif cat.endswith("_insumos"):
                    base = cat[:-8]
                    ejecutado_por_categoria[base] = ejecutado_por_categoria.get(base, 0) + total
                else:
                    ejecutado_por_categoria[cat] = ejecutado_por_categoria.get(cat, 0) + total
                total_ejecutado += total

            return {
                "ejecutado_por_categoria": ejecutado_por_categoria,
                "total_ejecutado": total_ejecutado,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
            }
        finally:
            conn.close()

    def get_gastos_por_rubro(self, finca_id: int, fecha_inicio: str, fecha_fin: str) -> list:
        """Gastos agrupados por rubro en un período.
        Retorna lista de dicts con rubro y total.
        """
        conn = self.get_conn()
        try:
            rows = conn.execute(
                """SELECT rubro, SUM(valor_total) as total
                   FROM gastos_reales
                   WHERE finca_id = ? AND fecha BETWEEN ? AND ?
                   GROUP BY rubro
                   ORDER BY total DESC""",
                (finca_id, fecha_inicio, fecha_fin),
            ).fetchall()
            return [{"rubro": r["rubro"], "total": r["total"] or 0} for r in rows]
        finally:
            conn.close()
