"""Salas LFG (rutas de la propuesta: /lfg/posts) y solicitudes para unirse."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response
from psycopg import Connection

from ..errors import ApiError
from ..schemas import (IdiomaSala, ModoJuego, Plataforma, Region, SalaActualizar, SalaCrear, SolicitudCrear,
                       SolicitudDecision)
from ..security import Db, Usuario

router = APIRouter(prefix="/lfg", tags=["Salas"])

ACTIVAS = ("OPEN", "FULL", "IN_PROGRESS")


# ---------------------------------------------------------------------------
# Funciones de apoyo
# ---------------------------------------------------------------------------
def _bloquear_sala(db: Connection, post_id: int) -> dict:
    """Lee la sala y la bloquea hasta el final de la transacción.

    Así dos anfitriones (o dos pestañas) no pueden aceptar a la vez al último jugador.
    """
    sala = db.execute("SELECT * FROM lfg_posts WHERE id = %s FOR UPDATE", (post_id,)).fetchone()
    if not sala:
        raise ApiError(404, "POST_NOT_FOUND", "Esa sala no existe.")
    return sala


def _solo_anfitrion(sala: dict, usuario: dict) -> None:
    if sala["host_id"] != usuario["id"]:
        raise ApiError(403, "NOT_HOST", "Solo el anfitrión de la sala puede hacer esto.")


def _no_terminada(sala: dict) -> None:
    if sala["status"] not in ACTIVAS:
        raise ApiError(409, "POST_FINISHED", "La sala ya terminó o fue cancelada.")


def _jugadores(db: Connection, post_id: int) -> int:
    """Anfitrión + solicitudes aceptadas (igual que current_players en v_lfg_posts)."""
    return 1 + db.execute("SELECT COUNT(*) AS n FROM applications WHERE post_id = %s AND status = 'ACCEPTED'",
                          (post_id,)).fetchone()["n"]


def _validar_plataformas(db: Connection, game_id: int, plataformas: list[str]) -> list[str]:
    """Mensajes claros antes de que el trigger trg_post_platforms_check rechace la sala."""
    plataformas = sorted(set(plataformas))
    juego = db.execute(
        """
        SELECT g.crossplay, ARRAY_AGG(gp.platform) AS disponibles
        FROM games g JOIN game_platforms gp ON gp.game_id = g.id
        WHERE g.id = %s GROUP BY g.id
        """,
        (game_id,),
    ).fetchone()
    if not juego:
        raise ApiError(422, "GAME_NOT_FOUND", "Ese juego no existe.")
    no_disponibles = [p for p in plataformas if p not in juego["disponibles"]]
    if no_disponibles:
        raise ApiError(422, "PLATFORM_NOT_AVAILABLE", "El juego no está disponible en esas plataformas.",
                       no_disponibles)
    if len(plataformas) > 1 and not juego["crossplay"]:
        raise ApiError(422, "NO_CROSSPLAY", "Este juego no tiene crossplay: elige una sola plataforma.")
    return plataformas


def _guardar_plataformas(db: Connection, post_id: int, plataformas: list[str]) -> None:
    db.execute("DELETE FROM post_platforms WHERE post_id = %s", (post_id,))
    with db.cursor() as cur:
        cur.executemany("INSERT INTO post_platforms (post_id, platform) VALUES (%s, %s)",
                        [(post_id, p) for p in plataformas])


def _detalle(db: Connection, post_id: int, usuario: dict) -> dict:
    sala = db.execute(
        """
        SELECT v.*, h.account_status AS host_account_status
        FROM v_lfg_posts v JOIN users h ON h.id = v.host_id
        WHERE v.id = %s
        """,
        (post_id,),
    ).fetchone()
    # La sala de una cuenta eliminada desaparece para todos menos para los administradores
    if not sala or (sala.pop("host_account_status") == "BANNED" and usuario["role"] != "ADMIN"):
        raise ApiError(404, "POST_NOT_FOUND", "Esa sala no existe.")

    sala["members"] = db.execute(
        """
        SELECT user_id, username, region, level, avatar_url, role, joined_at
        FROM v_post_members WHERE post_id = %s
        ORDER BY role = 'HOST' DESC, joined_at
        """,
        (post_id,),
    ).fetchall()
    mia = db.execute("SELECT id, status FROM applications WHERE post_id = %s AND applicant_id = %s",
                     (post_id, usuario["id"])).fetchone()
    sala["is_host"] = sala["host_id"] == usuario["id"]
    sala["my_application"] = mia
    if sala["is_host"]:
        sala["pending_applications"] = db.execute(
            "SELECT COUNT(*) AS n FROM applications WHERE post_id = %s AND status = 'PENDING'", (post_id,)
        ).fetchone()["n"]
    return sala


def _solicitud(db: Connection, application_id: int) -> dict:
    return db.execute(
        """
        SELECT a.id, a.post_id, a.status, a.message, a.created_at, a.updated_at,
               u.id AS applicant_id, u.username, u.level, u.region, u.avatar_url,
               u.preferred_language_speak
        FROM applications a JOIN users u ON u.id = a.applicant_id
        WHERE a.id = %s
        """,
        (application_id,),
    ).fetchone()


# ---------------------------------------------------------------------------
# Salas
# ---------------------------------------------------------------------------
@router.post("/posts", status_code=201, summary="Crear una sala")
def crear_sala(datos: SalaCrear, usuario: Usuario, db: Db) -> dict:
    if not db.execute("SELECT 1 FROM user_games WHERE user_id = %s AND game_id = %s",
                      (usuario["id"], datos.game_id)).fetchone():
        raise ApiError(422, "GAME_NOT_IN_PROFILE",
                       "Solo puedes crear salas de los juegos de tu perfil. Agrégalo en tu perfil primero.")
    plataformas = _validar_plataformas(db, datos.game_id, datos.platforms)

    with db.transaction():
        post_id = db.execute(
            """
            INSERT INTO lfg_posts (host_id, game_id, title, description, max_players, play_mode,
                                   rank_required, mic_required, required_language)
            VALUES (%(host_id)s, %(game_id)s, %(title)s, %(description)s, %(max_players)s, %(play_mode)s,
                    %(rank_required)s, %(mic_required)s, %(required_language)s)
            RETURNING id
            """,
            datos.model_dump(exclude={"platforms"}) | {"host_id": usuario["id"]},
        ).fetchone()["id"]
        _guardar_plataformas(db, post_id, plataformas)
    return _detalle(db, post_id, usuario)


@router.get("/posts", summary="Salas abiertas (feed de la página principal) con filtros")
def listar_salas(
    usuario: Usuario,
    db: Db,
    game_id: int | None = None,
    platform: Plataforma | None = None,
    play_mode: ModoJuego | None = None,
    language: Annotated[IdiomaSala | None, Query(description="Incluye las salas de cualquier idioma")] = None,
    region: Annotated[Region | None, Query(description="Región del anfitrión")] = None,
    mic_required: bool | None = None,
    only_my_games: Annotated[bool, Query(description="Solo los juegos de mi perfil")] = False,
    only_open: Annotated[bool, Query(description="Ocultar las salas llenas")] = False,
    q: Annotated[str | None, Query(max_length=50, description="Buscar en el título")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    # Cada filtro agrega una condición fija; los valores siempre van como parámetros
    condiciones = []
    if game_id is not None:
        condiciones.append("f.game_id = %(game_id)s")
    if platform:
        condiciones.append("%(platform)s = ANY(f.platforms)")
    if play_mode:
        condiciones.append("f.play_mode = %(play_mode)s")
    if language and language != "any":
        condiciones.append("f.required_language IN (%(language)s, 'any')")
    if region:
        condiciones.append("f.host_region = %(region)s")
    if mic_required is not None:
        condiciones.append("f.mic_required = %(mic_required)s")
    if only_my_games:
        condiciones.append("f.game_id IN (SELECT game_id FROM user_games WHERE user_id = %(yo)s)")
    if only_open:
        condiciones.append("f.status = 'OPEN'")
    if q:
        condiciones.append("f.title ILIKE %(q)s")
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    return db.execute(
        f"""
        SELECT f.*,
               f.host_id = %(yo)s AS is_host,
               (SELECT a.status FROM applications a
                 WHERE a.post_id = f.id AND a.applicant_id = %(yo)s) AS my_application_status
        FROM feed_for_user(%(yo)s) f
        {where}
        ORDER BY f.created_at DESC, f.id DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"yo": usuario["id"], "game_id": game_id, "platform": platform, "play_mode": play_mode,
         "language": language, "region": region, "mic_required": mic_required,
         "q": f"%{q}%" if q else None, "limit": limit, "offset": offset},
    ).fetchall()


