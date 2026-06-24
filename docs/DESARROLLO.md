# 🛠️ Guía de Desarrollo — Bot Asistente Caficultor ☕

> **Cómo extender, modificar y testear el bot**
> Para desarrolladores que trabajan en el proyecto

---

## 📋 Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| 🧠 Lenguaje | Python | 3.11+ |
| 🤖 Framework Telegram | aiogram | 3.x |
| 🗄️ Base de datos | SQLite | 3.x (WAL mode) |
| 📊 Excel | openpyxl | 3.1.x |
| 🎤 Voz | Whisper (local) | — |
| 🔄 CI/CD | GitHub Actions | — |
| ☁️ Sync | git (SSH) | — |

---

## 🏗️ Estructura del Proyecto

```
bot-asistente-caficultor/
├── main.py                 # Entry point del bot
├── config.py               # Configuración central (token, rutas, categorías)
├── database.py             # Capa de datos SQLite (clase Database)
├── excel_manager.py        # Generación de Excel (clase ExcelManager)
├── middleware.py           # CancelMiddleware (limpieza FSM global)
├── voice_handler.py        # Transcripción Whisper + parser NL
├── sync_to_github.py       # Sync diario a GitHub
├── utils.py                # Helpers: botones inline reutilizables
├── auditar_callbacks.py    # Auditoría de callbacks vs handlers
│
├── handlers/               # Handlers de Telegram
│   ├── __init__.py         # Exporta todos los get_*_router()
│   ├── menu.py             # /menu, /cancelar, borrar datos
│   ├── start.py            # /start, registro
│   ├── admin.py            # /usuarios, aprobar, revocar
│   ├── fincas.py           # /fincas, CRUD fincas
│   ├── lotes.py            # /lotes, CRUD lotes
│   ├── ingresos.py         # /ingreso, registrar ventas
│   ├── costos.py           # /costo, registrar gastos
│   ├── reportes.py         # /resumen, /excel
│   ├── importar.py         # Importar Excel
│   ├── ayuda.py            # /ayuda, guía
│   └── voice.py            # Mensajes de voz
│
├── data/
│   ├── finca.db            # Base de datos SQLite
│   └── plantilla/
│       └── Costos de produccion - 2026.xlsx  # Template Excel
│
├── tests/
│   ├── test_database.py         # Tests unitarios (9 tests)
│   ├── e2e_test.py             # Test E2E completo (21 pasos)
│   ├── informe_e2e.md          # Informe de test E2E
│   ├── conftest.py             # Fixtures de pytest
│   ├── simulador_caficultor.py # Simulador de datos masivos
│   └── simulador.py            # Simulador legacy
│
├── exports/                # Archivos Excel temporales
│
├── docs/                   # Documentación
│   ├── FLUJO.md            # Diagramas de flujo
│   ├── REFERENCIA_API.md   # Referencia de API
│   ├── EXCEL.md            # Estructura del Excel
│   └── DESARROLLO.md       # Esta guía
│
├── scripts/                # Scripts auxiliares
│   └── .bot_token_caficultor.txt  # Token de Telegram (gitignored)
│
├── systemd/
│   └── bot-asistente.service      # Servicio systemd
│
├── requirements.txt
└── README.md
```

---

## 🧩 Cómo agregar un nuevo Handler

### Paso 1: Crear el archivo

```bash
touch handlers/mi_handler.py
```

### Paso 2: Implementar el router

```python
"""handlers/mi_handler.py — Mi nuevo handler"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database import Database
from utils import boton_menu, botones_menu_cancelar

logger = logging.getLogger(__name__)


def get_mi_handler_router(db: Database) -> Router:
    router = Router()

    @router.message(Command("micomando"))
    @router.callback_query(F.data == "menu_micomando")
    async def cmd_micomando(event: types.Message | types.CallbackQuery, state: FSMContext):
        """Dual handler: acepta tanto /comando como callback del menú."""
        await state.clear()
        user_id = event.from_user.id

        # Normalizar event (Message o CallbackQuery)
        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
        else:
            message = event
            send = message.answer

        # Verificar acceso
        if not db.is_approved(user_id):
            await send("⏳ No tienes acceso.", parse_mode="HTML", reply_markup=boton_menu())
            return

        # ... lógica del handler ...
        await send("✅ ¡Comando ejecutado!", parse_mode="HTML", reply_markup=boton_menu())

    return router
```

