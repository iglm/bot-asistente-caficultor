"""API Backend para Mini App - Telegram Mini App."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from shared.database import Database

app = FastAPI(title="Asistente de Costos API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()

class TransaccionCreate(BaseModel):
    finca_id: int
    lote_id: int = 0
    categoria: str
    fecha: str
    labor: str = ""
    producto: str = ""
    cantidad: float = 0
    unidad: str = ""
    valor_unitario: float = 0
    valor_total: float = 0


@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/fincas/{user_id}")
def get_fincas(user_id: int):
    """Obtiene todas las fincas de un usuario."""
    fincas = db.get_fincas(user_id)
    if not fincas:
        raise HTTPException(status_code=404, detail="Usuario sin fincas")
    return {"fincas": [dict(f) for f in fincas]}


@app.get("/api/indicadores/{finca_id}")
def get_indicadores(finca_id: int):
    """Calcula indicadores de la finca."""
    indicadores = db.get_indicadores_tecnicos(finca_id)
    if not indicadores:
        raise HTTPException(status_code=404, detail="Sin datos")
    return dict(indicadores)


@app.get("/api/transacciones/{finca_id}")
def get_transacciones(
    finca_id: int,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
):
    """Obtiene transacciones, opcionalmente filtradas por período."""
    if fecha_inicio and fecha_fin:
        tx = db.get_transacciones_por_periodo(finca_id, fecha_inicio, fecha_fin)
    else:
        tx = db.get_all_transacciones(finca_id)
    return {"transacciones": [dict(t) for t in tx], "total": len(tx)}


@app.post("/api/transacciones")
def create_transaccion(t: TransaccionCreate):
    """Crea una nueva transacción."""
    db.insert_transaccion(
        finca_id=t.finca_id,
        categoria=t.categoria,
        fecha=t.fecha,
        labor=t.labor,
        producto=t.producto,
        cantidad=t.cantidad,
        unidad=t.unidad,
        valor_unitario=t.valor_unitario,
        valor_total=t.valor_total,
        lote_id=t.lote_id,
    )
    return {"status": "created"}


@app.get("/api/resumen/{finca_id}")
def get_resumen(finca_id: int):
    """Resumen financiero."""
    resumen = db.get_resumen_finca(finca_id)
    return resumen


@app.get("/api/gastos-por-rubro/{finca_id}")
def get_gastos_rubro(
    finca_id: int,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
):
    """Gastos agrupados por rubro."""
    gastos = db.get_gastos_por_rubro(
        finca_id,
        fecha_inicio or "2000-01-01",
        fecha_fin or "2099-12-31",
    )
    return {"gastos": [dict(g) for g in gastos]}


@app.get("/api/presupuesto/{finca_id}")
def get_presupuesto(finca_id: int):
    """Obtiene años con presupuesto."""
    anios = db.get_anios_con_datos(finca_id)
    return {"anios": anios}


# ═══════════════════════════════════════════
# PAGOS
# ═══════════════════════════════════════════

class PlanResponse(BaseModel):
    id: str
    nombre: str
    precio: float
    moneda: str
    caracteristicas: list[str]

PLANES = [
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

@app.get("/api/planes")
def get_planes():
    """Retorna planes disponibles."""
    return {"planes": PLANES}

@app.get("/api/config")
def get_config():
    """Configuración pública de la app."""
    return {
        "app_name": "Asistente de Costos",
        "version": "1.0.0",
        "developer": "Lucas Mateo Tabares Franco",
        "advisor": "Ing. Jhoan Sebastian Bustamante Montes",
        "contact": "mateotabares7@gmail.com",
        "telegram_bot": "@asistente_de_costos_bot",
        "planes": PLANES
    }

# Montar frontend en producción
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="mini-app")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
