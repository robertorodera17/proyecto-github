"""Alta y modificación de movimientos, con la validación del lado del servidor.

Las mismas reglas valen para el alta y la modificación (RF-26). Lo que llega del
formulario son textos: acá se validan todos los campos juntos, así cada uno puede
mostrar su error (AC-19).
"""

import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import fechas
from app.clasificacion import Tipo, es_valida
from app.modelos import Movimiento

# Mayor entero que guarda SQLite. El PRD no fija monto máximo; esto evita que un
# número absurdo termine en un error interno en vez de un mensaje en el campo.
MONTO_MAXIMO = 2**63 - 1

_SOLO_DIGITOS = re.compile(r"[0-9]+")
_CON_SEPARADOR_DE_MILES = re.compile(r"[0-9]{1,3}(\.[0-9]{3})+")
_CON_DECIMALES = re.compile(r"[0-9]*[.,][0-9]+")
_FECHA_ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

POR_PAGINA = 30  # RF-61


@dataclass
class DatosMovimiento:
    """Campos tal como llegan del formulario."""

    descripcion: str = ""
    tipo: str = ""
    monto: str = ""
    clasificacion: str = ""
    fecha: str = ""


@dataclass(frozen=True)
class MovimientoValido:
    descripcion: str
    tipo: Tipo
    monto: int  # ya con el signo del tipo
    clasificacion: str
    fecha: date


class MovimientoInvalido(ValueError):
    def __init__(self, errores: dict[str, str]):
        super().__init__(errores)
        self.errores = errores  # campo -> mensaje


class MovimientoNoEncontrado(LookupError):
    pass


def _validar_monto(texto: str) -> tuple[int | None, str | None]:
    if not texto:
        return None, "El monto es obligatorio."
    if _CON_SEPARADOR_DE_MILES.fullmatch(texto):
        return None, "Escribí el monto solo con dígitos, sin separador de miles (por ejemplo, 1200)."
    if _CON_DECIMALES.fullmatch(texto):
        return None, "El monto no admite decimales."
    if not _SOLO_DIGITOS.fullmatch(texto):
        return None, "El monto tiene que ser un número entero mayor que 0."
    monto = int(texto)
    if monto == 0:
        return None, "El monto tiene que ser un número entero mayor que 0."
    if monto > MONTO_MAXIMO:
        return None, "El monto es demasiado grande."
    return monto, None


def _validar_fecha(texto: str) -> tuple[date | None, str | None]:
    if not texto:
        return fechas.hoy(), None  # RF-43
    if not _FECHA_ISO.fullmatch(texto):
        return None, "La fecha no es válida."
    try:
        return date.fromisoformat(texto), None
    except ValueError:
        return None, "La fecha no existe."  # RF-44, por ejemplo 30/02


def validar(datos: DatosMovimiento) -> MovimientoValido:
    """Devuelve el movimiento listo para guardar o lanza MovimientoInvalido con todos los errores."""
    errores: dict[str, str] = {}

    descripcion = datos.descripcion.strip()
    if not descripcion:
        errores["descripcion"] = "La descripción es obligatoria."

    tipo: Tipo | None = None
    if not datos.tipo:
        errores["tipo"] = "Elegí el tipo de movimiento."
    elif datos.tipo in tuple(Tipo):
        tipo = Tipo(datos.tipo)
    else:
        errores["tipo"] = "El tipo tiene que ser Ingreso o Egreso."

    monto, error = _validar_monto(datos.monto.strip())
    if error:
        errores["monto"] = error

    clasificacion = datos.clasificacion.strip()
    if not clasificacion:
        errores["clasificacion"] = "Elegí una clasificación."
    elif tipo is not None and not es_valida(tipo, clasificacion):
        errores["clasificacion"] = f"La clasificación {clasificacion} no corresponde a un {tipo}."  # RF-17

    fecha, error = _validar_fecha(datos.fecha.strip())
    if error:
        errores["fecha"] = error

    if errores:
        raise MovimientoInvalido(errores)

    return MovimientoValido(
        descripcion=descripcion,
        tipo=tipo,
        monto=-monto if tipo is Tipo.EGRESO else monto,  # RF-05, RF-06
        clasificacion=clasificacion,
        fecha=fecha,
    )


def crear(sesion: Session, datos: DatosMovimiento) -> Movimiento:
    valido = validar(datos)
    movimiento = Movimiento(
        descripcion=valido.descripcion,
        tipo=valido.tipo.value,
        monto=valido.monto,
        clasificacion=valido.clasificacion,
        fecha=valido.fecha,
    )
    sesion.add(movimiento)
    sesion.commit()
    return movimiento


def obtener(sesion: Session, movimiento_id: int) -> Movimiento:
    """Un movimiento no eliminado; los eliminados no se pueden ver ni restaurar (FA-09)."""
    movimiento = sesion.scalar(
        select(Movimiento).where(Movimiento.id == movimiento_id, Movimiento.eliminado.is_(False))
    )
    if movimiento is None:
        raise MovimientoNoEncontrado(movimiento_id)
    return movimiento


def modificar(sesion: Session, movimiento_id: int, datos: DatosMovimiento) -> Movimiento:
    """Aplica las mismas validaciones que el alta; se puede cambiar todo, incluida la fecha (RF-26, RF-27)."""
    movimiento = obtener(sesion, movimiento_id)
    valido = validar(datos)
    movimiento.descripcion = valido.descripcion
    movimiento.tipo = valido.tipo.value
    movimiento.monto = valido.monto
    movimiento.clasificacion = valido.clasificacion
    movimiento.fecha = valido.fecha
    sesion.commit()
    return movimiento


def eliminar(sesion: Session, movimiento_id: int) -> None:
    """Baja lógica: marca el campo eliminado y nunca borra la fila (RF-12)."""
    obtener(sesion, movimiento_id).eliminado = True
    sesion.commit()


@dataclass(frozen=True)
class Pagina:
    movimientos: list[Movimiento]
    numero: int
    total_paginas: int


def listar(sesion: Session, pagina: int = 1) -> Pagina:
    """Movimientos no eliminados de cualquier fecha, de a 30 (RF-08, RF-61).

    Ordenados por fecha descendente y, dentro de una fecha, el último cargado arriba
    (RF-60, RF-65). Una página fuera de rango muestra la más cercana.
    """
    no_eliminados = Movimiento.eliminado.is_(False)
    total = sesion.scalar(select(func.count()).select_from(Movimiento).where(no_eliminados))
    total_paginas = max(1, -(-total // POR_PAGINA))
    numero = min(max(1, pagina), total_paginas)
    filas = sesion.scalars(
        select(Movimiento)
        .where(no_eliminados)
        .order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
        .limit(POR_PAGINA)
        .offset((numero - 1) * POR_PAGINA)
    ).all()
    return Pagina(movimientos=list(filas), numero=numero, total_paginas=total_paginas)


def del_dia(sesion: Session, fecha: date) -> list[Movimiento]:
    """Movimientos no eliminados de una fecha, en el orden en que se cargaron (RF-24)."""
    return list(
        sesion.scalars(
            select(Movimiento)
            .where(Movimiento.fecha == fecha, Movimiento.eliminado.is_(False))
            .order_by(Movimiento.id)
        )
    )
