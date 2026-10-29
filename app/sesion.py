"""Control de sesión: login obligatorio (RF-21) y vencimiento por inactividad (RNF-03)."""

import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.db import obtener_sesion
from app.modelos import Operador

INACTIVIDAD_MAXIMA = 60 * 60  # segundos (RNF-03)


def ahora() -> float:
    """Reloj de la sesión; los tests lo reemplazan. La zona horaria no importa acá."""
    return time.time()


def iniciar(request: Request, operador_id: int) -> None:
    request.session.clear()
    request.session["operador_id"] = operador_id
    request.session["ultima_actividad"] = ahora()


def cerrar(request: Request) -> None:
    request.session.clear()


def _al_login(request: Request) -> Response:
    # Un pedido de HTMX seguiría un redirect común y metería el login dentro de la
    # página; con HX-Redirect el navegador navega al login completo.
    if request.headers.get("HX-Request") == "true":
        return Response(status_code=200, headers={"HX-Redirect": "/login"})
    return RedirectResponse("/login", status_code=303)


def exigir_sesion(rutas_publicas: frozenset[str]):
    """Middleware: fuera de las rutas públicas, exige una sesión activa y la renueva."""

    async def middleware(request: Request, call_next) -> Response:
        if request.url.path in rutas_publicas:
            return await call_next(request)

        sesion = request.session
        if "operador_id" not in sesion:
            return _al_login(request)

        # A los 60 minutos justos la sesión ya está vencida (RNF-03).
        if ahora() - sesion.get("ultima_actividad", 0) >= INACTIVIDAD_MAXIMA:
            sesion.clear()
            sesion["vencida"] = True  # para avisarlo en el login (RF-34)
            return _al_login(request)

        # Cada acción, incluidas las de HTMX, renueva el plazo.
        sesion["ultima_actividad"] = ahora()
        return await call_next(request)

    return middleware


def operador_actual(request: Request, sesion: Annotated[Session, Depends(obtener_sesion)]) -> Operador:
    """Dependencia: el operador de la sesión. El middleware ya garantizó que hay sesión."""
    operador = sesion.get(Operador, request.session["operador_id"])
    if operador is None:
        cerrar(request)
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return operador
