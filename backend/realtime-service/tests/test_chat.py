"""Pruebas del chat en vivo y del historial.

Datos de demo: sala 1 (abierta) = ana (anfitriona, filtro STRICT) y bruno (aceptado, filtro MEDIUM);
diego tiene la solicitud pendiente. Sala 3 = partida terminada. El chat de la sala 1 tiene
3 mensajes; el último de bruno es MILD.
"""

import pytest
from fastapi.websockets import WebSocketDisconnect

from conftest import auth, como

HISTORIAL = "/api/v1/chat/posts/{}/history"


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


# ---------------------------------------------------------------------------
# Historial (ruta REST de la propuesta)
# ---------------------------------------------------------------------------
def test_historial_segun_el_filtro(cliente):
    de_ana = cliente.get(HISTORIAL.format(1), headers=como("ana")).json()
    assert len(de_ana) == 3
    # ana usa STRICT: el mensaje MILD de bruno le llega oculto y sin el texto
    assert de_ana[-1]["hidden"] is True and de_ana[-1]["message"] is None
    assert de_ana[0]["message"] == "¡Hola! Entramos en 10 min"

    # bruno lo escribió: siempre ve sus propios mensajes
    de_bruno = cliente.get(HISTORIAL.format(1), headers=como("bruno")).json()
    assert de_bruno[-1]["hidden"] is False

    paginado = cliente.get(HISTORIAL.format(1), headers=como("ana"), params={"limit": 1, "before_id": de_ana[-1]["id"]})
    assert [m["id"] for m in paginado.json()] == [de_ana[1]["id"]]


def test_historial_solo_para_integrantes(cliente):
    sin_sesion = cliente.get(HISTORIAL.format(1))
    assert sin_sesion.status_code == 401
    assert sin_sesion.json()["error"]["code"] == "NOT_AUTHENTICATED"

    diego = cliente.get(HISTORIAL.format(1), headers=como("diego"))
    assert diego.status_code == 403 and diego.json()["error"]["code"] == "NOT_A_MEMBER"
    assert cliente.get(HISTORIAL.format(999), headers=como("ana")).status_code == 404


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
def test_conectarse_requiere_sesion(cliente):
    with cliente.websocket_connect("/ws/chat/1") as ws:
        ws.send_json({"type": "message", "message": "hola"})
        assert recibir(ws, "error")["code"] == "NOT_AUTHENTICATED"
        assert cierre(ws) == 4401

    with cliente.websocket_connect("/ws/chat/1") as ws:
        ws.send_json({"type": "auth", "token": "auth0|sin-perfil"})
        assert recibir(ws, "error")["code"] == "ONBOARDING_REQUIRED"
        assert cierre(ws) == 4403


def test_solo_integrantes_de_la_sala(cliente):
    with cliente.websocket_connect("/ws/chat/1") as ws:
        ws.send_json(auth("diego"))  # solicitud pendiente: todavía no es integrante
        assert recibir(ws, "error")["code"] == "NOT_A_MEMBER"
        assert cierre(ws) == 4403

    with cliente.websocket_connect("/ws/chat/999") as ws:
        ws.send_json(auth("ana"))
        assert recibir(ws, "error")["code"] == "POST_NOT_FOUND"
        assert cierre(ws) == 4404


def test_origen_no_permitido(cliente):
    with pytest.raises(WebSocketDisconnect) as e:
        with cliente.websocket_connect("/ws/chat/1", headers={"origin": "https://sitio-malicioso.example"}):
            pass
    assert e.value.code == 4403


def test_chat_en_vivo_con_filtro(cliente, db):
    with cliente.websocket_connect("/ws/chat/1") as ana, cliente.websocket_connect("/ws/chat/1") as bruno:
        ana.send_json(auth("ana"))
        listo = recibir(ana, "ready")
        assert listo["read_only"] is False and len(listo["history"]) == 3

        bruno.send_json(auth("bruno"))
        recibir(bruno, "ready")
        assert [u["username"] for u in recibir(ana, "presence")["online"]] == ["ana_gg"]  # cuando entró ella
        presencia = recibir(ana, "presence")  # cuando entró bruno
        assert [u["username"] for u in presencia["online"]] == ["ana_gg", "bruno_tank"]

        # Un mensaje limpio les llega a los dos
        bruno.send_json({"type": "message", "message": "Listo, entro ya"})
        assert recibir(ana, "message")["message"] == "Listo, entro ya"
        assert recibir(bruno, "message")["message"] == "Listo, entro ya"

        # Un insulto: ana (STRICT) no recibe el texto; bruno ve el suyo
        bruno.send_json({"type": "message", "message": "eres una idiota"})
        para_ana = recibir(ana, "message")
        assert para_ana["hidden"] is True and para_ana["message"] is None
        assert para_ana["toxicity_level"] == "SEVERE"
        assert recibir(bruno, "message")["message"] == "eres una idiota"

    # Se guardó el texto original con su clasificación (sirve de evidencia para un reporte)
    guardado = db.execute("SELECT message, toxicity_level FROM chat_messages ORDER BY id DESC LIMIT 1").fetchone()
    assert guardado == ("eres una idiota", "SEVERE")


def test_validaciones_del_mensaje(cliente):
    with cliente.websocket_connect("/ws/chat/1") as ws:
        ws.send_json(auth("ana"))
        recibir(ws, "ready")
        ws.send_json({"type": "message", "message": "   "})
        assert recibir(ws, "error")["code"] == "VALIDATION_ERROR"
        ws.send_json({"type": "message", "message": "x" * 501})
        assert recibir(ws, "error")["code"] == "VALIDATION_ERROR"
        ws.send_text("esto no es JSON")
        assert recibir(ws, "error")["code"] == "INVALID_JSON"
        ws.send_json({"type": "ping"})
        assert recibir(ws, "pong")["type"] == "pong"


def test_anti_spam(cliente):
    with cliente.websocket_connect("/ws/chat/1") as ws:
        ws.send_json(auth("ana"))
        recibir(ws, "ready")
        for i in range(5):
            ws.send_json({"type": "message", "message": f"mensaje {i}"})
            recibir(ws, "message")
        ws.send_json({"type": "message", "message": "uno más"})
        assert recibir(ws, "error")["code"] == "RATE_LIMITED"


def test_partida_terminada_es_solo_lectura(cliente):
    with cliente.websocket_connect("/ws/chat/3") as ws:
        ws.send_json(auth("diego"))
        assert recibir(ws, "ready")["read_only"] is True
        ws.send_json({"type": "message", "message": "gg"})
        assert recibir(ws, "error")["code"] == "CHAT_CLOSED"


def test_si_lo_sacan_de_la_sala_pierde_el_chat(cliente, db):
    with cliente.websocket_connect("/ws/chat/1") as ws:
        ws.send_json(auth("bruno"))
        recibir(ws, "ready")
        db.execute("UPDATE applications SET status = 'REJECTED' WHERE post_id = 1 AND applicant_id = 2")
        ws.send_json({"type": "message", "message": "sigo aquí?"})
        assert recibir(ws, "error")["code"] == "NOT_A_MEMBER"
        assert cierre(ws) == 4403
