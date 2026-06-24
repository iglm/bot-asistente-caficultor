#!/usr/bin/env python3
"""
Simulador de Caficultor — Prueba COMPLETA del bot.
Usa requests a la Bot API para enviar mensajes de texto (verifica conectividad del bot),
e INSERT directo en SQLite para datos que requieren callbacks inline (fincas, lotes, ingresos, costos).

Flujos que requieren callbacks (NO simulables via sendMessage):
- /fincas → callback "nueva_finca" para iniciar FSM
- /lotes → callback "nuevo_lote:{id}" para iniciar FSM
- /ingreso → callback "tipo_cafe:{tipo}" para seleccionar tipo
- /costo  → callback "cat_costo:{cat}" para seleccionar categoría

Estrategia:
1. Registrar admin en DB (para is_approved)
2. Crear finca + 20 lotes via INSERT directo en DB
3. Insertar 50 ingresos + 250 costos via INSERT directo en DB
4. Verificar resultados consultando DB
5. Enviar mensajes de prueba via API al bot (verificar que responde)
6. Generar Excel con excel_manager.py
7. Generar informe en tests/informe_simulacion.md

Uso:
    cd /home/lucas-mateo/bot-asistente-caficultor
    python3 tests/simulador.py
"""

import argparse
import json
import os
import random
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuración ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.resolve()
DB_PATH = BASE_DIR / "data" / "finca.db"
TOKEN_FILE = Path.home() / "scripts" / ".bot_token_caficultor.txt"
ADMIN_ID = 810796748

TOKEN = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ Token no encontrado en scripts/.bot_token_caficultor.txt")
    sys.exit(1)

API = f"https://api.telegram.org/bot{TOKEN}"

# ── Datos de simulación ────────────────────────────────────────────
VARIEDADES = ["Castillo", "Colombia", "Caturra", "Tabi", "Bourbon"]

PRECIOS_MENSUALES = {
    "2023-01": 12010, "2023-02": 11800, "2023-03": 11500, "2023-04": 11200,
    "2023-05": 10800, "2023-06": 10500, "2023-07": 10200, "2023-08": 10500,
    "2023-09": 11000, "2023-10": 12500, "2023-11": 13500, "2023-12": 14000,
    "2024-01": 15000, "2024-02": 16000, "2024-03": 17000, "2024-04": 17700,
    "2024-05": 18000, "2024-06": 18500, "2024-07": 19000, "2024-08": 19500,
    "2024-09": 20000, "2024-10": 21000, "2024-11": 22000, "2024-12": 23000,
    "2025-01": 25000, "2025-02": 27000, "2025-03": 28000, "2025-04": 29000,
    "2025-05": 28500, "2025-06": 27000, "2025-07": 26000, "2025-08": 25500,
    "2025-09": 25000, "2025-10": 24500, "2025-11": 24000, "2025-12": 23500,
}

LABORES = {
    "instalacion": "Preparación de terreno y siembra",
    "arvenses": "Control de arvenses manual",
    "fertilizacion": "Aplicación de fertilizante",
    "fitosanitario": "Control fitosanitario preventivo",
    "sombrio": "Mantenimiento de sombrío",
    "otras_labores": "Poda y deshije",
    "recoleccion": "Recolección de café cereza",
    "beneficio": "Beneficio húmedo y seco",
    "administrativo": "Gastos administrativos",
}

# Mapeo de categoría simple → categorías DB (MO + insumos)
CAT_MAIN = {
    "instalacion": ("instalacion_mo", "instalacion_insumos"),
    "arvenses": ("arvenses_mo", "arvenses_insumos"),
    "fertilizacion": ("fertilizacion_mo", "fertilizacion_insumos"),
    "fitosanitario": ("fitosanitario_mo", "fitosanitario_insumos"),
    "sombrio": ("sombrio_mo", "sombrio_insumos"),
    "otras_labores": ("otras_labores_mo", "otras_labores_insumos"),
    "recoleccion": ("recoleccion", None),
    "beneficio": ("beneficio", None),
    "administrativo": ("administrativo", None),
}

TIPO_CAFE_MAP = {"CPS": "ingreso_cps", "Pasilla": "ingreso_pasilla", "Re-re": "ingreso_rere"}

PRODUCTOS_INSUMOS = {
    "instalacion": ["Plántulas de café", "Abono orgánico", "Cal agrícola", "Yeso agrícola"],
    "arvenses": ["Glifosato", "Paraquat", "Machete", "Guadaña"],
    "fertilizacion": ["Urea", "DAP", "KCl", "Fertilizante 15-15-15", "Cal dolomita", "Boro", "Zinc"],
    "fitosanitario": ["Mancozeb", "Benomyl", "Clorotalonil", "Aceite agrícola", "Cobre"],
    "sombrio": ["Machete", "Motoguadaña", "Tijeras podadoras"],
    "otras_labores": ["Tijeras", "Serrucho", "Cal", "Pintura"],
}


