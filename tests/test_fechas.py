from datetime import date, datetime, timezone

from app import fechas


def _reloj_fijo(instante_utc: datetime):
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return instante_utc.astimezone(tz)

    return Reloj


def test_ac97_hoy_es_la_fecha_de_argentina_aunque_en_utc_ya_sea_manana(monkeypatch):
    # 01:30 del 21/10/2026 en UTC son las 22:30 del 20/10/2026 en Argentina.
    monkeypatch.setattr(fechas, "datetime", _reloj_fijo(datetime(2026, 10, 21, 1, 30, tzinfo=timezone.utc)))
    assert fechas.hoy() == date(2026, 10, 20)


def test_ahora_tiene_zona_argentina(monkeypatch):
    monkeypatch.setattr(fechas, "datetime", _reloj_fijo(datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc)))
    ahora = fechas.ahora()
    assert ahora.tzinfo == fechas.ZONA_ARGENTINA
    assert (ahora.hour, ahora.minute) == (17, 0)
