"""
Conftest para los tests del bot asistente caficultor.
Provee fixtures compartidos: DB temporal, mock de Telegram Update.
"""

import sys
from pathlib import Path

# Asegurar que el directorio raíz esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unittest.mock import MagicMock, AsyncMock
import pytest
from database import Database


@pytest.fixture
def db(tmp_path):
    """
    Crea una instancia de Database apuntando a un archivo temporal
    (evita acceder a la BD real en data/finca.db).
    tmp_path se limpia automáticamente al finalizar el fixture.
    """
    db_path = str(tmp_path / "test.db")
    d = Database(db_path=db_path)
    d.init_db()
    yield d


@pytest.fixture
def finca_id(db: Database) -> int:
    """Crea un usuario y una finca de prueba, retorna el ID de la finca."""
    db.upsert_user(user_id=999, username="test_user")
    return db.create_finca(
        user_id=999,
        nombre="Finca Test",
        region="Test Region",
        departamento="Test Depto",
    )


@pytest.fixture
def lote_id(db: Database, finca_id: int) -> int:
    """Crea un lote de prueba, retorna el ID del lote."""
    return db.create_lote(
        finca_id=finca_id,
        nombre="Lote Test",
        area=5.0,
        num_arboles=5000,
        variedad="Castillo",
        fecha_siembra="2023-01-15",
    )


@pytest.fixture
def mock_telegram_update():
    """
    Crea un mock de un objeto Update de Telegram (aiogram) con fields comunes.
    Útil para tests de handlers y middlewares sin necesidad del bot real.
    """
    update = MagicMock()
    update.message = MagicMock()
    update.message.from_user = MagicMock()
    update.message.from_user.id = 999
    update.message.from_user.username = "test_user"
    update.message.text = ""
    update.message.chat = MagicMock()
    update.message.chat.id = 999
    update.message.reply = AsyncMock()
    update.message.answer = AsyncMock()
    update.callback_query = None
    return update
