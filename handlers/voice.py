"""
handlers/voice.py — Procesamiento de mensajes de voz con Whisper local.
=========================================================================
Flujo:
    Usuario envía voz → Bot descarga .ogg → Whisper transcribe →
    Parser extrae datos → Muestra resumen → Usuario confirma → Guarda en DB

NO usa DeepSeek. Whisper local es gratis.
Siempre parse_mode='HTML'. Botones inline siempre.
"""
import logging
import os
import tempfile
from datetime import datetime

from aiogram import Bot, Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from voice_handler import transcribe_audio, parse_voice_text

logger = logging.getLogger(__name__)


class VoiceForm(StatesGroup):
    """Estados FSM para el flujo de confirmación de voz."""
    esperando_confirmacion = State()
    esperando_finca = State()


def format_parsed_data_html(data: dict) -> tuple:
    """Formatea los datos parseados a HTML.
    Retorna (texto_html, keyboard) para usar con parse_mode='HTML'.
    """
    lines = [
        "🎤 <b>Mensaje de voz recibido</b>",
        "",
    ]
    texto_original = data.get("texto_original", "")
    if len(texto_original) > 100:
        lines.append(f"📝 <i>\"{texto_original[:100]}...\"</i>")
    else:
        lines.append(f"📝 <i>\"{texto_original}\"</i>")
    lines.append("")
    lines.append("📊 <b>Datos extraídos:</b>")

    if data.get("fecha"):
        lines.append(f"📅 Fecha: <b>{data['fecha']}</b>")
    if data.get("categoria"):
        cat_nombre = data["categoria"].replace("_", " ").title()
        lines.append(f"🏷️ Categoría: <b>{cat_nombre}</b>")
    if data.get("labor"):
        lines.append(f"🔨 Labor: <b>{data['labor']}</b>")
    if data.get("cantidad"):
        unidad = data.get("unidad", "")
        lines.append(f"🔢 Cantidad: <b>{data['cantidad']}</b> {unidad}")
    if data.get("valor_unitario"):
        lines.append(f"💵 Valor unitario: <b>${data['valor_unitario']:,.0f}</b>")
    if data.get("valor_total"):
        lines.append(f"💰 Valor total: <b>${data['valor_total']:,.0f}</b>")
    if data.get("lote"):
        lines.append(f"🌱 <b>{data['lote']}</b>")

    lines.extend(["", "¿Estos datos están correctos?"])

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Confirmar", callback_data="voice_confirm:si"),
                types.InlineKeyboardButton(text="❌ Cancelar", callback_data="voice_confirm:no"),
                types.InlineKeyboardButton(text="✏️ Corregir", callback_data="voice_confirm:corregir"),
            ],
        ]
    )

    return "\n".join(lines), keyboard


async def guardar_transaccion_voz(
    db: Database, message: types.Message, parsed: dict, finca_id: int
):
    """Guarda la transacción parseada por voz en la base de datos."""
    categoria = parsed.get("categoria", "")
    if not categoria:
        categoria = "otras_labores_mo"

    try:
        db.insert_transaccion(
            finca_id=finca_id,
            lote_id=0,
            categoria=categoria,
            fecha=parsed.get("fecha", datetime.now().strftime("%Y-%m-%d")),
            labor=parsed.get("labor", parsed.get("texto_original", "")[:100]),
            producto=parsed.get("producto", ""),
            cantidad=float(parsed.get("cantidad") or 0),
            unidad=parsed.get("unidad", "jornal"),
            valor_unitario=float(parsed.get("valor_unitario") or 0),
            valor_total=float(parsed.get("valor_total") or 0),
        )
        await message.edit_text(
            "✅ <b>¡Transacción guardada exitosamente!</b> 🎉\n\n"
            "Usa /resumen para ver tus datos o envía otro mensaje de voz.",
            parse_mode="HTML",
        )
        logger.info(f"Voz → transacción guardada: {categoria} en finca {finca_id}")
    except Exception as e:
        logger.error(f"Error guardando transacción por voz: {e}", exc_info=True)
        await message.edit_text(
            "❌ <b>Error al guardar la transacción.</b> Intenta de nuevo.",
            parse_mode="HTML",
        )


