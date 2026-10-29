import logging
from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import db, mail, programador
from app.fechas import ZONA_ARGENTINA
from app.modelos import EnvioDiario, Movimiento
from tests.test_mail_envio import _puerto_libre, buzon, dos_socios  # noqa: F401  (fixtures)

HOY = date(2026, 10, 21)


def _a_las(hora, minuto=0):
    return datetime(2026, 10, 21, hora, minuto, tzinfo=ZONA_ARGENTINA)


def _registrados(sesion):
    sesion.expire_all()
    return sesion.scalars(select(EnvioDiario.fecha)).all()


@pytest.fixture
def servidor_caido(monkeypatch):
    for clave, valor in {"SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(_puerto_libre()), "SMTP_USER": "",
                         "SMTP_PASSWORD": "", "SMTP_FROM": "app@empresa.com", "SMTP_SEGURIDAD": "ninguna"}.items():
        monkeypatch.setenv(clave, valor)


@pytest.fixture
def intentos(monkeypatch):
    """Cuenta las veces que se intenta mandar el mail de un día."""
    llamadas = []
    enviar = mail.enviar
    monkeypatch.setattr(mail, "enviar", lambda sesion, fecha: llamadas.append(fecha) or enviar(sesion, fecha))
    return llamadas


# --- Envío de las 17:00 (RF-24, RF-39) ---

def test_ac42_a_las_17_cada_socio_recibe_solo_lo_de_hoy_no_eliminado(sesion, buzon, dos_socios, engine, monkeypatch):
    for descripcion, fecha, eliminado in [("De hoy", HOY, False), ("De hoy eliminado", HOY, True),
                                          ("De ayer", date(2026, 10, 20), False)]:
        sesion.add(Movimiento(descripcion=descripcion, tipo="Egreso", monto=-100, clasificacion="SUELDOS",
                              fecha=fecha, eliminado=eliminado))
    sesion.commit()
    monkeypatch.setattr(db, "Sesion", sessionmaker(engine, expire_on_commit=False))
    monkeypatch.setattr(programador.fechas, "hoy", lambda: HOY)

    programador._tarea_de_las_17()

    assert [sobre for sobre, _ in buzon.recibidos] == [["jose@empresa.com"], ["ana@empresa.com"]]
    for _, recibido in buzon.recibidos:
        texto = recibido.get_content()
        assert "De hoy |" in texto and "eliminado" not in texto and "De ayer" not in texto
    assert _registrados(sesion) == [HOY]


def test_el_dia_se_registra_antes_de_mandar(sesion, buzon, dos_socios, monkeypatch):
    registrado_al_mandar = []
    enviar = mail.enviar
    monkeypatch.setattr(mail, "enviar",
                        lambda s, f: registrado_al_mandar.append(programador.ya_enviado(s, f)) or enviar(s, f))
    programador.envio_automatico(sesion, HOY)
    assert registrado_al_mandar == [True]


def test_no_manda_dos_veces_el_mismo_dia(sesion, buzon, dos_socios):
    assert programador.envio_automatico(sesion, HOY) is True
    assert programador.envio_automatico(sesion, HOY) is False
    assert len(buzon.recibidos) == 2  # un mail por socio, una sola vez


# --- Al arrancar (RF-38, RF-52, RF-53) ---

def test_ac63_arranca_a_las_17_30_sin_haber_mandado_y_lo_manda(sesion, buzon, dos_socios):
    programador.al_arrancar(sesion, _a_las(17, 30))
    assert len(buzon.recibidos) == 2
    assert _registrados(sesion) == [HOY]


def test_ac65_ya_se_mando_a_las_17_y_al_reiniciar_a_las_17_30_no_se_repite(sesion, buzon, dos_socios, intentos):
    programador.envio_automatico(sesion, HOY)
    programador.al_arrancar(sesion, _a_las(17, 30))
    assert intentos == [HOY]
    assert len(buzon.recibidos) == 2


@pytest.mark.parametrize("hora, minuto", [(18, 0), (21, 15)])
def test_ac64_ac76_desde_las_18_no_lo_manda_y_deja_el_comando_en_el_log(sesion, buzon, dos_socios, caplog,
                                                                        hora, minuto):
    with caplog.at_level(logging.WARNING, logger="app.programador"):
        programador.al_arrancar(sesion, _a_las(hora, minuto))
    assert buzon.recibidos == []
    assert "python -m app.mail enviar --fecha 2026-10-21" in caplog.text
    assert _registrados(sesion) == []


