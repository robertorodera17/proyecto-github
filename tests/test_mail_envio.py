import logging
import os
import smtplib
import socket
import subprocess
import sys
from datetime import date
from email import message_from_bytes, policy
from pathlib import Path

import pytest
from aiosmtpd.controller import Controller

from app import mail
from app.modelos import Movimiento
from app.socios import alta_socio

RAIZ = Path(__file__).resolve().parent.parent
HOY = date(2026, 10, 21)


class Buzon:
    """Handler de aiosmtpd: guarda cada mail y rechaza las direcciones indicadas."""

    def __init__(self):
        self.recibidos = []  # (destinatarios del sobre, mensaje)
        self.rechazar = set()

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if address in self.rechazar:
            return "550 5.1.1 Direccion inexistente"
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        self.recibidos.append((list(envelope.rcpt_tos), message_from_bytes(envelope.content, policy=policy.default)))
        return "250 OK"


def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def buzon(monkeypatch):
    handler = Buzon()
    controlador = Controller(handler, hostname="127.0.0.1", port=_puerto_libre())
    controlador.start()
    for clave, valor in {
        "SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(controlador.port), "SMTP_USER": "", "SMTP_PASSWORD": "",
        "SMTP_FROM": "app@empresa.com", "SMTP_SEGURIDAD": "ninguna",
    }.items():
        monkeypatch.setenv(clave, valor)
    yield handler
    controlador.stop()


@pytest.fixture
def dos_socios(sesion):
    alta_socio(sesion, "José", "jose@empresa.com")
    alta_socio(sesion, "Ana", "ana@empresa.com")


def _mov(sesion, descripcion, fecha=HOY, eliminado=False):
    sesion.add(Movimiento(descripcion=descripcion, tipo="Egreso", monto=-1200, clasificacion="SUELDOS",
                          fecha=fecha, eliminado=eliminado))
    sesion.commit()


# --- Destinatarios (RF-36) ---

def test_ac60_un_mail_por_socio_con_un_solo_destinatario(sesion, buzon, dos_socios):
    resultado = mail.enviar(sesion, HOY)
    assert resultado.ok
    assert [(sobre, m["To"]) for sobre, m in buzon.recibidos] == [
        (["jose@empresa.com"], "jose@empresa.com"),
        (["ana@empresa.com"], "ana@empresa.com"),
    ]


def test_ac61_si_rechazan_al_primero_el_segundo_lo_recibe_y_queda_en_el_log(sesion, buzon, dos_socios, caplog):
    buzon.rechazar.add("jose@empresa.com")
    with caplog.at_level(logging.ERROR, logger="app.mail"):
        resultado = mail.enviar(sesion, HOY)
    assert [sobre for sobre, _ in buzon.recibidos] == [["ana@empresa.com"]]
    assert (resultado.enviados, resultado.fallidos) == (["ana@empresa.com"], ["jose@empresa.com"])
    assert "jose@empresa.com" in caplog.text and "550" in caplog.text


# --- Contenido (RF-24) ---

def test_ac42_solo_va_el_movimiento_de_hoy_no_eliminado(sesion, buzon, dos_socios):
    _mov(sesion, "De hoy")
    _mov(sesion, "De hoy eliminado", eliminado=True)
    _mov(sesion, "De ayer", fecha=date(2026, 10, 20))
    mail.enviar(sesion, HOY)
    texto = buzon.recibidos[0][1].get_content()
    assert "De hoy |" in texto
    assert "eliminado" not in texto and "De ayer" not in texto


def test_ac66_el_envio_de_otra_fecha_lleva_esa_fecha_y_sus_movimientos(sesion, buzon, dos_socios):
    _mov(sesion, "Del 10", fecha=date(2026, 10, 10))
    _mov(sesion, "De hoy")
    mail.enviar(sesion, date(2026, 10, 10))
    recibido = buzon.recibidos[0][1]
    assert recibido["Subject"] == "Movimientos del 10/10/2026"
    assert "Del 10 |" in recibido.get_content() and "De hoy" not in recibido.get_content()


def test_ac62_sin_movimientos_igual_manda_el_mail(sesion, buzon, dos_socios):
    mail.enviar(sesion, HOY)
    assert len(buzon.recibidos) == 2
    assert "No hubo movimientos." in buzon.recibidos[0][1].get_content()


def test_ac101_llega_como_texto_plano_de_una_sola_parte(sesion, buzon, dos_socios):
    mail.enviar(sesion, HOY)
    recibido = buzon.recibidos[0][1]
    assert not recibido.is_multipart() and recibido.get_content_type() == "text/plain"


# --- Errores (RF-55, RF-56) ---

def test_ac78_servidor_caido_queda_en_el_log_sin_reintentar(sesion, dos_socios, monkeypatch, caplog):
    for clave, valor in {"SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(_puerto_libre()), "SMTP_USER": "",
                         "SMTP_PASSWORD": "", "SMTP_FROM": "app@empresa.com", "SMTP_SEGURIDAD": "ninguna"}.items():
        monkeypatch.setenv(clave, valor)
    intentos = []
    conectar = mail._conectar
    monkeypatch.setattr(mail, "_conectar", lambda config: intentos.append(1) or conectar(config))
    with caplog.at_level(logging.ERROR, logger="app.mail"):
        resultado = mail.enviar(sesion, HOY)
    assert resultado.fallidos == ["jose@empresa.com", "ana@empresa.com"]
    assert len(intentos) == 2  # uno por socio, sin reintentos (RF-56)
    assert caplog.text.count("no se pudo conectar con el servidor de correo") == 2


