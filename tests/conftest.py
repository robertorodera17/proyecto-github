import os

# app.main crea la app al importarse y exige SECRET_KEY (RF-57).
os.environ.setdefault("SECRET_KEY", "clave-de-test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.modelos  # noqa: F401  registra las tablas en Base.metadata
from app.config import Config
from app.db import Base, obtener_sesion
from app.main import crear_app


@pytest.fixture
def engine():
    """Base SQLite en memoria, nueva para cada test y compartida entre hilos."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sesion(engine):
    with Session(engine, expire_on_commit=False) as s:
        yield s


@pytest.fixture
def cliente(engine):
    app = crear_app(Config(secret_key="clave-de-test"), mail_diario=False)

    def sesion_de_test():
        with Session(engine, expire_on_commit=False) as s:
            yield s

    app.dependency_overrides[obtener_sesion] = sesion_de_test
    with TestClient(app) as c:
        yield c


def iniciar_sesion(cliente, sesion, sigla="JP", nombre="Juan"):
    """Crea el operador con contraseña y entra con él."""
    from app.operadores import alta_operador, definir_password

    operador = alta_operador(sesion, sigla, nombre, f"{sigla.lower()}@empresa.com")
    definir_password(sesion, operador, "secreta123")
    respuesta = cliente.post("/login/ingresar", data={"sigla": sigla, "password": "secreta123"}, follow_redirects=False)
    assert respuesta.status_code == 303
    return cliente


@pytest.fixture
def logueado(cliente, sesion):
    """Cliente con sesión iniciada como JP."""
    return iniciar_sesion(cliente, sesion)
