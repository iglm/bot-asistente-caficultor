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
        # Como no hay transacciones, GROUP BY no devuelve filas,
        # así que el dict puede estar vacío. Cualquier categoría
        # consultada debe retornar 0 via .get().
        for cat in Database.CATEGORIAS_CON_MO_Y_INSUMOS + Database.CATEGORIAS_SIMPLE:
            assert resumen["egresos_por_categoria"].get(cat, 0) == 0, (
                f"Se esperaba 0 para '{cat}'"
            )
        # Todos los ingresos_por_tipo deben ser 0
        for tipo in ("ingreso_cps", "ingreso_pasilla"):
            assert resumen["ingresos_por_tipo"].get(tipo, 0) == 0, (
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
        # Las demás categorías deben estar en cero (o no existir en el dict)
        for cat in Database.CATEGORIAS_CON_MO_Y_INSUMOS:
            if cat != "instalacion":
                assert resumen["egresos_por_categoria"].get(cat, 0) == 0

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


# ─── Tests: CRUD básico ─────────────────────────────────────────────


class TestCRUDFincas:
    """Prueba operaciones CRUD sobre fincas."""

    def test_create_finca(self, db: Database):
        """Crear una finca y verificar que se guarda con sus datos."""
        db.upsert_user(user_id=100, username="user_finca")
        fid = db.create_finca(user_id=100, nombre="Mi Finca", region="Caldas", departamento="Manizales")
        assert isinstance(fid, int)
        assert fid > 0

        finca = db.get_finca(fid)
        assert finca is not None
        assert finca["nombre"] == "Mi Finca"
        assert finca["region"] == "Caldas"
        assert finca["departamento"] == "Manizales"
        assert finca["user_id"] == 100

    def test_get_fincas_de_usuario(self, db: Database):
        """Obtener fincas de un usuario específico."""
        db.upsert_user(user_id=101, username="multi_finca")
        fid1 = db.create_finca(101, "Finca A", region="Quindío")
        fid2 = db.create_finca(101, "Finca B", region="Risaralda")
        fid3 = db.create_finca(101, "Finca C", region="Caldas")

        fincas = db.get_fincas(101)
        assert len(fincas) == 3
        ids = [f["id"] for f in fincas]
        assert fid1 in ids
        assert fid2 in ids
        assert fid3 in ids

    def test_get_finca_by_id_returns_none(self, db: Database):
        """get_finca con ID inexistente retorna None."""
        assert db.get_finca(99999) is None

    def test_get_finca_by_id_alias(self, db: Database, finca_id: int):
        """El alias get_finca_by_id funciona igual que get_finca."""
        f1 = db.get_finca(finca_id)
        f2 = db.get_finca_by_id(finca_id)
        assert f1 == f2


class TestCRUDLotes:
    """Prueba operaciones CRUD sobre lotes."""

    def test_create_lote(self, db: Database, finca_id: int):
        """Crear un lote y verificar datos guardados."""
        lid = db.create_lote(
            finca_id=finca_id,
            nombre="Lote La Esperanza",
            area=3.5,
            num_arboles=4200,
            variedad="Castillo",
            fecha_siembra="2022-06-01",
        )
        assert isinstance(lid, int)
        assert lid > 0

        lote = db.get_lote_by_id(lid)
        assert lote is not None
        assert lote["nombre"] == "Lote La Esperanza"
        assert lote["area_hectareas"] == 3.5
        assert lote["num_arboles"] == 4200
        assert lote["variedad"] == "Castillo"
        assert lote["fecha_siembra"] == "2022-06-01"

    def test_get_lotes_de_finca(self, db: Database, finca_id: int):
        """Obtener lista de lotes de una finca."""
        db.create_lote(finca_id, "Lote 1", area=2.0)
        db.create_lote(finca_id, "Lote 2", area=3.0)
        db.create_lote(finca_id, "Lote 3", area=4.0)

        lotes = db.get_lotes(finca_id)
        assert len(lotes) == 3
        # Ordenados por nombre
        assert [l["nombre"] for l in lotes] == ["Lote 1", "Lote 2", "Lote 3"]

    def test_create_lote_con_valores_minimos(self, db: Database, finca_id: int):
        """Crear lote solo con campos obligatorios."""
        lid = db.create_lote(finca_id, "Lote Mínimo")
        assert lid > 0
        lote = db.get_lote_by_id(lid)
        assert lote["nombre"] == "Lote Mínimo"
        assert lote["area_hectareas"] == 0
        assert lote["num_arboles"] == 0

    def test_get_lote_by_id_returns_none(self, db: Database):
        """get_lote_by_id con ID inexistente retorna None."""
        assert db.get_lote_by_id(99999) is None


class TestCRUDTransacciones:
    """Prueba operaciones CRUD sobre transacciones."""

    def test_insert_transaccion(self, db: Database, finca_id: int):
        """Insertar una transacción y verificar datos guardados."""
        tid = db.insert_transaccion(
            finca_id=finca_id,
            categoria="recoleccion",
            fecha="2024-10-15",
            labor="Recolección cereza",
            cantidad=500,
            unidad="kg",
            valor_unitario=55000,
            valor_total=500 * 55000,
        )
        assert isinstance(tid, int)
        assert tid > 0

        trans = db.get_all_transacciones(finca_id)
        assert len(trans) == 1
        assert trans[0]["categoria"] == "recoleccion"
        assert trans[0]["valor_total"] == 27_500_000

    def test_insert_transaccion_con_lote(self, db: Database, finca_id: int, lote_id: int):
        """Insertar una transacción asociada a un lote específico."""
        tid = db.insert_transaccion(
            finca_id=finca_id,
            lote_id=lote_id,
            categoria="fertilizacion_mo",
            fecha="2024-03-10",
            labor="Aplicación fertilizante",
            cantidad=5,
            unidad="jornal",
            valor_unitario=55000,
            valor_total=275000,
        )
        assert tid > 0
        trans = db.get_transacciones(finca_id, "fertilizacion_mo")
        assert len(trans) == 1
        assert trans[0]["lote_id"] == lote_id

    def test_get_transacciones_vacio(self, db: Database, finca_id: int):
        """Obtener transacciones de una finca sin datos retorna lista vacía."""
        assert db.get_all_transacciones(finca_id) == []
        assert db.get_transacciones(finca_id, "recoleccion") == []

    def test_get_transacciones_por_periodo(self, db: Database, finca_id: int):
        """Filtrar transacciones por rango de fechas."""
        db.insert_transaccion(finca_id, "recoleccion", "2024-01-15", valor_total=100_000)
        db.insert_transaccion(finca_id, "recoleccion", "2024-06-15", valor_total=200_000)
        db.insert_transaccion(finca_id, "recoleccion", "2024-12-15", valor_total=300_000)

        # Solo las de la primera mitad del año
        rango = db.get_transacciones_por_periodo(finca_id, "2024-01-01", "2024-06-30")
        assert len(rango) == 2

        # Solo las de diciembre
        rango2 = db.get_transacciones_por_periodo(finca_id, "2024-12-01", "2024-12-31")
        assert len(rango2) == 1
        assert rango2[0]["valor_total"] == 300_000


class TestIndicadoresTecnicos:
    """Prueba el cálculo de indicadores técnicos (get_indicadores_tecnicos)."""

    def test_indicadores_vacio(self, db: Database, finca_id: int):
        """Sin lotes ni transacciones, los indicadores deben estar en cero."""
        ind = db.get_indicadores_tecnicos(finca_id)
        assert ind["area_total"] == 0
        assert ind["area_productiva"] == 0
        assert ind["ingresos_totales"] == 0
        assert ind["costos_total"] == 0
        assert ind["kg_producidos"] == 0
        assert ind["productividad"] == 0
        assert ind["costo_por_kilo"] == 0
        assert ind["precio_venta_promedio"] == 0

    def test_indicadores_con_lotes_y_transacciones(self, db: Database, finca_id: int):
        """Calcular indicadores con datos completos."""
        # Crear lotes productivos (con árboles y fecha de siembra)
        db.create_lote(finca_id, "Lote 1", area=5.0, num_arboles=5000, variedad="Castillo", fecha_siembra="2022-01-01")
        db.create_lote(finca_id, "Lote 2", area=3.0, num_arboles=3000, variedad="Caturra", fecha_siembra="2021-06-01")

        # Lote no productivo (sin árboles)
        db.create_lote(finca_id, "Lote Vivero", area=1.0)

        # Ingresos
        db.insert_transaccion(finca_id, "ingreso_cps", "2024-10-15", producto="CPS", cantidad=2000, valor_unitario=18000, valor_total=36_000_000)
        db.insert_transaccion(finca_id, "ingreso_pasilla", "2024-10-15", producto="Pasilla", cantidad=200, valor_unitario=3000, valor_total=600_000)

        # Costos MO
        db.insert_transaccion(finca_id, "recoleccion", "2024-10-01", labor="Corte", cantidad=50, unidad="jornal", valor_unitario=55000, valor_total=2_750_000)
        db.insert_transaccion(finca_id, "fertilizacion_mo", "2024-03-10", labor="Aplicación", cantidad=10, unidad="jornal", valor_unitario=55000, valor_total=550_000)
        db.insert_transaccion(finca_id, "administrativo", "2024-12-01", labor="Contador", valor_total=500_000)

        # Costos Insumos
        db.insert_transaccion(finca_id, "fertilizacion_insumos", "2024-03-10", producto="Urea", cantidad=200, unidad="kg", valor_unitario=3200, valor_total=640_000)

        ind = db.get_indicadores_tecnicos(finca_id)

        # Área
        assert ind["area_total"] == 9.0
        assert ind["area_productiva"] == 8.0  # solo Lote 1 + Lote 2

        # Ingresos
        assert ind["ingresos_totales"] == 36_600_000

        # Costos
        assert ind["costos_mo"] == 3_800_000  # 2.75M + 0.55M + 0.5M
        assert ind["costos_insumos"] == 640_000
        assert ind["costos_total"] == 4_440_000

        # Producción
        assert ind["kg_producidos"] == 2200  # 2000 CPS + 200 pasilla

        # Indicadores derivados (división segura)
        assert ind["productividad"] == pytest.approx(2200 / 9.0)  # kg/ha total
        assert ind["rendimiento"] == pytest.approx(2200 / 8.0)  # kg/ha productiva
        assert ind["costo_por_kilo"] == pytest.approx(4_440_000 / 2200)  # COP/kg
        assert ind["precio_venta_promedio"] == pytest.approx(36_600_000 / 2200)
        assert ind["costo_total_por_ha"] == pytest.approx(4_440_000 / 9.0)
        assert ind["margen_por_ha"] == pytest.approx((36_600_000 - 4_440_000) / 9.0)

        # Comparación con FNC (valores de referencia)
        assert "fnc_productividad_ha" in ind
        assert "fnc_costo_ha" in ind
        assert "fnc_precio_venta_promedio" in ind

    def test_lote_es_productivo(self, db: Database):
        """_lote_es_productivo identifica correctamente lotes productivos."""
        # Productivo: tiene num_arboles y fecha_siembra
        assert db._lote_es_productivo({"num_arboles": 5000, "fecha_siembra": "2022-01-01"})
        # No productivo: sin árboles
        assert not db._lote_es_productivo({"num_arboles": 0, "fecha_siembra": "2022-01-01"})
        # No productivo: sin fecha de siembra
        assert not db._lote_es_productivo({"num_arboles": 5000, "fecha_siembra": ""})
        # No productivo: ambos vacíos
        assert not db._lote_es_productivo({"num_arboles": 0, "fecha_siembra": ""})

    def test_indicadores_solo_lotes_sin_transacciones(self, db: Database, finca_id: int):
        """Con lotes pero sin transacciones, indicadores deben ser cero o valores seguros."""
        db.create_lote(finca_id, "Lote 1", area=5.0, num_arboles=5000, variedad="Castillo", fecha_siembra="2022-01-01")

        ind = db.get_indicadores_tecnicos(finca_id)
        assert ind["area_total"] == 5.0
        assert ind["area_productiva"] == 5.0
        assert ind["ingresos_totales"] == 0
        assert ind["costos_total"] == 0
        assert ind["productividad"] == 0  # kg_producidos / area_total = 0 / 5
        assert ind["costo_por_kilo"] == 0  # costos_total / kg_producidos = 0 / 0
        assert ind["precio_venta_promedio"] == 0
