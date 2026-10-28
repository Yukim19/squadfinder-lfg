"""Punto de entrada del realtime-service (chat en vivo).

Ejecutar en desarrollo (desde backend/realtime-service):
    uvicorn app.main:app --reload --port 8002
Documentación interactiva: http://127.0.0.1:8002/docs

Protocolo del WebSocket /ws/chat/{post_id} (mensajes JSON):
    cliente -> {"type": "auth", "token": "<JWT>"}       (primer mensaje, antes de 10 s)
    servidor -> {"type": "ready", "history": [...], "read_only": false, ...}
    cliente -> {"type": "message", "message": "texto"}
    servidor -> {"type": "message", ...}                (a cada integrante, según su filtro)
    servidor -> {"type": "presence", "online": [...]}   (alguien entró o salió)
    servidor -> {"type": "error", "code": "...", "message": "..."}
    cliente -> {"type": "ping"}  /  servidor -> {"type": "pong"}

Mensajes privados entre amigos: WebSocket /ws/dm (ver su docstring) e historial en /api/v1/dm/{id}/history.
"""

import asyncio
import json
import re
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from .chat import ABIERTAS, Conexion, Salas, guardar_mensaje, historial, permitido_por_ritmo
from .mensajes import (Buzones, guardar_mensaje_privado, historial_privado, ids_de_amigos, marcar_leidos,
                       mensaje_privado_para)
from .config import get_settings
from .database import abrir_pool, cerrar_pool, conexion
from .security import ErrorAuth, acceso_a_sala, usuario_activo, verificar_token

PREFIJO = "/api/v1"
MAX_CARACTERES = 500
ORIGEN_LOCAL = r"http://(localhost|127\.0\.0\.1)(:\d+)?"

# Código HTTP y código de cierre del WebSocket para cada error
ESTADOS = {"NOT_AUTHENTICATED": 401, "TOKEN_EXPIRED": 401, "INVALID_TOKEN": 401, "POST_NOT_FOUND": 404,
           "USER_NOT_FOUND": 404}
CIERRES = {401: 4401, 403: 4403, 404: 4404}

bearer = HTTPBearer(auto_error=False)
dev_user = APIKeyHeader(name="X-Dev-User", auto_error=False, description="Usuario de prueba, por ejemplo demo|ana")


def _autenticar(token: str | None, post_id: int) -> tuple[dict, dict]:
    """Usuario y sala, o ErrorAuth. Se ejecuta en un hilo aparte (psycopg es síncrono)."""
    sub = verificar_token(token, get_settings())
    with conexion() as db:
        usuario = usuario_activo(db, sub)
        sala = acceso_a_sala(db, post_id, usuario["id"])
    return usuario, sala


def _autenticar_usuario(token: str | None) -> dict:
    """Usuario autenticado (sin sala), para los mensajes privados."""
    sub = verificar_token(token, get_settings())
    with conexion() as db:
        return usuario_activo(db, sub)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    abrir_pool(get_settings().database_url)
    yield
    cerrar_pool()


