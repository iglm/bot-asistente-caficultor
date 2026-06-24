# 📚 Referencia de API — Handlers del Bot ☕

> **Documentación técnica de cada handler, sus parámetros, retornos y ejemplos**
> Framework: aiogram 3.x | Filtros: Command, F.text, F.callback_query, F.voice

---

## 📁 Estructura de Handlers

```
handlers/
├── __init__.py   → Exporta todos los get_*_router()
├── menu.py       → /menu, /cancelar, borrar datos, volver
├── start.py      → /start, registro de usuarios
├── admin.py      → /usuarios, /aprobar, /revocar, /reactivar
├── fincas.py     → /fincas, crear finca
├── lotes.py      → /lotes, crear lote
├── ingresos.py   → /ingreso, registrar venta
├── costos.py     → /costo, registrar gasto (MO + insumos)
├── reportes.py   → /resumen, /excel, generar Excel
├── importar.py   → /importar, subir Excel, parsear, confirmar
├── ayuda.py      → /ayuda, guía de uso
└── voice.py      → Mensajes de voz, Whisper + parser NL
```

Cada handler exporta: `get_*_router(db: Database) -> Router`

---

## 1. 🏠 `menu.py` — Menú y Cancelación

### `get_menu_router(db)`
Router de **prioridad máxima**. Se registra primero en el dispatcher.

#### Comandos de texto

| Filtro | Función | Parámetros | Retorno |
|--------|---------|-------------|---------|
| `Command("menu")` | `cmd_menu()` | `event: Message, state: FSMContext` | Mensaje HTML con inline keyboard |
| `Command("cancelar")` | `cmd_menu()` | Ídem | Limpia estado + muestra menú |
| `F.text == "/"` | `cmd_menu()` | Ídem | Ídem |

**Comportamiento:** Llama `state.clear()` si hay estado FSM activo, luego construye el menú según el estado del usuario (pending/approved/admin).

#### Callbacks

| Callback | Handler | Descripción |
|----------|---------|-------------|
| `F.data == "ir_borrar"` | `menu_borrar()` | Muestra primera confirmación de borrado |
| `F.data.startswith("confirmar_borrar:")` | `confirmar_borrar()` | Segunda confirmación |
| `F.data.startswith("confirmar_borrar_2:")` | `confirmar_borrar_2()` | Ejecuta `db.delete_all_user_data()` |
| `F.data == "ir_admin"` | `menu_admin()` | Muestra panel admin |
| `F.data == "volver_menu"` | `volver_menu()` | Reconstruye menú principal |
| `F.data == "cancelar_operacion"` | `cancelar_operacion()` | `state.clear()` + mensaje |

**Ejemplo de flujo de borrado:**

```python
# El usuario presiona 🗑️ Borrar datos
# → menu_borrar() verifica si hay datos
# → Si hay: pide confirmación (1ra vez)
# → confirmar_borrar:si → pide CONFIRMACIÓN (2da vez, más fuerte)
# → confirmar_borrar_2:si → db.delete_all_user_data()
# → Muestra resumen de lo borrado
```

---

## 2. 🚀 `start.py` — Registro de usuarios

### `get_start_router(db)`

#### Comandos

| Filtro | Función | Parámetros |
|--------|---------|-------------|
| `CommandStart()` | `cmd_start()` | `message: Message` |

**Flujo detallado:**

```python
# 1. Obtener user_id, username, full_name del message.from_user
# 2. db.get_user_status(user_id)
# 
# Si status == None (nuevo usuario):
#   - db.register_user(user_id, username) → status = 'pending'
#   - Mensaje de bienvenida
#   - Notifica a todos los ADMIN_IDS con botones [✅ Aprobar] [❌ Rechazar]
#   - Notifica al NOTIFICATION_GROUP_ID
#
# Si status == 'approved':
#   - mostrar_menu_principal(message)
#
# Si status == 'pending':
#   - Mensaje: "Tu solicitud está en revisión"
#
# Si status == 'rejected':
#   - Mensaje: "Acceso denegado"
```

**Función helper:** `mostrar_menu_principal(message)` — construye inline keyboard idéntico al de `cmd_menu()` pero sin botón Admin.

