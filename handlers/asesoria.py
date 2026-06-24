"""
Handler de Asesoría — Interpretación de datos, sugerencias, plan de acción y contacto.
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import Database
from config import ASESORIA_EMAIL, ASESOR_NOMBRE, ASESOR_ASESOR
from utils import boton_menu

logger = logging.getLogger(__name__)


def get_asesoria_router(db: Database) -> Router:
    """Router para el servicio de asesoría profesional."""
    router = Router()

    @router.message(Command("asesoria"))
    async def cmd_asesoria(message: types.Message, state: FSMContext):
        """Menú principal de asesoría."""
        await state.clear()

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📊 Interpretar mis datos", callback_data="as_interpretar")],
            [types.InlineKeyboardButton(text="💡 Sugerencias de mejora", callback_data="as_sugerencias")],
            [types.InlineKeyboardButton(text="🎯 Plan de acción", callback_data="as_plan")],
            [types.InlineKeyboardButton(text="📞 Solicitar asesoría personalizada", callback_data="as_personalizada")],
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
        ])

        await message.answer(
            "👨‍🏫 <b>Servicio de Asesoría</b>\n\n"
            "Acá podés obtener análisis profesional de los datos de tu finca "
            "y sugerencias para mejorar tu producción.\n\n"
            "¿Qué necesitás?",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @router.callback_query(F.data == "as_interpretar")
    async def as_interpretar(callback: types.CallbackQuery, state: FSMContext):
        """Interpreta los datos del usuario y genera recomendaciones."""
        await callback.answer()
        await state.clear()
        user_id = callback.from_user.id

        # Obtener indicadores del usuario
        fincas = db.get_fincas(user_id)
        if not fincas:
            await callback.message.edit_text(
                "❌ No tenés fincas registradas. Primero creá una finca.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        finca_id = fincas[0]["id"]
        indicadores = db.get_indicadores_tecnicos(finca_id)

        if not indicadores or indicadores.get('kg_producidos', 0) == 0:
            await callback.message.edit_text(
                "📊 Aún no tenés suficientes datos para generar un análisis.\n\n"
                "Necesitás al menos registrar algunos costos e ingresos.\n"
                "Empezá registrando tus labores y ventas.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        # Generar interpretación profesional
        analisis = _generar_interpretacion(indicadores)

        await callback.message.edit_text(
            analisis,
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="💡 Ver sugerencias", callback_data="as_sugerencias")],
                [types.InlineKeyboardButton(text="🎯 Generar plan de acción", callback_data="as_plan")],
                [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
            ]),
        )

    @router.callback_query(F.data == "as_sugerencias")
    async def as_sugerencias(callback: types.CallbackQuery, state: FSMContext):
        """Genera sugerencias de mejora personalizadas."""
        await callback.answer()
        await state.clear()

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🎯 Generar plan de acción", callback_data="as_plan")],
            [types.InlineKeyboardButton(text="📞 Solicitar asesoría personalizada", callback_data="as_personalizada")],
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
        ])

        await callback.message.edit_text(
            "💡 <b>SUGERENCIAS DE MEJORA</b>\n\n"
            "Basado en los datos de tu finca, las siguientes acciones "
            "pueden ayudarte a mejorar:\n\n"
            "1️⃣ <b>Recolección:</b> Optimizá la frecuencia de recolección. "
            "Priorizá los lotes con mayor productividad.\n\n"
            "2️⃣ <b>Fertilización:</b> Realizá análisis de suelo para ajustar "
            "dosis. No apliques más de lo necesario.\n\n"
            "3️⃣ <b>Control de arvenses:</b> Alterná entre control manual y "
            "químico para reducir costos.\n\n"
            "4️⃣ <b>Administración:</b> Revisá gastos mensuales y eliminá "
            "gastos innecesarios.\n\n"
            "5️⃣ <b>Renovación:</b> Priorizá lotes con productividad menor "
            "a 500 kg/ha.\n\n"
            "¿Querés que genere un plan de acción detallado?",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @router.callback_query(F.data == "as_plan")
    async def as_plan(callback: types.CallbackQuery, state: FSMContext):
        """Genera un plan de acción detallado."""
        await callback.answer()
        await state.clear()

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📞 Solicitar asesoría personalizada", callback_data="as_personalizada")],
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
        ])

        await callback.message.edit_text(
            "🎯 <b>PLAN DE ACCIÓN PARA TU FINCA</b>\n\n"
            "<b>CORTO PLAZO (1-3 meses):</b>\n"
            "• Registrar TODOS los gastos diarios\n"
            "• Controlar jornales por lote\n"
            "• Revisar precios de insumos con proveedores\n\n"
            "<b>MEDIO PLAZO (3-6 meses):</b>\n"
            "• Realizar análisis de suelo\n"
            "• Ajustar fertilización según resultados\n"
            "• Implementar control integrado de plagas\n\n"
            "<b>LARGO PLAZO (6-12 meses):</b>\n"
            "• Renovar lotes improductivos\n"
            "• Diversificar variedades\n"
            "• Optimizar proceso de beneficio\n\n"
            "📞 Para un plan personalizado adaptado a tu zona y condiciones, "
            "solicitá asesoría individualizada.",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @router.callback_query(F.data == "as_personalizada")
    async def as_personalizada(callback: types.CallbackQuery, state: FSMContext):
        """Solicitud de asesoría personalizada."""
        await callback.answer()
        await state.clear()

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
        ])

        await callback.message.edit_text(
            "📞 <b>ASESORÍA PERSONALIZADA</b>\n\n"
            "Para recibir asesoría profesional personalizada sobre tu finca, "
            "enviá un correo a:\n\n"
            f"📧 <b>{ASESORIA_EMAIL}</b>\n\n"
            "Incluí en el correo:\n"
            "• Nombre de tu finca\n"
            "• Ubicación (municipio/departamento)\n"
            "• Área total\n"
            "• Principal consulta o problema\n\n"
            "Un asesor especializado te contactará en las próximas 48 horas.\n\n"
            "<i>Servicio incluido sin costo adicional.</i>\n\n"
            f"👨‍🌾 <b>Desarrollador:</b> {ASESOR_NOMBRE}\n"
            f"👨‍🔬 <b>Asesor técnico:</b> {ASESOR_ASESOR}",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    return router


def _generar_interpretacion(ind: dict) -> str:
    """Genera interpretación profesional de los indicadores."""
    texto = "📊 <b>ANÁLISIS DE TU FINCA</b>\n\n"

    # Productividad
    prod = ind.get('productividad', 0)
    if prod > 1000:
        texto += f"✅ <b>Productividad:</b> {prod:.0f} kg/ha — Excelente nivel.\n"
    elif prod > 500:
        texto += f"⚠️ <b>Productividad:</b> {prod:.0f} kg/ha — Aceptable, pero hay margen de mejora.\n"
    else:
        texto += f"🔴 <b>Productividad:</b> {prod:.0f} kg/ha — Baja. Requiere atención.\n"

    # Costo por hectárea
    costo_ha = ind.get('costo_total_por_ha', 0)
    if costo_ha > 0:
        if costo_ha < 10000000:
            texto += f"✅ <b>Costo/ha:</b> ${costo_ha:,.0f} — Eficiente.\n"
        elif costo_ha < 18000000:
            texto += f"⚠️ <b>Costo/ha:</b> ${costo_ha:,.0f} — Dentro del promedio.\n"
        else:
            texto += f"🔴 <b>Costo/ha:</b> ${costo_ha:,.0f} — Alto. Revisá los gastos.\n"

    # Margen por hectárea
    margen = ind.get('margen_por_ha', 0)
    if margen > 0:
        texto += f"✅ <b>Margen/ha:</b> ${margen:,.0f} — Rentable.\n"
    else:
        texto += f"🔴 <b>Margen/ha:</b> ${margen:,.0f} — Estás perdiendo dinero.\n"

    # Eficiencia mano de obra
    eficiencia = ind.get('eficiencia_mo', 0)
    if eficiencia > 0.5:
        texto += f"✅ <b>Eficiencia MO:</b> {eficiencia:.2f} kg/jornal — Buena.\n"
    elif eficiencia > 0.3:
        texto += f"⚠️ <b>Eficiencia MO:</b> {eficiencia:.2f} kg/jornal — Aceptable.\n"
    else:
        texto += f"🔴 <b>Eficiencia MO:</b> {eficiencia:.2f} kg/jornal — Baja.\n"

    texto += "\n💡 <b>Recomendación general:</b>\n"

    if prod > 800 and costo_ha < 15000000:
        texto += "Tu finca está en buen camino. Mantené las prácticas actuales y "
        texto += "considerá invertir en renovación para sostener la productividad."
    elif prod < 500:
        texto += "Priorizá la fertilización y el control de arvenses. "
        texto += "Considerá renovar lotes con baja productividad."
    elif costo_ha > 18000000:
        texto += "Revisá los gastos en insumos y administrativos. "
        texto += "Buscá proveedores más competitivos o ajustá las dosis."
    else:
        texto += "Tu finca tiene potencial de mejora. "
        texto += "Enfocate en aumentar la productividad por hectárea."

    return texto
