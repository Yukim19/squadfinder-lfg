"""Pruebas de salas (crear, feed, detalle, editar, cancelar) y solicitudes para unirse.

Datos de demo: sala 1 = Valorant de ana (bruno aceptado, diego pendiente),
sala 2 = LoL de carla, sala 3 = partida terminada de bruno, sala 4 = Fortnite crossplay de diego.
"""

from conftest import como

SALAS = "/api/v1/lfg/posts"
NUEVA = {
    "game_id": 7,  # Fortnite (crossplay), está en el perfil de ana
    "title": "Duos casuales",
    "max_players": 2,
    "platforms": ["PC", "Mobile", "PC"],
}


def test_crear_sala(cliente):
    r = cliente.post(SALAS, headers=como("ana"), json=NUEVA)
    assert r.status_code == 201
    sala = r.json()
    assert sala["platforms"] == ["Mobile", "PC"]  # sin repetidos
    assert sala["status"] == "OPEN" and sala["current_players"] == 1
    assert sala["is_host"] is True
    assert [m["username"] for m in sala["members"]] == ["ana_gg"]


def test_reglas_al_crear(cliente):
    def crear(**cambios):
        return cliente.post(SALAS, headers=como("ana"), json=NUEVA | cambios)

    # Solo juegos del perfil (ana no tiene League of Legends)
    assert crear(game_id=5, platforms=["PC"]).json()["error"]["code"] == "GAME_NOT_IN_PROFILE"
    # Valorant no tiene crossplay: una sola plataforma
    assert crear(game_id=1, platforms=["PC", "Xbox"]).json()["error"]["code"] == "NO_CROSSPLAY"
    # Valorant no existe en Switch
    r = crear(game_id=1, platforms=["Switch"])
    assert r.json()["error"]["code"] == "PLATFORM_NOT_AVAILABLE"
    assert r.json()["error"]["details"] == ["Switch"]
    # El rango solo en partidas competitivas
    assert crear(rank_required="Oro").status_code == 422
    assert crear(play_mode="COMPETITIVE", rank_required="Oro").status_code == 201
    # Límites de la base de datos
    assert crear(max_players=11).status_code == 422
    assert crear(title="  ").status_code == 422
    assert crear(platforms=[]).status_code == 422


def test_feed_y_filtros(cliente):
    def titulos(usuario="ana", **filtros):
        return {s["title"] for s in cliente.get(SALAS, headers=como(usuario), params=filtros).json()}

    # Las terminadas no salen en el feed
    assert titulos() == {"Ranked tranqui esta noche", "Flex queue, chill vibes", "Dúos cross-plataforma"}
    assert titulos(game_id=1) == {"Ranked tranqui esta noche"}
    assert titulos(platform="Switch") == {"Dúos cross-plataforma"}
    assert titulos(play_mode="COMPETITIVE") == {"Ranked tranqui esta noche"}
    # "es" incluye las salas de cualquier idioma
    assert titulos(language="es") == {"Ranked tranqui esta noche", "Dúos cross-plataforma"}
    assert titulos(region="NA_WEST") == {"Flex queue, chill vibes"}
    assert titulos(only_my_games=True) == {"Ranked tranqui esta noche", "Dúos cross-plataforma"}
    assert titulos(q="flex") == {"Flex queue, chill vibes"}

    feed = cliente.get(SALAS, headers=como("diego"), params={"game_id": 1}).json()
    assert feed[0]["my_application_status"] == "PENDING"
    assert feed[0]["host_region"] == "NA_EAST"


def test_feed_respeta_la_lista_negra(cliente):
    cliente.post(SALAS, headers=como("bruno"), json={"game_id": 1, "title": "Ranked de bruno",
                                                     "max_players": 5, "platforms": ["PC"]})
    # diego tiene a bruno en su lista negra; ana no
    assert "Ranked de bruno" in {s["title"] for s in cliente.get(SALAS, headers=como("ana")).json()}
    assert "Ranked de bruno" not in {s["title"] for s in cliente.get(SALAS, headers=como("diego")).json()}


