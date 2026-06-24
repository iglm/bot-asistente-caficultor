# 📊 Informe de Prueba E2E — Bot Asistente Caficultor ☕

**Fecha:** 2026-06-24 12:38:27
**Duración:** 12.5 segundos
**Bot Token:** 86607604...rGmE
**Admin ID:** 810796748
**DB:** `/home/lucas-mateo/bot-asistente-caficultor/data/finca.db`
**Template Excel:** `/home/lucas-mateo/bot-asistente-caficultor/data/plantilla/Costos de produccion - 2026.xlsx`

---

## 📋 Resumen de Resultados

| Métrica | Valor |
|---------|-------|
| Total pasos probados | 21 |
| ✅ Exitosos | 21 |
| ❌ Fallidos | 0 |
| 📊 Tasa de éxito | 100.0% |
| ⚠️ Errores | 0 |

## ✅/❌ Pasos Detallados

| ✅ | Limpiar DB | DB limpia, admin reconectado |
| ✅ | Bot conectado | @asistente_de_costos_bot (ID: 8660760448) |
| ✅ | /start | Mensaje enviado correctamente |
| ✅ | /menu | Menú principal mostrado |
| ✅ | Crear finca en DB | ID=1, 'Finca El Paraíso' — Manizales, Caldas |
| ✅ | Crear 3 lotes | 3/3 lotes creados en DB |
| ✅ | /fincas | Lista de fincas mostrada |
| ✅ | /lotes | Lista de lotes mostrada |
| ✅ | Crear 2 ingresos | 2/2 ingresos, total $23,250,000 |
| ✅ | Crear 5 costos | 5/5 costos, total $6,830,000 |
| ✅ | /resumen | Resumen financiero solicitado |
| ✅ | Exportar Excel | Archivo: /home/lucas-mateo/bot-asistente-caficultor/exports/test_e2e_20260624_123824.xlsx (42,451 bytes) |
| ✅ | Plantilla existe | Template: /home/lucas-mateo/bot-asistente-caficultor/data/plantilla/Costos de produccion - 2026.xlsx (37,932 bytes) |
| ✅ | Generar plantilla vacía | Plantilla generada (37,374 bytes) |
| ✅ | Borrar datos | Eliminados: 1 fincas, 3 lotes, 7 transacciones |
| ✅ | /menu después de operaciones | Menú principal funciona |
| ✅ | Re-crear finca | ID=2 |
| ✅ | Re-crear lote |  |
| ✅ | Re-crear transacción |  |
| ✅ | Consultar transacciones | 1 transacciones encontradas |
| ✅ | Suma de ingresos | Total ingresos: $9,000,000 |

## 💾 Estado Final de la Base de Datos

| Tabla | Registros |
|-------|-----------|
| usuarios | 1 |
| fincas | 1 |
| lotes | 1 |
| transacciones | 1 |

## 🔍 Detalle de Transacciones

| Categoría | Cantidad | Total |
|-----------|----------|-------|
| ingreso_cps | 1 | $9,000,000 |

## 📐 Problemas Encontrados

✅ **No se encontraron problemas.**

## 💡 Sugerencias de Mejora

1. **Simulación de callbacks inline**: Los flujos FSM que requieren `callback_query` (crear finca, lotes, ingresos, costos) no se pueden probar completamente via `sendMessage`. Considerar:
   - Usar `aiogram` testing utilities para simular callbacks
   - Crear un bot de prueba con webhook para pruebas E2E completas
   - Implementar un modo "text fallback" donde los callback_data también se acepten como mensajes de texto

2. **Pruebas de carga**: El bot usa MemoryStorage para FSM — verificar comportamiento con múltiples usuarios concurrentes.

3. **Verificación de Excel generado**: Abrir manualmente el Excel exportado para verificar fórmulas y formato.

4. **Monitoreo**: El bot consume ~135 MB según `ps aux` — monitorear uso de memoria con datos grandes.

5. **Logging de errores**: Considerar agregar más logging en handlers críticos para facilitar debugging.

## 📝 Log de Ejecución

