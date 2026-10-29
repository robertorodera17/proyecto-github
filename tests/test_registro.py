import logging
from datetime import datetime, timezone

from app.registro import _FormatoArgentina


def test_el_log_muestra_la_hora_de_argentina():
    registro = logging.LogRecord("app.mail", logging.INFO, __file__, 1, "hola", None, None)
    registro.created = datetime(2026, 10, 21, 20, 0, tzinfo=timezone.utc).timestamp()  # 17:00 en Argentina
    assert _FormatoArgentina("%(asctime)s %(message)s").format(registro) == "2026-10-21 17:00:00 hola"
