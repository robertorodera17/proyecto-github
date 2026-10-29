"""Hash de contraseñas con bcrypt, costo 12 (RNF-02)."""

from passlib.context import CryptContext

MIN_CARACTERES = 8  # RF-31
MAX_BYTES = 72  # límite de bcrypt (RF-48, RF-62)

_contexto = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)


def validar_password(password: str) -> str | None:
    """Devuelve el mensaje de error, o None si la contraseña es válida."""
    if len(password) < MIN_CARACTERES:
        return f"La contraseña debe tener al menos {MIN_CARACTERES} caracteres."
    if len(password.encode("utf-8")) > MAX_BYTES:
        return (
            f"La contraseña puede tener hasta {MAX_BYTES} bytes "
            "(72 caracteres sin tildes; cada letra con tilde o ñ ocupa 2)."
        )
    return None


def hashear(password: str) -> str:
    return _contexto.hash(password)


def verificar(password: str, password_hash: str) -> bool:
    return _contexto.verify(password, password_hash)
