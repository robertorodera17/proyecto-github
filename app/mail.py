"""Mail diario a los socios con los movimientos del día (RF-24, RF-25).

Envío manual: python -m app.mail enviar [--fecha AAAA-MM-DD]
"""

import argparse
import logging
import os
import smtplib
import ssl
import sys
from dataclasses import dataclass, field
from datetime import date
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import fechas, formato, movimientos, registro
from app.config import ARCHIVO_ENV
from app.modelos import Movimiento, Socio

log = logging.getLogger("app.mail")

SEGURIDADES = {"starttls": 587, "ssl": 465, "ninguna": 25}  # seguridad -> puerto por defecto
TIEMPO_MAXIMO = 30  # segundos para conectar y para cada respuesta del servidor


def asunto(fecha: date) -> str:
    return f"Movimientos del {formato.fecha(fecha)}"  # RF-50


def _en_una_linea(texto: str) -> str:
    # El formulario no deja escribir saltos de línea, pero un pedido armado a mano sí
    # podría: cada movimiento tiene que ocupar una sola línea (RF-68).
    return " ".join(texto.split())


def linea(movimiento: Movimiento) -> str:
    """Descripción, monto, tipo, clasificación y fecha (RF-25), con el monto como en la grilla (RF-63)."""
    return " | ".join(
        [
            _en_una_linea(movimiento.descripcion),
            formato.monto(movimiento.monto),
            movimiento.tipo,
            movimiento.clasificacion,
            formato.fecha(movimiento.fecha),
        ]
    )


def cuerpo(fecha: date, movimientos: list[Movimiento]) -> str:
    renglones = [asunto(fecha), "", f"Cantidad de movimientos: {len(movimientos)}", ""]  # RF-51
    if movimientos:
        renglones.append("Descripción | Monto | Tipo | Clasificación | Fecha")
        renglones.extend(linea(m) for m in movimientos)  # RF-68
    else:
        renglones.append("No hubo movimientos.")  # RF-37
    return "\n".join(renglones) + "\n"


def armar(fecha: date, movimientos: list[Movimiento], remitente: str, destinatario: str) -> EmailMessage:
    """Un mail en texto plano para un solo socio (RF-36, RF-67)."""
    mensaje = EmailMessage()
    mensaje["Subject"] = asunto(fecha)
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje["Date"] = format_datetime(fechas.ahora())
    mensaje["Message-ID"] = make_msgid()
    # quoted-printable deja el texto legible en crudo (por ejemplo, en aiosmtpd); solo codifica las tildes.
    mensaje.set_content(cuerpo(fecha, movimientos), cte="quoted-printable")
    return mensaje


# --- Configuración SMTP (RNF-04: todo viene de .env) ---


class ConfigSmtpIncompleta(ValueError):
    pass


@dataclass(frozen=True)
class ConfigSmtp:
    host: str
    puerto: int
    usuario: str
    password: str = field(repr=False)  # que no aparezca si se loguea la configuración
    remitente: str
    seguridad: str


def cargar_config_smtp() -> ConfigSmtp:
    load_dotenv(ARCHIVO_ENV)
    leer = lambda clave: os.environ.get(clave, "").strip()  # noqa: E731
    host, usuario, password = leer("SMTP_HOST"), leer("SMTP_USER"), leer("SMTP_PASSWORD")
    remitente = leer("SMTP_FROM") or usuario
    seguridad = (leer("SMTP_SEGURIDAD") or "starttls").lower()

    faltan = [clave for clave, valor in (("SMTP_HOST", host), ("SMTP_FROM", remitente)) if not valor]
    if usuario and not password:
        faltan.append("SMTP_PASSWORD")
    if faltan:
        raise ConfigSmtpIncompleta(f"falta {', '.join(faltan)} en .env")
    if seguridad not in SEGURIDADES:
        raise ConfigSmtpIncompleta(f"SMTP_SEGURIDAD={seguridad} no es válido: usar starttls, ssl o ninguna")
    puerto_texto = leer("SMTP_PORT")
    if puerto_texto and not puerto_texto.isdigit():
        raise ConfigSmtpIncompleta(f"SMTP_PORT={puerto_texto} no es un número")
    puerto = int(puerto_texto) if puerto_texto else SEGURIDADES[seguridad]
    return ConfigSmtp(host, puerto, usuario, password, remitente, seguridad)


# --- Envío ---