---

## 3. 🔧 `admin.py` — Administración

### `get_admin_router(db)`

#### Comandos de texto

| Filtro | Función | Parámetros | Descripción |
|--------|---------|-------------|-------------|
| `Command("usuarios")` | `cmd_usuarios()` | `message: Message` | Lista aprobados/pendientes/rechazados con botones inline |
| `Command("revocar")` | `cmd_revocar()` | `message: Message` | `/revocar USER_ID` → cambia status a 'rejected' |

#### Callbacks

| Callback | Handler | Descripción |
|----------|---------|-------------|
| `F.data.startswith("aprobar:")` | `callback_aprobar()` | Aprueba usuario pendiente + notifica |
| `F.data.startswith("rechazar:")` | `callback_rechazar()` | Rechaza usuario pendiente + notifica |
| `F.data.startswith("revocar:")` | `callback_revocar()` | Revoca usuario aprobado + notifica |
| `F.data.startswith("reactivar:")` | `callback_reactivar()` | Reactiva usuario rechazado → pending |

**Ejemplo de callback:**

```python
@router.callback_query(F.data.startswith("aprobar:"))
async def callback_aprobar(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    db.approve_user(user_id, admin_id)
    # Notificar al usuario
    await callback.bot.send_message(
        user_id,
        "✅ ¡Felicidades! Tu solicitud ha sido aprobada."
    )
```

---

## 4. 🗺️ `fincas.py` — Gestión de Fincas

### `get_fincas_router(db)`

#### FSM: `FincaForm`

| State | Campo esperado | Validación |
|-------|----------------|------------|
| `esperando_nombre` | `F.text` (nombre) | No vacío, ≤100 chars, no duplicado |
| `esperando_region` | `F.text` (región) | Opcional (`/` para omitir) |
| `esperando_departamento` | `F.text` (depto) | Opcional (`/` para omitir) |

#### Comandos

| Filtro | Función |
|--------|---------|
| `Command("fincas")` | `cmd_fincas()` |
| `F.data == "menu_fincas"` | `cmd_fincas()` |

**Parámetros en `cmd_fincas()`:**

```python
event: types.Message | types.CallbackQuery  # Dual handler
state: FSMContext
```

**Retorno:** Mensaje HTML con lista de fincas + botón `[➕ Nueva Finca]`.

#### Llamadas a DB utilizadas

```python
db.get_fincas(user_id)           # Listar fincas
db.create_finca(user_id, nombre, region, departamento)  # Crear
```

---

## 5. 🌱 `lotes.py` — Gestión de Lotes

### `get_lotes_router(db)`

#### FSM: `LoteForm`

| State | Campo esperado | Validación |
|-------|----------------|------------|
| `esperando_nombre` | `F.text` | No vacío |
| `esperando_area` | `F.text` → `float` | ≥ 0 |
| `esperando_arboles` | `F.text` → `int` | ≥ 0 |
| `esperando_variedad` | `F.text` | Opcional (`/`) |
| `esperando_fecha_siembra` | `F.text` | DD/MM/AAAA o AAAA-MM-DD o `/` |

#### Comandos

| Filtro | Función |
|--------|---------|
| `Command("lotes")` | `cmd_lotes()` |
| `F.data == "menu_lotes"` | `cmd_lotes()` |

#### Callbacks

| Callback | Handler | Descripción |
|----------|---------|-------------|
| `F.data.startswith("lotes_finca:")` | `seleccionar_finca_lotes()` | Muestra lotes de finca específica |
| `F.data.startswith("nuevo_lote:")` | `nuevo_lote()` | Inicia creación de lote |

**Función helper:**

```python
async def mostrar_lotes(db, message, finca_id, finca_nombre, edit=False)
```
Muestra lista de lotes con nombres, área, árboles y variedad.

---

## 6. 💰 `ingresos.py` — Registrar Ingresos

### `get_ingresos_router(db)`

#### FSM: `IngresoForm`

