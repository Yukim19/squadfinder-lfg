"""Pruebas de los mensajes privados entre amigos.

Datos de demo: ana (1) y bruno (2) son amigos y tienen 3 mensajes (el último, de bruno, sin leer).
carla (3) le envió una solicitud a ana pero todavía no son amigas. diego (4) tiene a bruno en su lista negra.
ana usa el filtro STRICT, bruno MEDIUM y carla OFF.
"""

import pytest
from fastapi.websockets import WebSocketDisconnect

from conftest import auth, como

HISTORIAL = "/api/v1/dm/{}/history"
LEER = "/api/v1/dm/{}/read"


def recibir(ws, tipo: str) -> dict:
    """Lee mensajes hasta encontrar uno del tipo pedido (se saltan los avisos de presencia)."""
    for _ in range(20):
        mensaje = ws.receive_json()
        if mensaje["type"] == tipo:
            return mensaje
    raise AssertionError(f"No llegó ningún mensaje de tipo {tipo}")


def cierre(ws) -> int:
    with pytest.raises(WebSocketDisconnect) as e:
        for _ in range(5):
            ws.receive_json()
    return e.value.code


def hacerse_amigos(db, a: int, b: int) -> None:
    db.execute("INSERT INTO friendships (requester_id, addressee_id, status, responded_at) "
               "VALUES (%s, %s, 'ACCEPTED', NOW())", (a, b))


# ---------------------------------------------------------------------------
# Historial
# ---------------------------------------------------------------------------
def test_historial_de_la_conversacion(cliente):
    de_ana = cliente.get(HISTORIAL.format(2), headers=como("ana")).json()
    assert [m["message"] for m in de_ana] == [
        "Oye, ¿jugamos ranked más tarde?", "¡Dale! Entro a las 8.", "Perfecto, te espero en la sala."]
    assert [m["sender_id"] for m in de_ana] == [2, 1, 2]
    # Es la misma conversación vista desde el otro lado
    assert len(cliente.get(HISTORIAL.format(1), headers=como("bruno")).json()) == 3


def test_solo_los_amigos_pueden_leer_y_escribir(cliente, db):
    # carla y ana todavía no son amigas (solo hay una solicitud pendiente)
    r = cliente.get(HISTORIAL.format(3), headers=como("ana"))
    assert r.status_code == 403 and r.json()["error"]["code"] == "NOT_FRIENDS"
    assert cliente.get(HISTORIAL.format(999), headers=como("ana")).json()["error"]["code"] == "USER_NOT_FOUND"
    # Sin sesión no hay acceso
    assert cliente.get(HISTORIAL.format(2)).status_code == 401


def test_marcar_como_leidos(cliente, db):
    assert db.execute("SELECT COUNT(*) FROM direct_messages WHERE read_at IS NULL").fetchone()[0] == 1
    assert cliente.post(LEER.format(2), headers=como("ana")).json() == {"marked": 1}
    assert db.execute("SELECT COUNT(*) FROM direct_messages WHERE read_at IS NULL").fetchone()[0] == 0
    assert cliente.post(LEER.format(2), headers=como("ana")).json() == {"marked": 0}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
def test_conectarse_requiere_sesion(cliente):
    with cliente.websocket_connect("/ws/dm") as ws:
        ws.send_json({"type": "message", "to": 2, "message": "hola"})
        assert recibir(ws, "error")["code"] == "NOT_AUTHENTICATED"
        assert cierre(ws) == 4401


def test_origen_no_permitido(cliente):
    with pytest.raises(WebSocketDisconnect) as e:
        with cliente.websocket_connect("/ws/dm", headers={"origin": "https://sitio-malicioso.example"}):
            pass
    assert e.value.code == 4403


