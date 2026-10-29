import os
import subprocess
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

import app.modelos  # noqa: F401  registra las tablas en Base.metadata
from app.db import Base

RAIZ = Path(__file__).resolve().parent.parent


def _alembic(*args, url_base):
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=RAIZ, env={**os.environ, "DATABASE_URL": url_base}, capture_output=True, text=True,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_las_migraciones_coinciden_con_los_modelos(tmp_path):
    """Si falla, falta generar una migración: `alembic revision --autogenerate -m "..."`."""
    url_base = f"sqlite:///{tmp_path / 'test.db'}"
    _alembic("upgrade", "head", url_base=url_base)
    engine = create_engine(url_base)
    with engine.connect() as conexion:
        diferencias = compare_metadata(MigrationContext.configure(conexion), Base.metadata)
    engine.dispose()
    assert diferencias == []


def test_las_migraciones_se_pueden_deshacer(tmp_path):
    url_base = f"sqlite:///{tmp_path / 'test.db'}"
    _alembic("upgrade", "head", url_base=url_base)
    _alembic("downgrade", "base", url_base=url_base)
