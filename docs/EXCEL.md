# 📊 Estructura del Excel de Costos de Producción ☕

> **Documentación del archivo Excel generado por el bot**
> Template: `data/plantilla/Costos de produccion - 2026.xlsx`
> Formato oficial para caficultores colombianos — 18 hojas, fórmulas automáticas, gráficos

---

## 📋 Resumen del Archivo

| Propiedad | Valor |
|-----------|-------|
| 📄 Hojas totales | **18** (16 datos + 1 resultados + 1 gráficos) |
| 📦 Tamaño template | ~38 KB |
| 📦 Tamaño con datos | ~42-50 KB |
| 🔧 Librería | openpyxl 3.1.x |
| 🧮 Fórmulas | Dinámicas (se copian según cantidad de filas) |
| 📈 Gráficos | BarChart, PieChart, LineChart |
| 🌐 Compatible con | Excel, LibreOffice, Google Sheets |

---

## 🗂️ Lista de Hojas

### Hojas de Datos (16)

| # | Hoja | Categorías DB | Columnas MO | Columnas Insumos |
|---|------|---------------|-------------|-------------------|
| 1 | `ID lotes` | — (lotes) | nombre, área, árboles, variedad, siembra | — |
| 2 | `Ingresos por ventas de cafe` | ingreso_cps, ingreso_pasilla, ingreso_rere | fecha, tipo, cantidad, v.unitario, v.total | — |
| 3 | `Instalacion de Cafe` | instalacion_mo, instalacion_insumos | A-F: lote, fecha, labor, cantidad, v.unitario, v.total | H-L: fecha, producto, cantidad, v.unitario, v.total |
| 4 | `Control de arvenses` | arvenses_mo, arvenses_insumos | A-F: lote, fecha, labor, cantidad, v.unitario, v.total | H-M: fecha, labor, producto, cantidad, v.unitario, v.total |
| 5 | `Fertilizacion` | fertilizacion_mo, fertilizacion_insumos | A-F: lote, fecha, labor, cantidad, v.unitario, v.total | H-L: fecha, producto, cantidad, v.unitario, v.total |
| 6 | `Control Fitosanitario` | fitosanitario_mo, fitosanitario_insumos | A-F: lote, fecha, labor, cantidad, v.unitario, v.total | H-M: fecha, labor, producto, cantidad, v.unitario, v.total |
| 7 | `Regulacion de sombrio` | sombrio_mo, sombrio_insumos | A-F: lote, fecha, labor, cantidad, v.unitario, v.total | H-L: fecha, producto, cantidad, v.unitario, v.total |
| 8 | `Otras Labores` | otras_labores_mo, otras_labores_insumos | A-F: lote, fecha, labor, cantidad, v.unitario, v.total | H-L: fecha, producto, cantidad, v.unitario, v.total |
| 9 | `Recoleccion` | recoleccion | A-E: fecha, labor, kilos, v.unitario (=E/C), v.total | — |
| 10 | `Beneficio` | beneficio | A-E: fecha, labor, jornales, v.unitario, v.total (=D*C) | — |
| 11 | `Gastos Administrativos` | administrativo | A-C: fecha, gasto, v.total | — |

### Hojas de Resultados

| # | Hoja | Descripción |
|---|------|-------------|
| 12-17 | Resumen/Resultados | **6 hojas adicionales** en el template con fórmulas de totales, subtotales y consolidación |
| 18 | `Gráficos` | BarChart, PieChart y LineChart generados dinámicamente |

---

## 📐 Columnas por Hoja

### `ID lotes`

| Columna | Campo | Tipo | Descripción |
|---------|-------|------|-------------|
| A | nombre | Texto | Nombre del lote |
| B | area_hectareas | Número | Área en hectáreas |
| C | num_arboles | Entero | Número de árboles |
| D | variedad | Texto | Variedad (Castillo, Caturra, Colombia) |
| E | fecha_siembra | Fecha | Fecha de siembra |
| F | — | — | Año de siembra calculado |

### `Ingresos por ventas de cafe`

