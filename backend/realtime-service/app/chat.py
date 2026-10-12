"""Salas de chat en memoria y mensajes en la base de datos.

Cada mensaje se guarda una sola vez (texto original + toxicity_level) y al repartirlo se
adapta a cada receptor según su filtro: a quien lo tiene oculto no le llega el texto.
"""

import time
from collections import deque
from dataclasses import dataclass, field

from fastapi import WebSocket

from .database import conexion
from .security import ErrorAuth, acceso_a_sala
from .toxicidad import Nivel, clasificar, se_oculta

ABIERTAS = ("OPEN", "FULL", "IN_PROGRESS")


@dataclass(eq=False)
class Conexion:
    websocket: WebSocket
    usuario: dict
    envios: deque = field(default_factory=deque)  # momentos de los últimos mensajes (anti-spam)


def mensaje_para(fila: dict, receptor: dict) -> dict:
    """Mensaje tal como lo debe ver `receptor` según su filtro."""
    propio = fila["sender_id"] == receptor["id"]
    oculto = not propio and se_oculta(fila["toxicity_level"], receptor["toxicity_filter_level"])
    return {
        "type": "message",
        "id": fila["id"],
        "post_id": fila["post_id"],
        "sender_id": fila["sender_id"],
        "username": fila["username"],
        "avatar_url": fila["avatar_url"],
        "message": None if oculto else fila["message"],
        "hidden": oculto,
        "toxicity_level": fila["toxicity_level"],
        "sent_at": fila["sent_at"].isoformat(),
    }


def historial(post_id: int, receptor: dict, limite: int, antes_de: int | None) -> list[dict]:
    """Últimos mensajes de la sala (del más viejo al más nuevo)."""
    with conexion() as db:
        filas = db.execute(
            """
            SELECT m.id, m.post_id, m.sender_id, u.username, u.avatar_url, m.message, m.toxicity_level, m.sent_at
            FROM chat_messages m JOIN users u ON u.id = m.sender_id
            WHERE m.post_id = %s AND (%s::bigint IS NULL OR m.id < %s)
            ORDER BY m.id DESC
            LIMIT %s
            """,
            (post_id, antes_de, antes_de, limite),
        ).fetchall()
    return [mensaje_para(f, receptor) for f in reversed(filas)]


def guardar_mensaje(post_id: int, usuario: dict, texto: str) -> dict:
    """Clasifica y guarda el mensaje. Revisa otra vez que siga en la sala (pudieron sacarlo)."""
    toxicidad: Nivel = clasificar(texto)
    with conexion() as db:
        sala = acceso_a_sala(db, post_id, usuario["id"])
        if sala["status"] not in ABIERTAS:
            raise ErrorAuth("CHAT_CLOSED", "La partida terminó: el chat es solo de lectura.")
        fila = db.execute(
            """
            INSERT INTO chat_messages (post_id, sender_id, message, toxicity_level)
            VALUES (%s, %s, %s, %s)
            RETURNING id, post_id, sender_id, message, toxicity_level, sent_at
            """,
            (post_id, usuario["id"], texto, toxicidad),
        ).fetchone()
    return fila | {"username": usuario["username"], "avatar_url": usuario["avatar_url"]}


class Salas:
    """Conexiones abiertas por sala.

    Vive en memoria: alcanza para una sola instancia del servicio (Render gratis).
    Con varias instancias se usaría Redis Pub/Sub (Upstash) para repartir los mensajes.
    """

    def __init__(self) -> None:
        self._salas: dict[int, set[Conexion]] = {}

    def entrar(self, post_id: int, conexion: Conexion) -> None:
        self._salas.setdefault(post_id, set()).add(conexion)

    def salir(self, post_id: int, conexion: Conexion) -> None:
        sala = self._salas.get(post_id, set())
        sala.discard(conexion)
        if not sala:
            self._salas.pop(post_id, None)

    def conectados(self, post_id: int) -> list[dict]:
        unicos = {c.usuario["id"]: c.usuario for c in self._salas.get(post_id, set())}
        return sorted(({"user_id": u["id"], "username": u["username"]} for u in unicos.values()),
                      key=lambda u: u["username"])

    async def avisar_presencia(self, post_id: int) -> None:
        await self._enviar_a_todos(post_id, lambda _: {"type": "presence", "online": self.conectados(post_id)})

    async def repartir(self, post_id: int, fila: dict) -> None:
        await self._enviar_a_todos(post_id, lambda receptor: mensaje_para(fila, receptor))

    async def _enviar_a_todos(self, post_id: int, armar) -> None:
        for c in list(self._salas.get(post_id, set())):
            try:
                await c.websocket.send_json(armar(c.usuario))
            except Exception:
                # Conexión que se cortó sin avisar
                self.salir(post_id, c)


def permitido_por_ritmo(conexion: Conexion, maximo: int, ventana: float) -> bool:
    """Anti-spam: como máximo `maximo` mensajes cada `ventana` segundos."""
    ahora = time.monotonic()
    while conexion.envios and ahora - conexion.envios[0] > ventana:
        conexion.envios.popleft()
    if len(conexion.envios) >= maximo:
        return False
    conexion.envios.append(ahora)
    return True
