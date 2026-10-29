"""Tipos de movimiento, clasificaciones válidas para cada uno (RF-04, RF-13, RF-14)
y la clasificación que propone la descripción (RF-15, RF-16)."""

import re
import unicodedata
from enum import StrEnum


class Tipo(StrEnum):
    INGRESO = "Ingreso"
    EGRESO = "Egreso"


# El orden es el que se muestra en el selector.
CLASIFICACIONES: dict[Tipo, tuple[str, ...]] = {
    Tipo.INGRESO: ("SERVICIOS-PRESTADOS", "ALQUILERES", "FINANCIEROS"),
    Tipo.EGRESO: ("SUELDOS", "IMPUESTOS-TASAS", "VIATICOS", "PAGO-PROVEEDORES", "TURISMO"),
}


def clasificaciones_de(tipo: Tipo) -> tuple[str, ...]:
    return CLASIFICACIONES[tipo]


def es_valida(tipo: Tipo, clasificacion: str) -> bool:
    """La clasificación tiene que pertenecer al tipo (RF-17)."""
    return clasificacion in CLASIFICACIONES[tipo]


# Solo cuentan las palabras clave del tipo elegido (RF-15).
PALABRAS_CLAVE: dict[Tipo, dict[str, str]] = {
    Tipo.EGRESO: {
        "sue": "SUELDOS",
        "imp": "IMPUESTOS-TASAS",
        "via": "VIATICOS",
        "prov": "PAGO-PROVEEDORES",
        "tur": "TURISMO",
    },
    Tipo.INGRESO: {
        "serv": "SERVICIOS-PRESTADOS",
        "alq": "ALQUILERES",
        "fin": "FINANCIEROS",
    },
}

_PALABRA = re.compile(r"[a-z0-9]+")


def _palabras(texto: str) -> list[str]:
    """Palabras en minúscula y sin tildes: "Viáticos Córdoba" -> ["viaticos", "cordoba"]."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return _PALABRA.findall(sin_tildes.lower())


def proponer(tipo: Tipo | str, descripcion: str) -> str | None:
    """La clasificación que propone la descripción, o None si el operador tiene que elegirla.

    La palabra clave tiene que estar al inicio de una palabra: "Factura" no coincide con
    "tur" (RF-15). Si coinciden palabras clave de más de una clasificación, no se propone
    ninguna (RF-16); la misma clasificación repetida cuenta una sola vez (AC-81).
    """
    if tipo not in tuple(Tipo):
        return None
    palabras_clave = PALABRAS_CLAVE[Tipo(tipo)]
    encontradas = {
        clasificacion
        for palabra in _palabras(descripcion)
        for clave, clasificacion in palabras_clave.items()
        if palabra.startswith(clave)
    }
    return encontradas.pop() if len(encontradas) == 1 else None
