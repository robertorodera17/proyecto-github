from datetime import date
from email import message_from_bytes, policy

import pytest

from app import mail, movimientos
from app.modelos import Movimiento

HOY = date(2026, 10, 21)


def _mov(descripcion="Sueldo marzo", tipo="Egreso", monto=-1200, clasificacion="SUELDOS", fecha=HOY, eliminado=False):
    return Movimiento(descripcion=descripcion, tipo=tipo, monto=monto, clasificacion=clasificacion,
                      fecha=fecha, eliminado=eliminado)


def _lineas_de_movimiento(texto):
    return [l for l in texto.splitlines() if l.count(" | ") == 4 and not l.startswith("Descripción |")]


def _armado(movs, fecha=HOY):
    """El mail tal como lo recibe el socio, después de pasar por bytes."""
    mensaje = mail.armar(fecha, movs, "app@empresa.com", "jose@empresa.com")
    return message_from_bytes(mensaje.as_bytes(), policy=policy.default)


# --- Asunto y destinatario ---

def test_ac74_el_asunto_lleva_la_fecha_del_mail():
    assert _armado([])["Subject"] == "Movimientos del 21/10/2026"


def test_ac66_con_otra_fecha_el_asunto_lleva_esa_fecha():
    assert _armado([], fecha=date(2026, 10, 10))["Subject"] == "Movimientos del 10/10/2026"


def test_ac60_el_unico_destinatario_es_el_socio():
    recibido = _armado([])
    assert recibido["To"] == "jose@empresa.com"
    assert recibido["Cc"] is None and recibido["Bcc"] is None


# --- Cuerpo ---

def test_ac43_cada_movimiento_muestra_sus_cinco_datos():
    assert mail.linea(_mov()) == "Sueldo marzo | -1.200 | Egreso | SUELDOS | 21/10/2026"


def test_ac87_ingreso_de_1200_se_ve_como_1_200():
    linea = mail.linea(_mov(tipo="Ingreso", monto=1200, clasificacion="ALQUILERES"))
    assert " | 1.200 | " in linea


def test_ac90_egreso_de_1200_se_ve_como_menos_1_200():
    assert " | -1.200 | " in mail.linea(_mov())


def test_ac75_informa_la_cantidad_de_movimientos():
    texto = _armado([_mov(), _mov(), _mov()]).get_content()
    assert "Cantidad de movimientos: 3" in texto


def test_ac102_una_linea_por_movimiento():
    movs = [_mov(descripcion=d) for d in ("Uno", "Dos", "Tres")]
    lineas = _lineas_de_movimiento(_armado(movs).get_content())
    assert [l.split(" | ")[0] for l in lineas] == ["Uno", "Dos", "Tres"]


def test_una_descripcion_con_saltos_de_linea_ocupa_una_sola_linea():
    texto = _armado([_mov(descripcion="Sueldo\nmarzo\r\nextra")]).get_content()
    assert _lineas_de_movimiento(texto) == ["Sueldo marzo extra | -1.200 | Egreso | SUELDOS | 21/10/2026"]


def test_ac62_sin_movimientos_dice_no_hubo_movimientos_con_la_fecha():
    texto = _armado([]).get_content()
    assert "No hubo movimientos." in texto
    assert "21/10/2026" in texto
    assert "Cantidad de movimientos: 0" in texto
    assert _lineas_de_movimiento(texto) == []


def test_tildes_y_enes_llegan_bien():
    texto = _armado([_mov(descripcion="Viáticos Córdoba, año")]).get_content()
    assert "Viáticos Córdoba, año" in texto


# --- Formato (RF-67) ---

def test_ac101_una_sola_parte_text_plain_sin_html():
    recibido = _armado([_mov()])
    assert not recibido.is_multipart()
    assert recibido.get_content_type() == "text/plain"
    assert "text/html" not in recibido.as_string()


# --- Qué movimientos entran (RF-24) ---

def test_ac42_solo_los_no_eliminados_de_la_fecha(sesion):
    sesion.add_all([
        _mov(descripcion="De hoy"),
        _mov(descripcion="De hoy eliminado", eliminado=True),
        _mov(descripcion="De ayer", fecha=date(2026, 10, 20)),
    ])
    sesion.commit()
    assert [m.descripcion for m in movimientos.del_dia(sesion, HOY)] == ["De hoy"]


def test_vienen_en_el_orden_en_que_se_cargaron(sesion):
    for d in ("Primero", "Segundo", "Tercero"):
        sesion.add(_mov(descripcion=d))
        sesion.commit()
    assert [m.descripcion for m in movimientos.del_dia(sesion, HOY)] == ["Primero", "Segundo", "Tercero"]
