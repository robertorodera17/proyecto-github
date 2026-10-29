"""Punto de entrada: `uvicorn app.main:app`."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app import formulario, grilla, login, programador, registro
from app import sesion as sesion_web
from app.config import Config, cargar_config

# Únicas rutas que se atienden sin sesión. Todo lo demás exige login (RF-21).
RUTAS_PUBLICAS = frozenset({"/login", "/login/sigla", "/login/definir", "/login/ingresar"})


@asynccontextmanager
async def _con_mail_diario(app: FastAPI):
    registro.configurar()
    mail_diario = programador.iniciar()
    yield
    mail_diario.shutdown(wait=False)


def crear_app(config: Config, mail_diario: bool = True) -> FastAPI:
    """`mail_diario=False` en los tests: la app no programa el envío de las 17:00."""
    # Sin /docs ni /openapi.json: serían rutas públicas fuera de RUTAS_PUBLICAS.
    app = FastAPI(
        title="Registro de movimientos",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=_con_mail_diario if mail_diario else None,
    )
    app.state.config = config
    # El último middleware agregado es el que corre primero: la sesión tiene que estar
    # cargada antes de que exigir_sesion la mire.
    app.add_middleware(BaseHTTPMiddleware, dispatch=sesion_web.exigir_sesion(RUTAS_PUBLICAS))
    app.add_middleware(SessionMiddleware, secret_key=config.secret_key, same_site="lax")
    app.include_router(login.router)
    app.include_router(grilla.router)
    app.include_router(formulario.router)
    # También exige sesión: el login no usa htmx.
    app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")
    return app


# Si falta SECRET_KEY, cargar_config() lanza ConfigError y uvicorn no arranca (RF-57).
app = crear_app(cargar_config())