```
[12:38:14] 
============================================================
[12:38:14] 📌 FASE 0: Limpiar base de datos
[12:38:14] ============================================================
[12:38:14]   ✅ Limpiar DB: DB limpia, admin reconectado
[12:38:14] 
============================================================
[12:38:14] 📌 FASE 1: Verificar conectividad del bot
[12:38:14] ============================================================
[12:38:14]   ✅ Bot conectado: @asistente_de_costos_bot (ID: 8660760448)
[12:38:14] 
============================================================
[12:38:14] 📌 FASE 2: Probar /start
[12:38:14] ============================================================
[12:38:16]   ✅ /start: Mensaje enviado correctamente
[12:38:16] 
============================================================
[12:38:16] 📌 FASE 3: Probar /menu
[12:38:16] ============================================================
[12:38:18]   ✅ /menu: Menú principal mostrado
[12:38:18] 
============================================================
[12:38:18] 📌 FASE 4: Crear finca
[12:38:18] ============================================================
[12:38:18]   ✅ Crear finca en DB: ID=1, 'Finca El Paraíso' — Manizales, Caldas
[12:38:18] 
============================================================
[12:38:18] 📌 FASE 5: Crear lotes
[12:38:18] ============================================================
[12:38:18]   ✅ Crear 3 lotes: 3/3 lotes creados en DB
[12:38:18] 
============================================================
[12:38:18] 📌 FASE 6: Probar /fincas
[12:38:18] ============================================================
[12:38:20]   ✅ /fincas: Lista de fincas mostrada
[12:38:20] 
============================================================
[12:38:20] 📌 FASE 7: Probar /lotes
[12:38:20] ============================================================
[12:38:22]   ✅ /lotes: Lista de lotes mostrada
[12:38:22] 
============================================================
[12:38:22] 📌 FASE 8: Registrar ingresos
[12:38:22] ============================================================
[12:38:22]   ✅ Crear 2 ingresos: 2/2 ingresos, total $23,250,000
[12:38:22] 
============================================================
[12:38:22] 📌 FASE 9: Registrar costos
[12:38:22] ============================================================
[12:38:22]   ✅ Crear 5 costos: 5/5 costos, total $6,830,000
[12:38:22] 
============================================================
[12:38:22] 📌 FASE 10: Probar /resumen
[12:38:22] ============================================================
[12:38:24]   ✅ /resumen: Resumen financiero solicitado
[12:38:24] 
============================================================
[12:38:24] 📌 FASE 11: Exportar Excel
[12:38:24] ============================================================
[12:38:25]   ✅ Exportar Excel: Archivo: /home/lucas-mateo/bot-asistente-caficultor/exports/test_e2e_20260624_123824.xlsx (42,451 bytes)
[12:38:25] 
============================================================
[12:38:25] 📌 FASE 12: Importar plantilla Excel
[12:38:25] ============================================================
[12:38:25]   ✅ Plantilla existe: Template: /home/lucas-mateo/bot-asistente-caficultor/data/plantilla/Costos de produccion - 2026.xlsx (37,932 bytes)
[12:38:25]   ✅ Generar plantilla vacía: Plantilla generada (37,374 bytes)
[12:38:25] 
============================================================
[12:38:25] 📌 FASE 13: Probar borrar datos
[12:38:25] ============================================================
[12:38:25]   Datos antes de borrar: fincas=1, lotes=3, transacciones=7
[12:38:25]   Datos después de borrar: fincas=0, lotes=0, transacciones=0
[12:38:25]   ✅ Borrar datos: Eliminados: 1 fincas, 3 lotes, 7 transacciones
[12:38:25] 
============================================================
[12:38:25] 📌 FASE 14: Volver al menú principal
[12:38:25] ============================================================
[12:38:27]   ✅ /menu después de operaciones: Menú principal funciona
[12:38:27] 
============================================================
[12:38:27] 📌 FASE 15: Verificar persistencia en DB
[12:38:27] ============================================================
[12:38:27]   ✅ Re-crear finca: ID=2
[12:38:27]   ✅ Re-crear lote: 
[12:38:27]   ✅ Re-crear transacción: 
[12:38:27]   ✅ Consultar transacciones: 1 transacciones encontradas
[12:38:27]   ✅ Suma de ingresos: Total ingresos: $9,000,000
[12:38:27] 
============================================================
[12:38:27] 📌 FASE 16: Generar informe
[12:38:27] ============================================================
```
