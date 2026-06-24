#!/usr/bin/env python3
"""
Script de auditoría preciso de callbacks vs handlers.

Usa lógica startswith() para verificar que TODOS los callbacks
tienen su handler correspondiente — sin falsos positivos.
"""
import re
import os
import sys
from pathlib import Path

HANDLERS_DIR = Path("/home/lucas-mateo/bot-asistente-caficultor/handlers")


def extract_callbacks(content: str, fname: str) -> list[dict]:
    """Extrae callback_data definidos en botones InlineKeyboardButton."""
    callbacks = []
    # Busca callback_data="..." y callback_data=f"..." — maneja comillas anidadas
    for m in re.finditer(
        r'callback_data\s*=\s*[fF]?(["\'])((?:(?!\1).)*?)\1',
        content,
    ):
        cb = m.group(2)
        line = content[:m.start()].count('\n') + 1
        callbacks.append({'callback': cb, 'file': fname, 'line': line})
    return callbacks


def extract_handlers(content: str, fname: str) -> tuple[list[dict], list[dict]]:
    """Extrae handlers de callbacks: startswith patterns y exact match patterns."""
    startswith_handlers = []
    exact_handlers = []

    # Buscar F.data.startswith("xxx") — permite args extras antes/después
    for m in re.finditer(
        r'@router\.callback_query\([^)]*?F\.data\.startswith\(["\']([^"\']+)["\'][^)]*\)',
        content,
    ):
        prefix = m.group(1)
        line = content[:m.start()].count('\n') + 1
        startswith_handlers.append({'prefix': prefix, 'file': fname, 'line': line})

    # Buscar F.data == "xxx" — permite args extras antes/después
    for m in re.finditer(
        r'@router\.callback_query\([^)]*?F\.data\s*==\s*["\']([^"\']+)["\'][^)]*\)',
        content,
    ):
        cb = m.group(1)
        line = content[:m.start()].count('\n') + 1
        exact_handlers.append({'callback': cb, 'file': fname, 'line': line})

    return startswith_handlers, exact_handlers


def callback_matches_handler(callback: str, startswith_handlers: list, exact_handlers: list) -> bool:
    """Verifica si un callback tiene un handler que lo captura."""
    # 1. Exact match
    for h in exact_handlers:
        if callback == h['callback']:
            return True

    # 2. startswith match
    for h in startswith_handlers:
        if callback.startswith(h['prefix']):
            return True

    return False


def callback_is_dynamic(callback: str) -> bool:
    """Detecta si un callback tiene formato dinámico (contiene {expresion})."""
    return '{' in callback and '}' in callback


def find_unhandled_callbacks():
    """Encuentra callbacks sin handler. Retorna (reales, dinámicos/falsos)."""
    all_callbacks = []
    all_startswith_handlers = []
    all_exact_handlers = []

    for fname in sorted(os.listdir(HANDLERS_DIR)):
        if not fname.endswith('.py') or fname == '__init__.py':
            continue
        content = (HANDLERS_DIR / fname).read_text(encoding='utf-8')

        cbs = extract_callbacks(content, fname)
        all_callbacks.extend(cbs)

        sw_handlers, ex_handlers = extract_handlers(content, fname)
        all_startswith_handlers.extend(sw_handlers)
        all_exact_handlers.extend(ex_handlers)

    unhandled_real = []
    unhandled_dynamic = []

    for cb_info in all_callbacks:
        cb = cb_info['callback']
        if callback_is_dynamic(cb):
            unhandled_dynamic.append(cb_info)
            continue
        if not callback_matches_handler(cb, all_startswith_handlers, all_exact_handlers):
            unhandled_real.append(cb_info)

    return unhandled_real, unhandled_dynamic, all_startswith_handlers, all_exact_handlers, all_callbacks


def find_orphan_handlers(all_startswith_handlers: list, all_exact_handlers: list, all_callbacks: list) -> list[dict]:
    """Encuentra handlers que nunca capturan ningún callback (código muerto)."""
    orphan = []

    for h in all_exact_handlers:
        if not any(cb['callback'] == h['callback'] for cb in all_callbacks):
            orphan.append(h)

    for h in all_startswith_handlers:
        prefix = h['prefix']
        if not any(cb['callback'].startswith(prefix) for cb in all_callbacks):
            orphan.append(h)

    return orphan


