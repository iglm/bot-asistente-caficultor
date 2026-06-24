"""
Handler de /indicadores — Indicadores Técnicos de Rendimiento.
Calcula productividad, jornales/ha, costo/kg, margen/ha, etc.
Todos los indicadores se calculan exclusivamente con datos de la finca.
"""
import logging
import os
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import Database
from config import EXPORTS_DIR
from utils import boton_menu, agregar_boton_menu

logger = logging.getLogger(__name__)


def _formatear_moneda(valor: float) -> str:
    """Formatea un número como moneda: $X,XXX,XXX"""
    return f"${valor:,.0f}"


def _formatear_numero(valor: float, decimales: int = 2) -> str:
    """Formatea un número con separadores de miles."""
    if decimales == 0:
        return f"{valor:,.0f}"
    return f"{valor:,.{decimales}f}"


def _indicador_o_cero(valor: float, etiqueta: str = "") -> str:
    """Retorna el valor formateado o '—' si es cero."""
    if etiqueta == "moneda":
        return _formatear_moneda(valor) if valor > 0 else "$0"
    elif etiqueta == "kg":
        return f"{_formatear_numero(valor, 2)} kg" if valor > 0 else "0 kg"
    else:
        return _formatear_numero(valor, 2) if valor > 0 else "—"


async def mostrar_indicadores(db: Database, send_func, finca_id: int, finca_nombre: str, filtro: str = "general"):
    """Muestra los indicadores técnicos según el filtro seleccionado."""
    indicadores = db.get_indicadores_tecnicos(finca_id)

    if not indicadores or indicadores.get('area_total', 0) == 0:
        await send_func(
            "⚠️ <b>No hay datos suficientes para calcular indicadores.</b>\n\n"
            "Registrá lotes con /lotes y transacciones con /ingresos y /costo "
            "para generar indicadores.",
            parse_mode="HTML",
            reply_markup=boton_menu(),
        )
        return

    # Construir texto según filtro
    texto = f"📊 <b>Indicadores Técnicos — {finca_nombre}</b>\n\n"

    if filtro in ("general", "area"):
        texto += "🌱 <b>Área</b>\n"
        texto += f"• Total: {_formatear_numero(indicadores['area_total'], 2)} ha\n"
        texto += f"• Productiva: {_formatear_numero(indicadores['area_productiva'], 2)} ha\n\n"

    if filtro in ("general", "mo"):
        texto += "👷 <b>Mano de Obra</b>\n"
        texto += f"• Total jornales: {_formatear_numero(indicadores['total_jornales'], 0)}\n"
        texto += f"• Jornales/ha: {_formatear_numero(indicadores['jornales_por_ha'], 2)}\n"
        texto += f"• Costo MO/ha: {_formatear_moneda(indicadores['costo_mo_por_ha'])}\n"
        texto += f"• Eficiencia: {_formatear_numero(indicadores['eficiencia_mo'], 2)} kg/jornal\n\n"

    if filtro in ("general", "insumos"):
        texto += "🧪 <b>Insumos</b>\n"
        texto += f"• Costo insumos/ha: {_formatear_moneda(indicadores['costo_insumos_por_ha'])}\n"
        texto += f"• Costo insumos/kg CPS: {_formatear_moneda(indicadores['costo_insumos_por_kg_cps'])}/kg\n"
        texto += f"• Insumos total (kg eq.): {_formatear_numero(indicadores['insumos_total_kg'], 2)} kg\n"
        if indicadores['insumos_total_litros'] > 0:
            texto += f"• Insumos total (L eq.): {_formatear_numero(indicadores['insumos_total_litros'], 2)} L\n"
        texto += f"• Insumos por hectárea: {_formatear_numero(indicadores['insumos_por_ha'], 2)} kg/ha\n"
        texto += f"• Kg CPS producidos: {_formatear_numero(indicadores['kg_producidos'], 2)} kg\n"
        efic_ins = indicadores['eficiencia_insumos']
        if efic_ins > 0:
            texto += f"• Eficiencia insumos: {_formatear_numero(efic_ins, 2)} kg CPS/kg insumo\n"
        texto += "\n"

    if filtro in ("general", "financiero"):
        texto += "💰 <b>Financiero</b>\n"
        texto += f"• Ingresos totales: {_formatear_moneda(indicadores['ingresos_totales'])}\n"
        texto += f"• Costos MO: {_formatear_moneda(indicadores['costos_mo'])}\n"
        texto += f"• Costos Insumos: {_formatear_moneda(indicadores['costos_insumos'])}\n"
        texto += f"• Costos totales: {_formatear_moneda(indicadores['costos_total'])}\n"
        texto += f"• Costo total/ha: {_formatear_moneda(indicadores['costo_total_por_ha'])}\n"
        texto += f"• Costo/kg CPS: {_formatear_moneda(indicadores['costo_por_kilo'])}\n"
        texto += f"• Precio venta promedio: {_formatear_moneda(indicadores['precio_venta_promedio'])}/kg\n"
        margen = indicadores['margen_por_ha']
        if margen >= 0:
            texto += f"✅ Margen/ha: {_formatear_moneda(margen)}\n"
        else:
            texto += f"❌ Margen/ha: -{_formatear_moneda(abs(margen))} (pérdida)\n\n"

    if filtro in ("general",):
        texto += "📈 <b>Productividad</b>\n"
        texto += f"• Productividad: {_formatear_numero(indicadores['productividad'], 2)} kg/ha\n"
        texto += f"• Rendimiento: {_formatear_numero(indicadores['rendimiento'], 2)} kg/ha productivo\n\n"

    # ─── Alertas automáticas (MEJORA 3) ───
    texto += _generar_alertas(indicadores, db, finca_id)

    # Teclado de navegación
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📈 General", callback_data=f"indicador:general:{finca_id}"),
                types.InlineKeyboardButton(text="👷 MO", callback_data=f"indicador:mo:{finca_id}"),
            ],
            [
                types.InlineKeyboardButton(text="🧪 Insumos", callback_data=f"indicador:insumos:{finca_id}"),
                types.InlineKeyboardButton(text="💰 Financiero", callback_data=f"indicador:financiero:{finca_id}"),
            ],
            [
                types.InlineKeyboardButton(text="📥 Exportar Excel", callback_data=f"indicador_excel:{finca_id}"),
            ],
            [
                types.InlineKeyboardButton(text="📄 Exportar PDF", callback_data=f"indicador_pdf:{finca_id}"),
            ],
            [
                types.InlineKeyboardButton(text="🏠 Menú Principal", callback_data="volver_menu"),
            ],
        ]
    )

    await send_func(texto, parse_mode="HTML", reply_markup=keyboard)