@dataclass
class ResultadoEnvio:
    enviados: list[str] = field(default_factory=list)
    fallidos: list[str] = field(default_factory=list)
    error_general: str | None = None  # configuración incompleta o sin socios

    @property
    def ok(self) -> bool:
        return self.error_general is None and not self.fallidos


def _conectar(config: ConfigSmtp) -> smtplib.SMTP:
    if config.seguridad == "ssl":
        conexion = smtplib.SMTP_SSL(
            config.host, config.puerto, timeout=TIEMPO_MAXIMO, context=ssl.create_default_context()
        )
    else:
        conexion = smtplib.SMTP(config.host, config.puerto, timeout=TIEMPO_MAXIMO)
        if config.seguridad == "starttls":
            conexion.starttls(context=ssl.create_default_context())
    if config.usuario:
        conexion.login(config.usuario, config.password)
    return conexion


def _mandar(config: ConfigSmtp, mensaje: EmailMessage) -> None:
    with _conectar(config) as conexion:
        conexion.send_message(mensaje)


def enviar(sesion: Session, fecha: date) -> ResultadoEnvio:
    """Manda a cada socio, por separado, el mail de la fecha (RF-36).

    Cada error queda en el log y no se reintenta (RF-55, RF-56). Una conexión por socio:
    si una dirección falla, los demás lo reciben igual (AC-61).
    """
    resultado = ResultadoEnvio()
    try:
        config = cargar_config_smtp()
    except ConfigSmtpIncompleta as e:
        resultado.error_general = f"Configuración SMTP incompleta: {e}"
        log.error("No se mandó el mail del %s. %s", formato.fecha(fecha), resultado.error_general)
        return resultado

    socios = sesion.scalars(select(Socio).order_by(Socio.id)).all()
    if not socios:
        resultado.error_general = "No hay socios dados de alta (python -m app.socios alta \"Nombre\" mail)"
        log.warning("No se mandó el mail del %s. %s", formato.fecha(fecha), resultado.error_general)
        return resultado

    del_dia = movimientos.del_dia(sesion, fecha)
    for socio in socios:
        try:
            _mandar(config, armar(fecha, del_dia, config.remitente, socio.mail))
        except (smtplib.SMTPException, OSError) as e:
            resultado.fallidos.append(socio.mail)
            log.error("No se pudo mandar el mail del %s a %s: %s", formato.fecha(fecha), socio.mail, _describir(e))
        else:
            resultado.enviados.append(socio.mail)

    log.info(
        "Mail del %s (%d movimientos): enviado a %d de %d socios.",
        formato.fecha(fecha), len(del_dia), len(resultado.enviados), len(socios),
    )
    return resultado


def _describir(error: Exception) -> str:
    if isinstance(error, smtplib.SMTPRecipientsRefused):
        return "el servidor rechazó la dirección " + "; ".join(
            f"{codigo} {texto.decode(errors='replace')}" for codigo, texto in error.recipients.values()
        )
    if isinstance(error, smtplib.SMTPAuthenticationError):
        return "usuario o contraseña SMTP incorrectos (con Gmail hace falta una contraseña de aplicación)"
    if isinstance(error, smtplib.SMTPNotSupportedError) and "AUTH" in str(error):
        return "el servidor no acepta usuario y contraseña: dejar vacíos SMTP_USER y SMTP_PASSWORD"
    if isinstance(error, (ConnectionError, TimeoutError, OSError)) and not isinstance(error, smtplib.SMTPException):
        return f"no se pudo conectar con el servidor de correo ({error})"
    return str(error) or type(error).__name__


# --- Consola ---


def _fecha(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{texto} no es una fecha AAAA-MM-DD válida") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.mail")
    comandos = parser.add_subparsers(dest="comando", required=True)
    enviar_cmd = comandos.add_parser("enviar", help="mandar a mano el mail de un día a todos los socios")
    enviar_cmd.add_argument("--fecha", type=_fecha, help="AAAA-MM-DD; por defecto, hoy en Argentina")
    args = parser.parse_args(argv)

    registro.configurar()
    from app.db import Sesion

    with Sesion() as sesion:
        # El envío manual no queda registrado como enviado: siempre manda (RF-54).
        resultado = enviar(sesion, args.fecha or fechas.hoy())
    return 0 if resultado.ok else 1


if __name__ == "__main__":
    sys.exit(main())