| Columna | Campo | Tipo | Descripción |
|---------|-------|------|-------------|
| A | — | — | (vacía o lote) |
| B | fecha | Fecha | Fecha de la venta |
| C | tipo | Texto | CPS, Pasilla, Re-re |
| D | cantidad | Número | Kilos vendidos |
| E | valor_unitario | Fórmula | =F/D (valor total / kilos) |
| F | valor_total | Número | Valor total de la venta |

### Hojas compuestas (Instalación, Arvenses, Fertilización, etc.)

#### Sección MO (Columnas A-F)

| Columna | Campo | Tipo | Descripción |
|---------|-------|------|-------------|
| A | Lote | Texto | Nombre del lote |
| B | Fecha | Fecha | Fecha de la labor |
| C | Labor | Texto | Descripción de la labor |
| D | Cantidad | Número | Jornales o unidades |
| E | V.Unitario | Número | Valor por jornal ($) |
| F | V.Total | **Fórmula** | =D×E (cantidad × valor unitario) |

#### Sección Insumos (Columnas H+)

| Columna | Campo | Tipo | Descripción |
|---------|-------|------|-------------|
| H | Fecha | Fecha | Fecha de compra/aplicación |
| I | Producto | Texto | Nombre del producto/insumo |
| J | Cantidad | Número | Cantidad adquirida |
| K | V.Unitario | Número | Precio por unidad ($) |
| L | V.Total | **Fórmula** | =J×K (cantidad × v.unitario) |

### Hoja `Recoleccion`

| Columna | Campo | Tipo | Descripción |
|---------|-------|------|-------------|
| A | Fecha | Fecha | Fecha de recolección |
| B | Labor | Texto | Descripción |
| C | Kilos | Número | Kilos de café cereza |
| D | V.Unitario | Fórmula | =E/C (v.total / kilos) |
| E | V.Total | Número | Valor total pagado |

### Hoja `Beneficio`

| Columna | Campo | Tipo | Descripción |
|---------|-------|------|-------------|
| A | Fecha | Fecha | Fecha del beneficio |
| B | Labor | Texto | Descripción |
| C | Jornales | Número | Número de jornales |
| D | V.Unitario | Número | Valor por jornal |
| E | V.Total | **Fórmula** | =C×D (jornales × v.unitario) |

### Hoja `Gastos Administrativos`

| Columna | Campo | Tipo | Descripción |
|---------|-------|------|-------------|
| A | Fecha | Fecha | Fecha del gasto |
| B | Gasto | Texto | Descripción del gasto |
| C | V.Total | Número | Valor total del gasto |

---

## 🧮 Fórmulas Automáticas

### Fórmulas por fila

```
# MO (Filas de datos): V.Total = Cantidad × V.Unitario
F3 = D3 * E3

# Insumos: V.Total = Cantidad × V.Unitario
L3 = J3 * K3   (o M3 = K3 * L3 según hoja)

# Recolección: V.Unitario = V.Total / Kilos
D3 = E3 / C3

# Beneficio: V.Total = Jornales × V.Unitario
E3 = C3 * D3
```

### Fórmulas de subtotal

```
# Cada hoja tiene SUM en la fila de subtotal:
F{subtotal} = SUM(F{data_start}:F{data_end})
```

### Fórmulas en hojas de resultados

Las hojas de resultados (12-17) contienen referencias cruzadas a las hojas de datos usando `SUM()` y referencias de celda que se actualizan dinámicamente.

---

## 📈 Gráficos (Hoja 18: "Gráficos")

Tres gráficos generados automáticamente:

### 1. BarChart — Costos por Categoría
```
- Eje X: Categorías (Instalación, Arvenses, Fertilización, etc.)
- Eje Y: Valores totales ($)
- Título: "Costos de Producción por Categoría"
```

### 2. PieChart — Distribución de Costos
```
- Sectores: Cada categoría de costo
- Valores: Porcentaje del total
- Título: "Distribución de Costos"
- Etiquetas: Con porcentaje visible
```

### 3. LineChart — Ingresos vs Egresos (Tendencia)
```
- Eje X: Períodos/meses
- Línea 1: Ingresos
- Línea 2: Egresos
- Título: "Tendencia de Ingresos y Egresos"
```

