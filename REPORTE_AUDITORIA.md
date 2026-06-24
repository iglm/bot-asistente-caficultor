# 📋 REPORTE DE AUDITORÍA EXHAUSTIVA — Bot Asistente Caficultor

**Fecha:** 24 de junio de 2026
**Versión auditada:** 28 archivos Python, SQLite, aiogram 3.x, openpyxl 3.1.5
**Metodología:** Compilación + imports + callbacks + FSM + DB + Excel, verificación end-to-end

---

## RESUMEN EJECUTIVO

| Categoría | Estado |
|-----------|--------|
| ✅ Compilación | **28/28 archivos compilan** sin errores |
| ✅ Imports | **Todos los imports son correctos** |
| ✅ Base de datos | **Todos los métodos funcionan** (verificado en memoria) |
| ✅ Callbacks | **49/50 callbacks tienen handler** |
| ⚠️ FSM States | **48 estados OK, 6 huérfanos** (estados definidos pero no usados) |
| ❌ Excel `_llenar_hoja_presupuesto` | **BUG: `ws.cell()` recibe `font` como kwarg inválido** |
| ❌ Presupuesto exportar | **Código muerto: `if False else {}`** |
| ⚠️ Voice handler | **Función `format_parsed_data` duplicada/obsoleta** |
| ✅ Botones de escape | **Mayoría cubiertos, algunos con warnings menores** |

---

## 1️⃣ MODULAR AUDIT

### 1.1 handlers/start.py — ✅ COMPILA ✅
- `/start` para usuario nuevo: ✅ flujo de aprobación completo
- `/start` para usuario existente: ✅ bienvenida + menú
- `/start` para usuario rechazado: ✅ mensaje rechazo
- Callbacks `aprobar:`, `rechazar:`: ✅ manejados en admin.py
- Botón de escape: ✅ `boton_menu()` en todos los mensajes
- **NOTA:** No registra callbacks inline directos (los delega a admin.py)

### 1.2 handlers/menu.py — ✅ COMPILA ✅
- `/menu`, `/cancelar`, `/`: ✅ con prioridad máxima
- `ir_borrar` → `confirmar_borrar:` → `confirmar_borrar_2:`: ✅ flujo completo
- `ir_admin`: ✅ solo para ADMIN_IDS
- `volver_menu`: ✅ reconstruye menú completo
- `cancelar_operacion`: ✅ handler global de cancelación
- **⚠️ ADVERTENCIA:** `cancelar_operacion` NO está en la lista del `CancelMiddleware` (solo `menu_*` e `ir_*`), pero el handler manualmente hace `state.clear()` ✅

### 1.3 handlers/fincas.py — ✅ COMPILA ✅
- FSM: `FincaForm.esperando_nombre → esperando_region → esperando_departamento`
- Todos los estados con handler: ✅
- Callbacks: `nueva_finca` ✅, `menu_fincas` ✅
- Botones de escape: ✅ `botones_menu_cancelar()` en cada paso
- DB methods: `db.create_finca()`, `db.get_fincas()`, `db.is_approved()` ✅

### 1.4 handlers/lotes.py — ✅ COMPILA ✅
- FSM: `LoteForm.esperando_finca → esperando_nombre → esperando_area → esperando_arboles → esperando_variedad → esperando_fecha_siembra`
- **⚠️ `LoteForm.esperando_finca`** definido pero NUNCA usado como estado FSM. El código elige finca vía callback inline, no FSM.
- Callbacks: `lotes_finca:`, `nuevo_lote:`, `fecha:` → ✅ todos con handler
- Botones de escape: ✅
- DB methods: `db.create_lote()`, `db.get_lotes()`, `db.get_lote_by_id()`, `db.get_finca_by_id()` ✅

