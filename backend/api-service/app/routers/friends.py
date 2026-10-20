"""Amigos: solicitudes, lista de amigos y resumen para la campanita.

Los mensajes privados solo se pueden enviar entre amigos (lo comprueba el realtime-service).
Una amistad es una solicitud que la otra persona acepta; si la rechaza, se borra.
"""

from fastapi import APIRouter, Response
from psycopg import Connection

from ..errors import ApiError
from ..schemas import AmistadCrear, AmistadDecision
from ..security import Db, Usuario

router = APIRouter(prefix="/friends", tags=["Amigos"])


def _par(db: Connection, a: int, b: int) -> dict | None:
    """La fila de amistad entre dos personas (sin importar quién envió la solicitud)."""
    return db.execute(
        """
        SELECT id, requester_id, addressee_id, status FROM friendships
        WHERE LEAST(requester_id, addressee_id) = LEAST(%(a)s, %(b)s)
          AND GREATEST(requester_id, addressee_id) = GREATEST(%(a)s, %(b)s)
        """,
        {"a": a, "b": b},
    ).fetchone()


def _bloqueados(db: Connection, a: int, b: int) -> bool:
    """True si alguno de los dos tiene al otro en su lista negra."""
    return db.execute(
        """
        SELECT 1 FROM user_blocks
        WHERE (blocker_id = %(a)s AND blocked_id = %(b)s) OR (blocker_id = %(b)s AND blocked_id = %(a)s)
        """,
        {"a": a, "b": b},
    ).fetchone() is not None


@router.get("", summary="Mis amigos, con mensajes sin leer y la hora del último mensaje")
def listar_amigos(usuario: Usuario, db: Db) -> list[dict]:
    return db.execute(
        """
        SELECT u.id AS user_id, u.username, u.avatar_url, u.level,
               (SELECT COUNT(*) FROM direct_messages m
                 WHERE m.sender_id = u.id AND m.recipient_id = %(yo)s AND m.read_at IS NULL)::int AS unread,
               (SELECT MAX(m.sent_at) FROM direct_messages m
                 WHERE LEAST(m.sender_id, m.recipient_id) = LEAST(u.id, %(yo)s)
                   AND GREATEST(m.sender_id, m.recipient_id) = GREATEST(u.id, %(yo)s)) AS last_message_at
        FROM friendships f
        JOIN users u ON u.id = CASE WHEN f.requester_id = %(yo)s THEN f.addressee_id ELSE f.requester_id END
        WHERE f.status = 'ACCEPTED' AND %(yo)s IN (f.requester_id, f.addressee_id)
          AND u.account_status <> 'BANNED'
        ORDER BY last_message_at DESC NULLS LAST, u.username
        """,
        {"yo": usuario["id"]},
    ).fetchall()


@router.get("/requests", summary="Solicitudes de amistad que recibí y que envié")
def listar_solicitudes(usuario: Usuario, db: Db) -> dict:
    filas = db.execute(
        """
        SELECT f.id, f.created_at, u.id AS user_id, u.username, u.avatar_url, u.level,
               (f.addressee_id = %(yo)s) AS incoming
        FROM friendships f
        JOIN users u ON u.id = CASE WHEN f.requester_id = %(yo)s THEN f.addressee_id ELSE f.requester_id END
        WHERE f.status = 'PENDING' AND %(yo)s IN (f.requester_id, f.addressee_id)
          AND u.account_status <> 'BANNED'
        ORDER BY f.created_at DESC
        """,
        {"yo": usuario["id"]},
    ).fetchall()
    return {
        "incoming": [{k: v for k, v in f.items() if k != "incoming"} for f in filas if f["incoming"]],
        "outgoing": [{k: v for k, v in f.items() if k != "incoming"} for f in filas if not f["incoming"]],
    }


@router.get("/summary", summary="Contadores para la campanita: mensajes sin leer y solicitudes pendientes")
def resumen(usuario: Usuario, db: Db) -> dict:
    return db.execute(
        """
        SELECT (SELECT COUNT(*) FROM direct_messages m
                  JOIN friendships f ON f.status = 'ACCEPTED'
                   AND LEAST(f.requester_id, f.addressee_id) = LEAST(m.sender_id, m.recipient_id)
                   AND GREATEST(f.requester_id, f.addressee_id) = GREATEST(m.sender_id, m.recipient_id)
                 WHERE m.recipient_id = %(yo)s AND m.read_at IS NULL)::int AS unread_messages,
               (SELECT COUNT(*) FROM friendships
                 WHERE addressee_id = %(yo)s AND status = 'PENDING')::int AS pending_requests
        """,
        {"yo": usuario["id"]},
    ).fetchone()