def test_antes_de_las_17_al_arrancar_no_hace_nada(sesion, buzon, dos_socios, caplog):
    with caplog.at_level(logging.INFO, logger="app.programador"):
        programador.al_arrancar(sesion, _a_las(16, 59))
    assert buzon.recibidos == [] and caplog.text == ""


def test_desde_las_18_si_ya_se_mando_no_avisa_nada(sesion, buzon, dos_socios, caplog):
    programador.envio_automatico(sesion, HOY)
    with caplog.at_level(logging.WARNING, logger="app.programador"):
        programador.al_arrancar(sesion, _a_las(18, 30))
    assert caplog.text == ""


# --- Envío manual (RF-54) ---

def test_ac77_el_envio_manual_de_las_16_no_impide_el_automatico(sesion, buzon, dos_socios):
    mail.enviar(sesion, HOY)  # lo que hace `python -m app.mail enviar`
    assert _registrados(sesion) == []
    assert programador.envio_automatico(sesion, HOY) is True
    assert len(buzon.recibidos) == 4  # 2 del manual y 2 del automático


# --- Fallas (RF-55, RF-56) ---

def test_ac79_si_falla_no_se_reintenta_ni_al_reiniciar_a_las_17_30(sesion, dos_socios, servidor_caido, intentos,
                                                                  caplog):
    with caplog.at_level(logging.ERROR, logger="app.mail"):
        programador.envio_automatico(sesion, HOY)
    assert "no se pudo conectar" in caplog.text
    assert _registrados(sesion) == [HOY]

    programador.al_arrancar(sesion, _a_las(17, 30))  # reinicio
    programador.envio_automatico(sesion, HOY)  # el programador no vuelve a correr ese día, pero si lo hiciera
    assert intentos == [HOY]


def test_un_error_inesperado_queda_en_el_log(caplog):
    def falla():
        raise RuntimeError("base bloqueada")

    with caplog.at_level(logging.ERROR, logger="app.programador"):
        programador._sin_errores_sueltos(falla)()
    assert "Falló la tarea del mail diario" in caplog.text and "base bloqueada" in caplog.text


# --- Programación (RF-24) ---

def test_esta_programado_todos_los_dias_a_las_17_de_argentina():
    trabajo = programador.crear().get_job("mail_diario")
    disparador = trabajo.trigger
    # Desde las 16:00 de hoy, el próximo es hoy a las 17:00; desde las 17:01, mañana a las 17:00.
    assert disparador.get_next_fire_time(None, _a_las(16)) == _a_las(17)
    assert disparador.get_next_fire_time(None, _a_las(17, 1)) == datetime(2026, 10, 22, 17, 0, tzinfo=ZONA_ARGENTINA)
    # También sábados y domingos: 24/10/2026 es sábado.
    sabado = datetime(2026, 10, 24, 12, 0, tzinfo=ZONA_ARGENTINA)
    assert disparador.get_next_fire_time(None, sabado) == datetime(2026, 10, 24, 17, 0, tzinfo=ZONA_ARGENTINA)
    assert trabajo.misfire_grace_time == 3600 and trabajo.coalesce


def test_con_el_servidor_en_utc_se_dispara_a_las_17_de_argentina():
    disparador = programador.crear().get_job("mail_diario").trigger
    desde_utc = datetime.fromisoformat("2026-10-21T15:00:00+00:00")  # 12:00 en Argentina
    assert disparador.get_next_fire_time(None, desde_utc) == datetime.fromisoformat("2026-10-21T20:00:00+00:00")


def test_la_app_inicia_y_detiene_el_programador(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import Config
    from app.main import crear_app

    eventos = []

    class ProgramadorFalso:
        def shutdown(self, wait=True):
            eventos.append("detenido")

    monkeypatch.setattr(programador, "iniciar", lambda: eventos.append("iniciado") or ProgramadorFalso())
    with TestClient(crear_app(Config(secret_key="x"))):
        assert eventos == ["iniciado"]
    assert eventos == ["iniciado", "detenido"]
