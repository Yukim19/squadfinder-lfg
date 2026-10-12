"""Pruebas de salud, autenticación, errores y catálogo."""

from conftest import como


def test_health(cliente):
    r = cliente.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_sin_autenticacion_da_401(cliente):
    r = cliente.get("/api/v1/users/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_usuario_sin_onboarding_da_403(cliente):
    r = cliente.get("/api/v1/users/me", headers={"X-Dev-User": "auth0|nuevo"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ONBOARDING_REQUIRED"


def test_cuenta_eliminada_no_puede_entrar(cliente, db):
    db.execute("UPDATE users SET account_status = 'BANNED' WHERE username = 'bruno_tank'")
    r = cliente.get("/api/v1/users/me", headers=como("bruno"))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ACCOUNT_BANNED"


def test_cuenta_suspendida_y_reactivacion(cliente, db):
    db.execute("UPDATE users SET account_status = 'SUSPENDED', suspended_until = NOW() + INTERVAL '2 days' "
               "WHERE username = 'carla_heals'")
    r = cliente.get("/api/v1/users/me", headers=como("carla"))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ACCOUNT_SUSPENDED"
    assert "suspended_until" in r.json()["error"]["details"]

    # Cuando la suspensión termina, la cuenta se reactiva sola
    db.execute("UPDATE users SET suspended_until = NOW() - INTERVAL '1 minute' WHERE username = 'carla_heals'")
    r = cliente.get("/api/v1/users/me", headers=como("carla"))
    assert r.status_code == 200
    assert r.json()["account_status"] == "ACTIVE"


def test_catalogo_de_juegos(cliente):
    juegos = cliente.get("/api/v1/catalog/games").json()
    assert len(juegos) == 35
    valorant = next(j for j in juegos if j["name"] == "Valorant")
    assert valorant["crossplay"] is False
    assert valorant["platforms"] == ["PC", "PlayStation", "Xbox"]

    moviles = cliente.get("/api/v1/catalog/games", params={"platform": "Mobile"}).json()
    assert len(moviles) == 17
    assert all("Mobile" in j["platforms"] for j in moviles)


def test_generos(cliente):
    generos = cliente.get("/api/v1/catalog/genres").json()
    assert len(generos) == 16


def test_sugerir_juego(cliente):
    existente = cliente.post("/api/v1/catalog/game-requests", headers=como("ana"), json={"game_name": "valorant"})
    assert existente.status_code == 409
    assert existente.json()["error"]["code"] == "GAME_EXISTS"

    nuevo = cliente.post("/api/v1/catalog/game-requests", headers=como("ana"),
                         json={"game_name": "Splitgate 2", "platforms_note": "PC"})
    assert nuevo.status_code == 201
    assert nuevo.json()["status"] == "PENDING"

    repetido = cliente.post("/api/v1/catalog/game-requests", headers=como("ana"), json={"game_name": "SPLITGATE 2"})
    assert repetido.status_code == 409
    assert repetido.json()["error"]["code"] == "REQUEST_PENDING"


def test_validacion_con_formato_uniforme(cliente):
    r = cliente.post("/api/v1/catalog/game-requests", headers=como("ana"), json={"game_name": "x"})
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["campo"] == "game_name"