### Paso 3: Registrar el handler

En `handlers/__init__.py`:

```python
from handlers.mi_handler import get_mi_handler_router

__all__.append("get_mi_handler_router")
```

En `main.py`:

```python
from handlers import (
    ...
    get_mi_handler_router,
)

dp.include_router(get_mi_handler_router(db))
```

### Paso 4: Agregar al menú

En `handlers/menu.py`, en `cmd_menu()` y `volver_menu()`, agregar botón:

```python
types.InlineKeyboardButton(text="🔧 Mi Comando", callback_data="menu_micomando"),
```

### Paso 5: Agregar al CancelMiddleware (si aplica)

En `middleware.py`, en `COMMANDS`:

```python
COMMANDS = {..., "/micomando"}
```

### Paso 6: Agregar al CancelMiddleware para callbacks

```python
if callback_data.startswith("menu_") or callback_data.startswith("ir_") or callback_data.startswith("menu_micomando"):
```

---

## 📝 Convenciones de código

### Reglas obligatorias

1. **Dual handlers**: Todo comando debe aceptar `Message | CallbackQuery`
2. **`state.clear()` al inicio**: Siempre limpiar estado al entrar a un handler
3. **`parse_mode="HTML"`**: Siempre, nunca Markdown
4. **Botones inline**: Usar `utils.py` helpers (`boton_menu()`, `botones_menu_cancelar()`, etc.)
5. **Callbacks dinámicos**: Usar `F.data.startswith("prefix:")` para callbacks con parámetros
6. **Logging**: Usar `logger = logging.getLogger(__name__)` en cada handler
7. **Errores**: Capturar con `try/except` y loguear con `logger.error(..., exc_info=True)`

### Nombrado de callbacks

```
# Menú principal
menu_fincas, menu_lotes, menu_ingresos, menu_costos
menu_resumen, menu_excel, menu_importar, menu_ayuda

# Acciones
nueva_finca, nuevo_lote:{finca_id}
ingreso_finca:{id}, costo_finca:{id}
costo_lote:{id}  # 0 = toda la finca
cat_costo:{categoria_key}

# Confirmación
conf_ingreso:si/no
conf_costo_mo:si/no/insumos
conf_insumo:si/otro/no
confirmar_borrar:si/no, confirmar_borrar_2:si/no

# Navegación
volver_menu, cancelar_operacion
```

---

## 🗄️ Cómo agregar una nueva categoría de costo

### Paso 1: En `config.py`

```python
# En CATEGORIAS_PADRE (si tiene MO + Insumos):
CATEGORIAS_PADRE = {
    ...
    "mi_categoria": {
        "nombre": "🔬 Mi Categoría",
        "mo": "mi_categoria_mo",
        "insumos": "mi_categoria_insumos",
    },
}

# En CATEGORIAS (mapeo completo):
CATEGORIAS = {
    ...
    "mi_categoria_mo": {"nombre": "Mi Categoría MO", "hoja": "Mi Hoja", "seccion": "MO"},
    "mi_categoria_insumos": {"nombre": "Mi Categoría Insumos", "hoja": "Mi Hoja", "seccion": "Insumos"},
    "mi_categoria": {"nombre": "Mi Categoría", "hoja": "Mi Hoja", "seccion": "Total"},
}
```

### Paso 2: En `handlers/costos.py`

Agregar botón en `mostrar_categorias_costos()`:

```python
types.InlineKeyboardButton(text="🔬 Mi Categoría", callback_data="cat_costo:mi_categoria"),
```

### Paso 3: En `database.py`

```python
CATEGORIAS_CON_MO_Y_INSUMOS = [
    ..., "mi_categoria",
]
```

### Paso 4: En `excel_manager.py`

```python
HOJA_CONFIG = {
    ...
    "Mi Hoja": {
        "mo_cols": {...},
        "insumos_cols": {...},
        "categorias_mo": ["mi_categoria_mo"],
        "categorias_insumos": ["mi_categoria_insumos"],
    },
}
```

---

## 🧪 Testing

### Tests unitarios

```bash
cd /home/lucas-mateo/bot-asistente-caficultor
source venv/bin/activate
python -m pytest tests/test_database.py -v
```

