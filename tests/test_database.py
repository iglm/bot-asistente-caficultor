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
        for tipo in ("ingreso_cps", "ingreso_pasilla", "ingreso_rere"):
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
        db.insert_transaccion(finca_id, "ingreso_rere", "2024-04-15",
                              producto="Re-re", cantidad=50, valor_unitario=1_000,
                              valor_total=50_000)

        # Agregar un egreso para verificar margen
        db.insert_transaccion(finca_id, "recoleccion", "2024-04-20",
                              labor="Corte", valor_total=1_000_000)

        resumen = db.get_resumen_finca(finca_id)

        assert resumen["ingresos_por_tipo"]["ingreso_cps"] == 4_000_000
        assert resumen["ingresos_por_tipo"]["ingreso_pasilla"] == 300_000
        assert resumen["ingresos_por_tipo"]["ingreso_rere"] == 50_000
        assert resumen["ingresos"] == 4_350_000
        assert resumen["egresos"] == 1_000_000
        assert resumen["margen"] == 3_350_000

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