def test_mensaje_privado_en_vivo_y_presencia(cliente, db):
    with cliente.websocket_connect("/ws/dm") as ana, cliente.websocket_connect("/ws/dm") as bruno:
        ana.send_json(auth("ana"))
        assert recibir(ana, "ready")["online"] == []  # bruno todavía no está conectado
        bruno.send_json(auth("bruno"))
        assert recibir(bruno, "ready")["online"] == [1]
        assert recibir(ana, "presence") == {"type": "presence", "user_id": 2, "online": True}

        ana.send_json({"type": "message", "to": 2, "message": "Ya estoy dentro"})
        recibido = recibir(bruno, "message")
        assert recibido["message"] == "Ya estoy dentro" and recibido["sender_id"] == 1 and recibido["hidden"] is False
        eco = recibir(ana, "message")  # el emisor recibe el eco: confirma que se guardó
        assert eco["id"] == recibido["id"]

    guardado = db.execute("SELECT sender_id, recipient_id, message FROM direct_messages ORDER BY id DESC LIMIT 1").fetchone()
    assert guardado == (1, 2, "Ya estoy dentro")


def test_el_filtro_de_quien_recibe_oculta_los_insultos(cliente):
    with cliente.websocket_connect("/ws/dm") as ana, cliente.websocket_connect("/ws/dm") as bruno:
        ana.send_json(auth("ana"))
        recibir(ana, "ready")
        bruno.send_json(auth("bruno"))
        recibir(bruno, "ready")

        bruno.send_json({"type": "message", "to": 1, "message": "eres un idiota de mierda"})
        # ana usa STRICT: el texto no le llega. bruno (quien lo escribió) sí ve el suyo.
        para_ana = recibir(ana, "message")
        assert para_ana["hidden"] is True and para_ana["message"] is None and para_ana["toxicity_level"] == "SEVERE"
        propio = recibir(bruno, "message")
        assert propio["hidden"] is False and propio["message"] == "eres un idiota de mierda"


def test_no_se_puede_escribir_a_quien_no_es_amigo(cliente, db):
    with cliente.websocket_connect("/ws/dm") as ana:
        ana.send_json(auth("ana"))
        recibir(ana, "ready")
        ana.send_json({"type": "message", "to": 3, "message": "hola carla"})
        assert recibir(ana, "error")["code"] == "NOT_FRIENDS"
        ana.send_json({"type": "message", "to": 999, "message": "hola"})
        assert recibir(ana, "error")["code"] == "USER_NOT_FOUND"
        ana.send_json({"type": "message", "to": 1, "message": "yo conmigo"})
        assert recibir(ana, "error")["code"] == "VALIDATION_ERROR"
    assert db.execute("SELECT COUNT(*) FROM direct_messages").fetchone()[0] == 3


def test_la_lista_negra_corta_la_conversacion(cliente, db):
    # diego y bruno fueran amigos, pero diego tiene a bruno en su lista negra
    hacerse_amigos(db, 4, 2)
    with cliente.websocket_connect("/ws/dm") as bruno:
        bruno.send_json(auth("bruno"))
        recibir(bruno, "ready")
        bruno.send_json({"type": "message", "to": 4, "message": "hola diego"})
        assert recibir(bruno, "error")["code"] == "FRIEND_BLOCKED"


def test_validaciones_y_ritmo(cliente):
    with cliente.websocket_connect("/ws/dm") as ws:
        ws.send_json(auth("ana"))
        recibir(ws, "ready")
        ws.send_json({"type": "message", "to": 2, "message": "   "})
        assert recibir(ws, "error")["code"] == "VALIDATION_ERROR"
        ws.send_json({"type": "message", "to": 2, "message": "x" * 501})
        assert recibir(ws, "error")["code"] == "VALIDATION_ERROR"
        ws.send_json({"type": "cosa-rara"})
        assert recibir(ws, "error")["code"] == "UNKNOWN_TYPE"
        # Anti-spam: 5 mensajes cada 5 segundos
        for _ in range(5):
            ws.send_json({"type": "message", "to": 2, "message": "spam"})
            recibir(ws, "message")
        ws.send_json({"type": "message", "to": 2, "message": "uno más"})
        assert recibir(ws, "error")["code"] == "RATE_LIMITED"


def test_marcar_leidos_por_websocket(cliente, db):
    with cliente.websocket_connect("/ws/dm") as ana:
        ana.send_json(auth("ana"))
        recibir(ana, "ready")
        ana.send_json({"type": "read", "with": 2})
        assert recibir(ana, "read") == {"type": "read", "with": 2}
    assert db.execute("SELECT COUNT(*) FROM direct_messages WHERE read_at IS NULL").fetchone()[0] == 0
