import re
from datetime import date

import pytest
from sqlalchemy import select

from app.modelos import Movimiento
from tests.test_formulario import HTMX, _campo_marcado, _opciones_visibles, _seleccionada


@pytest.fixture
def egreso(sesion):
    """Egreso de 500 con SUELDOS y fecha 17/10/2026."""
    movimiento = Movimiento(descripcion="Sueldo marzo", tipo="Egreso", monto=-500,
                            clasificacion="SUELDOS", fecha=date(2026, 10, 17))
    sesion.add(movimiento)
    sesion.commit()
    return movimiento


def _datos(movimiento, **cambios):
    datos = {
        "descripcion": movimiento.descripcion,
        "tipo": movimiento.tipo,
        "monto": str(abs(movimiento.monto)),
        "clasificacion": movimiento.clasificacion,
        "fecha": movimiento.fecha.isoformat(),
    }
    return {**datos, **cambios}


def _guardar(cliente, movimiento, **cambios):
    return cliente.post(f"/movimientos/{movimiento.id}", data=_datos(movimiento, **cambios), headers=HTMX)


def _recargado(sesion, movimiento):
    sesion.expire_all()
    return sesion.get(Movimiento, movimiento.id)


# --- Abrir la modificación (RF-10, RF-45) ---

def test_ac28_doble_click_en_la_fila_abre_la_modificacion(logueado, egreso):
    html = logueado.get("/").text
    fila = re.search(rf'<tr data-id="{egreso.id}"[^>]*>', html, re.S).group(0)
    assert f'hx-get="/movimientos/{egreso.id}/editar"' in fila
    assert 'hx-trigger="dblclick' in fila
    assert 'hx-target="#formulario"' in fila


def test_ac28_el_formulario_trae_los_datos_del_movimiento(logueado, egreso):
    html = logueado.get(f"/movimientos/{egreso.id}/editar", headers=HTMX).text
    assert "Modificar movimiento" in html
    assert f'hx-post="/movimientos/{egreso.id}"' in html
    assert 'name="descripcion" value="Sueldo marzo"' in html
    assert _seleccionada(html, "tipo") == "Egreso"
    assert _seleccionada(html) == "SUELDOS"
    assert 'name="fecha" value="2026-10-17"' in html


def test_ac69_el_monto_se_muestra_sin_signo(logueado, egreso):
    assert 'name="monto" value="500"' in logueado.get(f"/movimientos/{egreso.id}/editar").text


def test_al_modificar_la_descripcion_no_propone_clasificacion(logueado, egreso):
    html = logueado.get(f"/movimientos/{egreso.id}/editar").text
    descripcion = re.search(r'<input name="descripcion"[^>]*>', html, re.S).group(0)
    assert "hx-post" not in descripcion


# --- Cambiar el tipo (RF-46, RF-47) ---

def test_ac70_al_pasar_a_ingreso_la_clasificacion_queda_vacia(logueado, egreso):
    html = logueado.post(f"/movimientos/{egreso.id}/clasificacion", data=_datos(egreso, tipo="Ingreso"), headers=HTMX).text
    assert _opciones_visibles(html, "clasificacion") == ["SERVICIOS-PRESTADOS", "ALQUILERES", "FINANCIEROS"]
    assert _seleccionada(html) is None


def test_ac71_al_volver_a_egreso_recupera_la_clasificacion_guardada(logueado, egreso):
    logueado.post(f"/movimientos/{egreso.id}/clasificacion", data=_datos(egreso, tipo="Ingreso"), headers=HTMX)
    html = logueado.post(
        f"/movimientos/{egreso.id}/clasificacion", data=_datos(egreso, tipo="Egreso", clasificacion=""), headers=HTMX
    ).text
    assert _seleccionada(html) == "SUELDOS"


def test_el_tipo_pide_el_selector_de_la_modificacion(logueado, egreso):
    html = logueado.get(f"/movimientos/{egreso.id}/editar").text
    tipo = re.search(r'<select name="tipo"[^>]*>', html, re.S).group(0)
    assert f'hx-post="/movimientos/{egreso.id}/clasificacion"' in tipo


# --- Guardar la modificación (RF-26, RF-27) ---

def test_ac29_cambia_la_descripcion_y_la_grilla_la_muestra(logueado, sesion, egreso):
    respuesta = _guardar(logueado, egreso, descripcion="Sueldo abril")
    assert respuesta.headers["HX-Refresh"] == "true"
    assert _recargado(sesion, egreso).descripcion == "Sueldo abril"
    assert "Sueldo abril" in logueado.get("/").text


