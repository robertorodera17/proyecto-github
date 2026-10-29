from pathlib import Path

from fastapi.templating import Jinja2Templates

from app import formato

plantillas = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")
plantillas.env.filters["monto"] = formato.monto
plantillas.env.filters["fecha"] = formato.fecha
