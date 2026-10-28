"""Mensajes privados entre amigos.

Cada persona tiene UNA conexión WebSocket (/ws/dm) con la que recibe los mensajes de todos
sus amigos. Igual que en las salas, el texto original y su toxicity_level se guardan una vez
y al repartirlo se adapta al filtro de quien lo recibe.
"""

from fastapi import WebSocket

from .chat import Conexion, mensaje_para
from .database import conexion
from .security import ErrorAuth
from .toxicidad import Nivel, clasificar


def comprobar_amistad(db, yo: int, otro: int) -> dict:
    """Solo los amigos (sin bloqueos entre ellos) pueden escribirse. Devuelve los datos de `otro`."""
    if yo == otro:
        raise ErrorAuth("VALIDATION_ERROR", "No puedes escribirte a ti mismo.")
    destino = db.execute(
        "SELECT id, username, avatar_url, toxicity_filter_level, account_status FROM users WHERE id = %s",
        (otro,),
    ).fetchone()
    if destino is None or destino["account_status"] == "BANNED":
        raise ErrorAuth("USER_NOT_FOUND", "Ese jugador no existe.")
    amigos = db.execute(
        """
        SELECT 1 FROM friendships
        WHERE status = 'ACCEPTED'
          AND LEAST(requester_id, addressee_id) = LEAST(%(a)s, %(b)s)
          AND GREATEST(requester_id, addressee_id) = GREATEST(%(a)s, %(b)s)
        """,
        {"a": yo, "b": otro},
    ).fetchone()
    if not amigos:
        raise ErrorAuth("NOT_FRIENDS", "Solo puedes escribirle a tus amigos.")
    bloqueo = db.execute(
        """
        SELECT 1 FROM user_blocks
        WHERE (blocker_id = %(a)s AND blocked_id = %(b)s) OR (blocker_id = %(b)s AND blocked_id = %(a)s)
        """,
        {"a": yo, "b": otro},
    ).fetchone()
    if bloqueo:
        raise ErrorAuth("FRIEND_BLOCKED", "No puedes escribirle a esta persona.")
    return destino


def mensaje_privado_para(fila: dict, receptor: dict) -> dict:
    """Mensaje tal como lo debe ver `receptor`: oculto si su filtro lo exige (salvo los propios)."""
    visible = mensaje_para({**fila, "post_id": None, "avatar_url": None, "username": ""}, receptor)
    return {
        "type": "message",
        "id": fila["id"],
        "sender_id": fila["sender_id"],
        "recipient_id": fila["recipient_id"],
        "message": visible["message"],
        "hidden": visible["hidden"],
        "toxicity_level": fila["toxicity_level"],
        "sent_at": fila["sent_at"].isoformat(),
    }


def guardar_mensaje_privado(emisor: dict, otro_id: int, texto: str) -> tuple[dict, dict]:
    """Clasifica y guarda el mensaje. Devuelve (fila, datos del destinatario)."""
    toxicidad: Nivel = clasificar(texto)
    with conexion() as db:
        destino = comprobar_amistad(db, emisor["id"], otro_id)
        fila = db.execute(
            """
            INSERT INTO direct_messages (sender_id, recipient_id, message, toxicity_level)
            VALUES (%s, %s, %s, %s)
            RETURNING id, sender_id, recipient_id, message, toxicity_level, sent_at
            """,
            (emisor["id"], otro_id, texto, toxicidad),
        ).fetchone()
    return fila, destino


def historial_privado(yo: dict, otro_id: int, limite: int, antes_de: int | None) -> list[dict]:
    """Últimos mensajes con un amigo (del más viejo al más nuevo)."""
    with conexion() as db:
        comprobar_amistad(db, yo["id"], otro_id)
        filas = db.execute(
            """
            SELECT id, sender_id, recipient_id, message, toxicity_level, sent_at
            FROM direct_messages
            WHERE LEAST(sender_id, recipient_id) = LEAST(%(a)s, %(b)s)
              AND GREATEST(sender_id, recipient_id) = GREATEST(%(a)s, %(b)s)
              AND (%(antes)s::bigint IS NULL OR id < %(antes)s)
            ORDER BY id DESC
            LIMIT %(limite)s
            """,
            {"a": yo["id"], "b": otro_id, "antes": antes_de, "limite": limite},
        ).fetchall()
    return [mensaje_privado_para(f, yo) for f in reversed(filas)]


def marcar_leidos(yo: dict, otro_id: int) -> int:
    """Marca como leídos los mensajes que `otro` le envió a `yo`. Devuelve cuántos eran nuevos."""
    with conexion() as db:
        comprobar_amistad(db, yo["id"], otro_id)
        return db.execute(
            """
            UPDATE direct_messages SET read_at = NOW()
            WHERE recipient_id = %s AND sender_id = %s AND read_at IS NULL
            """,
            (yo["id"], otro_id),
        ).rowcount


def ids_de_amigos(user_id: int) -> list[int]:
    with conexion() as db:
        filas = db.execute(
            """
            SELECT CASE WHEN requester_id = %(yo)s THEN addressee_id ELSE requester_id END AS amigo
            FROM friendships WHERE status = 'ACCEPTED' AND %(yo)s IN (requester_id, addressee_id)
            """,
            {"yo": user_id},
        ).fetchall()
    return [f["amigo"] for f in filas]


class Buzones:
    """Conexiones abiertas de cada persona (una persona puede tener varias pestañas abiertas).

    Vive en memoria, igual que Salas: alcanza para una sola instancia del servicio.
    """

    def __init__(self) -> None:
        self._conexiones: dict[int, set[Conexion]] = {}

    def entrar(self, conexion_: Conexion) -> None:
        self._conexiones.setdefault(conexion_.usuario["id"], set()).add(conexion_)

    def salir(self, conexion_: Conexion) -> None:
        usuario_id = conexion_.usuario["id"]
        abiertas = self._conexiones.get(usuario_id, set())
        abiertas.discard(conexion_)
        if not abiertas:
            self._conexiones.pop(usuario_id, None)

    def en_linea(self, usuario_id: int) -> bool:
        return usuario_id in self._conexiones

    async def enviar(self, usuario_id: int, armar) -> None:
        """Envía a todas las pestañas de una persona; `armar(usuario)` arma el mensaje para ella."""
        for c in list(self._conexiones.get(usuario_id, set())):
            await self._mandar(c, armar(c.usuario))

    async def _mandar(self, c: Conexion, contenido: dict) -> None:
        websocket: WebSocket = c.websocket
        try:
            await websocket.send_json(contenido)
        except Exception:
            # Conexión que se cortó sin avisar
            self.salir(c)
