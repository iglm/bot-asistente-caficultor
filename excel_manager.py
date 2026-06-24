"""
Manejador de Excel para el Bot Asistente Caficultor.
Carga el template, llena SOLO las hojas de datos con información de SQLite,
y guarda manteniendo fórmulas intactas.

VERSIÓN DINÁMICA: En lugar de extender fórmulas hasta límites fijos,
crea filas según los datos reales usando copy/paste de fórmulas.
"""
import os
import re
import shutil
import logging
from copy import copy
from datetime import datetime
from typing import Optional

import openpyxl
from openpyxl.chart import BarChart, PieChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint
from openpyxl.drawing.fill import PatternFillProperties, ColorChoice
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# Mapeo de categorías DB → hojas Excel y sus configuraciones
HOJA_CONFIG = {
    # (hoja, columnas_mo, columnas_insumos, columna_inicio_insumos)
    # None para columnas significa que esa sección no aplica
    "Instalacion de Cafe": {
        "mo_cols": {"start": "A", "end": "F", "campos": ["lote", "fecha", "labor", "cantidad", "valor_unitario", "valor_total_formula"]},
        "insumos_cols": {"start": "H", "end": "L", "campos": ["fecha", "producto", "cantidad", "valor_unitario", "valor_total_formula"]},
        "categorias_mo": ["instalacion_mo"],
        "categorias_insumos": ["instalacion_insumos"],
    },
    "Control de arvenses": {
        "mo_cols": {"start": "A", "end": "F", "campos": ["lote", "fecha", "labor", "cantidad", "valor_unitario", "valor_total_formula"]},
        "insumos_cols": {"start": "H", "end": "M", "campos": ["fecha", "labor", "producto", "cantidad", "valor_unitario", "valor_total_formula"]},
        "categorias_mo": ["arvenses_mo"],
        "categorias_insumos": ["arvenses_insumos"],
    },
    "Fertilizacion": {
        "mo_cols": {"start": "A", "end": "F", "campos": ["lote", "fecha", "labor", "cantidad", "valor_unitario", "valor_total_formula"]},
        "insumos_cols": {"start": "H", "end": "L", "campos": ["fecha", "producto", "cantidad", "valor_unitario", "valor_total_formula"]},
        "categorias_mo": ["fertilizacion_mo"],
        "categorias_insumos": ["fertilizacion_insumos"],
    },
    "Control Fitosanitario": {
        "mo_cols": {"start": "A", "end": "F", "campos": ["lote", "fecha", "labor", "cantidad", "valor_unitario", "valor_total_formula"]},
        "insumos_cols": {"start": "H", "end": "M", "campos": ["fecha", "labor", "producto", "cantidad", "valor_unitario", "valor_total_formula"]},
        "categorias_mo": ["fitosanitario_mo"],
        "categorias_insumos": ["fitosanitario_insumos"],
    },
    "Regulacion de sombrio": {
        "mo_cols": {"start": "A", "end": "F", "campos": ["lote", "fecha", "labor", "cantidad", "valor_unitario", "valor_total_formula"]},
        "insumos_cols": {"start": "H", "end": "L", "campos": ["fecha", "producto", "cantidad", "valor_unitario", "valor_total_formula"]},
        "categorias_mo": ["sombrio_mo"],
        "categorias_insumos": ["sombrio_insumos"],
    },
    "Otras Labores": {
        "mo_cols": {"start": "A", "end": "F", "campos": ["lote", "fecha", "labor", "cantidad", "valor_unitario", "valor_total_formula"]},
        "insumos_cols": {"start": "H", "end": "L", "campos": ["fecha", "producto", "cantidad", "valor_unitario", "valor_total_formula"]},
        "categorias_mo": ["otras_labores_mo"],
        "categorias_insumos": ["otras_labores_insumos"],
    },
    "Recoleccion": {
        # Recolección es especial: A=Fecha, B=Labor, C=Kilos, D=V.Unitario(formula=E/C), E=V.Total
        "columnas_especiales": ["fecha", "labor", "cantidad", "valor_unitario_formula", "valor_total"],
        "categorias": ["recoleccion"],
    },
    "Beneficio": {
        # Beneficio: A=Fecha, B=Labor, C=Jornales, D=V.Unitario, E=V.Total(formula=D*C)
        "columnas_especiales": ["fecha", "labor", "cantidad", "valor_unitario", "valor_total_formula"],
        "categorias": ["beneficio"],
    },
    "Gastos Administrativos": {
        # Gastos Admin: A=Fecha, B=Gasto, C=V.Total
        "columnas_especiales": ["fecha", "labor", "valor_total"],
        "categorias": ["administrativo"],
    },
}

# Hoja ID lotes tiene Tabla4 — no usar insert_rows que la rompe,
# mejor extender filas manualmente
HOJA_LOTES_START_ROW = 2
HOJA_LOTES_SUBTOTAL_ROW = 17
HOJA_LOTES_TEMPLATE_ROWS = 15  # filas 2-16

# Para hojas con datos desde fila 3 hasta subtotal en fila 20
HOJA_COSTOS_START_ROW = 3
HOJA_COSTOS_SUBTOTAL_ROW = 20
HOJA_COSTOS_TEMPLATE_ROWS = 17  # filas 3-19