def main():
    print("=" * 72)
    print("  AUDITORÍA DE CALLBACKS vs HANDLERS — Asistente Caficultor")
    print("=" * 72)

    result = find_unhandled_callbacks()
    unhandled_real, unhandled_dynamic, sw_handlers, ex_handlers, all_callbacks = result

    print(f"\n📊  ESTADÍSTICAS:")
    print(f"     Callbacks en botones:     {len(all_callbacks)}")
    print(f"     Handlers exact match:     {len(ex_handlers)}")
    print(f"     Handlers startswith:      {len(sw_handlers)}")
    print(f"     Callbacks dinámicos (f):  {len(unhandled_dynamic)}")

    # ── Handlers exact match ──
    print(f"\n📋  HANDLERS EXACT MATCH (F.data == \"xxx\"):")
    for h in sorted(ex_handlers, key=lambda x: x['callback']):
        print(f"     ✅ {h['callback']:<35} en {h['file']}:{h['line']}")

    # ── Handlers startswith ──
    print(f"\n📋  HANDLERS STARTSWITH (F.data.startswith(\"xxx\")):")
    for h in sorted(sw_handlers, key=lambda x: x['prefix']):
        print(f"     ✅ {h['prefix']:<35} en {h['file']}:{h['line']}")

    # ── Callbacks sin handler ──
    print(f"\n{'=' * 72}")
    print(f"  RESULTADO DE AUDITORÍA")
    print(f"{'=' * 72}")

    if unhandled_real:
        print(f"\n❌  CALLBACKS SIN HANDLER ({len(unhandled_real)}):")
        for cb in unhandled_real:
            print(f"     🔴 {cb['callback']:<40} en {cb['file']}:{cb['line']}")
        print("\n⚠️  Estos callbacks NO tienen un handler que los capture.")
        print("   Es necesario agregar handlers o verificar si son falsos positivos.\n")
    else:
        print(f"\n✅  ¡TODOS LOS CALLBACKS TIENEN SU HANDLER! 0 pendientes.\n")

    # ── Orphan handlers ──
    orphan = find_orphan_handlers(sw_handlers, ex_handlers, all_callbacks)
    if orphan:
        print(f"⚠️  HANDLERS QUE NUNCA CAPTURAN CALLBACKS (código muerto, {len(orphan)}):")
        for h in orphan:
            if 'prefix' in h:
                print(f"     💀 startswith(\"{h['prefix']}\") en {h['file']}:{h['line']}")
            else:
                print(f"     💀 F.data == \"{h['callback']}\" en {h['file']}:{h['line']}")
        print()
    else:
        print("✅  Todos los handlers capturan al menos un callback.\n")

    # ── Detalle de callbacks dinámicos ──
    if unhandled_dynamic:
        print(f"ℹ️  CALLBACKS DINÁMICOS (contienen {{}}) — se ignoran en auditoría:")
        for cb in unhandled_dynamic:
            print(f"     {cb['callback']:<40} en {cb['file']}:{cb['line']}")
        print()

    # ── Mapa de cobertura ──
    print("📋  MAPA DE COBERTURA POR PREFIJO STARTSWITH:")
    covered_by_prefix = {}
    for h in sw_handlers:
        matches = [cb for cb in all_callbacks if cb['callback'].startswith(h['prefix'])]
        covered_by_prefix[h['prefix']] = matches
        for cb in matches:
            covered_by_prefix.setdefault(h['prefix'], [])

    for prefix in sorted(covered_by_prefix.keys()):
        matches = covered_by_prefix[prefix]
        if matches:
            examples = [m['callback'].replace(prefix, f"{prefix}[...]")[:50] for m in matches[:3]]
            print(f"     ✅ startswith(\"{prefix}\") → {len(matches)} callbacks: {', '.join(examples)}")
        else:
            print(f"     ❌ startswith(\"{prefix}\") → 0 callbacks (código muerto)")

    return len(unhandled_real)


if __name__ == "__main__":
    exit(main())
