from app.clasificacion import Tipo, clasificaciones_de, es_valida


def test_ac21_los_tipos_son_exactamente_ingreso_y_egreso():
    assert [t.value for t in Tipo] == ["Ingreso", "Egreso"]


def test_ac17_clasificaciones_de_ingreso():
    assert clasificaciones_de(Tipo.INGRESO) == ("SERVICIOS-PRESTADOS", "ALQUILERES", "FINANCIEROS")


def test_ac18_clasificaciones_de_egreso():
    assert clasificaciones_de(Tipo.EGRESO) == (
        "SUELDOS", "IMPUESTOS-TASAS", "VIATICOS", "PAGO-PROVEEDORES", "TURISMO",
    )


def test_ac09_alquileres_no_es_valida_para_egreso():
    assert not es_valida(Tipo.EGRESO, "ALQUILERES")


def test_ac10_sueldos_no_es_valida_para_ingreso():
    assert not es_valida(Tipo.INGRESO, "SUELDOS")


def test_cada_clasificacion_es_valida_para_su_tipo():
    for tipo in Tipo:
        for clasificacion in clasificaciones_de(tipo):
            assert es_valida(tipo, clasificacion)


def test_la_clasificacion_tiene_que_coincidir_exacta():
    # El valor viene del selector: tiene que coincidir exacto.
    assert not es_valida(Tipo.EGRESO, "sueldos")
