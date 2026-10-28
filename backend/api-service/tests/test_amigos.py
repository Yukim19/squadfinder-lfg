"""Pruebas de amigos: solicitudes, aceptar, rechazar, eliminar y bloqueos.

Datos de demo: ana (1) y bruno (2) son amigos y bruno le dejó un mensaje sin leer a ana.
carla (3) le envió una solicitud a ana. diego (4) tiene a bruno en su lista negra.
"""

from conftest import como

AMIGOS = "/api/v1/friends"


def test_lista_de_amigos_con_mensajes_sin_leer(cliente):
    amigos = cliente.get(AMIGOS, headers=como("ana")).json()
    assert [a["username"] for a in amigos] == ["bruno_tank"]
    assert amigos[0]["unread"] == 1
    assert amigos[0]["last_message_at"] is not None

    # Desde el otro lado, bruno ve a ana (y no tiene nada sin leer)
    de_bruno = cliente.get(AMIGOS, headers=como("bruno")).json()
    assert [(a["username"], a["unread"]) for a in de_bruno] == [("ana_gg", 0)]


def test_resumen_para_la_campanita(cliente):
    assert cliente.get(f"{AMIGOS}/summary", headers=como("ana")).json() == {"unread_messages": 1, "pending_requests": 1}
    assert cliente.get(f"{AMIGOS}/summary", headers=como("diego")).json() == {"unread_messages": 0, "pending_requests": 0}


def test_solicitudes_recibidas_y_enviadas(cliente):
    de_ana = cliente.get(f"{AMIGOS}/requests", headers=como("ana")).json()
    assert [s["username"] for s in de_ana["incoming"]] == ["carla_heals"]
    assert de_ana["outgoing"] == []
    de_carla = cliente.get(f"{AMIGOS}/requests", headers=como("carla")).json()
    assert [s["username"] for s in de_carla["outgoing"]] == ["ana_gg"]


def test_enviar_y_aceptar_una_solicitud(cliente):
    r = cliente.post(f"{AMIGOS}/requests", headers=como("diego"), json={"user_id": 3})
    assert r.status_code == 201 and r.json()["status"] == "PENDING"
    assert cliente.get(f"{AMIGOS}/status/3", headers=como("diego")).json()["status"] == "REQUEST_SENT"
    assert cliente.get(f"{AMIGOS}/status/4", headers=como("carla")).json()["status"] == "REQUEST_RECEIVED"

    aceptada = cliente.put(f"{AMIGOS}/requests/{r.json()['id']}", headers=como("carla"), json={"status": "ACCEPTED"})
    assert aceptada.json()["status"] == "ACCEPTED"
    assert "carla_heals" in [a["username"] for a in cliente.get(AMIGOS, headers=como("diego")).json()]
    assert cliente.get(f"{AMIGOS}/status/4", headers=como("carla")).json()["status"] == "FRIENDS"


def test_rechazar_borra_la_solicitud(cliente):
    pendiente = cliente.get(f"{AMIGOS}/requests", headers=como("ana")).json()["incoming"][0]
    r = cliente.put(f"{AMIGOS}/requests/{pendiente['id']}", headers=como("ana"), json={"status": "REJECTED"})
    assert r.json()["status"] == "REJECTED"
    assert cliente.get(f"{AMIGOS}/status/3", headers=como("ana")).json()["status"] == "NONE"


def test_solo_quien_recibe_puede_responder(cliente):
    solicitud = cliente.get(f"{AMIGOS}/requests", headers=como("ana")).json()["incoming"][0]
    for quien in ("carla", "bruno"):  # carla la envió; bruno no tiene nada que ver
        r = cliente.put(f"{AMIGOS}/requests/{solicitud['id']}", headers=como(quien), json={"status": "ACCEPTED"})
        assert r.json()["error"]["code"] == "REQUEST_NOT_FOUND"


def test_agregar_a_quien_ya_te_agrego_los_hace_amigos(cliente):
    # carla ya le había enviado una solicitud a ana: si ana la agrega, quedan como amigas al instante
    r = cliente.post(f"{AMIGOS}/requests", headers=como("ana"), json={"user_id": 3})
    assert r.status_code == 201 and r.json()["status"] == "ACCEPTED"
    assert cliente.get(f"{AMIGOS}/status/1", headers=como("carla")).json()["status"] == "FRIENDS"


def test_reglas_de_las_solicitudes(cliente):
    def agregar(usuario, otro):
        return cliente.post(f"{AMIGOS}/requests", headers=como(usuario), json={"user_id": otro}).json()["error"]["code"]

    assert agregar("ana", 1) == "CANNOT_ADD_SELF"
    assert agregar("ana", 2) == "ALREADY_FRIENDS"
    assert agregar("carla", 1) == "REQUEST_ALREADY_SENT"
    assert agregar("ana", 999) == "USER_NOT_FOUND"
    # diego tiene a bruno en su lista negra: ninguno de los dos puede agregar al otro
    assert agregar("diego", 2) == "FRIEND_BLOCKED"
    assert agregar("bruno", 4) == "FRIEND_BLOCKED"


def test_eliminar_amigo_y_cancelar_solicitud(cliente):
    assert cliente.delete(f"{AMIGOS}/2", headers=como("ana")).status_code == 204
    assert cliente.get(AMIGOS, headers=como("bruno")).json() == []
    # carla cancela su solicitud pendiente
    assert cliente.delete(f"{AMIGOS}/1", headers=como("carla")).status_code == 204
    assert cliente.get(f"{AMIGOS}/requests", headers=como("ana")).json()["incoming"] == []
    assert cliente.delete(f"{AMIGOS}/2", headers=como("ana")).json()["error"]["code"] == "NOT_FRIENDS"


def test_bloquear_deshace_la_amistad(cliente):
    r = cliente.post("/api/v1/users/me/blocks", headers=como("ana"), json={"user_id": 2})
    assert r.status_code == 201
    assert cliente.get(f"{AMIGOS}/status/2", headers=como("ana")).json()["status"] == "NONE"
    assert cliente.get(AMIGOS, headers=como("bruno")).json() == []


def test_buscar_jugadores_para_agregar(cliente):
    def buscar(usuario, q):
        return cliente.get("/api/v1/users/search", headers=como(usuario), params={"q": q})

    r = buscar("ana", "br").json()
    assert [(j["username"], j["friendship"]) for j in r] == [("bruno_tank", "FRIENDS")]
    assert [(j["username"], j["friendship"]) for j in buscar("ana", "carl").json()] == [("carla_heals", "REQUEST_RECEIVED")]
    assert [(j["username"], j["friendship"]) for j in buscar("carla", "ana").json()] == [("ana_gg", "REQUEST_SENT")]
    assert [(j["username"], j["friendship"]) for j in buscar("diego", "carla").json()] == [("carla_heals", "NONE")]
    # No aparece uno mismo ni quien está en una lista negra (en ningún sentido)
    assert buscar("ana", "ana").json() == []
    assert buscar("diego", "bruno").json() == []
    assert buscar("bruno", "diego").json() == []
    # Los comodines se buscan como texto, y se piden al menos 2 letras
    assert buscar("ana", "%%").json() == []
    assert buscar("ana", "b").status_code == 422
