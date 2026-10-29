import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.modelos import Socio
from app.socios import SocioInvalido, alta_socio

RAIZ = Path(__file__).resolve().parent.parent


def _cantidad(sesion):
    return sesion.scalar(select(func.count()).select_from(Socio))


def test_ac58_crea_el_socio(sesion):
    alta_socio(sesion, "José", "jose@empresa.com")
    socio = sesion.scalar(select(Socio))
    assert (socio.nombre, socio.mail) == ("José", "jose@empresa.com")


@pytest.mark.parametrize("mail", ["", "   "])
def test_ac41_rechaza_un_socio_sin_mail(sesion, mail):
    with pytest.raises(SocioInvalido, match="tiene que tener mail"):
        alta_socio(sesion, "José", mail)
    assert _cantidad(sesion) == 0


def test_ac59_rechaza_un_mail_repetido_sin_distinguir_mayusculas(sesion):
    alta_socio(sesion, "José", "jose@empresa.com")
    with pytest.raises(SocioInvalido, match="Ya existe un socio con el mail jose@empresa.com"):
        alta_socio(sesion, "Otro José", "JOSE@empresa.com")
    assert _cantidad(sesion) == 1


def test_el_mail_se_guarda_en_minusculas_y_sin_espacios(sesion):
    assert alta_socio(sesion, "José", "  Jose@Empresa.com ").mail == "jose@empresa.com"


def test_no_valida_el_formato_del_mail(sesion):
    # FA-06: el formato del mail no se valida.
    assert alta_socio(sesion, "José", "jose").mail == "jose"


def test_admite_varios_socios_con_mails_distintos(sesion):
    alta_socio(sesion, "José", "jose@empresa.com")
    alta_socio(sesion, "Ana", "ana@empresa.com")
    assert _cantidad(sesion) == 2


def _correr(args, url_base):
    entorno = {**os.environ, "DATABASE_URL": url_base}
    return subprocess.run([sys.executable, "-m", *args], cwd=RAIZ, env=entorno, capture_output=True, text=True)


def test_ac58_ac59_ac41_alta_por_consola_sobre_la_base_migrada(tmp_path):
    archivo = tmp_path / "test.db"
    url_base = f"sqlite:///{archivo}"
    assert _correr(["alembic", "upgrade", "head"], url_base).returncode == 0

    alta = _correr(["app.socios", "alta", "José", "jose@empresa.com"], url_base)
    assert alta.returncode == 0, alta.stderr
    assert "jose@empresa.com" in alta.stdout

    repetido = _correr(["app.socios", "alta", "Otro", "JOSE@empresa.com"], url_base)
    assert repetido.returncode == 1
    assert "Ya existe un socio con el mail jose@empresa.com" in repetido.stderr

    sin_mail = _correr(["app.socios", "alta", "Ana", ""], url_base)
    assert sin_mail.returncode == 1
    assert "tiene que tener mail" in sin_mail.stderr

    falta_el_argumento = _correr(["app.socios", "alta", "Ana"], url_base)
    assert falta_el_argumento.returncode != 0

    with sqlite3.connect(archivo) as conexion:
        assert conexion.execute("SELECT nombre, mail FROM socios").fetchall() == [("José", "jose@empresa.com")]
