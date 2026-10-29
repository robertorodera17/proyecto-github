"""AC-45 (RNF-04): el repositorio no tiene credenciales y .env no se versiona."""

import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SECRETOS = ("SECRET_KEY", "SMTP_USER", "SMTP_PASSWORD")


def _versionados():
    return subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.split()


def test_env_no_esta_versionado_y_esta_ignorado():
    assert ".env" not in _versionados()
    ignorado = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=RAIZ)
    assert ignorado.returncode == 0


def test_el_ejemplo_no_trae_valores_secretos():
    for linea in (RAIZ / ".env.example").read_text().splitlines():
        clave, _, valor = linea.partition("=")
        if clave in SECRETOS:
            assert valor == "", f"{clave} tiene que quedar vacía en .env.example"


def test_la_secret_key_local_no_esta_en_ningun_archivo_versionado():
    env = RAIZ / ".env"
    if not env.exists():
        return
    valores = [
        valor for clave, _, valor in (l.partition("=") for l in env.read_text().splitlines())
        if clave in SECRETOS and len(valor) >= 8
    ]
    for archivo in _versionados():
        ruta = RAIZ / archivo
        if ruta.is_file() and ruta.stat().st_size < 1_000_000:
            contenido = ruta.read_text(errors="ignore")
            assert not any(v in contenido for v in valores), f"{archivo} contiene un valor de .env"
