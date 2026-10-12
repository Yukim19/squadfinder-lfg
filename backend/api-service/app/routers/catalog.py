"""Catálogo: géneros, juegos (con plataformas y crossplay) y sugerencias de juegos."""

from fastapi import APIRouter, Query

from ..errors import ApiError
from ..schemas import SugerenciaJuego
from ..security import Db, Usuario

router = APIRouter(prefix="/catalog", tags=["Catálogo"])


@router.get("/genres", summary="Lista de géneros")
def listar_generos(db: Db) -> list[dict]:
    return db.execute("SELECT id, name FROM genres ORDER BY name").fetchall()


@router.get("/games", summary="Lista de juegos con sus plataformas")
def listar_juegos(
    db: Db,
    platform: str | None = Query(None, description="Solo juegos disponibles en esta plataforma"),
    genre_id: int | None = Query(None),
) -> list[dict]:
    return db.execute(
        """
        SELECT g.id, g.name, g.crossplay, ge.id AS genre_id, ge.name AS genre,
               ARRAY_AGG(gp.platform ORDER BY gp.platform) AS platforms
        FROM games g
        JOIN genres ge ON ge.id = g.genre_id
        JOIN game_platforms gp ON gp.game_id = g.id
        WHERE (%(genre)s::int IS NULL OR g.genre_id = %(genre)s)
        GROUP BY g.id, ge.id
        HAVING %(platform)s::text IS NULL OR %(platform)s = ANY(ARRAY_AGG(gp.platform))
        ORDER BY g.id
        """,
        {"genre": genre_id, "platform": platform},
    ).fetchall()


@router.post("/game-requests", status_code=201, summary="Sugerir un juego que no está en la lista")
def sugerir_juego(datos: SugerenciaJuego, usuario: Usuario, db: Db) -> dict:
    existe = db.execute("SELECT 1 FROM games WHERE LOWER(name) = LOWER(%s)", (datos.game_name,)).fetchone()
    if existe:
        raise ApiError(409, "GAME_EXISTS", "Ese juego ya está en la lista.")
    repetida = db.execute(
        "SELECT 1 FROM game_requests WHERE user_id = %s AND LOWER(game_name) = LOWER(%s) AND status = 'PENDING'",
        (usuario["id"], datos.game_name),
    ).fetchone()
    if repetida:
        raise ApiError(409, "REQUEST_PENDING", "Ya sugeriste ese juego; está pendiente de revisión.")
    return db.execute(
        """
        INSERT INTO game_requests (user_id, game_name, platforms_note)
        VALUES (%s, %s, %s)
        RETURNING id, game_name, platforms_note, status, created_at
        """,
        (usuario["id"], datos.game_name, datos.platforms_note),
    ).fetchone()
