"""Grilla de movimientos (RF-08)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import movimientos
from app.db import obtener_sesion
from app.modelos import Operador
from app.plantillas import plantillas
from app.sesion import operador_actual

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def grilla(
    request: Request,
    sesion: Annotated[Session, Depends(obtener_sesion)],
    operador: Annotated[Operador, Depends(operador_actual)],
    pagina: str = "1",
):
    # Un número de página inválido muestra la primera, en vez de un error.
    numero = int(pagina) if pagina.isdigit() else 1
    return plantillas.TemplateResponse(
        request, "grilla.html", {"operador": operador, "pagina": movimientos.listar(sesion, numero)}
    )
