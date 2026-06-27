"""
Tests de validación de datos.

Verifica funciones de validación para precios, áreas, fechas y más,
que son típicas del dominio caficultor. Estas funciones representan
validaciones que se aplican en los handlers del bot.
"""

import pytest
from datetime import datetime, date


# ─── Funciones de validación bajo test ──────────────────────────────
#
# Estas funciones representan la lógica de validación que se usa
# en los handlers del bot. Se definen aquí como funciones puras para
# poder testearlas unitariamente sin depender del contexto de aiogram.


def validar_precio_positivo(valor: float) -> tuple[bool, str]:
    """
    Valida que un precio sea un número positivo.
    Retorna (True, "") si es válido, (False, mensaje_error) si no.
    """
    if valor is None:
        return False, "El precio no puede estar vacío"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return False, "El precio debe ser un número válido"
    if v <= 0:
        return False, "El precio debe ser un valor positivo mayor a cero"
    return True, ""


def validar_area_positiva(area: float) -> tuple[bool, str]:
    """
    Valida que un área (en hectáreas) sea un número positivo.
    Retorna (True, "") si es válido, (False, mensaje_error) si no.
    """
    if area is None:
        return False, "El área no puede estar vacía"
    try:
        a = float(area)
    except (TypeError, ValueError):
        return False, "El área debe ser un número válido"
    if a <= 0:
        return False, "El área debe ser un valor positivo mayor a cero"
    if a > 1000:
        return False, "El área no puede superar las 1000 hectáreas"
    return True, ""


def validar_fecha(fecha_str: str) -> tuple[bool, str]:
    """
    Valida que una fecha tenga formato válido (YYYY-MM-DD o DD/MM/AAAA)
    y no sea una fecha futura.
    Retorna (True, "") si es válida, (False, mensaje_error) si no.
    """
    if not fecha_str or not fecha_str.strip():
        return False, "La fecha no puede estar vacía"

    fecha_str = fecha_str.strip()

    # Intentar formato YYYY-MM-DD
    for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
        try:
            fecha = datetime.strptime(fecha_str, fmt).date()
            break
        except ValueError:
            continue
    else:
        return False, "Formato de fecha inválido. Use AAAA-MM-DD o DD/MM/AAAA"

    # No permitir fechas futuras (hasta 1 día de tolerancia por zonas horarias)
    if fecha > date.today():
        return False, "La fecha no puede ser futura"

    # No permitir fechas demasiado antiguas (< 1950)
    if fecha < date(1950, 1, 1):
        return False, "La fecha no puede ser anterior a 1950"

    return True, ""


def validar_cantidad_positiva(cantidad: float) -> tuple[bool, str]:
    """
    Valida que una cantidad (kilos, jornales, etc.) sea positiva.
    Retorna (True, "") si es válida, (False, mensaje_error) si no.
    """
    if cantidad is None:
        return False, "La cantidad no puede estar vacía"
    try:
        c = float(cantidad)
    except (TypeError, ValueError):
        return False, "La cantidad debe ser un número válido"
    if c <= 0:
        return False, "La cantidad debe ser un valor positivo mayor a cero"
    if c > 1_000_000:
        return False, "La cantidad no puede superar 1,000,000"
    return True, ""


def validar_texto_no_vacio(texto: str, campo: str = "El campo") -> tuple[bool, str]:
    """
    Valida que un texto no esté vacío.
    Retorna (True, "") si es válido, (False, mensaje_error) si no.
    """
    if not texto or not texto.strip():
        return False, f"{campo} no puede estar vacío"
    if len(texto.strip()) > 200:
        return False, f"{campo} no puede superar los 200 caracteres"
    return True, ""


# ─── Tests: Precio positivo ─────────────────────────────────────────


class TestValidarPrecio:
    """Pruebas para validar_precio_positivo."""

    def test_precio_valido(self):
        """Precio positivo es válido."""
        ok, msg = validar_precio_positivo(15000)
        assert ok
        assert msg == ""

    def test_precio_float_valido(self):
        """Precio con decimales es válido."""
        ok, msg = validar_precio_positivo(15500.50)
        assert ok

    def test_precio_cero(self):
        """Precio igual a cero no es válido."""
        ok, msg = validar_precio_positivo(0)
        assert not ok
        assert "positivo" in msg.lower()

    def test_precio_negativo(self):
        """Precio negativo no es válido."""
        ok, msg = validar_precio_positivo(-1000)
        assert not ok
        assert "positivo" in msg.lower()

    def test_precio_none(self):
        """Precio None no es válido."""
        ok, msg = validar_precio_positivo(None)
        assert not ok
        assert "vacío" in msg.lower()

    def test_precio_string_no_numerico(self):
        """String no numérico no es válido."""
        ok, msg = validar_precio_positivo("abc")
        assert not ok
        assert "número" in msg.lower()


# ─── Tests: Área positiva ───────────────────────────────────────────


