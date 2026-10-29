import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import ConfigError, cargar_config

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def sin_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)


def test_lee_secret_key_del_env(tmp_path):
    env = tmp_path / ".env"
    env.write_text("SECRET_KEY=abc123\n")
    assert cargar_config(env).secret_key == "abc123"


def test_variable_de_entorno_tiene_prioridad_sobre_env(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("SECRET_KEY=del-archivo\n")
    monkeypatch.setenv("SECRET_KEY", "del-entorno")
    assert cargar_config(env).secret_key == "del-entorno"


@pytest.mark.parametrize("contenido", ["", "SECRET_KEY=\n", "SECRET_KEY=   \n"])
def test_rechaza_secret_key_faltante_o_vacia(tmp_path, contenido):
    env = tmp_path / ".env"
    env.write_text(contenido)
    with pytest.raises(ConfigError, match="SECRET_KEY"):
        cargar_config(env)


def test_ac73_la_app_no_arranca_sin_secret_key(tmp_path):
    """AC-73: sin SECRET_KEY, importar app.main (lo que hace uvicorn) falla."""
    codigo = (
        "import app.config as c, pathlib;"
        f"c.ARCHIVO_ENV = pathlib.Path({str(tmp_path / '.env')!r});"
        "import app.main"
    )
    entorno = {k: v for k, v in os.environ.items() if k != "SECRET_KEY"}
    resultado = subprocess.run(
        [sys.executable, "-c", codigo], cwd=RAIZ, env=entorno, capture_output=True, text=True
    )
    assert resultado.returncode != 0
    assert "ConfigError" in resultado.stderr