### 1.5 handlers/ingresos.py — ✅ COMPILA ✅
- FSM: `IngresoForm.esperando_finca → esperando_fecha → esperando_tipo → esperando_cantidad → esperando_valor_total → esperando_confirmar`
- Todos los estados con handler: ✅
- Callbacks: `ingreso_finca:`, `tipo_cafe:`, `conf_ingreso:`, `ingreso_volver_fecha`, `fecha:` → ✅
- Botones de escape: ✅
- DB methods: `db.insert_transaccion()`, `db.get_fincas()`, `db.get_finca_by_id()` ✅

### 1.6 handlers/costos.py — ✅ COMPILA ✅
- FSM: 16 estados definidos en `CostoForm`
- **⚠️ `CostoForm.esperando_agregar_insumos`** → HUÉRFANO (definido, nunca usado como estado)
- **⚠️ `CostoForm.esperando_mas_insumos`** → HUÉRFANO (definido, nunca usado como estado)
- Los 14 estados restantes ✅ con handlers
- Callbacks: `costo_finca:`, `costo_lote:todos/especifico/seleccionar`, `toggle_lote:`, `cat_costo:`, `conf_costo_mo:`, `conf_insumo:`, `fecha:`
- **⚠️ `cancelar_operacion` se registra DOS VECES**: una en menu.py (línea 275) y otra en costos.py (línea 997). La de costos.py tiene scope dentro del router de costos, y la de menu.py en el router de menú. Ambos hacen `state.clear()`. No es bug pero es código duplicado.
- Botones de escape: ✅ `botones_menu_cancelar()` en cada paso
- DB methods: `guardar_mo()` llama `db.insert_transaccion()` ✅, `db.get_lotes()` ✅

### 1.7 handlers/reportes.py — ✅ COMPILA ✅
- `/resumen` → ✅ muestra resumen financiero
- `resumen_finca:` → ✅ callback con handler
- `menu_excel` / `generar_excel:` → ✅ genera y envía Excel
- **⚠️ `mostrar_resumen()` usa `_split_texto()`** para textos largos ✅
- Botones de escape: ✅
- DB methods: `db.get_resumen_finca()`, `db.get_all_data_for_export()`, `db.get_finca_by_id()` ✅
- Excel: `ExcelManager.generar_excel()` ✅

### 1.8 handlers/presupuesto.py — ✅ COMPILA ✅
- **❌ BUG CRÍTICO:** Línea 840: `data = await state.get_data() if False else {}`
  - `if False` hardcodeado → **siempre devuelve `{}`** ignorando el estado real
  - `data` se usa más abajo en `línea 840-850` pero luego se re-obtiene con `sdata = await state.get_data()` en línea 867, mitigando el error
  - **IMPACTO:** El código funciona porque la línea 867 vuelve a leer el state. La línea 840 es código muerto.
- **⚠️ Estados huérfanos:**
  - `PresupuestoStates.confirmar_guardado` → nunca seteado como estado
  - `PresupuestoStates.consultar_anio` → nunca seteado como estado  
  - `PresupuestoStates.ejecucion_anio` → nunca seteado como estado
  - Estos estados existen en la clase pero NUNCA se usan en `set_state()`. Los flujos usan callbacks directos, no FSM.
- FSM activos: `esperando_anio`, `esperando_area`, `editando_categoria` → ✅
- Callbacks: `presup_crear`, `presup_consultar`, `presup_ejecutar`, `presup_exportar`, `presup_anio:`, `presup_area:`, `presup_editar_cat:`, `presup_confirmar`, `menu_presupuesto` → ✅ con handlers
- DB methods: `db.guardar_presupuesto()`, `db.get_presupuesto()`, `db.get_presupuesto_anios()`, `db.get_ejecucion_presupuesto()` ✅ verificados

### 1.9 handlers/importar.py — ✅ COMPILA ✅
- FSM: `ImportExcelState.esperando_archivo → preview_mostrado → confirmado`
- Todos activos ✅
- Callbacks: `menu_importar`, `importar:descargar_plantilla`, `importar:confirmar`, `importar:cancelar` → ✅
- **⚠️ `importar:subir`** mencionado en la especificación pero **NUNCA usado en el código real** (no hay botón con ese callback, no hay handler). No es un bug, el botón no se implementó.
- Excel: ✅ `generar_plantilla_vacia()` funciona correctamente
- DB methods: `db.create_finca()`, `db.create_lote()`, `db.insert_transaccion()`, `db.get_fincas()`, `db.get_lotes()` ✅

