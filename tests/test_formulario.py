import re
import time
from datetime import date

import pytest
from sqlalchemy import select

from app import fechas
from app.modelos import Movimiento

HTMX = {"HX-Request": "true"}
VALIDO = {"descripcion": "Sueldo marzo", "tipo": "Egreso", "monto": "1000", "clasificacion": "SUELDOS", "fecha": "2026-10-20"}


def _opciones(html, nombre):
    """(valor, atributos) de cada <option> de un <select>."""
    select_html = re.search(rf'<select name="{nombre}".*?</select>', html, re.S).group(0)
    return re.findall(r'<option value="([^"]*)"([^>]*)>', select_html)


def _opciones_visibles(html, nombre):
    """Opciones que el operador ve en la lista: sin el cartel oculto "Elegí…"."""
    return [valor for valor, atributos in _opciones(html, nombre) if "hidden" not in atributos]


def _seleccionada(html, nombre="clasificacion"):
    """Valor elegido, o None si quedó el cartel vacío."""
    elegidas = [valor for valor, atributos in _opciones(html, nombre) if re.search(r"\bselected\b", atributos)]
    return elegidas[0] or None if elegidas else None


def _campo_marcado(html, campo):
    return f'aria-describedby="error-{campo}"' in html and f'id="error-{campo}"' in html


def _proponer(cliente, **campos):
    return cliente.post("/movimientos/nuevo/clasificacion", data=campos, headers=HTMX).text


# --- Abrir el formulario (RF-09, RF-03) ---

def test_ac27_la_grilla_tiene_el_boton_agregar_movimiento(logueado):
    html = logueado.get("/").text
    assert re.search(r'<button[^>]*hx-get="/movimientos/nuevo"[^>]*>Agregar movimiento</button>', html)


def test_ac27_ac20_el_formulario_de_alta_esta_vacio_con_la_fecha_de_hoy(logueado, monkeypatch):
    monkeypatch.setattr(fechas, "hoy", lambda: date(2026, 10, 21))
    html = logueado.get("/movimientos/nuevo", headers=HTMX).text
    assert 'name="descripcion" value=""' in html
    assert 'name="monto" value=""' in html
    assert _seleccionada(html, "tipo") is None
    assert 'name="fecha" value="2026-10-21"' in html


