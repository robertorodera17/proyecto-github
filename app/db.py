"""Conexión a SQLite con SQLAlchemy 2.x."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import ARCHIVO_ENV

load_dotenv(ARCHIVO_ENV)

URL_BASE = os.environ.get("DATABASE_URL") or f"sqlite:///{ARCHIVO_ENV.parent / 'movimientos.db'}"

engine = create_engine(URL_BASE)
Sesion = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def obtener_sesion():
    """Dependencia de FastAPI: una sesión por pedido."""
    with Sesion() as sesion:
        yield sesion
