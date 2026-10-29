"""Alta de operadores, solo por consola (RF-30, FA-04).

Uso: python -m app.operadores alta SIGLA "Nombre" mail
"""

import argparse
import sys

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import seguridad
from app.modelos import Operador


class OperadorDuplicado(ValueError):
    pass


class PasswordYaDefinida(ValueError):
    pass


def normalizar_sigla(sigla: str) -> str:
    return sigla.strip().upper()


def buscar_por_sigla(sesion: Session, sigla: str) -> Operador | None:
    """El login no distingue mayúsculas: "ro" es "RO" (RF-29)."""
    return sesion.scalar(select(Operador).where(Operador.sigla == normalizar_sigla(sigla)))


def definir_password(sesion: Session, operador: Operador, password: str) -> None:
    """Guarda la contraseña del primer ingreso (RF-19).

    Solo si el operador todavía no tiene una: la condición va en el UPDATE para que
    dos pedidos simultáneos no puedan pisarse (AC-52).
    """
    resultado = sesion.execute(
        update(Operador)
        .where(Operador.id == operador.id, Operador.password_hash.is_(None))
        .values(password_hash=seguridad.hashear(password))
    )
    sesion.commit()
    if resultado.rowcount != 1:
        raise PasswordYaDefinida(f"El operador {operador.sigla} ya tiene contraseña.")
    sesion.refresh(operador)


def autenticar(sesion: Session, sigla: str, password: str) -> Operador | None:
    """Devuelve el operador si la sigla y la contraseña coinciden (RF-20)."""
    operador = buscar_por_sigla(sesion, sigla)
    if operador is None or operador.password_hash is None:
        return None
    if not seguridad.verificar(password, operador.password_hash):
        return None
    return operador


def alta_operador(sesion: Session, sigla: str, nombre: str, mail: str) -> Operador:
    """Crea un operador sin contraseña (RF-18, RF-41).

    Rechaza una sigla que ya exista, sin distinguir mayúsculas (RF-29).
    """
    sigla = normalizar_sigla(sigla)
    if buscar_por_sigla(sesion, sigla):
        raise OperadorDuplicado(f"Ya existe un operador con la sigla {sigla}")
    operador = Operador(sigla=sigla, nombre=nombre.strip(), mail=mail.strip())
    sesion.add(operador)
    try:
        sesion.commit()
    except IntegrityError:
        # Otra alta con la misma sigla entró entre la consulta y el commit.
        sesion.rollback()
        raise OperadorDuplicado(f"Ya existe un operador con la sigla {sigla}") from None
    return operador


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.operadores")
    comandos = parser.add_subparsers(dest="comando", required=True)
    alta = comandos.add_parser("alta", help="dar de alta un operador sin contraseña")
    alta.add_argument("sigla")
    alta.add_argument("nombre")
    alta.add_argument("mail")
    args = parser.parse_args(argv)

    from app.db import Sesion

    with Sesion() as sesion:
        try:
            operador = alta_operador(sesion, args.sigla, args.nombre, args.mail)
        except OperadorDuplicado as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    print(f"Operador {operador.sigla} creado. Define su contraseña en el primer ingreso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
