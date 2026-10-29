import pytest
from sqlalchemy import select

from app import seguridad
from app.modelos import Operador
from app.operadores import alta_operador, definir_password

PASSWORD = "secreta123"


@pytest.fixture
def sin_password(sesion):
    return alta_operador(sesion, "RO", "Rocío", "rocio@empresa.com")


@pytest.fixture
def con_password(sesion):
    operador = alta_operador(sesion, "JP", "Juan", "juan@empresa.com")
    definir_password(sesion, operador, PASSWORD)
    return operador


def _hash_guardado(sesion, sigla):
    sesion.expire_all()
    return sesion.scalar(select(Operador.password_hash).where(Operador.sigla == sigla))


def _definir(cliente, sigla, password, repetir=None, **kwargs):
    """Define la contraseña repitiéndola igual, salvo que se indique otra cosa."""
    datos = {"sigla": sigla, "password": password, "repetir": password if repetir is None else repetir}
    return cliente.post("/login/definir", data=datos, **kwargs)


def _entro(cliente):
    """Accede a la pantalla principal sin que lo manden al login."""
    respuesta = cliente.get("/", follow_redirects=False)
    return respuesta.status_code == 200


# --- Paso de la sigla ---

def test_ac54_sigla_inexistente_avisa_y_no_pide_contrasena(cliente):
    respuesta = cliente.post("/login/sigla", data={"sigla": "XX"})
    assert "No existe un operador con la sigla XX" in respuesta.text
    assert 'type="password"' not in respuesta.text


def test_ac35_sin_contrasena_pide_definirla(cliente, sin_password):
    respuesta = cliente.post("/login/sigla", data={"sigla": "RO"})
    assert respuesta.status_code == 200
    assert 'action="/login/definir"' in respuesta.text
    assert not _entro(cliente)


def test_con_contrasena_la_pide(cliente, con_password):
    respuesta = cliente.post("/login/sigla", data={"sigla": "JP"})
    assert 'action="/login/ingresar"' in respuesta.text


def test_la_sigla_no_distingue_mayusculas(cliente, con_password):
    respuesta = cliente.post("/login/sigla", data={"sigla": " jp "})
    assert 'action="/login/ingresar"' in respuesta.text


# --- Definir la contraseña en el primer ingreso ---

def test_ac53_rechaza_contrasena_de_7_caracteres(cliente, sesion, sin_password):
    respuesta = _definir(cliente, "RO", "a" * 7)
    assert respuesta.status_code == 400
    assert "al menos 8 caracteres" in respuesta.text
    assert _hash_guardado(sesion, "RO") is None
    assert not _entro(cliente)


def test_ac98_acepta_contrasena_de_8_caracteres(cliente, sin_password):
    respuesta = _definir(cliente, "RO", "a" * 8, follow_redirects=False)
    assert respuesta.status_code == 303
    assert _entro(cliente)


def test_ac72_acepta_72_bytes_y_despues_ingresa_con_ella(cliente, sin_password):
    password = "a" * 72
    _definir(cliente, "RO", password)
    cliente.cookies.clear()
    assert not _entro(cliente)

    respuesta = cliente.post("/login/ingresar", data={"sigla": "RO", "password": password}, follow_redirects=False)
    assert respuesta.status_code == 303
    assert _entro(cliente)


def test_ac86_rechaza_73_bytes_con_mensaje(cliente, sesion, sin_password):
    respuesta = _definir(cliente, "RO", "a" * 73)
    assert respuesta.status_code == 400
    assert "hasta 72 bytes" in respuesta.text
    assert _hash_guardado(sesion, "RO") is None
    assert not _entro(cliente)


def test_ac103_rechaza_si_las_contrasenas_no_coinciden(cliente, sesion, sin_password):
    respuesta = _definir(cliente, "RO", "secreta123", repetir="secreta124")
    assert respuesta.status_code == 400
    assert "Las contraseñas no coinciden" in respuesta.text
    assert _hash_guardado(sesion, "RO") is None
    assert not _entro(cliente)


def test_el_formulario_de_primer_ingreso_pide_repetirla(cliente, sin_password):
    respuesta = cliente.post("/login/sigla", data={"sigla": "RO"})
    assert 'name="repetir"' in respuesta.text


def test_cuenta_bytes_y_no_caracteres(cliente, sin_password):
    # 37 "ñ" son 37 caracteres pero 74 bytes en UTF-8.
    respuesta = _definir(cliente, "RO", "ñ" * 37)
    assert respuesta.status_code == 400


def test_ac52_no_se_puede_redefinir_una_contrasena(cliente, sesion, con_password):
    antes = _hash_guardado(sesion, "JP")
    respuesta = _definir(cliente, "JP", "otra-clave-nueva")
    assert respuesta.status_code == 409
    assert _hash_guardado(sesion, "JP") == antes
    assert not _entro(cliente)


def test_ac52_el_servicio_tambien_lo_rechaza(sesion, con_password):
    from app.operadores import PasswordYaDefinida

    with pytest.raises(PasswordYaDefinida):
        definir_password(sesion, con_password, "otra-clave-nueva")
    assert seguridad.verificar(PASSWORD, _hash_guardado(sesion, "JP"))


# --- Ingresar con contraseña ---

def test_ac36_sigla_y_contrasena_correctas_acceden(cliente, con_password):
    respuesta = cliente.post("/login/ingresar", data={"sigla": "jp", "password": PASSWORD})
    assert respuesta.status_code == 200
    assert "<h1>Movimientos</h1>" in respuesta.text
    assert "Juan (JP)" in respuesta.text


def test_ac37_contrasena_incorrecta_no_accede(cliente, con_password):
    respuesta = cliente.post("/login/ingresar", data={"sigla": "JP", "password": "incorrecta"})
    assert respuesta.status_code == 401
    assert "Contraseña incorrecta" in respuesta.text
    assert not _entro(cliente)


# --- Hash (RNF-02) ---

def test_ac44_ac95_se_guarda_hash_bcrypt_con_costo_12(sesion, con_password):
    guardado = _hash_guardado(sesion, "JP")
    assert PASSWORD not in guardado
    assert guardado.startswith("$2b$12$")