def crear_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SquadFinder LFG - realtime-service",
        version="0.1.0",
        description="Chat en vivo por WebSocket con filtro anti-toxicidad (NLTK).",
        lifespan=ciclo_de_vida,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=ORIGEN_LOCAL if settings.environment == "development" else None,
        allow_methods=["GET"],
        allow_headers=["Authorization", "X-Dev-User"],
    )
    salas = Salas()
    buzones = Buzones()

    @app.exception_handler(ErrorAuth)
    async def _error_auth(_: Request, exc: ErrorAuth) -> JSONResponse:
        return JSONResponse(status_code=ESTADOS.get(exc.code, 403),
                            content={"error": {"code": exc.code, "message": exc.message, "details": None}})

    @app.get(f"{PREFIJO}/health", tags=["Sistema"], summary="Estado del servicio y de la base de datos")
    def health() -> dict:
        with conexion() as db:
            db.execute("SELECT 1")
        return {"status": "ok", "database": "ok", "environment": settings.environment}

    # Ruta de la propuesta: GET /api/v1/chat/posts/{post_id}/history
    @app.get(f"{PREFIJO}/chat/posts/{{post_id}}/history", tags=["Chat"],
             summary="Mensajes anteriores de la sala (filtrados según mi nivel de filtro)")
    def ver_historial(
        post_id: int,
        credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        sub_dev: Annotated[str | None, Depends(dev_user)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        before_id: Annotated[int | None, Query(description="Para cargar mensajes más viejos")] = None,
    ) -> list[dict]:
        token = sub_dev if settings.auth_mode == "dev" else (credenciales.credentials if credenciales else None)
        usuario, _ = _autenticar(token, post_id)
        return historial(post_id, usuario, limit, before_id)

    @app.websocket("/ws/chat/{post_id}")
    async def chat(websocket: WebSocket, post_id: int):
        # Solo las páginas permitidas pueden abrir el chat (protege contra sitios de terceros)
        origen = websocket.headers.get("origin")
        local = settings.environment == "development" and origen and re.fullmatch(ORIGEN_LOCAL, origen)
        if origen and origen not in settings.cors_origins and not local:
            await websocket.close(code=4403, reason="Origen no permitido")
            return
        await websocket.accept()

        async def error(code: str, message: str) -> None:
            await websocket.send_json({"type": "error", "code": code, "message": message})

        try:
            primero = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout=10))
            if not isinstance(primero, dict) or primero.get("type") != "auth":
                raise ErrorAuth("NOT_AUTHENTICATED", "El primer mensaje debe ser de tipo auth.")
            usuario, sala = await run_in_threadpool(_autenticar, primero.get("token"), post_id)
        except (asyncio.TimeoutError, json.JSONDecodeError):
            await error("NOT_AUTHENTICATED", "Debes iniciar sesión.")
            await websocket.close(code=4401)
            return
        except ErrorAuth as exc:
            await error(exc.code, exc.message)
            await websocket.close(code=CIERRES[ESTADOS.get(exc.code, 403)])
            return
        except WebSocketDisconnect:
            return

        actual = Conexion(websocket, usuario)
        salas.entrar(post_id, actual)
        try:
            await websocket.send_json({
                "type": "ready",
                "post_id": post_id,
                "user": {"id": usuario["id"], "username": usuario["username"],
                         "toxicity_filter_level": usuario["toxicity_filter_level"]},
                "read_only": sala["status"] not in ABIERTAS,
                "history": await run_in_threadpool(historial, post_id, usuario, 50, None),
            })
            await salas.avisar_presencia(post_id)

            while True:
                try:
                    datos = json.loads(await websocket.receive_text())
                except json.JSONDecodeError:
                    await error("INVALID_JSON", "El mensaje no es JSON válido.")
                    continue
                tipo = datos.get("type") if isinstance(datos, dict) else None

                if tipo == "ping":
                    await websocket.send_json({"type": "pong"})
                elif tipo == "message":
                    texto = str(datos.get("message") or "").strip()
                    if not texto or len(texto) > MAX_CARACTERES:
                        await error("VALIDATION_ERROR", f"El mensaje debe tener entre 1 y {MAX_CARACTERES} caracteres.")
                        continue
                    if not permitido_por_ritmo(actual, settings.max_mensajes, settings.ventana_segundos):
                        await error("RATE_LIMITED", "Estás enviando mensajes muy rápido. Espera unos segundos.")
                        continue
                    try:
                        fila = await run_in_threadpool(guardar_mensaje, post_id, usuario, texto)
                    except ErrorAuth as exc:
                        await error(exc.code, exc.message)
                        if exc.code in ("NOT_A_MEMBER", "POST_NOT_FOUND"):
                            # Lo sacaron de la sala mientras estaba conectado
                            await websocket.close(code=CIERRES[ESTADOS.get(exc.code, 403)])
                            break
                        continue
                    await salas.repartir(post_id, fila)
                else:
                    await error("UNKNOWN_TYPE", "Tipo de mensaje desconocido.")
        except WebSocketDisconnect:
            pass
        finally:
            salas.salir(post_id, actual)
            await salas.avisar_presencia(post_id)

    # ------------------------------------------------------------------
    # Mensajes privados entre amigos
    # ------------------------------------------------------------------
    def _usuario_dm(credenciales, sub_dev) -> dict:
        token = sub_dev if settings.auth_mode == "dev" else (credenciales.credentials if credenciales else None)
        return _autenticar_usuario(token)

    @app.get(f"{PREFIJO}/dm/{{user_id}}/history", tags=["Mensajes privados"],
             summary="Conversación con un amigo (filtrada según mi nivel de filtro)")
    def ver_historial_privado(
        user_id: int,
        credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        sub_dev: Annotated[str | None, Depends(dev_user)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        before_id: Annotated[int | None, Query(description="Para cargar mensajes más viejos")] = None,
    ) -> list[dict]:
        return historial_privado(_usuario_dm(credenciales, sub_dev), user_id, limit, before_id)

    @app.post(f"{PREFIJO}/dm/{{user_id}}/read", tags=["Mensajes privados"],
              summary="Marcar como leídos los mensajes de un amigo")
    def marcar_leido(
        user_id: int,
        credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        sub_dev: Annotated[str | None, Depends(dev_user)],
    ) -> dict:
        return {"marked": marcar_leidos(_usuario_dm(credenciales, sub_dev), user_id)}

    @app.websocket("/ws/dm")
    async def mensajes_privados(websocket: WebSocket):
        """Protocolo (JSON):
            cliente -> {"type": "auth", "token": "..."}
            servidor -> {"type": "ready", "online": [ids de amigos conectados]}
            cliente -> {"type": "message", "to": <id del amigo>, "message": "texto"}
            servidor -> {"type": "message", ...}   (al amigo y a ti: el eco confirma que se guardó)
            cliente -> {"type": "read", "with": <id del amigo>}
            servidor -> {"type": "presence", "user_id": 2, "online": true}
        """
        origen = websocket.headers.get("origin")
        local = settings.environment == "development" and origen and re.fullmatch(ORIGEN_LOCAL, origen)
        if origen and origen not in settings.cors_origins and not local:
            await websocket.close(code=4403, reason="Origen no permitido")
            return
        await websocket.accept()

        async def error(code: str, message: str) -> None:
            await websocket.send_json({"type": "error", "code": code, "message": message})

        try:
            primero = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout=10))
            if not isinstance(primero, dict) or primero.get("type") != "auth":
                raise ErrorAuth("NOT_AUTHENTICATED", "El primer mensaje debe ser de tipo auth.")
            usuario = await run_in_threadpool(_autenticar_usuario, primero.get("token"))
        except (asyncio.TimeoutError, json.JSONDecodeError):
            await error("NOT_AUTHENTICATED", "Debes iniciar sesión.")
            await websocket.close(code=4401)
            return
        except ErrorAuth as exc:
            await error(exc.code, exc.message)
            await websocket.close(code=CIERRES[ESTADOS.get(exc.code, 403)])
            return
        except WebSocketDisconnect:
            return

        actual = Conexion(websocket, usuario)
        amigos = await run_in_threadpool(ids_de_amigos, usuario["id"])
        primera_pestana = not buzones.en_linea(usuario["id"])
        buzones.entrar(actual)
        try:
            await websocket.send_json({"type": "ready", "user": {"id": usuario["id"], "username": usuario["username"]},
                                       "online": [a for a in amigos if buzones.en_linea(a)]})
            if primera_pestana:
                for amigo in amigos:
                    await buzones.enviar(amigo, lambda _: {"type": "presence", "user_id": usuario["id"], "online": True})

            while True:
                try:
                    datos = json.loads(await websocket.receive_text())
                except json.JSONDecodeError:
                    await error("INVALID_JSON", "El mensaje no es JSON válido.")
                    continue
                tipo = datos.get("type") if isinstance(datos, dict) else None

                if tipo == "ping":
                    await websocket.send_json({"type": "pong"})
                elif tipo == "message":
                    texto = str(datos.get("message") or "").strip()
                    destino = datos.get("to")
                    if not isinstance(destino, int) or not texto or len(texto) > MAX_CARACTERES:
                        await error("VALIDATION_ERROR", f"Indica a quién y un mensaje de 1 a {MAX_CARACTERES} caracteres.")
                        continue
                    if not permitido_por_ritmo(actual, settings.max_mensajes, settings.ventana_segundos):
                        await error("RATE_LIMITED", "Estás enviando mensajes muy rápido. Espera unos segundos.")
                        continue
                    try:
                        fila, _ = await run_in_threadpool(guardar_mensaje_privado, usuario, destino, texto)
                    except ErrorAuth as exc:
                        await error(exc.code, exc.message)
                        continue
                    await buzones.enviar(destino, lambda receptor: mensaje_privado_para(fila, receptor))
                    await buzones.enviar(usuario["id"], lambda receptor: mensaje_privado_para(fila, receptor))
                elif tipo == "read":
                    otro = datos.get("with")
                    if not isinstance(otro, int):
                        await error("VALIDATION_ERROR", "Indica de qué amigo son los mensajes.")
                        continue
                    try:
                        await run_in_threadpool(marcar_leidos, usuario, otro)
                    except ErrorAuth as exc:
                        await error(exc.code, exc.message)
                        continue
                    # Para que otras pestañas del mismo usuario también actualicen su contador
                    await buzones.enviar(usuario["id"], lambda _: {"type": "read", "with": otro})
                else:
                    await error("UNKNOWN_TYPE", "Tipo de mensaje desconocido.")
        except WebSocketDisconnect:
            pass
        finally:
            buzones.salir(actual)
            if not buzones.en_linea(usuario["id"]):
                for amigo in amigos:
                    await buzones.enviar(amigo, lambda _: {"type": "presence", "user_id": usuario["id"], "online": False})

    return app


app = crear_app()
