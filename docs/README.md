# ☕ Asistente de Costos para Caficultores

Sistema integral de gestión financiera para caficultores colombianos.

## 📋 Descripción

Aplicación que permite a los caficultores registrar ingresos, costos,
y generar indicadores técnicos de rendimiento. Incluye bot de Telegram
y Mini App web.

## 🏗️ Arquitectura

```
├── bot/                        # Bot de Telegram (aiogram 3.x)
│   ├── main.py                # Punto de entrada
│   ├── handlers/              # 11 handlers (fincas, lotes, costos, etc.)
│   ├── database.py            # Base de datos SQLite
│   ├── excel_manager.py       # Export/Import Excel
│   └── ...
├── mini-app/                  # Telegram Mini App (web)
│   ├── index.html             # Frontend SPA
│   ├── css/                   # Estilos
│   ├── js/                    # Lógica frontend
│   └── api/                   # Backend FastAPI
├── shared/                    # Componentes compartidos
│   └── database.py            # BD SQLite thread-safe
└── .github/workflows/         # CI/CD
```

## 🚀 Instalación

```bash
# Clonar repositorio
git clone https://github.com/iglm/asistente-caficultor.git
cd asistente-caficultor

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
pip install -r mini-app/api/requirements.txt

# Configurar token
echo "TU_TOKEN_AQUI" > scripts/.bot_token_caficultor.txt

# Iniciar bot
python main.py
```

## 📱 Mini App

La Mini App se despliega automáticamente en GitHub Pages:
**https://iglm.github.io/asistente-caficultor/**

### Configurar en BotFather:
1. Hablar con @BotFather
2. `/newapp`
3. Seleccionar el bot
4. Título: "Asistente de Costos"
5. Short name: `caficultor`
6. URL: `https://iglm.github.io/asistente-caficultor/`

## 📊 Funcionalidades

- ✅ Registro de fincas y lotes
- ✅ Registro de ingresos (CPS, Pasilla, Re-re)
- ✅ Registro de costos (9 categorías FEPCafé)
- ✅ Indicadores técnicos automáticos
- ✅ Export/Import Excel (18 hojas con fórmulas y gráficos)
- ✅ Presupuestos
- ✅ Asesoría profesional
- ✅ Filtro por período (semana/mes/año)
- ✅ Alertas automáticas
- ✅ Entrada por voz (Whisper)

## 👨‍💻 Desarrollado por

**Lucas Mateo Tabares Franco**
Asesorado por: **Ing. Jhoan Sebastian Bustamante Montes**
Contacto: mateotabares7@gmail.com
