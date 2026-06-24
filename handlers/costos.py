"""
Handler de /costo - Registro de costos de producción.
"""
import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from config import CATEGORIAS_PADRE, CATEGORIAS_SIMPLE

logger = logging.getLogger(__name__)

# Botón de cancelar reutilizable
CANCEL_KB = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Cancelar", callback_data="cancelar_operacion")],
    ]
)


class CostoForm(StatesGroup):
    esperando_finca = State()
    esperando_categoria = State()
    esperando_fecha = State()
    esperando_labor = State()
    esperando_cantidad = State()
    esperando_valor_unitario = State()
    esperando_valor_total = State()
    esperando_agregar_insumos = State()
    esperando_producto = State()
    esperando_cantidad_insumo = State()
    esperando_valor_unitario_insumo = State()
    esperando_valor_total_insumo = State()
    esperando_confirmar_mo = State()
    esperando_confirmar_insumo = State()
    esperando_mas_insumos = State()


def get_costos_router(db: Database) -> Router:
    router = Router()

    @router.message(Command("costo"))
    @router.callback_query(F.data == "menu_costos")
    async def cmd_costo(event: types.Message | types.CallbackQuery, state: FSMContext):
        """Inicia el registro de un costo."""
        user_id = event.from_user.id

        if isinstance(event, types.CallbackQuery):
            await event.answer()
            message = event.message
            send = message.answer
        else:
            message = event
            send = message.answer

        if not db.is_approved(user_id):
            await send("⏳ *No tienes acceso.* Usa /start para solicitar aprobación.", parse_mode="Markdown")
            return

        try:
            fincas = db.get_fincas(user_id)
            if not fincas:
                await send(
                    "❌ *No tienes fincas registradas.*\n\n"
                    "Primero crea una finca con /fincas 🗺️",
                    parse_mode="Markdown",
                )
                return

            if len(fincas) == 1:
                await state.update_data(finca_id=fincas[0]["id"], finca_nombre=fincas[0]["nombre"])
                await mostrar_categorias_costos(message)
                return

            # Varias fincas
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(
                        text=f"🏠 {f['nombre']}",
                        callback_data=f"costo_finca:{f['id']}",
                    )]
                    for f in fincas
                ]
                + [
                    [types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu")],
                ]
            )

            await send(
                "📉 *Registrar Costo*\n\nSelecciona la finca:",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            await state.set_state(CostoForm.esperando_finca)

        except Exception as e:
            logger.error(f"Error en /costo: {e}", exc_info=True)
            await send("❌ *Error al iniciar registro.*", parse_mode="Markdown")

    @router.callback_query(CostoForm.esperando_finca, F.data.startswith("costo_finca:"))
    async def seleccionar_finca_costo(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        finca_id = int(callback.data.split(":")[1])
        finca = db.get_finca_by_id(finca_id)
        if not finca:
            await callback.message.edit_text("❌ *Finca no encontrada.*", parse_mode="Markdown")
            await state.clear()
            return

        await state.update_data(finca_id=finca_id, finca_nombre=finca["nombre"])
        await mostrar_categorias_costos(callback.message)

    async def mostrar_categorias_costos(message: types.Message):
        """Muestra las categorías de costos disponibles."""
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="🌱 Instalación", callback_data="cat_costo:instalacion"),
                    types.InlineKeyboardButton(text="🌿 Arvenses", callback_data="cat_costo:arvenses"),
                ],
                [
                    types.InlineKeyboardButton(text="🧪 Fertilización", callback_data="cat_costo:fertilizacion"),
                    types.InlineKeyboardButton(text="🛡️ Fitosanitario", callback_data="cat_costo:fitosanitario"),
                ],
                [
                    types.InlineKeyboardButton(text="🌳 Sombrío", callback_data="cat_costo:sombrio"),
                    types.InlineKeyboardButton(text="🔧 Otras Labores", callback_data="cat_costo:otras_labores"),
                ],
                [
                    types.InlineKeyboardButton(text="☕ Recolección", callback_data="cat_costo:recoleccion"),
                    types.InlineKeyboardButton(text="🏭 Beneficio", callback_data="cat_costo:beneficio"),
                ],
                [
                    types.InlineKeyboardButton(text="📋 Gtos Admin", callback_data="cat_costo:administrativo"),
                ],
                [
                    types.InlineKeyboardButton(text="🔙 Volver", callback_data="volver_menu"),
                ],
            ]
        )

        # Intentar editar o responder
        try:
            await message.edit_text(
                "📉 *Registrar Costo de Producción*\n\n"
                "Selecciona la *categoría* del costo:",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        except Exception:
            await message.answer(
                "📉 *Registrar Costo de Producción*\n\n"
                "Selecciona la *categoría* del costo:",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

        await CostoForm.esperando_categoria.set()

    @router.callback_query(CostoForm.esperando_categoria, F.data.startswith("cat_costo:"))
    async def seleccionar_categoria(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        cat_key = callback.data.split(":", 1)[1]

        await state.update_data(cat_key=cat_key)

        data = await state.get_data()

        if cat_key in CATEGORIAS_PADRE:
            cat_info = CATEGORIAS_PADRE[cat_key]
            texto = (
                f"📉 *{cat_info['nombre']}*\n\n"
                f"🏠 *Finca:* {data.get('finca_nombre', '')}\n\n"
                "Paso 1: ¿Cuál es la *fecha* de la labor?\n\n"
                "*(Formato: DD/MM/AAAA)*"
            )
        elif cat_key in CATEGORIAS_SIMPLE:
            cat_info = CATEGORIAS_SIMPLE[cat_key]
            texto = (
                f"📉 *{cat_info['nombre']}*\n\n"
                f"🏠 *Finca:* {data.get('finca_nombre', '')}\n\n"
                "¿Cuál es la *fecha*?\n\n"
                "*(Formato: DD/MM/AAAA)*"
            )
        else:
            await callback.message.edit_text("❌ *Categoría no válida.*", parse_mode="Markdown")
            await state.clear()
            return

        await callback.message.edit_text(texto, parse_mode="Markdown", reply_markup=CANCEL_KB)
        await state.set_state(CostoForm.esperando_fecha)

    @router.message(CostoForm.esperando_fecha, F.text)
    async def recibir_fecha_costo(message: types.Message, state: FSMContext):
        fecha_str = message.text.strip()
        fecha_valida = None
        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                fecha_valida = datetime.strptime(fecha_str, fmt)
                break
            except ValueError:
                continue

        if not fecha_valida:
            await message.answer("❌ Fecha inválida. Usa formato DD/MM/AAAA:")
            return

        fecha_iso = fecha_valida.strftime("%Y-%m-%d")
        await state.update_data(fecha=fecha_iso)

        data = await state.get_data()
        cat_key = data.get("cat_key", "")

        if cat_key == "administrativo":
            await message.answer(
                f"✅ *Fecha:* {fecha_str}\n\n"
                "¿Cuál es el *gasto administrativo*?\n\n"
                "*(Describe el gasto, ej: Servicios públicos, Transporte)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_labor)
        else:
            await message.answer(
                f"✅ *Fecha:* {fecha_str}\n\n"
                "¿Cuál es la *labor realizada*?\n\n"
                "*(Describe la labor o actividad)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_labor)

    @router.message(CostoForm.esperando_labor, F.text)
    async def recibir_labor(message: types.Message, state: FSMContext):
        labor = message.text.strip()
        if not labor:
            await message.answer("❌ La labor no puede estar vacía:")
            return

        await state.update_data(labor=labor)

        data = await state.get_data()
        cat_key = data.get("cat_key", "")

        if cat_key == "administrativo":
            # Gastos admin: solo fecha, labor, valor total
            await message.answer(
                f"✅ *Gasto:* {labor}\n\n"
                "¿Cuál fue el *valor total* del gasto?\n\n"
                "*(Escribe el valor en pesos)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_valor_total)
        elif cat_key == "recoleccion":
            await message.answer(
                f"✅ *Labor:* {labor}\n\n"
                "¿Cuántos *kilos* se recolectaron?\n\n"
                "*(Escribe la cantidad)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_cantidad)
        elif cat_key == "beneficio":
            await message.answer(
                f"✅ *Labor:* {labor}\n\n"
                "¿Cuántos *jornales* se usaron?\n\n"
                "*(Escribe el número)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_cantidad)
        else:
            # MO para categorías con insumos
            await message.answer(
                f"✅ *Labor:* {labor}\n\n"
                "¿Cuántos *jornales* se usaron?\n\n"
                "*(Escribe el número)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_cantidad)

    @router.message(CostoForm.esperando_cantidad, F.text)
    async def recibir_cantidad_costo(message: types.Message, state: FSMContext):
        try:
            cantidad = float(message.text.strip().replace(",", "."))
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un número válido (mayor a 0):")
            return

        await state.update_data(cantidad=cantidad)

        data = await state.get_data()
        cat_key = data.get("cat_key", "")

        if cat_key == "recoleccion":
            # Recolección: solo valor total (V.Unitario = fórmula = E/C)
            await message.answer(
                f"✅ *Cantidad:* {cantidad}\n\n"
                "¿Cuál fue el *valor total* pagado?\n\n"
                "*(Escribe el valor en pesos)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_valor_total)
        else:
            await message.answer(
                f"✅ *Cantidad:* {cantidad}\n\n"
                "¿Cuál fue el *valor unitario* por jornal?\n\n"
                "*(Escribe el valor en pesos)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_valor_unitario)

    @router.message(CostoForm.esperando_valor_unitario, F.text)
    async def recibir_valor_unitario(message: types.Message, state: FSMContext):
        try:
            vu = float(message.text.strip().replace(".", "").replace(",", "."))
            if vu <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un valor válido (mayor a 0):")
            return

        await state.update_data(valor_unitario=vu)

        data = await state.get_data()
        cantidad = data.get("cantidad", 0)
        valor_total = vu * cantidad

        await message.answer(
            f"✅ *Valor unitario:* ${vu:,.0f}\n"
            f"💰 *Valor total calculado:* ${valor_total:,.0f} ({cantidad} × ${vu:,.0f})\n\n"
            "¿*Confirmas* el valor total o quieres ingresar uno diferente?\n\n"
            "*(Escribe el valor total o 'ok' para aceptar el calculado)*",
            parse_mode="Markdown",
        )
        await state.update_data(valor_total_calculado=valor_total)
        await state.set_state(CostoForm.esperando_valor_total)

    @router.message(CostoForm.esperando_valor_total, F.text)
    async def recibir_valor_total_costo(message: types.Message, state: FSMContext):
        texto = message.text.strip().lower()
        data = await state.get_data()

        if texto == "ok":
            valor_total = data.get("valor_total_calculado", 0)
        else:
            try:
                valor_total = float(message.text.strip().replace(".", "").replace(",", "."))
                if valor_total <= 0:
                    raise ValueError
            except ValueError:
                await message.answer("❌ Ingresa un valor válido o 'ok':")
                return

        await state.update_data(valor_total=valor_total)

        cat_key = data.get("cat_key", "")
        labor = data.get("labor", "")
        fecha = data.get("fecha", "")
        cantidad = data.get("cantidad", 0)
        vu = data.get("valor_unitario", 0)

        # Resumen MO
        texto_resumen = (
            f"📋 *Resumen — Mano de Obra*\n\n"
            f"🏠 *Finca:* {data.get('finca_nombre', '')}\n"
            f"📂 *Categoría:* {CATEGORIAS_PADRE.get(cat_key, CATEGORIAS_SIMPLE.get(cat_key, {}).get('nombre', cat_key))}\n"
            f"📅 *Fecha:* {fecha}\n"
            f"🔧 *Labor:* {labor}\n"
        )

        if cat_key == "administrativo":
            texto_resumen += f"💰 *Valor Total:* ${valor_total:,.0f}\n\n"
        elif cat_key == "recoleccion":
            texto_resumen += (
                f"⚖️ *Kilos:* {cantidad}\n"
                f"💰 *Valor Total:* ${valor_total:,.0f}\n\n"
            )
        elif cat_key == "beneficio":
            texto_resumen += (
                f"👷 *Jornales:* {cantidad}\n"
                f"💵 *V.Unitario:* ${vu:,.0f}\n"
                f"💰 *Valor Total:* ${valor_total:,.0f}\n\n"
            )
        else:
            texto_resumen += (
                f"👷 *Jornales:* {cantidad}\n"
                f"💵 *V.Unitario:* ${vu:,.0f}\n"
                f"💰 *Valor Total:* ${valor_total:,.0f}\n\n"
            )

        # Preguntar si quiere agregar insumos (solo para categorías que los tienen)
        if cat_key in CATEGORIAS_PADRE:
            texto_resumen += "¿*Confirmas* esta Mano de Obra?\n\n¿Quieres agregar *insumos* también?"
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(text="✅ Confirmar MO", callback_data="conf_costo_mo:si"),
                        types.InlineKeyboardButton(text="❌ Cancelar", callback_data="conf_costo_mo:no"),
                    ],
                    [
                        types.InlineKeyboardButton(text="➕ Agregar insumos", callback_data="conf_costo_mo:insumos"),
                    ],
                ]
            )
        else:
            texto_resumen += "¿*Confirmas* y guardas?"
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(text="✅ Sí, guardar", callback_data="conf_costo_mo:si"),
                        types.InlineKeyboardButton(text="❌ Cancelar", callback_data="conf_costo_mo:no"),
                    ],
                ]
            )

        await message.answer(texto_resumen, parse_mode="Markdown", reply_markup=keyboard)
        await state.set_state(CostoForm.esperando_confirmar_mo)

    @router.callback_query(CostoForm.esperando_confirmar_mo, F.data.startswith("conf_costo_mo:"))
    async def confirmar_mo(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        decision = callback.data.split(":", 1)[1]

        if decision == "no":
            await callback.message.edit_text(
                "❌ *Registro cancelado.*\n\nUsa /costo para intentar de nuevo.",
                parse_mode="Markdown",
            )
            await state.clear()
            return

        data = await state.get_data()
        cat_key = data.get("cat_key", "")

        if decision == "insumos":
            # Guardar MO y luego preguntar por insumos
            await guardar_mo(db, callback.message, data, state)

            await callback.message.edit_text(
                "✅ *Mano de Obra guardada.*\n\n"
                "Ahora, ¿cuál es el *producto/insumo* usado?\n\n"
                "*(Escribe el nombre del producto)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_producto)
            return

        # Solo guardar MO
        await guardar_mo(db, callback.message, data, state)
        await callback.message.edit_text(
            "✅ *¡Costo registrado exitosamente!* 🎉📉\n\n"
            "Usa /costo para registrar otro o /resumen para ver tus datos.",
            parse_mode="Markdown",
        )
        await state.clear()

    async def guardar_mo(db: Database, message: types.Message, data: dict, state: FSMContext):
        """Guarda un registro de Mano de Obra."""
        cat_key = data.get("cat_key", "")

        # Determinar categoría DB
        if cat_key in CATEGORIAS_PADRE:
            categoria_db = CATEGORIAS_PADRE[cat_key]["mo"]
        elif cat_key == "recoleccion":
            categoria_db = "recoleccion"
        elif cat_key == "beneficio":
            categoria_db = "beneficio"
        elif cat_key == "administrativo":
            categoria_db = "administrativo"
        else:
            logger.warning(f"Categoría desconocida: {cat_key}")
            return

        cantidad = data.get("cantidad", 0)
        vu = data.get("valor_unitario", 0)
        valor_total = data.get("valor_total", 0)

        # Para admin, no hay cantidad ni vu
        if cat_key == "administrativo":
            cantidad = 1
            vu = valor_total

        db.insert_transaccion(
            finca_id=data["finca_id"],
            lote_id=0,
            categoria=categoria_db,
            fecha=data["fecha"],
            labor=data.get("labor", ""),
            producto="",
            cantidad=cantidad,
            unidad="jornal",
            valor_unitario=vu,
            valor_total=valor_total,
        )
        logger.info(f"MO guardada: {categoria_db} en finca {data['finca_id']}")

    # --- FLUJO DE INSUMOS ---

    @router.message(CostoForm.esperando_producto, F.text)
    async def recibir_producto(message: types.Message, state: FSMContext):
        producto = message.text.strip()
        if not producto:
            await message.answer("❌ El producto no puede estar vacío:")
            return

        await state.update_data(producto=producto)
        await message.answer(
            f"✅ *Producto:* {producto}\n\n"
            "¿Cuál es la *cantidad* del insumo?\n\n"
            "*(Ej: 5 litros, 10 kg, 2 unidades)*",
            parse_mode="Markdown",
        )
        await state.set_state(CostoForm.esperando_cantidad_insumo)

    @router.message(CostoForm.esperando_cantidad_insumo, F.text)
    async def recibir_cantidad_insumo(message: types.Message, state: FSMContext):
        try:
            cantidad = float(message.text.strip().replace(",", "."))
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa una cantidad válida:")
            return

        await state.update_data(cantidad_insumo=cantidad)
        await message.answer(
            f"✅ *Cantidad:* {cantidad}\n\n"
            "¿Cuál es el *valor unitario* del insumo?\n\n"
            "*(Escribe el valor en pesos)*",
            parse_mode="Markdown",
        )
        await state.set_state(CostoForm.esperando_valor_unitario_insumo)

    @router.message(CostoForm.esperando_valor_unitario_insumo, F.text)
    async def recibir_vu_insumo(message: types.Message, state: FSMContext):
        try:
            vu = float(message.text.strip().replace(".", "").replace(",", "."))
            if vu <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Ingresa un valor válido:")
            return

        await state.update_data(vu_insumo=vu)

        data = await state.get_data()
        cantidad = data.get("cantidad_insumo", 0)
        valor_total = vu * cantidad

        await message.answer(
            f"✅ *Valor unitario:* ${vu:,.0f}\n"
            f"💰 *Valor total calculado:* ${valor_total:,.0f}\n\n"
            "¿*Confirmas* el valor total?\n\n"
            "*(Escribe el valor o 'ok' para aceptar)*",
            parse_mode="Markdown",
        )
        await state.update_data(valor_total_insumo_calc=valor_total)
        await state.set_state(CostoForm.esperando_valor_total_insumo)

    @router.message(CostoForm.esperando_valor_total_insumo, F.text)
    async def recibir_vt_insumo(message: types.Message, state: FSMContext):
        texto = message.text.strip().lower()
        data = await state.get_data()

        if texto == "ok":
            valor_total = data.get("valor_total_insumo_calc", 0)
        else:
            try:
                valor_total = float(message.text.strip().replace(".", "").replace(",", "."))
                if valor_total <= 0:
                    raise ValueError
            except ValueError:
                await message.answer("❌ Ingresa un valor válido o 'ok':")
                return

        await state.update_data(valor_total_insumo=valor_total)

        data = await state.get_data()
        texto_resumen = (
            f"📋 *Resumen — Insumo*\n\n"
            f"📦 *Producto:* {data.get('producto', '')}\n"
            f"⚖️ *Cantidad:* {data.get('cantidad_insumo', 0)}\n"
            f"💵 *V.Unitario:* ${data.get('vu_insumo', 0):,.0f}\n"
            f"💰 *Valor Total:* ${valor_total:,.0f}\n\n"
            "¿*Confirmas* este insumo?"
        )

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="✅ Sí, guardar", callback_data="conf_insumo:si"),
                    types.InlineKeyboardButton(text="➕ Otro insumo", callback_data="conf_insumo:otro"),
                    types.InlineKeyboardButton(text="❌ Cancelar", callback_data="conf_insumo:no"),
                ],
            ]
        )

        await message.answer(texto_resumen, parse_mode="Markdown", reply_markup=keyboard)
        await state.set_state(CostoForm.esperando_confirmar_insumo)

    @router.callback_query(CostoForm.esperando_confirmar_insumo, F.data.startswith("conf_insumo:"))
    async def confirmar_insumo(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        decision = callback.data.split(":", 1)[1]

        if decision == "no":
            await callback.message.edit_text(
                "❌ *Insumo cancelado.* Los datos de MO ya fueron guardados.",
                parse_mode="Markdown",
            )
            await state.clear()
            return

        data = await state.get_data()
        cat_key = data.get("cat_key", "")

        # Guardar insumo
        if cat_key in CATEGORIAS_PADRE:
            categoria_db = CATEGORIAS_PADRE[cat_key]["insumos"]
        else:
            logger.warning(f"No hay categoría de insumos para {cat_key}")
            await callback.message.edit_text("❌ *Error al guardar insumo.*", parse_mode="Markdown")
            await state.clear()
            return

        try:
            db.insert_transaccion(
                finca_id=data["finca_id"],
                lote_id=0,
                categoria=categoria_db,
                fecha=data.get("fecha", ""),
                labor=data.get("producto", ""),
                producto=data.get("producto", ""),
                cantidad=data.get("cantidad_insumo", 0),
                unidad="unidad",
                valor_unitario=data.get("vu_insumo", 0),
                valor_total=data.get("valor_total_insumo", 0),
            )
            logger.info(f"Insumo guardado: {categoria_db} en finca {data['finca_id']}")
        except Exception as e:
            logger.error(f"Error al guardar insumo: {e}", exc_info=True)
            await callback.message.edit_text("❌ *Error al guardar insumo.*", parse_mode="Markdown")
            await state.clear()
            return

        if decision == "otro":
            await callback.message.edit_text(
                "✅ *Insumo guardado.*\n\n"
                "¿Cuál es el siguiente *producto/insumo*?\n\n"
                "*(Escribe el nombre o /cancelar para terminar)*",
                parse_mode="Markdown",
            )
            await state.set_state(CostoForm.esperando_producto)
        else:
            await callback.message.edit_text(
                "✅ *¡Todos los datos registrados exitosamente!* 🎉📉\n\n"
                "Usa /costo para registrar otro o /resumen para ver tus datos.",
                parse_mode="Markdown",
            )
            await state.clear()

    @router.callback_query(F.data == "cancelar_operacion")
    async def cancelar_operacion(callback: types.CallbackQuery, state: FSMContext):
        """Cancela la operación actual desde un botón inline."""
        await callback.answer()
        await state.clear()
        await callback.message.edit_text(
            "❌ *Operación cancelada.*\n\nUsa /costo para intentar de nuevo.",
            parse_mode="Markdown",
        )

    return router
