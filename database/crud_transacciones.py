"""
database/crud_transacciones.py — Operaciones CRUD de ingresos, costos y transacciones.
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)


class TransaccionesMixin:
    """Mixin con operaciones de transacciones e indicadores técnicos."""

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

    def get_transacciones_por_periodo(self, finca_id: int, fecha_inicio: str, fecha_fin: str) -> list:
        """Obtiene transacciones en un rango de fechas."""
        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM transacciones WHERE finca_id=? AND fecha BETWEEN ? AND ? ORDER BY fecha",
                (finca_id, fecha_inicio, fecha_fin)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_resumen_por_periodo(self, finca_id: int, fecha_inicio: str, fecha_fin: str) -> dict:
        """Obtiene resumen financiero de una finca en un período específico."""
        conn = self.get_conn()
        try:
            # Total ingresos en el período
            ingresos = conn.execute(
                "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria LIKE 'ingreso_%' AND fecha BETWEEN ? AND ?",
                (finca_id, fecha_inicio, fecha_fin)
            ).fetchone()["total"] or 0

            # Total egresos en el período
            egresos = conn.execute(
                "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria NOT LIKE 'ingreso_%' AND fecha BETWEEN ? AND ?",
                (finca_id, fecha_inicio, fecha_fin)
            ).fetchone()["total"] or 0

            # Egresos por categoría en el período
            egresos_cat = {}
            for cat in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                total_mo = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ? AND fecha BETWEEN ? AND ?",
                    (finca_id, f"{cat}_mo", fecha_inicio, fecha_fin)
                ).fetchone()["total"] or 0
                total_ins = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ? AND fecha BETWEEN ? AND ?",
                    (finca_id, f"{cat}_insumos", fecha_inicio, fecha_fin)
                ).fetchone()["total"] or 0
                egresos_cat[cat] = total_mo + total_ins
            for cat in self.CATEGORIAS_SIMPLE:
                total = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ? AND fecha BETWEEN ? AND ?",
                    (finca_id, cat, fecha_inicio, fecha_fin)
                ).fetchone()["total"] or 0
                egresos_cat[cat] = total

            # Ingresos por tipo en el período
            ingresos_tipos = {}
            for cat_ing in ["ingreso_cps", "ingreso_pasilla"]:
                total = conn.execute(
                    "SELECT SUM(valor_total) as total FROM transacciones WHERE finca_id = ? AND categoria = ? AND fecha BETWEEN ? AND ?",
                    (finca_id, cat_ing, fecha_inicio, fecha_fin)
                ).fetchone()["total"] or 0
                ingresos_tipos[cat_ing] = total

            return {
                "ingresos": ingresos,
                "egresos": egresos,
                "margen": ingresos - egresos,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "egresos_por_categoria": egresos_cat,
                "ingresos_por_tipo": ingresos_tipos,
            }
        finally:
            conn.close()

    def get_resumen_semanal(self, finca_id: int, año: int, semana: int) -> dict:
        """Resumen de una semana específica (ISO week)."""
        from datetime import datetime, timedelta
        # Calcular lunes de la semana ISO
        # Usar el 4 de enero como referencia ISO
        jan4 = datetime(año, 1, 4)
        # Día de la semana (lunes=0)
        jan4_weekday = (jan4.weekday() + 1) % 7  # Lunes=0
        # Primer día de semana 1
        week1_start = jan4 - timedelta(days=jan4_weekday)
        # Fecha inicio de la semana solicitada
        inicio = week1_start + timedelta(weeks=semana - 1)
        fin = inicio + timedelta(days=6)
        fecha_inicio = inicio.strftime("%Y-%m-%d")
        fecha_fin = fin.strftime("%Y-%m-%d")
        return self.get_resumen_por_periodo(finca_id, fecha_inicio, fecha_fin)

    def get_resumen_mensual(self, finca_id: int, año: int, mes: int) -> dict:
        """Resumen de un mes específico."""
        fecha_inicio = f"{año}-{mes:02d}-01"
        if mes == 12:
            fecha_fin = f"{año + 1}-01-01"
        else:
            fecha_fin = f"{año}-{mes + 1:02d}-01"
        from datetime import datetime, timedelta
        # Restar 1 día para llegar al último día del mes
        fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d") - timedelta(days=1)
        fecha_fin = fin_dt.strftime("%Y-%m-%d")
        return self.get_resumen_por_periodo(finca_id, fecha_inicio, fecha_fin)

    def get_resumen_anual(self, finca_id: int, año: int) -> dict:
        """Resumen de un año específico."""
        fecha_inicio = f"{año}-01-01"
        fecha_fin = f"{año}-12-31"
        return self.get_resumen_por_periodo(finca_id, fecha_inicio, fecha_fin)

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

    def get_transacciones_finca(self, finca_id: int) -> list:
        """Obtener todas las transacciones de una finca (alias simple).

        Retorna lista de dicts, vacía si no hay transacciones.
        """
        return self.get_all_transacciones(finca_id)

    def simular_datos_finca(self, finca_id: int):
        """Simula datos de ejemplo para generar un Excel con contenido.

        Solo inserta si no hay transacciones reales.
        Usa datos realistas de costos cafeteros colombianos.
        """
        import random
        from datetime import datetime

        # No simular si ya hay datos reales
        if self.get_all_transacciones(finca_id):
            return

        lotes = self.get_lotes(finca_id)
        if not lotes:
            return

        anio = datetime.now().year

        for lote in lotes:
            lote_id = lote["id"]

            # Simular ingresos (cosecha principal Oct-Dic)
            for mes in [10, 11, 12]:
                kg = random.randint(200, 800)
                precio = random.randint(20000, 28000)
                self.insert_transaccion(
                    finca_id=finca_id, lote_id=lote_id,
                    categoria="ingreso_cps",
                    fecha=f"{anio}-{mes:02d}-15",
                    labor="Venta cosecha",
                    producto="CPS",
                    cantidad=kg, unidad="kg",
                    valor_unitario=precio,
                    valor_total=kg * precio,
                )

            # Simular costos por categoría
            categorias = [
                ("recoleccion", "Recolección", "Jornal", 55000),
                ("fertilizacion_mo", "Fertilización", "Jornal", 55000),
                ("fertilizacion_insumos", "Fertilizante NPK", "kg", 3200),
                ("arvenses_mo", "Control arvenses", "Jornal", 55000),
                ("administrativo", "Administración", "mes", 500000),
            ]

            for cat, labor, unidad, valor_unit in categorias:
                for mes in [3, 6, 9]:
                    cant = random.randint(2, 10)
                    self.insert_transaccion(
                        finca_id=finca_id, lote_id=lote_id,
                        categoria=cat,
                        fecha=f"{anio}-{mes:02d}-10",
                        labor=labor,
                        producto=labor,
                        cantidad=cant, unidad=unidad,
                        valor_unitario=valor_unit,
                        valor_total=cant * valor_unit,
                    )

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
            for cat_ing in ["ingreso_cps", "ingreso_pasilla"]:
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
                    (finca_id, cat)
                ).fetchall()]
                data[cat] = rows

            return data
        finally:
            conn.close()

    def get_resumen_finca(self, finca_id: int) -> dict:
        """Obtener resumen financiero de una finca usando GROUP BY."""
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

            # Egresos e ingresos por categoría en UNA sola query GROUP BY
            rows = conn.execute(
                """SELECT categoria, SUM(valor_total) as total, COUNT(*) as cantidad
                   FROM transacciones WHERE finca_id = ?
                   GROUP BY categoria""",
                (finca_id,)
            ).fetchall()

            # Construir dicts a partir del resultado GROUP BY
            egresos_cat = {}
            ingresos_tipos = {}
            for r in rows:
                cat = r["categoria"]
                total = r["total"] or 0
                if cat.startswith("ingreso_"):
                    ingresos_tipos[cat] = total
                else:
                    # Agrupar categorías compuestas (con _mo / _insumos) bajo su nombre base
                    if cat.endswith("_mo"):
                        base = cat[:-3]
                        egresos_cat[base] = egresos_cat.get(base, 0) + total
                    elif cat.endswith("_insumos"):
                        base = cat[:-8]
                        egresos_cat[base] = egresos_cat.get(base, 0) + total
                    else:
                        egresos_cat[cat] = egresos_cat.get(cat, 0) + total

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

    # ─── Indicadores Técnicos ───

    @staticmethod
    def _lote_es_productivo(lote: dict) -> bool:
        """Determina si un lote es productivo (tiene árboles y fecha de siembra)."""
        return bool(lote.get("num_arboles", 0) and lote.get("fecha_siembra", ""))

    def _get_total_insumos_cantidad_convertida(self, finca_id: int) -> dict:
        """Obtiene la cantidad total de insumos convertida a unidad estándar.

        Retorna:
            dict con:
            - total_kg: cantidad total en kg equivalentes (sólidos + bultos)
            - total_litros: cantidad total en L equivalentes (líquidos)
            - total_estandar: cantidad total en kg (todo convertido a kg)
        """
        from config import CONVERSION_A_KG, CONVERSION_A_LITROS, UNIDADES_SOLIDOS, UNIDADES_LIQUIDOS

        conn = self.get_conn()
        try:
            rows = conn.execute(
                "SELECT cantidad, unidad FROM transacciones WHERE finca_id = ? AND categoria LIKE '%_insumos'",
                (finca_id,)
            ).fetchall()
        finally:
            conn.close()

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
                # Sin unidad definida, asumir 1:1 a kg
                total_kg += cantidad

        return {
            'total_kg': total_kg,
            'total_litros': total_litros,
            'total_estandar': total_kg,  # para comparaciones, usar kg
        }

    def _get_total_ingresos(self, finca_id: int) -> float:
        """Obtiene el total de ingresos de una finca."""
        conn = self.get_conn()
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones WHERE finca_id = ? AND categoria LIKE 'ingreso_%'",
                (finca_id,)
            ).fetchone()
            return row[0] if row else 0.0
        finally:
            conn.close()

    def _get_costos_por_tipo(self, finca_id: int, tipo: str) -> float:
        """Obtiene costos por tipo: 'mo' o 'insumos'.

        MO: categorías que terminan en _mo + categorías simples (recoleccion, beneficio, administrativo)
        Insumos: categorías que terminan en _insumos
        """
        conn = self.get_conn()
        try:
            if tipo == 'mo':
                # Sumar todas las categorías _mo
                total = 0.0
                for cat_base in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                    row = conn.execute(
                        "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones WHERE finca_id = ? AND categoria = ?",
                        (finca_id, f"{cat_base}_mo")
                    ).fetchone()
                    total += row[0] if row else 0.0
                # Sumar categorías simples (recoleccion, beneficio, administrativo)
                for cat in self.CATEGORIAS_SIMPLE:
                    row = conn.execute(
                        "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones WHERE finca_id = ? AND categoria = ?",
                        (finca_id, cat)
                    ).fetchone()
                    total += row[0] if row else 0.0
                return total
            elif tipo == 'insumos':
                total = 0.0
                for cat_base in self.CATEGORIAS_CON_MO_Y_INSUMOS:
                    row = conn.execute(
                        "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones WHERE finca_id = ? AND categoria = ?",
                        (finca_id, f"{cat_base}_insumos")
                    ).fetchone()
                    total += row[0] if row else 0.0
                return total
            return 0.0
        finally:
            conn.close()

    def _get_kg_producidos(self, finca_id: int) -> float:
        """Obtiene kg totales producidos (de transacciones ingreso_cps e ingreso_pasilla)."""
        conn = self.get_conn()
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM(cantidad), 0) FROM transacciones WHERE finca_id = ? AND categoria IN ('ingreso_cps', 'ingreso_pasilla')",
                (finca_id,)
            ).fetchone()
            return row[0] if row else 0.0
        finally:
            conn.close()

    def _get_total_jornales(self, finca_id: int) -> float:
        """Obtiene total de jornales registrados en la finca.

        Busca transacciones de categorías MO donde unidad sea 'día', 'jornal' o vacío (asume jornal).
        """
        conn = self.get_conn()
        try:
            # Categorías MO: todas las _mo + categorías simples
            categorias_mo = [f"{c}_mo" for c in self.CATEGORIAS_CON_MO_Y_INSUMOS] + list(self.CATEGORIAS_SIMPLE)
            placeholders = ",".join("?" for _ in categorias_mo)
            row = conn.execute(
                f"SELECT COALESCE(SUM(cantidad), 0) FROM transacciones "
                f"WHERE finca_id = ? AND categoria IN ({placeholders}) "
                f"AND (unidad IN ('día', 'dia', 'jornal', 'jornales', '') OR unidad IS NULL)",
                (finca_id, *categorias_mo)
            ).fetchone()
            return row[0] if row else 0.0
        finally:
            conn.close()

    def get_indicadores_tecnicos(self, finca_id: int) -> dict:
        """Calcula todos los indicadores técnicos de la finca.

        Basado en metodología estándar del sector.
        Incluye datos de referencia FNC/FEPCafé 2024 para comparación.
        """
        from config import FNC_INDICADORES

        # Obtener área total y productiva
        conn = self.get_conn()
        try:
            lotes = [dict(r) for r in conn.execute(
                "SELECT * FROM lotes WHERE finca_id = ?", (finca_id,)
            ).fetchall()]
        finally:
            conn.close()

        area_total = sum(l['area_hectareas'] for l in lotes)
        area_productiva = sum(l['area_hectareas'] for l in lotes if self._lote_es_productivo(l))

        # Obtener datos financieros y productivos
        ingresos = self._get_total_ingresos(finca_id)
        costos_mo = self._get_costos_por_tipo(finca_id, 'mo')
        costos_insumos = self._get_costos_por_tipo(finca_id, 'insumos')
        costos_total = costos_mo + costos_insumos
        kg_producidos = self._get_kg_producidos(finca_id)
        total_jornales = self._get_total_jornales(finca_id)
        insumos_cant = self._get_total_insumos_cantidad_convertida(finca_id)

        # Calcular indicadores con división segura
        return {
            'area_total': area_total,
            'area_productiva': area_productiva,
            'ingresos_totales': ingresos,
            'costos_mo': costos_mo,
            'costos_insumos': costos_insumos,
            'costos_total': costos_total,
            'kg_producidos': kg_producidos,
            'total_jornales': total_jornales,
            'productividad': kg_producidos / area_total if area_total > 0 else 0,
            'rendimiento': kg_producidos / area_productiva if area_productiva > 0 else 0,
            'jornales_por_ha': total_jornales / area_total if area_total > 0 else 0,
            'costo_mo_por_ha': costos_mo / area_total if area_total > 0 else 0,
            'costo_insumos_por_ha': costos_insumos / area_total if area_total > 0 else 0,
            'costo_total_por_ha': costos_total / area_total if area_total > 0 else 0,
            'costo_por_kilo': costos_total / kg_producidos if kg_producidos > 0 else 0,
            'margen_por_ha': (ingresos - costos_total) / area_total if area_total > 0 else 0,
            'precio_venta_promedio': ingresos / kg_producidos if kg_producidos > 0 else 0,
            'eficiencia_mo': kg_producidos / total_jornales if total_jornales > 0 else 0,
            # Nuevos indicadores con unidades
            'costo_insumos_por_kg_cps': costos_insumos / kg_producidos if kg_producidos > 0 else 0,
            'costo_mo_por_kg_cps': costos_mo / kg_producidos if kg_producidos > 0 else 0,
            'insumos_por_ha': insumos_cant['total_estandar'] / area_total if area_total > 0 else 0,
            'insumos_total_kg': insumos_cant['total_estandar'],
            'insumos_total_litros': insumos_cant['total_litros'],
            'eficiencia_insumos': kg_producidos / insumos_cant['total_estandar'] if insumos_cant['total_estandar'] > 0 else 0,
            # Comparación con promedios FNC/FEPCafé 2024
            'fnc_productividad_ha': FNC_INDICADORES['productividad_ha'],
            'fnc_costo_ha': FNC_INDICADORES['costo_ha'],
            'fnc_rendimiento_ha': FNC_INDICADORES['rendimiento_ha'],
            'fnc_precio_venta_promedio': FNC_INDICADORES['precio_venta_promedio'],
            'fnc_costo_produccion_kilo': FNC_INDICADORES['costo_produccion_kilo'],
            'fnc_margen_ha': FNC_INDICADORES['margen_ha'],
            'fnc_area_promedio': FNC_INDICADORES['area_promedio'],
        }
