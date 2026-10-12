"""Reputación (rutas de la propuesta: /reputation): reseñas entre compañeros y nivel de honor."""

from fastapi import APIRouter, Response
from psycopg import Connection

from ..errors import ApiError
from ..schemas import ResenaActualizar, ResenaCrear
from ..security import Db, Usuario

router = APIRouter(prefix="/reputation", tags=["Reputación"])

XP_POR_NIVEL = 100
NIVEL_MAXIMO = 10


def _jugo_en(db: Connection, post_id: int, usuario_id: int) -> bool:
    return db.execute("SELECT 1 FROM v_post_members WHERE post_id = %s AND user_id = %s",
                      (post_id, usuario_id)).fetchone() is not None


def _resena_propia(db: Connection, review_id: int, usuario: dict) -> dict:
    resena = db.execute("SELECT * FROM user_reviews WHERE id = %s", (review_id,)).fetchone()
    if not resena:
        raise ApiError(404, "REVIEW_NOT_FOUND", "Esa reseña no existe.")
    if resena["reviewer_id"] != usuario["id"]:
        raise ApiError(403, "NOT_REVIEW_AUTHOR", "Solo puedes cambiar tus propias reseñas.")
    return resena


def _con_nivel(db: Connection, resena: dict) -> dict:
    """Devuelve la reseña junto con el nivel ya recalculado (lo hace el trigger trg_reviews_level)."""
    destino = db.execute("SELECT username, xp, level FROM users WHERE id = %s",
                         (resena["target_user_id"],)).fetchone()
    return resena | {"target": destino}


@router.post("/reviews", status_code=201, summary="Calificar a un compañero después de una partida")
def crear_resena(datos: ResenaCrear, usuario: Usuario, db: Db) -> dict:
    if datos.target_user_id == usuario["id"]:
        raise ApiError(422, "CANNOT_REVIEW_SELF", "No puedes calificarte a ti mismo.")
    sala = db.execute("SELECT status FROM lfg_posts WHERE id = %s", (datos.post_id,)).fetchone()
    if not sala:
        raise ApiError(404, "POST_NOT_FOUND", "Esa partida no existe.")
    if sala["status"] != "CLOSED":
        raise ApiError(409, "MATCH_NOT_FINISHED", "Solo se puede calificar cuando la partida terminó.")
    if not _jugo_en(db, datos.post_id, usuario["id"]):
        raise ApiError(403, "NOT_IN_MATCH", "No jugaste en esa partida.")
    if not _jugo_en(db, datos.post_id, datos.target_user_id):
        raise ApiError(422, "TARGET_NOT_IN_MATCH", "Esa persona no jugó contigo en esa partida.")
    if db.execute("SELECT 1 FROM user_reviews WHERE post_id = %s AND reviewer_id = %s AND target_user_id = %s",
                  (datos.post_id, usuario["id"], datos.target_user_id)).fetchone():
        raise ApiError(409, "ALREADY_REVIEWED", "Ya calificaste a esa persona en esta partida. Puedes editar tu reseña.")

    resena = db.execute(
        """
        INSERT INTO user_reviews (post_id, reviewer_id, target_user_id, rating, tag, comment)
        VALUES (%(post_id)s, %(yo)s, %(target_user_id)s, %(rating)s, %(tag)s, %(comment)s)
        RETURNING *
        """,
        datos.model_dump() | {"yo": usuario["id"]},
    ).fetchone()
    return _con_nivel(db, resena)


@router.put("/reviews/{review_id}", summary="Editar mi reseña (solo los campos enviados)")
def editar_resena(review_id: int, datos: ResenaActualizar, usuario: Usuario, db: Db) -> dict:
    _resena_propia(db, review_id, usuario)
    cambios = datos.model_dump(exclude_unset=True)
    if cambios.get("rating", 0) is None:
        raise ApiError(422, "VALIDATION_ERROR", "La calificación no puede quedar vacía.")
    if cambios:
        columnas = ", ".join(f"{campo} = %({campo})s" for campo in cambios)
        db.execute(f"UPDATE user_reviews SET {columnas} WHERE id = %(id)s", cambios | {"id": review_id})
    resena = db.execute("SELECT * FROM user_reviews WHERE id = %s", (review_id,)).fetchone()
    return _con_nivel(db, resena)


@router.delete("/reviews/{review_id}", status_code=204, summary="Borrar mi reseña")
def borrar_resena(review_id: int, usuario: Usuario, db: Db) -> Response:
    _resena_propia(db, review_id, usuario)
    db.execute("DELETE FROM user_reviews WHERE id = %s", (review_id,))
    return Response(status_code=204)


@router.get("/users/{user_id}", summary="Honor Score de un jugador: nivel, XP, reseñas y etiquetas")
def honor(user_id: int, usuario: Usuario, db: Db) -> dict:
    jugador = db.execute("SELECT id, username, xp, level, account_status FROM users WHERE id = %s",
                         (user_id,)).fetchone()
    if not jugador or jugador.pop("account_status") == "BANNED":
        raise ApiError(404, "USER_NOT_FOUND", "Ese jugador no existe.")

    # Barra de progreso hacia el siguiente nivel (nivel 0 = Rookie, XP negativa)
    if jugador["level"] >= NIVEL_MAXIMO:
        progreso = {"xp_in_level": XP_POR_NIVEL, "xp_for_next": 0, "percent": 100}
    elif jugador["xp"] < 0:
        progreso = {"xp_in_level": 0, "xp_for_next": -jugador["xp"], "percent": 0}
    else:
        dentro = jugador["xp"] % XP_POR_NIVEL
        progreso = {"xp_in_level": dentro, "xp_for_next": XP_POR_NIVEL - dentro, "percent": dentro}

    resumen = db.execute(
        """
        SELECT COUNT(*) AS total, ROUND(AVG(rating), 2)::float8 AS average,
               COUNT(*) FILTER (WHERE rating = 5) AS "5", COUNT(*) FILTER (WHERE rating = 4) AS "4",
               COUNT(*) FILTER (WHERE rating = 3) AS "3", COUNT(*) FILTER (WHERE rating = 2) AS "2",
               COUNT(*) FILTER (WHERE rating = 1) AS "1"
        FROM user_reviews WHERE target_user_id = %s
        """,
        (user_id,),
    ).fetchone()
    etiquetas = db.execute(
        """
        SELECT tag, COUNT(*) AS total FROM user_reviews
        WHERE target_user_id = %s AND tag IS NOT NULL
        GROUP BY tag ORDER BY total DESC, tag
        """,
        (user_id,),
    ).fetchall()
    recientes = db.execute(
        """
        SELECT r.id, r.rating, r.tag, r.comment, r.created_at,
               u.username AS reviewer_username, u.avatar_url AS reviewer_avatar_url, g.name AS game_name
        FROM user_reviews r
        JOIN users u ON u.id = r.reviewer_id
        JOIN lfg_posts p ON p.id = r.post_id
        JOIN games g ON g.id = p.game_id
        WHERE r.target_user_id = %s AND u.account_status <> 'BANNED'
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT 10
        """,
        (user_id,),
    ).fetchall()
    return jugador | {
        "is_rookie": jugador["level"] == 0,
        "progress": progreso,
        "reviews": {"total": resumen.pop("total"), "average": resumen.pop("average"),
                    "distribution": {k: v for k, v in resumen.items()}},
        "top_tags": etiquetas,
        "recent_reviews": recientes,
    }
