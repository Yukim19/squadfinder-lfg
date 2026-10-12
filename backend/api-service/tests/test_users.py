"""Pruebas de usuarios: onboarding, perfil, cuentas vinculadas, lista negra y perfil público."""

from conftest import como

NUEVO = {"X-Dev-User": "auth0|jugador-nuevo"}
ONBOARDING = {
    "username": "nuevo_jugador",
    "region": "LATAM_NORTH",
    "preferred_language_speak": "both",
    "games": [1, 19, 19],  # Valorant y PUBG Mobile (el repetido se ignora)
    "genres": [1],
}


def test_onboarding_crea_el_perfil(cliente):
    r = cliente.post("/api/v1/users/onboarding", headers=NUEVO, json=ONBOARDING)
    assert r.status_code == 201
    perfil = r.json()
    assert perfil["username"] == "nuevo_jugador"
    assert perfil["level"] == 1 and perfil["xp"] == 0
    assert perfil["games"] == [1, 19]
    assert perfil["is_onboarding_completed"] is True

    # Ya puede usar las rutas protegidas
    assert cliente.get("/api/v1/users/me", headers=NUEVO).status_code == 200

    # No puede hacer el onboarding dos veces
    otra_vez = cliente.post("/api/v1/users/onboarding", headers=NUEVO, json=ONBOARDING)
    assert otra_vez.json()["error"]["code"] == "ALREADY_ONBOARDED"


def test_onboarding_reglas(cliente):
    sin_juegos = cliente.post("/api/v1/users/onboarding", headers=NUEVO, json=ONBOARDING | {"games": []})
    assert sin_juegos.status_code == 422

    region_mala = cliente.post("/api/v1/users/onboarding", headers=NUEVO, json=ONBOARDING | {"region": "MARTE"})
    assert region_mala.status_code == 422

    nombre_con_espacios = cliente.post("/api/v1/users/onboarding", headers=NUEVO, json=ONBOARDING | {"username": "ana gg"})
    assert nombre_con_espacios.status_code == 422

    # Mismo nombre que ana_gg aunque cambien las mayúsculas
    ocupado = cliente.post("/api/v1/users/onboarding", headers=NUEVO, json=ONBOARDING | {"username": "ANA_GG"})
    assert ocupado.status_code == 409
    assert ocupado.json()["error"]["code"] == "USERNAME_TAKEN"

    juego_inexistente = cliente.post("/api/v1/users/onboarding", headers=NUEVO, json=ONBOARDING | {"games": [999]})
    assert juego_inexistente.status_code == 422
    assert juego_inexistente.json()["error"]["code"] == "INVALID_REFERENCE"
    # La transacción se deshizo: el usuario no quedó creado a medias
    assert cliente.get("/api/v1/users/me", headers=NUEVO).json()["error"]["code"] == "ONBOARDING_REQUIRED"

    campo_desconocido = cliente.post("/api/v1/users/onboarding", headers=NUEVO, json=ONBOARDING | {"role": "ADMIN"})
    assert campo_desconocido.status_code == 422


def test_mi_perfil(cliente):
    perfil = cliente.get("/api/v1/users/me", headers=como("ana")).json()
    assert perfil["username"] == "ana_gg"
    assert perfil["role"] == "ADMIN"
    assert perfil["linked_accounts"] == {"discord": "ana_gg", "twitch": "ana_gg_live"}
    assert "auth0_id" not in perfil


def test_actualizar_solo_lo_enviado(cliente):
    r = cliente.put("/api/v1/users/me", headers=como("ana"),
                    json={"toxicity_filter_level": "OFF", "games": [7, 20], "avatar_url": "preset:🐉"})
    assert r.status_code == 200
    perfil = r.json()
    assert perfil["toxicity_filter_level"] == "OFF"
    assert perfil["games"] == [7, 20]
    assert perfil["avatar_url"] == "preset:🐉"
    assert perfil["region"] == "NA_EAST"  # no se envió: no cambia

    sin_juegos = cliente.put("/api/v1/users/me", headers=como("ana"), json={"games": []})
    assert sin_juegos.status_code == 422

    no_editable = cliente.put("/api/v1/users/me", headers=como("ana"), json={"level": 10})
    assert no_editable.status_code == 422


def test_cambiar_nombre_a_uno_ocupado(cliente):
    r = cliente.put("/api/v1/users/me", headers=como("ana"), json={"username": "Bruno_Tank"})
    assert r.status_code == 409


def test_cuentas_vinculadas(cliente):
    r = cliente.put("/api/v1/users/social/steam", headers=como("ana"), json={"external_username": "ana_steam"})
    assert r.status_code == 200
    assert r.json()["steam"] == "ana_steam"

    assert cliente.delete("/api/v1/users/social/steam", headers=como("ana")).status_code == 204
    assert cliente.delete("/api/v1/users/social/steam", headers=como("ana")).status_code == 404
    assert cliente.put("/api/v1/users/social/myspace", headers=como("ana"),
                       json={"external_username": "x"}).status_code == 422


def test_lista_negra(cliente):
    assert cliente.get("/api/v1/users/me/blocks", headers=como("ana")).json() == []

    r = cliente.post("/api/v1/users/me/blocks", headers=como("ana"), json={"user_id": 4, "reason": "No juega en equipo"})
    assert r.status_code == 201
    lista = cliente.get("/api/v1/users/me/blocks", headers=como("ana")).json()
    assert [b["username"] for b in lista] == ["diego_entry"]

    a_mi_mismo = cliente.post("/api/v1/users/me/blocks", headers=como("ana"), json={"user_id": 1})
    assert a_mi_mismo.json()["error"]["code"] == "CANNOT_BLOCK_SELF"
    no_existe = cliente.post("/api/v1/users/me/blocks", headers=como("ana"), json={"user_id": 999})
    assert no_existe.status_code == 404

    assert cliente.delete("/api/v1/users/me/blocks/4", headers=como("ana")).status_code == 204
    assert cliente.delete("/api/v1/users/me/blocks/4", headers=como("ana")).status_code == 404


def test_perfil_publico(cliente):
    perfil = cliente.get("/api/v1/users/2", headers=como("ana")).json()
    assert perfil["username"] == "bruno_tank"
    assert perfil["reviews"]["total"] == 2
    assert {t["tag"] for t in perfil["top_tags"]} == {"GREAT_LEADER", "FRIENDLY"}
    # Datos privados que nunca deben salir en un perfil público
    for privado in ("auth0_id", "role", "warnings_count", "toxicity_filter_level", "penalty_xp"):
        assert privado not in perfil

    assert cliente.get("/api/v1/users/999", headers=como("ana")).status_code == 404


def test_eliminar_cuenta(cliente, db):
    assert cliente.delete("/api/v1/users/me", headers=como("carla")).status_code == 204
    assert db.execute("SELECT 1 FROM users WHERE username = 'carla_heals'").fetchone() is None
    # Su sala se borró en cascada
    assert db.execute("SELECT 1 FROM lfg_posts WHERE title = 'Flex queue, chill vibes'").fetchone() is None
