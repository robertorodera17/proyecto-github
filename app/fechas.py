"""Fecha y hora de Argentina, sin importar la zona del servidor (RF-03).

Usar siempre `hoy()` y `ahora()`; nunca `date.today()` ni `datetime.now()` sin zona.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA_ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")


def ahora() -> datetime:
    return datetime.now(ZONA_ARGENTINA)


def hoy() -> date:
    return ahora().date()