| State | Campo esperado | Validación |
|-------|----------------|------------|
| `esperando_finca` | Callback `ingreso_finca:{id}` | Validar propiedad |
| `esperando_fecha` | `F.text` | DD/MM/AAAA o AAAA-MM-DD |
| `esperando_tipo` | Callback `tipo_cafe:{tipo}` | CPS, Pasilla o Re-re |
| `esperando_cantidad` | `F.text` → `float` | > 0 |
| `esperando_valor_total` | `F.text` → `float` | > 0 |
| `esperando_confirmar` | Callback `conf_ingreso:si/no` | — |

#### Tipos de café (desde `config.py`)

```python
TIPOS_CAFE_LIST = [
    "CPS (Café Pergamino Seco)",
    "Pasilla",
    "Re-re (Re-recolección)",
]
TIPOS_CAFE = {
    "CPS (Café Pergamino Seco)": "CPS",
    "Pasilla": "Pasilla",
    "Re-re (Re-recolección)": "Re-re",
}
```

**Mapeo a categorías DB:**

```python
{"CPS": "ingreso_cps", "Pasilla": "ingreso_pasilla", "Re-re": "ingreso_rere"}
```

---

## 7. 📉 `costos.py` — Registrar Costos

### `get_costos_router(db)`

#### FSM: `CostoForm` — **16 estados** (el más complejo)

| State | Descripción |
|-------|-------------|
| `esperando_finca` | Seleccionar finca |
| `esperando_lote` | `costo_lote:0` (toda la finca) o `costo_lote:{id}` |
| `esperando_categoria` | `cat_costo:{categoria_key}` |
| `esperando_fecha` | Fecha de la labor |
| `esperando_labor` | Descripción |
| `esperando_cantidad` | Jornales, kilos o N/A |
| `esperando_valor_unitario` | $/jornal |
| `esperando_valor_total` | Valor total o 'ok' |
| `esperando_agregar_insumos` | ¿Agregar insumos? |
| `esperando_producto` | Nombre del producto |
| `esperando_cantidad_insumo` | Cantidad |
| `esperando_valor_unitario_insumo` | $/unidad |
| `esperando_valor_total_insumo` | Valor total |
| `esperando_confirmar_mo` | Confirmar mano de obra |
| `esperando_confirmar_insumo` | Confirmar insumo |
| `esperando_mas_insumos` | ¿Otro insumo? |

#### Categorías disponibles

| Categoría | MO | Insumos | Tipo |
|-----------|----|---------|------|
| 🌱 Instalación | `instalacion_mo` | `instalacion_insumos` | Compuesta |
| 🌿 Arvenses | `arvenses_mo` | `arvenses_insumos` | Compuesta |
| 🧪 Fertilización | `fertilizacion_mo` | `fertilizacion_insumos` | Compuesta |
| 🛡️ Fitosanitario | `fitosanitario_mo` | `fitosanitario_insumos` | Compuesta |
| 🌳 Sombrío | `sombrio_mo` | `sombrio_insumos` | Compuesta |
| 🔧 Otras Labores | `otras_labores_mo` | `otras_labores_insumos` | Compuesta |
| ☕ Recolección | `recoleccion` | — | Simple |
| 🏭 Beneficio | `beneficio` | — | Simple |
| 📋 Administrativo | `administrativo` | — | Simple |

**Función helper `guardar_mo()`:**

```python
async def guardar_mo(db, message, data, state):
    # Determina categoria_db según cat_key
    # Inserta en db.insert_transaccion() con unidad="jornal"
    # Para admin: cantidad=1, vu=valor_total
```

---

## 8. 📊 `reportes.py` — Resumen y Excel

### `get_reportes_router(db)`

#### Comandos

| Filtro | Función | Descripción |
|--------|---------|-------------|
| `Command("resumen")` | `cmd_resumen()` | Ver resumen financiero |
| `F.data == "menu_resumen"` | `cmd_resumen()` | Ídem desde menú |

#### Callbacks

| Callback | Handler | Descripción |
|----------|---------|-------------|
| `F.data.startswith("resumen_finca:")` | `seleccionar_finca_resumen()` | Resumen de finca específica |
| `F.data == "menu_excel"` | `cmd_generar_excel()` | Inicia exportación |
| `F.data.startswith("generar_excel:")` | `cmd_generar_excel()` | Genera Excel para finca específica |

