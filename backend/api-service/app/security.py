"""Autenticación (JWT de Auth0) y autorización (cuenta activa, rol ADMIN)."""

from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Connection

from .config import Settings, get_settings
from .database import get_db
from .errors import ApiError

bearer = HTTPBearer(auto_error=False)
# Solo en modo dev: aparece en el botón "Authorize" de /docs para elegir el usuario de prueba
dev_user = APIKeyHeader(name="X-Dev-User", auto_error=False, description="Usuario de prueba, por ejemplo demo|ana")


@lru_cache
def _cliente_jwks(dominio: str) -> jwt.PyJWKClient:
    # Las llaves públicas de Auth0 se descargan una vez y se guardan en caché
    return jwt.PyJWKClient(f"https://{dominio}/.well-known/jwks.json", cache_keys=True)


def obtener_sub(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    sub_dev: Annotated[str | None, Depends(dev_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Devuelve el identificador del usuario (`sub`) del JWT ya verificado."""
    if settings.auth_mode == "dev":
        if not sub_dev:
            raise ApiError(401, "NOT_AUTHENTICATED", "Falta el encabezado X-Dev-User (modo desarrollo).")
        return sub_dev

    if credenciales is None:
        raise ApiError(401, "NOT_AUTHENTICATED", "Debes iniciar sesión.")
    try:
        llave = _cliente_jwks(settings.auth0_domain).get_signing_key_from_jwt(credenciales.credentials)
        datos = jwt.decode(
            credenciales.credentials,
            llave.key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(401, "TOKEN_EXPIRED", "Tu sesión expiró. Vuelve a iniciar sesión.") from exc
    except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
        raise ApiError(401, "INVALID_TOKEN", "El token de sesión no es válido.") from exc
    return datos["sub"]


def usuario_actual(
    sub: Annotated[str, Depends(obtener_sub)],
    db: Annotated[Connection, Depends(get_db)],
) -> dict:
    """Usuario registrado, con onboarding completo y cuenta activa."""
    usuario = db.execute("SELECT * FROM users WHERE auth0_id = %s", (sub,)).fetchone()
    if usuario is None:
        raise ApiError(403, "ONBOARDING_REQUIRED", "Completa la configuración inicial de tu perfil.")

    if usuario["account_status"] == "BANNED":
        raise ApiError(403, "ACCOUNT_BANNED", "Tu cuenta fue eliminada por un administrador.")
    if usuario["account_status"] == "SUSPENDED":
        if usuario["suspended_until"] > datetime.now(timezone.utc):
            raise ApiError(403, "ACCOUNT_SUSPENDED", "Tu cuenta está suspendida.",
                           {"suspended_until": usuario["suspended_until"].isoformat()})
        # La suspensión ya terminó: se reactiva la cuenta
        db.execute("UPDATE users SET account_status = 'ACTIVE', suspended_until = NULL WHERE id = %s",
                   (usuario["id"],))
        usuario["account_status"] = "ACTIVE"
    return usuario


def admin_actual(usuario: Annotated[dict, Depends(usuario_actual)]) -> dict:
    if usuario["role"] != "ADMIN":
        raise ApiError(403, "FORBIDDEN", "Solo los administradores pueden hacer esto.")
    return usuario


# Atajos para usar en las rutas
Sub = Annotated[str, Depends(obtener_sub)]
Usuario = Annotated[dict, Depends(usuario_actual)]
Admin = Annotated[dict, Depends(admin_actual)]
Db = Annotated[Connection, Depends(get_db)]
