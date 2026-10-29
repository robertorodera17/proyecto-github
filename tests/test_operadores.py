import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.modelos import Operador
from app.operadores import OperadorDuplicado, alta_operador

RAIZ = Path(__file__).resolve().parent.parent


def test_ac96_guarda_sigla_nombre_y_mail(sesion):
    alta_operador(sesion, "JP", "Juan", "juan@empresa.com")
    operador = sesion.scalar(select(Operador))
    assert (operador.sigla, operador.nombre, operador.mail) == ("JP", "Juan", "juan@empresa.com")


def test_ac51_se_crea_sin_contrasena(sesion):
    operador = alta_operador(sesion, "JP", "Juan", "juan@empresa.com")
    assert operador.password_hash is None


def test_la_sigla_se_guarda_en_mayusculas(sesion):
    assert alta_operador(sesion, " ro ", "Rocío", "rocio@empresa.com").sigla == "RO"


@pytest.mark.parametrize("sigla_repetida", ["RO", "ro", "Ro"])
def test_ac34_ac50_rechaza_sigla_repetida_sin_distinguir_mayusculas(sesion, sigla_repetida):
    alta_operador(sesion, "RO", "Rocío", "rocio@empresa.com")
    with pytest.raises(OperadorDuplicado, match="RO"):
        alta_operador(sesion, sigla_repetida, "Otra", "otra@empresa.com")
    assert sesion.scalar(select(func.count()).select_from(Operador)) == 1


def _correr(args, url_base):
    entorno = {**os.environ, "DATABASE_URL": url_base}
    return subprocess.run(
        [sys.executable, "-m", *args], cwd=RAIZ, env=entorno, capture_output=True, text=True
    )


def test_ac51_ac96_alta_por_consola_sobre_la_base_migrada(tmp_path):
    archivo = tmp_path / "test.db"
    url_base = f"sqlite:///{archivo}"
    migracion = _correr(["alembic", "upgrade", "head"], url_base)
    assert migracion.returncode == 0, migracion.stderr

    alta = _correr(["app.operadores", "alta", "JP", "Juan", "juan@empresa.com"], url_base)
    assert alta.returncode == 0, alta.stderr
    assert "JP" in alta.stdout

    repetida = _correr(["app.operadores", "alta", "jp", "Otro", "otro@empresa.com"], url_base)
    assert repetida.returncode == 1
    assert "Ya existe un operador con la sigla JP" in repetida.stderr

    with sqlite3.connect(archivo) as conexion:
        filas = conexion.execute("SELECT sigla, nombre, mail, password_hash FROM operadores").fetchall()
    assert filas == [("JP", "Juan", "juan@empresa.com", None)]
