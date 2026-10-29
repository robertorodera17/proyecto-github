import time

import pytest

from app.clasificacion import CLASIFICACIONES, PALABRAS_CLAVE, Tipo, proponer


@pytest.mark.parametrize(
    "tipo, descripcion, propuesta",
    [
        (Tipo.EGRESO, "Sueldo marzo", "SUELDOS"),  # AC-01
        (Tipo.EGRESO, "Impuesto municipal", "IMPUESTOS-TASAS"),  # AC-02
        (Tipo.EGRESO, "Viáticos Córdoba", "VIATICOS"),  # AC-03
        (Tipo.EGRESO, "Proveedor de resmas", "PAGO-PROVEEDORES"),  # AC-04
        (Tipo.EGRESO, "Turismo Bariloche", "TURISMO"),  # AC-05
        (Tipo.INGRESO, "Servicio de consultoría", "SERVICIOS-PRESTADOS"),  # AC-06
        (Tipo.INGRESO, "Alquiler local", "ALQUILERES"),  # AC-07
        (Tipo.INGRESO, "Financiación cliente", "FINANCIEROS"),  # AC-08
        (Tipo.EGRESO, "VIATICO cordoba", "VIATICOS"),  # AC-14
        (Tipo.EGRESO, "Sueldo marzo y sueldo abril", "SUELDOS"),  # AC-81
    ],
)
def test_propone_la_clasificacion_de_la_palabra_clave(tipo, descripcion, propuesta):
    assert proponer(tipo, descripcion) == propuesta


@pytest.mark.parametrize(
    "descripcion",
    [
        "Compra de café",  # AC-12: ninguna palabra clave
        "Impuesto sobre sueldos",  # AC-13: dos clasificaciones
        "Factura de luz",  # AC-15: "tur" no está al inicio de una palabra
        "Alquiler oficina",  # AC-16: palabra clave de Ingreso en un Egreso
        "",
    ],
)
def test_no_propone_nada_y_elige_el_operador(descripcion):
    assert proponer(Tipo.EGRESO, descripcion) is None


def test_la_palabra_clave_puede_estar_en_cualquier_palabra():
    assert proponer(Tipo.EGRESO, "Pago a proveedores") == "PAGO-PROVEEDORES"


def test_los_signos_separan_palabras():
    assert proponer(Tipo.EGRESO, "Pago/proveedores") == "PAGO-PROVEEDORES"
    assert proponer(Tipo.INGRESO, "(Alquiler) local") == "ALQUILERES"


def test_la_palabra_entera_tambien_coincide():
    assert proponer(Tipo.EGRESO, "Sue") == "SUELDOS"


def test_acepta_el_tipo_como_texto_del_formulario():
    assert proponer("Egreso", "Sueldo marzo") == "SUELDOS"


@pytest.mark.parametrize("tipo", ["", "Otro"])
def test_sin_tipo_valido_no_propone(tipo):
    assert proponer(tipo, "Sueldo marzo") is None


def test_cada_palabra_clave_propone_una_clasificacion_de_su_tipo():
    for tipo, palabras_clave in PALABRAS_CLAVE.items():
        assert set(palabras_clave.values()) == set(CLASIFICACIONES[tipo])


def test_es_rapido_con_descripciones_largas():
    # RNF-01 pide menos de 2 s incluyendo la red; el clasificador tiene que ser despreciable.
    descripcion = "palabra " * 2000 + "sueldo"
    inicio = time.perf_counter()
    for _ in range(100):
        proponer(Tipo.EGRESO, descripcion)
    assert (time.perf_counter() - inicio) / 100 < 0.05
