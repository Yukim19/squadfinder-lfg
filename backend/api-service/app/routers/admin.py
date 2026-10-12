"""Panel de administración (admin_reportes.html). Todas las rutas exigen role = 'ADMIN'."""

from typing import Literal

from fastapi import APIRouter
from psycopg import Connection

from ..errors import ApiError
from ..schemas import DecisionJuego, ReglasModeracion, ResolverReporte
from ..security import Admin, Db

router = APIRouter(prefix="/admin", tags=["Administración"])

# Reporte con la evidencia: mensajes del reportado en esa partida que el filtro marcó como tóxicos
CONSULTA_REPORTES = """
    SELECT r.*,
           COALESCE((SELECT JSON_AGG(JSON_BUILD_OBJECT('message', m.message, 'toxicity_level', m.toxicity_level,
                                                       'sent_at', m.sent_at) ORDER BY m.sent_at)
                       FROM chat_messages m
                      WHERE m.post_id = r.post_id AND m.sender_id = r.reported_user_id
                        AND m.toxicity_level <> 'NONE'), '[]') AS evidence
    FROM v_reports_admin r
"""


def _reporte(db: Connection, report_id: int) -> dict:
    reporte = db.execute(CONSULTA_REPORTES + " WHERE r.id = %s", (report_id,)).fetchone()
    if not reporte:
        raise ApiError(404, "REPORT_NOT_FOUND", "Ese reporte no existe.")
    return reporte


# ---------------------------------------------------------------------------
# Reportes y sanciones
# ---------------------------------------------------------------------------
@router.get("/reports", summary="Reportes (pendientes primero) con la evidencia del chat")
def listar_reportes(
    admin: Admin,
    db: Db,
    status: Literal["PENDING", "DISMISSED", "WARNED", "SUSPENDED", "BANNED"] | None = None,
) -> list[dict]:
    return db.execute(
        CONSULTA_REPORTES + """
        WHERE (%(status)s::text IS NULL OR r.status = %(status)s)
        ORDER BY r.status = 'PENDING' DESC, r.created_at DESC, r.id DESC
        """,
        {"status": status},
    ).fetchall()


@router.get("/reports/{report_id}", summary="Detalle de un reporte")
def ver_reporte(report_id: int, admin: Admin, db: Db) -> dict:
    return _reporte(db, report_id)


@router.put("/reports/{report_id}", summary="Resolver un reporte: descartar, advertir, suspender o eliminar la cuenta")
def resolver_reporte(report_id: int, datos: ResolverReporte, admin: Admin, db: Db) -> dict:
    if _reporte(db, report_id)["status"] != "PENDING":
        raise ApiError(409, "REPORT_ALREADY_RESOLVED", "Ese reporte ya fue resuelto.")
    # resolve_report() aplica la sanción, los niveles y la regla automática de advertencias
    db.execute(
        "SELECT resolve_report(%s, %s, %s::varchar, %s::smallint, %s::smallint, %s::varchar)",
        (report_id, admin["id"], datos.action, datos.suspension_days, datos.levels_removed, datos.notes),
    )
    reporte = _reporte(db, report_id)
    reporte["reported_user"] = db.execute(
        "SELECT id, username, xp, level, warnings_count, account_status, suspended_until FROM users WHERE id = %s",
        (reporte["reported_user_id"],),
    ).fetchone()
    return reporte


@router.post("/users/{user_id}/reactivate", summary="Levantar la suspensión o eliminación de una cuenta")
def reactivar(user_id: int, admin: Admin, db: Db) -> dict:
    usuario = db.execute(
        """
        UPDATE users SET account_status = 'ACTIVE', suspended_until = NULL WHERE id = %s
        RETURNING id, username, xp, level, warnings_count, account_status, suspended_until
        """,
        (user_id,),
    ).fetchone()
    if not usuario:
        raise ApiError(404, "USER_NOT_FOUND", "Ese jugador no existe.")
    return usuario


