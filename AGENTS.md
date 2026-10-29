# AGENTS.md

## Propósito
App web para que un operador cargue, modifique y dé de baja movimientos de ingreso/egreso
de la empresa. A las 17 h envía por mail a los socios los movimientos del día.

## Stack
- Python 3.12 · FastAPI 0.115 · Uvicorn
- Jinja2 + HTMX (sin SPA)
- SQLite · SQLAlchemy 2.x · Alembic
- Clasificación: reglas por palabra clave sobre la descripción (AC-01..05 egresos, AC-06..08 ingresos);
  si no hay coincidencia, elige el operador; la clasificación debe ser válida para el signo del monto (AC-09/10)
- Mail: SMTP (`smtplib`) disparado por APScheduler a las 17:00 de Argentina
- Secretos en `.env`; contraseñas con hash bcrypt (`passlib`)
- Tests: pytest

## Cómo correr
```bash
uv venv .venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt     # el .venv de uv no trae pip: `pip install` no funciona
[ -f .env ] || cp .env.example .env    # y completar SECRET_KEY (ver abajo)
alembic upgrade head
python -m app.operadores alta RO "Nombre" mail@empresa.com
python -m app.socios alta "Nombre" mail@empresa.com
uvicorn app.main:app --reload --host 0.0.0.0   # http://127.0.0.1:8000
pytest
```

- `SECRET_KEY` firma la cookie de sesión y es obligatoria: sin ella la app no arranca. Generarla con
  `python -c "import secrets; print(secrets.token_urlsafe(32))"` y pegarla en `.env`.
- Los operadores se dan de alta solo por consola (`python -m app.operadores alta SIGLA "Nombre" mail`),
  sin contraseña: la definen en su primer ingreso. La sigla es única y se guarda en mayúsculas.
- Los socios también se dan de alta solo por consola (`python -m app.socios alta "Nombre" mail`). No tienen
  login: solo reciben el mail diario. No se admiten dos socios con el mismo mail.
- `--host 0.0.0.0` hace falta en WSL: sin él, el navegador de Windows no llega a la app.

## Mail diario a los socios
- Se manda solo a las 17:00 de Argentina, un mail por socio. Si la app arranca entre las 17:00 y las 18:00
  sin haberlo mandado, lo manda al arrancar. Cada día enviado queda en la tabla `envios_diarios`, así que
  un reinicio no lo repite.
- Configuración SMTP en `.env`. Para Gmail:
  ```
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=cuenta@gmail.com
  SMTP_PASSWORD=contraseña-de-aplicación   # 16 caracteres, de https://myaccount.google.com/apppasswords
  SMTP_FROM=cuenta@gmail.com               # Gmail exige que sea igual a SMTP_USER
  SMTP_SEGURIDAD=starttls                  # starttls | ssl | ninguna
  ```
  Formato `CLAVE=valor`, sin espacios ni comillas. Después de cambiar `.env` hay que reiniciar uvicorn:
  `--reload` solo detecta cambios en archivos `.py`.
- Envío manual (para probar o para reenviar un día que falló): `python -m app.mail enviar [--fecha AAAA-MM-DD]`.
- Probar sin mandar nada a internet: `uvx --from aiosmtpd==1.4.6 aiosmtpd -n -l 127.0.0.1:1025` en una
  terminal, y en otra `SMTP_HOST=127.0.0.1 SMTP_PORT=1025 SMTP_SEGURIDAD=ninguna SMTP_FROM=app@empresa.com SMTP_USER= SMTP_PASSWORD= python -m app.mail enviar`.
  Las variables que no se pisan en el comando salen de `.env`: sin `SMTP_USER=` vacío, intenta loguearse en el
  servidor de prueba con la cuenta de Gmail y falla.
- Los resultados y errores del envío salen en la consola de uvicorn, con hora de Argentina.

## Qué NO hacer
- No borrar movimientos físicamente: la baja es lógica, con el campo "eliminado" (RF-12).
- No poner contraseñas, API keys ni credenciales SMTP en el código ni en el repo; van en `.env` (RNF-02).
- No integrar bancos ni billeteras virtuales (FA-02/03).
- No usar `date.today()` ni `datetime.now()` sin zona: "hoy" es `app.fechas.hoy()`, en hora de Argentina.
- No agregar rutas públicas por fuera de `RUTAS_PUBLICAS` (`app/main.py`): todo lo demás exige sesión (RF-21).
- No levantar dos copias de la app contra la misma base en producción: cada una tiene su programador de mails.