@router.get("/history", summary="Mi historial: partidas terminadas con mis compañeros")
def historial(usuario: Usuario, db: Db) -> list[dict]:
    # v_match_history tiene una fila por compañero; aquí se agrupan por partida
    return db.execute(
        """
        SELECT post_id, title, game_name, platforms, closed_at,
               JSON_AGG(JSON_BUILD_OBJECT(
                   'user_id', teammate_id, 'username', teammate_username,
                   'region', teammate_region, 'level', teammate_level,
                   'is_blocked', is_blocked, 'already_reviewed', already_reviewed,
                   'already_reported', already_reported
               ) ORDER BY teammate_username) AS teammates
        FROM v_match_history
        WHERE user_id = %s
        GROUP BY post_id, title, game_name, platforms, closed_at
        ORDER BY closed_at DESC NULLS LAST, post_id DESC
        """,
        (usuario["id"],),
    ).fetchall()


@router.get("/mine", summary="Mis salas activas (como anfitrión o integrante)")
def mis_salas(usuario: Usuario, db: Db) -> list[dict]:
    return db.execute(
        """
        SELECT v.*, v.host_id = %(yo)s AS is_host
        FROM v_lfg_posts v
        WHERE v.status IN ('OPEN', 'FULL', 'IN_PROGRESS')
          AND (v.host_id = %(yo)s OR EXISTS (
               SELECT 1 FROM applications a
               WHERE a.post_id = v.id AND a.applicant_id = %(yo)s AND a.status = 'ACCEPTED'))
        ORDER BY v.created_at DESC, v.id DESC
        """,
        {"yo": usuario["id"]},
    ).fetchall()


