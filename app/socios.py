"""Alta de socios, solo por consola (RF-35, FA-05).

Uso: python -m app.socios alta "Nombre" mail
"""

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos import Socio


class SocioInvalido(ValueError):
    pass


def normalizar_mail(mail: str) -> str:
    return mail.strip().lower()


def alta_socio(sesion: Session, nombre: str, mail: str) -> Socio:
    """Crea un socio. Rechaza el alta sin mail (RF-23) o con un mail que ya existe,
    sin distinguir mayúsculas (RF-49). El formato del mail no se valida (FA-06)."""
    mail = normalizar_mail(mail)
    if not mail:
        raise SocioInvalido("El socio tiene que tener mail.")
    if sesion.scalar(select(Socio).where(Socio.mail == mail)):
        raise SocioInvalido(f"Ya existe un socio con el mail {mail}")
    socio = Socio(nombre=nombre.strip(), mail=mail)
    sesion.add(socio)
    try:
        sesion.commit()
    except IntegrityError:
        # Otra alta con el mismo mail entró entre la consulta y el commit.
        sesion.rollback()
        raise SocioInvalido(f"Ya existe un socio con el mail {mail}") from None
    return socio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.socios")
    comandos = parser.add_subparsers(dest="comando", required=True)
    alta = comandos.add_parser("alta", help="dar de alta un socio que recibe el mail diario")
    alta.add_argument("nombre")
    alta.add_argument("mail")
    args = parser.parse_args(argv)

    from app.db import Sesion

    with Sesion() as sesion:
        try:
            socio = alta_socio(sesion, args.nombre, args.mail)
        except SocioInvalido as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    print(f"Socio {socio.nombre} <{socio.mail}> creado. Va a recibir el mail diario de las 17:00.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
