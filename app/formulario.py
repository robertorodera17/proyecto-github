"""Formulario de alta, modificación y baja de movimientos, con HTMX (RF-01, RF-09..12, RF-15)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app import fechas, movimientos
from app.clasificacion import CLASIFICACIONES, Tipo, proponer
from app.db import obtener_sesion
from app.modelos import Movimiento
from app.movimientos import DatosMovimiento, MovimientoInvalido, MovimientoNoEncontrado
from app.plantillas import plantillas

router = APIRouter()

SesionDB = Annotated[Session, Depends(obtener_sesion)]


def datos_del_formulario(
    descripcion: Annotated[str, Form()] = "",
    tipo: Annotated[str, Form()] = "",
    monto: Annotated[str, Form()] = "",
    clasificacion: Annotated[str, Form()] = "",
    fecha: Annotated[str, Form()] = "",
) -> DatosMovimiento:
    return DatosMovimiento(descripcion, tipo, monto, clasificacion, fecha)


Datos = Annotated[DatosMovimiento, Depends(datos_del_formulario)]


def _opciones(tipo: str) -> tuple[str, ...]:
    return CLASIFICACIONES[Tipo(tipo)] if tipo in tuple(Tipo) else ()


def _formulario(
    request: Request,
    datos: DatosMovimiento,
    errores: dict[str, str] | None = None,
    status: int = 200,
    movimiento_id: int | None = None,
):
    contexto = {
        "movimiento_id": movimiento_id,
        "datos": datos,
        "errores": errores or {},
        "tipos": [t.value for t in Tipo],
        "opciones": _opciones(datos.tipo),
        "seleccionada": datos.clasificacion,
    }
    return plantillas.TemplateResponse(request, "movimiento_form.html", contexto, status_code=status)


@router.get("/movimientos/nuevo", response_class=HTMLResponse)
def nuevo(request: Request):
    # El formulario arranca vacío, con la fecha de hoy en Argentina (RF-03, AC-27).
    return _formulario(request, DatosMovimiento(fecha=fechas.hoy().isoformat()))


@router.post("/movimientos/nuevo/clasificacion", response_class=HTMLResponse)
def clasificacion_propuesta(request: Request, datos: Datos):
    """Selector de clasificación para el tipo elegido, con la propuesta de la descripción.

    Se pide cada vez que cambia la descripción o el tipo. La propuesta reemplaza la
    elegida a mano, y si la descripción no propone ninguna, la selección queda vacía
    (RF-42, RF-66).
    """
    contexto = {
        "opciones": _opciones(datos.tipo),
        "seleccionada": proponer(datos.tipo, datos.descripcion) or "",
        "errores": {},
    }
    return plantillas.TemplateResponse(request, "_clasificacion.html", contexto)


@router.post("/movimientos", response_class=HTMLResponse)
def crear(request: Request, sesion: SesionDB, datos: Datos):
    try:
        movimientos.crear(sesion, datos)
    except MovimientoInvalido as e:
        # 422: htmx está configurado para mostrar el formulario con los errores (base.html).
        return _formulario(request, datos, e.errores, status=422)
    if _es_htmx(request):
        # Va a la primera página para que la grilla muestre el movimiento nuevo arriba.
        return Response(status_code=200, headers={"HX-Redirect": "/"})
    return RedirectResponse("/", status_code=303)


def _es_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _volver_a_la_grilla(request: Request) -> Response:
    # Recarga la página actual de la grilla, sin perder el número de página.
    if _es_htmx(request):
        return Response(status_code=200, headers={"HX-Refresh": "true"})
    return RedirectResponse("/", status_code=303)


def _no_existe(request: Request) -> HTMLResponse:
    mensaje = '<p class="error" role="alert">Ese movimiento ya no existe: puede haberlo eliminado otro operador.</p>'
    # A htmx se le responde 200 para que muestre el aviso donde iba el formulario.
    return HTMLResponse(mensaje, status_code=200 if _es_htmx(request) else 404)


def _datos_de(movimiento: Movimiento) -> DatosMovimiento:
    return DatosMovimiento(
        descripcion=movimiento.descripcion,
        tipo=movimiento.tipo,
        monto=str(abs(movimiento.monto)),  # sin signo: lo define el tipo (RF-45)
        clasificacion=movimiento.clasificacion,
        fecha=movimiento.fecha.isoformat(),
    )


@router.get("/movimientos/{movimiento_id:int}/editar", response_class=HTMLResponse)
def editar(request: Request, sesion: SesionDB, movimiento_id: int):
    try:
        movimiento = movimientos.obtener(sesion, movimiento_id)
    except MovimientoNoEncontrado:
        return _no_existe(request)
    return _formulario(request, _datos_de(movimiento), movimiento_id=movimiento_id)


@router.post("/movimientos/{movimiento_id:int}/clasificacion", response_class=HTMLResponse)
def clasificacion_al_cambiar_el_tipo(request: Request, sesion: SesionDB, movimiento_id: int, datos: Datos):
    """Selector de clasificación al cambiar el tipo en la modificación.

    Las clasificaciones de un tipo nunca valen para el otro: con el tipo nuevo queda
    vacía, y al volver al tipo guardado se recupera la clasificación guardada (RF-46, RF-47).
    """
    try:
        movimiento = movimientos.obtener(sesion, movimiento_id)
    except MovimientoNoEncontrado:
        return _no_existe(request)
    contexto = {
        "opciones": _opciones(datos.tipo),
        "seleccionada": movimiento.clasificacion if datos.tipo == movimiento.tipo else "",
        "errores": {},
    }
    return plantillas.TemplateResponse(request, "_clasificacion.html", contexto)


@router.post("/movimientos/{movimiento_id:int}", response_class=HTMLResponse)
def guardar_modificacion(request: Request, sesion: SesionDB, movimiento_id: int, datos: Datos):
    try:
        movimientos.modificar(sesion, movimiento_id, datos)
    except MovimientoNoEncontrado:
        return _no_existe(request)
    except MovimientoInvalido as e:
        return _formulario(request, datos, e.errores, status=422, movimiento_id=movimiento_id)
    return _volver_a_la_grilla(request)


@router.post("/movimientos/{movimiento_id:int}/eliminar")
def eliminar(request: Request, sesion: SesionDB, movimiento_id: int):
    # La confirmación la pide el navegador antes de mandar el pedido (hx-confirm, RF-28).
    try:
        movimientos.eliminar(sesion, movimiento_id)
    except MovimientoNoEncontrado:
        return _no_existe(request)
    return _volver_a_la_grilla(request)
