"""Reportes de jugadores tóxicos (lado del jugador). La revisión la hace un ADMIN en /admin/reports."""

from fastapi import APIRouter

from ..errors import ApiError
from ..schemas import ReporteCrear
from ..security import Db, Usuario

router = APIRouter(prefix="/reports", tags=["Reportes"])


@router.post("", status_code=201, summary="Reportar a un compañero de partida")
def reportar(datos: ReporteCrear, usuario: Usuario, db: Db) -> dict:
    if datos.reported_user_id == usuario["id"]:
        raise ApiError(422, "CANNOT_REPORT_SELF", "No puedes reportarte a ti mismo.")
    if not db.execute("SELECT 1 FROM lfg_posts WHERE id = %s", (datos.post_id,)).fetchone():
        raise ApiError(404, "POST_NOT_FOUND", "Esa partida no existe.")
    # Solo se reporta a alguien con quien compartiste la sala (así el admin puede revisar ese chat)
    juntos = db.execute(
        """
        SELECT COUNT(DISTINCT user_id) AS n FROM v_post_members
        WHERE post_id = %s AND user_id IN (%s, %s)
        """,
        (datos.post_id, usuario["id"], datos.reported_user_id),
    ).fetchone()["n"]
    if juntos < 2:
        raise ApiError(422, "NOT_TEAMMATES", "Solo puedes reportar a alguien que estuvo contigo en esa sala.")
    if db.execute("SELECT 1 FROM user_reports WHERE reporter_id = %s AND reported_user_id = %s AND post_id = %s",
                  (usuario["id"], datos.reported_user_id, datos.post_id)).fetchone():
        raise ApiError(409, "ALREADY_REPORTED", "Ya reportaste a esa persona por esta partida.")

    return db.execute(
        """
        INSERT INTO user_reports (reporter_id, reported_user_id, post_id, reason, comment)
        VALUES (%(yo)s, %(reported_user_id)s, %(post_id)s, %(reason)s, %(comment)s)
        RETURNING id, reported_user_id, post_id, reason, comment, status, created_at
        """,
        datos.model_dump() | {"yo": usuario["id"]},
    ).fetchone()


@router.get("/mine", summary="Mis reportes y en qué quedaron")
def mis_reportes(usuario: Usuario, db: Db) -> list[dict]:
    # El jugador ve si su reporte se atendió, pero no las notas internas del administrador
    return db.execute(
        """
        SELECT r.id, r.reported_user_id, u.username AS reported_username, r.post_id, p.title AS post_title,
               r.reason, r.comment, r.status, r.created_at, r.resolved_at
        FROM user_reports r
        JOIN users u ON u.id = r.reported_user_id
        LEFT JOIN lfg_posts p ON p.id = r.post_id
        WHERE r.reporter_id = %s
        ORDER BY r.created_at DESC, r.id DESC
        """,
        (usuario["id"],),
    ).fetchall()
