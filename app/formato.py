"""Cómo se muestran montos y fechas, igual en la grilla y en el mail (RF-59, RF-63)."""

from datetime import date


def monto(valor: int) -> str:
    """Punto como separador de miles, sin decimales y con signo menos: -1200 -> "-1.200"."""
    texto = f"{abs(valor):,}".replace(",", ".")
    return f"-{texto}" if valor < 0 else texto


def fecha(valor: date) -> str:
    return valor.strftime("%d/%m/%Y")
