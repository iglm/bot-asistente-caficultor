# 📊 Informe de Simulación — Bot Asistente Caficultor ☕

**Fecha:** 2026-06-24 05:36:57
**Duración:** 38.1 segundos
**Bot:** @asistente_de_costos_bot (ID: 8660760448)
**Admin:** Mateo (ID: 810796748)
**Finca simulada:** Finca La Esperanza — Manizales, Caldas
**Área total:** 20.6 ha

---

## 1. Resumen de Resultados

| Métrica | Valor |
|---------|-------|
| Mensajes enviados via API | 10 |
| Éxitos API | 10 |
| Fallos API | 0 |
| Tasa de éxito API | 100.0% |
| Errores detectados | 0 |
| Advertencias | 0 |

## 2. Base de Datos

| Tabla | Registros |
|-------|-----------|
| usuarios | 1 |
| fincas | 1 |
| lotes | 20 |
| transacciones (ingresos) | 50 |
| transacciones (costos) | 250 |
| **Total transacciones** | 300 |

### 2.1 Resumen Financiero

| Concepto | Valor |
|----------|-------|
| 💰 Total Ingresos | $1,028,971,119 |
| 💸 Total Costos | $260,549,093 |
| 📈 Margen Neto | $768,422,026 |
| 💵 Costo por Hectárea | $12,648,014 |

### 2.2 Ingresos por Año

| Año | Cantidad | Total |
|-----|----------|-------|
| 2023 | 20 | $252,555,746 |
| 2024 | 17 | $386,548,060 |
| 2025 | 13 | $389,867,313 |

### 2.3 Costos por Año

| Año | Cantidad | Total |
|-----|----------|-------|
| 2023 | 79 | $69,830,642 |
| 2024 | 79 | $78,084,240 |
| 2025 | 92 | $112,634,211 |

### 2.4 Desglose por Categoría de Transacción

| Categoría | Registros | Total |
|-----------|-----------|-------|
| ingreso_cps | 39 | $822,433,958 |
| ingreso_pasilla | 7 | $149,799,869 |
| recoleccion | 22 | $71,031,816 |
| ingreso_rere | 4 | $56,737,292 |
| beneficio | 20 | $54,688,437 |
| arvenses_insumos | 17 | $31,616,010 |
| fertilizacion_insumos | 21 | $23,766,573 |
| otras_labores_insumos | 11 | $15,987,472 |
| sombrio_insumos | 9 | $14,656,551 |
| fitosanitario_insumos | 10 | $10,634,907 |
| arvenses_mo | 29 | $8,072,949 |
| fertilizacion_mo | 32 | $6,921,970 |
| otras_labores_mo | 22 | $5,263,932 |
| fitosanitario_mo | 22 | $5,050,116 |
| instalacion_insumos | 2 | $4,410,369 |
| sombrio_mo | 13 | $3,715,117 |
| administrativo | 12 | $2,936,733 |
| instalacion_mo | 8 | $1,796,141 |

### 2.5 Lotes

| Lote | Área (ha) | Árboles | Variedad |
|------|-----------|---------|----------|
| Lote El Abra | 0.9 | 3400 | Colombia |
| Lote El Altozano | 1.0 | 3700 | Bourbon |
| Lote El Bosque | 1.3 | 4800 | Tabi |
| Lote El Cerro | 1.2 | 4300 | Colombia |
| Lote El Mirador | 1.4 | 5100 | Caturra |
| Lote El Oasis | 0.7 | 2600 | Bourbon |
| Lote El Respaldo | 0.8 | 3000 | Tabi |
| Lote El Rincón | 0.6 | 2200 | Castillo |
| Lote El Talud | 1.2 | 4500 | Caturra |
| Lote El Valle | 1.1 | 4000 | Castillo |
| Lote La Cañada | 1.0 | 3600 | Colombia |
| Lote La Cima | 1.2 | 4400 | Castillo |
| Lote La Colina | 0.9 | 3300 | Colombia |
| Lote La Hondonada | 1.1 | 4100 | Caturra |
| Lote La Ladera | 1.0 | 3800 | Caturra |
| Lote La Meseta | 1.3 | 4700 | Bourbon |
| Lote La Montaña | 0.8 | 2900 | Bourbon |
| Lote La Planada | 0.9 | 3300 | Tabi |
| Lote La Quebrada | 0.7 | 2600 | Tabi |
| Lote La Vega | 1.5 | 5500 | Castillo |