@router.get("/posts/{post_id}", summary="Detalle de una sala con sus integrantes")
def ver_sala(post_id: int, usuario: Usuario, db: Db) -> dict:
    return _detalle(db, post_id, usuario)


@router.put("/posts/{post_id}", summary="Editar mi sala, empezar la partida o terminarla")
def editar_sala(post_id: int, datos: SalaActualizar, usuario: Usuario, db: Db) -> dict:
    with db.transaction():
        sala = _bloquear_sala(db, post_id)
        _solo_anfitrion(sala, usuario)
        _no_terminada(sala)

        cambios = datos.model_dump(exclude_unset=True, exclude={"platforms", "status"})
        modo = cambios.get("play_mode", sala["play_mode"])
        if modo == "CASUAL":
            if cambios.get("rank_required"):
                raise ApiError(422, "RANK_ONLY_COMPETITIVE", "Solo las salas competitivas pueden pedir un rango mínimo.")
            cambios["rank_required"] = None

        jugadores = _jugadores(db, post_id)
        maximo = cambios.get("max_players", sala["max_players"])
        if maximo < jugadores:
            raise ApiError(422, "MAX_BELOW_CURRENT",
                           f"Ya hay {jugadores} jugadores en la sala: el máximo no puede ser menor.")

        nuevo_estado = datos.status
        if nuevo_estado == "IN_PROGRESS" and sala["status"] == "IN_PROGRESS":
            raise ApiError(409, "INVALID_TRANSITION", "La partida ya empezó.")
        if nuevo_estado:
            cambios["status"] = nuevo_estado
        elif sala["status"] in ("OPEN", "FULL"):
            # Si cambia el máximo, la sala se abre o se llena según los lugares libres
            cambios["status"] = "FULL" if jugadores >= maximo else "OPEN"

        if cambios:
            # Los nombres de columna vienen del modelo (lista cerrada), nunca del usuario
            columnas = ", ".join(f"{campo} = %({campo})s" for campo in cambios)
            if nuevo_estado == "CLOSED":
                columnas += ", closed_at = NOW()"
            db.execute(f"UPDATE lfg_posts SET {columnas} WHERE id = %(id)s", cambios | {"id": post_id})
        if nuevo_estado == "CLOSED":
            # Las solicitudes que nadie respondió ya no tienen sentido
            db.execute("UPDATE applications SET status = 'REJECTED' WHERE post_id = %s AND status = 'PENDING'",
                       (post_id,))
        if datos.platforms is not None:
            _guardar_plataformas(db, post_id, _validar_plataformas(db, sala["game_id"], datos.platforms))
    return _detalle(db, post_id, usuario)