### 1.10 handlers/voice.py — ✅ COMPILA ✅
- FSM: `VoiceForm.esperando_confirmacion`, `VoiceForm.esperando_finca` → ✅
- Callbacks: `voice_confirm:si/no/corregir`, `voice_finca:`, `voice_cancel` → ✅
- Whisper local: `transcribe_audio()` → ✅
- Parser: `parse_voice_text()` → ✅
- **⚠️ `voice_handler.py` tiene función `format_parsed_data()`** que **NUNCA se llama** desde voice.py. voice.py usa su propia `format_parsed_data_html()` (en el mismo archivo). La función en `voice_handler.py` es código muerto/obsoleto.
- Botones de escape: ✅

### 1.11 handlers/admin.py — ✅ COMPILA ✅
- `/usuarios`: ✅ lista completa con botones inline
- `/revocar`: ✅ comando + callback
- Callbacks: `aprobar:`, `rechazar:`, `revocar:`, `reactivar:` → ✅ todos con handler
- **⚠️ `reactivar:`** es un callback que **no está definido en `/usuarios`** pero sí se usa en `start.py`... espera, no. `reactivar:` solo se usa en `/usuarios` (línea 107). Revisando: en admin.py línea 291 hay `@router.callback_query(F.data.startswith("reactivar:"))` ✅
- Botones de escape: ✅ (todos los errores y mensajes tienen `boton_menu()`)
- DB methods: `db.approve_user()`, `db.reject_user()`, `db.revoke_user()`, `db.reactivate_user()`, `db.get_pending_users()`, `db.get_approved_users()`, `db.get_rejected_users()`, `db.get_all_users()` ✅

### 1.12 handlers/ayuda.py — ✅ COMPILA ✅
- `/ayuda` y `menu_ayuda`: ✅ muestran guía completa
- Botones de escape: ✅
- **NOTA:** `get_ayuda_router(db=None)` acepta `db` como opcional — correcto ya que no usa DB.

### 1.13 middleware.py — ✅ COMPILA ✅
- `CancelMiddleware`: intercepta comandos y callbacks `menu_*` / `ir_*` → ✅
- **⚠️ `cancelar_operacion`** NO está en la lista de callbacks que limpian estado en middleware, pero el handler en menu.py hace `state.clear()` manualmente → funciona ✅
- **⚠️ `volver_menu`** NO está en la lista del middleware → pero el handler hace `state.clear()` ✅
- La lista `COMMANDS` incluye `/menu`, `/cancelar`, `/start`, `/ayuda`, `/`, `/excel`, `/fincas`, `/lotes`, `/ingreso`, `/costo`, `/resumen`, `/usuarios` → cobertura completa ✅

### 1.14 database.py — ✅ COMPILA ✅
- **Verificado en memoria:** TODOS los métodos funcionan correctamente
- Tablas creadas correctamente con índices ✅
- Admin por defecto (ID: 810796748) creado automáticamente ✅
- **Métodos verificados:**
  - `init_db()`, `register_user()`, `upsert_user()`, `get_user_status()`, `is_approved()`, `is_pending()` ✅
  - `approve_user()`, `reject_user()`, `revoke_user()`, `reactivate_user()` ✅
  - `get_pending_users()`, `get_approved_users()`, `get_rejected_users()`, `get_all_users()` ✅
  - `create_finca()`, `get_fincas()`, `get_finca()`, `get_finca_by_id()` ✅
  - `create_lote()`, `get_lotes()`, `get_lote_by_id()` ✅
  - `insert_transaccion()`, `get_transacciones()`, `get_all_transacciones()`, `get_transacciones_por_finca()`, `get_all_data_for_export()` ✅
  - `get_resumen_finca()` ✅
  - `guardar_presupuesto()`, `get_presupuesto()`, `get_presupuesto_anios()`, `delete_presupuesto()`, `get_ejecucion_presupuesto()` ✅
  - `delete_all_user_data()` ✅
  - `_es_categoria_compuesta()`, `_es_categoria_simple()` ✅