@pytest.mark.parametrize(
    "variables, falta",
    [
        ({"SMTP_HOST": ""}, "SMTP_HOST"),
        ({"SMTP_FROM": "", "SMTP_USER": ""}, "SMTP_FROM"),
        ({"SMTP_USER": "cuenta@gmail.com", "SMTP_PASSWORD": ""}, "SMTP_PASSWORD"),
        ({"SMTP_SEGURIDAD": "tls"}, "SMTP_SEGURIDAD"),
        ({"SMTP_PORT": "abc"}, "SMTP_PORT"),
    ],
)
def test_configuracion_incompleta_queda_en_el_log_y_no_manda(sesion, buzon, dos_socios, monkeypatch, caplog,
                                                            variables, falta):
    for clave, valor in variables.items():
        monkeypatch.setenv(clave, valor)
    with caplog.at_level(logging.ERROR, logger="app.mail"):
        resultado = mail.enviar(sesion, HOY)
    assert not resultado.ok and buzon.recibidos == []
    assert "Configuración SMTP incompleta" in caplog.text and falta in caplog.text


def test_sin_socios_lo_avisa_y_no_manda(sesion, buzon, caplog):
    with caplog.at_level(logging.WARNING, logger="app.mail"):
        resultado = mail.enviar(sesion, HOY)
    assert not resultado.ok and buzon.recibidos == []
    assert "No hay socios" in caplog.text


# --- Configuración ---

def test_el_remitente_por_defecto_es_el_usuario_y_el_puerto_sale_de_la_seguridad(monkeypatch):
    for clave, valor in {"SMTP_HOST": "smtp.gmail.com", "SMTP_PORT": "", "SMTP_USER": "cuenta@gmail.com",
                         "SMTP_PASSWORD": "secreta", "SMTP_FROM": "", "SMTP_SEGURIDAD": "STARTTLS"}.items():
        monkeypatch.setenv(clave, valor)
    config = mail.cargar_config_smtp()
    assert (config.remitente, config.puerto, config.seguridad) == ("cuenta@gmail.com", 587, "starttls")
    assert "secreta" not in repr(config)


class _SmtpFalso:
    """Registra qué se llamó, para verificar cada modo de seguridad sin un servidor real."""

    llamadas: list = []

    def __init__(self, host, puerto, timeout=None, context=None):
        self.llamadas.append((type(self).__name__, host, puerto))

    def starttls(self, context=None):
        self.llamadas.append("starttls")

    def login(self, usuario, password):
        self.llamadas.append(("login", usuario))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class SMTP(_SmtpFalso):
    pass


class SMTP_SSL(_SmtpFalso):
    pass


@pytest.mark.parametrize(
    "seguridad, esperado",
    [
        ("starttls", [("SMTP", "h", 587), "starttls", ("login", "u")]),
        ("ssl", [("SMTP_SSL", "h", 465), ("login", "u")]),
        ("ninguna", [("SMTP", "h", 25), ("login", "u")]),
    ],
)
def test_cada_modo_de_seguridad_conecta_como_corresponde(monkeypatch, seguridad, esperado):
    _SmtpFalso.llamadas = []
    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", SMTP_SSL)
    mail._conectar(mail.ConfigSmtp("h", mail.SEGURIDADES[seguridad], "u", "p", "u", seguridad))
    assert _SmtpFalso.llamadas == esperado


# --- Consola (RF-40) ---

def test_ac66_envio_manual_por_consola(tmp_path, buzon):
    archivo = tmp_path / "test.db"
    entorno = {**os.environ, "DATABASE_URL": f"sqlite:///{archivo}"}
    correr = lambda *args: subprocess.run([sys.executable, "-m", *args], cwd=RAIZ, env=entorno,  # noqa: E731
                                          capture_output=True, text=True)
    assert correr("alembic", "upgrade", "head").returncode == 0
    assert correr("app.socios", "alta", "José", "jose@empresa.com").returncode == 0

    resultado = correr("app.mail", "enviar", "--fecha", "2026-10-10")
    assert resultado.returncode == 0, resultado.stderr
    assert [m["Subject"] for _, m in buzon.recibidos] == ["Movimientos del 10/10/2026"]
    assert "enviado a 1 de 1 socios" in resultado.stderr

    invalida = correr("app.mail", "enviar", "--fecha", "2026-02-30")
    assert invalida.returncode != 0 and "no es una fecha" in invalida.stderr


def test_si_el_servidor_no_acepta_login_explica_que_hay_que_vaciar_el_usuario(sesion, buzon, dos_socios,
                                                                             monkeypatch, caplog):
    # Caso típico: .env con la cuenta de Gmail y la prueba contra aiosmtpd, que no tiene AUTH.
    monkeypatch.setenv("SMTP_USER", "cuenta@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcdabcdabcdabcd")
    with caplog.at_level(logging.ERROR, logger="app.mail"):
        mail.enviar(sesion, HOY)
    assert "dejar vacíos SMTP_USER y SMTP_PASSWORD" in caplog.text