Actualmente **9 tests pasando** que cubren:

| Test | Descripción |
|------|-------------|
| `test_es_categoria_compuesta_returns_true` | Categorías compuestas detectadas |
| `test_es_categoria_compuesta_returns_false_for_simple` | Categorías simples no son compuestas |
| `test_es_categoria_simple_returns_true` | Categorías simples detectadas |
| `test_es_categoria_simple_returns_false_for_compuesta` | Compuestas no son simples |
| `test_resumen_vacio` | Resumen con datos cero |
| `test_resumen_categorias_compuestas` | Suma MO + Insumos correcta |
| `test_resumen_categorias_simples` | Categorías simples suman bien |
| `test_resumen_ingresos` | Ingresos, egresos y margen |
| `test_resumen_con_lotes_y_costo_hectarea` | Área y costo por hectárea |

### Test E2E

```bash
python tests/e2e_test.py
```

**21 pasos** que verifican:
1. Limpieza de BD
2. Conectividad del bot
3. `/start` y `/menu`
4. Creación de fincas y lotes
5. Registro de ingresos y costos
6. `/resumen` y exportación Excel
7. Importación de plantilla
8. Borrado de datos
9. Persistencia (re-crear y verificar)

### Simulación de datos masivos

```bash
python tests/simulador_caficultor.py
```

- 1 finca, 20 lotes, 3 años de datos
- 894+ transacciones en todas las categorías
- Precios reales del mercado/sector/USDA

### Auditoría de callbacks

```bash
python3 ~/.hermes/skills/devops/probador-de-bots/scripts/auditar_callbacks.py
```

Verifica que **todos los botones inline tengan su handler correspondiente**.

---

## 🚀 Deploy

### Como servicio systemd

```bash
sudo cp systemd/bot-asistente.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bot-asistente
sudo systemctl start bot-asistente
```

**SIEMPRE reiniciar después de editar código:**

```bash
sudo systemctl restart bot-asistente
```

### Logs

```bash
# Log del bot
tail -f /home/lucas-mateo/bot-asistente-caficultor/bot.log

# Log del servicio
journalctl -u bot-asistente -f
```

---

## 🔄 Sync a GitHub

Se ejecuta automáticamente cada 24 horas (cron job).

```bash
python sync_to_github.py           # Todos los usuarios
python sync_to_github.py --user-id 123456  # Solo uno
python sync_to_github.py --dry-run         # Simular
```

Requiere SSH key configurada para `git@github.com:iglm/caficultor-datos.git`.

---

## 🐛 Pitfalls conocidos

| # | Problema | Solución |
|---|----------|----------|
| 1 | BD se limpia al reiniciar | `init_db()` crea admin por defecto |
| 2 | Fincas duplicadas | Validar `SELECT COUNT(*)` antes de crear |
| 3 | FSM state no limpia | CancelMiddleware con todos los comandos |
| 4 | Excel límites hardcodeados | `insert_rows()` dinámico + copy/paste fórmulas |
| 5 | Resumen no contabiliza categorías simples | Separar queries por tipo de categoría |
| 6 | `parse_mode` inconsistente | Usar HTML siempre |
| 7 | systemd no recarga cambios | `sudo systemctl restart bot-asistente` |
| 8 | Estructura de costos irreal | Usar target-driven generation con % reales |
| 9 | Menú inconsistente | Callbacks IDÉNTICOS en cmd_menu y volver_menu |
| 10 | Transacciones sin finca_id | Siempre insertar finca_id + lote_id |

---

## 📌 Checklist para nuevo release

- [ ] Tests unitarios pasan (9/9)
- [ ] Test E2E pasa (21/21)
- [ ] Auditoría de callbacks: 0 handlers faltantes
- [ ] Sin errores en `bot.log`
- [ ] Excel generado con fórmulas correctas
- [ ] Menú idéntico en `cmd_menu` y `volver_menu`
- [ ] Borrar datos funciona (incluso sin datos)
- [ ] Exportar Excel funciona (incluso sin datos)
- [ ] Importar Excel funciona (plantilla + preview + confirmar)
- [ ] GitHub sync configurado
- [ ] `sudo systemctl restart bot-asistente` ejecutado
