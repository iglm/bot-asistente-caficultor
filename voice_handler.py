"""
voice_handler.py — Procesamiento de mensajes de voz para el bot caficultor
==========================================================================
Usa Whisper local (open-source, gratis) para transcribir voz a texto.
Luego usa un parser de lenguaje natural (sin IA) para extraer datos.

Flujo:
    Usuario envía voz → Bot descarga .ogg → Whisper transcribe → 
    Parser extrae datos → Muestra resumen → Usuario confirma → Guarda en DB
"""

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from aiogram import types

logger = logging.getLogger(__name__)

# ── Modelo Whisper (tiny = rápido, base = balance, small = mejor) ──
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

# ── Diccionarios para parser de lenguaje natural ──

# Mapeo de palabras clave → categorías de costo
COSTO_KEYWORDS = {
    # Instalación
    "siembr": "instalacion", "trasplant": "instalacion", "vivero": "instalacion",
    "colino": "instalacion", "hoyo": "instalacion", "ahoy": "instalacion",
    "chapol": "instalacion", "matachapol": "instalacion",
    # Arvenses
    "maleza": "arvenses", "guadañ": "arvenses", "deshierb": "arvenses",
    "plateo": "arvenses", "machete": "arvenses", "herbicid": "arvenses",
    "gramoxon": "arvenses", "matamalez": "arvenses",
    "limpi": "arvenses", "rocer": "arvenses", "roza": "arvenses",
    "chapia": "arvenses", "chapiamos": "arvenses", "chape": "arvenses",
    "corte de arvense": "arvenses", "control maleza": "arvenses",
    # Fertilización
    "abon": "fertilizacion", "fertiliz": "fertilizacion", "enmiend": "fertilizacion",
    "urea": "fertilizacion", "npk": "fertilizacion", "cal": "fertilizacion",
    "dolomita": "fertilizacion", "abono organico": "fertilizacion",
    "compost": "fertilizacion", "gallinaza": "fertilizacion", "bokashi": "fertilizacion",
    "edáfic": "fertilizacion", "foliar": "fertilizacion",
    # Fitosanitario
    "fumig": "fitosanitario", "roya": "fitosanitario", "broca": "fitosanitario",
    "insecticid": "fitosanitario", "fungicid": "fitosanitario",
    "plaga": "fitosanitario", "enfermed": "fitosanitario",
    "mancha de hierro": "fitosanitario", "gotera": "fitosanitario",
    "antracnosis": "fitosanitario", "ojo de gallo": "fitosanitario",
    "cercospora": "fitosanitario", "minador": "fitosanitario",
    # Sombrío
    "sombri": "sombrio", "podar": "sombrio", "arbol": "sombrio",
    "guamo": "sombrio", "carbonero": "sombrio",
    "regulacion sombrio": "sombrio", "sombrío": "sombrio",
    "poda de sombra": "sombrio", "tumbar palo": "sombrio",
    "rale": "sombrio", "árbol": "sombrio",
    # Recolección
    "cosech": "recoleccion", "recog": "recoleccion", "cort": "recoleccion",
    "cafeter": "recoleccion", "grano": "recoleccion",
    "recolect": "recoleccion", "pisca": "recoleccion", "piscar": "recoleccion",
    "café cereza": "recoleccion", "cereza": "recoleccion",
    # Beneficio
    "despulpar": "beneficio", "lavar cafe": "beneficio", "secar cafe": "beneficio",
    "beneficio": "beneficio", "trill": "beneficio",
    "despulp": "beneficio", "ferment": "beneficio",
    "canal de beneficio": "beneficio", "marquesina": "beneficio",
    "secadero": "beneficio", "máquina beneficios": "beneficio",
    # Administrativo
    "mayordomo": "administrativo", "administrad": "administrativo",
    "servicio": "administrativo", "impuesto": "administrativo",
    "predial": "administrativo", "herramienta": "administrativo",
    "transport": "administrativo", "vehiculo": "administrativo",
    "arriendo": "administrativo", "contador": "administrativo",
    "papelería": "administrativo", "seguro": "administrativo",
}

# Mapeo de palabras clave → categorías de ingreso
INGRESO_KEYWORDS = {
    "vend": "ingreso", "venta": "ingreso", "entreg": "ingreso",
    "cps": "cps", "pergamino": "cps",
    "pasilla": "pasilla",
}

