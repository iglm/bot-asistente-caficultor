# ☕🤖 Asistente Financiero para Caficultores

> **Tu finca organizada desde el celular.** Registra tus gastos e ingresos de café y lleva el control de tu producción — todo desde un mensaje de Telegram.

---

## 📖 ¿Qué hace este bot?

Este bot te ayuda a **llevar la cuenta de tu finca de café** de forma fácil:

| 📋 ¿Qué puedes hacer? | 📝 Ejemplo |
|---|---|
| 🏡 Registrar tus fincas | "Finca El Paraíso, Huila, Garzón" |
| 🌱 Registrar tus lotes | "Lote 1, 2.5 hectáreas, Caturra" |
| 💰 Registrar ventas de café | "Vendí 500 kilos de CPS a $2,800,000" |
| 📉 Registrar gastos de producción | "5 jornales de guadaña a $40,000" |
| 📊 Ver resumen financiero | Cuánto gastaste, cuánto ganaste, tu margen |
| 📥 Descargar tu Excel | El formato oficial FNC de costos |

---

## 🚀 Cómo empezar

### Paso 1: Solicitar accion
1. Busca el bot en Telegram: **@TuBotCaficultor**
2. Escribe `/start`
3. El bot te registrará automáticamente y pedirá aprobación

### Paso 2: Esperar aprobación
- El administrador revisará tu solicitud
- En menos de 24 horas tendrás acceso
- Recibirás un mensaje cuando estés aprobado

### Paso 3: ¡Empezar a usar!
Una vez aprobado, el bot estará listo para usar:

```
/start → Ver menú principal
```

---

## 📱 Comandos disponibles

| Comando | Qué hace |
|---------|----------|
| `/start` | Inicio + menú principal |
| `/ayuda` | Ver guía de uso |
| `/fincas` | Gestionar tus fincas |
| `/lotes` | Gestionar tus lotes |
| `/ingreso` | Registrar una venta de café |
| `/costo` | Registrar un gasto de producción |
| `/resumen` | Ver el resumen de tu finca |
| `/excel` | Descargar tu Excel de costos |

---

## 💡 Cómo registrar un gasto (ejemplo)

```
1. Escribe /costo
2. El bot pregunta: "¿Qué finca?" → Selecciona tu finca
3. El bot pregunta: "¿Qué tipo de gasto?" → Elige una opción
   [🌱 Instalación] [🌿 Arvenses] [🧪 Fertilización]
   [🛡️ Fitosanitario] [🌳 Sombrío] [🔧 Otras Labores]
   [☕ Recolección] [🏭 Beneficio] [📋 Administrativo]
4. El bot pregunta datos específicos según el tipo
5. Confirma y ¡listo! Los datos se guardan
```

---

## 💰 Cómo registrar una venta

```
1. Escribe /ingreso
2. Selecciona tu finca
3. El bot pregunta:
   - ¿Cuándo vendiste? (fecha)
   - ¿Qué tipo de café? (CPS, Pasilla, Re-re)
   - ¿Cuántos kilos?
   - ¿A cuánto te pagaron el kilo?
4. Confirma y ¡listo!
```

---

## 📊 Tu Excel de costos

Cada vez que necesites ver el estado completo de tu producción:

```
1. Escribe /excel
2. El bot genera tu Excel oficial de costos de producción
3. Lo recibes directo en Telegram como archivo
4. Ábrelo en Excel o en Google Sheets
```

El Excel incluye:
- ✅ Resumen de ingresos y egresos
- ✅ Costo total de producción
- ✅ Margen de ganancia
- ✅ Gráficos de participación por rubro
- ✅ Formato oficial para caficultores colombianos

---

## 🔐 Tus datos están seguros

- Tus datos se guardan en una base de datos privada
- Solo tú y el administrador tienen acceso
- Los datos se respaldan automáticamente cada 24 horas
- Puedes pedir tu Excel en cualquier momento

---

## ❓ Preguntas frecuentes

**¿Puedo registrar más de una finca?**
Sí, puedes registrar todas las fincas que tengas.

**¿Puedo registrar varios lotes en una finca?**
Sí, cada finca puede tener varios lotes con su propia información.

**¿Qué pasa si me equivoco al registrar algo?**
Puedes volver a registrar. El bot va acumulando todo.

**¿Puedo usar el bot desde cualquier celular?**
Sí, mientras tengas Telegram instalado.

**¿Qué es CPS?**
CPS = Café Pergamino Seco, el tipo de café más común que venden los caficultores.

---

## 📞 Soporte

Si tienes problemas con el bot, contacta al administrador:
📱 @MateoWhatsApp

---

## 👨‍💻 Para técnicos: Instalación

```bash
# 1. Clonar
git clone https://github.com/iglm/bot-asistente-caficultor.git
cd bot-asistente-caficultor

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configurar
echo "TU_TOKEN_AQUI" > scripts/.bot_token_caficultor.txt
cp "Costos de produccion - 2026.xlsx" data/plantilla/

# 4. Probar
python main.py

# 5. Instalar como servicio
sudo cp systemd/bot-asistente.service /etc/systemd/system/
sudo systemctl enable bot-asistentor
sudo systemctl start bot-asistente
```

---

## 📄 Licencia

MIT — Libre para uso de caficultores colombianos 🇨🇴☕