def test_detalle(cliente):
    sala = cliente.get(f"{SALAS}/1", headers=como("ana")).json()
    assert sala["game_name"] == "Valorant"
    assert [m["username"] for m in sala["members"]] == ["ana_gg", "bruno_tank"]
    assert sala["current_players"] == 2
    assert sala["pending_applications"] == 1

    otra = cliente.get(f"{SALAS}/1", headers=como("diego")).json()
    assert otra["is_host"] is False
    assert otra["my_application"]["status"] == "PENDING"
    assert "pending_applications" not in otra

    assert cliente.get(f"{SALAS}/999", headers=como("ana")).status_code == 404


def test_editar_sala(cliente):
    r = cliente.put(f"{SALAS}/1", headers=como("ana"), json={"play_mode": "CASUAL", "platforms": ["Xbox"]})
    assert r.status_code == 200
    assert r.json()["rank_required"] is None  # al pasar a casual se quita el rango
    assert r.json()["platforms"] == ["Xbox"]

    # Con diego aceptado hay 3 jugadores: el máximo no puede bajar a 2
    diego = cliente.get(f"{SALAS}/1/applications", headers=como("ana"), params={"status": "PENDING"}).json()[0]
    cliente.put(f"{SALAS}/1/applications/{diego['id']}", headers=como("ana"), json={"status": "ACCEPTED"})
    r = cliente.put(f"{SALAS}/1", headers=como("ana"), json={"max_players": 2})
    assert r.json()["error"]["code"] == "MAX_BELOW_CURRENT"
    cliente.put(f"{SALAS}/1/applications/{diego['id']}", headers=como("ana"), json={"status": "REJECTED"})

    # Con 2 jugadores y máximo 2 la sala queda llena
    assert cliente.put(f"{SALAS}/1", headers=como("ana"), json={"max_players": 2}).json()["status"] == "FULL"
    assert cliente.put(f"{SALAS}/1", headers=como("ana"), json={"max_players": 4}).json()["status"] == "OPEN"

    assert cliente.put(f"{SALAS}/1", headers=como("bruno"), json={"title": "Hackeada"}).json()["error"]["code"] == "NOT_HOST"
    assert cliente.put(f"{SALAS}/1", headers=como("ana"), json={"game_id": 2}).status_code == 422


def test_empezar_y_terminar_partida(cliente, db):
    assert cliente.put(f"{SALAS}/1", headers=como("ana"), json={"status": "IN_PROGRESS"}).json()["status"] == "IN_PROGRESS"
    terminada = cliente.put(f"{SALAS}/1", headers=como("ana"), json={"status": "CLOSED"}).json()
    assert terminada["status"] == "CLOSED" and terminada["closed_at"] is not None
    # La solicitud pendiente de diego se rechaza sola
    assert db.execute("SELECT status FROM applications WHERE post_id = 1 AND applicant_id = 4").fetchone()[0] == "REJECTED"
    # Ya no se puede editar ni cancelar: es historial
    assert cliente.put(f"{SALAS}/1", headers=como("ana"), json={"title": "Otra"}).json()["error"]["code"] == "POST_FINISHED"
    assert cliente.delete(f"{SALAS}/1", headers=como("ana")).status_code == 409


def test_cancelar_sala(cliente):
    assert cliente.delete(f"{SALAS}/2", headers=como("ana")).status_code == 204  # ana es ADMIN
    assert cliente.get(f"{SALAS}/2", headers=como("carla")).json()["status"] == "CANCELLED"
    assert cliente.delete(f"{SALAS}/4", headers=como("carla")).json()["error"]["code"] == "NOT_HOST"
    assert cliente.delete(f"{SALAS}/4", headers=como("diego")).status_code == 204


