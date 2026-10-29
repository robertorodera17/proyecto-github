import pytest

from app import sesion as sesion_web
from app.main import RUTAS_PUBLICAS
from app.operadores import alta_operador, definir_password

PASSWORD = "secreta123"
MINUTO = 60


class Reloj:
    def __init__(self):
        self.segundos = 1_000_000.0

    def __call__(self):
        return self.segundos

    def avanzar(self, minutos):
        self.segundos += minutos * MINUTO


@pytest.fixture
def reloj(monkeypatch):
    r = Reloj()
    monkeypatch.setattr(sesion_web, "ahora", r)
    return r


@pytest.fixture
def logueado(cliente, sesion, reloj):
    """Cliente con sesión iniciada como JP."""
    operador = alta_operador(sesion, "JP", "Juan", "juan@empresa.com")
    definir_password(sesion, operador, PASSWORD)
    respuesta = cliente.post("/login/ingresar", data={"sigla": "JP", "password": PASSWORD}, follow_redirects=False)
    assert respuesta.status_code == 303
    return cliente


def _va_al_login(respuesta):
    return respuesta.status_code == 303 and respuesta.headers["location"] == "/login"


# --- RF-21: sin sesión, solo el login ---

@pytest.mark.parametrize(
    "metodo, ruta",
    [
        ("get", "/"),
        ("get", "/movimientos"),
        ("post", "/movimientos"),
        ("post", "/movimientos/1"),
        ("post", "/movimientos/1/eliminar"),
        ("get", "/docs"),
        ("get", "/openapi.json"),
        ("post", "/logout"),
    ],
)
def test_ac38_sin_sesion_cualquier_ruta_va_al_login(cliente, metodo, ruta):
    respuesta = getattr(cliente, metodo)(ruta, follow_redirects=False)
    assert _va_al_login(respuesta)


def test_las_rutas_publicas_son_solo_las_del_login():
    assert RUTAS_PUBLICAS == {"/login", "/login/sigla", "/login/definir", "/login/ingresar"}


def test_el_login_se_ve_sin_sesion(cliente):
    assert cliente.get("/login").status_code == 200


def test_pedido_htmx_sin_sesion_redirige_la_pagina_entera(cliente):
    respuesta = cliente.get("/", headers={"HX-Request": "true"}, follow_redirects=False)
    assert respuesta.status_code == 200
    assert respuesta.headers["HX-Redirect"] == "/login"


def test_con_sesion_entra(logueado):
    respuesta = logueado.get("/", follow_redirects=False)
    assert respuesta.status_code == 200
    assert "Cerrar sesión" in respuesta.text


# --- RNF-03 y RF-34: vencimiento por inactividad ---

def test_ac55_con_59_minutos_de_inactividad_sigue_adentro(logueado, reloj):
    reloj.avanzar(59)
    assert logueado.get("/", follow_redirects=False).status_code == 200


def test_ac40_a_los_60_minutos_justos_va_al_login(logueado, reloj):
    reloj.avanzar(60)
    assert _va_al_login(logueado.get("/", follow_redirects=False))


def test_ac56_el_login_avisa_que_la_sesion_vencio(logueado, reloj):
    reloj.avanzar(60)
    respuesta = logueado.get("/")  # sigue el redirect al login
    assert "Tu sesión venció por inactividad" in respuesta.text
    # El aviso se muestra una sola vez.
    assert "venció" not in logueado.get("/login").text


def test_cada_accion_renueva_el_plazo(logueado, reloj):
    reloj.avanzar(59)
    assert logueado.get("/", follow_redirects=False).status_code == 200
    reloj.avanzar(59)
    assert logueado.get("/", follow_redirects=False).status_code == 200


def test_los_pedidos_htmx_tambien_renuevan_el_plazo(logueado, reloj):
    reloj.avanzar(59)
    logueado.get("/", headers={"HX-Request": "true"})
    reloj.avanzar(59)
    assert logueado.get("/", follow_redirects=False).status_code == 200


def test_pedido_htmx_con_sesion_vencida_redirige_la_pagina_entera(logueado, reloj):
    reloj.avanzar(60)
    respuesta = logueado.get("/", headers={"HX-Request": "true"}, follow_redirects=False)
    assert respuesta.headers["HX-Redirect"] == "/login"


def test_sin_aviso_de_vencida_si_nunca_hubo_sesion(cliente):
    assert "venció" not in cliente.get("/login").text


# --- RF-32: cerrar sesión ---

def test_ac57_cerrar_sesion_lleva_al_login_y_no_deja_volver(logueado):
    respuesta = logueado.post("/logout", follow_redirects=False)
    assert _va_al_login(respuesta)
    assert _va_al_login(logueado.get("/", follow_redirects=False))
    assert "venció" not in logueado.get("/login").text