# ---------------------------------------------------------------------------
# Reglas de moderación
# ---------------------------------------------------------------------------
@router.get("/settings", summary="Reglas de moderación")
def ver_reglas(admin: Admin, db: Db) -> dict:
    return db.execute("SELECT * FROM moderation_settings WHERE id = 1").fetchone()


@router.put("/settings", summary="Cambiar las reglas de moderación (solo los campos enviados)")
def cambiar_reglas(datos: ReglasModeracion, admin: Admin, db: Db) -> dict:
    cambios = {k: v for k, v in datos.model_dump(exclude_unset=True).items() if v is not None}
    columnas = "".join(f"{campo} = %({campo})s, " for campo in cambios)
    return db.execute(
        f"UPDATE moderation_settings SET {columnas}updated_by = %(admin)s WHERE id = 1 RETURNING *",
        cambios | {"admin": admin["id"]},
    ).fetchone()


# ---------------------------------------------------------------------------
# Juegos sugeridos por los usuarios
# ---------------------------------------------------------------------------
@router.get("/game-requests", summary="Juegos sugeridos (pendientes primero)")
def listar_sugerencias(
    admin: Admin,
    db: Db,
    status: Literal["PENDING", "APPROVED", "REJECTED"] | None = None,
) -> list[dict]:
    return db.execute(
        """
        SELECT gr.*, u.username,
               (SELECT COUNT(*) FROM game_requests x
                 WHERE LOWER(x.game_name) = LOWER(gr.game_name) AND x.status = 'PENDING') AS times_requested
        FROM game_requests gr JOIN users u ON u.id = gr.user_id
        WHERE (%(status)s::text IS NULL OR gr.status = %(status)s)
        ORDER BY gr.status = 'PENDING' DESC, gr.created_at DESC, gr.id DESC
        """,
        {"status": status},
    ).fetchall()


@router.put("/game-requests/{request_id}", summary="Aprobar (agrega el juego al catálogo) o rechazar una sugerencia")
def decidir_sugerencia(request_id: int, datos: DecisionJuego, admin: Admin, db: Db) -> dict:
    with db.transaction():
        sugerencia = db.execute("SELECT * FROM game_requests WHERE id = %s FOR UPDATE", (request_id,)).fetchone()
        if not sugerencia:
            raise ApiError(404, "REQUEST_NOT_FOUND", "Esa sugerencia no existe.")
        if sugerencia["status"] != "PENDING":
            raise ApiError(409, "REQUEST_ALREADY_REVIEWED", "Esa sugerencia ya fue revisada.")

        if datos.status == "REJECTED":
            return db.execute(
                "UPDATE game_requests SET status = 'REJECTED', reviewed_by = %s WHERE id = %s RETURNING *",
                (admin["id"], request_id),
            ).fetchone()

        nombre = datos.name or sugerencia["game_name"]
        if db.execute("SELECT 1 FROM games WHERE LOWER(name) = LOWER(%s)", (nombre,)).fetchone():
            raise ApiError(409, "GAME_EXISTS", "Ese juego ya está en el catálogo.")
        if datos.crossplay and len(set(datos.platforms)) < 2:
            raise ApiError(422, "CROSSPLAY_NEEDS_PLATFORMS", "El crossplay necesita al menos dos plataformas.")
        juego_id = db.execute(
            "INSERT INTO games (name, genre_id, crossplay) VALUES (%s, %s, %s) RETURNING id",
            (nombre, datos.genre_id, datos.crossplay),
        ).fetchone()["id"]
        with db.cursor() as cur:
            cur.executemany("INSERT INTO game_platforms (game_id, platform) VALUES (%s, %s)",
                            [(juego_id, p) for p in sorted(set(datos.platforms))])
        # Las demás personas que sugirieron el mismo juego también quedan atendidas
        db.execute(
            """
            UPDATE game_requests SET status = 'APPROVED', game_id = %s, reviewed_by = %s
            WHERE status = 'PENDING' AND (id = %s OR LOWER(game_name) = LOWER(%s))
            """,
            (juego_id, admin["id"], request_id, sugerencia["game_name"]),
        )
        return db.execute("SELECT * FROM game_requests WHERE id = %s", (request_id,)).fetchone()
