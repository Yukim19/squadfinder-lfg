"""Punto de entrada del api-service.

Ejecutar en desarrollo (desde backend/api-service):
    uvicorn app.main:app --reload --port 8001
Documentación interactiva: http://127.0.0.1:8001/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import abrir_pool, cerrar_pool
from .errors import registrar_manejadores
from .routers import admin, catalog, lfg, reports, reputation, users
from .security import Db

PREFIJO = "/api/v1"
ORIGEN_LOCAL = r"http://(localhost|127\.0\.0\.1)(:\d+)?"


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    abrir_pool(get_settings().database_url)
    yield
    cerrar_pool()


def crear_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SquadFinder LFG - api-service",
        version="0.1.0",
        description="API REST principal: usuarios, catálogo, salas, solicitudes, reputación y moderación.",
        lifespan=ciclo_de_vida,
        # La documentación interactiva no se publica en producción
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # En desarrollo se acepta cualquier puerto local (Live Server, vista previa, etc.)
        allow_origin_regex=ORIGEN_LOCAL if settings.environment == "development" else None,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Dev-User"],
    )
    registrar_manejadores(app)

    @app.get(f"{PREFIJO}/health", tags=["Sistema"], summary="Estado del servicio y de la base de datos")
    def health(db: Db) -> dict:
        db.execute("SELECT 1")
        # auth_mode le dice al frontend si usar Auth0 o los usuarios de prueba
        return {"status": "ok", "database": "ok", "environment": settings.environment, "auth_mode": settings.auth_mode}

    app.include_router(catalog.router, prefix=PREFIJO)
    app.include_router(users.router, prefix=PREFIJO)
    app.include_router(lfg.router, prefix=PREFIJO)
    app.include_router(reputation.router, prefix=PREFIJO)
    app.include_router(reports.router, prefix=PREFIJO)
    app.include_router(admin.router, prefix=PREFIJO)
    return app


app = crear_app()