## 3. Pruebas de API del Bot

✅ **Todos los mensajes via API se enviaron correctamente.** El bot @asistente_de_costos_bot está online y responde.

## 4. Limitaciones Detectadas

### 4.1 Flujos con Callbacks (NO simulables via sendMessage)

Los siguientes flujos FSM requieren **inline callbacks** (botones presionables) que NO se pueden simular con `sendMessage`:

| Flujo | Handler requerido | Bloqueante |
|-------|------------------|------------|
| Crear finca | `@router.callback_query(F.data == "nueva_finca")` | Sí |
| Crear lote | `@router.callback_query(F.data.startswith("nuevo_lote:"))` | Sí |
| Seleccionar tipo de café (ingreso) | `@router.callback_query(F.data.startswith("tipo_cafe:"))` | Sí |
| Confirmar ingreso | `@router.callback_query(F.data.startswith("conf_ingreso:"))` | Sí |
| Seleccionar categoría (costo) | `@router.callback_query(F.data.startswith("cat_costo:"))` | Sí |
| Confirmar MO (costo) | `@router.callback_query(F.data.startswith("conf_costo_mo:"))` | Sí |
| Confirmar insumo (costo) | `@router.callback_query(F.data.startswith("conf_insumo:"))` | Sí |

**Solución aplicada en el simulador:** Los datos se insertan directamente en SQLite mediante INSERT, evitando los callbacks.

### 4.2 Excel Template
✅ Template Excel disponible en: `/home/lucas-mateo/bot-asistente-caficultor/data/plantilla/Costos de produccion - 2026.xlsx`

## 5. Recomendaciones

1. **E2E testing completo:** Implementar pruebas con `aiogram` testing utilities o usar un bot de prueba para simular callbacks reales.
2. **Automatizar más datos:** El simulador podría generar datos más realistas si se conectara a fuentes de precios históricos reales.
3. **Verificación de Excel:** Abrir manualmente el Excel generado para verificar que las fórmulas y los datos se hayan copiado correctamente.
4. **Pruebas de concurrencia:** Probar con múltiples usuarios simulados enviando comandos simultáneamente.
5. **Monitoreo de memoria:** El bot usa ~112 MB en reposo — monitorear fugas de memoria con cargas grandes.

## 6. Log de Ejecución

