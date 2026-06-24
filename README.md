# ☕🤖 Asistente Financiero para Caficultores

> **Tu finca organizada desde el celular.** Registra gastos e ingresos de café, lleva el control de tu producción y genera tu Excel oficial de costos — todo desde un mensaje de Telegram.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-lightgrey.svg)](https://sqlite.org)
[![openpyxl](https://img.shields.io/badge/openpyxl-3.1.x-orange.svg)](https://openpyxl.readthedocs.io)
[![Tests](https://img.shields.io/badge/tests-9/9%20✅-success.svg)](tests/test_database.py)
[![E2E](https://img.shields.io/badge/E2E-21/21%20✅-success.svg)](tests/e2e_test.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 📖 ¿Qué hace este bot?

Este bot de Telegram ayuda a **caficultores colombianos** a llevar el control financiero de sus fincas de café de forma simple y desde el celular.

| 📋 Funcionalidad | 📝 Descripción |
|---|---|
| 🏡 **Gestionar fincas** | Registra una o varias fincas con ubicación |
| 🌱 **Gestionar lotes** | Crea lotes con área, árboles, variedad y fecha de siembra |
| 💰 **Registrar ventas** | Venta de CPS, Pasilla y Re-re con fecha, kilos y valor |
| 📉 **Registrar costos** | 9 categorías de costos: instalación, fertilización, recolección, etc. |
| 📊 **Ver resumen** | Ingresos, egresos, margen y costo por hectárea |
| 📋 **Exportar Excel** | Excel profesional con 18 hojas, fórmulas y gráficos |
| 📥 **Importar Excel** | Carga datos desde plantilla Excel |
| 🎤 **Entrada por voz** | Envía mensaje de voz y el bot transcribe y parsea los datos |
| 🗑️ **Borrar datos** | Confirmación triple para eliminación segura |

---

## 🚀 Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| 🧠 Lenguaje | **Python 3.11** |
| 🤖 Framework | **aiogram 3.x** (telegram bot API) |
| 🗄️ Base de datos | **SQLite** (WAL mode, sin servidor) |
| 📊 Excel | **openpyxl** (generación dinámica con fórmulas y gráficos) |
| 🎤 Voz | **Whisper** (transcripción local, gratis) |
| 🔄 CI | **GitHub Actions** |
| ☁️ Backup | **GitHub Sync** (automático cada 24h) |

---

## 🏗️ Estructura del Proyecto

```
bot-asistente-caficultor/
├── main.py                 # 🚀 Entry point
├── config.py               # ⚙️ Configuración (token, rutas, categorías)
├── database.py             # 🗄️ Capa SQLite (usuarios, fincas, lotes, transacciones)
├── excel_manager.py        # 📊 Generación de Excel (18 hojas + gráficos)
├── middleware.py            # 🔄 CancelMiddleware (limpieza FSM global)
├── voice_handler.py        # 🎤 Transcripción Whisper + parser NL
├── utils.py                # 🔧 Helpers: botones inline reutilizables
├── sync_to_github.py       # ☁️ Sync diario a GitHub
│
├── handlers/               # 📁 Handlers de Telegram
│   ├── menu.py             # /menu, /cancelar, borrar datos
│   ├── start.py            # /start, registro de usuarios
│   ├── admin.py            # /usuarios, aprobar, revocar
│   ├── fincas.py           # /fincas, CRUD fincas
│   ├── lotes.py            # /lotes, CRUD lotes
│   ├── ingresos.py         # /ingreso, registrar ventas
│   ├── costos.py           # /costo, registrar gastos (16 estados FSM)
│   ├── reportes.py         # /resumen, /excel
│   ├── importar.py         # Importar Excel desde archivo
│   ├── ayuda.py            # /ayuda, guía completa
│   └── voice.py            # Mensajes de voz
│
├── tests/                  # 🧪 Tests
│   ├── test_database.py    # 9 tests unitarios
│   ├── e2e_test.py         # 21 pasos E2E
│   └── simulador_caficultor.py  # Simulación masiva (894+ transacciones)
│
├── docs/                   # 📚 Documentación
│   ├── FLUJO.md            # Diagramas de flujo y FSM
│   ├── REFERENCIA_API.md   # Referencia de API
│   ├── EXCEL.md            # Estructura del Excel
│   └── DESARROLLO.md       # Guía de desarrollo
│
├── data/                   # 📦 Datos
│   ├── finca.db            # Base de datos SQLite
│   └── plantilla/          # Template Excel
│
└── exports/                # 📤 Exportaciones temporales
```

---

## 📱 Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| `/start` | Inicio + solicitud de acceso |
| `/menu` | Menú principal 🏠 |
| `/ayuda` | Guía completa de uso ❓ |
| `/fincas` | Gestionar tus fincas 🗺️ |
| `/lotes` | Gestionar tus lotes 🌱 |
| `/ingreso` | Registrar venta de café ☕💰 |
| `/costo` | Registrar costo de producción 📉 |
| `/resumen` | Ver resumen financiero 📊 |
| `/excel` | Generar y descargar Excel 📋 |
| `/cancelar` | Cancelar operación actual ❌ |

**Admin:**
| `/usuarios` | Ver todos los usuarios |
| `/revocar USER_ID` | Revocar acceso |
| Aprobar/Rechazar desde botones inline | Gestionar solicitudes |

---

## 🧪 Testing

### Tests unitarios (9/9 pasando ✅)

```bash
cd /home/lucas-mateo/bot-asistente-caficultor
source venv/bin/activate
python -m pytest tests/test_database.py -v
```

### Test E2E (21/21 pasos exitosos ✅)

```bash
python tests/e2e_test.py
```

### Simulación de datos masivos

```bash
python tests/simulador_caficultor.py
```

Genera 1 finca, 20 lotes, 894+ transacciones en 3 años con precios reales.

---

## 💻 Instalación (para técnicos)

### Requisitos

- Python 3.11+
- Git
- Token de Bot de Telegram (de [@BotFather](https://t.me/BotFather))

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/iglm/bot-asistente-caficultor.git
cd bot-asistente-caficultor

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar token
echo "TU_TOKEN_AQUI" > scripts/.bot_token_caficultor.txt

# 5. Verificar template Excel
ls -la "data/plantilla/Costos de produccion - 2026.xlsx"

# 6. Ejecutar
python main.py
```

### Instalación como servicio

```bash
sudo cp systemd/bot-asistente.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bot-asistente
sudo systemctl start bot-asistente

# Ver logs
journalctl -u bot-asistente -f
```

---

## 📊 El Excel de Costos

Cada vez que uses `/excel`, el bot genera un archivo `.xlsx` con:

| Componente | Descripción |
|------------|-------------|
| 📄 **18 hojas** | Datos de lotes, ingresos, costos (9 categorías), resultados |
| 🧮 **Fórmulas automáticas** | Subtotales, totales, costo por hectárea |
| 📈 **3 gráficos** | BarChart (costos), PieChart (distribución), LineChart (tendencia) |
| 🔄 **Dinámico** | Sin límites de filas — se adapta a tus datos |
| 📥 **Importable** | Puedes subir datos desde Excel al bot |

---

## 🔐 Seguridad y Privacidad

- ✅ Datos almacenados en SQLite local (no en la nube)
- ✅ Sistema de aprobación de usuarios (solo usuarios autorizados)
- ✅ Confirmación triple para borrar datos
- ✅ Sync cifrado vía SSH a GitHub privado
- ✅ Logs detallados para auditoría

---

## 📚 Documentación

| Documento | Descripción |
|-----------|-------------|
| [📖 FLUJO.md](docs/FLUJO.md) | Diagramas de flujo de cada comando y FSM states |
| [📚 REFERENCIA_API.md](docs/REFERENCIA_API.md) | Documentación técnica de handlers y métodos |
| [📊 EXCEL.md](docs/EXCEL.md) | Estructura del Excel, fórmulas y hojas |
| [🛠️ DESARROLLO.md](docs/DESARROLLO.md) | Guía para desarrolladores |

---

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor:

1. Hacé fork del proyecto
2. Creá una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Hacé commit de tus cambios (`git commit -m 'Agrega nueva funcionalidad'`)
4. Hacé push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrí un Pull Request

Ver [DESARROLLO.md](docs/DESARROLLO.md) para convenciones y guía de desarrollo.

---

## 📄 Licencia

**MIT** — Libre para uso de caficultores colombianos 🇨🇴☕

---

## 📞 Soporte

¿Problemas con el bot? Contactá al administrador:
📱 **@MateoWhatsApp**

---

<p align="center">
  <b>☕ ¡Buena cosecha! 🌱</b><br>
  <i>Hecho con ❤️ para caficultores colombianos</i>
</p>
