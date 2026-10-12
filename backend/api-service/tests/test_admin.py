"""Pruebas del panel de administración: reportes, sanciones, reglas y juegos sugeridos.

Datos de demo: reporte 1 = diego reporta a bruno (pendiente; bruno escribió un mensaje SEVERE
en la sala 3); reporte 2 = ya resuelto con advertencia. Reglas: 3 advertencias = eliminar cuenta.
"""

from conftest import como

REPORTES = "/api/v1/admin/reports"


def test_solo_administradores(cliente):
    for ruta in (REPORTES, "/api/v1/admin/settings", "/api/v1/admin/game-requests"):
        r = cliente.get(ruta, headers=como("bruno"))
        assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"


def test_lista_de_reportes_con_evidencia(cliente):
    reportes = cliente.get(REPORTES, headers=como("ana")).json()
    assert [r["status"] for r in reportes] == ["PENDING", "WARNED"]  # pendientes primero
    pendiente = reportes[0]
    assert pendiente["reported_username"] == "bruno_tank"
    assert [m["toxicity_level"] for m in pendiente["evidence"]] == ["SEVERE"]
    assert cliente.get(REPORTES, headers=como("ana"), params={"status": "WARNED"}).json()[0]["id"] == 2
    assert cliente.get(f"{REPORTES}/999", headers=como("ana")).status_code == 404


def test_advertencia(cliente):
    r = cliente.put(f"{REPORTES}/1", headers=como("ana"), json={"action": "WARNED", "notes": "Cuidado con el chat"})
    assert r.status_code == 200
    resultado = r.json()
    assert resultado["status"] == "WARNED" and resultado["levels_removed"] == 1
    # bruno tenía 50 XP; la advertencia quita 1 nivel (100 XP) y queda Rookie
    assert resultado["reported_user"]["warnings_count"] == 1
    assert resultado["reported_user"]["xp"] == -50 and resultado["reported_user"]["level"] == 0

    otra_vez = cliente.put(f"{REPORTES}/1", headers=como("ana"), json={"action": "DISMISSED"})
    assert otra_vez.json()["error"]["code"] == "REPORT_ALREADY_RESOLVED"


def test_regla_automatica_de_advertencias(cliente):
    cliente.put("/api/v1/admin/settings", headers=como("ana"),
                json={"warnings_limit": 1, "auto_action": "SUSPEND", "auto_suspension_days": 5})
    resultado = cliente.put(f"{REPORTES}/1", headers=como("ana"), json={"action": "WARNED"}).json()
    assert resultado["status"] == "SUSPENDED" and resultado["is_automatic"] is True
    assert resultado["suspension_days"] == 5
    assert resultado["reported_user"]["account_status"] == "SUSPENDED"
    # La suspensión ya se nota al intentar usar la API
    assert cliente.get("/api/v1/users/me", headers=como("bruno")).json()["error"]["code"] == "ACCOUNT_SUSPENDED"


def test_suspension_personalizada(cliente):
    resultado = cliente.put(f"{REPORTES}/1", headers=como("ana"),
                            json={"action": "SUSPENDED", "suspension_days": 3, "levels_removed": 0}).json()
    assert resultado["suspension_days"] == 3 and resultado["levels_removed"] == 0
    assert resultado["reported_user"]["xp"] == 50  # sin niveles descontados
    assert cliente.put(f"{REPORTES}/1", headers=como("ana"),
                       json={"action": "SUSPENDED", "suspension_days": 400}).status_code == 422


def test_eliminar_cuenta_y_reactivar(cliente):
    resultado = cliente.put(f"{REPORTES}/1", headers=como("ana"), json={"action": "BANNED"}).json()
    assert resultado["reported_user"]["account_status"] == "BANNED"
    assert cliente.get("/api/v1/users/me", headers=como("bruno")).json()["error"]["code"] == "ACCOUNT_BANNED"
    assert cliente.get("/api/v1/users/2", headers=como("carla")).status_code == 404

    reactivado = cliente.post("/api/v1/admin/users/2/reactivate", headers=como("ana")).json()
    assert reactivado["account_status"] == "ACTIVE"
    assert cliente.get("/api/v1/users/me", headers=como("bruno")).status_code == 200


def test_reglas_de_moderacion(cliente):
    reglas = cliente.get("/api/v1/admin/settings", headers=como("ana")).json()
    assert reglas["warnings_limit"] == 3 and reglas["auto_action"] == "BAN"

    nuevas = cliente.put("/api/v1/admin/settings", headers=como("ana"), json={"warnings_limit": 5}).json()
    assert nuevas["warnings_limit"] == 5 and nuevas["auto_action"] == "BAN"  # lo demás no cambia
    assert nuevas["updated_by"] == 1
    assert cliente.put("/api/v1/admin/settings", headers=como("ana"), json={"warnings_limit": 11}).status_code == 422
    assert cliente.put("/api/v1/admin/settings", headers=como("ana"), json={"auto_action": "KICK"}).status_code == 422


def test_aprobar_juego_sugerido(cliente):
    pendientes = cliente.get("/api/v1/admin/game-requests", headers=como("ana"), params={"status": "PENDING"}).json()
    assert [s["game_name"] for s in pendientes] == ["Deadlock"]
    deadlock = pendientes[0]["id"]

    sin_datos = cliente.put(f"/api/v1/admin/game-requests/{deadlock}", headers=como("ana"), json={"status": "APPROVED"})
    assert sin_datos.status_code == 422

    r = cliente.put(f"/api/v1/admin/game-requests/{deadlock}", headers=como("ana"),
                    json={"status": "APPROVED", "genre_id": 1, "platforms": ["PC"]})
    assert r.json()["status"] == "APPROVED" and r.json()["game_id"] is not None

    # Ya aparece en el catálogo para todos
    juegos = cliente.get("/api/v1/catalog/games").json()
    assert len(juegos) == 36 and any(j["name"] == "Deadlock" for j in juegos)

    otra_vez = cliente.put(f"/api/v1/admin/game-requests/{deadlock}", headers=como("ana"), json={"status": "REJECTED"})
    assert otra_vez.json()["error"]["code"] == "REQUEST_ALREADY_REVIEWED"


def test_rechazar_y_nombre_repetido(cliente):
    sugerencia = cliente.post("/api/v1/catalog/game-requests", headers=como("bruno"),
                              json={"game_name": "Valoran"}).json()
    # El admin corrige el nombre, pero Valorant ya existe
    r = cliente.put(f"/api/v1/admin/game-requests/{sugerencia['id']}", headers=como("ana"),
                    json={"status": "APPROVED", "name": "valorant", "genre_id": 1, "platforms": ["PC"]})
    assert r.json()["error"]["code"] == "GAME_EXISTS"

    rechazada = cliente.put(f"/api/v1/admin/game-requests/{sugerencia['id']}", headers=como("ana"),
                            json={"status": "REJECTED"})
    assert rechazada.json()["status"] == "REJECTED" and rechazada.json()["reviewed_by"] == 1