# ---------------------------------------------------------------------------
# Solicitudes
# ---------------------------------------------------------------------------
def test_flujo_de_solicitudes(cliente):
    # carla pide unirse a la sala de diego
    r = cliente.post(f"{SALAS}/4/applications", headers=como("carla"), json={"message": "Juego en Switch"})
    assert r.status_code == 201
    solicitud = r.json()
    assert solicitud["status"] == "PENDING" and solicitud["username"] == "carla_heals"

    otra_vez = cliente.post(f"{SALAS}/4/applications", headers=como("carla"), json={})
    assert otra_vez.json()["error"]["code"] == "ALREADY_APPLIED"
    propia = cliente.post(f"{SALAS}/4/applications", headers=como("diego"), json={})
    assert propia.json()["error"]["code"] == "IS_HOST"

    # Solo el anfitrión ve y decide
    assert cliente.get(f"{SALAS}/4/applications", headers=como("carla")).status_code == 403
    pendientes = cliente.get(f"{SALAS}/4/applications", headers=como("diego"), params={"status": "PENDING"}).json()
    assert [p["username"] for p in pendientes] == ["carla_heals"]

    aceptada = cliente.put(f"{SALAS}/4/applications/{solicitud['id']}", headers=como("diego"), json={"status": "ACCEPTED"})
    assert aceptada.json()["status"] == "ACCEPTED"
    assert cliente.get(f"{SALAS}/4", headers=como("diego")).json()["current_players"] == 2

    # carla se sale y puede volver a pedir entrar
    assert cliente.delete(f"{SALAS}/4/applications/me", headers=como("carla")).status_code == 204
    assert cliente.delete(f"{SALAS}/4/applications/me", headers=como("carla")).status_code == 404
    assert cliente.post(f"{SALAS}/4/applications", headers=como("carla"), json={}).json()["status"] == "PENDING"


def test_sala_se_llena_y_se_vuelve_a_abrir(cliente):
    cliente.put(f"{SALAS}/4", headers=como("diego"), json={"max_players": 2})
    ana = cliente.post(f"{SALAS}/4/applications", headers=como("ana"), json={}).json()
    carla = cliente.post(f"{SALAS}/4/applications", headers=como("carla"), json={}).json()

    cliente.put(f"{SALAS}/4/applications/{ana['id']}", headers=como("diego"), json={"status": "ACCEPTED"})
    assert cliente.get(f"{SALAS}/4", headers=como("diego")).json()["status"] == "FULL"

    llena = cliente.put(f"{SALAS}/4/applications/{carla['id']}", headers=como("diego"), json={"status": "ACCEPTED"})
    assert llena.json()["error"]["code"] == "POST_FULL"
    # Una sala llena no recibe solicitudes nuevas
    assert cliente.post(f"{SALAS}/4/applications", headers=como("bruno"), json={}).json()["error"]["code"] == "POST_NOT_OPEN"

    # Sacar a ana libera el lugar
    sacada = cliente.put(f"{SALAS}/4/applications/{ana['id']}", headers=como("diego"), json={"status": "REJECTED"})
    assert sacada.json()["status"] == "REJECTED"
    assert cliente.get(f"{SALAS}/4", headers=como("diego")).json()["status"] == "OPEN"
    # Una vez rechazada no puede insistir
    assert cliente.post(f"{SALAS}/4/applications", headers=como("ana"), json={}).json()["error"]["code"] == "APPLICATION_REJECTED"


def test_lista_negra_del_anfitrion_impide_unirse(cliente):
    cliente.post(SALAS, headers=como("bruno"), json={"game_id": 1, "title": "Sala de bruno",
                                                     "max_players": 5, "platforms": ["PC"]})
    sala_id = cliente.get(SALAS, headers=como("ana"), params={"q": "Sala de bruno"}).json()[0]["id"]
    cliente.post("/api/v1/users/me/blocks", headers=como("bruno"), json={"user_id": 3})
    r = cliente.post(f"{SALAS}/{sala_id}/applications", headers=como("carla"), json={})
    assert r.status_code == 403 and r.json()["error"]["code"] == "CANNOT_JOIN"
