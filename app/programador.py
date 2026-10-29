"""Mail automático de las 17:00 de Argentina (RF-24, RF-38, RF-39, RF-52, RF-53).

Cada copia de la app tiene su programador: no levantar dos contra la misma base en
producción. Si pasara, el registro en envios_diarios igual evita el mail repetido.
"""

import logging
from datetime import date, datetime, time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import db, fechas, formato, mail
from app.modelos import EnvioDiario

log = logging.getLogger("app.programador")

HORA_DE_ENVIO = time(17, 0)
FIN_DE_LA_VENTANA = time(18, 0)  # al arrancar desde esta hora ya no se manda (RF-52)
_VENTANA_EN_SEGUNDOS = 60 * 60


def ya_enviado(sesion: Session, fecha: date) -> bool:
    return sesion.get(EnvioDiario, fecha) is not None


def envio_automatico(sesion: Session, fecha: date) -> bool:
    """Registra el día y después manda. Devuelve False si ese día ya estaba registrado.

    El registro va primero y se confirma antes de mandar: si dos procesos llegan a la
    vez, la clave de la tabla deja pasar a uno solo (RF-39). Si el envío falla, el día
    queda registrado igual y no se reintenta; se reenvía a mano (RF-56, RF-40).
    """
    sesion.add(EnvioDiario(fecha=fecha, registrado_en=fechas.ahora()))
    try:
        sesion.commit()
    except IntegrityError:
        sesion.rollback()
        log.info("El mail del %s ya se había mandado; no se repite.", formato.fecha(fecha))
        return False
    mail.enviar(sesion, fecha)
    return True


def al_arrancar(sesion: Session, ahora: datetime) -> None:
    """Si la app arranca después de las 17:00 sin haber mandado el mail del día (RF-38, RF-52, RF-53)."""
    hoy = ahora.date()
    if ahora.time() < HORA_DE_ENVIO or ya_enviado(sesion, hoy):
        return
    if ahora.time() < FIN_DE_LA_VENTANA:
        log.info("La app arrancó a las %s sin haber mandado el mail de hoy: se manda ahora.", ahora.strftime("%H:%M"))
        envio_automatico(sesion, hoy)
    else:
        log.warning(
            "El mail del %s no se mandó: la app estuvo apagada entre las 17:00 y las 18:00. "
            "Para mandarlo a mano: python -m app.mail enviar --fecha %s",
            formato.fecha(hoy),
            hoy.isoformat(),
        )


def _tarea_de_las_17() -> None:
    with db.Sesion() as sesion:
        envio_automatico(sesion, fechas.hoy())


def _tarea_al_arrancar() -> None:
    with db.Sesion() as sesion:
        al_arrancar(sesion, fechas.ahora())


def _sin_errores_sueltos(tarea):
    # Un error inesperado (por ejemplo, la base bloqueada) tiene que quedar en el log
    # de la app con su explicación, no perderse en el de APScheduler.
    def envoltura():
        try:
            tarea()
        except Exception:
            log.exception("Falló la tarea del mail diario")

    envoltura.__name__ = tarea.__name__
    return envoltura


def crear() -> BackgroundScheduler:
    """Programador con el envío diario a las 17:00 de Argentina, todos los días (RF-24)."""
    programador = BackgroundScheduler(timezone=fechas.ZONA_ARGENTINA)
    programador.add_job(
        _sin_errores_sueltos(_tarea_de_las_17),
        CronTrigger(hour=HORA_DE_ENVIO.hour, minute=HORA_DE_ENVIO.minute, timezone=fechas.ZONA_ARGENTINA),
        id="mail_diario",
        # Si la tarea arranca tarde (máquina ocupada o suspendida), se manda igual hasta las 18:00.
        misfire_grace_time=_VENTANA_EN_SEGUNDOS,
        coalesce=True,
    )
    return programador


def iniciar() -> BackgroundScheduler:
    programador = crear()
    # La revisión del arranque va en segundo plano: un envío lento no demora el inicio de la app.
    programador.add_job(_sin_errores_sueltos(_tarea_al_arrancar), id="mail_al_arrancar")
    programador.start()
    proxima = programador.get_job("mail_diario").next_run_time
    log.info("Mail diario programado. Próximo envío: %s.", proxima.strftime("%d/%m/%Y %H:%M"))
    return programador