#### Función helper `mostrar_resumen()`

```python
async def mostrar_resumen(db, send_func, finca_id, finca_nombre):
    """
    Args:
        db: Database instance
        send_func: callable (message.answer o message.edit_text)
        finca_id: int
        finca_nombre: str
    
    Retorna: None (envía mensaje con el resumen)
    
    Datos mostrados:
    - Área total (ha)
    - Ingresos totales ($)
    - Egresos totales ($)
    - Margen ($, con indicador ✅/❌)
    - Costo por hectárea ($/ha)
    - Egresos por categoría (ordenados, con %)
    - Ingresos por tipo (CPS, Pasilla, Re-re)
    - Botón [📊 Generar Excel]
    """
```

#### Exportación de Excel

```python
# Con datos:
manager = ExcelManager(EXCEL_TEMPLATE)
manager.generar_excel(finca_id, db, output_path)

# Sin datos (plantilla vacía):
manager.generar_plantilla_vacia(output_path)
```

**Retorno:** Archivo .xlsx enviado como `answer_document()`.

---

## 9. 📥 `importar.py` — Importar Excel

### `get_importar_router(db)`

#### FSM: `ImportExcelState`

| State | Descripción |
|-------|-------------|
| `esperando_archivo` | Esperando archivo .xlsx |
| `preview_mostrado` | Preview visible, esperando confirmación |
| `confirmado` | Importando datos |

#### Callbacks

| Callback | Handler | Descripción |
|----------|---------|-------------|
| `F.data == "menu_importar"` | `menu_importar()` | Inicia flujo |
| `F.data == "importar:descargar_plantilla"` | `descargar_plantilla()` | Genera plantilla vacía |
| `F.data == "importar:cancelar"` | `cancelar_importacion()` | Cancela |
| `F.data == "importar:confirmar"` | `confirmar_importacion()` | Ejecuta importación |

#### Hojas esperadas en el Excel

```python
HOJAS_ESPERADAS = {
    "Fincas": ["nombre", "region", "departamento"],
    "Lotes": ["finca_nombre", "nombre", "area_hectareas", "num_arboles", "variedad", "fecha_siembra"],
    "Ingresos": ["finca_nombre", "tipo", "fecha", "cantidad", "valor_total"],
    "Costos_MO": ["finca_nombre", "lote_nombre", "categoria", "fecha", "labor", "cantidad", "valor_unitario", "valor_total"],
    "Costos_Insumos": ["finca_nombre", "lote_nombre", "categoria", "fecha", "producto", "cantidad", "unidad", "valor_unitario", "valor_total"],
}
```

**Validaciones:**

```python
CATEGORIAS_MO_VALIDAS = [
    "instalacion_mo", "arvenses_mo", "fertilizacion_mo",
    "fitosanitario_mo", "sombrio_mo", "otras_labores_mo",
    "recoleccion", "beneficio", "administrativo",
]
CATEGORIAS_INSUMOS_VALIDAS = [
    "instalacion_insumos", "arvenses_insumos", "fertilizacion_insumos",
    "fitosanitario_insumos", "sombrio_insumos", "otras_labores_insumos",
]
```

---

## 10. ❓ `ayuda.py` — Guía de uso

### `get_ayuda_router(db)`

| Filtro | Función | Descripción |
|--------|---------|-------------|
| `Command("ayuda")` | `cmd_ayuda()` | Muestra guía completa |
| `F.data == "menu_ayuda"` | `cmd_ayuda()` | Ídem |

**Retorno:** Mensaje HTML dividido en partes si excede 4096 chars.

---

## 11. 🎤 `voice.py` — Mensajes de voz

### `get_voice_router(db)`

#### FSM: `VoiceForm`

| State | Descripción |
|-------|-------------|
| `esperando_confirmacion` | Mostrando datos parseados, esperando confirmación |
| `esperando_finca` | Seleccionando finca (si tiene varias) |

#### Filtros