def test_ac48_cambia_la_fecha(logueado, sesion, egreso):
    _guardar(logueado, egreso, fecha="2026-10-10")
    assert _recargado(sesion, egreso).fecha == date(2026, 10, 10)
    assert "10/10/2026" in logueado.get("/").text


def test_ac93_pasa_a_ingreso_con_alquileres_y_monto_500(logueado, sesion, egreso):
    _guardar(logueado, egreso, tipo="Ingreso", clasificacion="ALQUILERES")
    guardado = _recargado(sesion, egreso)
    assert (guardado.tipo, guardado.clasificacion, guardado.monto) == ("Ingreso", "ALQUILERES", 500)


def test_ac94_cambia_el_monto_a_800_y_queda_en_menos_800(logueado, sesion, egreso):
    _guardar(logueado, egreso, monto="800")
    assert _recargado(sesion, egreso).monto == -800


def test_ac30_ingreso_con_sueldos_se_rechaza_en_clasificacion(logueado, sesion, egreso):
    respuesta = _guardar(logueado, egreso, tipo="Ingreso")
    assert respuesta.status_code == 422
    assert _campo_marcado(respuesta.text, "clasificacion")
    assert "Modificar movimiento" in respuesta.text
    assert _recargado(sesion, egreso).tipo == "Egreso"


@pytest.mark.parametrize("monto", ["0", "12,5"])  # AC-31, AC-100
def test_ac31_ac100_monto_invalido_se_rechaza_en_monto(logueado, sesion, egreso, monto):
    respuesta = _guardar(logueado, egreso, monto=monto)
    assert respuesta.status_code == 422
    assert _campo_marcado(respuesta.text, "monto")
    assert _recargado(sesion, egreso).monto == -500


# --- Eliminar (RF-11, RF-12, RF-28) ---

def test_la_modificacion_tiene_eliminar_con_confirmacion(logueado, egreso):
    html = logueado.get(f"/movimientos/{egreso.id}/editar").text
    boton = re.search(r'<button[^>]*>Eliminar</button>', html, re.S).group(0)
    assert f'hx-post="/movimientos/{egreso.id}/eliminar"' in boton
    assert "hx-confirm=" in boton


def test_ac32_eliminar_lo_saca_de_la_grilla(logueado, egreso):
    respuesta = logueado.post(f"/movimientos/{egreso.id}/eliminar", headers=HTMX)
    assert respuesta.headers["HX-Refresh"] == "true"
    assert "Sueldo marzo" not in logueado.get("/").text


def test_ac33_el_registro_sigue_en_la_base_marcado_como_eliminado(logueado, sesion, egreso):
    logueado.post(f"/movimientos/{egreso.id}/eliminar", headers=HTMX)
    filas = sesion.execute(select(Movimiento.id, Movimiento.eliminado)).all()
    assert filas == [(egreso.id, True)]


def test_ac49_si_cancela_la_confirmacion_no_se_manda_nada_y_sigue_igual(logueado, sesion, egreso):
    # Cancelar en hx-confirm hace que el navegador no mande el pedido: sin POST, nada cambia.
    logueado.get(f"/movimientos/{egreso.id}/editar")
    assert _recargado(sesion, egreso).eliminado is False
    assert "Sueldo marzo" in logueado.get("/").text


# --- Movimientos que ya no existen (FA-09) ---

@pytest.mark.parametrize(
    "metodo, ruta",
    [("get", "/editar"), ("post", ""), ("post", "/eliminar"), ("post", "/clasificacion")],
)
def test_un_movimiento_eliminado_no_se_puede_abrir_modificar_ni_eliminar(logueado, sesion, egreso, metodo, ruta):
    egreso.eliminado = True
    sesion.commit()
    respuesta = getattr(logueado, metodo)(f"/movimientos/{egreso.id}{ruta}", headers=HTMX, **(
        {"data": _datos(egreso)} if metodo == "post" else {}))
    assert "ya no existe" in respuesta.text


def test_sin_htmx_un_movimiento_inexistente_da_404(logueado):
    assert logueado.get("/movimientos/999/editar").status_code == 404


@pytest.mark.parametrize("metodo, ruta", [("get", "/movimientos/1/editar"), ("post", "/movimientos/1"),
                                          ("post", "/movimientos/1/eliminar")])
def test_ac38_sin_sesion_va_al_login(cliente, egreso, metodo, ruta):
    respuesta = getattr(cliente, metodo)(ruta, follow_redirects=False)
    assert respuesta.headers["location"] == "/login"
