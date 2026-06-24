"""
Handler de /resumen - Reportes y exportación de Excel.
"""
import os
import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command

from database import Database
from config import CATEGORIAS, EXPORTS_DIR, EXCEL_TEMPLATE, ADMIN_IDS

logger = logging.getLogger(__name__)


def _split_texto(texto: str, max_len: int = 4096) -> list:
    """Divide un texto largo en partes."""
    if len(texto) <= max_len:
        return [texto]

    partes = []
    while len(texto) > max_len:
        # Buscar el último salto de línea antes del límite
        corte = texto.rfind("\n", 0, max_len)
        if corte == -1:
            corte = max_len
        partes.append(texto[:corte])
        texto = texto[corte:].strip()
    if texto:
        partes.append(texto)
    return partes


async def mostrar_resumen(db: Database, send_func, finca_id: int, finca_nombre: str):
    """Muestra el resumen detallado de una finca."""
    resumen = db.get_resumen_finca(finca_id)
    if not resumen:
        await send_func("❌ <b>Error al obtener el resumen.</b>", parse_mode="HTML")
        return

    total_ingresos = resumen.get("ingresos", 0)
    total_egresos = resumen.get("egresos", 0)
    margen = resumen.get("margen", 0)
    area = resumen.get("area_total", 0)
    costo_ha = resumen.get("costo_por_hectarea", 0)

    texto = (
        f"📊 <b>Resumen — {finca_nombre}</b>\n\n"
        f"📐 <b>Área total:</b> {area:.2f} ha\n\n"
        f"💰 <b>Ingresos Totales:</b> ${total_ingresos:,.0f}\n"
        f"📉 <b>Egresos Totales:</b> ${total_egresos:,.0f}\n"
    )

    if margen >= 0:
        texto += f"✅ <b>Margen:</b> ${margen:,.0f}\n"
    else:
        texto += f"❌ <b>Margen:</b> -${abs(margen):,.0f} (pérdida)\n"

    texto += f"📊 <b>Costo por hectárea:</b> ${costo_ha:,.0f}\n\n"

    # Egresos por categoría
    if resumen["egresos_por_categoria"]:
        texto += "<b>Egresos por categoría:</b>\n"
        for cat, total in sorted(resumen["egresos_por_categoria"].items(), key=lambda x: x[1], reverse=True):
            nombre_cat = CATEGORIAS.get(cat, {}).get("nombre", cat)
            porcentaje = (total / total_egresos * 100) if total_egresos > 0 else 0
            texto += f"  • {nombre_cat}: ${total:,.0f} ({porcentaje:.1f}%)\n"

    # Ingresos por tipo
    if resumen["ingresos_por_tipo"]:
        texto += "\n<b>Ingresos por tipo:</b>\n"
        for cat, total in resumen["ingresos_por_tipo"].items():
            nombre_cat = CATEGORIAS.get(cat, {}).get("nombre", cat)
            texto += f"  • {nombre_cat}: ${total:,.0f}\n"

    texto += "\n<b>Acciones:</b>"

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text="📊 Generar Excel",
                callback_data=f"generar_excel:{finca_id}",
            )],
            [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
        ]
    )

    # Manejar textos largos
    partes = _split_texto(texto)
    for i, parte in enumerate(partes):
        if i == len(partes) - 1:
            await send_func(parte, parse_mode="HTML", reply_markup=keyboard)
        else:
            await send_func(parte, parse_mode="HTML")