| Filtro | Función | Descripción |
|--------|---------|-------------|
| `F.voice` | `handle_voice()` | Recibe voz → descarga .ogg → Whisper → parse → muestra |
| `F.data == "voice_confirm:si"` | `confirmar_voz()` | Guarda transacción |
| `F.data == "voice_confirm:no"` | `cancelar_voz()` | Cancela |
| `F.data == "voice_confirm:corregir"` | `corregir_voz()` | Pide corrección manual |
| `F.data.startswith("voice_finca:")` | `seleccionar_finca_voz()` | Selecciona finca |

**Dependencias externas:**

```python
from voice_handler import transcribe_audio  # Whisper local
from voice_handler import parse_voice_text  # Parser NL
```

---

## 🛠️ `middleware.py` — CancelMiddleware

### `CancelMiddleware(BaseMiddleware)`

```python
class CancelMiddleware(BaseMiddleware):
    COMMANDS = {"/menu", "/cancelar", "/start", "/ayuda", "/",
                "/excel", "/fincas", "/lotes", "/ingreso",
                "/costo", "/resumen", "/usuarios"}
    
    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.text:
            cmd = event.text.split("@")[0].lower()
            if cmd in self.COMMANDS:
                state = data.get("state")
                if state:
                    await state.clear()
        
        if isinstance(event, CallbackQuery):
            if event.data.startswith("menu_") or event.data.startswith("ir_"):
                state = data.get("state")
                if state:
                    await state.clear()
        
        return await handler(event, data)
```

---

## 🗄️ `database.py` — Referencia de métodos

### Usuarios

| Método | Retorno | Descripción |
|--------|---------|-------------|
| `upsert_user(user_id, username)` | None | Insertar o ignorar |
| `register_user(user_id, username)` | `bool` | True si era nuevo |
| `get_user_status(user_id)` | `str` o None | 'pending', 'approved', 'rejected' |
| `is_approved(user_id)` | `bool` | status == 'approved' |
| `approve_user(user_id, admin_id)` | `bool` | pending → approved |
| `reject_user(user_id)` | `bool` | pending → rejected |
| `revoke_user(user_id)` | `bool` | approved → rejected |
| `reactivate_user(user_id)` | `bool` | rejected → pending |
| `delete_all_user_data(user_id)` | `dict` | {fincas, lotes, transacciones} |
| `get_pending_users()` | `list[dict]` | Usuarios pendientes |
| `get_approved_users()` | `list[dict]` | Usuarios aprobados |
| `get_all_users()` | `list[dict]` | Todos |

### Fincas

| Método | Retorno |
|--------|---------|
| `create_finca(user_id, nombre, region, depto)` | `int` (ID) |
| `get_fincas(user_id)` | `list[dict]` |
| `get_finca(finca_id)` | `dict` o None |

### Lotes

| Método | Retorno |
|--------|---------|
| `create_lote(finca_id, nombre, área, árboles, variedad, fecha)` | `int` (ID) |
| `get_lotes(finca_id)` | `list[dict]` |
| `get_lote_by_id(lote_id)` | `dict` o None |

### Transacciones

| Método | Retorno |
|--------|---------|
| `insert_transaccion(finca_id, categoria, fecha, ...)` | `int` (ID) |
| `get_transacciones(finca_id, categoria)` | `list[dict]` |
| `get_all_transacciones(finca_id)` | `list[dict]` |
| `get_transacciones_por_finca(finca_id)` | `dict` por categoría |
| `get_all_data_for_export(finca_id)` | `dict` completo |
| `get_resumen_finca(finca_id)` | `dict` con ingresos, egresos, margen |

### Helpers estáticos

| Método | Descripción |
|--------|-------------|
| `_es_categoria_compuesta(cat)` | True si tiene MO + Insumos |
| `_es_categoria_simple(cat)` | True si solo MO |

**Constantes:**

```python
CATEGORIAS_CON_MO_Y_INSUMOS = [
    "instalacion", "arvenses", "fertilizacion",
    "fitosanitario", "sombrio", "otras_labores",
]
CATEGORIAS_SIMPLE = ["recoleccion", "beneficio", "administrativo"]
```
