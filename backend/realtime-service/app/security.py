"""Autenticación del chat.

El navegador no puede enviar encabezados al abrir un WebSocket, así que el token
llega en el primer mensaje: {"type": "auth", "token": "<JWT de Auth0>"}.
Así el token tampoco queda escrito en la URL ni en los registros del servidor.
"""

from datetime import datetime, timezone
from functools import lru_cache

import jwt
from psycopg import Connection

from .config import Settings


class ErrorAuth(Exception):
    """Error de autenticación o permisos, con un código estable para el frontend."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message


@lru_cache
def _cliente_jwks(dominio: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"https://{dominio}/.well-known/jwks.json", cache_keys=True)


def verificar_token(token: str | None, settings: Settings) -> str:
    """Devuelve el `sub` (identificador del usuario en Auth0) de un token válido."""
    if not token:
        raise ErrorAuth("NOT_AUTHENTICATED", "Debes iniciar sesión.")
    if settings.auth_mode == "dev":
        return token
    try:
        llave = _cliente_jwks(settings.auth0_domain).get_signing_key_from_jwt(token)
        datos = jwt.decode(token, llave.key, algorithms=["RS256"], audience=settings.auth0_audience,
                           issuer=f"https://{settings.auth0_domain}/")
    except jwt.ExpiredSignatureError as exc:
        raise ErrorAuth("TOKEN_EXPIRED", "Tu sesión expiró. Vuelve a iniciar sesión.") from exc
    except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
        raise ErrorAuth("INVALID_TOKEN", "El token de sesión no es válido.") from exc
    return datos["sub"]


def usuario_activo(db: Connection, sub: str) -> dict:
    """Mismas reglas que el api-service: perfil completo y cuenta sin sanción vigente."""
    usuario = db.execute(
        """
        SELECT id, username, avatar_url, role, toxicity_filter_level, account_status, suspended_until
        FROM users WHERE auth0_id = %s
        """,
        (sub,),
    ).fetchone()
    if usuario is None:
        raise ErrorAuth("ONBOARDING_REQUIRED", "Completa la configuración inicial de tu perfil.")
    if usuario["account_status"] == "BANNED":
        raise ErrorAuth("ACCOUNT_BANNED", "Tu cuenta fue eliminada por un administrador.")
    if usuario["account_status"] == "SUSPENDED" and usuario["suspended_until"] > datetime.now(timezone.utc):
        raise ErrorAuth("ACCOUNT_SUSPENDED", "Tu cuenta está suspendida.")
    return usuario


def acceso_a_sala(db: Connection, post_id: int, usuario_id: int) -> dict:
    """Solo los integrantes (anfitrión o aceptados) entran al chat de una sala."""
    sala = db.execute(
        """
        SELECT p.id, p.status,
               EXISTS (SELECT 1 FROM v_post_members m WHERE m.post_id = p.id AND m.user_id = %s) AS es_miembro
        FROM lfg_posts p WHERE p.id = %s
        """,
        (usuario_id, post_id),
    ).fetchone()
    if sala is None:
        raise ErrorAuth("POST_NOT_FOUND", "Esa sala no existe.")
    if not sala["es_miembro"]:
        raise ErrorAuth("NOT_A_MEMBER", "Solo los integrantes de la sala pueden usar su chat.")
    return sala