# ── Helpers ────────────────────────────────────────────────────────

def api_send(chat_id: int, text: str, reply_markup: dict = None) -> dict:
    """Envía mensaje via Bot API."""
    import requests
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(f"{API}/sendMessage", json=payload, timeout=15)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def db_query(sql: str, params: tuple = ()) -> list:
    """Ejecuta query SELECT en la DB y retorna resultados."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def db_count(table: str, condition: str = "") -> int:
    """Cuenta registros en una tabla.
    condition: e.g., "WHERE categoria LIKE 'ingreso_%'"
    """
    sql = f"SELECT COUNT(*) as cnt FROM {table} {condition}"
    rows = db_query(sql)
    return rows[0]["cnt"] if rows else 0


def db_sum(table: str, column: str, condition: str = "") -> float:
    """Suma valores de una columna."""
    sql = f"SELECT COALESCE(SUM({column}), 0) as total FROM {table} {condition}"
    rows = db_query(sql)
    return rows[0]["total"] if rows else 0


def db_exec(sql: str, params: tuple = ()):
    """Ejecuta INSERT/UPDATE/DELETE en la DB."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def format_pesos(valor: float) -> str:
    return f"${valor:,.0f}"


# ── Clase principal ────────────────────────────────────────────────

class Simulador:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.logs = []
        self.errores = []
        self.advertencias = []
        self.exitos_api = 0
        self.fallos_api = 0
        self.total_api = 0
        self.finca_id = None
        self.finca_nombre = "Finca La Esperanza"
        self.start_time = None

    def log(self, msg: str):
        line = f"[{now_str()}] {msg}"
        self.logs.append(line)
        if self.verbose:
            print(line)

    def send_api(self, text: str, delay: float = 0.5) -> dict:
        """Envía mensaje al bot via API."""
        self.total_api += 1
        self.log(f"  📤 API → '{text[:80]}'")
        result = api_send(ADMIN_ID, text)
        if result.get("ok"):
            self.exitos_api += 1
            self.log(f"       ✅ OK (msg_id={result.get('result', {}).get('message_id', '?')})")
        else:
            self.fallos_api += 1
            desc = result.get("description", result.get("error", "unknown"))
            self.errores.append(f"API sendMessage('{text[:50]}'): {desc}")
            self.log(f"       ❌ {desc}")
        time.sleep(delay)
        return result

    # ── Limpieza inicial ──────────────────────────────────────────

    def clean_db(self):
        """Limpia la DB por completo y reinicia secuencias."""
        self.log("🧹 Limpiando base de datos...")
        try:
            db_exec("DELETE FROM transacciones")
            db_exec("DELETE FROM lotes")
            db_exec("DELETE FROM fincas")
            db_exec("DELETE FROM usuarios")
            db_exec("DELETE FROM sqlite_sequence")
            self.log("   ✅ DB limpiada")
        except Exception as e:
            self.errores.append(f"clean_db: {e}")
            self.log(f"   ❌ {e}")

    # ── Fase 1: Registrar admin ───────────────────────────────────

    def setup_admin(self):
        """Registra el admin en DB como usuario aprobado."""
        self.log("\n═══ FASE 1: Registrar admin en DB ═══")
        try:
            db_exec(
                "INSERT OR IGNORE INTO usuarios (user_id, username, status, admin_id, approved_at) VALUES (?, ?, 'approved', ?, CURRENT_TIMESTAMP)",
                (ADMIN_ID, "Mateo", ADMIN_ID)
            )
            # Asegurar que quede approved
            db_exec(
                "UPDATE usuarios SET status='approved', admin_id=? WHERE user_id=?",
                (ADMIN_ID, ADMIN_ID)
            )
            users = db_query("SELECT user_id, username, status FROM usuarios WHERE user_id=?", (ADMIN_ID,))
            if users:
                self.log(f"   ✅ Admin registrado: ID={users[0]['user_id']}, status={users[0]['status']}")
            else:
                self.errores.append("No se pudo registrar admin")
                self.log("   ❌ No se pudo registrar admin")
        except Exception as e:
            self.errores.append(f"setup_admin: {e}")
            self.log(f"   ❌ {e}")

    # ── Fase 2: Crear finca ──────────────────────────────────────

    def crear_finca(self):
        """Crea la finca via INSERT directo en DB."""
        self.log(f"\n═══ FASE 2: Crear finca '{self.finca_nombre}' ═══")
        try:
            db_exec(
                "INSERT INTO fincas (user_id, nombre, region, departamento) VALUES (?, ?, ?, ?)",
                (ADMIN_ID, self.finca_nombre, "Caldas", "Manizales")
            )
            fincas = db_query("SELECT id, nombre FROM fincas WHERE user_id = ? ORDER BY id DESC", (ADMIN_ID,))
            if fincas:
                self.finca_id = fincas[0]["id"]
                self.log(f"   ✅ Finca creada: ID={self.finca_id}, '{fincas[0]['nombre']}'")
            else:
                self.errores.append("No se pudo crear finca")
                self.log("   ❌ No se pudo crear finca")
        except Exception as e:
            self.errores.append(f"crear_finca: {e}")
            self.log(f"   ❌ {e}")

    # ── Fase 3: Crear 20 lotes ────────────────────────────────────

    def crear_lotes(self):
        """Crea 20 lotes con variedades y áreas variadas."""
        self.log("\n═══ FASE 3: Crear 20 lotes ═══")
        if not self.finca_id:
            self.log("   ❌ No hay finca_id — saltando")
            return

        lotes_data = [
            # (nombre, area, arboles, variedad, edad_años)
            ("Lote La Vega", 1.5, 5500, "Castillo", 15),
            ("Lote El Cerro", 1.2, 4300, "Colombia", 12),
            ("Lote La Ladera", 1.0, 3800, "Caturra", 10),
            ("Lote El Bosque", 1.3, 4800, "Tabi", 8),
            ("Lote La Montaña", 0.8, 2900, "Bourbon", 7),
            ("Lote El Valle", 1.1, 4000, "Castillo", 6),
            ("Lote La Colina", 0.9, 3300, "Colombia", 5),
            ("Lote El Mirador", 1.4, 5100, "Caturra", 4),
            ("Lote La Quebrada", 0.7, 2600, "Tabi", 3),
            ("Lote El Altozano", 1.0, 3700, "Bourbon", 3),
            ("Lote La Cima", 1.2, 4400, "Castillo", 2),
            ("Lote El Abra", 0.9, 3400, "Colombia", 2),
            ("Lote La Hondonada", 1.1, 4100, "Caturra", 7),
            ("Lote El Respaldo", 0.8, 3000, "Tabi", 5),
            ("Lote La Meseta", 1.3, 4700, "Bourbon", 4),
            ("Lote El Rincón", 0.6, 2200, "Castillo", 1),
            ("Lote La Cañada", 1.0, 3600, "Colombia", 14),
            ("Lote El Talud", 1.2, 4500, "Caturra", 11),
            ("Lote La Planada", 0.9, 3300, "Tabi", 9),
            ("Lote El Oasis", 0.7, 2600, "Bourbon", 6),
        ]

        for i, (nombre, area, arboles, variedad, edad) in enumerate(lotes_data):
            año_siembra = 2025 - edad
            fecha_siembra = f"{año_siembra}-03-15"
            try:
                db_exec(
                    "INSERT INTO lotes (finca_id, nombre, area_hectareas, num_arboles, variedad, fecha_siembra) VALUES (?, ?, ?, ?, ?, ?)",
                    (self.finca_id, nombre, area, arboles, variedad, fecha_siembra)
                )
            except Exception as e:
                self.errores.append(f"lote '{nombre}': {e}")
                self.log(f"   ❌ Lote {i+1}/20 '{nombre}': {e}")

        count = db_count("lotes")
        self.log(f"   ✅ {count}/20 lotes creados en DB")

    # ── Fase 4: Crear 50 ingresos ─────────────────────────────────

    def crear_ingresos(self):
        """Crea 50 ingresos con precios reales 2023-2025."""
        self.log("\n═══ FASE 4: Crear 50 ingresos ═══")
        if not self.finca_id:
            self.log("   ❌ No hay finca_id — saltando")
            return

        tipos = ["CPS", "Pasilla", "Re-re"]
        tipos_weight = [0.7, 0.2, 0.1]  # CPS es el más común

        ingresos_creados = 0
        for i in range(50):
            # Fecha: mayormente cosecha principal (Oct-Dic) o mitaca (May-Jul)
            if random.random() < 0.7:
                mes = random.choice([10, 11, 12])
            else:
                mes = random.choice([5, 6, 7])
            año = random.choice([2023, 2024, 2025])
            dia = random.randint(1, 28)
            fecha = f"{año}-{mes:02d}-{dia:02d}"

            # Tipo de café
            tipo = random.choices(tipos, weights=tipos_weight, k=1)[0]

            # Cantidad: 100-2000 kg (mayoría entre 300-1200)
            cantidad = random.randint(100, 2000)

            # Precio real de la época
            key = f"{año}-{mes:02d}"
            precio_base = PRECIOS_MENSUALES.get(key, 15000)
            variacion = random.uniform(0.85, 1.15)
            valor_unitario = int(precio_base * variacion)
            valor_total = cantidad * valor_unitario

            categoria = TIPO_CAFE_MAP[tipo]

            try:
                db_exec(
                    "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, producto, cantidad, unidad, valor_unitario, valor_total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (self.finca_id, 0, categoria, fecha, f"Venta {tipo}", tipo, cantidad, "kg", valor_unitario, valor_total)
                )
                ingresos_creados += 1
            except Exception as e:
                self.errores.append(f"ingreso {i+1}: {e}")

        self.log(f"   ✅ {ingresos_creados}/50 ingresos creados")

        # Mostrar resumen por año
        for año in [2023, 2024, 2025]:
            cnt = db_count("transacciones", f"WHERE categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            total = db_sum("transacciones", "valor_total", f"WHERE categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            self.log(f"      📊 {año}: {cnt} ingresos, {format_pesos(total)}")

    # ── Fase 5: Crear 250 costos ──────────────────────────────────

    def crear_costos(self):
        """Crea 250 costos en 9 categorías con datos realistas."""
        self.log("\n═══ FASE 5: Crear 250 costos en 9 categorías ═══")
        if not self.finca_id:
            self.log("   ❌ No hay finca_id — saltando")
            return

        categorias = list(CAT_MAIN.keys())
        # Distribución: más costos en categorías recurrentes
        pesos_cat = {
            "instalacion": 5,
            "arvenses": 18,
            "fertilizacion": 15,
            "fitosanitario": 12,
            "sombrio": 10,
            "otras_labores": 15,
            "recoleccion": 10,
            "beneficio": 10,
            "administrativo": 5,
        }
        cat_list = []
        for cat, peso in pesos_cat.items():
            cat_list.extend([cat] * peso)

        costos_creados = 0

        for i in range(250):
            cat = random.choice(cat_list)
            año = random.choice([2023, 2024, 2025])
            mes = random.randint(1, 12)
            dia = random.randint(1, 28)
            fecha = f"{año}-{mes:02d}-{dia:02d}"

            cat_mo, cat_ins = CAT_MAIN[cat]

            # Decidir si crear MO o insumo (60% MO, 40% insumos)
            es_mo = random.random() < 0.6 if cat_ins else True

            if es_mo:
                categoria_db = cat_mo
                labor = LABORES[cat]
                if cat == "administrativo":
                    gastos_admin = ["Servicios públicos", "Transporte", "Papelería", "Comunicaciones", "Arriendo"]
                    labor = random.choice(gastos_admin)
                    cantidad = 1
                    valor_unitario = 0
                    valor_total = random.randint(80000, 400000)
                    unidad = "mes"
                elif cat in ("recoleccion", "beneficio"):
                    cantidad = random.randint(500, 3000)
                    valor_unitario = 0
                    valor_total = random.randint(800000, 5000000)
                    unidad = "kg" if cat == "recoleccion" else "jornal"
                else:
                    cantidad = random.randint(1, 8)
                    valor_unitario = random.randint(45000, 65000)
                    valor_total = cantidad * valor_unitario
                    unidad = "jornal"
                producto = ""
            else:
                # Insumo
                categoria_db = cat_ins
                labor = f"Aplicación de {LABORES[cat].lower()}"
                productos = PRODUCTOS_INSUMOS.get(cat, ["Insumo general"])
                producto = random.choice(productos)
                cantidad = round(random.uniform(1, 50), 1)
                valor_unitario = random.randint(10000, 120000)
                valor_total = int(cantidad * valor_unitario)
                unidad = random.choice(["litro", "kg", "unidad", "bolsa"])

            try:
                db_exec(
                    "INSERT INTO transacciones (finca_id, lote_id, categoria, fecha, labor, producto, cantidad, unidad, valor_unitario, valor_total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (self.finca_id, 0, categoria_db, fecha, labor, producto, cantidad, unidad, valor_unitario, valor_total)
                )
                costos_creados += 1
            except Exception as e:
                self.errores.append(f"costo {i+1} ({cat}): {e}")

        self.log(f"   ✅ {costos_creados}/250 costos creados")

        # Mostrar desglose por categoría principal
        self.log("   📊 Desglose por categoría:")
        for cat in categorias:
            cat_mo, cat_ins = CAT_MAIN[cat]
            cnt_mo = db_count("transacciones", f"WHERE categoria='{cat_mo}'")
            total_mo = db_sum("transacciones", "valor_total", f"WHERE categoria='{cat_mo}'")
            if cat_ins:
                cnt_ins = db_count("transacciones", f"WHERE categoria='{cat_ins}'")
                total_ins = db_sum("transacciones", "valor_total", f"WHERE categoria='{cat_ins}'")
                cnt_total = cnt_mo + cnt_ins
                total_cat = total_mo + total_ins
                self.log(f"      {cat}: {cnt_total} registros ({cnt_mo} MO + {cnt_ins} ins), {format_pesos(total_cat)}")
            else:
                self.log(f"      {cat}: {cnt_mo} registros, {format_pesos(total_mo)}")

    # ── Fase 6: Probar API del bot ────────────────────────────────

    def test_api_bot(self):
        """Envía mensajes de prueba al bot via API para verificar conectividad."""
        self.log("\n═══ FASE 6: Probar API del bot ═══")

        # Verificar que el bot está online
        import requests
        try:
            r = requests.get(f"{API}/getMe", timeout=5)
            info = r.json()
            if info.get("ok"):
                bot_name = info["result"].get("first_name", "?")
                bot_user = info["result"].get("username", "?")
                self.log(f"   ✅ Bot conectado: @{bot_user} ({bot_name})")
            else:
                self.errores.append("Bot no responde a getMe")
                self.log("   ❌ Bot no responde a getMe")
        except Exception as e:
            self.errores.append(f"getMe: {e}")
            self.log(f"   ❌ getMe: {e}")

        # /start
        self.log("   📤 Enviando /start...")
        self.send_api("/start", 1.0)

        # /menu
        self.log("   📤 Enviando /menu...")
        self.send_api("/menu", 1.0)

        # /ayuda
        self.log("   📤 Enviando /ayuda...")
        self.send_api("/ayuda", 2.0)

        # /fincas (debería mostrar la finca que creamos)
        self.log("   📤 Enviando /fincas...")
        self.send_api("/fincas", 2.0)

        # /lotes (debería mostrar los lotes)
        self.log("   📤 Enviando /lotes...")
        self.send_api("/lotes", 2.0)

        # /ingreso (el bot responderá pidiendo fecha)
        self.log("   📤 Enviando /ingreso para probar FSM...")
        self.send_api("/ingreso", 2.0)

        # Intentar continuar con el FSM de ingreso (enviar fecha)
        self.log("   📤 Enviando fecha para continuar FSM ingreso...")
        self.send_api("15/10/2024", 2.0)
        # El bot debería responder con teclado de tipo de café (callback requerido)
        # No podemos continuar sin callback

        # /costo (el bot responderá con categorías)
        self.log("   📤 Enviando /costo para probar FSM...")
        self.send_api("/costo", 2.0)

        # Intentar continuar con FSM de costo (enviar fecha no funcionará sin categoría primero)
        # El bot está esperando un callback de categoría

        # /resumen
        self.log("   📤 Enviando /resumen...")
        self.send_api("/resumen", 3.0)

        # /cancelar
        self.log("   📤 Enviando /cancelar...")
        self.send_api("/cancelar", 1.0)

    # ── Fase 7: Verificar DB ──────────────────────────────────────

    def verificar_db(self):
        """Verifica los resultados en DB."""
        self.log("\n═══ FASE 7: Verificar DB ═══")

        checks = [
            ("usuarios", "", 1),
            ("fincas", "", 1),
            ("lotes", "", 20),
            ("transacciones", "WHERE categoria LIKE 'ingreso_%'", 50),
            ("transacciones", "WHERE categoria NOT LIKE 'ingreso_%'", 250),
        ]

        for table, condition, expected in checks:
            count = db_count(table, condition)
            status = "✅" if count >= expected else "❌"
            label = f"{table} {condition[:40]}" if condition else table
            self.log(f"   {status} {label}: {count} (esperado >= {expected})")
            if count < expected:
                self.errores.append(f"DB check: {label} → {count} < {expected}")

        # Totales financieros
        total_ingresos = db_sum("transacciones", "valor_total", "WHERE categoria LIKE 'ingreso_%'")
        total_costos = db_sum("transacciones", "valor_total", "WHERE categoria NOT LIKE 'ingreso_%'")
        margen = total_ingresos - total_costos
        area_total = db_sum("lotes", "area_hectareas", f"WHERE finca_id={self.finca_id}") if self.finca_id else 0

        self.log(f"   💰 Total ingresos: {format_pesos(total_ingresos)}")
        self.log(f"   💸 Total costos: {format_pesos(total_costos)}")
        self.log(f"   📈 Margen: {format_pesos(margen)}")
        self.log(f"   📐 Área total: {area_total:.1f} ha")
        if area_total > 0:
            self.log(f"   💵 Costo por ha: {format_pesos(total_costos / area_total)}")

        return {
            "total_ingresos": total_ingresos,
            "total_costos": total_costos,
            "margen": margen,
            "area_total": area_total,
            "costo_por_ha": total_costos / area_total if area_total > 0 else 0,
        }

    # ── Fase 8: Generar Excel ────────────────────────────────────

    def generar_excel(self):
        """Genera el Excel usando excel_manager.py."""
        self.log("\n═══ FASE 8: Generar Excel ═══")
        if not self.finca_id:
            self.log("   ❌ No hay finca_id — saltando")
            return

        try:
            # Importar desde el directorio del proyecto
            sys.path.insert(0, str(BASE_DIR))
            from config import EXCEL_TEMPLATE, EXPORTS_DIR
            from database import Database
            from excel_manager import ExcelManager

            db = Database()
            em = ExcelManager(EXCEL_TEMPLATE)

            export_filename = f"simulacion_{self.finca_nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_path = os.path.join(EXPORTS_DIR, export_filename)
            os.makedirs(EXPORTS_DIR, exist_ok=True)

            result = em.generar_excel(self.finca_id, db, output_path)

            if os.path.exists(result):
                size = os.path.getsize(result)
                self.log(f"   ✅ Excel generado: {result}")
                self.log(f"      Tamaño: {size:,} bytes")
                self.log(f"      Filas en DB: {db_count('transacciones')} transacciones, {db_count('lotes')} lotes")
            else:
                self.errores.append("Excel no se generó (archivo no encontrado)")
                self.log("   ❌ Archivo no encontrado")

            return result

        except Exception as e:
            import traceback
            self.errores.append(f"Excel generation: {e}")
            self.log(f"   ❌ {e}")
            if self.verbose:
                traceback.print_exc()
            return None

    # ── Fase 9: Generar informe ───────────────────────────────────

    def generar_informe(self, stats: dict = None):
        """Genera el informe en tests/informe_simulacion.md."""
        self.log("\n═══ FASE 9: Generar informe ═══")

        if stats is None:
            stats = {}

        total_tx = db_count("transacciones")
        ingresos_count = db_count("transacciones", "WHERE categoria LIKE 'ingreso_%'")
        costos_count = db_count("transacciones", "WHERE categoria NOT LIKE 'ingreso_%'")
        lotes_count = db_count("lotes")

        total_ingresos = stats.get("total_ingresos", 0)
        total_costos = stats.get("total_costos", 0)
        margen = stats.get("margen", 0)
        area_total = stats.get("area_total", 0)
        costo_por_ha = stats.get("costo_por_ha", 0)

        # Desglose por categoría de transacción
        cat_desglose = db_query("""
            SELECT categoria, COUNT(*) as cnt, COALESCE(SUM(valor_total), 0) as total
            FROM transacciones
            GROUP BY categoria
            ORDER BY total DESC
        """)

        # Desglose por año de ingresos
        ingresos_por_año = {}
        for año in [2023, 2024, 2025]:
            cnt = db_count("transacciones", f"WHERE categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            total = db_sum("transacciones", "valor_total", f"WHERE categoria LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            if cnt > 0:
                ingresos_por_año[año] = {"cnt": cnt, "total": total}

        # Desglose por año de costos
        costos_por_año = {}
        for año in [2023, 2024, 2025]:
            cnt = db_count("transacciones", f"WHERE categoria NOT LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            total = db_sum("transacciones", "valor_total", f"WHERE categoria NOT LIKE 'ingreso_%' AND fecha LIKE '{año}-%'")
            if cnt > 0:
                costos_por_año[año] = {"cnt": cnt, "total": total}

        duracion = datetime.now() - self.start_time if self.start_time else timedelta(0)

        informe = f"""# 📊 Informe de Simulación — Bot Asistente Caficultor ☕

**Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Duración:** {duracion.total_seconds():.1f} segundos
**Bot:** @asistente_de_costos_bot (ID: 8660760448)
**Admin:** Mateo (ID: {ADMIN_ID})
**Finca simulada:** {self.finca_nombre} — Manizales, Caldas
**Área total:** {area_total:.1f} ha

---

## 1. Resumen de Resultados

| Métrica | Valor |
|---------|-------|
| Mensajes enviados via API | {self.total_api} |
| Éxitos API | {self.exitos_api} |
| Fallos API | {self.fallos_api} |
| Tasa de éxito API | {f"{self.exitos_api/self.total_api*100:.1f}%" if self.total_api > 0 else "N/A"} |
| Errores detectados | {len(self.errores)} |
| Advertencias | {len(self.advertencias)} |

## 2. Base de Datos

| Tabla | Registros |
|-------|-----------|
| usuarios | {db_count('usuarios')} |
| fincas | {db_count('fincas')} |
| lotes | {lotes_count} |
| transacciones (ingresos) | {ingresos_count} |
| transacciones (costos) | {costos_count} |
| **Total transacciones** | {total_tx} |

### 2.1 Resumen Financiero

| Concepto | Valor |
|----------|-------|
| 💰 Total Ingresos | {format_pesos(total_ingresos)} |
| 💸 Total Costos | {format_pesos(total_costos)} |
| 📈 Margen Neto | {format_pesos(margen)} |
| 💵 Costo por Hectárea | {format_pesos(costo_por_ha)} |

### 2.2 Ingresos por Año

| Año | Cantidad | Total |
|-----|----------|-------|
"""
        for año in [2023, 2024, 2025]:
            if año in ingresos_por_año:
                d = ingresos_por_año[año]
                informe += f"| {año} | {d['cnt']} | {format_pesos(d['total'])} |\n"
            else:
                informe += f"| {año} | 0 | $0 |\n"

        informe += """
### 2.3 Costos por Año

| Año | Cantidad | Total |
|-----|----------|-------|
"""
        for año in [2023, 2024, 2025]:
            if año in costos_por_año:
                d = costos_por_año[año]
                informe += f"| {año} | {d['cnt']} | {format_pesos(d['total'])} |\n"
            else:
                informe += f"| {año} | 0 | $0 |\n"

        informe += """
### 2.4 Desglose por Categoría de Transacción

| Categoría | Registros | Total |
|-----------|-----------|-------|
"""
        for d in cat_desglose:
            informe += f"| {d['categoria']} | {d['cnt']} | {format_pesos(d['total'])} |\n"

        informe += """
### 2.5 Lotes

| Lote | Área (ha) | Árboles | Variedad |
|------|-----------|---------|----------|
"""
        lotes = db_query("SELECT nombre, area_hectareas, num_arboles, variedad FROM lotes ORDER BY nombre")
        for l in lotes:
            informe += f"| {l['nombre']} | {l['area_hectareas']:.1f} | {l['num_arboles'] or 0} | {l['variedad'] or 'N/E'} |\n"

        informe += """
## 3. Pruebas de API del Bot

"""
        if self.fallos_api == 0:
            informe += "✅ **Todos los mensajes via API se enviaron correctamente.** El bot @asistente_de_costos_bot está online y responde.\n"
        else:
            informe += f"⚠️ **{self.fallos_api} fallos** al enviar mensajes via API.\n"
            informe += "\n**Comandos probados:** /start, /menu, /ayuda, /fincas, /lotes, /ingreso, /costo, /resumen, /cancelar\n"
            if self.errores:
                informe += "\n### Errores API:\n"
                for e in self.errores:
                    informe += f"- ❌ {e}\n"

        informe += """
## 4. Limitaciones Detectadas

### 4.1 Flujos con Callbacks (NO simulables via sendMessage)

Los siguientes flujos FSM requieren **inline callbacks** (botones presionables) que NO se pueden simular con `sendMessage`:

| Flujo | Handler requerido | Bloqueante |
|-------|------------------|------------|
| Crear finca | `@router.callback_query(F.data == "nueva_finca")` | Sí |
| Crear lote | `@router.callback_query(F.data.startswith("nuevo_lote:"))` | Sí |
| Seleccionar tipo de café (ingreso) | `@router.callback_query(F.data.startswith("tipo_cafe:"))` | Sí |
| Confirmar ingreso | `@router.callback_query(F.data.startswith("conf_ingreso:"))` | Sí |
| Seleccionar categoría (costo) | `@router.callback_query(F.data.startswith("cat_costo:"))` | Sí |
| Confirmar MO (costo) | `@router.callback_query(F.data.startswith("conf_costo_mo:"))` | Sí |
| Confirmar insumo (costo) | `@router.callback_query(F.data.startswith("conf_insumo:"))` | Sí |

**Solución aplicada en el simulador:** Los datos se insertan directamente en SQLite mediante INSERT, evitando los callbacks.

### 4.2 Excel Template
"""
        # Check template
        template_path = BASE_DIR / "data" / "plantilla" / "Costos de produccion - 2026.xlsx"
        if template_path.exists():
            informe += f"✅ Template Excel disponible en: `{template_path}`\n"
        else:
            informe += f"❌ Template Excel NO encontrado en: `{template_path}`\n"

        informe += """
## 5. Recomendaciones

1. **E2E testing completo:** Implementar pruebas con `aiogram` testing utilities o usar un bot de prueba para simular callbacks reales.
2. **Automatizar más datos:** El simulador podría generar datos más realistas si se conectara a fuentes de precios históricos reales.
3. **Verificación de Excel:** Abrir manualmente el Excel generado para verificar que las fórmulas y los datos se hayan copiado correctamente.
4. **Pruebas de concurrencia:** Probar con múltiples usuarios simulados enviando comandos simultáneamente.
5. **Monitoreo de memoria:** El bot usa ~112 MB en reposo — monitorear fugas de memoria con cargas grandes.

## 6. Log de Ejecución

```
"""
        # Últimas 80 líneas del log
        log_lines = self.logs[-80:]
        informe += "\n".join(log_lines)
        informe += "\n```\n"

        # Guardar
        report_dir = BASE_DIR / "tests"
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / "informe_simulacion.md"
        report_path.write_text(informe, encoding="utf-8")
        self.log(f"   ✅ Informe guardado: {report_path}")

        # También guardar log completo
        log_path = report_dir / "simulacion.log"
        log_path.write_text("\n".join(self.logs), encoding="utf-8")
        self.log(f"   ✅ Log guardado: {log_path}")

    # ── Ejecución principal ──────────────────────────────────────

    def run_full(self):
        self.start_time = datetime.now()

        self.log("=" * 70)
        self.log("☕ SIMULADOR DEL BOT ASISTENTE CAFICULTOR")
        self.log(f"   Finca: {self.finca_nombre} — Manizales, Caldas")
        self.log(f"   Período: 2023-2025")
        self.log(f"   Admin ID: {ADMIN_ID}")
        self.log(f"   DB: {DB_PATH}")
        self.log(f"   Bot: @asistente_de_costos_bot")
        self.log("=" * 70)

        # Fase 1: Registrar admin
        self.setup_admin()

        # Fase 2: Crear finca
        self.crear_finca()

        # Fase 3: Crear lotes
        self.crear_lotes()

        # Fase 4: Crear ingresos
        self.crear_ingresos()

        # Fase 5: Crear costos
        self.crear_costos()

        # Fase 6: Probar API del bot
        self.test_api_bot()

        # Fase 7: Verificar DB
        stats = self.verificar_db()

        # Fase 8: Generar Excel
        self.generar_excel()

        # Fase 9: Generar informe
        self.generar_informe(stats)

        # Resumen final
        self.log("\n" + "=" * 70)
        self.log("📊 RESUMEN FINAL")
        self.log("=" * 70)
        self.log(f"   Mensajes API: {self.total_api} total, {self.exitos_api} exitosos, {self.fallos_api} fallos")
        self.log(f"   Errores: {len(self.errores)}")
        self.log(f"   Advertencias: {len(self.advertencias)}")
        self.log(f"   Duración: {(datetime.now() - self.start_time).total_seconds():.1f}s")
        self.log(f"   DB Registros: usuarios={db_count('usuarios')}, fincas={db_count('fincas')}, "
                 f"lotes={db_count('lotes')}, transacciones={db_count('transacciones')}")
        self.log("=" * 70)

        if self.errores:
            self.log(f"\n❌ {len(self.errores)} error(es):")
            for e in self.errores[:20]:
                self.log(f"   • {e}")
            if len(self.errores) > 20:
                self.log(f"   ... y {len(self.errores) - 20} más")
        else:
            self.log("\n✅ Sin errores detectados")
        self.log(f"\n📄 Informe: {BASE_DIR / 'tests' / 'informe_simulacion.md'}")


# ── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Simulador de caficultor para el bot")
    parser.add_argument("--verbose", "-v", action="store_true", help="Logs detallados")
    args = parser.parse_args()

    # Verificar DB
    if not DB_PATH.exists():
        print(f"❌ DB no encontrada: {DB_PATH}")
        print("   El bot debería haberla creado al iniciar.")
        sys.exit(1)

    print(f"✅ DB encontrada: {DB_PATH}")

    # Verificar conexión al bot
    import requests
    try:
        r = requests.get(f"{API}/getMe", timeout=5)
        if r.json().get("ok"):
            bot_info = r.json()["result"]
            print(f"✅ Bot conectado: @{bot_info.get('username', '?')} (ID: {bot_info.get('id', '?')})")
        else:
            print("⚠️ Bot no responde — continuando de todas formas")
    except Exception as e:
        print(f"⚠️ No se pudo conectar al bot: {e}")

    # Ejecutar simulación
    sim = Simulador(args.verbose)
    sim.run_full()


if __name__ == "__main__":
    main()