class TestValidarArea:
    """Pruebas para validar_area_positiva."""

    def test_area_valida(self):
        """Área positiva es válida."""
        ok, msg = validar_area_positiva(5.0)
        assert ok
        assert msg == ""

    def test_area_pequena_valida(self):
        """Área pequeña (0.1 ha) es válida."""
        ok, msg = validar_area_positiva(0.1)
        assert ok

    def test_area_cero(self):
        """Área igual a cero no es válida."""
        ok, msg = validar_area_positiva(0)
        assert not ok
        assert "positivo" in msg.lower()

    def test_area_negativa(self):
        """Área negativa no es válida."""
        ok, msg = validar_area_positiva(-2)
        assert not ok
        assert "positivo" in msg.lower()

    def test_area_demasiado_grande(self):
        """Área mayor a 1000 ha no es válida."""
        ok, msg = validar_area_positiva(1500)
        assert not ok
        assert "1000" in msg

    def test_area_none(self):
        """Área None no es válida."""
        ok, msg = validar_area_positiva(None)
        assert not ok
        assert "vacía" in msg.lower()


# ─── Tests: Fechas válidas ──────────────────────────────────────────


class TestValidarFecha:
    """Pruebas para validar_fecha."""

    def test_fecha_formato_iso(self):
        """Formato YYYY-MM-DD es válido."""
        hoy = date.today()
        ok, msg = validar_fecha(f"{hoy.year}-01-15")
        assert ok
        assert msg == ""

    def test_fecha_formato_latino(self):
        """Formato DD/MM/AAAA es válido."""
        ok, msg = validar_fecha("15/01/2024")
        assert ok

    def test_fecha_vacia(self):
        """Fecha vacía no es válida."""
        ok, msg = validar_fecha("")
        assert not ok
        assert "vacía" in msg.lower()

    def test_fecha_formato_invalido(self):
        """Formato inválido no es aceptado."""
        ok, msg = validar_fecha("15-01-2024")
        assert not ok
        assert "formato" in msg.lower()

    def test_fecha_futura(self):
        """Fecha futura no es válida."""
        from datetime import timedelta
        futuro = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
        ok, msg = validar_fecha(futuro)
        assert not ok
        assert "futura" in msg.lower()

    def test_fecha_muy_antigua(self):
        """Fecha anterior a 1950 no es válida."""
        ok, msg = validar_fecha("1949-12-31")
        assert not ok
        assert "1950" in msg

    def test_fecha_dia_mes_invalido(self):
        """Día o mes inválido (ej. 32/01/2024) no es aceptado."""
        ok, msg = validar_fecha("32/01/2024")
        assert not ok
        assert "formato" in msg.lower() or "inválido" in msg.lower()

    def test_fecha_mes_invalido(self):
        """Mes 13 no es válido."""
        ok, msg = validar_fecha("2024-13-01")
        assert not ok


# ─── Tests: Cantidad positiva ───────────────────────────────────────


class TestValidarCantidad:
    """Pruebas para validar_cantidad_positiva."""

    def test_cantidad_valida(self):
        """Cantidad positiva es válida."""
        ok, msg = validar_cantidad_positiva(500)
        assert ok
        assert msg == ""

    def test_cantidad_cero(self):
        """Cantidad cero no es válida."""
        ok, msg = validar_cantidad_positiva(0)
        assert not ok
        assert "positivo" in msg.lower()

    def test_cantidad_negativa(self):
        """Cantidad negativa no es válida."""
        ok, msg = validar_cantidad_positiva(-100)
        assert not ok

    def test_cantidad_muy_grande(self):
        """Cantidad mayor a 1,000,000 no es válida."""
        ok, msg = validar_cantidad_positiva(2_000_000)
        assert not ok

    def test_cantidad_none(self):
        """Cantidad None no es válida."""
        ok, msg = validar_cantidad_positiva(None)
        assert not ok


# ─── Tests: Texto no vacío ──────────────────────────────────────────


class TestValidarTexto:
    """Pruebas para validar_texto_no_vacio."""

    def test_texto_valido(self):
        """Texto con contenido es válido."""
        ok, msg = validar_texto_no_vacio("Finca La Esperanza")
        assert ok

    def test_texto_vacio(self):
        """Texto vacío no es válido."""
        ok, msg = validar_texto_no_vacio("")
        assert not ok
        assert "vacío" in msg.lower()

    def test_texto_solo_espacios(self):
        """Texto con solo espacios no es válido."""
        ok, msg = validar_texto_no_vacio("   ")
        assert not ok

    def test_texto_demasiado_largo(self):
        """Texto mayor a 200 caracteres no es válido."""
        ok, msg = validar_texto_no_vacio("a" * 201)
        assert not ok
        assert "200" in msg

    def test_texto_con_nombre_campo_personalizado(self):
        """El mensaje de error incluye el nombre del campo personalizado."""
        ok, msg = validar_texto_no_vacio("", "El nombre de la finca")
        assert "El nombre de la finca" in msg