---

## 🔧 Cómo se genera el Excel

### Con datos (`generar_excel()`)

```python
# 1. Copiar template a archivo temporal
shutil.copy2(template_path, output_path)

# 2. Abrir con openpyxl
wb = openpyxl.load_workbook(output_path)

# 3. Para cada hoja de datos:
#    a. Obtener transacciones de DB
#    b. Si hay más filas que el template:
#       - ws.insert_rows() para crear espacio
#       - Copiar fórmulas de fila template a nuevas filas
#       - Ajustar referencias de celdas en fórmulas
#    c. Si hay menos, dejar filas template vacías
#    d. Escribir datos reales en las filas
#    e. Actualizar fórmulas SUBTOTAL (SUM)

# 4. Generar/actualizar gráficos en hoja "Gráficos"

# 5. Guardar y cerrar
wb.save(output_path)
wb.close()
```

### Sin datos (`generar_plantilla_vacia()`)

```python
# 1. Copiar template
shutil.copy2(template_path, output_path)

# 2. Abrir con openpyxl

# 3. Para cada hoja:
#    a. Limpiar filas de datos (desde fila 3)
#    b. Agregar fila 2 con datos de ejemplo (en gris itálico)

# 4. Agregar hoja "NOTAS" con instrucciones detalladas

# 5. Guardar
```

### Clase `ExcelManager`

```python
class ExcelManager:
    def __init__(self, template_path: str)
    
    # Métodos públicos:
    def generar_excel(finca_id: int, db: Database, output_path: str) -> str
    def generar_plantilla_vacia(output_path: str) -> str
    
    # Métodos privados:
    def _validar_template(self)
    def _asegurar_filas_suficientes(ws, start, subtotal, needed, template_rows, max_col) -> tuple
    def _copiar_formula_fila(ws, fila_origen, fila_destino, max_col)
    def _ajustar_referencias_fila(formula, fila_origen, fila_destino) -> str
    def _copiar_estilo_celda(origen, destino)
    def _actualizar_sum_subtotal(ws, subtotal_row, data_start, data_end, celdas_sum)
    def _preparar_hojas_plantilla(wb)
    def _agregar_hoja_notas(wb)
```

---

## 📥 Cómo importar/exportar

### Exportar desde el bot

```
1. Usa /excel o presiona 📋 Exportar Excel en el menú
2. Si tienes varias fincas, selecciona una
3. El bot genera el Excel y te lo envía como archivo
4. Ábrelo en Excel, LibreOffice o Google Sheets
5. Las fórmulas se calculan automáticamente al abrir
```

### Importar al bot

```
1. Presiona 📥 Importar Excel en el menú
2. Descarga la plantilla vacía (tiene datos de ejemplo + instrucciones)
3. Llena los datos en las hojas correspondientes
4. Guarda el archivo
5. Envíalo al bot
6. El bot muestra preview de los datos
7. Confirma la importación
```

### Formato esperado para importación

| Hoja | Columnas requeridas |
|------|---------------------|
| `Fincas` | nombre, region, departamento |
| `Lotes` | finca_nombre, nombre, area_hectareas, num_arboles, variedad, fecha_siembra |
| `Ingresos` | finca_nombre, tipo (CPS/Pasilla/Re-re), fecha, cantidad, valor_total |
| `Costos_MO` | finca_nombre, lote_nombre, categoria, fecha, labor, cantidad, valor_unitario, valor_total |
| `Costos_Insumos` | finca_nombre, lote_nombre, categoria, fecha, producto, cantidad, unidad, valor_unitario, valor_total |

---

## 🧪 Verificación de integridad

Al generar el Excel, el bot verifica:

- ✅ Template existe (`_validar_template()`)
- ✅ Fórmulas copiadas correctamente (`_ajustar_referencias_fila()`)
- ✅ Rangos SUM actualizados (`_actualizar_sum_subtotal()`)
- ✅ Tablas Excel expandidas (ej: `Tabla4` en ID lotes)
- ✅ Gráficos generados con datos reales
- ✅ Sin límites de filas (insert_rows() dinámico)