def _generar_alertas(indicadores: dict, db, finca_id: int) -> str:
    """Genera alertas automáticas basadas en los indicadores (MEJORA 3)."""
    alertas = []
    if indicadores.get('area_total', 0) == 0:
        return ""

    prod = indicadores.get('productividad', 0)
    if 0 < prod < 800:
        alertas.append(f"⚠️ Productividad baja: {prod:.1f} kg/ha (mínimo esperado: 800 kg/ha)")

    if indicadores.get('margen_por_ha', 0) < 0:
        alertas.append(f"🔴 ¡MARGEN NEGATIVO! Estás perdiendo ${abs(indicadores['margen_por_ha']):,.0f}/ha")

    costo_kg = indicadores.get('costo_por_kilo', 0)
    precio = indicadores.get('precio_venta_promedio', 0)
    if costo_kg > precio and precio > 0:
        alertas.append(f"🔴 Costo/kg (${costo_kg:,.0f}) supera precio venta (${precio:,.0f}/kg)")

    if indicadores.get('jornales_por_ha', 0) > 80:
        alertas.append(f"⚠️ Alta intensidad MO: {indicadores['jornales_por_ha']:.1f} jornales/ha")

    if not alertas:
        return ""

    texto = "\n🚨 <b>Alertas:</b>\n"
    for al in alertas:
        texto += f"{al}\n"
    texto += "\n"
    return texto


