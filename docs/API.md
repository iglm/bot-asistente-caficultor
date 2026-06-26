# API Documentation

## Base URL
- Desarrollo: `http://localhost:8080/api`
- Producción: `https://iglm.github.io/asistente-caficultor/api`

## Endpoints

### Health
- `GET /api/health` — Estado del servidor

### Fincas
- `GET /api/fincas/{user_id}` — Obtener fincas de un usuario

### Indicadores
- `GET /api/indicadores/{finca_id}` — Indicadores técnicos de la finca

### Transacciones
- `GET /api/transacciones/{finca_id}` — Listar transacciones
- `GET /api/transacciones/{finca_id}?fecha_inicio=2024-01-01&fecha_fin=2024-12-31` — Filtrar por período
- `POST /api/transacciones` — Crear transacción

### Resumen
- `GET /api/resumen/{finca_id}` — Resumen financiero (ingresos, egresos, margen, costo/ha)

### Gastos
- `GET /api/gastos-por-rubro/{finca_id}` — Gastos agrupados por rubro
- `GET /api/gastos-por-rubro/{finca_id}?fecha_inicio=2024-01-01&fecha_fin=2024-12-31` — Filtrar por período

### Presupuesto
- `GET /api/presupuesto/{finca_id}` — Años con datos disponibles

### Pagos
- `GET /api/planes` — Planes disponibles (Gratis, Premium, Enterprise)
- `GET /api/config` — Configuración pública de la app

## Ejemplos

```bash
# Health check
curl https://iglm.github.io/asistente-caficultor/api/health

# Obtener fincas de un usuario
curl https://iglm.github.io/asistente-caficultor/api/fincas/123456789

# Obtener indicadores
curl https://iglm.github.io/asistente-caficultor/api/indicadores/1

# Obtener transacciones
curl https://iglm.github.io/asistente-caficultor/api/transacciones/1

# Transacciones filtradas por período
curl "https://iglm.github.io/asistente-caficultor/api/transacciones/1?fecha_inicio=2024-01-01&fecha_fin=2024-12-31"

# Crear transacción
curl -X POST https://iglm.github.io/asistente-caficultor/api/transacciones \
  -H "Content-Type: application/json" \
  -d '{
    "finca_id": 1,
    "categoria": "ingreso_cps",
    "fecha": "2024-01-15",
    "cantidad": 500,
    "valor_unitario": 24000,
    "valor_total": 12000000
  }'

# Resumen financiero
curl https://iglm.github.io/asistente-caficultor/api/resumen/1

# Gastos por rubro
curl https://iglm.github.io/asistente-caficultor/api/gastos-por-rubro/1

# Años con presupuesto
curl https://iglm.github.io/asistente-caficultor/api/presupuesto/1

# Planes disponibles
curl https://iglm.github.io/asistente-caficultor/api/planes

# Configuración de la app
curl https://iglm.github.io/asistente-caficultor/api/config
```

## Modelos

### TransaccionCreate (POST /api/transacciones)

```json
{
  "finca_id": 1,
  "lote_id": 0,
  "categoria": "ingreso_cps",
  "fecha": "2024-01-15",
  "labor": "",
  "producto": "",
  "cantidad": 500,
  "unidad": "",
  "valor_unitario": 24000,
  "valor_total": 12000000
}
```

### Config (GET /api/config)

```json
{
  "app_name": "Asistente de Costos",
  "version": "1.0.0",
  "developer": "Lucas Mateo Tabares Franco",
  "advisor": "Ing. Jhoan Sebastian Bustamante Montes",
  "contact": "mateotabares7@gmail.com",
  "telegram_bot": "@asistente_de_costos_bot",
  "planes": [
    {
      "id": "gratis",
      "nombre": "Gratis",
      "precio": 0,
      "moneda": "COP",
      "caracteristicas": ["Registro básico", "Exportar Excel", "5 fincas"]
    },
    {
      "id": "premium",
      "nombre": "Premium",
      "precio": 29000,
      "moneda": "COP",
      "caracteristicas": ["Fincas ilimitadas", "Gráficos avanzados", "Asesoría prioritaria", "Soporte 24/7"]
    },
    {
      "id": "enterprise",
      "nombre": "Enterprise",
      "precio": 99000,
      "moneda": "COP",
      "caracteristicas": ["Todo Premium", "API access", "Multi-usuario", "White-label"]
    }
  ]
}
```