@router.delete("/posts/{post_id}", status_code=204, summary="Cancelar una sala (anfitrión o administrador)")
def cancelar_sala(post_id: int, usuario: Usuario, db: Db) -> Response:
    with db.transaction():
        sala = _bloquear_sala(db, post_id)
        if usuario["role"] != "ADMIN":
            _solo_anfitrion(sala, usuario)
        # Las partidas terminadas no se borran: son el historial y la base de las reseñas
        _no_terminada(sala)
        db.execute("UPDATE lfg_posts SET status = 'CANCELLED' WHERE id = %s", (post_id,))
        db.execute("UPDATE applications SET status = 'REJECTED' WHERE post_id = %s AND status = 'PENDING'",
                   (post_id,))
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Solicitudes para unirse
# ---------------------------------------------------------------------------
@router.post("/posts/{post_id}/applications", status_code=201, summary="Pedir unirme a una sala")
def solicitar_unirse(post_id: int, datos: SolicitudCrear, usuario: Usuario, db: Db) -> dict:
    with db.transaction():
        sala = _bloquear_sala(db, post_id)
        if sala["host_id"] == usuario["id"]:
            raise ApiError(409, "IS_HOST", "Ya eres el anfitrión de esta sala.")
        anfitrion = db.execute("SELECT account_status FROM users WHERE id = %s", (sala["host_id"],)).fetchone()
        if anfitrion["account_status"] == "BANNED":
            raise ApiError(404, "POST_NOT_FOUND", "Esa sala no existe.")
        if sala["status"] != "OPEN":
            raise ApiError(409, "POST_NOT_OPEN", "Esta sala ya no acepta jugadores.")
        # Si el anfitrión te tiene en su lista negra no se le dice el motivo a nadie
        if db.execute("SELECT 1 FROM user_blocks WHERE blocker_id = %s AND blocked_id = %s",
                      (sala["host_id"], usuario["id"])).fetchone():
            raise ApiError(403, "CANNOT_JOIN", "No puedes unirte a esta sala.")

        previa = db.execute("SELECT id, status FROM applications WHERE post_id = %s AND applicant_id = %s",
                            (post_id, usuario["id"])).fetchone()
        if previa and previa["status"] in ("PENDING", "ACCEPTED"):
            raise ApiError(409, "ALREADY_APPLIED", "Ya enviaste una solicitud a esta sala.")
        if previa and previa["status"] == "REJECTED":
            raise ApiError(409, "APPLICATION_REJECTED", "El anfitrión ya rechazó tu solicitud.")

        if previa:  # La había retirado y vuelve a intentarlo
            solicitud_id = db.execute(
                "UPDATE applications SET status = 'PENDING', message = %s WHERE id = %s RETURNING id",
                (datos.message, previa["id"]),
            ).fetchone()["id"]
        else:
            solicitud_id = db.execute(
                "INSERT INTO applications (post_id, applicant_id, message) VALUES (%s, %s, %s) RETURNING id",
                (post_id, usuario["id"], datos.message),
            ).fetchone()["id"]
    return _solicitud(db, solicitud_id)


