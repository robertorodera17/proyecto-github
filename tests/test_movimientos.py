from dataclasses import replace
from datetime import date

import pytest
from sqlalchemy import select

from app import fechas, movimientos
from app.modelos import Movimiento
from app.movimientos import DatosMovimiento, MovimientoInvalido, MovimientoNoEncontrado

VALIDO = DatosMovimiento(
    descripcion="Sueldo marzo", tipo="Egreso", monto="1000", clasificacion="SUELDOS", fecha="2026-10-20"
)


def _errores(datos):
    with pytest.raises(MovimientoInvalido) as error:
        movimientos.validar(datos)
    return error.value.errores


@pytest.fixture
def hoy_fijo(monkeypatch):
    monkeypatch.setattr(fechas, "hoy", lambda: date(2026, 10, 21))


# --- Alta ---

def test_ac68_registra_todos_los_campos_con_monto_negativo(sesion):
    movimientos.crear(sesion, VALIDO)
    guardado = sesion.scalar(select(Movimiento))
    assert (guardado.descripcion, guardado.tipo, guardado.monto, guardado.clasificacion, guardado.fecha) == (
        "Sueldo marzo", "Egreso", -1000, "SUELDOS", date(2026, 10, 20),
    )
    assert guardado.eliminado is False


def test_ac22_egreso_de_500_queda_en_menos_500(sesion):
    assert movimientos.crear(sesion, replace(VALIDO, monto="500")).monto == -500


def test_ac23_ingreso_de_500_queda_en_500(sesion):
    datos = replace(VALIDO, tipo="Ingreso", clasificacion="ALQUILERES", monto="500")
    assert movimientos.crear(sesion, datos).monto == 500


@pytest.mark.parametrize("campo", ["descripcion", "tipo", "monto", "clasificacion"])
def test_ac19_cada_campo_obligatorio_vacio_se_rechaza_y_se_marca(campo):
    assert list(_errores(replace(VALIDO, **{campo: ""}))) == [campo]


def test_ac19_una_descripcion_de_espacios_cuenta_como_vacia():
    assert "descripcion" in _errores(replace(VALIDO, descripcion="   "))


def test_informa_todos_los_errores_juntos():
    assert set(_errores(DatosMovimiento())) == {"descripcion", "tipo", "monto", "clasificacion"}


def test_la_descripcion_se_guarda_sin_espacios_de_mas(sesion):
    assert movimientos.crear(sesion, replace(VALIDO, descripcion="  Sueldo marzo ")).descripcion == "Sueldo marzo"


def test_rechaza_un_tipo_que_no_es_ingreso_ni_egreso():
    assert "tipo" in _errores(replace(VALIDO, tipo="Transferencia"))


# --- Monto (RF-07, RF-58, RF-64) ---

@pytest.mark.parametrize(
    "monto, mensaje",
    [
        ("0", "mayor que 0"),  # AC-24
        ("-500", "mayor que 0"),  # AC-25
        ("12abc", "mayor que 0"),  # AC-26
        ("12,5", "decimales"),  # AC-82
        ("12.5", "decimales"),
        ("1.200", "separador de miles"),  # AC-88
        ("1.200.000", "separador de miles"),
        ("000", "mayor que 0"),
        ("1 200", "mayor que 0"),
        ("١٢", "mayor que 0"),  # dígitos arábigos: solo se aceptan 0-9
        (str(movimientos.MONTO_MAXIMO + 1), "demasiado grande"),
    ],
)
def test_rechaza_montos_invalidos_con_error_en_el_campo(monto, mensaje):
    errores = _errores(replace(VALIDO, monto=monto))
    assert list(errores) == ["monto"]
    assert mensaje in errores["monto"]


def test_acepta_el_monto_maximo(sesion):
    datos = replace(VALIDO, tipo="Ingreso", clasificacion="FINANCIEROS", monto=str(movimientos.MONTO_MAXIMO))
    assert movimientos.crear(sesion, datos).monto == movimientos.MONTO_MAXIMO


def test_ignora_espacios_alrededor_del_monto():
    assert movimientos.validar(replace(VALIDO, monto=" 1200 ")).monto == -1200


# --- Fecha (RF-43, RF-44) ---

def test_ac46_sin_fecha_guarda_la_fecha_de_hoy_en_argentina(sesion, hoy_fijo):
    assert movimientos.crear(sesion, replace(VALIDO, fecha="")).fecha == date(2026, 10, 21)


