"""Configuración de la app, leída de `.env` y del entorno (RNF-04)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ARCHIVO_ENV = Path(__file__).resolve().parent.parent / ".env"


class ConfigError(RuntimeError):
    """Falta o es inválida una variable obligatoria."""


@dataclass(frozen=True)
class Config:
    secret_key: str


def cargar_config(archivo_env: Path | None = None) -> Config:
    """Lee `.env` (sin pisar variables ya definidas en el entorno) y valida.

    Sin `SECRET_KEY` la app no debe arrancar (RF-57).
    """
    load_dotenv(archivo_env or ARCHIVO_ENV)
    secret_key = os.environ.get("SECRET_KEY", "").strip()
    if not secret_key:
        raise ConfigError(
            "Falta SECRET_KEY en .env. Generala con "
            '`python -c "import secrets; print(secrets.token_urlsafe(32))"`.'
        )
    return Config(secret_key=secret_key)