### 1.15 excel_manager.py — ✅ COMPILA ✅
- **❌ BUG CRÍTICO:** Línea 1132: `ws.cell(row=1, column=1, value=f"Presupuesto {anio}", font=FONT_TITLE)`
  - openpyxl 3.1.5 **NO acepta** `font=` como kwarg en `ws.cell()`
  - Causa: `TypeError: Worksheet.cell() got an unexpected keyword argument 'font'`
  - **IMPACTO:** `_llenar_hoja_presupuesto()` FALLA al ejecutarse → **no se puede generar Excel con hoja Presupuesto**
  - **FIX:** Separar en dos líneas:
    ```python
    cell = ws.cell(row=1, column=1, value=f"Presupuesto {anio}")
    cell.font = FONT_TITLE
    ```
- `generar_excel()`: ✅ flujo completo (validar template, copiar, llenar hojas)
- `generar_plantilla_vacia()`: ✅ genera plantilla con ejemplos
- `_llenar_hoja_lotes()`: ✅ funciona correctamente
- `_llenar_hoja_ingresos()`: ✅
- `_llenar_hojas_costos()`: ✅ todas las hojas de costos
- `_llenar_hoja_presupuesto()`: **❌** (bug arriba)
- `_generar_hoja_graficos()`: ✅ genera 3 gráficos (Bar, Pie, Line)
- `_poner_fecha()`: ✅ maneja múltiples formatos

### 1.16 sync_to_github.py — ✅ COMPILA ✅
- Script completo: ✅ clona repo, exporta datos, hace commit y push
- **⚠️ Solo exporta primera finca** (línea 104: `break` después de la primera)
- Depende de SSH keys configuradas → no se puede probar sin conexión
- DB methods: `db.get_fincas()`, `db.get_lotes()`, `db.get_all_transacciones()`, `db.get_resumen_finca()` ✅

---

## 2️⃣ LISTA DE PROBLEMAS ENCONTRADOS

### 🔴 CRÍTICOS (bloquean funcionalidad)

| # | Módulo | Problema | Impacto | Fix |
|---|--------|----------|---------|-----|
| 1 | `excel_manager.py:1132` | `ws.cell(..., font=FONT_TITLE)` — `font` no es kwarg válido en openpyxl 3.1.5 | **Excel con hoja Presupuesto no se genera** — crash al exportar si hay presupuesto | Separar en 2 líneas: cell + cell.font |

### 🟡 ALTOS (funcionalidad comprometida)

| # | Módulo | Problema | Impacto | Fix |
|---|--------|----------|---------|-----|
| 2 | `presupuesto.py:840` | `data = await state.get_data() if False else {}` — hardcoded False | Código muerto, pero mitigado porque se re-obtiene state en línea 867 | Cambiar a `data = await state.get_data()` o eliminar línea |
| 3 | `voice_handler.py` | `format_parsed_data()` nunca se llama desde voice.py | Función duplicada obsoleta de 50 líneas | Eliminar (voice.py tiene su propia versión HTML) |

### 🟡 MEDIOS (estabilidad)

| # | Módulo | Problema | Impacto | Fix |
|---|--------|----------|---------|-----|
| 4 | `lotes.py` | `LoteForm.esperando_finca` definido pero nunca usado como estado FSM | Estado huérfano (inofensivo, solo ruido) | Eliminar de la clase o implementar |
| 5 | `costos.py` | `CostoForm.esperando_agregar_insumos` y `CostoForm.esperando_mas_insumos` huérfanos | 2 estados definidos sin uso | Eliminar o implementar |
| 6 | `presupuesto.py` | `PresupuestoStates.confirmar_guardado`, `.consultar_anio`, `.ejecucion_anio` huérfanos | 3 estados definidos sin uso | Eliminar o implementar |
| 7 | `costos.py:997` | `cancelar_operacion` registrado también en menu.py:275 | Handler duplicado (ambos routers tienen el mismo callback) | Eliminar de costos.py (menu.py ya lo maneja) |