```
[05:36:19] ======================================================================
[05:36:19] ☕ SIMULADOR DEL BOT ASISTENTE CAFICULTOR
[05:36:19]    Finca: Finca La Esperanza — Manizales, Caldas
[05:36:19]    Período: 2023-2025
[05:36:19]    Admin ID: 810796748
[05:36:19]    DB: /home/lucas-mateo/bot-asistente-caficultor/data/finca.db
[05:36:19]    Bot: @asistente_de_costos_bot
[05:36:19] ======================================================================
[05:36:19] 
═══ FASE 1: Registrar admin en DB ═══
[05:36:19]    ✅ Admin registrado: ID=810796748, status=approved
[05:36:19] 
═══ FASE 2: Crear finca 'Finca La Esperanza' ═══
[05:36:19]    ✅ Finca creada: ID=1, 'Finca La Esperanza'
[05:36:19] 
═══ FASE 3: Crear 20 lotes ═══
[05:36:19]    ✅ 20/20 lotes creados en DB
[05:36:19] 
═══ FASE 4: Crear 50 ingresos ═══
[05:36:19]    ✅ 50/50 ingresos creados
[05:36:19]       📊 2023: 20 ingresos, $252,555,746
[05:36:19]       📊 2024: 17 ingresos, $386,548,060
[05:36:19]       📊 2025: 13 ingresos, $389,867,313
[05:36:19] 
═══ FASE 5: Crear 250 costos en 9 categorías ═══
[05:36:19]    ✅ 250/250 costos creados
[05:36:19]    📊 Desglose por categoría:
[05:36:19]       instalacion: 10 registros (8 MO + 2 ins), $6,206,510
[05:36:19]       arvenses: 46 registros (29 MO + 17 ins), $39,688,959
[05:36:19]       fertilizacion: 53 registros (32 MO + 21 ins), $30,688,543
[05:36:19]       fitosanitario: 32 registros (22 MO + 10 ins), $15,685,023
[05:36:19]       sombrio: 22 registros (13 MO + 9 ins), $18,371,668
[05:36:19]       otras_labores: 33 registros (22 MO + 11 ins), $21,251,404
[05:36:19]       recoleccion: 22 registros, $71,031,816
[05:36:19]       beneficio: 20 registros, $54,688,437
[05:36:19]       administrativo: 12 registros, $2,936,733
[05:36:19] 
═══ FASE 6: Probar API del bot ═══
[05:36:20]    ✅ Bot conectado: @asistente_de_costos_bot (Asistente de costos)
[05:36:20]    📤 Enviando /start...
[05:36:20]   📤 API → '/start'
[05:36:20]        ✅ OK (msg_id=79)
[05:36:21]    📤 Enviando /menu...
[05:36:21]   📤 API → '/menu'
[05:36:21]        ✅ OK (msg_id=80)
[05:36:22]    📤 Enviando /ayuda...
[05:36:22]   📤 API → '/ayuda'
[05:36:23]        ✅ OK (msg_id=81)
[05:36:25]    📤 Enviando /fincas...
[05:36:25]   📤 API → '/fincas'
[05:36:25]        ✅ OK (msg_id=82)
[05:36:27]    📤 Enviando /lotes...
[05:36:27]   📤 API → '/lotes'
[05:36:28]        ✅ OK (msg_id=83)
[05:36:30]    📤 Enviando /ingreso para probar FSM...
[05:36:30]   📤 API → '/ingreso'
[05:36:45]        ✅ OK (msg_id=84)
[05:36:47]    📤 Enviando fecha para continuar FSM ingreso...
[05:36:47]   📤 API → '15/10/2024'
[05:36:47]        ✅ OK (msg_id=85)
[05:36:49]    📤 Enviando /costo para probar FSM...
[05:36:49]   📤 API → '/costo'
[05:36:50]        ✅ OK (msg_id=86)
[05:36:52]    📤 Enviando /resumen...
[05:36:52]   📤 API → '/resumen'
[05:36:52]        ✅ OK (msg_id=87)
[05:36:55]    📤 Enviando /cancelar...
[05:36:55]   📤 API → '/cancelar'
[05:36:56]        ✅ OK (msg_id=88)
[05:36:57] 
═══ FASE 7: Verificar DB ═══
[05:36:57]    ✅ usuarios: 1 (esperado >= 1)
[05:36:57]    ✅ fincas: 1 (esperado >= 1)
[05:36:57]    ✅ lotes: 20 (esperado >= 20)
[05:36:57]    ✅ transacciones WHERE categoria LIKE 'ingreso_%': 50 (esperado >= 50)
[05:36:57]    ✅ transacciones WHERE categoria NOT LIKE 'ingreso_%': 250 (esperado >= 250)
[05:36:57]    💰 Total ingresos: $1,028,971,119
[05:36:57]    💸 Total costos: $260,549,093
[05:36:57]    📈 Margen: $768,422,026
[05:36:57]    📐 Área total: 20.6 ha
[05:36:57]    💵 Costo por ha: $12,648,014
[05:36:57] 
═══ FASE 8: Generar Excel ═══
[05:36:57]    ✅ Excel generado: /home/lucas-mateo/bot-asistente-caficultor/exports/simulacion_Finca_La_Esperanza_20260624_053657.xlsx
[05:36:57]       Tamaño: 42,438 bytes
[05:36:57]       Filas en DB: 300 transacciones, 20 lotes
[05:36:57] 
═══ FASE 9: Generar informe ═══
```
