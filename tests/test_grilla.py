import re
from datetime import date

import pytest

from app import movimientos
from app.modelos import Movimiento
from tests.conftest import iniciar_sesion


def _cargar(sesion, descripcion="Sueldo marzo", tipo="Egreso", monto=1000, clasificacion="SUELDOS",
            fecha=date(2026, 10, 20), eliminado=False):
    signo = -1 if tipo == "Egreso" else 1
    movimiento = Movimiento(descripcion=descripcion, tipo=tipo, monto=signo * monto,
                            clasificacion=clasificacion, fecha=fecha, eliminado=eliminado)
    sesion.add(movimiento)
    sesion.commit()
    return movimiento


def _filas(html):
    """Celdas de cada fila de la grilla, como textos."""
    cuerpo = html.split("<tbody>")[1].split("</tbody>")[0]
    return [
        [re.sub(r"\s+", " ", celda).strip() for celda in re.findall(r"<td[^>]*>(.*?)</td>", fila, re.S)]
        for fila in re.findall(r"<tr[^>]*>(.*?)</tr>", cuerpo, re.S)
    ]


def _descripciones(html):
    return [fila[0] for fila in _filas(html)]


def test_ac11_muestra_las_cinco_columnas_en_orden(logueado, sesion):
    _cargar(sesion)
    html = logueado.get("/").text
    encabezados = re.findall(r"<th[^>]*>(.*?)</th>", html)
    assert encabezados == ["Descripción", "Monto", "Tipo", "Clasificación", "Fecha"]
    assert _filas(html) == [["Sueldo marzo", "-1.000", "Egreso", "SUELDOS", "20/10/2026"]]


def test_ac99_muestra_movimientos_de_cualquier_fecha(logueado, sesion):
    _cargar(sesion, descripcion="De hoy", fecha=date(2026, 10, 21))
    _cargar(sesion, descripcion="De enero", fecha=date(2026, 1, 1))
    assert set(_descripciones(logueado.get("/").text)) == {"De hoy", "De enero"}


def test_ac83_ingreso_de_1200_se_ve_como_1_200(logueado, sesion):
    _cargar(sesion, tipo="Ingreso", clasificacion="ALQUILERES", monto=1200)
    assert _filas(logueado.get("/").text)[0][1] == "1.200"


def test_ac89_egreso_de_1200_se_ve_como_menos_1_200(logueado, sesion):
    _cargar(sesion, monto=1200)
    assert _filas(logueado.get("/").text)[0][1] == "-1.200"


def test_ac84_ordena_por_fecha_de_la_mas_reciente_a_la_mas_antigua(logueado, sesion):
    for dia in (10, 12, 11):
        _cargar(sesion, descripcion=f"Del {dia}", fecha=date(2026, 10, dia))
    assert _descripciones(logueado.get("/").text) == ["Del 12", "Del 11", "Del 10"]


def test_ac91_en_la_misma_fecha_el_ultimo_cargado_va_arriba(logueado, sesion):
    _cargar(sesion, descripcion="Alquiler local", tipo="Ingreso", clasificacion="ALQUILERES", fecha=date(2026, 10, 21))
    _cargar(sesion, descripcion="Sueldo marzo", fecha=date(2026, 10, 21))
    assert _descripciones(logueado.get("/").text) == ["Sueldo marzo", "Alquiler local"]


def test_ac85_pagina_de_a_30(logueado, sesion):
    for i in range(31):
        _cargar(sesion, descripcion=f"Mov {i}")
    primera = logueado.get("/").text
    segunda = logueado.get("/?pagina=2").text
    assert len(_filas(primera)) == 30
    assert len(_filas(segunda)) == 1
    assert "Página 1 de 2" in primera and 'href="/?pagina=2"' in primera
    assert "Página 2 de 2" in segunda and 'href="/?pagina=1"' in segunda
    # El primero cargado es el más viejo dentro de la misma fecha: queda solo en la página 2.
    assert _descripciones(segunda) == ["Mov 0"]


def test_con_30_o_menos_no_muestra_paginas(logueado, sesion):
    for i in range(30):
        _cargar(sesion, descripcion=f"Mov {i}")
    assert "Página" not in logueado.get("/").text


@pytest.mark.parametrize("pagina, esperada", [("0", 1), ("abc", 1), ("99", 2), ("-1", 1)])
def test_pagina_fuera_de_rango_o_invalida_muestra_la_mas_cercana(logueado, sesion, pagina, esperada):
    for i in range(31):
        _cargar(sesion, descripcion=f"Mov {i}")
    respuesta = logueado.get(f"/?pagina={pagina}")
    assert respuesta.status_code == 200
    assert f"Página {esperada} de 2" in respuesta.text


def test_no_muestra_los_eliminados(logueado, sesion):
    _cargar(sesion, descripcion="Visible")
    _cargar(sesion, descripcion="Eliminado", eliminado=True)
    assert _descripciones(logueado.get("/").text) == ["Visible"]


def test_los_eliminados_no_cuentan_para_las_paginas(sesion):
    for i in range(30):
        _cargar(sesion, descripcion=f"Mov {i}")
    _cargar(sesion, descripcion="Eliminado", eliminado=True)
    assert movimientos.listar(sesion).total_paginas == 1


def test_sin_movimientos_lo_avisa(logueado):
    assert "No hay movimientos cargados." in logueado.get("/").text


def test_ac39_otro_operador_ve_los_mismos_movimientos(cliente, sesion):
    iniciar_sesion(cliente, sesion, "RO", "Rocío")
    _cargar(sesion, descripcion="Cargado por RO")
    cliente.post("/logout")
    iniciar_sesion(cliente, sesion, "JP", "Juan")
    assert _descripciones(cliente.get("/").text) == ["Cargado por RO"]


def test_escapa_el_html_de_la_descripcion(logueado, sesion):
    _cargar(sesion, descripcion="<script>alert(1)</script>")
    html = logueado.get("/").text
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