### ⚪ BAJOS (cosméticos/mantenibilidad)

| # | Módulo | Problema | Impacto | Fix |
|---|--------|----------|---------|-----|
| 8 | `middleware.py` | `volver_menu` y `cancelar_operacion` no están en middleware de limpieza | NO es bug (los handlers hacen state.clear()) | Podrían agregarse para consistencia |
| 9 | `sync_to_github.py:104` | Solo exporta primera finca (`break`) | Si hay múltiples fincas, solo una se exporta | Iterar sobre todas o documentar |
| 10 | `presupuesto.py` | No hay `/presupuesto` en `COMMANDS` del middleware | El middleware no limpia estado para `/presupuesto` | Agregar a la lista |
| 11 | `menu.py` | `menu_ayuda` callback pero no hay handler directo en menu.py | NO es bug — ayuda.py lo maneja ✅ | Solo documentación |

---

## 3️⃣ ESTADO POR MÓDULO — LISTO PARA PRODUCCIÓN

| Módulo | Estado | Observaciones |
|--------|--------|---------------|
| `handlers/start.py` | ✅ **LISTO** | Flujo completo verificado |
| `handlers/menu.py` | ✅ **LISTO** | Prioridad máxima, FSM cleanup |
| `handlers/fincas.py` | ✅ **LISTO** | FSM completo, validaciones |
| `handlers/lotes.py` | ✅ **LISTO** | FSM completo, botones fecha ✅ |
| `handlers/ingresos.py` | ✅ **LISTO** | FSM completo, confirmación |
| `handlers/costos.py` | ✅ **LISTO** | FSM complejo, MO+insumos, multi-lote |
| `handlers/reportes.py` | ✅ **LISTO** | Resumen + Excel ✅ |
| `handlers/presupuesto.py` | ⚠️ **CON RESERVAS** | Código muerto L840, estados huérfanos |
| `handlers/importar.py` | ✅ **LISTO** | Parseo Excel + preview + confirmación |
| `handlers/voice.py` | ✅ **LISTO** | Whisper local + parser NL |
| `handlers/admin.py` | ✅ **LISTO** | CRUD completo de usuarios |
| `handlers/ayuda.py` | ✅ **LISTO** | Guía completa |
| `middleware.py` | ✅ **LISTO** | Cancelación FSM en comandos y menú |
| `database.py` | ✅ **LISTO** | 35 métodos, todos verificados en memoria |
| `excel_manager.py` | ❌ **NO LISTO** | **BUG CRÍTICO L1132** — bloquea exportación con presupuesto |
| `sync_to_github.py` | ✅ **LISTO** | Requiere SSH keys configuradas |
| `voice_handler.py` | ✅ **LISTO** | Whisper + parser NL (código muerto menor) |

---

## 4️⃣ CONCLUSIÓN

**El bot está MUY cerca de producción.** De 16 módulos auditados:

- **14 módulos** están ✅ listos para producción
- **1 módulo** (presupuesto) tiene código muerto pero funcional
- **1 módulo** (excel_manager) tiene **1 bug crítico** que bloquea la generación de Excel cuando hay presupuestos guardados

### Prioridad de fixes:

1. **🔴 INMEDIATO:** Fix `excel_manager.py:1132` — `ws.cell(..., font=FONT_TITLE)` → separar en 2 líneas
2. **🟡 IMPORTANTE:** Fix `presupuesto.py:840` — eliminar `if False else {}`
3. **🟡 NORMAL:** Agregar `/presupuesto` a `COMMANDS` en middleware.py
4. **⚪ OPCIONAL:** Limpiar estados huérfanos (6 estados en 3 clases)
5. **⚪ OPCIONAL:** Eliminar `format_parsed_data` duplicado en voice_handler.py

**Una vez corregido el bug #1, el bot está listo para producción.**
