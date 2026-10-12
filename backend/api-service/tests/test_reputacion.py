"""Pruebas de reseñas, nivel de honor, historial de partidas y reportes.

Datos de demo: la sala 3 (de bruno) terminó con ana y diego. bruno tiene 50 XP (nivel 1),
ana 30 XP (nivel 1) y diego -100 XP (nivel 0, Rookie) por una advertencia.
"""

from conftest import como

RESENAS = "/api/v1/reputation/reviews"


def test_calificar_compañero_sube_su_xp(cliente):
    r = cliente.post(RESENAS, headers=como("ana"),
                     json={"post_id": 3, "target_user_id": 4, "rating": 5, "tag": "TEAM_PLAYER"})
    assert r.status_code == 201
    assert r.json()["target"] == {"username": "diego_entry", "xp": -70, "level": 0}

    otra_vez = cliente.post(RESENAS, headers=como("ana"), json={"post_id": 3, "target_user_id": 4, "rating": 4})
    assert otra_vez.json()["error"]["code"] == "ALREADY_REVIEWED"


def test_reglas_de_las_reseñas(cliente):
    def resenar(usuario, **datos):
        return cliente.post(RESENAS, headers=como(usuario), json={"rating": 5} | datos).json()["error"]["code"]

    assert resenar("ana", post_id=3, target_user_id=1) == "CANNOT_REVIEW_SELF"
    assert resenar("ana", post_id=1, target_user_id=2) == "MATCH_NOT_FINISHED"
    assert resenar("carla", post_id=3, target_user_id=2) == "NOT_IN_MATCH"
    assert resenar("ana", post_id=3, target_user_id=3) == "TARGET_NOT_IN_MATCH"
    assert resenar("ana", post_id=999, target_user_id=2) == "POST_NOT_FOUND"
    assert cliente.post(RESENAS, headers=como("ana"),
                        json={"post_id": 3, "target_user_id": 4, "rating": 6}).status_code == 422


def test_editar_y_borrar_reseña(cliente, db):
    resena_id = db.execute("SELECT id FROM user_reviews WHERE reviewer_id = 1 AND target_user_id = 2").fetchone()[0]

    # 5★ (30 XP) -> 3★ (10 XP): bruno baja de 50 a 30 XP
    r = cliente.put(f"{RESENAS}/{resena_id}", headers=como("ana"), json={"rating": 3, "comment": None})
    assert r.json()["rating"] == 3 and r.json()["comment"] is None
    assert r.json()["target"]["xp"] == 30

    assert cliente.put(f"{RESENAS}/{resena_id}", headers=como("bruno"), json={"rating": 1}).status_code == 403
    assert cliente.put(f"{RESENAS}/{resena_id}", headers=como("ana"), json={"rating": None}).status_code == 422

    assert cliente.delete(f"{RESENAS}/{resena_id}", headers=como("ana")).status_code == 204
    assert db.execute("SELECT xp FROM users WHERE id = 2").fetchone()[0] == 20
    assert cliente.delete(f"{RESENAS}/{resena_id}", headers=como("ana")).status_code == 404


def test_honor_score(cliente):
    bruno = cliente.get("/api/v1/reputation/users/2", headers=como("ana")).json()
    assert bruno["level"] == 1 and bruno["xp"] == 50
    assert bruno["progress"] == {"xp_in_level": 50, "xp_for_next": 50, "percent": 50}
    assert bruno["reviews"]["total"] == 2
    assert bruno["reviews"]["average"] == 4.5
    assert bruno["reviews"]["distribution"] == {"5": 1, "4": 1, "3": 0, "2": 0, "1": 0}
    assert [r["reviewer_username"] for r in bruno["recent_reviews"]] and bruno["recent_reviews"][0]["game_name"] == "Valorant"

    diego = cliente.get("/api/v1/reputation/users/4", headers=como("ana")).json()
    assert diego["is_rookie"] is True
    assert diego["progress"]["xp_for_next"] == 100  # le faltan 100 XP para volver al nivel 1

    assert cliente.get("/api/v1/reputation/users/999", headers=como("ana")).status_code == 404


def test_historial_de_partidas(cliente):
    historial = cliente.get("/api/v1/lfg/history", headers=como("ana")).json()
    assert len(historial) == 1
    partida = historial[0]
    assert partida["title"] == "Partida de ayer" and partida["game_name"] == "Valorant"
    companeros = {c["username"]: c for c in partida["teammates"]}
    assert set(companeros) == {"bruno_tank", "diego_entry"}
    assert companeros["bruno_tank"]["already_reviewed"] is True
    assert companeros["diego_entry"]["already_reviewed"] is False

    # diego tiene a bruno en su lista negra
    de_diego = cliente.get("/api/v1/lfg/history", headers=como("diego")).json()[0]["teammates"]
    assert {c["username"]: c["is_blocked"] for c in de_diego} == {"ana_gg": False, "bruno_tank": True}

    assert cliente.get("/api/v1/lfg/history", headers=como("carla")).json() == []


def test_mis_salas_activas(cliente):
    assert [s["title"] for s in cliente.get("/api/v1/lfg/mine", headers=como("ana")).json()] == ["Ranked tranqui esta noche"]
    # bruno no es anfitrión de la sala 1, pero está aceptado
    de_bruno = cliente.get("/api/v1/lfg/mine", headers=como("bruno")).json()
    assert [(s["title"], s["is_host"]) for s in de_bruno] == [("Ranked tranqui esta noche", False)]


# ---------------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------------
def test_reportar(cliente):
    reporte = {"reported_user_id": 4, "post_id": 3, "reason": "TOXIC_CHAT", "comment": "Insultó a todo el equipo."}
    r = cliente.post("/api/v1/reports", headers=como("ana"), json=reporte)
    assert r.status_code == 201 and r.json()["status"] == "PENDING"

    assert cliente.post("/api/v1/reports", headers=como("ana"), json=reporte).json()["error"]["code"] == "ALREADY_REPORTED"
    # carla no estuvo en esa partida
    assert cliente.post("/api/v1/reports", headers=como("carla"), json=reporte).json()["error"]["code"] == "NOT_TEAMMATES"
    assert cliente.post("/api/v1/reports", headers=como("diego"),
                        json=reporte).json()["error"]["code"] == "CANNOT_REPORT_SELF"
    # El comentario debe explicar lo que pasó (mínimo 10 caracteres)
    assert cliente.post("/api/v1/reports", headers=como("ana"),
                        json=reporte | {"reported_user_id": 2, "comment": "malo"}).status_code == 422


def test_mis_reportes(cliente):
    de_bruno = cliente.get("/api/v1/reports/mine", headers=como("bruno")).json()
    assert [(r["reported_username"], r["status"]) for r in de_bruno] == [("diego_entry", "WARNED")]
    assert "admin_notes" not in de_bruno[0]  # las notas del admin son internas
