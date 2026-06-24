"""
Handler de /ayuda - Guía de uso del bot.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command

logger = logging.getLogger(__name__)


def get_ayuda_router(db=None) -> Router:
    router = Router()

    def _split_texto(texto: str, max_len: int = 4096) -> list:
        if len(texto) <= max_len:
            return [texto]
        partes = []
        while len(texto) > max_len:
            corte = texto.rfind("\n", 0, max_len)
            if corte == -1:
                corte = max_len
            partes.append(texto[:corte])
            texto = texto[corte:].strip()
        if texto:
            partes.append(texto)
        return partes

    @router.message(Command("ayuda"))
    @router.callback_query(F.data == "menu_ayuda")
    async def cmd_ayuda(event: types.Message | types.CallbackQuery):
        """Muestra la guía de uso del bot."""

        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
        else:
            message = event
            send = message.answer

        texto = (
            "☕ *Asistente Caficultor — Guía de Uso* 🌱\n\n"
            "Este bot te ayuda a registrar los ingresos y costos "
            "de tu finca cafetera, y genera un Excel profesional "
            "de costos de producción.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*📋 Comandos disponibles:*\n\n"
            "*/start* — Inicio y verificación de acceso\n"
            "*/fincas* — Gestionar tus fincas 🗺️\n"
            "*/lotes* — Administrar lotes de cada finca 🌱\n"
            "*/ingreso* — Registrar venta de café ☕💰\n"
            "*/costo* — Registrar costo de producción 📉\n"
            "*/resumen* — Ver resumen de tu finca 📊\n"
            "*/ayuda* — Mostrar esta guía ❓\n"
            "*/cancelar* — Cancelar operación actual\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*📌 ¿Cómo empezar?*\n\n"
            "1. Usa /start para solicitar acceso\n"
            "2. Espera a que el administrador apruebe tu solicitud ✅\n"
            "3. Crea tu finca con /fincas 🏠\n"
            "4. Registra los lotes con /lotes 📍\n"
            "5. Empieza a registrar ingresos y costos\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*💰 Registrar Ingresos:*\n\n"
            "Usa /ingreso y sigue los pasos:\n"
            "• Selecciona la finca\n"
            "• Ingresa la fecha de venta\n"
            "• Selecciona el tipo de café (CPS, Pasilla, Re-re)\n"
            "• Indica los kilos vendidos\n"
            "• Indica el valor total recibido\n"
            "• Confirma los datos\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*📉 Registrar Costos:*\n\n"
            "Usa /costo y selecciona la categoría:\n\n"
            "🌱 *Instalación* — Costos de siembra y establecimiento\n"
            "🌿 *Arvenses* — Control de malezas\n"
            "🧪 *Fertilización* — Abonos y fertilizantes\n"
            "🛡️ *Fitosanitario* — Control de plagas y enfermedades\n"
            "🌳 *Sombrío* — Regulación de sombra\n"
            "🔧 *Otras Labores* — Otras actividades\n"
            "☕ *Recolección* — Cosecha de café\n"
            "🏭 *Beneficio* — Procesamiento del café\n"
            "📋 *Gastos Admin* — Gastos administrativos\n\n"
            "Para cada costo puedes agregar:\n"
            "• Mano de obra (jornales)\n"
            "• Insumos (productos, fertilizantes, etc.)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*📊 Generar Excel:*\n\n"
            "Usa /resumen para ver tus datos y generar\n"
            "el Excel de costos de producción.\n\n"
            "El Excel incluye 18 hojas con:\n"
            "• Resultados económicos automáticos\n"
            "• Gráficos de participación por rubro\n"
            "• Todas las fórmulas pre-cargadas\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*🌐 Tipos de Café:*\n\n"
            "• *CPS* — Café Pergamino Seco\n"
            "• *Pasilla* — Café de segunda calidad\n"
            "• *Re-re* — Re-recolección\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*❓ ¿Necesitas ayuda?*\n\n"
            "Contacta al administrador si tienes dudas\n"
            "o problemas con el bot.\n\n"
            "☕ *¡Buena cosecha!* 🌱"
        )

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Volver al menú", callback_data="volver_menu")],
            ]
        )

        partes = _split_texto(texto)
        for i, parte in enumerate(partes):
            if i == len(partes) - 1:
                await send(parte, parse_mode="Markdown", reply_markup=keyboard)
            else:
                await send(parte, parse_mode="Markdown")

    return router
