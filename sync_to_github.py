#!/usr/bin/env python3
"""
sync_to_github.py — Sincroniza datos de clientes con GitHub
============================================================
Exporta datos de SQLite a JSON + Excel y los sube al repo privado.

Uso:
    source venv/bin/activate && python sync_to_github.py
    python sync_to_github.py --user-id 123456  # Solo un cliente
    python sync_to_github.py --dry-run         # Ver qué haría sin subir
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from config import EXPORTS_DIR, BASE_DIR
from database import Database
from excel_manager import ExcelManager

log = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Configuración GitHub ──
GITHUB_DATA_REPO = os.environ.get("GITHUB_DATA_REPO", "iglm/caficultor-datos")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def run(cmd: list[str], cwd: str = None, check: bool = True) -> subprocess.CompletedProcess:
    """Ejecutar comando shell."""
    log.info(f"💻 {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def clone_repo(temp_dir: str) -> str:
    """Clonar repo de datos en directorio temporal."""
    repo_dir = os.path.join(temp_dir, "data-repo")
    if GITHUB_TOKEN:
        url = f"https://{GITHUB_TOKEN}:x-oauth-basic@github.com/{GITHUB_DATA_REPO}.git"
    else:
        url = f"https://github.com/{GITHUB_DATA_REPO}.git"
    
    run(["git", "clone", "--depth=1", url, repo_dir])
    return repo_dir


def export_client(db: Database, user_id: int, username: str, repo_dir: str, em: ExcelManager):
    """Exportar datos de un cliente al repo."""
    # Obtener datos
    fincas = db.get_fincas(user_id)
    if not fincas:
        log.warning(f"⚠️ Usuario {user_id} sin fincas, saltando...")
        return
    
    # Crear estructura de datos
    finca_data = {
        "user_id": user_id,
        "username": username or "",
        "fincas": [],
        "last_sync": datetime.now(timezone.utc).isoformat(),
    }
    
    for finca in fincas:
        finca_id = finca["id"]
        lotes = db.get_lotes(finca_id)
        transacciones = db.get_all_transacciones(finca_id)
        resumen = db.get_resumen_finca(finca_id)
        
        finca_data["fincas"].append({
            **finca,
            "lotes": lotes,
            "transacciones": transacciones,
            "resumen": resumen,
        })
    
    # Crear carpeta del cliente
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (username or str(user_id)))
    client_dir = os.path.join(repo_dir, "clientes", f"{user_id}_{safe_name}")
    os.makedirs(client_dir, exist_ok=True)
    
    # Guardar JSON de finca
    with open(os.path.join(client_dir, "finca.json"), "w", encoding="utf-8") as f:
        json.dump(finca_data, f, indent=2, ensure_ascii=False, default=str)
    
    # Guardar JSON de transacciones
    all_trans = []
    for finca in fincas:
        all_trans.extend(db.get_all_transacciones(finca["id"]))
    
    with open(os.path.join(client_dir, "transacciones.json"), "w", encoding="utf-8") as f:
        json.dump(all_trans, f, indent=2, ensure_ascii=False, default=str)
    
    # Generar Excel
    excel_path = os.path.join(client_dir, "Costos de produccion - 2026.xlsx")
    for finca in fincas:
        em.generar_excel(finca["id"], db, excel_path)
        break  # Solo la primera finca por ahora
    
    # Generar README del cliente
    readme_content = _generate_readme(finca_data)
    with open(os.path.join(client_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    log.info(f"✅ Exportado cliente {user_id} ({username}) → {client_dir}")


def _generate_readme(data: dict) -> str:
    """Generar README.md para un cliente."""
    lines = [
        f"# ☕ Cliente: {data.get('username', data['user_id'])}",
        f"",
        f"**User ID:** `{data['user_id']}`",
        f"**Última sincronización:** {data.get('last_sync', 'N/A')}",
        f"",
    ]
    
    for finca in data.get("fincas", []):
        resumen = finca.get("resumen", {})
        lines.extend([
            f"## 🏡 {finca['nombre']}",
            f"",
            f"- **Departamento:** {finca.get('departamento', 'N/A')}",
            f"- **Región:** {finca.get('region', 'N/A')}",
            f"- **Área total:** {resumen.get('area_total', 0):.2f} hectáreas",
            f"",
            f"### 💰 Resumen Financiero",
            f"",
            f"| Concepto | Valor |",
            f"|----------|-------|",
            f"| Ingresos | ${resumen.get('ingresos', 0):,.0f} |",
            f"| Egresos | ${resumen.get('egresos', 0):,.0f} |",
            f"| **Margen** | **${resumen.get('margen', 0):,.0f}** |",
            f"| Costo/ha | ${resumen.get('costo_por_hectarea', 0):,.0f} |",
            f"",
        ])
        
        # Egresos por categoría
        egresos_cat = resumen.get("egresos_por_categoria", {})
        if egresos_cat:
            lines.extend([
                f"### 📉 Egresos por Categoría",
                f"",
                f"| Categoría | Valor |",
                f"|-----------|-------|",
            ])
            for cat, val in egresos_cat.items():
                if val > 0:
                    lines.append(f"| {cat.capitalize()} | ${val:,.0f} |")
            lines.append("")
        
        # Lotes
        lotes = finca.get("lotes", [])
        if lotes:
            lines.extend([
                f"### 🌱 Lotes",
                f"",
                f"| Lote | Area (ha) | Árboles | Variedad |",
                f"|------|-----------|----------|-----------|",
            ])
            for lote in lotes:
                lines.append(
                    f"| {lote['nombre']} | {lote.get('area_hectareas', 0)} | "
                    f"{lote.get('num_arboles', 0)} | {lote.get('variedad', 'N/A')} |"
                )
            lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sincroniza datos con GitHub")
    parser.add_argument("--user-id", type=int, help="Exportar solo un usuario")
    parser.add_argument("--dry-run", action="store_true", help="Sin subir cambios")
    args = parser.parse_args()
    
    db = Database()
    db.init_db()
    em = ExcelManager()
    
    # Obtener usuarios aprobados
    conn = db.get_conn()
    try:
        if args.user_id:
            users = conn.execute(
                "SELECT user_id, username FROM usuarios WHERE user_id = ? AND status='approved'",
                (args.user_id,)
            ).fetchall()
        else:
            users = conn.execute(
                "SELECT user_id, username FROM usuarios WHERE status='approved'"
            ).fetchall()
    finally:
        conn.close()
    
    if not users:
        log.warning("⚠️ Sin usuarios aprobados para exportar")
        return
    
    log.info(f"📤 Exportando {len(users)} clientes...")
    
    # Crear directorio temporal
    with tempfile.TemporaryDirectory() as temp_dir:
        # Clonar repo
        log.info(f"📥 Clonando repo {GITHUB_DATA_REPO}...")
        repo_dir = clone_repo(temp_dir)
        
        # Exportar cada cliente
        for user in users:
            export_client(db, user["user_id"], user["username"], repo_dir, em)
        
        if args.dry_run:
            log.info("🔍 DRY RUN - No se subieron cambios")
            return
        
        # Git add, commit, push
        run(["git", "config", "user.email", "bot@caficultor.local"], cwd=repo_dir)
        run(["git", "config", "user.name", "Bot Caficultor"], cwd=repo_dir)
        run(["git", "add", "-A"], cwd=repo_dir)
        
        # Solo commit si hay cambios
        status = run(["git", "status", "--porcelain"], cwd=repo_dir, check=False)
        if status.stdout.strip():
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            run(["git", "commit", "-m", f"📊 Sync automático — {timestamp}"], cwd=repo_dir)
            run(["git", "push", "origin", "main"], cwd=repo_dir)
            log.info("✅ Cambios subidos a GitHub")
        else:
            log.info("ℹ️ Sin cambios para subir")


if __name__ == "__main__":
    main()
