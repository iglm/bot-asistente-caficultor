# AUDITORÍA EXHAUSTIVA — Bot Asistente Caficultor → Mini App

> **Fecha:** 2026-06-26
> **Proyecto:** Asistente de Costos para Caficultores ☕
> **Ruta:** `/home/lucas-mateo/bot-asistente-caficultor/`

---

## ÍNDICE

1. [ESTRUCTURA DEL PROYECTO](#1-estructura-del-proyecto)
2. [CONFIGURACIÓN (config.py)](#2-configuración-configpy)
3. [BASE DE DATOS (database.py) — TODOS LOS MÉTODOS](#3-base-de-datos-databasepy)
4. [HANDLERS — CADA FUNCIONALIDAD](#4-handlers)
5. [EXCEL MANAGER (excel_manager.py)](#5-excel-manager-excel_managerpy)
6. [VOICE HANDLER (voice_handler.py)](#6-voice-handler-voice_handlerpy)
7. [UTILS (utils.py)](#7-utils-utilspy)
8. [MIDDLEWARE (middleware.py)](#8-middleware-middlewarepy)
9. [MAIN (main.py)](#9-main-mainpy)
10. [MINI APP EXISTENTE](#10-mini-app-existente)
11. [SHARED DATABASE](#11-shared-database)
12. [REQUERIMIENTOS PARA LA API DE LA MINI APP](#12-requerimientos-api-mini-app)
13. [PANTALLAS NECESARIAS EN LA MINI APP](#13-pantallas-mini-app)

---

## 1. ESTRUCTURA DEL PROYECTO

```
bot-asistente-caficultor/
├── main.py                    # Entry point del bot
├── config.py                  # Configuración central
├── database.py                # Database SQLite (bot original)
├── utils.py                   # Helpers UI (botones, menús)
├── middleware.py               # Middleware de cancelación FSM
├── excel_manager.py           # Exportación/Importación Excel
├── voice_handler.py           # Transcripción Whisper + parser NL
├── sync_to_github.py          # Script de sincronización
├── requirements.txt           # Dependencias del bot
├── .env.example               # Variables de entorno ejemplo
│
├── handlers/
│   ├── __init__.py            # Exporta todos los routers
│   ├── start.py               # /start — registro, aviso legal
│   ├── menu.py                # /menu, /cancelar, borrar datos, admin, pdf, dashboard
│   ├── fincas.py              # /fincas — CRUD fincas
│   ├── lotes.py               # /lotes — CRUD lotes
│   ├── ingresos.py            # /ingreso — registrar ventas de café
│   ├── costos.py              # /costo — registrar costos de producción
│   ├── reportes.py            # /resumen, /filtrar, Excel, PDF
│   ├── admin.py               # /usuarios, /revocar, aprobar/rechazar
│   ├── importar.py            # Importar Excel masivo
│   ├── ayuda.py               # /ayuda — guía de uso
│   ├── voice.py               # Procesamiento de voz (Whisper)
│   ├── presupuesto.py         # /presupuesto — planificación
│   └── indicadores.py         # /indicadores — KPIs técnicos
│   └── asesoria.py            # /asesoria — interpretación y consejos
│
├── shared/
│   ├── __init__.py            # Exporta Database compartida
│   └── database.py            # DB thread-safe (Bot + Mini App)
│
├── mini-app/
│   ├── api/
│   │   ├── app.py             # API FastAPI existente
│   │   └── requirements.txt   # fastapi, uvicorn, pydantic
│   └── robots.txt
│
├── data/
│   ├── finca.db               # SQLite database
│   └── plantilla/
│       └── Costos de produccion - 2026.xlsx  # Template Excel (openpyxl)
├── mini-app/
│   ├── api/
│   │   ├── app.py             # API FastAPI (uvicorn)
│   │   └── requirements.txt
│
├── exports/                   # Archivos exportados temporales
├── tests/                     # Tests E2E y simulaciones
└── docs/                      # Documentación
```

---

## 2. CONFIGURACIÓN (config.py)

### Constantes y Configuraciones

| Constante | Valor | Descripción |
|-----------|-------|-------------|
| `BOT_TOKEN` | `~/.bot_token_caficultor.txt` o env var | Token de Telegram |
| `ADMIN_IDS` | `[810796748]` por defecto | IDs de administradores |
| `NOTIFICATION_GROUP_ID` | `-1003545220692` | Grupo de notificaciones |
| `DB_PATH` | `data/finca.db` | Ruta BD SQLite |
| `EXCEL_TEMPLATE` | `data/plantilla/Costos de produccion - 2026.xlsx` | Template Excel |
| `EXPORTS_DIR` | `exports/` | Directorio de exportaciones |
| `AVISO_LEGAL` | Texto largo | Aviso legal Ley 1581/2012 |
| `ASESORIA_EMAIL` | `mateotabares7@gmail.com` | Email de asesoría |
| `ASESOR_NOMBRE` | `Lucas Mateo Tabares Franco` | Desarrollador |
| `ASESOR_ASESOR` | `Ing. Jhoan Sebastian Bustamante Montes` | Asesor técnico |
| `BOT_NAME` | `Asistente Caficultor ☕` | Nombre del bot |

### CATEGORÍAS DE COSTOS

#### CATEGORIAS_PADRE (tienen MO + Insumos)
```python
instalacion    → instalacion_mo + instalacion_insumos
arvenses       → arvens_mo + arvens_insumos
fertilizacion  → fertilizacion_mo + fertilizacion_insumos
fitosanitario  → fitosanitario_mo + fitosanitario_insumos
sombrio        → sombrio_mo + sombrio_insumos
otras_labores  → otras_labores_mo + otras_labores_insumos
```

#### CATEGORIAS_SIMPLE (solo MO)
```python
recoleccion    → recoleccion
beneficio      → beneficio
administrativo → administrativo
```

#### CATEGORIAS_COMPLETAS (para Excel)
19 categorías totales en el dict `CATEGORIAS`:
- `ingreso_cps`, `ingreso_pasilla` (ingresos)
- `instalacion_mo`, `instalacion_insumos`, `instalacion`
- `arvenses_mo`, `arvenses_insumos`, `arvenses`
- `fertilizacion_mo`, `fertilizacion_insumos`, `fertilizacion`
- `fitosanitario_mo`, `fitosanitario_insumos`, `fitosanitario`
- `sombrio_mo`, `sombrio_insumos`, `sombrio`
- `otras_labores_mo`, `otras_labores_insumos`, `otras_labores`
- `recoleccion`, `beneficio`, `administrativo`

### TIPOS DE CAFÉ
```python
TIPOS_CAFE_LIST = ["CPS (Café Pergamino Seco)", "Pasilla"]
```

### UNIDADES DE INSUMO
```python
UNIDADES_INSUMO = ['g', 'kg', 'mg', 'ml', 'l', 'bulto']
UNIDADES_SOLIDOS = {'g', 'kg', 'mg', 'bulto'}  # → kg
UNIDADES_LIQUIDOS = {'ml', 'l'}                 # → L
```

### PRESUPUESTO PORCENTAJES (FNC/FEPCafé 2024)
```python
PRESUPUESTO_PORCENTAJES = {
    "recoleccion": 0.54, "fertilizacion": 0.19, "administrativo": 0.07,
    "arvenses": 0.06, "beneficio": 0.06, "fitosanitario": 0.02,
    "renovacion": 0.05, "otras_labores": 0.01,
}
RUBROS_GLOBALES = ["administrativo", "beneficio"]  # Aplican a toda la finca
```

### INDICADORES FNC DE REFERENCIA
```python
FNC_INDICADORES = {
    "precio_venta_promedio": 17700,
    "costo_produccion_kilo": 9790,
    "productividad_ha": 1669,
    "rendimiento_ha": 2087,
    "area_promedio": 2.9,
    "costo_ha": 16340000,
    "margen_ha": 13164000,
    "productividad_pais_sacos_ha": 21,
    "carga_kg_ha": 1500,
}
```

### Función de conversión
```python
convertir_a_estandar(cantidad, unidad) → (cantidad_convertida, unidad_estandar)
```

---

## 3. BASE DE DATOS (database.py) — TODOS LOS MÉTODOS

### Tablas SQLite
1. **usuarios** — user_id, username, nombre, telefono, status, admin_id, created_at, approved_at, acepto_terminos
2. **fincas** — id, user_id, nombre, region, departamento, created_at
3. **lotes** — id, finca_id, nombre, area_hectareas, num_arboles, variedad, fecha_siembra
4. **transacciones** — id, finca_id, lote_id, categoria, fecha, labor, producto, cantidad, unidad, valor_unitario, valor_total, created_at
5. **presupuestos** — id, finca_id, anio, categoria, monto_planificado, created_at (UNIQUE finca_id, anio, categoria)
6. **presupuesto_detalle** — id, presupuesto_id, lote_id, rubro, mes, cantidad_plan, unidad, valor_unitario, valor_total_plan
7. **gastos_reales** — id, finca_id, lote_id, fecha, rubro, labor, insumo, cantidad, unidad, valor_unitario, valor_total, estado
8. **sync_queue** — id, action, data, created_at

### Métodos — Usuarios
| Método | Parámetros | Retorna | Descripción |
|--------|-----------|---------|-------------|
| `upsert_user` | user_id, username | void | Inserta o ignora usuario |
| `register_user` | user_id, username | bool | True si era nuevo |
| `get_user_status` | user_id | str\|None | 'pending', 'approved', 'rejected' |
| `is_approved` | user_id | bool | Status == 'approved' |
| `is_pending` | user_id | bool | Status == 'pending' |
| `approve_user` | user_id, approved_by | bool | pending → approved |
| `reject_user` | user_id | bool | pending → rejected |
| `get_pending_users` | | list | Usuarios pendientes |
| `get_all_users` | | list | Todos los usuarios |
| `get_approved_users` | | list | Usuarios aprobados |
| `get_rejected_users` | | list | Usuarios rechazados |
| `get_user` | user_id | dict\|None | Todos los campos del usuario |
| `aceptar_terminos` | user_id | bool | Marca acepto_terminos=1 |
| `revoke_user` | user_id | bool | approved → rejected |
| `reactivate_user` | user_id | bool | rejected → pending |
| `delete_all_user_data` | user_id | dict{fincas,lotes,transacciones} | Borra todo |

### Métodos — Fincas
| Método | Parámetros | Retorna |
|--------|-----------|---------|
| `create_finca` | user_id, nombre, region, departamento | int (id) |
| `get_fincas` | user_id | list[dict] |
| `get_finca` | finca_id | dict\|None |
| `get_finca_by_id` | finca_id | dict\|None (alias) |

### Métodos — Lotes
| Método | Parámetros | Retorna |
|--------|-----------|---------|
| `create_lote` | finca_id, nombre, area, num_arboles, variedad, fecha_siembra | int (id) |
| `get_lotes` | finca_id | list[dict] |
| `get_lote_by_id` | lote_id | dict\|None |

### Métodos — Transacciones
| Método | Parámetros | Retorna |
|--------|-----------|---------|
| `insert_transaccion` | finca_id, categoria, fecha, labor, producto, cantidad, unidad, valor_unitario, valor_total, lote_id | int (id) |
| `get_transacciones_por_periodo` | finca_id, fecha_inicio, fecha_fin | list[dict] |
| `get_resumen_por_periodo` | finca_id, fecha_inicio, fecha_fin | dict |
| `get_resumen_semanal` | finca_id, año, semana | dict |
| `get_resumen_mensual` | finca_id, año, mes | dict |
| `get_resumen_anual` | finca_id, año | dict |
| `get_transacciones` | finca_id, categoria | list[dict] |
| `get_all_transacciones` | finca_id | list[dict] |
| `get_transacciones_finca` | finca_id | list[dict] (alias) |
| `get_transacciones_por_finca` | finca_id | dict{categoria: [transacciones]} |
| `get_all_data_for_export` | finca_id | dict (completo para Excel) |
| `get_resumen_finca` | finca_id | dict (resumen financiero) |
| `simular_datos_finca` | finca_id | void (datos de ejemplo) |

### Métodos — Presupuestos
| Método | Parámetros | Retorna |
|--------|-----------|---------|
| `guardar_presupuesto` | finca_id, anio, datos(categoria→monto) | void |
| `get_presupuesto` | finca_id, anio | list[dict] |
| `get_presupuesto_anios` | finca_id | list[int] |
| `get_anios_con_datos` | finca_id | list[int] |
| `delete_presupuesto` | finca_id, anio | void |
| `guardar_detalle_presupuesto` | presupuesto_id, detalle | bool |
| `get_ejecucion_presupuesto` | finca_id, anio | dict (plan vs real) |
| `get_ejecucion_por_periodo` | finca_id, fecha_inicio, fecha_fin | dict |
| `get_gastos_por_rubro` | finca_id, fecha_inicio, fecha_fin | list[dict] |

### Métodos — Indicadores Técnicos
| Método | Parámetros | Retorna |
|--------|-----------|---------|
| `_lote_es_productivo` | lote | bool |
| `_get_total_insumos_cantidad_convertida` | finca_id | dict{total_kg, total_litros, total_estandar} |
| `_get_total_ingresos` | finca_id | float |
| `_get_costos_por_tipo` | finca_id, tipo('mo'\|'insumos') | float |
| `_get_kg_producidos` | finca_id | float |
| `_get_total_jornales` | finca_id | float |
| `get_indicadores_tecnicos` | finca_id | dict (25+ KPIs) |

### Métodos — Sync Queue
| Método | Parámetros | Retorna |
|--------|-----------|---------|
| `add_sync_queue` | action, data | void |
| `get_sync_queue` | | list[dict] |
| `process_sync_queue` | | void |

---

## 4. HANDLERS

### 4.1 START (`handlers/start.py`)

| Comando/Callback | Funcionalidad | Datos que solicita | Respuesta |
|-----------------|---------------|-------------------|-----------|
| `/start` | Inicio del bot | — | Verifica si aceptó términos → Sí: menú principal. No: aviso legal |
| `aceptar_terminos` | Acepta aviso legal | user_id | Marca acepto_terminos=1, muestra menú principal |
| `no_aceptar_terminos` | Rechaza términos | — | Mensaje de rechazo, no puede usar el bot |
| — (notificar_admin_nuevo_usuario) | Notifica a admins | user_id, username | Envía mensaje a ADMIN_IDS + NOTIFICATION_GROUP_ID con botones aprobar/rechazar |

### 4.2 MENÚ (`handlers/menu.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/menu`, `/cancelar`, `/` | Menú principal | user_id | Limpia FSM, muestra menú u "esperando aprobación" |
| `ir_borrar` | Inicia borrado de datos | user_id | Pregunta confirmación |
| `confirmar_borrar:si` | 1ra confirmación | user_id | Pide 2da confirmación + advertencia |
| `confirmar_borrar:no` | Cancela borrado | — | "Operación cancelada" |
| `confirmar_borrar_2:si` | Ejecuta borrado | user_id | `delete_all_user_data()` + resumen |
| `confirmar_borrar_2:no` | Cancela borrado | — | "Operación cancelada" |
| `ir_admin` | Panel de admin | user_id | Muestra comandos admin si es admin |
| `volver_menu` | Vuelve al menú | user_id | Limpia FSM, muestra menú principal |
| `cancelar_operacion` | Cancela operación | — | Limpia FSM, muestra menú |
| `menu_pdf` | Exportar PDF | fincas | Selecciona finca → redirige a indicadores |
| `menu_dashboard` | Dashboard | fincas | Selecciona finca → vista de indicadores |

### 4.3 FINCAS (`handlers/fincas.py`)

| Comando/Callback | Funcionalidad | Datos solicitados | Respuesta |
|-----------------|---------------|-------------------|-----------|
| `/fincas`, `menu_fincas` | Menú fincas | user_id | Lista fincas + botón "Nueva Finca" |
| `nueva_finca` | Crear finca paso 1 | — | Pide nombre |
| FSM: esperando_nombre | Recibe nombre | nombre (texto) | Valida duplicados, pide región |
| FSM: esperando_region | Recibe región | región (texto o '/') | Guarda, pide departamento |
| FSM: esperando_departamento | Recibe depto y crea | departamento | `create_finca()`, muestra confirmación |

### 4.4 LOTES (`handlers/lotes.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/lotes`, `menu_lotes` | Menú lotes | user_id | Si 1 finca→ muestra lotes. Si varias→ selector |
| `lotes_finca:X` | Selecciona finca | finca_id | Muestra lotes de esa finca |
| `nuevo_lote:X` | Crear lote paso 1 | finca_id, finca_nombre | Pide nombre del lote |
| FSM: esperando_nombre | Recibe nombre | nombre | Valida, pide área |
| FSM: esperando_area | Recibe área | float | Valida, pide #árboles |
| FSM: esperando_arboles | Recibe árboles | int | Pide variedad |
| FSM: esperando_variedad | Recibe variedad | texto o '/' | Pide fecha siembra |
| FSM: esperando_fecha_siembra (text) | Recibe fecha | DD/MM/AAAA o '/' | `create_lote()`, confirmación |
| `fecha:hoy`/`fecha:ayer` | Atajo fecha | — | Usa fecha actual/ayer |
| FSM: entradas inválidas | Validación | — | Mensaje de error |

### 4.5 INGRESOS (`handlers/ingresos.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/ingreso`, `menu_ingresos` | Inicia registro ingreso | user_id | Si 1 finca→pide fecha. Si varias→selector |
| `ingreso_finca:X` | Selecciona finca | finca_id | Pide fecha |
| FSM: esperando_fecha | Recibe fecha | DD/MM/AAAA | Guarda, pide tipo café |
| `fecha:hoy`/`fecha:ayer` | Atajo fecha | — | Misma lógica |
| `tipo_cafe:X` | Selecciona tipo | CPS o Pasilla | Pide cantidad (kg) |
| FSM: esperando_cantidad | Recibe kg | float>0 | Pide valor total |
| FSM: esperando_valor_total | Recibe $ total | float>0 | Muestra resumen con Confirmar/Editar/Cancelar |
| `conf_ingreso:si` | Confirma | data FSM | `insert_transaccion()` con categoría ingreso_cps o ingreso_pasilla |
| `conf_ingreso:no` | Cancela | — | Mensaje cancelación |
| `editar_ingreso` | Editar | — | Menú de campos editables |
| `edit_ingreso_fecha` | Editar fecha | — | Pide nueva fecha |
| `edit_ingreso_cantidad` | Editar cantidad | — | Pide nueva cantidad |
| `edit_ingreso_valor_total` | Editar valor | — | Pide nuevo valor |
| `volver_resumen_ingreso` | Volver | — | Muestra resumen actualizado |

### 4.6 COSTOS (`handlers/costos.py`) — EL MÁS COMPLEJO

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/costo`, `menu_costos` | Inicia registro costo | user_id | Si 1 finca→ muestra lotes. Si varias→selector |
| `costo_finca:X` | Selecciona finca | finca_id | Muestra opciones de lote |
| `costo_lote:todos` | Toda la finca | — | Aplica a todos los lotes |
| `costo_lote:especifico` | Lote específico | — | Lista lotes para elegir |
| `costo_lote:seleccionar` | Múltiples lotes | — | Checkboxes con toggle |
| `toggle_lote:X` | Toggle lote | lote_id | Activa/desactiva en selección |
| `costo_lote:confirmar_seleccion` | Confirma selección | lotes_seleccionados | Avanza a categorías |
| `cat_costo:X` | Selecciona categoría | cat_key | Si tiene MO+Insumos→elige tipo. Si no→pide fecha |
| `registrar_mo` | Solo MO | — | Flujo MO: labor→cantidad→valor unitario→total |
| `registrar_insumos` | Solo Insumos | — | Flujo insumos: producto→unidad→cantidad→VU→total |
| `registrar_ambos` | MO + Insumos | — | Primero MO, luego insumos automáticamente |
| FSM: esperando_fecha | Recibe fecha | DD/MM/AAAA | Guarda fecha |
| FSM: esperando_labor | Recibe labor | texto | Guarda labor |
| FSM: esperando_cantidad | Recibe cantidad | float>0 | Para recolección→kg. Para otros→jornales |
| FSM: esperando_valor_unitario | Recibe VU | float>0 | Calcula total, pregunta confirmar |
| FSM: esperando_valor_total | Recibe VT o 'ok' | float o 'ok' | Muestra resumen |
| `conf_costo_mo:si` | Confirma MO | data FSM | `guardar_mo()`, si "ambos"→pasa a insumos |
| `conf_costo_mo:no` | Cancela MO | — | Mensaje cancelación |
| `editar_costo_mo` | Editar MO | — | Menú según categoría |
| `edit_mo_fecha/labor/cantidad/valor_unitario/valor_total` | Campos editables | — | Pide nuevo valor |
| — FLUJO INSUMOS — | | | |
| FSM: esperando_producto | Recibe producto | texto | Pide unidad |
| `unidad_insumo:X` | Selecciona unidad | g, kg, ml, l, bulto | Pide cantidad |
| FSM: esperando_cantidad_insumo | Cantidad insumo | float | Pide VU |
| FSM: esperando_valor_unitario_insumo | VU insumo | float | Pide VT o 'ok' |
| `conf_insumo:si` | Confirma insumo | data FSM | `insert_transaccion()` con categoría *_insumos |
| `conf_insumo:no` | Cancela insumo | — | Mensaje |
| `agregar_otro_insumo` | Otro insumo | — | Vuelve a pedir producto |
| `terminar_costo` | Termina | — | Limpia FSM, mensaje final |
| `editar_insumo` | Editar insumo | — | Menú edición |
| `edit_insumo_producto/cantidad/vu` | Editar campos | — | Pide nuevo valor |

### 4.7 REPORTES (`handlers/reportes.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/resumen`, `menu_resumen` | Resumen financiero | user_id | Si 1 finca→muestra resumen. Varias→selector |
| `resumen_finca:X` | Selecciona finca | finca_id | `get_resumen_finca()` → texto con ingresos, egresos, margen, categorías |
| `menu_excel` | Exportar Excel | fincas | Si sin fincas→plantilla vacía. Si 1→genera. Varias→selector |
| `generar_excel:X` | Genera Excel | finca_id | `ExcelManager.generar_excel()`, envía .xlsx |
| `resumen_pdf:X` | Exporta PDF | finca_id | Genera PDF con FPDF, envía archivo |
| `/filtrar`, `menu_filtrar` | Filtrar por período | fincas | Menú: semana, mes, año, personalizado |
| `filtrar:semana/mes/anio:X:...` | Ejecuta filtro | finca_id, período | `get_resumen_semanal/mensual/anual()` |
| `filtrar:personalizado:X` | Filtro personalizado | finca_id | Pide fecha inicio y fin |
| FSM: esperando_fecha_inicio | Recibe inicio | DD/MM/AAAA | Pide fecha fin |
| FSM: esperando_fecha_fin | Recibe fin | DD/MM/AAAA | `get_resumen_por_periodo()` |
| `excel_periodo:X:inicio:fin` | Excel del período | finca_id, fechas | Genera Excel + hoja período |

### 4.8 ADMIN (`handlers/admin.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/usuarios` | Lista usuarios | admin check | Muestra aprobados, pendientes, rechazados + botones |
| `/revocar USER_ID` | Revoca acceso | target_id | `revoke_user()`, notifica al usuario |
| `aprobar:X` | Aprueba usuario | user_id | `approve_user()`, notifica al usuario |
| `rechazar:X` | Rechaza usuario | user_id | `reject_user()`, notifica |
| `revocar:X` | Revoca callback | user_id | `revoke_user()`, notifica |
| `reactivar:X` | Reactiva usuario | user_id | `reactivate_user()`, notifica |

### 4.9 IMPORTAR EXCEL (`handlers/importar.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `menu_importar` | Inicia importación | — | Explica formato, espera archivo .xlsx |
| `importar:descargar_plantilla` | Descargar plantilla | — | Genera plantilla vacía desde template |
| Documento .xlsx recibido | Procesa archivo | archivo | Parse hojas: Fincas, Lotes, Ingresos, Costos_MO, Costos_Insumos |
| — | Validación | — | Valida headers, categorías, muestra errores |
| — | Preview | — | Muestra resumen de datos a importar |
| `importar:confirmar` | Ejecuta importación | datos_importados | Crea fincas→lotes→ingresos→costos MO→costos insumos |
| `importar:cancelar` | Cancela | — | Mensaje cancelación |

### 4.10 AYUDA (`handlers/ayuda.py`)

| Comando/Callback | Funcionalidad | Respuesta |
|-----------------|---------------|-----------|
| `/ayuda`, `menu_ayuda` | Guía de uso | Texto extenso con comandos, cómo empezar, tipos de café, reportes |

### 4.11 VOZ (`handlers/voice.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| Mensaje de voz (F.voice) | Procesa voz | audio .ogg | Descarga→Whisper transcribe→Parser NL→muestra resumen |
| `voice_confirm:si` | Confirma y guarda | parsed_data | Si 1 finca→guarda directo. Varias→pregunta finca |
| `voice_confirm:no` | Cancela | — | Mensaje cancelación |
| `voice_confirm:corregir` | Corregir | — | Pide escribir manualmente |
| `voice_finca:X` | Selecciona finca voz | finca_id | `guardar_transaccion_voz()` |

### 4.12 PRESUPUESTO (`handlers/presupuesto.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/presupuesto`, `menu_presupuesto` | Menú presupuesto | user_id | 4 opciones: Crear, Consultar, Ejecución, Exportar |
| `presup_crear` | Crear presupuesto | finca_id | Pide año→área→muestra sugeridos→edita→confirma |
| FSM: esperando_anio | Selecciona año | año (N-1, N, N+1) | Guarda año |
| FSM: esperando_area | Área | float o desde lotes | Calcula montos sugeridos por ha |
| Edición de categorías | Editar montos | cat_id, monto | Usuario modifica montos individualmente |
| `presup_confirmar` | Guarda presupuesto | categorías | `guardar_presupuesto()`, muestra distribución |
| `presup_consultar` | Consultar | finca_id, año | Muestra planificado por categoría |
| `presup_ejecutar` | Ejecución | finca_id, año | `get_ejecucion_presupuesto()` → plan vs real |
| `presup_exportar` | Exportar a Excel | finca_id, año | Genera Excel con hoja presupuesto |

### 4.13 INDICADORES (`handlers/indicadores.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/indicadores`, `menu_indicadores` | Menú indicadores | user_id | Si 1 finca→menú. Varias→selector |
| `indic_finca:X` | Selecciona finca | finca_id | Menú de vistas |
| `indicador:general:X` | Indicadores generales | finca_id | Área, MO, insumos, financiero, productividad, comparación FNC |
| `indicador:mo:X` | Solo MO | finca_id | Jornales, costo MO/ha, eficiencia |
| `indicador:insumos:X` | Solo insumos | finca_id | Costo insumos/ha, kg/ha, eficiencia |
| `indicador:financiero:X` | Solo financiero | finca_id | Ingresos, costos, margen, precio prom. |
| `indicador_excel:X` | Exportar indicadores | finca_id | Redirige a generar Excel |
| `indicador_pdf:X` | Exportar PDF indicadores | finca_id | Genera PDF con KPIs |
| `indicador_periodo:X` | Indicadores por período | finca_id | Menú período: mes, año, personalizado |
| `indic_filtro:mes/anio:X` | Filtro período | — | Resumen del período |
| — | Alertas automáticas | — | Productividad baja, margen negativo, costo>precio |

### 4.14 ASESORÍA (`handlers/asesoria.py`)

| Comando/Callback | Funcionalidad | Datos | Respuesta |
|-----------------|---------------|-------|-----------|
| `/asesoria` | Menú asesoría | — | 4 opciones: Interpretar, Sugerencias, Plan, Personalizada |
| `as_interpretar` | Interpreta datos | finca_id | Compara con FNC, genera análisis por productividad, costo, margen, eficiencia |
| `as_sugerencias` | Sugerencias mejora | — | 5 sugerencias genéricas |
| `as_plan` | Plan de acción | — | Corto/Medio/Largo plazo |
| `as_personalizada` | Contacto asesoría | — | Muestra email de contacto |

---

## 5. EXCEL MANAGER (excel_manager.py)

### HOJA_CONFIG — Mapeo categorías DB → hojas Excel

| Hoja Excel | Categorías MO | Categorías Insumos |
|-----------|--------------|-------------------|
| Instalacion de Cafe | instalacion_mo | instalacion_insumos |
| Control de arvenses | arvens_mo | arvens_insumos |
| Fertilizacion | fertilizacion_mo | fertilizacion_insumos |
| Control Fitosanitario | fitosanitario_mo | fitosanitario_insumos |
| Regulacion de sombrio | sombrio_mo | sombrio_insumos |
| Otras Labores | otras_labores_mo | otras_labores_insumos |
| Recoleccion | recoleccion (especial) | — |
| Beneficio | beneficio (especial) | — |
| Gastos Administrativos | administrativo (especial) | — |

### Métodos Principales

| Método | Descripción |
|--------|------------|
| `generar_excel(finca_id, db, output_path)` | Genera Excel completo con datos reales |
| `generar_plantilla_vacia(output_path)` | Genera plantilla limpia para importación |
| `_llenar_hoja_lotes(wb, lotes)` | Llena hoja ID lotes |
| `_llenar_hoja_ingresos(wb, data)` | Llena hoja Ingresos |
| `_llenar_hojas_costos(wb, data)` | Llena todas las hojas de costos |
| `_llenar_hoja_presupuesto(wb, db, finca_id)` | Llena hoja Presupuesto |
| `_llenar_hoja_indicadores(wb, db, finca_id)` | Llena hoja Indicadores |
| `_llenar_hoja_periodo(wb, db, finca_id, inicio, fin)` | Llena hoja adicional de período |
| `_generar_hoja_graficos(db, finca_id, ws)` | Crea hoja Gráficos con charts |
| `_crear_hoja_resumen_ejecutivo(wb, db, finca_id)` | Crea hoja Resumen Ejecutivo |
| `_crear_hoja_dashboard(wb, db, finca_id)` | Crea hoja Dashboard |
| `_crear_hoja_configuracion(wb, db, finca_id)` | Crea hoja Configuración |
| `_asegurar_filas_suficientes(...)` | Expande filas dinámicamente |
| `_actualizar_sum_subtotal(...)` | Actualiza fórmulas SUM |
| `_copiar_formula_fila(...)` | Copia fórmulas con ajuste de referencias |

### Hojas generadas en el Excel final:
1. NOTAS (instrucciones)
2. ID lotes
3. Ingresos
4. Instalacion de Cafe
5. Control de arvenses
6. Fertilizacion
7. Control Fitosanitario
8. Regulacion de sombrio
9. Otras Labores
10. Recoleccion
11. Beneficio
12. Gastos Administrativos
13. Presupuesto
14. Indicadores
15. Gráficos
16. Resumen Ejecutivo
17. Dashboard
18. Configuración

---

## 6. VOICE HANDLER (voice_handler.py)

### CONSTANTES
- `WHISPER_MODEL`: 'base' por defecto
- `COSTO_KEYWORDS`: 70+ palabras clave → categorías de costo
- `INGRESO_KEYWORDS`: palabras → ingreso_cps/ingreso_pasilla
- `UNIDAD_KEYWORDS`: palabras → jornal, kilo, litro, etc.
- `NUMEROS`: español → números

### FUNCIONES

| Función | Descripción |
|---------|-------------|
| `transcribe_audio(audio_path)` | Transcribe audio con Whisper local |
| `parse_number(text)` | Extrae número (soporta "40 mil", "1.500.000", "cinco") |
| `extract_fecha(text)` | Extrae fecha ("ayer", "15 de junio", DD/MM/AAAA) |
| `extract_categoria(text)` | Determina categoría por keywords |
| `extract_unidad(text)` | Extrae unidad de medida |
| `extract_lote(text)` | Extrae nombre de lote |
| `parse_voice_text(text)` | Parsea completo: fecha, categoría, labor, cantidad, VU, VT |
| `format_parsed_data(data)` | Formatea para mostrar al usuario |

---

## 7. UTILS (utils.py)

| Función | Descripción |
|---------|-------------|
| `fecha_hoy()` | Fecha actual DD/MM/AAAA |
| `fecha_ayer()` | Fecha de ayer DD/MM/AAAA |
| `botones_fecha()` | Teclado con Hoy, Ayer, Otra fecha |
| `boton_menu()` | Teclado solo "Menú Principal" |
| `boton_cancelar()` | Teclado solo "Cancelar" |
| `botones_menu_cancelar()` | Cancelar + Menú Principal |
| `agregar_boton_menu(keyboard)` | Agrega "Menú Principal" a teclado existente |
| `agregar_boton_cancelar(keyboard)` | Agrega "Cancelar" a teclado existente |
| `agregar_menu_cancelar(keyboard)` | Agrega ambos botones |
| `construir_menu_principal(db, user_id, is_admin)` | Menú principal completo con 14 botones |

### Botones del Menú Principal:
1. 🗺️ Fincas → `menu_fincas`
2. 🌱 Lotes → `menu_lotes`
3. 💰 Ingresos → `menu_ingresos`
4. 📉 Costos → `menu_costos`
5. 📊 Resumen → `menu_resumen`
6. 📈 Indicadores → `menu_indicadores`
7. 📋 Presupuesto → `menu_presupuesto`
8. 📋 Exportar Excel → `menu_excel`
9. 📄 Exportar PDF → `menu_pdf`
10. 📊 Dashboard → `menu_dashboard`
11. 👨‍🏫 Asesoría → `menu_asesoria`
12. 📥 Importar Excel → `menu_importar`
13. 🗑️ Borrar datos → `ir_borrar`
14. ❓ Ayuda → `menu_ayuda`
15. 🔧 Admin (solo admins) → `ir_admin`

---

## 8. MIDDLEWARE (middleware.py)

**CancelMiddleware**: Se ejecuta en cada mensaje y callback_query.

- Intercepta comandos: `/menu`, `/cancelar`, `/start`, `/ayuda`, `/`, `/excel`, `/fincas`, `/lotes`, `/ingreso`, `/costo`, `/resumen`, `/usuarios`, `/presupuesto`, `/indicadores`, `/importar`
- Intercepta callbacks: `menu_*`, `ir_*`
- Si hay un estado FSM activo, lo limpia automáticamente
- Garantiza que los comandos de navegación tengan prioridad absoluta sobre cualquier FSM

---

## 9. MAIN (main.py)

**Framework: aiogram 3.x** (Dispatcher, Router, FSM, MemoryStorage)

### Inicialización
1. Crea instancia de `Database()`
2. Llama a `db.init_db()`
3. Crea `Bot` con token y `DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)`
4. Crea `Dispatcher(storage=MemoryStorage())`

### Middleware registrado
- `CancelMiddleware` en `dp.message` y `dp.callback_query`

### Routers registrados (14 en total, en orden de prioridad)
1. `get_menu_router(db)` ← Prioridad máxima
2. `get_start_router(db)`
3. `get_admin_router(db)`
4. `get_fincas_router(db)`
5. `get_lotes_router(db)`
6. `get_ingresos_router(db)`
7. `get_costos_router(db)`
8. `get_reportes_router(db)`
9. `get_importar_router(db)`
10. `get_ayuda_router(db)`
11. `get_voice_router(db)`
12. `get_presupuesto_router(db)`
13. `get_indicadores_router(db)`
14. `get_asesoria_router(db)`

### Polling
- `dp.start_polling(bot, allowed_updates=["message", "callback_query"])`

---

## 10. MINI APP EXISTENTE

### API Endpoints (mini-app/api/app.py)

| Endpoint | Método | Parámetros | Descripción |
|---------|--------|------------|-------------|
| `/api/health` | GET | — | Health check |
| `/api/fincas/{user_id}` | GET | user_id | Obtener fincas del usuario |
| `/api/indicadores/{finca_id}` | GET | finca_id | Indicadores técnicos |
| `/api/transacciones/{finca_id}` | GET | finca_id, ?fecha_inicio, ?fecha_fin | Transacciones |
| `/api/transacciones` | POST | TransaccionCreate | Crear transacción |
| `/api/resumen/{finca_id}` | GET | finca_id | Resumen financiero |
| `/api/gastos-por-rubro/{finca_id}` | GET | finca_id, ?fecha_inicio, ?fecha_fin | Gastos agrupados |
| `/api/presupuesto/{finca_id}` | GET | finca_id | Años con datos |
| `/api/planes` | GET | — | Planes de suscripción |
| `/api/config` | GET | — | Configuración pública |

### Endpoints FALTANTES vs Bot:
- ❌ No hay CRUD de lotes
- ❌ No hay CRUD de fincas
- ❌ No hay gestión de usuarios (registro, aprobación)
- ❌ No hay presupuesto (crear, consultar, ejecución)
- ❌ No hay exportación Excel
- ❌ No hay importación Excel
- ❌ No hay filtrado por período
- ❌ No hay asesoría
- ❌ No hay planes/precios reales (solo mock)
- ❌ No hay autenticación (Telegram ID)
- ❌ No hay WebApp data verification
- ❌ No hay gestión de lotes por finca
- ❌ No hay sync queue processing

---

## 11. SHARED DATABASE

`shared/database.py` es una versión thread-safe de `database.py` que usa:
- `check_same_thread=False`
- Context manager `get_conn()` en lugar de open/close manual
- Mismos métodos que `database.py` pero con `with self.get_conn()`
- Incluye métodos nuevos para la Mini App:
  - `get_transacciones_por_periodo()`
  - `get_gastos_por_rubro()`
  - `get_ingresos_por_tipo()`
  - `get_resumen_periodo()`
  - `get_transacciones_finca()` (con filtro opcional)

---

## 12. REQUERIMIENTOS API MINI APP

### ENDPOINTS NECESARIOS (completos)

#### Usuarios
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/auth/verify` | POST | Verificar datos Telegram WebApp |
| `/api/auth/login` | POST | Login con initData de Telegram |
| `/api/usuarios/{user_id}` | GET | Perfil del usuario |
| `/api/usuarios/{user_id}/aceptar-terminos` | POST | Aceptar términos |
| `/api/admin/usuarios` | GET | Lista usuarios (admin) |
| `/api/admin/usuarios/aprobar/{user_id}` | POST | Aprobar usuario |
| `/api/admin/usuarios/rechazar/{user_id}` | POST | Rechazar usuario |
| `/api/admin/usuarios/revocar/{user_id}` | POST | Revocar acceso |

#### Fincas
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/fincas` | POST | Crear finca |
| `/api/fincas/{user_id}` | GET | Listar fincas del usuario |
| `/api/fincas/{finca_id}` | GET | Detalle finca |
| `/api/fincas/{finca_id}` | PUT | Editar finca |
| `/api/fincas/{finca_id}` | DELETE | Eliminar finca |

#### Lotes
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/lotes` | POST | Crear lote |
| `/api/lotes/{finca_id}` | GET | Listar lotes de finca |
| `/api/lotes/detalle/{lote_id}` | GET | Detalle lote |
| `/api/lotes/{lote_id}` | PUT | Editar lote |
| `/api/lotes/{lote_id}` | DELETE | Eliminar lote |

#### Transacciones / Ingresos
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/transacciones` | POST | Crear transacción |
| `/api/transacciones/{finca_id}` | GET | Listar (con filtros) |
| `/api/transacciones/detalle/{tx_id}` | GET | Detalle transacción |
| `/api/transacciones/{tx_id}` | PUT | Editar transacción |
| `/api/transacciones/{tx_id}` | DELETE | Eliminar transacción |
| `/api/ingresos/tipos` | GET | Tipos de café disponibles |

#### Costos
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/costos/categorias` | GET | Categorías de costos |
| `/api/costos/unidades` | GET | Unidades de insumo |
| `/api/costos/mo` | POST | Registrar MO |
| `/api/costos/insumos` | POST | Registrar insumos |

#### Reportes / Resumen
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/resumen/{finca_id}` | GET | Resumen financiero |
| `/api/resumen/{finca_id}/periodo` | GET | Resumen con filtro fechas |
| `/api/excel/{finca_id}` | GET | Generar y descargar Excel |
| `/api/excel/plantilla` | GET | Descargar plantilla vacía |
| `/api/excel/importar` | POST | Importar Excel |
| `/api/pdf/{finca_id}` | GET | Generar PDF |

#### Presupuesto
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/presupuesto/{finca_id}` | GET | Obtener presupuesto |
| `/api/presupuesto/{finca_id}` | POST | Crear/guardar presupuesto |
| `/api/presupuesto/{finca_id}/anios` | GET | Años con presupuesto |
| `/api/presupuesto/{finca_id}/ejecucion/{anio}` | GET | Ejecución vs plan |
| `/api/presupuesto/{finca_id}/sugerido` | GET | Montos sugeridos |

#### Indicadores
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/indicadores/{finca_id}` | GET | Todos los indicadores |
| `/api/indicadores/{finca_id}/mo` | GET | Solo MO |
| `/api/indicadores/{finca_id}/insumos` | GET | Solo insumos |
| `/api/indicadores/{finca_id}/financiero` | GET | Solo financiero |
| `/api/indicadores/referencia-fnc` | GET | Datos FNC de referencia |

#### Asesoría
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/asesoria/interpretar/{finca_id}` | GET | Interpretación datos |
| `/api/asesoria/sugerencias` | GET | Sugerencias de mejora |
| `/api/asesoria/plan` | GET | Plan de acción |
| `/api/asesoria/contacto` | GET | Info contacto asesoría |

#### Admin
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/admin/stats` | GET | Estadísticas del sistema |
| `/api/admin/usuarios/{user_id}/reactivar` | POST | Reactivar usuario |
| `/api/admin/borrar-datos/{user_id}` | DELETE | Borrar datos de usuario |

#### Voz
| Endpoint | Método | Descripción |
|---------|--------|-------------|
| `/api/voz/transcribir` | POST | Subir audio, transcribir con Whisper |
| `/api/voz/parsear` | POST | Enviar texto, parsear datos |

---

## 13. PANTALLAS NECESARIAS EN LA MINI APP

### Pantallas Principales

1. **Login / Verificación** — Pantalla de carga con verificación de Telegram WebApp data
2. **Aviso Legal** — Términos de uso con botón Aceptar/Rechazar
3. **Menú Principal** — Grid de acceso rápido a todas las funcionalidades (14 botones)
4. **Perfil** — Datos del usuario, estado de aprobación

### Gestión de Fincas
5. **Lista de Fincas** — Lista con nombre, región, departamento
6. **Crear Finca** — Formulario multi-paso (nombre, región, departamento)
7. **Editar Finca** — Editar datos de finca

### Gestión de Lotes
8. **Lista de Lotes** — Lista con área, árboles, variedad
9. **Crear Lote** — Formulario multi-paso (nombre, área, árboles, variedad, fecha)
10. **Editar Lote** — Editar datos de lote

### Ingresos
11. **Registrar Ingreso** — Formulario: fecha, tipo café, kg, valor total
12. **Editar Ingreso** — Editar campos del ingreso
13. **Historial Ingresos** — Lista de ingresos registrados

### Costos
14. **Seleccionar Finca** (para operaciones)
15. **Seleccionar Lote(s)** — Toda la finca, lote específico, múltiples lotes
16. **Seleccionar Categoría** — Grid de 9 categorías de costos
17. **Tipo de Costo** — MO / Insumos / Ambos
18. **Registrar MO** — Formulario: fecha, labor, jornales, VU, VT
19. **Registrar Insumo** — Formulario: producto, unidad, cantidad, VU, VT
20. **Resumen/Confirmación** — Resumen con Confirmar/Editar/Cancelar
21. **Editar Costo** — Editar campos
22. **Agregar Otro Insumo** — Continuar agregando insumos

### Reportes
23. **Resumen Financiero** — Dashboard con ingresos, egresos, margen, categorías
24. **Filtrar por Período** — Selector: semana, mes, año, personalizado
25. **Resultados Filtro** — Resumen del período seleccionado
26. **Exportar Excel** — Botón para generar y descargar
27. **Exportar PDF** — Botón para generar y descargar

### Indicadores
28. **Menú Indicadores** — Navegación: General, MO, Insumos, Financiero
29. **Indicadores Generales** — Todos los KPIs con comparación FNC
30. **Indicadores MO** — Jornales, costo MO/ha, eficiencia
31. **Indicadores Insumos** — Costo insumos, eficiencia
32. **Indicadores Financieros** — Ingresos, costos, margen, precio
33. **Alertas** — Alertas automáticas (rojas/amarillas)

### Presupuesto
34. **Menú Presupuesto** — Crear, Consultar, Ejecución, Exportar
35. **Crear Presupuesto** — Año, área, montos sugeridos editables
36. **Editar Categoría** — Modificar monto por categoría
37. **Consultar Presupuesto** — Planificado por categoría
38. **Ejecución Presupuestal** — Plan vs Real con alertas
39. **Resumen Presupuesto** — Barras de distribución

### Importación/Exportación
40. **Importar Excel** — Subir archivo, preview, confirmar
41. **Descargar Plantilla** — Descargar plantilla vacía

### Asesoría
42. **Menú Asesoría** — Interpretar, Sugerencias, Plan, Contacto
43. **Interpretación** — Análisis vs FNC
44. **Sugerencias** — Lista de recomendaciones
45. **Plan de Acción** — Corto/Medio/Largo plazo
46. **Contacto Asesoría** — Datos de contacto

### Voz
47. **Grabar/Subir Audio** (futuro) — Botón para grabar/subir audio

### Admin
48. **Panel Admin** — Lista de usuarios con acciones
49. **Gestionar Usuario** — Aprobar, Rechazar, Revocar, Reactivar
50. **Estadísticas Admin** — N° usuarios, fincas, transacciones

### Sistema
51. **Ayuda/FAQ** — Guía de uso completa
52. **Cargando/Procesando** — Pantallas de carga
53. **Error** — Pantalla de error genérico
54. **Confirmación de Borrado** — Doble confirmación
55. **Sync Offline** — Indicador de sincronización

---

## RESUMEN EJECUTIVO

### TOTAL: ~55 pantallas / ~40 endpoints API

### Prioridades de implementación:

**FASE 1 — Core (esencial):**
1. Autenticación Telegram WebApp
2. CRUD Fincas
3. CRUD Lotes
4. Registrar Ingresos
5. Registrar Costos (MO + Insumos)
6. Resumen Financiero
7. Exportar Excel
8. Menú Principal

**FASE 2 — Análisis:**
9. Indicadores Técnicos
10. Presupuesto
11. Filtrar por Período
12. Exportar PDF

**FASE 3 — Avanzado:**
13. Importar Excel
14. Asesoría
15. Voz (Whisper)
16. Admin Panel
17. Planes/Pagos
18. Borrar Datos