def get_reportes_router(db: Database) -> Router:
    router = Router()

    @router.message(Command("resumen"))
    @router.callback_query(F.data == "menu_resumen")
    async def cmd_resumen(event: types.Message | types.CallbackQuery):
        """Muestra el resumen de la finca."""
        user_id = event.from_user.id

        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
        else:
            message = event
            send = message.answer

        if not db.is_approved(user_id):
            await send("⏳ <b>No tienes acceso.</b> Usa /start para solicitar aprobación.", parse_mode="HTML")
            return

        try:
            fincas = db.get_fincas(user_id)
            if not fincas:
                await send(
                    "❌ <b>No tienes fincas registradas.</b>\n\n"
                    "Primero crea una finca con /fincas 🗺️",
                    parse_mode="HTML",
                )
                return

            if len(fincas) == 1:
                await mostrar_resumen(db, send, fincas[0]["id"], fincas[0]["nombre"])
                return

            # Varias fincas
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(
                        text=f"🏠 {f['nombre']}",
                        callback_data=f"resumen_finca:{f['id']}",
                    )]
                    for f in fincas
                ]
                + [
                    [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
                ]
            )

            await send(
                "📊 <b>Resumen de Finca</b>\n\nSelecciona la finca:",
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        except Exception as e:
            logger.error(f"Error en /resumen: {e}", exc_info=True)
            await send("❌ <b>Error al generar resumen.</b>", parse_mode="HTML")

    @router.callback_query(F.data.startswith("resumen_finca:"))
    async def seleccionar_finca_resumen(callback: types.CallbackQuery):
        await callback.answer()
        user_id = callback.from_user.id
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ <b>Finca no encontrada.</b>", parse_mode="HTML")
            return
        if finca["user_id"] != user_id:
            await callback.message.edit_text("❌ <b>Esta finca no te pertenece.</b>", parse_mode="HTML")
            return

        await mostrar_resumen(db, callback.message.edit_text, finca_id, finca["nombre"])

    @router.callback_query(F.data == "menu_excel")
    @router.callback_query(F.data.startswith("generar_excel:"))
    async def cmd_generar_excel(callback: types.CallbackQuery):
        """Genera y envía el Excel."""
        await callback.answer()

        if callback.data == "menu_excel":
            # Preguntar qué finca
            user_id = callback.from_user.id
            fincas = db.get_fincas(user_id)
            if not fincas:
                await callback.message.edit_text(
                    "❌ <b>No tienes fincas registradas.</b>",
                    parse_mode="HTML",
                )
                return

            if len(fincas) == 1:
                finca_id = fincas[0]["id"]
            else:
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(
                            text=f"🏠 {f['nombre']}",
                            callback_data=f"generar_excel:{f['id']}",
                        )]
                        for f in fincas
                    ]
                    + [
                        [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
                    ]
                )
                await callback.message.edit_text(
                    "📊 <b>Generar Excel</b>\n\nSelecciona la finca:",
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
                return
        else:
            finca_id = int(callback.data.split(":")[1])

        try:
            await callback.message.edit_text(
                "⏳ <b>Generando Excel...</b> Esto puede tomar unos segundos.",
                parse_mode="HTML",
            )

            # Generar Excel
            from excel_manager import ExcelManager
            manager = ExcelManager(EXCEL_TEMPLATE)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"costos_finca_{finca_id}_{timestamp}.xlsx"
            output_path = os.path.join(EXPORTS_DIR, output_filename)

            manager.generar_excel(finca_id, db, output_path)

            # Enviar archivo
            with open(output_path, "rb") as f:
                await callback.message.answer_document(
                    types.FSInputFile(output_path, filename=f"Costos_Produccion_{finca_id}.xlsx"),
                    caption="📊 <b>Excel de Costos de Producción generado</b> ☕\n\n"
                            "Las fórmulas de Resultados y Gráficos se calcularán "
                            "al abrir el archivo en Excel o LibreOffice.",
                    parse_mode="HTML",
                )

            # Limpiar archivo temporal
            try:
                os.remove(output_path)
            except Exception:
                pass

        except FileNotFoundError as e:
            logger.error(f"Template no encontrado: {e}")
            await callback.message.edit_text(
                "❌ <b>Error:</b> El template Excel no está disponible.\n\n"
                "Contacta al administrador.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Error al generar Excel: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ <b>Error al generar el Excel.</b> Intenta de nuevo más tarde.",
                parse_mode="HTML",
            )

    return router