def get_indicadores_router(db: Database) -> Router:
    router = Router()

    @router.message(Command("indicadores"))
    @router.callback_query(F.data == "menu_indicadores")
    async def cmd_indicadores(event: types.Message | types.CallbackQuery, state: FSMContext):
        """Muestra el menú principal de indicadores técnicos."""
        await state.clear()
        user_id = event.from_user.id

        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
        else:
            message = event
            send = message.answer

        if not db.is_approved(user_id):
            await send(
                "⏳ <b>No tienes acceso.</b> Usa /start para solicitar aprobación.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        try:
            fincas = db.get_fincas(user_id)
            if not fincas:
                await send(
                    "❌ <b>No tienes fincas registradas.</b>\n\n"
                    "Primero crea una finca con /fincas 🗺️",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )
                return

            # Si tiene una sola finca, mostrar el menú de indicadores directamente
            if len(fincas) == 1:
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(text="📈 General", callback_data=f"indicador:general:{fincas[0]['id']}"),
                            types.InlineKeyboardButton(text="👷 MO", callback_data=f"indicador:mo:{fincas[0]['id']}"),
                        ],
                        [
                            types.InlineKeyboardButton(text="🧪 Insumos", callback_data=f"indicador:insumos:{fincas[0]['id']}"),
                            types.InlineKeyboardButton(text="💰 Financiero", callback_data=f"indicador:financiero:{fincas[0]['id']}"),
                        ],
                        [
                            types.InlineKeyboardButton(text="📥 Exportar Excel", callback_data=f"indicador_excel:{fincas[0]['id']}"),
                        ],
                        [
                            types.InlineKeyboardButton(text="🏠 Menú Principal", callback_data="volver_menu"),
                        ],
                    ]
                )
                await send(
                    f"📊 <b>Indicadores Técnicos de Rendimiento</b>\n\n"
                    f"🏠 Finca: {fincas[0]['nombre']}\n\n"
                    f"¿Qué querés ver?",
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
                return

            # Varias fincas — mostrar selector
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(
                        text=f"🏠 {f['nombre']}",
                        callback_data=f"indic_finca:{f['id']}",
                    )]
                    for f in fincas
                ] + [
                    [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
                ]
            )

            await send(
                "📊 <b>Indicadores Técnicos</b>\n\nSelecciona la finca:",
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        except Exception as e:
            logger.error(f"Error en /indicadores: {e}", exc_info=True)
            await send(
                "❌ <b>Error al cargar indicadores.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

    @router.callback_query(F.data.startswith("indic_finca:"))
    async def seleccionar_finca_indicador(callback: types.CallbackQuery):
        """Selecciona una finca para ver sus indicadores."""
        await callback.answer()
        user_id = callback.from_user.id
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text(
                "❌ <b>Finca no encontrada.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return
        if finca["user_id"] != user_id:
            await callback.message.edit_text(
                "❌ <b>Esta finca no te pertenece.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="📈 General", callback_data=f"indicador:general:{finca_id}"),
                    types.InlineKeyboardButton(text="👷 MO", callback_data=f"indicador:mo:{finca_id}"),
                ],
                [
                    types.InlineKeyboardButton(text="🧪 Insumos", callback_data=f"indicador:insumos:{finca_id}"),
                    types.InlineKeyboardButton(text="💰 Financiero", callback_data=f"indicador:financiero:{finca_id}"),
                ],
                [
                    types.InlineKeyboardButton(text="📥 Exportar Excel", callback_data=f"indicador_excel:{finca_id}"),
                ],
                [
                    types.InlineKeyboardButton(text="🏠 Menú Principal", callback_data="volver_menu"),
                ],
            ]
        )
        await callback.message.edit_text(
            f"📊 <b>Indicadores Técnicos de Rendimiento</b>\n\n"
            f"🏠 Finca: {finca['nombre']}\n\n"
            f"¿Qué querés ver?",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    @router.callback_query(F.data.startswith("indicador:"))
    async def mostrar_filtro_indicador(callback: types.CallbackQuery):
        """Muestra los indicadores según el filtro seleccionado."""
        await callback.answer()
        user_id = callback.from_user.id
        parts = callback.data.split(":", 2)
        filtro = parts[1]
        finca_id = int(parts[2])
        finca = db.get_finca_by_id(finca_id)
        if not finca or finca["user_id"] != user_id:
            await callback.message.edit_text(
                "❌ <b>Finca no encontrada o no te pertenece.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        await mostrar_indicadores(db, callback.message.edit_text, finca_id, finca["nombre"], filtro)

    @router.callback_query(F.data.startswith("indicador_excel:"))
    async def exportar_indicadores_excel(callback: types.CallbackQuery):
        """Exporta los indicadores a un archivo Excel."""
        await callback.answer()
        user_id = callback.from_user.id
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca or finca["user_id"] != user_id:
            await callback.message.edit_text(
                "❌ <b>Finca no encontrada o no te pertenece.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        # Usar la exportación a Excel normal que ya existe (incluye indicadores)
        # Redirigir al flujo de generación de Excel
        await callback.message.edit_text(
            "📥 <b>Exportar Indicadores</b>\n\n"
            "Los indicadores se incluyen en el Excel de costos de producción.\n"
            "Usá /resumen para generar el Excel completo con la hoja de Indicadores.",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(
                        text="📊 Generar Excel",
                        callback_data=f"generar_excel:{finca_id}",
                    )],
                    [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
                ]
            ),
        )

    @router.callback_query(F.data.startswith("indicador_pdf:"))
    async def exportar_indicadores_pdf(callback: types.CallbackQuery):
        """Exporta los indicadores a un archivo PDF."""
        await callback.answer()
        user_id = callback.from_user.id
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca or finca["user_id"] != user_id:
            await callback.message.edit_text(
                "❌ <b>Finca no encontrada o no te pertenece.</b>",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
            return

        try:
            await callback.message.edit_text(
                "⏳ <b>Generando PDF del resumen ejecutivo...</b>",
                parse_mode="HTML",
            )

            indicadores = db.get_indicadores_tecnicos(finca_id)
            if not indicadores or indicadores.get('area_total', 0) == 0:
                await callback.message.edit_text(
                    "⚠️ <b>No hay datos suficientes para generar el PDF.</b>",
                    parse_mode="HTML",
                    reply_markup=boton_menu(),
                )
                return

            # Generar PDF con FPDF2
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(31, 78, 121)
            pdf.cell(0, 10, f"Resumen Ejecutivo - {finca['nombre']}", ln=True, align="C")
            pdf.ln(10)

            # KPIs
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, "INDICADORES CLAVE", ln=True)
            pdf.set_font("Helvetica", "", 10)

            kpis = [
                ("Productividad", f"{indicadores.get('productividad', 0):,.1f} kg/ha"),
                ("Rendimiento", f"{indicadores.get('rendimiento', 0):,.1f} kg/ha productivo"),
                ("Costo por Hectarea", f"${indicadores.get('costo_total_por_ha', 0):,.0f}"),
                ("Margen por Hectarea", f"${indicadores.get('margen_por_ha', 0):,.0f}"),
                ("Costo por kg CPS", f"${indicadores.get('costo_por_kilo', 0):,.0f}"),
                ("Precio Venta Promedio", f"${indicadores.get('precio_venta_promedio', 0):,.0f}"),
                ("Jornales/ha", f"{indicadores.get('jornales_por_ha', 0):,.1f}"),
            ]
            for label, valor in kpis:
                pdf.cell(0, 7, f"  {label}: {valor}", ln=True)

            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "INGRESOS vs COSTOS", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 7, f"  Ingresos Totales: ${indicadores.get('ingresos_totales', 0):,.0f}", ln=True)
            pdf.cell(0, 7, f"  Costos Totales: ${indicadores.get('costos_total', 0):,.0f}", ln=True)
            pdf.cell(0, 7, f"  Margen Neto: ${indicadores.get('ingresos_totales', 0) - indicadores.get('costos_total', 0):,.0f}", ln=True)

            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "AREA", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 7, f"  Total: {indicadores.get('area_total', 0):,.1f} ha", ln=True)
            pdf.cell(0, 7, f"  Productiva: {indicadores.get('area_productiva', 0):,.1f} ha", ln=True)
            pdf.cell(0, 7, f"  Lotes: {len(db.get_lotes(finca_id))}", ln=True)

            from config import EXPORTS_DIR
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"resumen_ejecutivo_{finca_id}_{timestamp}.pdf"
            output_path = os.path.join(EXPORTS_DIR, output_filename)
            pdf.output(output_path)

            with open(output_path, "rb") as f:
                await callback.message.answer_document(
                    types.FSInputFile(output_path, filename=f"Resumen_Ejecutivo_{finca['nombre']}.pdf"),
                    caption=f"📄 <b>Resumen Ejecutivo generado</b> ☕\n\n"
                            f"PDF con los indicadores clave de {finca['nombre']}.",
                    parse_mode="HTML",
                )

            try:
                os.remove(output_path)
            except Exception:
                pass

        except ImportError:
            await callback.message.edit_text(
                "⚠️ <b>FPDF2 no está instalado.</b>\n\n"
                "Instalalo con: pip install fpdf2\n"
                "Mientras tanto, usá la exportación a Excel.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )
        except Exception as e:
            logger.error(f"Error al generar PDF: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ <b>Error al generar el PDF.</b> Intenta de nuevo más tarde.",
                parse_mode="HTML",
                reply_markup=boton_menu(),
            )

    return router
