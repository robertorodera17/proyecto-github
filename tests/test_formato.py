from datetime import date

import pytest

from app import formato


@pytest.mark.parametrize(
    "valor, texto",
    [
        (1200, "1.200"),  # AC-83
        (-1200, "-1.200"),  # AC-89
        (5, "5"),
        (-500, "-500"),
        (1000, "1.000"),
        (1234567, "1.234.567"),
        (-1000000, "-1.000.000"),
    ],
)
def test_monto_con_punto_de_miles_y_signo_menos(valor, texto):
    assert formato.monto(valor) == texto


def test_fecha_dd_mm_aaaa():
    assert formato.fecha(date(2026, 1, 5)) == "05/01/2026"
