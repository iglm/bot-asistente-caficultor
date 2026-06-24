"""
Conftest para los tests del bot asistente caficultor.
Anula la configuración conflictiva del pyproject.toml del home.
"""
import sys
from pathlib import Path

# Asegurar que el directorio raíz esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