def test_ac97_con_el_servidor_en_utc_la_fecha_es_la_de_argentina(logueado, monkeypatch):
    from datetime import datetime, timezone

    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            # 01:30 del 21/10 en UTC son las 22:30 del 20/10 en Argentina.
            return datetime(2026, 10, 21, 1, 30, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(fechas, "datetime", Reloj)
    assert 'name="fecha" value="2026-10-20"' in logueado.get("/movimientos/nuevo").text


def test_el_formulario_de_alta_no_tiene_boton_eliminar(logueado):
    assert "Eliminar" not in logueado.get("/movimientos/nuevo").text


def test_ac21_el_tipo_ofrece_exactamente_ingreso_y_egreso(logueado):
    assert _opciones_visibles(logueado.get("/movimientos/nuevo").text, "tipo") == ["Ingreso", "Egreso"]


def test_sin_tipo_el_selector_de_clasificacion_esta_deshabilitado(logueado):
    html = logueado.get("/movimientos/nuevo").text
    assert re.search(r'<select name="clasificacion"\s+disabled', html)
    assert _opciones_visibles(html, "clasificacion") == []


# --- Selector y propuesta de clasificación (RF-13..16, RF-42, RF-66) ---

def test_ac17_con_ingreso_ofrece_solo_las_de_ingreso(logueado):
    html = _proponer(logueado, tipo="Ingreso", descripcion="")
    assert _opciones_visibles(html, "clasificacion") == ["SERVICIOS-PRESTADOS", "ALQUILERES", "FINANCIEROS"]


def test_ac18_con_egreso_ofrece_solo_las_de_egreso(logueado):
    html = _proponer(logueado, tipo="Egreso", descripcion="")
    assert _opciones_visibles(html, "clasificacion") == [
        "SUELDOS", "IMPUESTOS-TASAS", "VIATICOS", "PAGO-PROVEEDORES", "TURISMO",
    ]


def test_ac01_propone_sueldos(logueado):
    assert _seleccionada(_proponer(logueado, tipo="Egreso", descripcion="Sueldo marzo")) == "SUELDOS"


@pytest.mark.parametrize("descripcion", ["Compra de café", "Impuesto sobre sueldos", "Factura de luz", "Alquiler oficina"])
def test_ac12_ac13_ac15_ac16_sin_propuesta_queda_vacia(logueado, descripcion):
    assert _seleccionada(_proponer(logueado, tipo="Egreso", descripcion=descripcion)) is None


def test_ac67_la_propuesta_reemplaza_la_elegida_a_mano(logueado):
    html = _proponer(logueado, tipo="Egreso", descripcion="Sueldo marzo", clasificacion="VIATICOS")
    assert _seleccionada(html) == "SUELDOS"


def test_ac92_si_la_descripcion_no_propone_se_borra_la_elegida_a_mano(logueado):
    html = _proponer(logueado, tipo="Egreso", descripcion="Compra de café", clasificacion="VIATICOS")
    assert _seleccionada(html) is None


def test_al_cambiar_el_tipo_propone_entre_las_del_tipo_nuevo(logueado):
    html = _proponer(logueado, tipo="Ingreso", descripcion="Alquiler oficina", clasificacion="SUELDOS")
    assert _seleccionada(html) == "ALQUILERES"


def test_la_descripcion_y_el_tipo_piden_la_propuesta_al_cambiar(logueado):
    html = logueado.get("/movimientos/nuevo").text
    descripcion = re.search(r'<input name="descripcion"[^>]*>', html, re.S).group(0)
    tipo = re.search(r'<select name="tipo"[^>]*>', html, re.S).group(0)
    assert 'hx-post="/movimientos/nuevo/clasificacion"' in descripcion and 'hx-trigger="input changed' in descripcion
    assert 'hx-post="/movimientos/nuevo/clasificacion"' in tipo and 'hx-trigger="change"' in tipo


def test_ac80_la_propuesta_llega_en_menos_de_2_segundos(logueado):
    tiempos = []
    for i in range(100):
        inicio = time.perf_counter()
        logueado.post("/movimientos/nuevo/clasificacion", data={"tipo": "Egreso", "descripcion": f"Sueldo {i}"})
        tiempos.append(time.perf_counter() - inicio)
    assert sorted(tiempos)[94] < 2  # p95


# --- Guardar (RF-01, RF-02) ---

def test_ac68_guarda_y_vuelve_a_la_grilla(logueado, sesion):
    respuesta = logueado.post("/movimientos", data=VALIDO, headers=HTMX)
    assert respuesta.headers["HX-Redirect"] == "/"
    guardado = sesion.scalar(select(Movimiento))
    assert (guardado.descripcion, guardado.tipo, guardado.monto, guardado.clasificacion, guardado.fecha) == (
        "Sueldo marzo", "Egreso", -1000, "SUELDOS", date(2026, 10, 20),
    )
    assert "Sueldo marzo" in logueado.get("/").text


def test_sin_htmx_guardar_redirige_a_la_grilla(logueado):
    respuesta = logueado.post("/movimientos", data=VALIDO, follow_redirects=False)
    assert (respuesta.status_code, respuesta.headers["location"]) == (303, "/")


@pytest.mark.parametrize("campo", ["descripcion", "tipo", "monto", "clasificacion"])
def test_ac19_campo_vacio_rechaza_y_marca_ese_campo(logueado, sesion, campo):
    respuesta = logueado.post("/movimientos", data={**VALIDO, campo: ""}, headers=HTMX)
    assert respuesta.status_code == 422
    assert _campo_marcado(respuesta.text, campo)
    otros = {"descripcion", "tipo", "monto", "clasificacion", "fecha"} - {campo}
    assert not any(_campo_marcado(respuesta.text, otro) for otro in otros)
    assert sesion.scalar(select(Movimiento)) is None


@pytest.mark.parametrize("monto", ["0", "-500", "12abc", "12,5", "1.200"])  # AC-24/25/26/82/88
def test_monto_invalido_marca_el_campo_monto(logueado, monto):
    respuesta = logueado.post("/movimientos", data={**VALIDO, "monto": monto}, headers=HTMX)
    assert respuesta.status_code == 422
    assert _campo_marcado(respuesta.text, "monto")


def test_ac47_fecha_inexistente_marca_el_campo_fecha(logueado):
    respuesta = logueado.post("/movimientos", data={**VALIDO, "fecha": "2026-02-30"}, headers=HTMX)
    assert respuesta.status_code == 422
    assert _campo_marcado(respuesta.text, "fecha")


def test_ac09_egreso_con_alquileres_marca_clasificacion(logueado):
    respuesta = logueado.post("/movimientos", data={**VALIDO, "clasificacion": "ALQUILERES"}, headers=HTMX)
    assert respuesta.status_code == 422
    assert _campo_marcado(respuesta.text, "clasificacion")


def test_ac10_ingreso_con_sueldos_marca_clasificacion(logueado):
    respuesta = logueado.post("/movimientos", data={**VALIDO, "tipo": "Ingreso"}, headers=HTMX)
    assert respuesta.status_code == 422
    assert _campo_marcado(respuesta.text, "clasificacion")


def test_ac46_sin_fecha_guarda_la_de_hoy(logueado, sesion, monkeypatch):
    monkeypatch.setattr(fechas, "hoy", lambda: date(2026, 10, 21))
    logueado.post("/movimientos", data={**VALIDO, "fecha": ""}, headers=HTMX)
    assert sesion.scalar(select(Movimiento.fecha)) == date(2026, 10, 21)


def test_con_errores_conserva_lo_que_escribio_el_operador(logueado):
    datos = {**VALIDO, "descripcion": "Compra de café", "monto": "12,5", "clasificacion": "VIATICOS"}
    html = logueado.post("/movimientos", data=datos, headers=HTMX).text
    assert 'value="Compra de café"' in html
    assert 'value="12,5"' in html
    assert _seleccionada(html, "tipo") == "Egreso"
    assert _seleccionada(html) == "VIATICOS"


def test_el_formulario_exige_sesion(cliente):
    respuesta = cliente.post("/movimientos", data=VALIDO, follow_redirects=False)
    assert respuesta.headers["location"] == "/login"
