"""Usuarios: onboarding, perfil, cuentas vinculadas, perfil público y lista negra."""

from fastapi import APIRouter, Response
from psycopg import Connection

from ..errors import ApiError
from ..schemas import Bloqueo, CuentaVinculada, Onboarding, PerfilActualizar, Proveedor
from ..security import Db, Sub, Usuario

router = APIRouter(prefix="/users", tags=["Usuarios"])

# Campos que se pueden ver de otros jugadores (nunca auth0_id ni datos internos)
CAMPOS_PUBLICOS = ("id, username, region, avatar_url, xp, level, preferred_language_speak, "
                   "preferred_language_write, created_at")


def _preferencias(db: Connection, usuario_id: int) -> dict:
    juegos = db.execute("SELECT game_id FROM user_games WHERE user_id = %s ORDER BY game_id",
                        (usuario_id,)).fetchall()
    generos = db.execute("SELECT genre_id FROM user_genres WHERE user_id = %s ORDER BY genre_id",
                         (usuario_id,)).fetchall()
    cuentas = db.execute("SELECT provider, external_username FROM linked_accounts WHERE user_id = %s",
                         (usuario_id,)).fetchall()
    return {
        "games": [j["game_id"] for j in juegos],
        "genres": [g["genre_id"] for g in generos],
        "linked_accounts": {c["provider"]: c["external_username"] for c in cuentas},
    }


def _perfil_privado(db: Connection, usuario_id: int) -> dict:
    perfil = db.execute(
        """
        SELECT id, username, region, avatar_url, xp, level, warnings_count, role, account_status,
               ui_language, preferred_language_speak, preferred_language_write,
               toxicity_filter_level, is_onboarding_completed, created_at
        FROM users WHERE id = %s
        """,
        (usuario_id,),
    ).fetchone()
    return perfil | _preferencias(db, usuario_id)


def _guardar_preferencias(db: Connection, usuario_id: int, juegos: list[int] | None, generos: list[int] | None):
    if juegos is not None:
        db.execute("DELETE FROM user_games WHERE user_id = %s", (usuario_id,))
        with db.cursor() as cur:
            cur.executemany("INSERT INTO user_games (user_id, game_id) VALUES (%s, %s)",
                            [(usuario_id, j) for j in sorted(set(juegos))])
    if generos is not None:
        db.execute("DELETE FROM user_genres WHERE user_id = %s", (usuario_id,))
        with db.cursor() as cur:
            cur.executemany("INSERT INTO user_genres (user_id, genre_id) VALUES (%s, %s)",
                            [(usuario_id, g) for g in sorted(set(generos))])


def _nombre_libre(db: Connection, username: str, excepto_id: int | None = None) -> None:
    ocupado = db.execute(
        "SELECT 1 FROM users WHERE LOWER(username) = LOWER(%s) AND id IS DISTINCT FROM %s",
        (username, excepto_id),
    ).fetchone()
    if ocupado:
        raise ApiError(409, "USERNAME_TAKEN", "Ese nombre de usuario ya está en uso.")


# ---------------------------------------------------------------------------
# Mi perfil
# ---------------------------------------------------------------------------
@router.post("/onboarding", status_code=201, summary="Crear el perfil después del primer inicio de sesión")
def onboarding(datos: Onboarding, sub: Sub, db: Db) -> dict:
    if db.execute("SELECT 1 FROM users WHERE auth0_id = %s", (sub,)).fetchone():
        raise ApiError(409, "ALREADY_ONBOARDED", "Tu perfil ya fue configurado.")
    _nombre_libre(db, datos.username)

    with db.transaction():
        usuario_id = db.execute(
            """
            INSERT INTO users (auth0_id, username, region, ui_language, preferred_language_speak,
                               preferred_language_write, toxicity_filter_level, is_onboarding_completed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
            RETURNING id
            """,
            (sub, datos.username, datos.region, datos.ui_language, datos.preferred_language_speak,
             datos.preferred_language_write, datos.toxicity_filter_level),
        ).fetchone()["id"]
        _guardar_preferencias(db, usuario_id, datos.games, datos.genres)
    return _perfil_privado(db, usuario_id)


@router.get("/me", summary="Mi perfil completo")
def mi_perfil(usuario: Usuario, db: Db) -> dict:
    return _perfil_privado(db, usuario["id"])


@router.put("/me", summary="Actualizar mi perfil (solo los campos enviados)")
def actualizar_perfil(datos: PerfilActualizar, usuario: Usuario, db: Db) -> dict:
    cambios = datos.model_dump(exclude_unset=True, exclude={"games", "genres"})
    if "username" in cambios:
        _nombre_libre(db, cambios["username"], usuario["id"])

    with db.transaction():
        if cambios:
            # Los nombres de columna vienen del modelo (lista cerrada), nunca del usuario
            columnas = ", ".join(f"{campo} = %({campo})s" for campo in cambios)
            db.execute(f"UPDATE users SET {columnas} WHERE id = %(id)s", cambios | {"id": usuario["id"]})
        _guardar_preferencias(db, usuario["id"], datos.games, datos.genres)
    return _perfil_privado(db, usuario["id"])