@router.get("/posts/{post_id}/applications", summary="Solicitudes de mi sala (anfitrión)")
def listar_solicitudes(
    post_id: int,
    usuario: Usuario,
    db: Db,
    status: Literal["PENDING", "ACCEPTED", "REJECTED", "WITHDRAWN"] | None = None,
) -> list[dict]:
    sala = db.execute("SELECT host_id FROM lfg_posts WHERE id = %s", (post_id,)).fetchone()
    if not sala:
        raise ApiError(404, "POST_NOT_FOUND", "Esa sala no existe.")
    _solo_anfitrion(sala, usuario)
    return db.execute(
        """
        SELECT a.id, a.status, a.message, a.created_at,
               u.id AS applicant_id, u.username, u.level, u.region, u.avatar_url,
               u.preferred_language_speak
        FROM applications a JOIN users u ON u.id = a.applicant_id
        WHERE a.post_id = %s AND (%s::text IS NULL OR a.status = %s)
        ORDER BY a.status = 'PENDING' DESC, a.created_at
        """,
        (post_id, status, status),
    ).fetchall()


@router.put("/posts/{post_id}/applications/{application_id}",
            summary="Aceptar o rechazar una solicitud (rechazar a un aceptado lo saca de la sala)")
def decidir_solicitud(post_id: int, application_id: int, datos: SolicitudDecision, usuario: Usuario, db: Db) -> dict:
    with db.transaction():
        sala = _bloquear_sala(db, post_id)
        _solo_anfitrion(sala, usuario)
        _no_terminada(sala)
        solicitud = db.execute("SELECT id, status FROM applications WHERE id = %s AND post_id = %s",
                               (application_id, post_id)).fetchone()
        if not solicitud:
            raise ApiError(404, "APPLICATION_NOT_FOUND", "Esa solicitud no existe en esta sala.")
        jugadores = _jugadores(db, post_id)

        if datos.status == "ACCEPTED":
            if solicitud["status"] != "PENDING":
                raise ApiError(409, "INVALID_TRANSITION", "Solo se pueden aceptar solicitudes pendientes.")
            if jugadores >= sala["max_players"]:
                raise ApiError(409, "POST_FULL", "La sala ya está llena.")
            jugadores += 1
        else:
            if solicitud["status"] not in ("PENDING", "ACCEPTED"):
                raise ApiError(409, "INVALID_TRANSITION", "Esa solicitud ya no está activa.")
            if solicitud["status"] == "ACCEPTED":
                jugadores -= 1

        db.execute("UPDATE applications SET status = %s WHERE id = %s", (datos.status, application_id))
        if sala["status"] in ("OPEN", "FULL"):
            db.execute("UPDATE lfg_posts SET status = %s WHERE id = %s",
                       ("FULL" if jugadores >= sala["max_players"] else "OPEN", post_id))
    return _solicitud(db, application_id)


@router.delete("/posts/{post_id}/applications/me", status_code=204,
               summary="Retirar mi solicitud o salirme de la sala")
def retirar_solicitud(post_id: int, usuario: Usuario, db: Db) -> Response:
    with db.transaction():
        sala = _bloquear_sala(db, post_id)
        solicitud = db.execute(
            """
            SELECT id, status FROM applications
            WHERE post_id = %s AND applicant_id = %s AND status IN ('PENDING', 'ACCEPTED')
            """,
            (post_id, usuario["id"]),
        ).fetchone()
        if not solicitud:
            raise ApiError(404, "APPLICATION_NOT_FOUND", "No tienes una solicitud activa en esta sala.")
        _no_terminada(sala)
        db.execute("UPDATE applications SET status = 'WITHDRAWN' WHERE id = %s", (solicitud["id"],))
        if sala["status"] == "FULL" and solicitud["status"] == "ACCEPTED":
            db.execute("UPDATE lfg_posts SET status = 'OPEN' WHERE id = %s", (post_id,))
    return Response(status_code=204)