@router.get("/status/{user_id}", summary="Relación con otra persona: NONE, FRIENDS, REQUEST_SENT o REQUEST_RECEIVED")
def estado(user_id: int, usuario: Usuario, db: Db) -> dict:
    fila = _par(db, usuario["id"], user_id)
    if not fila:
        return {"status": "NONE", "request_id": None}
    if fila["status"] == "ACCEPTED":
        return {"status": "FRIENDS", "request_id": fila["id"]}
    return {"status": "REQUEST_SENT" if fila["requester_id"] == usuario["id"] else "REQUEST_RECEIVED",
            "request_id": fila["id"]}


@router.post("/requests", status_code=201, summary="Enviar una solicitud de amistad")
def enviar_solicitud(datos: AmistadCrear, usuario: Usuario, db: Db) -> dict:
    yo, otro = usuario["id"], datos.user_id
    if otro == yo:
        raise ApiError(422, "CANNOT_ADD_SELF", "No puedes agregarte a ti mismo.")
    destino = db.execute("SELECT account_status FROM users WHERE id = %s", (otro,)).fetchone()
    if not destino or destino["account_status"] == "BANNED":
        raise ApiError(404, "USER_NOT_FOUND", "Ese jugador no existe.")
    if _bloqueados(db, yo, otro):
        raise ApiError(403, "FRIEND_BLOCKED", "No puedes agregar a este jugador.")

    with db.transaction():
        existente = _par(db, yo, otro)
        if existente:
            if existente["status"] == "ACCEPTED":
                raise ApiError(409, "ALREADY_FRIENDS", "Ya son amigos.")
            if existente["requester_id"] == yo:
                raise ApiError(409, "REQUEST_ALREADY_SENT", "Ya le enviaste una solicitud.")
            # La otra persona ya te había enviado una: agregarla equivale a aceptar
            db.execute("UPDATE friendships SET status = 'ACCEPTED', responded_at = NOW() WHERE id = %s",
                       (existente["id"],))
            return {"id": existente["id"], "status": "ACCEPTED"}
        fila = db.execute(
            "INSERT INTO friendships (requester_id, addressee_id) VALUES (%s, %s) RETURNING id",
            (yo, otro),
        ).fetchone()
    return {"id": fila["id"], "status": "PENDING"}


@router.put("/requests/{request_id}", summary="Aceptar o rechazar una solicitud recibida")
def responder_solicitud(request_id: int, datos: AmistadDecision, usuario: Usuario, db: Db) -> dict:
    with db.transaction():
        fila = db.execute(
            "SELECT id, requester_id, addressee_id, status FROM friendships WHERE id = %s FOR UPDATE",
            (request_id,),
        ).fetchone()
        if not fila or fila["addressee_id"] != usuario["id"] or fila["status"] != "PENDING":
            raise ApiError(404, "REQUEST_NOT_FOUND", "Esa solicitud no existe.")
        if datos.status == "REJECTED":
            db.execute("DELETE FROM friendships WHERE id = %s", (request_id,))
            return {"id": request_id, "status": "REJECTED"}
        if _bloqueados(db, fila["requester_id"], fila["addressee_id"]):
            raise ApiError(403, "FRIEND_BLOCKED", "No puedes aceptar esta solicitud.")
        db.execute("UPDATE friendships SET status = 'ACCEPTED', responded_at = NOW() WHERE id = %s", (request_id,))
    return {"id": request_id, "status": "ACCEPTED"}


@router.delete("/{user_id}", status_code=204, summary="Eliminar a un amigo o cancelar una solicitud")
def eliminar(user_id: int, usuario: Usuario, db: Db) -> Response:
    fila = _par(db, usuario["id"], user_id)
    if not fila:
        raise ApiError(404, "NOT_FRIENDS", "No tienes una amistad ni una solicitud con esa persona.")
    db.execute("DELETE FROM friendships WHERE id = %s", (fila["id"],))
    return Response(status_code=204)