# Mapeo de palabras → unidades
UNIDAD_KEYWORDS = {
    "jornal": "jornal", "jornale": "jornal", "dia": "jornal", "día": "jornal",
    "kilo": "kilo", "kg": "kilo", "kilogramo": "kilo",
    "litro": "litro", "lt": "litro",
    "unidad": "unidad", "unidade": "unidad",
    "hectarea": "hectarea", "hectárea": "hectarea", "ha": "hectarea",
    "carga": "carga",
}

# Números en español
NUMEROS = {
    "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50,
    "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
    "cien": 100, "dosciento": 200, "tresciento": 300, "quiniento": 500,
    "mil": 1000, "millon": 1000000, "millón": 1000000,
}


def transcribe_audio(audio_path: str) -> str:
    """Transcribe un archivo de audio usando Whisper local."""
    try:
        import whisper
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(audio_path, language="es")
        return result["text"].strip()
    except ImportError:
        logger.error("❌ Whisper no instalado. Ejecutá: pip install openai-whisper")
        return ""
    except Exception as e:
        logger.error(f"❌ Error transcribiendo audio: {e}")
        return ""


def parse_number(text: str) -> Optional[float]:
    """Extrae un número de un texto (soporta '40 mil', '3.5', 'cinco', etc.)."""
    text_lower = text.lower()

    # "X mil" pattern
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*mil', text_lower)
    if match:
        return float(match.group(1).replace(".", "").replace(",", ".")) * 1000

    # "X millones" pattern
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*millones?', text_lower)
    if match:
        return float(match.group(1).replace(".", "").replace(",", ".")) * 1000000

    # Buscar patrón de número con separador de miles colombiano: 1.500.000 o 1.500.000,50
    # Primero intentar formato colombiano: puntos como miles, coma como decimal
    match_col = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d+)?)', text.replace(" ", ""))
    if match_col:
        num_str = match_col.group(1).replace(".", "").replace(",", ".")
        return float(num_str)

    # Número normal (con punto como decimal)
    match = re.search(r'(\d+(?:\.\d+)?)', text.replace(",", "."))
    if match:
        return float(match.group(1))

    # Número en palabras
    for palabra, valor in NUMEROS.items():
        if palabra in text_lower:
            return float(valor)

    return None


