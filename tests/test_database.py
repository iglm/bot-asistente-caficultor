"""
Tests unitarios para database.py — get_resumen_finca() y helpers.
Usa SQLite en memoria mediante monkeypatch de DB_PATH.
"""

import os
import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from database import Database


# ─── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    """
    Crea una instancia de Database apuntando a un archivo temporal
    (evita el problema de que SQLite :memory: crea una BD distinta
    por cada conexión). tmp_path se limpia automáticamente.
    """
    db_path = str(tmp_path / "test.db")
    d = Database(db_path=db_path)
    d.init_db()
    yield d
    # tmp_path se limpia automáticamente al finalizar el fixture


@pytest.fixture
def finca_id(db: Database) -> int:
    """Crea un usuario y una finca de prueba, retorna el ID de la finca."""
    db.upsert_user(user_id=999, username="test_user")
    return db.create_finca(user_id=999, nombre="Finca Test", region="Test", departamento="Test")


# ─── Tests: helpers _es_categoria_compuesta / _es_categoria_simple ──


class TestHelpers:
    """Prueba los métodos estáticos que clasifican categorías."""

    def test_es_categoria_compuesta_returns_true(self):
        """_es_categoria_compuesta debe retornar True para categorías con MO e Insumos."""
        for cat in Database.CATEGORIAS_CON_MO_Y_INSUMOS:
            assert Database._es_categoria_compuesta(cat), (
                f"Se esperaba True para '{cat}'"
            )

    def test_es_categoria_compuesta_returns_false_for_simple(self):
        """_es_categoria_compuesta debe retornar False para categorías simples."""
        for cat in Database.CATEGORIAS_SIMPLE:
            assert not Database._es_categoria_compuesta(cat), (
                f"Se esperaba False para '{cat}'"
            )

    def test_es_categoria_simple_returns_true(self):
        """_es_categoria_simple debe retornar True para categorías simples."""
        for cat in Database.CATEGORIAS_SIMPLE:
            assert Database._es_categoria_simple(cat), (
                f"Se esperaba True para '{cat}'"
            )

    def test_es_categoria_simple_returns_false_for_compuesta(self):
        """_es_categoria_simple debe retornar False para categorías compuestas."""
        for cat in Database.CATEGORIAS_CON_MO_Y_INSUMOS:
            assert not Database._es_categoria_simple(cat), (
                f"Se esperaba False para '{cat}'"
            )


# ─── Tests: get_resumen_finca ──────────────────────────────────────


class TestGetResumenFinca:
    """Prueba el método get_resumen_finca() en distintos escenarios."""

    def test_resumen_vacio(self, db: Database, finca_id: int):
        """
        Sin transacciones ni lotes, el resumen debe retornar
        todos los valores en cero.
        """
        resumen = db.get_resumen_finca(finca_id)

        assert resumen["ingresos"] == 0
        assert resumen["egresos"] == 0
        assert resumen["margen"] == 0
        assert resumen["area_total"] == 0
        assert resumen["costo_por_hectarea"] == 0
        # Todos los egresos_por_categoria deben ser 0
        for cat in Database.CATEGORIAS_CON_MO_Y_INSUMOS + Database.CATEGORIAS_SIMPLE:
            assert resumen["egresos_por_categoria"][cat] == 0, (
                f"Se esperaba 0 para '{cat}'"
            )
        # Todos los ingresos_por_tipo deben ser 0
        for tipo in ("ingreso_cps", "ingreso_pasilla"):
            assert resumen["ingresos_por_tipo"][tipo] == 0, (
                f"Se esperaba 0 para '{tipo}'"
            )

    def test_resumen_categorias_compuestas(self, db: Database, finca_id: int):
        """
        Inserta transacciones MO e Insumos en una categoría compuesta
        (instalacion). Verifica que egresos_por_categoria las sume
        correctamente y que el total de egresos refleje la suma.
        """
        db.insert_transaccion(finca_id, "instalacion_mo", "2024-01-15",
                              labor="Mano de obra", valor_total=100_000)
        db.insert_transaccion(finca_id, "instalacion_mo", "2024-02-10",
                              labor="Jornal", valor_total=50_000)
        db.insert_transaccion(finca_id, "instalacion_insumos", "2024-01-20",
                              producto="Bandejas", cantidad=200, valor_unitario=500,
                              valor_total=100_000)

        resumen = db.get_resumen_finca(finca_id)

        # instalacion debe sumar MO (150k) + Insumos (100k) = 250k
        assert resumen["egresos_por_categoria"]["instalacion"] == 250_000, (
            "La categoría compuesta 'instalacion' debe sumar MO e Insumos"
        )
        # Total egresos debe coincidir
        assert resumen["egresos"] == 250_000
        # Las demás categorías deben estar en cero
        for cat in Database.CATEGORIAS_CON_MO_Y_INSUMOS:
            if cat != "instalacion":
                assert resumen["egresos_por_categoria"][cat] == 0

    def test_resumen_categorias_simples(self, db: Database, finca_id: int):
        """
        Inserta transacciones en categorías simples (recoleccion, beneficio).
        Verifica que egresos_por_categoria las refleje individualmente.
        """
        db.insert_transaccion(finca_id, "recoleccion", "2024-03-01",
                              labor="Recolectores", valor_total=300_000)
        db.insert_transaccion(finca_id, "beneficio", "2024-03-05",
                              labor="Beneficiado", valor_total=120_000)
        db.insert_transaccion(finca_id, "administrativo", "2024-03-10",
                              labor="Contador", valor_total=80_000)

        resumen = db.get_resumen_finca(finca_id)

        assert resumen["egresos_por_categoria"]["recoleccion"] == 300_000
        assert resumen["egresos_por_categoria"]["beneficio"] == 120_000
        assert resumen["egresos_por_categoria"]["administrativo"] == 80_000
        assert resumen["egresos"] == 500_000

    def test_resumen_ingresos(self, db: Database, finca_id: int):
        """
        Inserta transacciones de ingreso de los tres tipos.
        Verifica ingresos totales, ingresos_por_tipo y margen.
        """
        db.insert_transaccion(finca_id, "ingreso_cps", "2024-04-01",
                              producto="CPS", cantidad=500, valor_unitario=8_000,
                              valor_total=4_000_000)
        db.insert_transaccion(finca_id, "ingreso_pasilla", "2024-04-10",
                              producto="Pasilla", cantidad=100, valor_unitario=3_000,
                              valor_total=300_000)

        # Agregar un egreso para verificar margen
        db.insert_transaccion(finca_id, "recoleccion", "2024-04-20",
                              labor="Corte", valor_total=1_000_000)

        resumen = db.get_resumen_finca(finca_id)

        assert resumen["ingresos_por_tipo"]["ingreso_cps"] == 4_000_000
        assert resumen["ingresos_por_tipo"]["ingreso_pasilla"] == 300_000
        assert resumen["ingresos"] == 4_300_000
        assert resumen["egresos"] == 1_000_000
        assert resumen["margen"] == 3_300_000

    def test_resumen_con_lotes_y_costo_hectarea(self, db: Database, finca_id: int):
        """
        Crea lotes y transacciones para verificar area_total y costo_por_hectarea.
        """
        db.create_lote(finca_id, "Lote A", area=5.0, num_arboles=5000)
        db.create_lote(finca_id, "Lote B", area=3.0, num_arboles=3000)

        db.insert_transaccion(finca_id, "fertilizacion_mo", "2024-05-01",
                              labor="Aplicación", valor_total=400_000)
        db.insert_transaccion(finca_id, "fertilizacion_insumos", "2024-05-01",
                              producto="Fertilizante", cantidad=10, valor_unitario=120_000,
                              valor_total=1_200_000)

        resumen = db.get_resumen_finca(finca_id)

        assert resumen["area_total"] == 8.0
        assert resumen["egresos"] == 1_600_000
        assert resumen["costo_por_hectarea"] == 200_000  # 1_600_000 / 8
        assert resumen["egresos_por_categoria"]["fertilizacion"] == 1_600_000


# ─── Tests: Presupuestos ──────────────────────────────────────


class TestPresupuestos:
    """Prueba los métodos de presupuesto."""

    def test_guardar_y_obtener_presupuesto(self, db: Database, finca_id: int):
        """Guarda un presupuesto y lo recupera."""
        datos = {
            "recoleccion": 5_000_000,
            "fertilizacion": 2_000_000,
            "administrativo": 700_000,
            "arvenses": 600_000,
            "beneficio": 500_000,
            "instalacion": 400_000,
            "fitosanitario": 200_000,
            "otras_labores": 100_000,
        }
        db.guardar_presupuesto(finca_id, 2025, datos)

        rows = db.get_presupuesto(finca_id, 2025)
        assert len(rows) == 8

        categorias = {r["categoria"]: r["monto_planificado"] for r in rows}
        assert categorias["recoleccion"] == 5_000_000
        assert categorias["fertilizacion"] == 2_000_000
        assert categorias["administrativo"] == 700_000

        total = sum(categorias.values())
        assert total == 9_500_000

    def test_actualizar_presupuesto(self, db: Database, finca_id: int):
        """Actualiza un presupuesto existente."""
        datos = {"recoleccion": 5_000_000, "fertilizacion": 2_000_000}
        db.guardar_presupuesto(finca_id, 2025, datos)

        # Actualizar
        datos_actualizados = {"recoleccion": 6_000_000, "fertilizacion": 2_500_000}
        db.guardar_presupuesto(finca_id, 2025, datos_actualizados)

        rows = db.get_presupuesto(finca_id, 2025)
        categorias = {r["categoria"]: r["monto_planificado"] for r in rows}
        assert categorias["recoleccion"] == 6_000_000
        assert categorias["fertilizacion"] == 2_500_000

    def test_get_presupuesto_anios(self, db: Database, finca_id: int):
        """Obtiene años disponibles."""
        db.guardar_presupuesto(finca_id, 2024, {"recoleccion": 4_000_000})
        db.guardar_presupuesto(finca_id, 2025, {"recoleccion": 5_000_000})

        anios = db.get_presupuesto_anios(finca_id)
        assert anios == [2025, 2024]  # Orden descendente

    def test_get_presupuesto_anios_vacio(self, db: Database, finca_id: int):
        """Años disponibles cuando no hay presupuesto."""
        anios = db.get_presupuesto_anios(finca_id)
        assert anios == []

    def test_delete_presupuesto(self, db: Database, finca_id: int):
        """Elimina un presupuesto."""
        db.guardar_presupuesto(finca_id, 2025, {"recoleccion": 5_000_000})
        assert len(db.get_presupuesto(finca_id, 2025)) == 1

        db.delete_presupuesto(finca_id, 2025)
        assert len(db.get_presupuesto(finca_id, 2025)) == 0

    def test_get_ejecucion_sin_presupuesto(self, db: Database, finca_id: int):
        """Ejecución sin presupuesto: todos los montos en 0."""
        ej = db.get_ejecucion_presupuesto(finca_id, 2025)
        assert len(ej["categorias"]) == 8
        assert ej["total_planificado"] == 0
        assert ej["total_ejecutado"] == 0
        assert ej["total_diferencia"] == 0
        for cat in ej["categorias"]:
            assert cat["monto_planificado"] == 0
            assert cat["monto_ejecutado"] == 0
            assert cat["pct_ejecucion"] == 0

    def test_get_ejecucion_con_presupuesto_y_transacciones(self, db: Database, finca_id: int):
        """Ejecución con presupuesto y transacciones reales."""
        # Guardar presupuesto para 2025
        datos = {
            "recoleccion": 5_000_000,
            "fertilizacion": 2_000_000,
            "administrativo": 700_000,
            "arvenses": 600_000,
            "beneficio": 500_000,
            "instalacion": 400_000,
            "fitosanitario": 200_000,
            "otras_labores": 100_000,
        }
        db.guardar_presupuesto(finca_id, 2025, datos)

        # Insertar transacciones reales (menores al presupuesto)
        db.insert_transaccion(finca_id, "recoleccion", "2025-03-01", labor="Corte", valor_total=4_000_000)
        db.insert_transaccion(finca_id, "fertilizacion_mo", "2025-04-01", labor="Aplicación", valor_total=500_000)
        db.insert_transaccion(finca_id, "fertilizacion_insumos", "2025-04-01", producto="Urea", cantidad=10, valor_unitario=100_000, valor_total=1_000_000)
        db.insert_transaccion(finca_id, "administrativo", "2025-05-01", labor="Contador", valor_total=600_000)

        # También una transacción de 2024 que NO debe contar
        db.insert_transaccion(finca_id, "recoleccion", "2024-03-01", labor="Corte", valor_total=3_000_000)

        ej = db.get_ejecucion_presupuesto(finca_id, 2025)

        # Verificar recolección
        rec = [c for c in ej["categorias"] if c["categoria"] == "recoleccion"][0]
        assert rec["monto_planificado"] == 5_000_000
        assert rec["monto_ejecutado"] == 4_000_000
        assert rec["diferencia"] == -1_000_000  # Por debajo del presupuesto
        assert rec["pct_ejecucion"] == 80.0  # 4M / 5M

        # Verificar fertilización (MO + Insumos)
        fert = [c for c in ej["categorias"] if c["categoria"] == "fertilizacion"][0]
        assert fert["monto_planificado"] == 2_000_000
        assert fert["monto_ejecutado"] == 1_500_000
        assert fert["diferencia"] == -500_000
        assert fert["pct_ejecucion"] == 75.0  # 1.5M / 2M

        # Verificar administrativo
        admin = [c for c in ej["categorias"] if c["categoria"] == "administrativo"][0]
        assert admin["monto_planificado"] == 700_000
        assert admin["monto_ejecutado"] == 600_000
        assert admin["diferencia"] == -100_000

        # Verificar totales
        assert ej["total_planificado"] == 9_500_000
        assert ej["total_ejecutado"] == 6_100_000  # 4M + 1.5M + 0.6M
        assert ej["total_diferencia"] == -3_400_000

    def test_get_ejecucion_sobregiro(self, db: Database, finca_id: int):
        """Ejecución con sobregiro (ejecutado > planificado)."""
        db.guardar_presupuesto(finca_id, 2025, {"recoleccion": 5_000_000})
        db.insert_transaccion(finca_id, "recoleccion", "2025-03-01", labor="Corte", valor_total=6_000_000)

        ej = db.get_ejecucion_presupuesto(finca_id, 2025)
        rec = [c for c in ej["categorias"] if c["categoria"] == "recoleccion"][0]
        assert rec["diferencia"] == 1_000_000  # Sobregiro
        assert rec["pct_ejecucion"] == 120.0  # 6M / 5M
