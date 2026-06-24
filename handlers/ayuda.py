"""
Handler de /ayuda - Guía de uso del bot.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


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


def get_ayuda_router(db=None) -> Router:
    router = Router()

    @router.message(Command("ayuda"))
    @router.callback_query(F.data == "menu_ayuda")
    async def cmd_ayuda(event: types.Message | types.CallbackQuery, state: FSMContext):
        """Muestra la guía de uso del bot."""
        await state.clear()

        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
        else:
            message = event
            send = message.answer

        texto = (
            "☕ <b>Asistente Caficultor — Guía de Uso</b> 🌱\n\n"
            "Este bot te ayuda a registrar los ingresos y costos "
            "de tu finca cafetera, y genera un Excel profesional "
            "de costos de producción.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>📋 Comandos disponibles:</b>\n\n"
            "<code>/start</code> — Inicio y verificación de acceso\n"
            "<code>/menu</code> — Mostrar el menú principal 🏠\n"
            "<code>/fincas</code> — Gestionar tus fincas 🗺️\n"
            "<code>/lotes</code> — Administrar lotes de cada finca 🌱\n"
            "<code>/ingreso</code> — Registrar venta de café ☕💰\n"
            "<code>/costo</code> — Registrar costo de producción 📉\n"
            "<code>/resumen</code> — Ver resumen de tu finca 📊\n"
            "<code>/excel</code> — Generar y descargar Excel 📋\n"
            "<code>/ayuda</code> — Mostrar esta guía ❓\n"
            "<code>/cancelar</code> — Cancelar operación actual\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>📌 ¿Cómo empezar?</b>\n\n"
            "1. Usa /start para solicitar acceso\n"
            "2. Espera a que el administrador apruebe tu solicitud ✅\n"
            "3. Crea tu finca con /fincas 🏠\n"
            "4. Registra los lotes con /lotes 📍\n"
            "5. Empieza a registrar ingresos y costos\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>💰 Registrar Ingresos:</b>\n\n"
            "Usa /ingreso y sigue los pasos:\n"
            "• Selecciona la finca\n"
            "• Ingresa la fecha de venta\n"
            "• Selecciona el tipo de café (CPS, Pasilla, Re-re)\n"
            "• Indica los kilos vendidos\n"
            "• Indica el valor total recibido\n"
            "• Confirma los datos\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>📉 Registrar Costos:</b>\n\n"
            "Usa /costo y selecciona la categoría:\n\n"
            "🌱 <b>Instalación</b> — Costos de siembra y establecimiento\n"
            "🌿 <b>Arvenses</b> — Control de malezas\n"
            "🧪 <b>Fertilización</b> — Abonos y fertilizantes\n"
            "🛡️ <b>Fitosanitario</b> — Control de plagas y enfermedades\n"
            "🌳 <b>Sombrío</b> — Regulación de sombra\n"
            "🔧 <b>Otras Labores</b> — Otras actividades\n"
            "☕ <b>Recolección</b> — Cosecha de café\n"
            "🏭 <b>Beneficio</b> — Procesamiento del café\n"
            "📋 <b>Gastos Admin</b> — Gastos administrativos\n\n"
            "Para cada costo puedes agregar:\n"
            "• Mano de obra (jornales)\n"
            "• Insumos (productos, fertilizantes, etc.)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>📊 Reportes y Excel:</b>\n\n"
            "• <code>/resumen</code> — Ver resumen de ingresos, egresos y\n"
            "  margen por categoría\n"
            "• <code>/excel</code> — Generar el Excel profesional de costos\n"
            "  de producción con 18 hojas, fórmulas y gráficos\n\n"
            "El Excel incluye:\n"
            "• Resultados económicos automáticos\n"
            "• Gráficos de participación por rubro\n"
            "• Todas las fórmulas pre-cargadas\n"
            "• Datos de lotes, ingresos y costos detallados\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🌐 Tipos de Café:</b>\n\n"
            "• <b>CPS</b> — Café Pergamino Seco\n"
            "• <b>Pasilla</b> — Café de segunda calidad\n"
            "• <b>Re-re</b> — Re-recolección\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>❓ ¿Necesitas ayuda?</b>\n\n"
            "Contacta al administrador si tienes dudas\n"
            "o problemas con el bot.\n\n"
            "☕ <b>¡Buena cosecha!</b> 🌱"
        )

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Volver al menú", callback_data="volver_menu")],
            ]
        )

        partes = _split_texto(texto)
        for i, parte in enumerate(partes):
            if i == len(partes) - 1:
                await send(parte, parse_mode="HTML", reply_markup=keyboard)
            else:
                await send(parte, parse_mode="HTML")

    return router
