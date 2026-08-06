"""Corrección automática del formato PEM para Streamlit Secrets.

Python importa este módulo al iniciar. El parche normaliza la clave privada
antes de que google-auth construya las credenciales de la cuenta de servicio.
"""

from google.oauth2.service_account import Credentials

_original_from_service_account_info = Credentials.from_service_account_info


def _normalizar_private_key(value: object) -> object:
    if not isinstance(value, str):
        return value

    key = value.strip()

    # Convierte los caracteres literales \\n en saltos de línea reales.
    key = key.replace("\\n", "\n")

    # Elimina comillas externas accidentales.
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {"'", '"'}:
        key = key[1:-1].strip()

    # Google espera un salto de línea al final del bloque PEM.
    if key and not key.endswith("\n"):
        key += "\n"

    return key


def _patched_from_service_account_info(cls, info, *args, **kwargs):
    normalized_info = dict(info)
    normalized_info["private_key"] = _normalizar_private_key(
        normalized_info.get("private_key", "")
    )
    return _original_from_service_account_info(normalized_info, *args, **kwargs)


Credentials.from_service_account_info = classmethod(
    _patched_from_service_account_info
)