def get_voice_router(db: Database) -> Router:
    """Crea y retorna el router de voz."""
    router = Router()

    # ────────────────────────────────────────────────────────────
    # MENSAJE DE VOZ → transcribir + parsear + mostrar resumen
    # ────────────────────────────────────────────────────────────
    @router.message(F.voice)
    async def handle_voice(message: types.Message, bot: Bot, state: FSMContext):
        user_id = message.from_user.id

        if not db.is_approved(user_id):
            await message.answer(
                "⏳ <b>No tienes acceso.</b> Usa /start para solicitar aprobación.",
                parse_mode="HTML",
            )
            return

        # Mensaje de "procesando…"
        status_msg = await message.answer(
            "🎤 <b>Procesando mensaje de voz...</b>\n"
            "<i>Transcribiendo con Whisper local...</i>",
            parse_mode="HTML",
        )

        temp_path = None
        try:
            # 1. Descargar audio a archivo temporal
            file_info = await bot.get_file(message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                temp_path = tmp.name
                await bot.download(file_info, destination=tmp)

            # 2. Transcribir con Whisper local
            texto = transcribe_audio(temp_path)
            if not texto:
                await status_msg.edit_text(
                    "❌ <b>No se pudo transcribir el audio.</b>\n\n"
                    "Intenta enviar un mensaje de voz más claro o escribe el dato manualmente.",
                    parse_mode="HTML",
                )
                return

            logger.info(f"Voz transcrita ({len(texto)} chars): {texto[:80]}...")

            # 3. Parsear con el parser NL de voice_handler.py
            parsed = parse_voice_text(texto)

            # 4. Guardar en FSM para confirmación posterior
            await state.update_data(parsed_data=parsed, voice_text=texto)

            # 5. Mostrar resumen con botones
            texto_resumen, keyboard = format_parsed_data_html(parsed)
            await status_msg.edit_text(
                texto_resumen, parse_mode="HTML", reply_markup=keyboard
            )
            await state.set_state(VoiceForm.esperando_confirmacion)

        except Exception as e:
            logger.error(f"Error procesando voz: {e}", exc_info=True)
            await status_msg.edit_text(
                "❌ <b>Error al procesar el mensaje de voz.</b>\n\n"
                "Intenta de nuevo o escribe los datos manualmente.",
                parse_mode="HTML",
            )
        finally:
            # Limpiar archivo temporal
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"No se pudo borrar temp {temp_path}: {e}")

    # ────────────────────────────────────────────────────────────
    # CONFIRMAR → guardar en DB
    # ────────────────────────────────────────────────────────────
    @router.callback_query(VoiceForm.esperando_confirmacion, F.data == "voice_confirm:si")
    async def confirmar_voz(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        data = await state.get_data()
        parsed = data.get("parsed_data", {})

        if not parsed:
            await callback.message.edit_text(
                "❌ <b>Error: datos no encontrados.</b> Envía el mensaje de voz de nuevo.",
                parse_mode="HTML",
            )
            await state.clear()
            return

        user_id = callback.from_user.id

        # Obtener fincas del usuario
        fincas = db.get_fincas(user_id)
        if not fincas:
            await callback.message.edit_text(
                "❌ <b>No tienes fincas registradas.</b>\n\n"
                "Primero crea una finca con /fincas 🗺️",
                parse_mode="HTML",
            )
            await state.clear()
            return

        if len(fincas) == 1:
            # Una sola finca → guardar directamente
            await guardar_transaccion_voz(db, callback.message, parsed, fincas[0]["id"])
            await state.clear()
        else:
            # Varias fincas → preguntar cuál
            await state.update_data(parsed_data=parsed)
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text=f"🏠 {f['nombre']}",
                            callback_data=f"voice_finca:{f['id']}",
                        )
                    ]
                    for f in fincas
                ]
                + [
                    [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="voice_cancel")],
                ]
            )
            await callback.message.edit_text(
                "🏠 <b>Selecciona la finca para guardar:</b>",
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            await state.set_state(VoiceForm.esperando_finca)

    # ────────────────────────────────────────────────────────────
    # SELECCIONAR FINCA (cuando hay varias)
    # ────────────────────────────────────────────────────────────
    @router.callback_query(VoiceForm.esperando_finca, F.data.startswith("voice_finca:"))
    async def seleccionar_finca_voz(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        finca_id = int(callback.data.split(":")[1])
        data = await state.get_data()
        parsed = data.get("parsed_data", {})

        await guardar_transaccion_voz(db, callback.message, parsed, finca_id)
        await state.clear()

    # ────────────────────────────────────────────────────────────
    # CANCELAR desde voice_confirm
    # ────────────────────────────────────────────────────────────
    @router.callback_query(F.data == "voice_confirm:no")
    async def cancelar_voz(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.edit_text(
            "❌ <b>Registro cancelado.</b>",
            parse_mode="HTML",
        )
        await state.clear()

    # ────────────────────────────────────────────────────────────
    # CORREGIR
    # ────────────────────────────────────────────────────────────
    @router.callback_query(F.data == "voice_confirm:corregir")
    async def corregir_voz(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.edit_text(
            "✏️ <b>Corrige los datos manualmente.</b>\n\n"
            "Envía un mensaje de texto con la información corregida o "
            "un nuevo mensaje de voz.",
            parse_mode="HTML",
        )
        await state.clear()

    # ────────────────────────────────────────────────────────────
    # CANCELAR desde selector de finca
    # ────────────────────────────────────────────────────────────
    @router.callback_query(F.data == "voice_cancel")
    async def cancelar_operacion(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.edit_text(
            "❌ <b>Operación cancelada.</b>",
            parse_mode="HTML",
        )
        await state.clear()

    return router
