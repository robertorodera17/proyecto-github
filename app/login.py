"""Login en dos pasos: primero la sigla, después definir o ingresar la contraseña."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import operadores, seguridad
from app import sesion as sesion_web
from app.db import obtener_sesion
from app.plantillas import plantillas

router = APIRouter()

SesionDB = Annotated[Session, Depends(obtener_sesion)]


def _pantalla(
    request: Request,
    paso: str,
    sigla: str = "",
    error: str | None = None,
    status: int = 200,
    aviso: str | None = None,
):
    return plantillas.TemplateResponse(
        request,
        "login.html",
        {"paso": paso, "sigla": sigla, "error": error, "aviso": aviso},
        status_code=status,
    )


def _no_existe(request: Request, sigla: str):
    # RF-33: se informa sin pedir contraseña.
    return _pantalla(request, "sigla", sigla, f"No existe un operador con la sigla {sigla}", 404)


def _iniciar_sesion(request: Request, operador) -> RedirectResponse:
    sesion_web.iniciar(request, operador.id)
    return RedirectResponse("/", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def pantalla_login(request: Request):
    if request.session.pop("vencida", False):
        return _pantalla(request, "sigla", aviso="Tu sesión venció por inactividad.")
    return _pantalla(request, "sigla")


@router.post("/logout")
def cerrar_sesion(request: Request):
    sesion_web.cerrar(request)
    return RedirectResponse("/login", status_code=303)


@router.post("/login/sigla", response_class=HTMLResponse)
def ingresar_sigla(request: Request, sesion: SesionDB, sigla: Annotated[str, Form()] = ""):
    sigla = operadores.normalizar_sigla(sigla)
    if not sigla:
        return _pantalla(request, "sigla", error="Ingresá tu sigla.", status=400)
    operador = operadores.buscar_por_sigla(sesion, sigla)
    if operador is None:
        return _no_existe(request, sigla)
    # RF-19: sin contraseña, es el primer ingreso.
    return _pantalla(request, "definir" if operador.password_hash is None else "ingresar", sigla)


@router.post("/login/definir", response_class=HTMLResponse)
def definir_password(
    request: Request,
    sesion: SesionDB,
    sigla: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    repetir: Annotated[str, Form()] = "",
):
    sigla = operadores.normalizar_sigla(sigla)
    operador = operadores.buscar_por_sigla(sesion, sigla)
    if operador is None:
        return _no_existe(request, sigla)
    if operador.password_hash is not None:
        # AC-52: la contraseña se define una sola vez.
        return _pantalla(request, "ingresar", sigla, f"El operador {sigla} ya tiene contraseña.", 409)
    if error := seguridad.validar_password(password):
        return _pantalla(request, "definir", sigla, error, 400)
    # No hay forma de recuperar una contraseña olvidada (FA-07): un error de tipeo
    # dejaría al operador afuera para siempre.
    if password != repetir:
        return _pantalla(request, "definir", sigla, "Las contraseñas no coinciden.", 400)
    try:
        operadores.definir_password(sesion, operador, password)
    except operadores.PasswordYaDefinida as e:
        return _pantalla(request, "ingresar", sigla, str(e), 409)
    return _iniciar_sesion(request, operador)


@router.post("/login/ingresar", response_class=HTMLResponse)
def ingresar(
    request: Request,
    sesion: SesionDB,
    sigla: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
):
    sigla = operadores.normalizar_sigla(sigla)
    operador = operadores.buscar_por_sigla(sesion, sigla)
    if operador is None:
        return _no_existe(request, sigla)
    if operador.password_hash is None:
        return _pantalla(request, "definir", sigla)
    operador = operadores.autenticar(sesion, sigla, password)
    if operador is None:
        return _pantalla(request, "ingresar", sigla, "Contraseña incorrecta.", 401)
    return _iniciar_sesion(request, operador)
