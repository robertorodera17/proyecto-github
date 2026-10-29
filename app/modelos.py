"""Tablas de la base. Cada cambio necesita su migración de Alembic."""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.clasificacion import CLASIFICACIONES, Tipo
from app.db import Base


class Operador(Base):
    __tablename__ = "operadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Se guarda en mayúsculas, así la unicidad no distingue mayúsculas (RF-29).
    sigla: Mapped[str] = mapped_column(String, unique=True)
    nombre: Mapped[str] = mapped_column(String)
    mail: Mapped[str] = mapped_column(String)
    # Vacío hasta que el operador define su contraseña en el primer ingreso (RF-41, RF-19).
    password_hash: Mapped[str | None] = mapped_column(String, default=None)


class Socio(Base):
    """Recibe el mail diario; no es usuario del sistema ni tiene login (RF-23)."""

    __tablename__ = "socios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String)
    # Se guarda en minúsculas, así la unicidad no distingue mayúsculas (RF-49).
    mail: Mapped[str] = mapped_column(String, unique=True)



class EnvioDiario(Base):
    """Día cuyo mail automático ya se mandó (o se intentó mandar).

    Se registra antes de mandar: la fecha es la clave, así ni un reinicio ni una segunda
    copia de la app lo repiten (RF-39), y un envío fallido no se reintenta (RF-56). El
    envío manual no se registra (RF-54).
    """

    __tablename__ = "envios_diarios"

    fecha: Mapped[date] = mapped_column(primary_key=True)
    registrado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _en(valores) -> str:
    return ", ".join(f"'{v}'" for v in valores)


class Movimiento(Base):
    """Movimiento de dinero. Todos los operadores ven y operan los mismos (RF-22)."""

    __tablename__ = "movimientos"

    # Además de identificar, da el orden de carga: dentro de una fecha, el último
    # cargado va arriba en la grilla (RF-65).
    id: Mapped[int] = mapped_column(primary_key=True)
    descripcion: Mapped[str] = mapped_column(String)
    tipo: Mapped[str] = mapped_column(String)
    # Entero con signo: negativo en egresos y positivo en ingresos (RF-05, RF-06, RF-58).
    monto: Mapped[int]
    clasificacion: Mapped[str] = mapped_column(String)
    fecha: Mapped[date]
    # Baja lógica: nunca se borra la fila (RF-12).
    eliminado: Mapped[bool] = mapped_column(default=False)

    # La validación con mensajes al operador va en el servicio (paso 6). Estas
    # restricciones son la última barrera para que la base no quede inconsistente.
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_en(Tipo)})", name="ck_movimientos_tipo"),
        CheckConstraint(
            f"(tipo = '{Tipo.EGRESO}' AND monto < 0) OR (tipo = '{Tipo.INGRESO}' AND monto > 0)",
            name="ck_movimientos_signo_monto",
        ),
        CheckConstraint(
            " OR ".join(
                f"(tipo = '{tipo}' AND clasificacion IN ({_en(clasificaciones)}))"
                for tipo, clasificaciones in CLASIFICACIONES.items()
            ),
            name="ck_movimientos_clasificacion_del_tipo",
        ),
        # La grilla filtra los no eliminados y ordena por fecha y carga (RF-08, RF-60, RF-65).
        Index("ix_movimientos_grilla", "eliminado", "fecha", "id"),
    )