def extract_fecha(text: str) -> str:
    """Extrae fecha del texto o retorna fecha de hoy."""
    from datetime import datetime, timedelta, timezone
    
    text_lower = text.lower()
    hoy = datetime.now(timezone.utc)
    
    if "ayer" in text_lower:
        return (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
    if "anteayer" in text_lower:
        return (hoy - timedelta(days=2)).strftime("%Y-%m-%d")
    if "semana pasada" in text_lower:
        return (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
    if "mes pasado" in text_lower:
        return (hoy - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Buscar patrón DD/MM/YYYY o DD-MM-YYYY
    match = re.search(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})', text)
    if match:
        d, m, y = match.groups()
        y = f"20{y}" if len(y) == 2 else y
        return f"{y}-{int(m):02d}-{int(d):02d}"
    
    # Buscar "el 15 de junio" etc
    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }
    for mes_nombre, mes_num in meses.items():
        if mes_nombre in text_lower:
            match = re.search(r'(\d{1,2})\s*de\s*' + mes_nombre, text_lower)
            if match:
                dia = int(match.group(1))
                return f"{hoy.year}-{mes_num:02d}-{dia:02d}"
    
    return hoy.strftime("%Y-%m-%d")


def extract_categoria(text: str) -> Optional[str]:
    """Determina la categoría basándose en palabras clave."""
    text_lower = text.lower()
    
    # Primero verificar si es ingreso (keywords más específicos)
    for keyword, cat in INGRESO_KEYWORDS.items():
        if keyword in text_lower:
            # Mapear keywords de ingreso a categorías DB
            ingreso_map = {
                "ingreso": None,  # genérico, no podemos determinar
                "cps": "ingreso_cps",
                "pasilla": "ingreso_pasilla",
            }
            mapped = ingreso_map.get(cat)
            if mapped:
                return mapped
            # Si es genérico "venta" → no podemos determinar subtipo
            return None
    
    # Luego verificar costos
    for keyword, cat in COSTO_KEYWORDS.items():
        if keyword in text_lower:
            return f"{cat}_mo"
    
    return None


def extract_unidad(text: str) -> str:
    """Extrae la unidad de medida del texto."""
    text_lower = text.lower()
    for keyword, unidad in UNIDAD_KEYWORDS.items():
        if keyword in text_lower:
            return unidad
    return "jornal"  # Default para caficultores


def extract_lote(text: str) -> str:
    """Extrae el nombre/número del lote del texto."""
    text_lower = text.lower()
    
    # Buscar "lote X", "en el lote X", etc.
    match = re.search(r'lote\s+(\w+)', text_lower)
    if match:
        return f"Lote {match.group(1)}"
    
    # Buscar "parcela X"
    match = re.search(r'parcela\s+(\w+)', text_lower)
    if match:
        return f"Parcela {match.group(1)}"
    
    return ""


def parse_voice_text(text: str) -> dict:
    """
    Parsea la transcripción de voz y extrae datos estructurados.
    Retorna un dict con los datos encontrados.
    """
    result = {
        "texto_original": text,
        "fecha": extract_fecha(text),
        "categoria": extract_categoria(text),
        "labor": "",
        "producto": "",
        "cantidad": None,
        "unidad": extract_unidad(text),
        "valor_unitario": None,
        "valor_total": None,
        "lote": extract_lote(text),
    }
    
    # Extraer cantidad
    cantidad = parse_number(text)
    if cantidad:
        result["cantidad"] = cantidad
    
    # Extraer valor (buscar patrones de dinero)
    # "a 40 mil", "por 40000", "a $40.000", etc.
    valor_match = re.search(r'(?:a|por|cada)\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:mil|millon)?', text.lower())
    if valor_match:
        valor = float(valor_match.group(1))
        if "mil" in text.lower() and valor < 1000:
            valor *= 1000
        result["valor_unitario"] = valor
    
    # Si hay cantidad y valor unitario, calcular total
    if result["cantidad"] and result["valor_unitario"]:
        result["valor_total"] = result["cantidad"] * result["valor_unitario"]
    
    # Extraer labor (descripción)
    # Tomar las primeras palabras significativas después de la categoría
    labor_patterns = [
        r'(?:hice|hicimos|pague|pagué|pagamos|trabajé|trabajamos)\s+(.+?)(?:\s+a\s+|\s+por\s+|\s+en\s+|$)',
        r'(?:guadañé|guadañamos|plateé|plateamos|fumigué|fumigamos)\s+(.+?)(?:\s+a\s+|\s+por\s+|$)',
    ]
    for pattern in labor_patterns:
        match = re.search(pattern, text.lower())
        if match:
            result["labor"] = match.group(1).strip()
            break
    
    return result


def format_parsed_data(data: dict) -> tuple:
    """
    Formatea los datos parseados para mostrar al usuario.
    Retorna (texto, keyboard) para usar con reply_markup.
    """
    lines = [
        "🎤 *Mensaje de voz recibido*",
        "",
    ]
    texto_original = data.get('texto_original', '')
    if len(texto_original) > 100:
        lines.append(f"📝 _\"{texto_original[:100]}...\"_")
    else:
        lines.append(f"📝 _\"{texto_original}_\"")
    lines.append("")
    lines.append("📊 *Datos extraídos:*")
    
    if data.get("fecha"):
        lines.append(f"📅 Fecha: {data['fecha']}")
    if data.get("categoria"):
        cat_nombre = data["categoria"].replace("_", " ").title()
        lines.append(f"🏷️ Categoría: {cat_nombre}")
    if data.get("labor"):
        lines.append(f"🔨 Labor: {data['labor']}")
    if data.get("cantidad"):
        unidad = data.get('unidad', '')
        lines.append(f"🔢 Cantidad: {data['cantidad']} {unidad}")
    if data.get("valor_unitario"):
        lines.append(f"💵 Valor unitario: ${data['valor_unitario']:,.0f}")
    if data.get("valor_total"):
        lines.append(f"💰 Valor total: ${data['valor_total']:,.0f}")
    if data.get("lote"):
        lines.append(f"🌱 {data['lote']}")
    
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
