# Guía de Despliegue

## GitHub Pages (Mini App)

El despliegue es automático vía GitHub Actions.

### Requisitos
1. Repositorio en GitHub
2. GitHub Pages habilitado (Settings > Pages > Source: GitHub Actions)

### Proceso
1. Push a `main` con cambios en `mini-app/`
2. GitHub Actions ejecuta `deploy.yml`
3. Mini App disponible en `https://<user>.github.io/<repo>/`

### Verificar
```bash
# Verificar que el workflow corra
gh workflow run deploy.yml

# Verificar estado
gh run list
```

### Workflow (`.github/workflows/deploy.yml`)
```yaml
name: Deploy Mini App to GitHub Pages
on:
  push:
    branches: [main]
    paths:
      - 'mini-app/**'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: 'mini-app'
      - uses: actions/deploy-pages@v4
```

## VPS (Bot de Telegram)

### Requisitos
- Ubuntu 20.04+
- Python 3.11+
- Token de Telegram (de [@BotFather](https://t.me/BotFather))

### Instalación
```bash
# Clonar repositorio
git clone https://github.com/iglm/asistente-caficultor.git
cd asistente-caficultor

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar token
echo "TU_TOKEN" > scripts/.bot_token_caficultor.txt

# Verificar template Excel
ls -la "data/plantilla/Costos de produccion - 2026.xlsx"

# Ejecutar manual (para prueba)
python main.py
```

### Instalación como servicio systemd

```bash
# Copiar archivo de servicio
sudo cp systemd/bot-asistente.service /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar e iniciar
sudo systemctl enable bot-asistente
sudo systemctl start bot-asistente
```

### Comandos útiles
```bash
# Ver estado
sudo systemctl status bot-asistente

# Reiniciar (siempre después de editar código)
sudo systemctl restart bot-asistente

# Ver logs del servicio
journalctl -u bot-asistente -f

# Ver logs del bot
tail -f /home/lucas-mateo/bot-asistente-caficultor/bot.log
```

### Archivo de servicio (`systemd/bot-asistente.service`)
```ini
[Unit]
Description=Bot Asistente Financiero Caficultor
After=network.target

[Service]
Type=simple
User=lucas-mateo
WorkingDirectory=/home/lucas-mateo/bot-asistente-caficultor
ExecStart=/home/lucas-mateo/bot-asistente-caficultor/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Mini App + API (Producción)

Para ejecutar la Mini App con su backend API en un servidor:

```bash
# Activar entorno
source venv/bin/activate

# Iniciar API (puerto 8080)
cd mini-app/api
python app.py

# O con uvicorn directamente
uvicorn app:app --host 0.0.0.0 --port 8080
```

## Sync automático a GitHub

El proyecto incluye un script de sincronización que se ejecuta cada 24h.

```bash
# Sync manual
python sync_to_github.py

# Solo un usuario específico
python sync_to_github.py --user-id 123456

# Simular (dry-run)
python sync_to_github.py --dry-run
```

Requiere SSH key configurada para `git@github.com:iglm/caficultor-datos.git`.

## Checklist de Despliegue

- [ ] Tests unitarios pasan (9/9)
- [ ] Test E2E pasa (21/21)
- [ ] Auditoría de callbacks: 0 handlers faltantes
- [ ] Sin errores en `bot.log`
- [ ] Token de Telegram configurado
- [ ] Excel template presente en `data/plantilla/`
- [ ] GitHub Pages habilitado
- [ ] systemd configurado (si aplica)
- [ ] `sudo systemctl restart bot-asistente` ejecutado