def test_ac47_rechaza_el_30_de_febrero():
    errores = _errores(replace(VALIDO, fecha="2026-02-30"))
    assert list(errores) == ["fecha"]
    assert "no existe" in errores["fecha"]


@pytest.mark.parametrize("fecha", ["20/10/2026", "2026-10", "hoy", "20261020"])
def test_rechaza_fechas_con_otro_formato(fecha):
    assert list(_errores(replace(VALIDO, fecha=fecha))) == ["fecha"]


# --- Clasificación válida para el tipo (RF-17) ---

def test_ac09_egreso_con_alquileres_se_rechaza_en_clasificacion():
    errores = _errores(replace(VALIDO, clasificacion="ALQUILERES"))
    assert list(errores) == ["clasificacion"]
    assert "no corresponde a un Egreso" in errores["clasificacion"]


def test_ac10_ingreso_con_sueldos_se_rechaza_en_clasificacion():
    errores = _errores(replace(VALIDO, tipo="Ingreso"))
    assert list(errores) == ["clasificacion"]
    assert "no corresponde a un Ingreso" in errores["clasificacion"]


def test_con_tipo_invalido_no_se_juzga_la_clasificacion():
    assert list(_errores(replace(VALIDO, tipo="Otro"))) == ["tipo"]


# --- Modificación (RF-26, RF-27) ---

@pytest.fixture
def existente(sesion):
    """Egreso de 500 con SUELDOS y fecha 17/10/2026."""
    return movimientos.crear(sesion, replace(VALIDO, monto="500", fecha="2026-10-17"))


def _modificar(sesion, movimiento, **cambios):
    datos = DatosMovimiento(
        descripcion=movimiento.descripcion,
        tipo=movimiento.tipo,
        monto=str(abs(movimiento.monto)),
        clasificacion=movimiento.clasificacion,
        fecha=movimiento.fecha.isoformat(),
    )
    return movimientos.modificar(sesion, movimiento.id, replace(datos, **cambios))


def test_ac29_cambia_la_descripcion(sesion, existente):
    assert _modificar(sesion, existente, descripcion="Sueldo abril").descripcion == "Sueldo abril"


def test_ac48_cambia_la_fecha(sesion, existente):
    assert _modificar(sesion, existente, fecha="2026-10-10").fecha == date(2026, 10, 10)


def test_ac93_pasa_a_ingreso_con_alquileres_y_monto_positivo(sesion, existente):
    modificado = _modificar(sesion, existente, tipo="Ingreso", clasificacion="ALQUILERES")
    assert (modificado.tipo, modificado.clasificacion, modificado.monto) == ("Ingreso", "ALQUILERES", 500)


def test_ac94_cambia_el_monto_y_conserva_el_signo_del_egreso(sesion, existente):
    assert _modificar(sesion, existente, monto="800").monto == -800


def test_ac30_rechaza_ingreso_con_sueldos_y_no_cambia_nada(sesion, existente):
    with pytest.raises(MovimientoInvalido) as error:
        _modificar(sesion, existente, tipo="Ingreso")
    assert list(error.value.errores) == ["clasificacion"]
    sesion.refresh(existente)
    assert (existente.tipo, existente.monto) == ("Egreso", -500)


@pytest.mark.parametrize("monto", ["0", "12,5"])  # AC-31, AC-100
def test_ac31_ac100_rechaza_montos_invalidos_en_la_modificacion(sesion, existente, monto):
    with pytest.raises(MovimientoInvalido) as error:
        _modificar(sesion, existente, monto=monto)
    assert list(error.value.errores) == ["monto"]


def test_no_se_puede_modificar_un_movimiento_eliminado(sesion, existente):
    existente.eliminado = True
    sesion.commit()
    with pytest.raises(MovimientoNoEncontrado):
        _modificar(sesion, existente, descripcion="Otra")


def test_no_se_puede_modificar_un_movimiento_inexistente(sesion):
    with pytest.raises(MovimientoNoEncontrado):
        movimientos.modificar(sesion, 999, VALIDO)


# --- Baja lógica (RF-12) ---

def test_eliminar_marca_el_campo_y_no_borra_la_fila(sesion, existente):
    movimientos.eliminar(sesion, existente.id)
    sesion.expire_all()
    assert sesion.get(Movimiento, existente.id).eliminado is True


def test_no_se_puede_eliminar_dos_veces(sesion, existente):
    movimientos.eliminar(sesion, existente.id)
    with pytest.raises(MovimientoNoEncontrado):
        movimientos.eliminar(sesion, existente.id)
