from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modelos import Movimiento


def _movimiento(**cambios):
    datos = dict(descripcion="Sueldo marzo", tipo="Egreso", monto=-1000, clasificacion="SUELDOS", fecha=date(2026, 10, 20))
    return Movimiento(**{**datos, **cambios})


def test_guarda_un_movimiento_valido_no_eliminado(sesion):
    sesion.add(_movimiento())
    sesion.commit()
    guardado = sesion.scalar(select(Movimiento))
    assert (guardado.descripcion, guardado.tipo, guardado.monto, guardado.clasificacion, guardado.fecha) == (
        "Sueldo marzo", "Egreso", -1000, "SUELDOS", date(2026, 10, 20),
    )
    assert guardado.eliminado is False


def test_el_id_sigue_el_orden_de_carga(sesion):
    primero, segundo = _movimiento(), _movimiento(descripcion="Sueldo abril")
    sesion.add(primero)
    sesion.commit()
    sesion.add(segundo)
    sesion.commit()
    assert segundo.id > primero.id


def test_admite_montos_grandes(sesion):
    # El PRD no fija monto máximo; SQLite guarda enteros de hasta 64 bits.
    sesion.add(_movimiento(tipo="Ingreso", clasificacion="FINANCIEROS", monto=9_000_000_000_000))
    sesion.commit()


@pytest.mark.parametrize(
    "cambios",
    [
        {"tipo": "Transferencia"},
        {"monto": 1000},  # egreso positivo
        {"tipo": "Ingreso", "clasificacion": "ALQUILERES", "monto": -1000},  # ingreso negativo
        {"monto": 0},
        {"clasificacion": "ALQUILERES"},  # AC-09: de ingreso en un egreso
        {"tipo": "Ingreso", "monto": 1000},  # AC-10: SUELDOS en un ingreso
        {"clasificacion": "OTRA"},
    ],
)
def test_la_base_rechaza_movimientos_inconsistentes(sesion, cambios):
    sesion.add(_movimiento(**cambios))
    with pytest.raises(IntegrityError):
        sesion.commit()
