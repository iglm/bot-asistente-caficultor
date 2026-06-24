"""
Manejador de Excel para el Bot Asistente Caficultor.
Carga el template, llena SOLO las hojas de datos con información de SQLite,
y guarda manteniendo fórmulas intactas.
"""
import os
import shutil
import logging
from datetime import datetime
from typing import Optional

import openpyxl
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

        # 4. Guardar
        wb.save(output_path)
        wb.close()
        logger.info(f"Excel generado exitosamente: {output_path}")

        return output_path

    def _llenar_hoja_lotes(self, wb, lotes: list):
        """Llena la hoja 'ID lotes' con los datos de los lotes."""
        if "ID lotes" not in wb.sheetnames:
            logger.warning("Hoja 'ID lotes' no encontrada en el template")
            return

        ws = wb["ID lotes"]
        logger.info(f"Llenando hoja 'ID lotes' con {len(lotes)} lotes")

        for i, lote in enumerate(lotes):
            fila = 2 + i  # Fila 2 es la primera de datos
            if fila > 16:
                logger.warning(f"Límite de 15 lotes alcanzado. Ignorando lote: {lote['nombre']}")
                break

            ws.cell(row=fila, column=1, value=lote["nombre"])        # A: ID LOTE
            ws.cell(row=fila, column=2, value=lote["area_hectareas"] or 0)  # B: AREA

            arboles = lote.get("num_arboles") or 0
            try:
                ws.cell(row=fila, column=3, value=int(arboles))      # C: # ARBOLES
            except (ValueError, TypeError):
                ws.cell(row=fila, column=3, value=0)

            ws.cell(row=fila, column=4, value=lote["variedad"] or "")  # D: VARIEDAD

            # E: Fecha de siembra - intentar poner como fecha
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

            # F: EDAD (MESES) - DEJAR LA FÓRMULA, no llenar
            # La fórmula ya está en el template: =IF(E="",0,DATEDIF(VALUE(E),TODAY(),"M"))

        logger.info(f"Hoja 'ID lotes' llenada: {min(len(lotes), 15)} lotes")

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

        for i, ingreso in enumerate(ingresos):
            fila = 3 + i  # Fila 3 es la primera de datos
            if fila > 19:
                logger.warning(f"Límite de 17 ingresos alcanzado. Ignorando...")
                break

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
            # No llenar, la fórmula del template se mantiene

            # F: Valor total
            ws.cell(row=fila, column=6, value=ingreso["valor_total"])

        logger.info(f"Hoja '{hoja_nombre}' llenada con {min(len(ingresos), 17)} registros")

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

        for i in range(len_max):
            fila = 3 + i
            if fila > 19:
                logger.warning(f"Límite de 17 filas alcanzado en '{hoja_nombre}'")
                break

            # --- Llenar MO (columnas A-F) ---
            if i < len(mo_data):
                self._escribir_fila_mo(ws, fila, mo_data[i], mo_cols)

            # --- Llenar Insumos (columnas H-M) ---
            if i < len(insumos_data):
                self._escribir_fila_insumos(ws, fila, insumos_data[i], insumos_cols)

    def _escribir_fila_mo(self, ws, fila: int, record: dict, cols_config: dict):
        """Escribe un registro de MO en una fila."""
        start_col = ord(cols_config["start"]) - ord("A") + 1  # 1-indexed
        campos = cols_config["campos"]

        for j, campo in enumerate(campos):
            col = start_col + j
            if campo == "lote":
                # Buscar nombre del lote
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
                # Valor Total con fórmula =D*E (D×E en el Excel)
                # La fórmula ya está en el template, no sobreescribir
                # Pero ponemos el valor por si acaso no hay fórmula
                if record.get("valor_total", 0):
                    ws.cell(row=fila, column=col, value=record["valor_total"])
                # La fórmula original del template se mantiene
            else:
                ws.cell(row=fila, column=col, value="")

    def _escribir_fila_insumos(self, ws, fila: int, record: dict, cols_config: dict):
        """Escribe un registro de Insumos en una fila."""
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
                # Mantener fórmula del template
                if record.get("valor_total", 0):
                    ws.cell(row=fila, column=col, value=record["valor_total"])
            else:
                ws.cell(row=fila, column=col, value="")

    def _llenar_hoja_recoleccion(self, wb, data: dict):
        """Llena la hoja 'Recoleccion'."""
        ws = wb["Recoleccion"]
        records = data.get("recoleccion", [])
        logger.info(f"Llenando hoja 'Recoleccion' con {len(records)} registros")

        for i, rec in enumerate(records):
            fila = 3 + i
            if fila > 19:
                break

            # A: Fecha
            self._poner_fecha(ws, fila, 1, rec.get("fecha", ""))

            # B: Recolección cereza (labor)
            ws.cell(row=fila, column=2, value=rec.get("labor", "recolección cereza"))

            # C: Kilos (cantidad)
            ws.cell(row=fila, column=3, value=rec.get("cantidad", 0) or 0)

            # D: V.Unitario - DEJAR FÓRMULA =E/C
            # No llenar, mantener fórmula del template

            # E: V.Total (valor_total)
            ws.cell(row=fila, column=5, value=rec.get("valor_total", 0) or 0)

    def _llenar_hoja_beneficio(self, wb, data: dict):
        """Llena la hoja 'Beneficio'."""
        ws = wb["Beneficio"]
        records = data.get("beneficio", [])
        logger.info(f"Llenando hoja 'Beneficio' con {len(records)} registros")

        for i, rec in enumerate(records):
            fila = 3 + i
            if fila > 19:
                break

            # A: Fecha
            self._poner_fecha(ws, fila, 1, rec.get("fecha", ""))

            # B: Labor realizada
            ws.cell(row=fila, column=2, value=rec.get("labor", ""))

            # C: Número de jornales (cantidad)
            ws.cell(row=fila, column=3, value=rec.get("cantidad", 0) or 0)

            # D: V.Unitario (valor_unitario)
            ws.cell(row=fila, column=4, value=rec.get("valor_unitario", 0) or 0)

            # E: V.Total - DEJAR FÓRMULA =D*C
            # Mantener fórmula del template; poner valor por si acaso
            if rec.get("valor_total", 0):
                ws.cell(row=fila, column=5, value=rec["valor_total"])

    def _llenar_hoja_gastos_admin(self, wb, data: dict):
        """Llena la hoja 'Gastos Administrativos'."""
        ws = wb["Gastos Administrativos"]
        records = data.get("administrativo", [])
        logger.info(f"Llenando hoja 'Gastos Administrativos' con {len(records)} registros")

        for i, rec in enumerate(records):
            fila = 3 + i
            if fila > 19:
                break

            # A: Fecha
            self._poner_fecha(ws, fila, 1, rec.get("fecha", ""))

            # B: Gasto administrativo (labor)
            ws.cell(row=fila, column=2, value=rec.get("labor", ""))

            # C: V.Total (valor_total)
            ws.cell(row=fila, column=3, value=rec.get("valor_total", 0) or 0)

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
