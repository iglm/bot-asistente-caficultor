#!/usr/bin/env python3
"""
Backup automático para SQLite (data/finca.db)
===============================================
- Crea backup con timestamp, comprime con gzip
- Verifica integridad del backup
- Mantiene solo los últimos 30 backups
- Log de cada operación en backup_db.log
- Usa exclusivamente stdlib de Python
"""

import sqlite3
import gzip
import shutil
import logging
import sys
from pathlib import Path
from datetime import datetime

# ─── Configuración ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "finca.db"
BACKUP_DIR = BASE_DIR / "backups"
LOG_FILE = BASE_DIR / "backup_db.log"
MAX_BACKUPS = 30
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("backup_db")


def ensure_backup_dir() -> Path:
    """Crea el directorio de backups si no existe."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Directorio de backups: %s", BACKUP_DIR)
    return BACKUP_DIR


def create_backup() -> tuple[Path, Path]:
    """
    1. Conecta a la DB en modo WAL y hace flush.
    2. Usa sqlite3.backup() para copia segura (sin locks largos).
    3. Comprime con gzip.
    4. Retorna (backup_gz_path, temp_db_path).
    """
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    temp_db = BACKUP_DIR / f"finca_{timestamp}.db"
    backup_gz = BACKUP_DIR / f"finca_{timestamp}.db.gz"

    # ── Backup con sqlite3.backup() ──────────────────────────────────────────
    logger.info("Iniciando backup de %s → %s", DB_PATH, temp_db.name)

    src_conn = sqlite3.connect(str(DB_PATH))
    try:
        # Forzar checkpoint en WAL
        src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        dst_conn = sqlite3.connect(str(temp_db))
        try:
            with dst_conn:
                src_conn.backup(dst_conn, pages=-1)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    if not temp_db.exists():
        raise RuntimeError("El archivo de backup temporal no se creó.")

    db_size = temp_db.stat().st_size
    logger.info("Backup temporal creado: %s (%d bytes)", temp_db.name, db_size)

    # ── Compresión gzip ──────────────────────────────────────────────────────
    logger.info("Comprimiendo con gzip...")
    with open(temp_db, "rb") as f_in:
        with gzip.open(backup_gz, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    gz_size = backup_gz.stat().st_size
    logger.info("Backup comprimido: %s (%d bytes, ratio %.1f%%)",
                backup_gz.name, gz_size, (gz_size / db_size * 100) if db_size else 0)

    # Eliminar el temporal sin comprimir
    temp_db.unlink()
    logger.debug("Archivo temporal eliminado: %s", temp_db.name)

    return backup_gz, temp_db


def verify_backup(backup_gz: Path) -> bool:
    """
    Descomprime el backup a un archivo temporal y ejecuta
    PRAGMA integrity_check. Retorna True si es íntegro.
    """
    logger.info("Verificando integridad del backup: %s", backup_gz.name)

    temp_verify = backup_gz.with_suffix(".verify_tmp")
    try:
        # Descomprimir
        with gzip.open(backup_gz, "rb") as f_in:
            with open(temp_verify, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Verificar
        conn = sqlite3.connect(str(temp_verify))
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check")
            result = cur.fetchone()[0]
            if result == "ok":
                logger.info("✅ Integridad verificada: OK")
                return True
            else:
                logger.error("❌ Integridad: %s", result)
                return False
        finally:
            conn.close()
    except Exception as e:
        logger.error("❌ Error durante verificación: %s", e)
        return False
    finally:
        # Limpiar temporal
        if temp_verify.exists():
            temp_verify.unlink()


def cleanup_old_backups(max_backups: int = MAX_BACKUPS):
    """
    Mantiene solo los últimos `max_backups` backups (por fecha de modificación).
    Elimina el resto.
    """
    backups = sorted(BACKUP_DIR.glob("finca_*.db.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(backups) <= max_backups:
        logger.info("Backups actuales: %d (máx. %d, no se requiere limpieza)",
                     len(backups), max_backups)
        return

    to_delete = backups[max_backups:]
    logger.info("Backups actuales: %d, eliminando %d antiguos...",
                len(backups), len(to_delete))

    for old in to_delete:
        old.unlink()
        logger.info("  Eliminado: %s", old.name)


def main():
    logger.info("=" * 60)
    logger.info("INICIO DE BACKUP — %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # Validar DB origen
    if not DB_PATH.exists():
        logger.error("❌ Base de datos no encontrada: %s", DB_PATH)
        sys.exit(1)

    try:
        # Prueba de conexión a la DB origen
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("SELECT 1")
        conn.close()
    except sqlite3.Error as e:
        logger.error("❌ No se puede conectar a la DB origen: %s", e)
        sys.exit(1)

    # 1. Crear directorio
    ensure_backup_dir()

    # 2. Backup + compresión
    backup_gz, _ = create_backup()

    # 3. Verificar integridad
    if not verify_backup(backup_gz):
        logger.error("❌ El backup NO pasó la verificación de integridad. Eliminando...")
        if backup_gz.exists():
            backup_gz.unlink()
        sys.exit(1)

    # 4. Limpiar backups viejos
    cleanup_old_backups()

    logger.info("✅ BACKUP COMPLETADO EXITOSAMENTE: %s", backup_gz.name)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