@router.delete("/me", status_code=204, summary="Eliminar mi cuenta y todos mis datos")
def eliminar_cuenta(usuario: Usuario, db: Db) -> Response:
    # Las FK con ON DELETE CASCADE borran salas, solicitudes, reseñas, mensajes, etc.
    db.execute("DELETE FROM users WHERE id = %s", (usuario["id"],))
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Cuentas vinculadas (rutas de la propuesta: /users/social/{provider})
# ---------------------------------------------------------------------------
@router.put("/social/{provider}", summary="Vincular o cambiar una cuenta externa")
def vincular_cuenta(provider: Proveedor, datos: CuentaVinculada, usuario: Usuario, db: Db) -> dict:
    db.execute(
        """
        INSERT INTO linked_accounts (user_id, provider, external_username, external_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, provider)
        DO UPDATE SET external_username = EXCLUDED.external_username, external_id = EXCLUDED.external_id
        """,
        (usuario["id"], provider, datos.external_username, datos.external_id),
    )
    return _preferencias(db, usuario["id"])["linked_accounts"]


@router.delete("/social/{provider}", status_code=204, summary="Desvincular una cuenta externa")
def desvincular_cuenta(provider: Proveedor, usuario: Usuario, db: Db) -> Response:
    borrada = db.execute("DELETE FROM linked_accounts WHERE user_id = %s AND provider = %s RETURNING id",
                         (usuario["id"], provider)).fetchone()
    if not borrada:
        raise ApiError(404, "NOT_LINKED", "Esa cuenta no está vinculada.")
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Lista negra personal
# ---------------------------------------------------------------------------
@router.get("/me/blocks", summary="Mi lista negra")
def lista_negra(usuario: Usuario, db: Db) -> list[dict]:
    return db.execute(
        """
        SELECT b.blocked_id AS user_id, u.username, u.avatar_url, b.reason, b.created_at
        FROM user_blocks b JOIN users u ON u.id = b.blocked_id
        WHERE b.blocker_id = %s
        ORDER BY b.created_at DESC
        """,
        (usuario["id"],),
    ).fetchall()


@router.post("/me/blocks", status_code=201, summary="Agregar a alguien a mi lista negra")
def bloquear(datos: Bloqueo, usuario: Usuario, db: Db) -> dict:
    if datos.user_id == usuario["id"]:
        raise ApiError(422, "CANNOT_BLOCK_SELF", "No puedes agregarte a tu propia lista negra.")
    if not db.execute("SELECT 1 FROM users WHERE id = %s", (datos.user_id,)).fetchone():
        raise ApiError(404, "USER_NOT_FOUND", "Ese jugador no existe.")
    fila = db.execute(
        """
        INSERT INTO user_blocks (blocker_id, blocked_id, reason) VALUES (%s, %s, %s)
        ON CONFLICT (blocker_id, blocked_id) DO UPDATE SET reason = EXCLUDED.reason
        RETURNING blocked_id AS user_id, reason, created_at
        """,
        (usuario["id"], datos.user_id, datos.reason),
    ).fetchone()
    return fila


@router.delete("/me/blocks/{user_id}", status_code=204, summary="Quitar a alguien de mi lista negra")
def desbloquear(user_id: int, usuario: Usuario, db: Db) -> Response:
    borrado = db.execute("DELETE FROM user_blocks WHERE blocker_id = %s AND blocked_id = %s RETURNING blocked_id",
                         (usuario["id"], user_id)).fetchone()
    if not borrado:
        raise ApiError(404, "NOT_BLOCKED", "Ese jugador no está en tu lista negra.")
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Perfil público (va al final para que /me no se confunda con un id)
# ---------------------------------------------------------------------------
@router.get("/{user_id}", summary="Perfil público de un jugador")
def perfil_publico(user_id: int, usuario: Usuario, db: Db) -> dict:
    perfil = db.execute(
        f"SELECT {CAMPOS_PUBLICOS}, account_status FROM users WHERE id = %s", (user_id,)
    ).fetchone()
    if not perfil or perfil["account_status"] == "BANNED":
        raise ApiError(404, "USER_NOT_FOUND", "Ese jugador no existe.")
    del perfil["account_status"]

    resenas = db.execute(
        """
        SELECT COUNT(*) AS total, ROUND(AVG(rating), 2)::float8 AS average
        FROM user_reviews WHERE target_user_id = %s
        """,
        (user_id,),
    ).fetchone()
    etiquetas = db.execute(
        """
        SELECT tag, COUNT(*) AS total FROM user_reviews
        WHERE target_user_id = %s AND tag IS NOT NULL
        GROUP BY tag ORDER BY total DESC
        """,
        (user_id,),
    ).fetchall()
    bloqueado = db.execute("SELECT 1 FROM user_blocks WHERE blocker_id = %s AND blocked_id = %s",
                           (usuario["id"], user_id)).fetchone()
    return perfil | _preferencias(db, user_id) | {
        "reviews": {"total": resenas["total"], "average": resenas["average"]},
        "top_tags": etiquetas,
        "is_blocked_by_me": bloqueado is not None,
    }
