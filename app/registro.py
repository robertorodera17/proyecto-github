"""Log de la app en la consola, con hora de Argentina."""

import logging
from datetime import datetime

from app.fechas import ZONA_ARGENTINA


class _FormatoArgentina(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created, ZONA_ARGENTINA).strftime("%Y-%m-%d %H:%M:%S")


def configurar() -> None:
    """Manda a la consola los mensajes del logger "app" (el de uvicorn tiene su propio formato)."""
    logger = logging.getLogger("app")
    if logger.handlers:
        return
    salida = logging.StreamHandler()
    salida.setFormatter(_FormatoArgentina("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(salida)
    logger.setLevel(logging.INFO)
    logger.propagate = False