class ExcelManager:
    """Manejador del template Excel. Solo llena datos, mantiene fórmulas."""

    def __init__(self, template_path: str):
        self.template_path = template_path

    def _validar_template(self):
        """Verifica que el template exista."""
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(
                f"Template Excel no encontrado: {self.template_path}"
            )

    # ------------------------------------------------------------------
    # Helpers para copiar fórmulas y formato (dinámicos)
    # ------------------------------------------------------------------

    @staticmethod
    def _ajustar_referencias_fila(formula: str, fila_origen: int, fila_destino: int) -> str:
        """
        Ajusta las referencias de celda en una fórmula de fila_origen a fila_destino.
        Ejemplo: '=IFERROR(F3/D3, 0)' con origen=3, destino=10 → '=IFERROR(F10/D10, 0)'
        Solo reemplaza referencias que apuntan EXACTAMENTE a fila_origen.
        """
        if fila_origen == fila_destino or not formula or not formula.startswith("="):
            return formula

        # Expresión regular: letras de columna (1-3) seguidas de dígitos de fila
        def _reemplazar(match):
            col = match.group(1)
            row = int(match.group(2))
            if row == fila_origen:
                return f"{col}{fila_destino}"
            return match.group(0)

        return re.sub(r'([A-Z]{1,3})(\d+)', _reemplazar, formula)

    @staticmethod
    def _copiar_estilo_celda(celda_origen, celda_destino):
        """Copia el formato (bordes, fuente, relleno, alineación, formato núm.) de una celda a otra."""
        if not celda_origen or not celda_destino:
            return
        try:
            if celda_origen.has_style:
                celda_destino.font = copy(celda_origen.font)
                celda_destino.border = copy(celda_origen.border)
                celda_destino.fill = copy(celda_origen.fill)
                celda_destino.number_format = copy(celda_origen.number_format)
                celda_destino.protection = copy(celda_origen.protection)
                celda_destino.alignment = copy(celda_origen.alignment)
        except Exception:
            pass  # Ignorar errores de copia de estilo (ej. fill inválido)

    @staticmethod
    def _copiar_formula_fila(ws, fila_origen: int, fila_destino: int, max_col: int):
        """
        Copia las fórmulas de fila_origen a fila_destino, ajustando referencias
        de celda. Preserva formato de todas las celdas.
        """
        for col in range(1, max_col + 1):
            celda_origen = ws.cell(row=fila_origen, column=col)
            celda_destino = ws.cell(row=fila_destino, column=col)

            # Copiar valor/fórmula ajustada
            val = celda_origen.value
            if val is not None:
                if isinstance(val, str) and val.startswith("="):
                    celda_destino.value = ExcelManager._ajustar_referencias_fila(
                        val, fila_origen, fila_destino
                    )
                elif isinstance(val, str):
                    # Copiar texto literal
                    celda_destino.value = val
                # No copiar valores numéricos/fechas — esos van con datos reales

            # Copiar formato
            ExcelManager._copiar_estilo_celda(celda_origen, celda_destino)

    def _asegurar_filas_suficientes(
        self, ws, data_start_row: int, subtotal_row_original: int,
        num_needed: int, template_rows: int, max_col: int
    ) -> tuple:
        """
        Asegura que haya suficientes filas de datos entre data_start_row y el subtotal.
        
        Args:
            ws: Worksheet
            data_start_row: Primera fila de datos (2 o 3)
            subtotal_row_original: Fila del subtotal en el template (17 o 20)
            num_needed: Número de filas de datos necesarias
            template_rows: Cuántas filas de datos tiene el template
            max_col: Número máximo de columnas a copiar
        
        Returns:
            tuple: (nuevo_subtotal_row, last_data_row)
        """
        if num_needed <= template_rows:
            # Suficientes filas en el template — solo devolver info
            last_data_row = data_start_row + num_needed - 1
            return subtotal_row_original, last_data_row

        # Necesitamos insertar filas
        rows_to_add = num_needed - template_rows
        last_existing_data = data_start_row + template_rows - 1  # ej: 19
        new_last_data = data_start_row + num_needed - 1  # ej: data_start + N - 1

        # Insertar filas justo después de la última fila de datos existente
        # (y antes del subtotal)
        ws.insert_rows(last_existing_data + 1, rows_to_add)

        # El subtotal se movió hacia abajo
        new_subtotal_row = subtotal_row_original + rows_to_add

        # Copiar fórmulas desde la primera fila de datos a las nuevas filas
        source_row = data_start_row
        for i in range(rows_to_add):
            target_row = last_existing_data + 1 + i
            self._copiar_formula_fila(ws, source_row, target_row, max_col)

        # Actualizar referencia de tabla Excel si existe (ID lotes)
        # ws.tables devuelve TableList (dict-like) con objetos Table como valores
        # En openpyxl 3.1.5, items() devuelve (name, Table) correctamente
        try:
            if ws.tables and "Tabla4" in ws.tables:
                table = ws.tables["Tabla4"]
                if hasattr(table, "ref"):
                    table_ref = table.ref
                    # ref format: A1:F17 → cambiar F17 a F(new_subtotal_row)
                    match = re.match(r'^([A-Z]+)(\d+):([A-Z]+)(\d+)$', table_ref)
                    if match:
                        col1, _, col2, _ = match.groups()
                        new_ref = f"{col1}{data_start_row-1}:{col2}{new_subtotal_row}"
                        table.ref = new_ref
                        logger.debug(f"Tabla {table.displayName} expandida: {table_ref} → {new_ref}")
        except Exception as e:
            logger.warning(f"No se pudo actualizar tabla Excel: {e}")

        return new_subtotal_row, new_last_data

    @staticmethod
    def _actualizar_sum_subtotal(ws, subtotal_row: int, data_start: int, data_end: int, celdas_sum: list):
        """
        Actualiza las fórmulas SUM en la fila de subtotal para cubrir el rango correcto.
        
        Args:
            ws: Worksheet
            subtotal_row: fila del subtotal
            data_start: primera fila de datos
            data_end: última fila de datos
            celdas_sum: lista de columnas (1-indexed) que tienen SUM
        """
        for col in celdas_sum:
            celda = ws.cell(row=subtotal_row, column=col)
            val = celda.value
            if val is not None and isinstance(val, str) and val.startswith("="):
                # Buscar SUM(rango) y actualizar el rango
                # Patrones: SUM(F3:F19), +SUM(C3:C19), etc.
                new_val = re.sub(
                    r'(SUM\()([A-Z]+)(\d+):([A-Z]+)(\d+)(\))',
                    lambda m: f"{m.group(1)}{m.group(2)}{data_start}:{m.group(4)}{data_end}{m.group(6)}",
                    val
                )
                if new_val != val:
                    celda.value = new_val
                    logger.debug(f"Subtotal col {col} actualizado: {val} → {new_val}")

    # ------------------------------------------------------------------
    # Método principal
    # ------------------------------------------------------------------

    def generar_excel(self, finca_id: int, db, output_path: str) -> str:
        """
        Genera el Excel con datos de la finca.
        1. Copia el template a output_path
        2. Abre con openpyxl
        3. Llena SOLO hojas de datos
        4. Guarda (manteniendo fórmulas)
        
        Args:
            finca_id: ID de la finca
            db: Instancia de Database
            output_path: Ruta donde guardar el Excel
            
        Returns:
            Ruta del archivo generado
        """
        self._validar_template()

        # Obtener todos los datos de la finca
        data = db.get_all_data_for_export(finca_id)
        finca = db.get_finca_by_id(finca_id)

        logger.info(f"Generando Excel para finca '{finca['nombre']}' (ID: {finca_id})")

        # 1. Copiar template
        shutil.copy2(self.template_path, output_path)
        logger.info(f"Template copiado a: {output_path}")

        # 2. Abrir con openpyxl (keep_vba=False para limpiar macros si hubiera)
        wb = openpyxl.load_workbook(output_path, keep_vba=False)
        logger.info(f"Hojas disponibles: {wb.sheetnames}")

        # 3. Llenar hojas
        self._llenar_hoja_lotes(wb, data.get("lotes", []))
        self._llenar_hoja_ingresos(wb, data)
        self._llenar_hojas_costos(wb, data)

        # 4. Generar hoja de gráficos
        ws_graficos = wb.create_sheet("Gráficos")
        # Mover "Gráficos" después de "ID lotes"
        idx_lotes = wb.sheetnames.index("ID lotes") if "ID lotes" in wb.sheetnames else 0
        wb.move_sheet("Gráficos", offset=idx_lotes + 1 - len(wb.sheetnames) + 1)
        self._generar_hoja_graficos(db, finca_id, ws_graficos)

        # 5. Guardar
        wb.save(output_path)
        wb.close()
        logger.info(f"Excel generado exitosamente: {output_path}")

        return output_path

    # ------------------------------------------------------------------
    # Hoja ID lotes
    # ------------------------------------------------------------------

    def _llenar_hoja_lotes(self, wb, lotes: list):
        """Llena la hoja 'ID lotes' con los datos de los lotes."""
        if "ID lotes" not in wb.sheetnames:
            logger.warning("Hoja 'ID lotes' no encontrada en el template")
            return

        ws = wb["ID lotes"]
        logger.info(f"Llenando hoja 'ID lotes' con {len(lotes)} lotes")

        num_needed = len(lotes)
        DATA_START = HOJA_LOTES_START_ROW  # 2
        SUBTOTAL_ROW = HOJA_LOTES_SUBTOTAL_ROW  # 17
        TEMPLATE_ROWS = HOJA_LOTES_TEMPLATE_ROWS  # 15
        MAX_COL = 9  # Columnas en esta hoja (A-I)

        # Asegurar filas suficientes
        new_subtotal_row, last_data_row = self._asegurar_filas_suficientes(
            ws, DATA_START, SUBTOTAL_ROW, num_needed, TEMPLATE_ROWS, MAX_COL
        )

        # Llenar datos
        for i, lote in enumerate(lotes):
            fila = DATA_START + i
            if fila >= new_subtotal_row:  # Safety check
                logger.warning(f"No hay espacio para lote: {lote['nombre']}")
                break

            # Fórmula de EDAD (col 6) — copiar si no existe
            col_f = ws.cell(row=fila, column=6)
            if not col_f.value or not str(col_f.value).startswith("="):
                col_f.value = f'=IF(E{fila}="", 0, DATEDIF(VALUE(E{fila}), TODAY(), "M"))'

            ws.cell(row=fila, column=1, value=lote["nombre"])        # A: ID LOTE
            ws.cell(row=fila, column=2, value=lote["area_hectareas"] or 0)  # B: AREA

            arboles = lote.get("num_arboles") or 0
            try:
                ws.cell(row=fila, column=3, value=int(arboles))      # C: # ARBOLES
            except (ValueError, TypeError):
                ws.cell(row=fila, column=3, value=0)

            ws.cell(row=fila, column=4, value=lote["variedad"] or "")  # D: VARIEDAD

            # E: Fecha de siembra
            fecha = lote.get("fecha_siembra", "") or ""
            if fecha:
                try:
                    from datetime import datetime as dt
                    fecha_dt = dt.strptime(fecha, "%Y-%m-%d")
                    ws.cell(row=fila, column=5, value=fecha_dt)
                    ws.cell(row=fila, column=5).number_format = "DD/MM/YYYY"
                except ValueError:
                    ws.cell(row=fila, column=5, value=fecha)
            else:
                ws.cell(row=fila, column=5, value="")

        logger.info(f"Hoja 'ID lotes' llenada: {num_needed} lotes (subtotal fila {new_subtotal_row})")

    # ------------------------------------------------------------------
    # Hoja Ingresos
    # ------------------------------------------------------------------

    def _llenar_hoja_ingresos(self, wb, data: dict):
        """Llena la hoja 'Ingresos por ventas de cafe'."""
        hoja_nombre = "Ingresos por ventas de cafe"
        if hoja_nombre not in wb.sheetnames:
            logger.warning(f"Hoja '{hoja_nombre}' no encontrada")
            return

        ws = wb[hoja_nombre]

        # Recolectar todos los ingresos
        ingresos = []
        for cat in ["ingreso_cps", "ingreso_pasilla", "ingreso_rere"]:
            for t in data.get(cat, []):
                tipo_map = {"ingreso_cps": "CPS", "ingreso_pasilla": "Pasilla", "ingreso_rere": "Re-re"}
                ingresos.append({
                    "fecha": t["fecha"],
                    "tipo": tipo_map[cat],
                    "cantidad": t["cantidad"] or 0,
                    "valor_total": t["valor_total"] or 0,
                })

        logger.info(f"Llenando hoja '{hoja_nombre}' con {len(ingresos)} ingresos")

        num_needed = len(ingresos)
        DATA_START = HOJA_COSTOS_START_ROW  # 3
        SUBTOTAL_ROW = HOJA_COSTOS_SUBTOTAL_ROW  # 20
        TEMPLATE_ROWS = HOJA_COSTOS_TEMPLATE_ROWS  # 17
        MAX_COL = 14  # Columnas en esta hoja (A-N)

        # Asegurar filas suficientes
        new_subtotal_row, last_data_row = self._asegurar_filas_suficientes(
            ws, DATA_START, SUBTOTAL_ROW, num_needed, TEMPLATE_ROWS, MAX_COL
        )

        # Actualizar fórmulas SUM en subtotal (columnas B, D, F)
        self._actualizar_sum_subtotal(
            ws, new_subtotal_row, DATA_START, last_data_row, celdas_sum=[2, 4, 6]
        )

        # Llenar datos
        for i, ingreso in enumerate(ingresos):
            fila = DATA_START + i
            if fila >= new_subtotal_row:
                break

            # Extender fórmula de valor unitario si no existe
            col_e = ws.cell(row=fila, column=5)
            if not col_e.value or not str(col_e.value).startswith("="):
                col_e.value = f'=IFERROR(F{fila}/D{fila}, 0)'

            # A: Fecha
            fecha = ingreso.get("fecha", "")
            if fecha:
                try:
                    from datetime import datetime as dt
                    fecha_dt = dt.strptime(fecha, "%Y-%m-%d")
                    ws.cell(row=fila, column=1, value=fecha_dt)
                    ws.cell(row=fila, column=1).number_format = "DD/MM/YYYY"
                except ValueError:
                    ws.cell(row=fila, column=1, value=fecha)
            else:
                ws.cell(row=fila, column=1, value="")

            # B: Unidad de venta (dejar vacío)
            ws.cell(row=fila, column=2, value="")

            # C: Tipo de café
            ws.cell(row=fila, column=3, value=ingreso["tipo"])

            # D: Cantidad
            ws.cell(row=fila, column=4, value=ingreso["cantidad"])

            # E: Valor Unitario - DEJAR LA FÓRMULA (=F/D)

            # F: Valor total
            ws.cell(row=fila, column=6, value=ingreso["valor_total"])

        logger.info(f"Hoja '{hoja_nombre}' llenada con {num_needed} registros")

    # ------------------------------------------------------------------
    # Hojas de costos (MO + Insumos, y especiales)
    # ------------------------------------------------------------------

    def _llenar_hojas_costos(self, wb, data: dict):
        """Llena todas las hojas de costos."""
        # Hojas con estructura MO + Insumos
        hojas_mo_insumos = [
            "Instalacion de Cafe",
            "Control de arvenses",
            "Fertilizacion",
            "Control Fitosanitario",
            "Regulacion de sombrio",
            "Otras Labores",
        ]

        for hoja in hojas_mo_insumos:
            if hoja not in wb.sheetnames:
                logger.warning(f"Hoja '{hoja}' no encontrada, saltando")
                continue
            self._llenar_hoja_mo_insumos(wb, hoja, data)

        # Hojas especiales
        if "Recoleccion" in wb.sheetnames:
            self._llenar_hoja_recoleccion(wb, data)
        if "Beneficio" in wb.sheetnames:
            self._llenar_hoja_beneficio(wb, data)
        if "Gastos Administrativos" in wb.sheetnames:
            self._llenar_hoja_gastos_admin(wb, data)

    def _llenar_hoja_mo_insumos(self, wb, hoja_nombre: str, data: dict):
        """
        Llena una hoja que tiene estructura MO (A-F) e Insumos (H-M).
        
        Estrategia: MO e insumos se llenan en las mismas filas, desde la fila 3.
        Si hay más MO que insumos (o viceversa), las celdas vacías quedan en blanco.
        """
        config = HOJA_CONFIG.get(hoja_nombre)
        if not config:
            logger.warning(f"Sin configuración para hoja '{hoja_nombre}'")
            return

        ws = wb[hoja_nombre]

        # Recolectar datos MO
        mo_data = []
        for cat in config.get("categorias_mo", []):
            mo_data.extend(data.get(cat, []))

        # Recolectar datos Insumos
        insumos_data = []
        for cat in config.get("categorias_insumos", []):
            insumos_data.extend(data.get(cat, []))

        logger.info(
            f"Llenando hoja '{hoja_nombre}': {len(mo_data)} MO, {len(insumos_data)} Insumos"
        )

        len_max = max(len(mo_data), len(insumos_data), 0)
        if len_max == 0:
            return

        mo_cols = config.get("mo_cols", {})
        insumos_cols = config.get("insumos_cols", {})

        num_needed = len_max
        DATA_START = HOJA_COSTOS_START_ROW  # 3
        SUBTOTAL_ROW = HOJA_COSTOS_SUBTOTAL_ROW  # 20
        TEMPLATE_ROWS = HOJA_COSTOS_TEMPLATE_ROWS  # 17
        MAX_COL = 20  # Suficiente para todas las variantes (Control arvenses usa hasta col T)

        # Asegurar filas suficientes
        new_subtotal_row, last_data_row = self._asegurar_filas_suficientes(
            ws, DATA_START, SUBTOTAL_ROW, num_needed, TEMPLATE_ROWS, MAX_COL
        )

        # Determinar qué columnas SUM están en subtotal según configuración de la hoja
        # MO subtotal: col 6 (suma F)
        # Insumos subtotal: depende de la hoja
        celdas_sum_mo = [6]  # Siempre col F
        celdas_sum_insumos = []
        if insumos_cols:
            # La columna de valor total de insumos está al final del rango de insumos
            ins_start_letter = insumos_cols["start"]
            ins_end_letter = insumos_cols["end"]
            ins_total_col = ord(ins_end_letter) - ord("A") + 1
            celdas_sum_insumos = [ins_total_col]

        # Actualizar fórmulas SUM en subtotal para MO e Insumos
        self._actualizar_sum_subtotal(
            ws, new_subtotal_row, DATA_START, last_data_row,
            celdas_sum=celdas_sum_mo + celdas_sum_insumos
        )

        # Llenar datos
        for i in range(len_max):
            fila = DATA_START + i
            if fila >= new_subtotal_row:
                logger.warning(f"Se alcanzó el límite de filas en '{hoja_nombre}'")
                break

            # --- Llenar MO (columnas A-F) ---
            if i < len(mo_data):
                self._escribir_fila_mo(ws, fila, mo_data[i], mo_cols)
            else:
                # Asegurar fórmula de V.Total MO incluso si no hay datos MO en esta fila
                self._asegurar_formula_mo(ws, fila, mo_cols)

            # --- Llenar Insumos (columnas H-M) ---
            if i < len(insumos_data):
                self._escribir_fila_insumos(ws, fila, insumos_data[i], insumos_cols)
            else:
                # Asegurar fórmula de V.Total Insumos incluso si no hay datos
                self._asegurar_formula_insumos(ws, fila, insumos_cols)

        logger.info(
            f"Hoja '{hoja_nombre}' llenada: {len(mo_data)} MO, {len(insumos_data)} Insumos"
        )

    def _asegurar_formula_mo(self, ws, fila: int, cols_config: dict):
        """Asegura que exista la fórmula de V.Total en la columna F de una fila MO."""
        if not cols_config:
            return
        end_col = ord(cols_config["end"]) - ord("A") + 1
        celda = ws.cell(row=fila, column=end_col)
        if not celda.value or not str(celda.value).startswith("="):
            # Fórmula típica: =IFERROR(D{fila}*E{fila}, 0) o =+E{fila}*D{fila}
            # Determinar según la configuración
            campos = cols_config.get("campos", [])
            # Encontrar columnas de cantidad y valor_unitario
            col_cant = None
            col_vu = None
            for j, campo in enumerate(campos):
                start_col = ord(cols_config["start"]) - ord("A") + 1
                if campo == "cantidad":
                    col_cant = start_col + j
                elif campo == "valor_unitario":
                    col_vu = start_col + j
            if col_cant and col_vu:
                celda.value = f'=IFERROR({get_column_letter(col_vu)}{fila}*{get_column_letter(col_cant)}{fila}, 0)'

    def _asegurar_formula_insumos(self, ws, fila: int, cols_config: dict):
        """Asegura que exista la fórmula de V.Total en la última columna de insumos."""
        if not cols_config:
            return
        end_col = ord(cols_config["end"]) - ord("A") + 1
        celda = ws.cell(row=fila, column=end_col)
        if not celda.value or not str(celda.value).startswith("="):
            # Fórmula típica: =IFERROR(+K{fila}*J{fila}, 0)
            campos = cols_config.get("campos", [])
            col_cant = None
            col_vu = None
            for j, campo in enumerate(campos):
                start_col = ord(cols_config["start"]) - ord("A") + 1
                if campo == "cantidad":
                    col_cant = start_col + j
                elif campo == "valor_unitario":
                    col_vu = start_col + j
            if col_cant and col_vu:
                celda.value = f'=IFERROR(+{get_column_letter(col_cant)}{fila}*{get_column_letter(col_vu)}{fila}, 0)'

    def _escribir_fila_mo(self, ws, fila: int, record: dict, cols_config: dict):
        """Escribe un registro de MO en una fila."""
        if not cols_config:
            return
        start_col = ord(cols_config["start"]) - ord("A") + 1  # 1-indexed
        campos = cols_config["campos"]

        for j, campo in enumerate(campos):
            col = start_col + j
            if campo == "lote":
                lote_id = record.get("lote_id", 0)
                ws.cell(row=fila, column=col, value=str(lote_id) if lote_id else "")
            elif campo == "fecha":
                self._poner_fecha(ws, fila, col, record.get("fecha", ""))
            elif campo == "labor":
                ws.cell(row=fila, column=col, value=record.get("labor", ""))
            elif campo == "cantidad":
                ws.cell(row=fila, column=col, value=record.get("cantidad", 0) or 0)
            elif campo == "valor_unitario":
                ws.cell(row=fila, column=col, value=record.get("valor_unitario", 0) or 0)
            elif campo == "valor_total_formula":
                # ✅ NUNCA sobreescribir la fórmula del template (F = D×E)
                pass
            else:
                ws.cell(row=fila, column=col, value="")

    def _escribir_fila_insumos(self, ws, fila: int, record: dict, cols_config: dict):
        """Escribe un registro de Insumos en una fila."""
        if not cols_config:
            return
        start_col = ord(cols_config["start"]) - ord("A") + 1  # 1-indexed
        campos = cols_config["campos"]

        for j, campo in enumerate(campos):
            col = start_col + j
            if campo == "fecha":
                self._poner_fecha(ws, fila, col, record.get("fecha", ""))
            elif campo == "labor":
                ws.cell(row=fila, column=col, value=record.get("labor", ""))
            elif campo == "producto":
                ws.cell(row=fila, column=col, value=record.get("producto", ""))
            elif campo == "cantidad":
                ws.cell(row=fila, column=col, value=record.get("cantidad", 0) or 0)
            elif campo == "valor_unitario":
                ws.cell(row=fila, column=col, value=record.get("valor_unitario", 0) or 0)
            elif campo == "valor_total_formula":
                # ✅ NUNCA sobreescribir la fórmula del template (L/M = K×J)
                pass
            else:
                ws.cell(row=fila, column=col, value="")

    # ------------------------------------------------------------------
    # Hojas especiales
    # ------------------------------------------------------------------

    def _llenar_hoja_recoleccion(self, wb, data: dict):
        """Llena la hoja 'Recoleccion'."""
        ws = wb["Recoleccion"]
        records = data.get("recoleccion", [])
        logger.info(f"Llenando hoja 'Recoleccion' con {len(records)} registros")

        num_needed = len(records)
        DATA_START = HOJA_COSTOS_START_ROW  # 3
        SUBTOTAL_ROW = HOJA_COSTOS_SUBTOTAL_ROW  # 20
        TEMPLATE_ROWS = HOJA_COSTOS_TEMPLATE_ROWS  # 17
        MAX_COL = 14  # A-N

        # Asegurar filas suficientes
        new_subtotal_row, last_data_row = self._asegurar_filas_suficientes(
            ws, DATA_START, SUBTOTAL_ROW, num_needed, TEMPLATE_ROWS, MAX_COL
        )

        # Actualizar SUBTOTAL: col C (SUM kilos), col E (SUM valor total)
        self._actualizar_sum_subtotal(
            ws, new_subtotal_row, DATA_START, last_data_row, celdas_sum=[3, 5]
        )

        # Llenar datos
        for i, rec in enumerate(records):
            fila = DATA_START + i
            if fila >= new_subtotal_row:
                break

            # A: Fecha
            self._poner_fecha(ws, fila, 1, rec.get("fecha", ""))

            # B: Recolección cereza (labor)
            ws.cell(row=fila, column=2, value=rec.get("labor", "recolección cereza"))

            # C: Kilos (cantidad)
            ws.cell(row=fila, column=3, value=rec.get("cantidad", 0) or 0)

            # D: V.Unitario - asegurar fórmula =E/C
            col_d = ws.cell(row=fila, column=4)
            if not col_d.value or not str(col_d.value).startswith("="):
                col_d.value = f'=IFERROR(E{fila}/C{fila}, 0)'

            # E: V.Total (valor_total)
            ws.cell(row=fila, column=5, value=rec.get("valor_total", 0) or 0)

        logger.info(f"Hoja 'Recoleccion' llenada con {num_needed} registros")

    def _llenar_hoja_beneficio(self, wb, data: dict):
        """Llena la hoja 'Beneficio'."""
        ws = wb["Beneficio"]
        records = data.get("beneficio", [])
        logger.info(f"Llenando hoja 'Beneficio' con {len(records)} registros")

        num_needed = len(records)
        DATA_START = HOJA_COSTOS_START_ROW  # 3
        SUBTOTAL_ROW = HOJA_COSTOS_SUBTOTAL_ROW  # 20
        TEMPLATE_ROWS = HOJA_COSTOS_TEMPLATE_ROWS  # 17
        MAX_COL = 6  # A-F

        # Asegurar filas suficientes
        new_subtotal_row, last_data_row = self._asegurar_filas_suficientes(
            ws, DATA_START, SUBTOTAL_ROW, num_needed, TEMPLATE_ROWS, MAX_COL
        )

        # Actualizar SUBTOTAL: col E (SUM valor total)
        self._actualizar_sum_subtotal(
            ws, new_subtotal_row, DATA_START, last_data_row, celdas_sum=[5]
        )

        # Llenar datos
        for i, rec in enumerate(records):
            fila = DATA_START + i
            if fila >= new_subtotal_row:
                break

            # A: Fecha
            self._poner_fecha(ws, fila, 1, rec.get("fecha", ""))

            # B: Labor realizada
            ws.cell(row=fila, column=2, value=rec.get("labor", ""))

            # C: Número de jornales (cantidad)
            ws.cell(row=fila, column=3, value=rec.get("cantidad", 0) or 0)

            # D: V.Unitario (valor_unitario)
            ws.cell(row=fila, column=4, value=rec.get("valor_unitario", 0) or 0)

            # E: V.Total - asegurar fórmula =D*C
            col_e = ws.cell(row=fila, column=5)
            if not col_e.value or not str(col_e.value).startswith("="):
                col_e.value = f'=IFERROR(D{fila}*C{fila}, 0)'

        logger.info(f"Hoja 'Beneficio' llenada con {num_needed} registros")

    def _llenar_hoja_gastos_admin(self, wb, data: dict):
        """Llena la hoja 'Gastos Administrativos'."""
        ws = wb["Gastos Administrativos"]
        records = data.get("administrativo", [])
        logger.info(f"Llenando hoja 'Gastos Administrativos' con {len(records)} registros")

        num_needed = len(records)
        DATA_START = HOJA_COSTOS_START_ROW  # 3
        SUBTOTAL_ROW = HOJA_COSTOS_SUBTOTAL_ROW  # 20
        TEMPLATE_ROWS = HOJA_COSTOS_TEMPLATE_ROWS  # 17
        MAX_COL = 9  # A-I

        # Asegurar filas suficientes
        new_subtotal_row, last_data_row = self._asegurar_filas_suficientes(
            ws, DATA_START, SUBTOTAL_ROW, num_needed, TEMPLATE_ROWS, MAX_COL
        )

        # Actualizar SUBTOTAL: col C (SUM valor total)
        self._actualizar_sum_subtotal(
            ws, new_subtotal_row, DATA_START, last_data_row, celdas_sum=[3]
        )

        # Llenar datos
        for i, rec in enumerate(records):
            fila = DATA_START + i
            if fila >= new_subtotal_row:
                break

            # A: Fecha
            self._poner_fecha(ws, fila, 1, rec.get("fecha", ""))

            # B: Gasto administrativo (labor)
            ws.cell(row=fila, column=2, value=rec.get("labor", ""))

            # C: V.Total (valor_total)
            ws.cell(row=fila, column=3, value=rec.get("valor_total", 0) or 0)

        logger.info(f"Hoja 'Gastos Administrativos' llenada con {num_needed} registros")

    # ------------------------------------------------------------------
    # Gráficos de tendencia (MEJORA 4)
    # ------------------------------------------------------------------

    def _generar_hoja_graficos(self, db, finca_id: int, ws):
        """
        Genera 3 gráficos de tendencia en la hoja de gráficos:
        1. BarChart: Ingresos vs Egresos por año (2023-2025)
        2. PieChart: Distribución de costos por categoría
        3. LineChart: Evolución del costo total por mes
        """
        conn = db.get_conn()
        try:
            # =============================================================
            # 1. BARCHART: Ingresos vs Egresos por año
            # =============================================================
            ws['A1'] = 'Año'
            ws['B1'] = 'Ingresos'
            ws['C1'] = 'Egresos'

            for i, year in enumerate([2023, 2024, 2025]):
                row = 2 + i
                ws.cell(row=row, column=1, value=year)

                ing = conn.execute(
                    "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones "
                    "WHERE finca_id = ? AND categoria LIKE 'ingreso_%' AND fecha LIKE ?",
                    (finca_id, f"{year}%")
                ).fetchone()[0]
                ws.cell(row=row, column=2, value=ing or 0)

                egr = conn.execute(
                    "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones "
                    "WHERE finca_id = ? AND categoria NOT LIKE 'ingreso_%' AND fecha LIKE ?",
                    (finca_id, f"{year}%")
                ).fetchone()[0]
                ws.cell(row=row, column=3, value=egr or 0)

            chart1 = BarChart()
            chart1.type = "col"
            chart1.title = "Ingresos vs Egresos por Año"
            chart1.y_axis.title = "Valor ($)"
            chart1.style = 10

            data1 = Reference(ws, min_col=1, min_row=1, max_col=3, max_row=4)
            cats1 = Reference(ws, min_col=1, min_row=2, max_row=4)
            chart1.add_data(data1, titles_from_data=True)
            chart1.set_categories(cats1)

            # Colores: Ingresos verde (#2E7D32), Egresos rojo (#C62828)
            chart1.series[0].graphicalProperties.solidFill = "2E7D32"
            chart1.series[1].graphicalProperties.solidFill = "C62828"

            ws.add_chart(chart1, "E1")

            # =============================================================
            # 2. PIECHART: Distribución de costos por categoría
            # =============================================================
            ws['A10'] = 'Categoría'
            ws['B10'] = 'Total'

            categorias_costo = [
                ("Instalación", ["instalacion_mo", "instalacion_insumos"]),
                ("Arvenses", ["arvenses_mo", "arvenses_insumos"]),
                ("Fertilización", ["fertilizacion_mo", "fertilizacion_insumos"]),
                ("Fitosanitario", ["fitosanitario_mo", "fitosanitario_insumos"]),
                ("Sombrio", ["sombrio_mo", "sombrio_insumos"]),
                ("Otras Labores", ["otras_labores_mo", "otras_labores_insumos"]),
                ("Recolección", ["recoleccion"]),
                ("Beneficio", ["beneficio"]),
                ("Administrativo", ["administrativo"]),
            ]

            pie_palette = [
                "2E7D32", "1565C0", "F9A825", "E65100",
                "6A1B9A", "00838F", "C62828", "4E342E", "558B2F",
            ]

            for i, (cat_name, cat_db_names) in enumerate(categorias_costo):
                row = 11 + i
                ws.cell(row=row, column=1, value=cat_name)

                placeholders = ",".join("?" for _ in cat_db_names)
                total = conn.execute(
                    f"SELECT COALESCE(SUM(valor_total), 0) FROM transacciones "
                    f"WHERE finca_id = ? AND categoria IN ({placeholders})",
                    (finca_id, *cat_db_names)
                ).fetchone()[0]
                ws.cell(row=row, column=2, value=total or 0)

            chart2 = PieChart()
            chart2.title = "Distribución de Costos por Categoría"
            chart2.style = 10

            data2 = Reference(ws, min_col=2, min_row=10, max_row=10 + len(categorias_costo))
            cats2 = Reference(ws, min_col=1, min_row=11, max_row=10 + len(categorias_costo))
            chart2.add_data(data2, titles_from_data=True)
            chart2.set_categories(cats2)

            # Data labels con porcentaje y nombre de categoría
            chart2.dataLabels = DataLabelList()
            chart2.dataLabels.showPercent = True
            chart2.dataLabels.showCatName = True

            # Colores para cada sector del pie
            for i in range(len(categorias_costo)):
                pt = DataPoint(idx=i)
                pt.graphicalProperties.solidFill = pie_palette[i]
                chart2.series[0].data_points.append(pt)

            ws.add_chart(chart2, "E17")

            # =============================================================
            # 3. LINECHART: Costo total por mes (todas las categorías de egreso)
            # =============================================================
            ws['A20'] = 'Mes'
            ws['B20'] = 'Costo Total'

            meses = [
                "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
            ]

            for i, mes_nombre in enumerate(meses):
                row = 21 + i
                ws.cell(row=row, column=1, value=mes_nombre)
                mes_num = f"{i + 1:02d}"

                total = conn.execute(
                    "SELECT COALESCE(SUM(valor_total), 0) FROM transacciones "
                    "WHERE finca_id = ? AND categoria NOT LIKE 'ingreso_%' "
                    "AND substr(fecha, 6, 2) = ?",
                    (finca_id, mes_num)
                ).fetchone()[0]
                ws.cell(row=row, column=2, value=total or 0)

            chart3 = LineChart()
            chart3.title = "Costo Total por Mes"
            chart3.y_axis.title = "Costo ($)"
            chart3.x_axis.title = "Mes"
            chart3.style = 10

            data3 = Reference(ws, min_col=2, min_row=20, max_row=32)
            cats3 = Reference(ws, min_col=1, min_row=21, max_row=32)
            chart3.add_data(data3, titles_from_data=True)
            chart3.set_categories(cats3)

            # Color de la línea: azul
            chart3.series[0].graphicalProperties.line.solidFill = "1565C0"
            chart3.series[0].graphicalProperties.line.width = 25000  # 2.5pt en EMUs

            ws.add_chart(chart3, "E33")

            logger.info("Hoja 'Gráficos' generada con 3 gráficos (Bar, Pie, Line)")

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _poner_fecha(self, ws, fila: int, col: int, fecha_str: str):
        """Pone una fecha en una celda, intentando convertir a datetime."""
        if not fecha_str:
            ws.cell(row=fila, column=col, value="")
            return

        try:
            from datetime import datetime as dt
            # Intentar varios formatos
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
                try:
                    fecha_dt = dt.strptime(fecha_str, fmt)
                    cell = ws.cell(row=fila, column=col, value=fecha_dt)
                    cell.number_format = "DD/MM/YYYY"
                    return
                except ValueError:
                    continue
            # Si no funciona ningún formato, poner como string
            ws.cell(row=fila, column=col, value=fecha_str)
        except Exception as e:
            logger.warning(f"Error al parsear fecha '{fecha_str}': {e}")
            ws.cell(row=fila, column=col, value=fecha_str)
